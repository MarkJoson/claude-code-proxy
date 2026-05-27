#!/usr/bin/env python3
"""
最短成功路径: 用最终正确文件替换初始写入，跳过所有调试。
输出 qwen3.6-35b 标准格式的 SFT 数据集。

用法:
  1. 修改下方 OP_CONFIG 为目标算子的配置
  2. 运行: python3 optimize_shortest.py
  3. 输出: {算子名}_sft_shortest.json
"""
import json, sqlite3, copy, os

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'trace.db')

# ============================================================
# 算子配置 — 每个算子改这里
# ============================================================
OP_CONFIG = {
    # 算子名，用于输出文件命名
    "name": "1_GELU",

    # 对话链 trace_id 列表，按时间顺序排列
    "chains": [
        "msg_f5987407a81e47dd8b805b2a",
    ],

    # tools schema 来源 (任意一个有 tool_count > 0 的 trace_id)
    "tools_trace_id": "msg_2cf6747961ca463dae08ccbd",

    # 最终文件版本
    "final_files_json": os.path.join(HERE, "1_GELU_final_files.json"),

    # 要保留的 merged 消息索引 (跳过所有调试循环)
    "keep": [
        *range(0, 9),        # Phase 0-1: Init + 环境准备
        *range(9, 22),       # Phase 2: case-simplifier
        22, 23,              # Phase 3: TileLang Skill launch
        *range(23, 37),      # refs + Write files + 退化检测 PASS
        # SKIP [37-52]: TileLang 功能验证调试 (编译器 bug, 最终 SKIP)
        53,                  # "Phase 3 完成"
        54,                  # Phase 4: AscendC Skill launch
        *range(55, 83),      # refs + Write files + 退化检测 PASS
        # SKIP [83-356]: AscendC 功能验证调试 (274 msgs)
        357, 358,            # AscendC 全部 case 通过 + 退化检测 PASS
        359, 360,            # Phase 4 record
        361, 362,            # Phase 5: Performance Skill launch
        *range(363, 397),    # Performance run + 全量验证
        397, 398,            # Phase 7: trace recorder launch
        *range(399, 403),    # trace.md write + TodoUpdate
    ],

    # Write 内容替换: merged_index → final_files 中的 key
    "replace_files": {
        73:  "gelu_kernel.h",
        75:  "gelu.cpp",
        77:  "pybind11.cpp",
        79:  "model_new_ascendc.py",
    },

    # Bash 命令替换 (无，GELU 没有 cmake configure 缺失问题)
    "replace_commands": {},
}


# ============================================================
# 以下为通用处理逻辑，通常不需要修改
# ============================================================

def load_chain(trace_id):
    conn = sqlite3.connect(DB)
    rows = conn.execute('''
        SELECT msg_index, role_or_source, full_content_json
        FROM messages WHERE trace_id = ?
        ORDER BY msg_index
    ''', (trace_id,)).fetchall()
    conn.close()
    return [{'idx': r[0], 'role': r[1],
             'blocks': [b for b in (json.loads(r[2]) if r[2] else []) if isinstance(b, dict)]}
            for r in rows]

def load_tools(trace_id):
    conn = sqlite3.connect(DB)
    row = conn.execute("""
        SELECT converted_request_json
        FROM requests WHERE trace_id = ?
    """, (trace_id,)).fetchone()
    conn.close()
    return json.loads(row[0])['tools']

def convert_messages(selected):
    """将 Claude Code 格式转为 qwen3.6 格式"""
    out = []
    for msg in selected:
        role = msg['role']
        blks = msg['blocks']

        if role == 'user':
            tool_results = [b for b in blks if b.get('type') == 'tool_result']
            text_blocks = [b for b in blks if b.get('type') == 'text' and b.get('text', '').strip()]

            is_skill_launch = (
                len(tool_results) == 1 and len(text_blocks) == 1
                and 'Launching skill:' in str(tool_results[0].get('content', ''))
            )
            is_skill_text = (
                len(text_blocks) == 1
                and text_blocks[0].get('text', '').startswith('Base directory for this skill')
            )

            if is_skill_launch:
                tr = tool_results[0]
                c = tr.get('content', '')
                if isinstance(c, str):
                    c = c + '\n' + text_blocks[0].get('text', '')
                out.append({"role": "tool", "content": c, "tool_call_id": tr.get('tool_use_id', '')})
            elif is_skill_text and tool_results:
                for tr in tool_results[:-1]:
                    out.append({"role": "tool", "content": tr.get('content', ''),
                                "tool_call_id": tr.get('tool_use_id', '')})
                last = tool_results[-1]
                c = last.get('content', '')
                if isinstance(c, str):
                    c = c + '\n' + text_blocks[0].get('text', '')
                out.append({"role": "tool", "content": c, "tool_call_id": last.get('tool_use_id', '')})
            else:
                for tr in tool_results:
                    out.append({"role": "tool", "content": tr.get('content', ''),
                                "tool_call_id": tr.get('tool_use_id', '')})
                if text_blocks:
                    out.append({"role": "user", "content": '\n'.join(b.get('text', '') for b in text_blocks)})

        elif role == 'assistant':
            tool_uses = [b for b in blks if b.get('type') == 'tool_use']
            text = '\n'.join(b.get('text', '') for b in blks
                           if b.get('type') == 'text' and b.get('text', '').strip())
            m = {"role": "assistant", "content": text, "reasoning_content": ""}
            if tool_uses:
                m["tool_calls"] = [
                    {"id": tc.get('id', ''), "type": "function",
                     "function": {"name": tc.get('name', ''), "arguments": tc.get('input', {})}}
                    for tc in tool_uses
                ]
            out.append(m)

    return out

