#!/usr/bin/env python3
"""Generate an interactive HTML performance dashboard from trace.db.

The dashboard treats each `session_id` as one evaluation task (one user
question executed by the agent framework). Every task can be viewed in
isolation; the global view compares tasks side-by-side.

Usage:
    python scripts/export_dashboard.py --db cc_traces/trace.db --output perf_dashboard.html

The output is a fully self-contained HTML file (CSS + ECharts via CDN + embedded
JSON data). Open it in any modern browser; no server needed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from export_perf import PerfRecord, _load_records, _summarize


def _load_dotenv(env_path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Does not overwrite existing environment variables.
    """
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


def _derive_metrics_url(openai_base_url: Optional[str]) -> Optional[str]:
    """Derive vLLM metrics URL from OPENAI_BASE_URL.

    OPENAI_BASE_URL usually looks like http://host:port/v1;
    the Prometheus metrics are exposed at http://host:port/metrics.
    """
    if not openai_base_url:
        return None
    url = openai_base_url.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url + "/metrics"


def _fetch_vllm_metrics(metrics_url: str) -> Optional[str]:
    """Fetch raw Prometheus metrics text from vLLM."""
    try:
        with urllib.request.urlopen(metrics_url, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"Warning: could not fetch vLLM metrics from {metrics_url}: {exc}")
        return None


def _parse_metric_value(metrics_text: str, metric_name: str, labels: Optional[str] = None) -> Optional[float]:
    """Parse a single counter/gauge value from Prometheus text format."""
    pattern = rf"^{re.escape(metric_name)}"
    if labels is not None:
        pattern += rf"\{{{re.escape(labels)}\}}"
    else:
        pattern += r"(?:\{[^\}]*\})?"
    pattern += r"\s+([0-9eE+\-.]+)$"
    for line in metrics_text.splitlines():
        m = re.match(pattern, line)
        if m:
            return float(m.group(1))
    return None


