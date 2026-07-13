#!/usr/bin/env python3
"""Export and visualize per-request and per-task LLM performance metrics from trace.db.

Usage:
    python scripts/export_perf.py --db cc_traces/trace.db --output perf.jsonl
    python scripts/export_perf.py --db cc_traces/trace.db --csv perf.csv
    python scripts/export_perf.py --db cc_traces/trace.db --plots plots/
    python scripts/export_perf.py --db cc_traces/trace.db --tasks
    python scripts/export_perf.py --db cc_traces/trace.db --tasks-csv tasks.csv

Works with both new traces that contain `extra_json.perf` and historical
traces where only `duration_ms` and `response_usage_json` are available.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


@dataclass
class PerfRecord:
    trace_id: str
    session_id: Optional[str]
    role_kind: str
    agent_label: str
    model_mapped: str
    started_ms: Optional[int]
    duration_ms: Optional[int]
    status: str
    turn_index: int
    prefill_tokens: Optional[int]
    cached_tokens: Optional[int]
    output_tokens: Optional[int]
    decode_tokens: Optional[int]
    ttft_ms: Optional[int]
    prefill_ms: Optional[int]
    prefill_toks_per_sec: Optional[float]
    decode_ms: Optional[int]
    tpot_ms: Optional[float]
    decode_toks_per_sec: Optional[float]
    has_perf: bool  # True if extra_json.perf was present


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_usage(usage_json: Optional[str]) -> Dict[str, Any]:
    if not usage_json:
        return {}
    try:
        return json.loads(usage_json)
    except json.JSONDecodeError:
        return {}


def _extract_extra(extra_json: Optional[str]) -> Dict[str, Any]:
    if not extra_json:
        return {}
    try:
        return json.loads(extra_json)
    except json.JSONDecodeError:
        return {}


def _build_record(row: sqlite3.Row, turn_index: int) -> PerfRecord:
    usage = _extract_usage(row["response_usage_json"])
    extra = _extract_extra(row["extra_json"])
    perf = extra.get("perf") if isinstance(extra, dict) else None

    # New traces: use perf block directly.
    if isinstance(perf, dict):
        return PerfRecord(
            trace_id=row["trace_id"],
            session_id=row["session_id"],
            role_kind=row["role_kind"] or "unknown",
            agent_label=row["agent_label"] or "",
            model_mapped=row["model_mapped"] or "unknown",
            started_ms=_safe_int(row["started_ms"]),
            duration_ms=_safe_int(row["duration_ms"]),
            status=row["status"],
            turn_index=turn_index,
            prefill_tokens=_safe_int(perf.get("prefill_tokens")),
            cached_tokens=_safe_int(perf.get("cached_tokens")),
            output_tokens=_safe_int(perf.get("output_tokens")),
            decode_tokens=_safe_int(perf.get("decode_tokens")),
            ttft_ms=_safe_int(perf.get("ttft_ms")),
            prefill_ms=_safe_int(perf.get("prefill_ms")),
            prefill_toks_per_sec=_safe_float(perf.get("prefill_toks_per_sec")),
            decode_ms=_safe_int(perf.get("decode_ms")),
            tpot_ms=_safe_float(perf.get("tpot_ms")),
            decode_toks_per_sec=_safe_float(perf.get("decode_toks_per_sec")),
            has_perf=True,
        )

    # Historical fallback: derive what we can from usage + duration.
    # Anthropic usage uses `input_tokens` (non-cached prompt) and
    # `cache_read_input_tokens` (cached prompt) plus `output_tokens`.
    # OpenAI/vLLM usage uses `prompt_tokens`/`completion_tokens`.
    input_tokens = (
        _safe_int(usage.get("input_tokens"))
        or _safe_int(usage.get("prompt_tokens"))
    )
    output_tokens = (
        _safe_int(usage.get("output_tokens"))
        or _safe_int(usage.get("completion_tokens"))
    )
    cached_tokens = _safe_int(usage.get("cache_read_input_tokens"))

    # For Anthropic passthrough traces, `input_tokens` is only the non-cached
    # portion; total prefill length is the sum.
    total_prefill = (input_tokens or 0) + (cached_tokens or 0)

    return PerfRecord(
        trace_id=row["trace_id"],
        session_id=row["session_id"],
        role_kind=row["role_kind"] or "unknown",
        agent_label=row["agent_label"] or "",
        model_mapped=row["model_mapped"] or "unknown",
        started_ms=_safe_int(row["started_ms"]),
        duration_ms=_safe_int(row["duration_ms"]),
        status=row["status"],
        turn_index=turn_index,
        prefill_tokens=total_prefill if total_prefill > 0 else input_tokens,
        cached_tokens=cached_tokens,
        output_tokens=output_tokens,
        decode_tokens=output_tokens,
        ttft_ms=None,
        prefill_ms=None,
        prefill_toks_per_sec=None,
        decode_ms=None,
        tpot_ms=None,
        decode_toks_per_sec=None,
        has_perf=False,
    )


def _load_records(db_path: Path) -> List[PerfRecord]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Order by session and start time so turn_index is meaningful.
    rows = conn.execute(
        """
        SELECT
            trace_id,
            session_id,
            role_kind,
            agent_label,
            model_mapped,
            started_ms,
            duration_ms,
            status,
            response_usage_json,
            extra_json
        FROM requests
        WHERE api = 'messages'
          AND status = 'success'
        ORDER BY COALESCE(session_id, trace_id), started_ms
        """
    ).fetchall()

    records: List[PerfRecord] = []
    current_session: Optional[str] = None
    turn_index = 0
    for row in rows:
        sid = row["session_id"]
        if sid != current_session:
            current_session = sid
            turn_index = 0
        records.append(_build_record(row, turn_index))
        turn_index += 1

    return records


def _records_to_jsonl(records: Iterable[PerfRecord]) -> Iterable[str]:
    for r in records:
        yield json.dumps(asdict(r), ensure_ascii=False)


def _write_jsonl(records: List[PerfRecord], path: Path) -> None:
    path.write_text("\n".join(_records_to_jsonl(records)) + "\n", encoding="utf-8")


def _write_csv(records: List[PerfRecord], path: Path) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(asdict(records[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))


def _summarize(records: List[PerfRecord]) -> Dict[str, Any]:
    total = len(records)
    with_perf = [r for r in records if r.has_perf]
    fallback = [r for r in records if not r.has_perf]

    def _avg(vals: Sequence[Optional[float]]) -> Optional[float]:
        clean = [v for v in vals if v is not None]
        return round(sum(clean) / len(clean), 2) if clean else None

    summary: Dict[str, Any] = {
        "total_requests": total,
        "with_perf_metrics": len(with_perf),
        "fallback_only": len(fallback),
        "sessions": len({r.session_id for r in records if r.session_id}),
        "avg_prefill_tokens": _avg([r.prefill_tokens for r in records]),
        "avg_output_tokens": _avg([r.output_tokens for r in records]),
        "avg_cached_tokens": _avg([r.cached_tokens for r in records]),
        "avg_cache_hit_rate": _avg(
            [
                (r.cached_tokens / r.prefill_tokens) * 100
                for r in records
                if r.cached_tokens is not None
                and r.prefill_tokens
                and r.prefill_tokens > 0
            ]
        ),
        "avg_duration_ms": _avg([r.duration_ms for r in records]),
    }

    if with_perf:
        summary.update(
            {
                "avg_ttft_ms": _avg([r.ttft_ms for r in with_perf]),
                "avg_prefill_ms": _avg([r.prefill_ms for r in with_perf]),
                "avg_prefill_toks_per_sec": _avg(
                    [r.prefill_toks_per_sec for r in with_perf]
                ),
                "avg_decode_ms": _avg([r.decode_ms for r in with_perf]),
                "avg_tpot_ms": _avg([r.tpot_ms for r in with_perf]),
                "avg_decode_toks_per_sec": _avg(
                    [r.decode_toks_per_sec for r in with_perf]
                ),
            }
        )

    return summary


def _task_summary(records: List[PerfRecord]) -> List[Dict[str, Any]]:
    """Return one aggregated row per session/task with min/max/avg stats."""
    sessions = _group_by_session(records)
    rows: List[Dict[str, Any]] = []

    for task_id, group in sorted(sessions.items()):
        perf = [r for r in group if r.has_perf]

        def _avg(vals: Sequence[Optional[float]]) -> Optional[float]:
            clean = [v for v in vals if v is not None]
            return round(sum(clean) / len(clean), 2) if clean else None

        prefill_vals = [r.prefill_tokens for r in group if r.prefill_tokens is not None]
        output_vals = [r.output_tokens for r in group if r.output_tokens is not None]
        total_prefill = sum(prefill_vals) if prefill_vals else 0
        total_cached = sum((r.cached_tokens or 0) for r in group)

        rows.append(
            {
                "task_id": task_id,
                "request_count": len(group),
                "total_prefill_tokens": total_prefill,
                "total_output_tokens": sum(output_vals) if output_vals else 0,
                "total_cached_tokens": total_cached,
                "avg_prefill_tokens": _avg(prefill_vals),
                "min_prefill_tokens": min(prefill_vals) if prefill_vals else None,
                "max_prefill_tokens": max(prefill_vals) if prefill_vals else None,
                "avg_output_tokens": _avg(output_vals),
                "min_output_tokens": min(output_vals) if output_vals else None,
                "max_output_tokens": max(output_vals) if output_vals else None,
                "cache_hit_rate": round(total_cached / total_prefill * 100, 2) if total_prefill else None,
                "total_duration_ms": sum((r.duration_ms or 0) for r in group),
                "avg_duration_ms": _avg([r.duration_ms for r in group]),
                "avg_ttft_ms": _avg([r.ttft_ms for r in perf]),
                "avg_tpot_ms": _avg([r.tpot_ms for r in perf]),
                "avg_decode_toks_per_sec": _avg([r.decode_toks_per_sec for r in perf]),
            }
        )
    return rows


def _write_task_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _group_by_session(records: List[PerfRecord]) -> Dict[str, List[PerfRecord]]:
    groups: Dict[str, List[PerfRecord]] = {}
    for r in records:
        key = r.session_id or "no_session"
        groups.setdefault(key, []).append(r)
    # sort each group by turn_index
    for key in groups:
        groups[key].sort(key=lambda x: x.turn_index)
    return groups


def _plot_optional(records: List[PerfRecord], plot_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        print(
            f"matplotlib not installed ({exc}); skipping plots. "
            "Install with: pip install matplotlib"
        )
        return

    plot_dir.mkdir(parents=True, exist_ok=True)
    perf_records = [r for r in records if r.has_perf]

    # 1. TTFT vs prefill tokens
    if perf_records:
        fig, ax = plt.subplots(figsize=(8, 5))
        x = [r.prefill_tokens for r in perf_records if r.prefill_tokens is not None and r.ttft_ms is not None]
        y = [r.ttft_ms for r in perf_records if r.prefill_tokens is not None and r.ttft_ms is not None]
        ax.scatter(x, y, alpha=0.6)
        ax.set_xlabel("Prefill tokens")
        ax.set_ylabel("TTFT (ms)")
        ax.set_title("TTFT vs Prefill Length")
        fig.tight_layout()
        fig.savefig(plot_dir / "ttft_vs_prefill.png")
        plt.close(fig)

    # 2. TPOT distribution
    if perf_records:
        tpots = [r.tpot_ms for r in perf_records if r.tpot_ms is not None]
        if tpots:
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.hist(tpots, bins=30, edgecolor="black")
            ax.set_xlabel("TPOT (ms/token)")
            ax.set_ylabel("Count")
            ax.set_title("TPOT Distribution")
            fig.tight_layout()
            fig.savefig(plot_dir / "tpot_distribution.png")
            plt.close(fig)

    # 3. Tokens over turns per session (aggregate: median across sessions)
    sessions = _group_by_session(records)
    if sessions:
        max_turns = max(len(v) for v in sessions.values())
        turn_prefill: List[List[int]] = [[] for _ in range(max_turns)]
        turn_output: List[List[int]] = [[] for _ in range(max_turns)]
        turn_cache_rate: List[List[float]] = [[] for _ in range(max_turns)]

        for group in sessions.values():
            for r in group:
                if r.prefill_tokens is not None:
                    turn_prefill[r.turn_index].append(r.prefill_tokens)
                if r.output_tokens is not None:
                    turn_output[r.turn_index].append(r.output_tokens)
                if r.cached_tokens is not None and r.prefill_tokens:
                    rate = r.cached_tokens / r.prefill_tokens * 100
                    turn_cache_rate[r.turn_index].append(rate)

        turns = list(range(max_turns))
        import statistics

        med_prefill = [statistics.median(v) if v else 0 for v in turn_prefill]
        med_output = [statistics.median(v) if v else 0 for v in turn_output]
        med_cache = [statistics.median(v) if v else 0 for v in turn_cache_rate]

        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(turns, med_prefill, label="Prefill tokens", marker="o")
        ax1.plot(turns, med_output, label="Output tokens", marker="s")
        ax1.set_xlabel("Turn index")
        ax1.set_ylabel("Tokens")
        ax1.legend(loc="upper left")

        ax2 = ax1.twinx()
        ax2.plot(turns, med_cache, color="green", label="Cache hit rate (%)", marker="^")
        ax2.set_ylabel("Cache hit rate (%)")
        ax2.legend(loc="upper right")

        ax1.set_title("Tokens and Cache Hit Rate Over Turns")
        fig.tight_layout()
        fig.savefig(plot_dir / "tokens_over_turns.png")
        plt.close(fig)

    # 4. Total duration per session (works with or without perf metrics)
    sessions = _group_by_session(records)
    session_total = {
        sid: sum((r.duration_ms or 0) for r in group)
        for sid, group in sessions.items()
    }
    top_sessions = sorted(session_total.items(), key=lambda x: x[1], reverse=True)[:20]

    if top_sessions:
        fig, ax = plt.subplots(figsize=(12, 6))
        labels = [sid[:8] for sid, _ in top_sessions]
        vals = [total for _, total in top_sessions]
        ax.bar(labels, vals)
        ax.set_xlabel("Session")
        ax.set_ylabel("Total duration (ms)")
        ax.set_title("Total Duration per Session (Top 20)")
        fig.tight_layout()
        fig.savefig(plot_dir / "total_duration_per_session.png")
        plt.close(fig)

    # 5. Latency breakdown per session (requires perf metrics)
    if top_sessions and perf_records:
        fig, ax = plt.subplots(figsize=(12, 6))
        labels: List[str] = []
        ttft_vals: List[float] = []
        decode_vals: List[float] = []
        for sid, _ in top_sessions:
            group = sessions[sid]
            labels.append(sid[:8])
            ttft_vals.append(sum((r.ttft_ms or 0) for r in group))
            decode_vals.append(sum((r.decode_ms or 0) for r in group))

        ax.bar(labels, ttft_vals, label="Prefill (TTFT)")
        ax.bar(labels, decode_vals, bottom=ttft_vals, label="Decode")
        ax.set_xlabel("Session")
        ax.set_ylabel("Total latency (ms)")
        ax.set_title("Latency Breakdown per Session (Top 20)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(plot_dir / "latency_breakdown_per_session.png")
        plt.close(fig)

    print(f"Plots saved to {plot_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export and visualize perf metrics")
    parser.add_argument("--db", default="cc_traces/trace.db", help="Path to trace.db")
    parser.add_argument("--output", help="Output per-request JSONL path")
    parser.add_argument("--csv", help="Output per-request CSV path")
    parser.add_argument("--plots", help="Directory to save plots")
    parser.add_argument("--summary", action="store_true", help="Print summary to stdout")
    parser.add_argument("--tasks", action="store_true", help="Print task-level summary JSON to stdout")
    parser.add_argument("--tasks-csv", help="Output task-level summary CSV path")
    parser.add_argument("--tasks-output", help="Output task-level summary JSONL path")
    args = parser.parse_args()

    db_path = Path(args.db)
    records = _load_records(db_path)
    if not records:
        print("No successful /v1/messages requests found.")
        return 1

    if args.output:
        _write_jsonl(records, Path(args.output))
        print(f"Wrote {len(records)} records to {args.output}")

    if args.csv:
        _write_csv(records, Path(args.csv))
        print(f"Wrote {len(records)} records to {args.csv}")

    if args.plots:
        _plot_optional(records, Path(args.plots))

    task_rows = _task_summary(records)
    if args.tasks_output:
        Path(args.tasks_output).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in task_rows) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {len(task_rows)} tasks to {args.tasks_output}")

    if args.tasks_csv:
        _write_task_csv(task_rows, Path(args.tasks_csv))
        print(f"Wrote {len(task_rows)} tasks to {args.tasks_csv}")

    if args.tasks:
        print(json.dumps(task_rows, indent=2, ensure_ascii=False))

    if args.summary or not (args.output or args.csv or args.plots or args.tasks_output or args.tasks_csv or args.tasks):
        summary = _summarize(records)
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