def fix_structure(out):
    """修复结构: 合并连续 assistant、插入缺失 assistant、移除孤立 tool_calls"""
    # 合并连续 assistant
    fixed = []
    fix_count = 0
    for m in out:
        if not fixed:
            fixed.append(m)
            continue
        prev_role = fixed[-1]['role']
        cur_role = m['role']
        if prev_role == 'assistant' and cur_role == 'assistant':
            prev = fixed[-1]
            prev['content'] = (prev.get('content', '') + '\n' + m.get('content', '')).strip()
            if m.get('tool_calls'):
                prev['tool_calls'] = prev.get('tool_calls', []) + m['tool_calls']
            fix_count += 1
            continue
        if prev_role == 'tool' and cur_role == 'user':
            fixed.append({"role": "assistant", "content": "", "reasoning_content": ""})
            fix_count += 1
        fixed.append(m)
    out = fixed
    print(f"Structural fixes: {fix_count}")

    # 移除孤立 tool_calls
    result_ids = set(m.get('tool_call_id', '') for m in out if m['role'] == 'tool')
    orphan = 0
    for m in out:
        if m['role'] == 'assistant' and m.get('tool_calls'):
            orig = len(m['tool_calls'])
            m['tool_calls'] = [tc for tc in m['tool_calls'] if tc['id'] in result_ids]
            orphan += orig - len(m['tool_calls'])
            if not m['tool_calls']:
                del m['tool_calls']
    if orphan:
        print(f"Orphaned tool_calls removed: {orphan}")

    # 清理空 assistant (除非用作 tool→user 分隔)
    cleaned = []
    for i, m in enumerate(out):
        if m['role'] == 'assistant' and not m.get('content', '').strip() and not m.get('tool_calls'):
            if 0 < i < len(out) - 1:
                prev_r = cleaned[-1]['role'] if cleaned else None
                next_r = out[i+1]['role']
                if prev_r == 'tool' and next_r == 'user':
                    cleaned.append(m)
                else:
                    continue
            else:
                continue
        else:
            cleaned.append(m)
    return cleaned

def validate(out):
    """验证消息流合法性"""
    valid = {('user','assistant'), ('assistant','tool'), ('tool','tool'),
             ('tool','assistant'), ('assistant','user')}
    bad = 0
    for i in range(1, len(out)):
        pair = (out[i-1]['role'], out[i]['role'])
        if pair not in valid:
            print(f"  Bad: [{i-1}]{pair[0]} -> [{i}]{pair[1]}")
            bad += 1
    if bad:
        print(f"Bad transitions: {bad}")

    call_ids = set()
    for m in out:
        if m.get('tool_calls'):
            for tc in m['tool_calls']:
                call_ids.add(tc['id'])
    res_ids = set(m.get('tool_call_id', '') for m in out if m['role'] == 'tool')
    matched = call_ids & res_ids
    print(f"tool_calls: {len(call_ids)} calls, {len(res_ids)} results, {len(matched)} matched")


def main():
    cfg = OP_CONFIG
    out_path = os.path.join(HERE, f"{cfg['name']}_sft_shortest.json")

    # 加载对话链
    chains = []
    for tid in cfg['chains']:
        chains.append(load_chain(tid))
    merged = []
    for c in chains:
        merged.extend(c)
    print(f"Original: {len(merged)} messages")

    # 加载 tools — 自动收集实际用到的工具名
    all_tools = load_tools(cfg['tools_trace_id'])
    all_tools_map = {t['function']['name']: t for t in all_tools}

    # 先扫描 keep 的消息里实际用了哪些工具
    used = set()
    for idx in cfg['keep']:
        for b in merged[idx]['blocks']:
            if b.get('type') == 'tool_use':
                used.add(b.get('name'))
            if b.get('type') == 'tool_result':
                # tool_result 需要对应的 tool_use 也在 used 里
                pass
    ref_tools = []
    for t in all_tools:
        fn = t['function']
        if fn['name'] in used and fn['name'] in all_tools_map:
            params = fn.get('parameters', {})
            if 'type' not in params:
                params['type'] = 'object'
            ref_tools.append({
                "type": "function",
                "function": {"strict": True, "name": fn['name'],
                             "description": fn.get('description', ''), "parameters": params}
            })

    # 加载最终文件版本
    finals = {}
    if os.path.exists(cfg['final_files_json']):
        with open(cfg['final_files_json']) as f:
            finals = json.load(f)

    # 选取消息 + 替换
    selected = []
    keep = cfg['keep']
    replace_files = cfg.get('replace_files', {})
    replace_commands = cfg.get('replace_commands', {})

    for idx in keep:
        msg = copy.deepcopy(merged[idx])

        if idx in replace_files:
            for b in msg['blocks']:
                if b.get('type') == 'tool_use' and b.get('name') == 'Write':
                    b['input']['content'] = finals[replace_files[idx]]

        if idx in replace_commands:
            for b in msg['blocks']:
                if b.get('type') == 'tool_use' and b.get('name') == 'Bash':
                    b['input']['command'] = replace_commands[idx]

        selected.append(msg)

    print(f"Selected: {len(selected)} messages")

    # 转换 + 修复
    out = convert_messages(selected)
    out = fix_structure(out)

    # 保存
    sft = [{"tools": ref_tools, "messages": out}]
    with open(out_path, 'w') as f:
        json.dump(sft, f, ensure_ascii=False, indent=2)

    fsize = os.path.getsize(out_path)
    role_dist = {}
    for m in out:
        role_dist[m['role']] = role_dist.get(m['role'], 0) + 1
    print(f"\nResult: {len(out)} messages")
    print(f"Roles: {role_dist}")
    print(f"File: {fsize/1024:.1f} KB")

    validate(out)


if __name__ == '__main__':
    main()