def _compute_approx_cache_hit_rate(records: List[PerfRecord], metrics_url: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str]]:
    """Return (cache_hit_rate_pct, total_prefill, computed_tokens, note).

    cache_hit_rate_pct is approximate because it compares trace-level total
    prefill with vLLM global computed-token counter. It only makes sense when
    the trace DB corresponds to the same vLLM instance since its last restart.
    """
    if not metrics_url:
        return None, None, None, "未配置 vLLM metrics URL"

    metrics_text = _fetch_vllm_metrics(metrics_url)
    if metrics_text is None:
        return None, None, None, f"无法拉取 metrics: {metrics_url}"

    # Try vLLM's native prefix-cache counters first.
    hits = _parse_metric_value(metrics_text, "vllm:prefix_cache_hits_total")
    queries = _parse_metric_value(metrics_text, "vllm:prefix_cache_queries_total")
    if hits is not None and queries is not None and queries > 0:
        rate = hits / queries * 100
        return round(rate, 2), None, None, "来自 vllm:prefix_cache_*_total"

    # Fallback: use computed tokens vs total prompt tokens.
    computed_sum = _parse_metric_value(metrics_text, "vllm:request_prefill_kv_computed_tokens_sum")
    if computed_sum is None:
        return None, None, None, "metrics 中缺少 request_prefill_kv_computed_tokens_sum"

    total_prefill = sum((r.prefill_tokens or 0) for r in records)
    if total_prefill <= 0:
        return None, None, None, "trace 中没有 prefill token 数据"

    if computed_sum > total_prefill:
        # Metrics counter accumulated more than the trace window (e.g. vLLM was
        # running before these traces, or other traffic hit it). Cannot estimate.
        return None, total_prefill, computed_sum, "computed > prefill，可能 vLLM 还服务了其他流量"

    rate = (1 - computed_sum / total_prefill) * 100
    return round(rate, 2), total_prefill, computed_sum, "估算：1 - computed/prefill"


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LLM Perf Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <style>
    :root {
      --bg: #0b0d12;
      --bg-card: #12151d;
      --bg-hover: #1a1e29;
      --border: #232837;
      --text: #e6e8ef;
      --text-muted: #8b92a8;
      --accent: #6366f1;
      --accent-2: #22d3ee;
      --accent-3: #f472b6;
      --success: #34d399;
      --warning: #fbbf24;
      --danger: #f87171;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
      --shadow: 0 8px 24px rgba(0,0,0,.28);
    }
    .light {
      --bg: #f8f9fc;
      --bg-card: #ffffff;
      --bg-hover: #f1f4f9;
      --border: #e2e6f0;
      --text: #1f2937;
      --text-muted: #5d6474;
      --accent: #4f46e5;
      --accent-2: #0891b2;
      --accent-3: #db2777;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --shadow: 0 8px 24px rgba(0,0,0,.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--font);
      background: var(--bg);
      color: var(--text);
      transition: background .2s, color .2s;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(12px);
      background: color-mix(in srgb, var(--bg) 92%, transparent);
      border-bottom: 1px solid var(--border);
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand h1 { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -.2px; }
    .brand .subtitle { color: var(--text-muted); font-size: 12px; margin-top: 2px; }
    .logo {
      width: 36px; height: 36px; border-radius: 10px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      display: grid; place-items: center; font-weight: 800; color: #fff; font-size: 14px;
    }
    .controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    select, button, input {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      cursor: pointer;
      transition: background .15s, border-color .15s;
    }
    select:hover, button:hover { background: var(--bg-hover); border-color: var(--accent); }
    button.primary {
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      border: none; color: #fff; font-weight: 600;
    }
    button.primary:hover { filter: brightness(1.08); }
    main { padding: 24px; max-width: 1600px; margin: 0 auto; }
    .section-title {
      font-size: 16px; font-weight: 700; margin: 0 0 14px 0; color: var(--text);
      display: flex; align-items: center; gap: 8px;
    }
    .section-title::before { content: ""; display: inline-block; width: 6px; height: 14px; border-radius: 3px; background: linear-gradient(180deg, var(--accent), var(--accent-2)); }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .kpi {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
      position: relative;
      overflow: hidden;
      transition: transform .15s, box-shadow .15s;
      box-shadow: var(--shadow);
    }
    .kpi:hover { transform: translateY(-2px); }
    .kpi::before {
      content: "";
      position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      opacity: .7;
    }
    .kpi-label { color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: .6px; margin-bottom: 8px; }
    .kpi-value { font-size: 25px; font-weight: 800; letter-spacing: -.5px; }
    .kpi-sub { color: var(--text-muted); font-size: 12px; margin-top: 6px; }
    .task-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .task-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      cursor: pointer;
      transition: transform .15s, border-color .15s, box-shadow .15s;
      box-shadow: var(--shadow);
    }
    .task-card:hover { transform: translateY(-2px); border-color: var(--accent); }
    .task-card.active { border-color: var(--accent); box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent); }
    .task-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }
    .task-main { display: flex; gap: 16px; margin-bottom: 12px; }
    .task-metric { flex: 1; }
    .task-metric .value { font-size: 20px; font-weight: 800; }
    .task-metric .label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
    .task-row { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); margin-top: 6px; }
    .task-row span:last-child { color: var(--text); font-weight: 600; }
    .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); gap: 20px; margin-bottom: 24px; }
    .grid-1 { display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 24px; }
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
      box-shadow: var(--shadow);
    }
    .card-title { font-size: 15px; font-weight: 700; margin: 0 0 14px 0; color: var(--text); display: flex; align-items: center; gap: 8px; }
    .card-title::before { content: ""; display: inline-block; width: 6px; height: 14px; border-radius: 3px; background: linear-gradient(180deg, var(--accent), var(--accent-2)); }
    .chart { width: 100%; height: 340px; position: relative; }
    .chart-tall { height: 420px; }
    .no-data {
      position: absolute; inset: 0; display: grid; place-items: center; color: var(--text-muted); font-size: 14px; pointer-events: none;
    }
    .table-wrap { overflow: auto; max-height: 520px; border-radius: 10px; border: 1px solid var(--border); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
    th { position: sticky; top: 0; background: var(--bg-card); color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: .5px; z-index: 2; }
    tr:hover td { background: var(--bg-hover); }
    .tag {
      display: inline-block; padding: 3px 8px; border-radius: 20px; font-size: 11px; font-weight: 600;
      background: color-mix(in srgb, var(--accent) 15%, transparent);
      color: var(--accent);
    }
    footer { text-align: center; padding: 30px; color: var(--text-muted); font-size: 12px; }
    .model-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
    .model-card { background: var(--bg-hover); border-radius: 12px; padding: 14px; border: 1px solid var(--border); }
    .model-card .m-name { font-weight: 700; font-size: 14px; margin-bottom: 8px; }
    .model-card .m-row { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); margin-top: 4px; }
    .model-card .m-row span:last-child { color: var(--text); font-weight: 600; }
    .view-hint { color: var(--text-muted); font-size: 13px; margin-bottom: 18px; padding: 10px 14px; background: var(--bg-card); border-radius: 10px; border: 1px dashed var(--border); }
    @media (max-width: 640px) {
      .grid-2 { grid-template-columns: 1fr; }
      .kpi-value { font-size: 22px; }
      .chart { height: 280px; }
      .task-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="logo">P</div>
      <div>
        <h1>LLM 推理性能看板</h1>
        <div class="subtitle" id="subtitle">加载中...</div>
      </div>
    </div>
    <div class="controls">
      <select id="taskFilter"><option value="">所有任务</option></select>
      <select id="modelFilter"><option value="">所有模型</option></select>
      <select id="roleFilter"><option value="">所有 Role</option></select>
      <button class="primary" onclick="resetFilters()">重置</button>
      <button onclick="toggleTheme()">🌓 主题</button>
    </div>
  </header>

  <main>
    <div class="view-hint" id="view-hint">👇 点击任意任务卡片可单独查看该任务的完整指标与轮次曲线</div>

    <section>
      <div class="section-title">任务列表</div>
      <div class="task-grid" id="task-grid"></div>
    </section>

    <section class="kpi-grid" id="kpis"></section>

    <section class="grid-2" id="single-task-charts">
      <div class="card">
        <div class="card-title">TTFT vs Prefill 长度</div>
        <div id="chart-ttft" class="chart"><div class="no-data" id="nodata-ttft" style="display:none">暂无 perf 数据</div></div>
      </div>
      <div class="card">
        <div class="card-title">TPOT 分布</div>
        <div id="chart-tpot" class="chart"><div class="no-data" id="nodata-tpot" style="display:none">暂无 perf 数据</div></div>
      </div>
    </section>

    <section class="grid-2" id="single-task-turn-charts">
      <div class="card">
        <div class="card-title">该任务 Token 数量随轮次变化</div>
        <div id="chart-tokens-turn" class="chart chart-tall"></div>
      </div>
      <div class="card">
        <div class="card-title">该任务缓存命中率随轮次变化</div>
        <div id="chart-cache-turn" class="chart chart-tall"></div>
      </div>
    </section>

    <section class="grid-1" id="single-task-latency">
      <div class="card">
        <div class="card-title">该任务逐轮延迟拆解（prefill + decode）</div>
        <div id="chart-latency" class="chart chart-tall"><div class="no-data" id="nodata-latency" style="display:none">暂无 perf 数据</div></div>
      </div>
    </section>

    <section class="grid-1" id="all-tasks-charts">
      <div class="card">
        <div class="card-title">任务总耗时对比</div>
        <div id="chart-task-duration" class="chart chart-tall"></div>
      </div>
      <div class="card">
        <div class="card-title">任务 Token 生成对比</div>
        <div id="chart-task-tokens" class="chart chart-tall"></div>
      </div>
      <div class="card">
        <div class="card-title">任务平均 TTFT / TPOT 对比</div>
        <div id="chart-task-perf" class="chart chart-tall"></div>
      </div>
    </section>

    <section class="grid-1">
      <div class="card">
        <div class="card-title">模型对比</div>
        <div class="model-grid" id="model-grid"></div>
      </div>
    </section>

    <section class="grid-1">
      <div class="card">
        <div class="card-title">原始数据（<span id="table-count">0</span> 条）</div>
        <div class="table-wrap">
          <table id="data-table">
            <thead><tr>
              <th>trace_id</th><th>task</th><th>turn</th><th>role</th><th>model</th>
              <th>prefill</th><th>cached</th><th>output</th><th>duration(ms)</th>
              <th>ttft(ms)</th><th>prefill(ms)</th><th>decode(ms)</th><th>tpot(ms)</th>
            </tr></thead>
            <tbody id="table-body"></tbody>
          </table>
        </div>
      </div>
    </section>
  </main>

  <footer>
    Generated by claude-code-proxy/scripts/export_dashboard.py · ECharts 5
  </footer>

  <script>
    const DATA = __DATA_JSON__;
    const SUMMARY = __SUMMARY_JSON__;
    const TASKS = DATA.tasks || [];
    const RECORDS = DATA.records || [];
    const MODEL_SUMMARY = SUMMARY.model_summary || [];

    const state = { task: "", model: "", role: "" };
    const chartInstances = {};
    const allChartIds = ["chart-ttft", "chart-tpot", "chart-tokens-turn", "chart-cache-turn", "chart-latency", "chart-task-duration", "chart-task-tokens", "chart-task-perf"];

    function fmtNum(n, digits = 1) {
      if (n === null || n === undefined || Number.isNaN(n)) return "-";
      return Number(n).toLocaleString(undefined, { maximumFractionDigits: digits });
    }
    function fmtMs(n) { return fmtNum(n, 0); }
    function fmtPct(n) { return n === null || n === undefined ? "-" : Number(n).toFixed(1) + "%"; }

    function filteredRecords() {
      return RECORDS.filter(r =>
        (!state.task || r.session_id === state.task) &&
        (!state.model || r.model_mapped === state.model) &&
        (!state.role || r.role_kind === state.role)
      );
    }

    function selectedTask() {
      return state.task ? TASKS.find(t => t.task_id === state.task) : null;
    }

    function avg(arr) {
      const clean = arr.filter(v => v !== null && v !== undefined && !Number.isNaN(v));
      return clean.length ? clean.reduce((a, b) => a + b, 0) / clean.length : null;
    }

    function cacheRate(records) {
      const withCache = records.filter(r => r.cached_tokens !== null && r.prefill_tokens > 0);
      if (!withCache.length) return null;
      return withCache.reduce((a, r) => a + (r.cached_tokens / r.prefill_tokens * 100), 0) / withCache.length;
    }

    function updateFilters() {
      const tasks = [...new Set(RECORDS.map(r => r.session_id).filter(Boolean))].sort();
      const models = [...new Set(RECORDS.map(r => r.model_mapped).filter(Boolean))].sort();
      const roles = [...new Set(RECORDS.map(r => r.role_kind).filter(Boolean))].sort();
      const mkOpts = (arr, sel) => arr.map(v => `<option value="${v}" ${v === sel ? "selected" : ""}>${v}</option>`).join("");
      document.getElementById("taskFilter").innerHTML = `<option value="">所有任务</option>` + mkOpts(tasks, state.task);
      document.getElementById("modelFilter").innerHTML = `<option value="">所有模型</option>` + mkOpts(models, state.model);
      document.getElementById("roleFilter").innerHTML = `<option value="">所有 Role</option>` + mkOpts(roles, state.role);
    }

    function renderTaskCards() {
      const grid = document.getElementById("task-grid");
      grid.innerHTML = TASKS.map(t => `
        <div class="task-card ${state.task === t.task_id ? "active" : ""}" onclick="selectTask('${t.task_id}')">
          <div class="task-id">${t.task_id}</div>
          <div class="task-main">
            <div class="task-metric"><div class="value">${t.request_count}</div><div class="label">请求数</div></div>
            <div class="task-metric"><div class="value">${fmtMs(t.total_duration_ms)}</div><div class="label">总耗时 ms</div></div>
          </div>
          <div class="task-row"><span>Prefill 范围</span><span>${fmtNum(t.min_prefill_tokens, 0)} · ${fmtNum(t.avg_prefill_tokens, 0)} · ${fmtNum(t.max_prefill_tokens, 0)}</span></div>
          <div class="task-row"><span>Output 范围</span><span>${fmtNum(t.min_output_tokens, 0)} · ${fmtNum(t.avg_output_tokens, 0)} · ${fmtNum(t.max_output_tokens, 0)}</span></div>
          <div class="task-row"><span>缓存命中</span><span>${fmtPct(t.cache_hit_rate)}</span></div>
          <div class="task-row"><span>平均 TTFT</span><span>${fmtMs(t.avg_ttft_ms)}</span></div>
          <div class="task-row"><span>平均 TPOT</span><span>${fmtNum(t.avg_tpot_ms, 2)}</span></div>
        </div>
      `).join("");
    }

    function renderKpis() {
      const records = filteredRecords();
      const perf = records.filter(r => r.has_perf);
      const approxCache = SUMMARY.approx_cache_hit_rate;
      const kpis = [
        { label: "请求数", value: records.length, sub: state.task ? "当前任务" : `${TASKS.length} 个任务` },
        { label: "含 perf 指标", value: perf.length, sub: `${records.length ? Math.round(perf.length / records.length * 100) : 0}%` },
        { label: "平均 Prefill", value: fmtNum(avg(records.map(r => r.prefill_tokens))), sub: "tokens" },
        { label: "平均 Output", value: fmtNum(avg(records.map(r => r.output_tokens))), sub: "tokens" },
        { label: "缓存命中率", value: fmtNum(cacheRate(records), 1), sub: "%" },
        { label: "估算全局缓存命中", value: approxCache !== null ? fmtNum(approxCache, 1) : "-", sub: SUMMARY.approx_cache_note || "" },
        { label: "平均 TTFT", value: fmtMs(avg(perf.map(r => r.ttft_ms))), sub: "ms" },
        { label: "平均 TPOT", value: fmtNum(avg(perf.map(r => r.tpot_ms)), 2), sub: "ms/token" },
        { label: "平均 Decode 吞吐", value: fmtNum(avg(perf.map(r => r.decode_toks_per_sec)), 1), sub: "tok/s" },
      ];
      document.getElementById("kpis").innerHTML = kpis.map(k => `
        <div class="kpi">
          <div class="kpi-label">${k.label}</div>
          <div class="kpi-value">${k.value}</div>
          <div class="kpi-sub">${k.sub}</div>
        </div>
      `).join("");
    }

    function renderModelCards() {
      const grid = document.getElementById("model-grid");
      if (!MODEL_SUMMARY.length) {
        grid.innerHTML = `<div style="color:var(--text-muted)">无模型对比数据</div>`;
        return;
      }
      grid.innerHTML = MODEL_SUMMARY.map(m => `
        <div class="model-card">
          <div class="m-name">${m.model}</div>
          <div class="m-row"><span>请求数</span><span>${m.requests}</span></div>
          <div class="m-row"><span>平均 Prefill</span><span>${fmtNum(m.avg_prefill, 0)}</span></div>
          <div class="m-row"><span>平均 Output</span><span>${fmtNum(m.avg_output, 0)}</span></div>
          <div class="m-row"><span>平均 TTFT</span><span>${fmtMs(m.avg_ttft_ms)}</span></div>
          <div class="m-row"><span>平均 TPOT</span><span>${fmtNum(m.avg_tpot_ms, 2)}</span></div>
        </div>
      `).join("");
    }

    function axisColor() { return document.body.classList.contains("light") ? "#5d6474" : "#8b92a8"; }
    function splitColor() { return document.body.classList.contains("light") ? "#e2e6f0" : "#232837"; }
    function tooltipBg() { return document.body.classList.contains("light") ? "rgba(255,255,255,.95)" : "rgba(18,21,29,.95)"; }
    function textColor() { return document.body.classList.contains("light") ? "#1f2937" : "#e6e8ef"; }

    function baseOption() {
      return {
        backgroundColor: "transparent",
        textStyle: { fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color: textColor() },
        tooltip: { backgroundColor: tooltipBg(), borderColor: splitColor(), textStyle: { color: textColor() } },
        legend: { textStyle: { color: axisColor() }, bottom: 0 },
        grid: { left: "3%", right: "4%", bottom: "12%", top: "10%", containLabel: true }
      };
    }

    function setChart(id, option, hasData) {
      const dom = document.getElementById(id);
      const nodata = document.getElementById("nodata-" + id.replace("chart-", ""));
      if (nodata) nodata.style.display = hasData ? "none" : "flex";
      if (!hasData) {
        if (chartInstances[id]) { chartInstances[id].dispose(); delete chartInstances[id]; }
        return;
      }
      if (chartInstances[id]) chartInstances[id].dispose();
      chartInstances[id] = echarts.init(dom);
      chartInstances[id].setOption(option);
    }

    function renderCharts() {
      const records = filteredRecords();
      const perf = records.filter(r => r.has_perf);
      const isLight = document.body.classList.contains("light");
      const accent = isLight ? "#4f46e5" : "#6366f1";
      const accent2 = isLight ? "#0891b2" : "#22d3ee";
      const accent3 = isLight ? "#db2777" : "#f472b6";
      const success = isLight ? "#10b981" : "#34d399";
      const task = selectedTask();

      const singleMode = !!state.task;
      document.getElementById("single-task-charts").style.display = singleMode ? "grid" : "none";
      document.getElementById("single-task-turn-charts").style.display = singleMode ? "grid" : "none";
      document.getElementById("single-task-latency").style.display = singleMode ? "grid" : "none";
      document.getElementById("all-tasks-charts").style.display = singleMode ? "none" : "grid";
      document.getElementById("view-hint").textContent = singleMode
        ? `正在单独查看任务：${state.task}`
        : "👇 点击任意任务卡片可单独查看该任务的完整指标与轮次曲线";

      if (singleMode) {
        // Single task: TTFT vs prefill
        const ttftScatter = perf.filter(r => r.prefill_tokens !== null && r.ttft_ms !== null);
        setChart("chart-ttft", {
          ...baseOption(),
          tooltip: { trigger: "item", formatter: p => `prefill: ${fmtNum(p.data[0])}<br>ttft: ${fmtMs(p.data[1])} ms` },
          xAxis: { type: "value", name: "prefill tokens", splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          yAxis: { type: "value", name: "TTFT (ms)", splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          dataZoom: [{ type: "inside" }, { type: "slider", bottom: 30, borderColor: splitColor(), textStyle: { color: axisColor() } }],
          series: [{ name: "TTFT", type: "scatter", symbolSize: 10, itemStyle: { color: accent, shadowBlur: 10, shadowColor: accent }, data: ttftScatter.map(r => [r.prefill_tokens, r.ttft_ms]) }]
        }, ttftScatter.length > 0);

        // Single task: TPOT distribution
        const tpots = perf.map(r => r.tpot_ms).filter(v => v !== null);
        let tpotOption = null, hasTpot = false;
        if (tpots.length) {
          const bins = Math.min(20, Math.max(5, Math.ceil(tpots.length / 3)));
          const min = Math.min(...tpots, 0), max = Math.max(...tpots, 1);
          const step = (max - min) / bins || 1;
          const hist = new Array(bins).fill(0);
          tpots.forEach(v => { const i = Math.min(bins - 1, Math.floor((v - min) / step)); hist[i]++; });
          const xLabels = hist.map((_, i) => (min + i * step).toFixed(2));
          tpotOption = {
            ...baseOption(),
            tooltip: { trigger: "axis", formatter: p => `${p[0].name} ms: ${p[0].value} 次` },
            xAxis: { type: "category", data: xLabels, name: "TPOT (ms/token)", axisLabel: { rotate: 30, color: axisColor() }, axisLine: { lineStyle: { color: axisColor() } } },
            yAxis: { type: "value", name: "count", splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
            series: [{ name: "TPOT", type: "bar", data: hist, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: accent3 }, { offset: 1, color: accent }]) }, barMaxWidth: 30 }]
          };
          hasTpot = true;
        }
        setChart("chart-tpot", tpotOption, hasTpot);

        // Single task: tokens over turns
        const turns = (task && task.turns) || [];
        const turnIdx = turns.map(t => t.turn_index);
        setChart("chart-tokens-turn", {
          ...baseOption(),
          tooltip: { trigger: "axis" },
          legend: { data: ["Prefill", "Cached", "Output"], textStyle: { color: axisColor() } },
          xAxis: { type: "category", data: turnIdx, name: "turn", axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          yAxis: { type: "value", name: "tokens", splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          series: [
            { name: "Prefill", type: "line", smooth: true, data: turns.map(t => t.prefill_tokens), itemStyle: { color: accent }, areaStyle: { opacity: .15 } },
            { name: "Cached", type: "line", smooth: true, data: turns.map(t => t.cached_tokens), itemStyle: { color: accent2 }, areaStyle: { opacity: .15 } },
            { name: "Output", type: "line", smooth: true, data: turns.map(t => t.output_tokens), itemStyle: { color: accent3 }, areaStyle: { opacity: .15 } }
          ]
        }, turns.length > 0);

        // Single task: cache hit rate over turns
        setChart("chart-cache-turn", {
          ...baseOption(),
          tooltip: { trigger: "axis", formatter: p => `turn ${p[0].name}<br>cache hit: ${p[0].value.toFixed(1)}%` },
          xAxis: { type: "category", data: turnIdx, name: "turn", axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          yAxis: { type: "value", name: "cache hit (%)", min: 0, max: 100, splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          series: [{ name: "Cache hit rate", type: "line", smooth: true, data: turns.map(t => t.cache_hit_rate), itemStyle: { color: success }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: success }, { offset: 1, color: "transparent" }]), opacity: .25 } }]
        }, turns.length > 0);

        // Single task: latency breakdown per turn
        const perfTurns = turns.filter(t => t.ttft_ms !== null || t.decode_ms !== null);
        setChart("chart-latency", {
          ...baseOption(),
          tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
          legend: { data: ["Prefill (TTFT)", "Decode"], textStyle: { color: axisColor() } },
          xAxis: { type: "category", data: perfTurns.map(t => t.turn_index), name: "turn", axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          yAxis: { type: "value", name: "latency (ms)", splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          series: [
            { name: "Prefill (TTFT)", type: "bar", stack: "total", data: perfTurns.map(t => t.ttft_ms || 0), itemStyle: { color: accent } },
            { name: "Decode", type: "bar", stack: "total", data: perfTurns.map(t => t.decode_ms || 0), itemStyle: { color: accent2 } }
          ]
        }, perfTurns.length > 0);
      } else {
        // All tasks comparison
        const sortedTasks = [...TASKS].sort((a, b) => b.total_duration_ms - a.total_duration_ms).slice(0, 30);
        const taskIds = sortedTasks.map(t => t.task_id.slice(0, 8));

        setChart("chart-task-duration", {
          ...baseOption(),
          tooltip: { trigger: "axis" },
          xAxis: { type: "category", data: taskIds, axisLabel: { rotate: 30, color: axisColor() }, axisLine: { lineStyle: { color: axisColor() } } },
          yAxis: { type: "value", name: "ms", splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          series: [{ name: "Total duration", type: "bar", data: sortedTasks.map(t => t.total_duration_ms), itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: accent3 }, { offset: 1, color: accent }]) }, barMaxWidth: 28 }]
        }, sortedTasks.length > 0);

        const sortedTokens = [...TASKS].sort((a, b) => b.total_output - a.total_output).slice(0, 30);
        setChart("chart-task-tokens", {
          ...baseOption(),
          tooltip: { trigger: "axis" },
          xAxis: { type: "category", data: sortedTokens.map(t => t.task_id.slice(0, 8)), axisLabel: { rotate: 30, color: axisColor() }, axisLine: { lineStyle: { color: axisColor() } } },
          yAxis: { type: "value", name: "tokens", splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
          series: [
            { name: "Prefill", type: "bar", stack: "total", data: sortedTokens.map(t => t.total_prefill), itemStyle: { color: accent } },
            { name: "Output", type: "bar", stack: "total", data: sortedTokens.map(t => t.total_output), itemStyle: { color: success } }
          ]
        }, sortedTokens.length > 0);

        const perfTasks = TASKS.filter(t => t.avg_ttft_ms !== null || t.avg_tpot_ms !== null).slice(0, 30);
        setChart("chart-task-perf", {
          ...baseOption(),
          tooltip: { trigger: "axis" },
          legend: { data: ["Avg TTFT", "Avg TPOT"], textStyle: { color: axisColor() } },
          xAxis: { type: "category", data: perfTasks.map(t => t.task_id.slice(0, 8)), axisLabel: { rotate: 30, color: axisColor() }, axisLine: { lineStyle: { color: axisColor() } } },
          yAxis: [
            { type: "value", name: "TTFT (ms)", position: "left", splitLine: { lineStyle: { color: splitColor() } }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } },
            { type: "value", name: "TPOT (ms/tok)", position: "right", splitLine: { show: false }, axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: axisColor() } }
          ],
          series: [
            { name: "Avg TTFT", type: "bar", data: perfTasks.map(t => t.avg_ttft_ms), itemStyle: { color: accent }, barMaxWidth: 20 },
            { name: "Avg TPOT", type: "line", yAxisIndex: 1, data: perfTasks.map(t => t.avg_tpot_ms), itemStyle: { color: accent3 } }
          ]
        }, perfTasks.length > 0);
      }

      renderTable(records);
    }

    function renderTable(records) {
      const tbody = document.getElementById("table-body");
      document.getElementById("table-count").textContent = records.length;
      tbody.innerHTML = records.slice(0, 500).map(r => `
        <tr>
          <td><span class="tag">${r.trace_id.slice(0, 12)}...</span></td>
          <td>${r.session_id ? r.session_id.slice(0, 8) : "-"}</td>
          <td>${r.turn_index}</td>
          <td>${r.role_kind}</td>
          <td>${r.model_mapped}</td>
          <td>${fmtNum(r.prefill_tokens, 0)}</td>
          <td>${fmtNum(r.cached_tokens, 0)}</td>
          <td>${fmtNum(r.output_tokens, 0)}</td>
          <td>${fmtMs(r.duration_ms)}</td>
          <td>${fmtMs(r.ttft_ms)}</td>
          <td>${fmtMs(r.prefill_ms)}</td>
          <td>${fmtMs(r.decode_ms)}</td>
          <td>${fmtNum(r.tpot_ms, 2)}</td>
        </tr>
      `).join("");
    }

    function selectTask(tid) {
      state.task = tid;
      document.getElementById("taskFilter").value = tid;
      renderTaskCards();
      renderKpis();
      renderCharts();
    }

    function resetFilters() {
      state.task = state.model = state.role = "";
      updateFilters();
      renderTaskCards();
      renderKpis();
      renderCharts();
    }

    function toggleTheme() {
      document.body.classList.toggle("light");
      renderCharts();
    }

    ["taskFilter", "modelFilter", "roleFilter"].forEach(id => {
      document.getElementById(id).addEventListener("change", e => {
        const key = id.replace("Filter", "");
        state[key] = e.target.value;
        renderTaskCards();
        renderKpis();
        renderCharts();
      });
    });

    const cacheInfo = SUMMARY.approx_cache_hit_rate !== null
      ? ` · 估算缓存命中: ${SUMMARY.approx_cache_hit_rate}%`
      : "";
    document.getElementById("subtitle").textContent =
      `共 ${RECORDS.length} 条请求 · ${TASKS.length} 个任务${cacheInfo} · 生成时间: ${SUMMARY.generated_at}`;

    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      document.body.classList.add('light');
    }

    updateFilters();
    renderTaskCards();
    renderKpis();
    renderModelCards();
    renderCharts();
    window.addEventListener("resize", () => {
      allChartIds.forEach(id => chartInstances[id] && chartInstances[id].resize());
    });
  </script>
</body>
</html>
"""


def _prepare_record(r: PerfRecord) -> Dict[str, Any]:
    return {
        "trace_id": r.trace_id,
        "session_id": r.session_id,
        "role_kind": r.role_kind,
        "agent_label": r.agent_label,
        "model_mapped": r.model_mapped,
        "started_ms": r.started_ms,
        "duration_ms": r.duration_ms,
        "status": r.status,
        "turn_index": r.turn_index,
        "prefill_tokens": r.prefill_tokens,
        "cached_tokens": r.cached_tokens,
        "output_tokens": r.output_tokens,
        "decode_tokens": r.decode_tokens,
        "ttft_ms": r.ttft_ms,
        "prefill_ms": r.prefill_ms,
        "prefill_toks_per_sec": r.prefill_toks_per_sec,
        "decode_ms": r.decode_ms,
        "tpot_ms": r.tpot_ms,
        "decode_toks_per_sec": r.decode_toks_per_sec,
        "has_perf": r.has_perf,
    }


def _build_task_summary(records: List[PerfRecord]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[PerfRecord]] = defaultdict(list)
    for r in records:
        groups[r.session_id or "no_session"].append(r)

    tasks = []
    for task_id, group in sorted(groups.items()):
        group.sort(key=lambda x: x.turn_index)
        perf = [r for r in group if r.has_perf]

        def avg(arr):
            clean = [v for v in arr if v is not None]
            return round(sum(clean) / len(clean), 2) if clean else None

        prefill_vals = [r.prefill_tokens for r in group if r.prefill_tokens is not None]
        output_vals = [r.output_tokens for r in group if r.output_tokens is not None]
        total_prefill = sum(prefill_vals) if prefill_vals else 0
        total_output = sum(output_vals) if output_vals else 0
        total_cached = sum((r.cached_tokens or 0) for r in group)
        cache_hit_rate = round(total_cached / total_prefill * 100, 2) if total_prefill else None

        turns = []
        for r in group:
            turn_cache = round(r.cached_tokens / r.prefill_tokens * 100, 2) if r.cached_tokens is not None and r.prefill_tokens else None
            turns.append(
                {
                    "turn_index": r.turn_index,
                    "prefill_tokens": r.prefill_tokens,
                    "cached_tokens": r.cached_tokens,
                    "output_tokens": r.output_tokens,
                    "duration_ms": r.duration_ms,
                    "ttft_ms": r.ttft_ms,
                    "prefill_ms": r.prefill_ms,
                    "decode_ms": r.decode_ms,
                    "tpot_ms": r.tpot_ms,
                    "cache_hit_rate": turn_cache,
                }
            )

        tasks.append(
            {
                "task_id": task_id,
                "request_count": len(group),
                "total_prefill": total_prefill,
                "total_output": total_output,
                "total_cached": total_cached,
                "avg_prefill_tokens": round(sum(prefill_vals) / len(prefill_vals), 2) if prefill_vals else None,
                "min_prefill_tokens": min(prefill_vals) if prefill_vals else None,
                "max_prefill_tokens": max(prefill_vals) if prefill_vals else None,
                "avg_output_tokens": round(sum(output_vals) / len(output_vals), 2) if output_vals else None,
                "min_output_tokens": min(output_vals) if output_vals else None,
                "max_output_tokens": max(output_vals) if output_vals else None,
                "total_duration_ms": sum((r.duration_ms or 0) for r in group),
                "cache_hit_rate": cache_hit_rate,
                "avg_ttft_ms": avg([r.ttft_ms for r in perf]),
                "avg_tpot_ms": avg([r.tpot_ms for r in perf]),
                "avg_prefill_toks_per_sec": avg([r.prefill_toks_per_sec for r in perf]),
                "avg_decode_toks_per_sec": avg([r.decode_toks_per_sec for r in perf]),
                "turns": turns,
            }
        )
    return tasks


def _model_summary(records: List[PerfRecord]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[PerfRecord]] = defaultdict(list)
    for r in records:
        groups[r.model_mapped].append(r)

    rows = []
    for model, g in sorted(groups.items(), key=lambda x: -len(x[1])):
        perf = [r for r in g if r.has_perf]

        def avg(arr):
            clean = [v for v in arr if v is not None]
            return round(sum(clean) / len(clean), 2) if clean else None

        rows.append(
            {
                "model": model,
                "requests": len(g),
                "avg_prefill": avg([r.prefill_tokens for r in g]),
                "avg_output": avg([r.output_tokens for r in g]),
                "avg_ttft_ms": avg([r.ttft_ms for r in perf]),
                "avg_tpot_ms": avg([r.tpot_ms for r in perf]),
            }
        )
    return rows


def main() -> int:
    # Auto-load .env from the directory containing this script's parent (project root)
    # so OPENAI_BASE_URL is available for metrics URL derivation.
    _load_dotenv(Path(__file__).parent.parent / ".env")

    parser = argparse.ArgumentParser(description="Generate interactive HTML perf dashboard")
    parser.add_argument("--db", default="cc_traces/trace.db", help="Path to trace.db")
    parser.add_argument("--output", default="perf_dashboard.html", help="Output HTML path")
    parser.add_argument(
        "--vllm-metrics-url",
        default=os.environ.get("VLLM_METRICS_URL", _derive_metrics_url(os.environ.get("OPENAI_BASE_URL"))),
        help="vLLM Prometheus metrics URL (default: derived from OPENAI_BASE_URL)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    records = _load_records(db_path)
    if not records:
        print("No successful /v1/messages requests found.")
        return 1

    cache_rate, total_prefill, computed_tokens, cache_note = _compute_approx_cache_hit_rate(
        records, args.vllm_metrics_url
    )

    summary = _summarize(records)
    summary.update(
        {
            "db_path": str(db_path.resolve()),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "model_summary": _model_summary(records),
            "approx_cache_hit_rate": cache_rate,
            "approx_cache_total_prefill": total_prefill,
            "approx_cache_computed_tokens": computed_tokens,
            "approx_cache_note": cache_note,
            "vllm_metrics_url": args.vllm_metrics_url,
        }
    )

    data_payload = {
        "records": [_prepare_record(r) for r in records],
        "tasks": _build_task_summary(records),
    }

    html = (
        TEMPLATE.replace("__DATA_JSON__", json.dumps(data_payload, ensure_ascii=False))
        .replace("__SUMMARY_JSON__", json.dumps(summary, ensure_ascii=False))
    )

    out_path = Path(args.output)
    out_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {out_path.resolve()}")
    print(f"Records: {len(records)} | Tasks: {len(data_payload['tasks'])} | With perf: {summary['with_perf_metrics']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
