# AscendC 算子生成 SFT 数据集构建流水线

## 概述

本文档描述从 Claude Code API traces (`trace.db`) 中提取算子生成的**最短成功路径**，输出为 qwen3.6-35b 标准格式 SFT 训练数据集的通用方法。

**核心思路**: 原始 trace 包含大量失败的调试探索。通过跳过所有错误修复循环，并将初始文件写入替换为最终正确版本，得到一条"一次性成功"的理想路径。

---

## 1. 目录组织

所有文件在同一目录下。放入 `trace.db`，修改脚本顶部的 `OP_CONFIG`，运行即可生成数据集。

```
cc_traces/
  PIPELINE_DOC.md                        # 本文档 (通用流水线说明)
  trace.db                               # 原始 API traces (用户提供)
  optimize_shortest.py                   # 最短路径提取脚本
  optimize_final.py                      # 标准版提取脚本
  qwen3.6-35b-...json                    # 格式参考
  3_Add_sft_shortest.json                # 输出: 3_Add 最短路径数据集
  3_Add_sft_standard.json                # 输出: 3_Add 标准数据集
  final_all_files.json                   # 3_Add 最终文件版本
  final_files.json                       # 3_Add AscendC 最终文件
  tools_schema.json                      # 工具 schema
```

新增算子时，只需修改脚本的 `OP_CONFIG` 配置区，输出自动以 `{算子名}_sft_shortest.json` 命名。

---

## 2. 数据源: trace.db

### 2.1 关键表结构

```sql
-- 消息表: 存储每轮对话内容
messages (
    trace_id TEXT,            -- API 请求标识
    msg_index INTEGER,       -- 消息在对话中的顺序 (0-based)
    role_or_source TEXT,      -- 'user' | 'assistant' | 'system'
    content_kind TEXT,        -- 'text' | 'blocks'
    full_content_json TEXT,   -- JSON 数组，每个元素是一个 content block (dict)
    PRIMARY KEY (trace_id, msg_index)
)

-- 请求表: 存储工具定义等信息
requests (
    trace_id TEXT PRIMARY KEY,
    session_id TEXT,
    converted_request_json TEXT,  -- 包含 tools 定义
    parent_trace_id TEXT,         -- 父请求 (用于识别子 agent)
    ...
)

-- 工具事件表: tool_use / tool_result 详情
tool_events (event_id, trace_id, tool_name, tool_use_id, raw_block_json, ...)

-- Agent 调用表: 子 agent 的生命周期
agent_calls (agent_call_id, parent_trace_id, tool_use_id, result_trace_id, ...)
```

### 2.2 识别对话链

用户会告知需要提取的 session_id，每个 session_id 对应一个算子的完整链路。一个 session 下通常有一个最长的主对话 trace_id，可能还有续接对话。

```sql
-- 用 session_id 找到该算子的所有请求
SELECT trace_id, message_count, parent_trace_id, started_ms
FROM requests
WHERE session_id = '<session_id>'
ORDER BY started_ms;

-- 找到消息最多的 trace_id (主对话)
SELECT trace_id, COUNT(*) as cnt
FROM messages
GROUP BY trace_id
ORDER BY cnt DESC;
```

将识别出的 trace_id 填入脚本 `OP_CONFIG.chains` 中，按时间顺序排列。合并后索引连续: chain1 [0..N-1], chain2 [N..N+M-1]。

### 2.3 Tools Schema 来源

从 `requests` 表获取:

```sql
SELECT converted_request_json FROM requests
WHERE tool_count > 0
LIMIT 1;
```

提取后只保留训练中需要的工具，常见: `Bash, Read, Write, Edit, Skill, TaskCreate, TaskUpdate, TaskOutput`

---

## 3. 最短路径分析

### 3.1 分析流程

1. **合并对话链** → 按顺序得到所有消息
2. **标记阶段边界** — 识别 Skill 启动、Write 文件、Bash 构建/验证等关键节点
3. **识别错误循环** — 标记 `is_error=True` 的 tool_result 及其后续的修复过程
4. **确定跳过区间** — 错误发生到修复完成之间的所有消息
5. **识别文件最终版本** — 通过 Edit 操作重放或从 system-reminder 提取

### 3.2 通用跳过策略

| 跳过类型 | 识别方法 | 说明 |
|---|---|---|
| 初始验证失败 → 修复 | `tool_result.is_error=True` 后续到修复完成 | 替换文件后不再需要 |
| 功能测试调试循环 | 连续多轮 Bash 报错 + Edit/Write 修复 | 用最终文件替换后跳过 |
| cmake/build 调试 | cmake 报错 + CMakeLists.txt 修改循环 | 用最终 CMakeLists 替换后跳过 |
| 重复验证 | 同一验证脚本多次运行 | 只保留最终通过的那次 |

### 3.3 文件内容替换

**核心原理**: 如果 Write 的内容被替换为最终正确版本，那么后续所有针对该文件的调试 (Edit + 验证) 都可以跳过。

```python
replace_map = {
    msg_idx: final_content,  # 将该索引处 Write 的 content 替换为最终版本
    ...
}
```

### 3.4 命令修补

跳过调试区间后，某些 Bash 命令会缺少前置依赖。典型情况:

- **cmake build 命令**: 如果跳过了 cmake configure 阶段，build 命令前需要加 configure
- **验证脚本路径**: 跳过文件生成步骤后，验证脚本的路径参数可能需要调整

```python
# 如果跳过了 configure 阶段，build 命令需要合并 configure + build
new_cmd = 'rm -rf build && mkdir -p build && cmake -S . -B build && cmake --build build -j'
```

---

## 4. 最终文件版本获取

### 4.1 方法一: Edit 重放

适用于被多次 Edit 修改的文件:

```python
# 1. 从 DB 读取初始 Write 的 content
initial = load_write_content(msg_idx)

# 2. 按顺序找到所有对该文件的 Edit 操作
edits = find_edits_for_file(file_path)  # 按时间排序

# 3. 依次应用每次 Edit
content = initial
for edit in edits:
    content = content.replace(edit['old_string'], edit['new_string'])

# 最终 content 即为最终版本
```

### 4.2 方法二: 从 system-reminder 提取

续接对话的 system context 中可能包含之前写入的文件内容。提取时注意:

- **必须剥离 `</system-reminder>` 等闭合标签**，否则文件内容会带尾巴
- 检查提取内容是否完整 (与原始文件对比行数/字符数)

### 4.3 方法三: 从 tool_result 提取

某些文件在验证步骤中被 Read 工具读取，Read 的 tool_result 包含文件完整内容。

### 4.4 存储格式

最终文件版本存储为 `final_all_files.json`:

```json
{
  "<相对路径/文件名>": "<完整文件内容字符串>",
  ...
}
```

---

## 5. qwen3.6 SFT 格式转换

### 5.1 目标格式

```json
[{
  "tools": [
    {"type": "function", "function": {"strict": true, "name": "...", "description": "...", "parameters": {...}}}
  ],
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "reasoning_content": "",
     "tool_calls": [{"id": "call_xxx", "type": "function", "function": {"name": "Write", "arguments": {...}}}]},
    {"role": "tool", "content": "...", "tool_call_id": "call_xxx"},
    ...
  ]
}]
```

### 5.2 合法消息流转

```
user → assistant → tool → assistant → tool → ... → assistant → user
```

合法的相邻角色对:
- `user → assistant`
- `assistant → tool`
- `tool → tool` (同一轮多个 tool_result)
- `tool → assistant`
- `assistant → user`

**不合法** (需修复):
- `assistant → assistant` → 合并为一条
- `tool → user` → 插入空 assistant
- `user → tool` → 插入带 tool_calls 的 assistant

### 5.3 转换规则

Claude Code trace 中 `role=user` 的消息可能混合多种 block 类型，需要拆分:

| 原始 block 类型 | 所在 role | 转换为 |
|---|---|---|
| `type=text` | user 消息 | `role=user, content=text` |
| `type=tool_result` | user 消息 | `role=tool, content=..., tool_call_id=tool_use_id` |
| `type=tool_use` | assistant 消息 | `tool_calls=[{id, function: {name, arguments}}]` |
| `type=text` | assistant 消息 | `content=text` |

### 5.4 Skill 启动特殊处理

Skill 启动消息的 user 消息包含:
- `tool_result("Launching skill: ...")`
- `text("Base directory for this skill: ...")`

分开转换会产生非法的 `tool → user` 转换。**解决**: 将 text 合并到最后一个 tool_result:

```python
if is_skill_launch:
    merged = tool_result_content + '\n' + base_directory_text
    out.append({"role": "tool", "content": merged, "tool_call_id": ...})
```

---

## 6. 结构验证与修复

转换后必须执行以下修复，确保格式合规:

### 6.1 合并连续 assistant 消息

```
[assistant] [assistant]  →  [assistant] (合并 content + tool_calls)
```

### 6.2 插入缺失的 assistant 消息

```
[tool] [user]  →  [tool] [assistant(content="", reasoning_content="")] [user]
```

### 6.3 移除孤立 tool_calls

tool_call 的 id 在整个消息流中没有对应 tool result → 移除该 tool_call:

```python
result_ids = {m['tool_call_id'] for m in out if m['role'] == 'tool'}
for m in out:
    if m['role'] == 'assistant' and m.get('tool_calls'):
        m['tool_calls'] = [tc for tc in m['tool_calls'] if tc['id'] in result_ids]
```

### 6.4 清理空 assistant 消息

`content=""` 且无 `tool_calls` 的 assistant 消息，除非用于分隔 `tool → user` (去掉会导致非法转换)，否则移除。

### 6.5 验证 tool_call 配对

```python
call_ids = {tc['id'] for m in out if m['role']=='assistant' for tc in m.get('tool_calls', [])}
res_ids = {m['tool_call_id'] for m in out if m['role']=='tool'}
assert call_ids == res_ids, f"Mismatch: {call_ids ^ res_ids}"
```

---

## 7. 已知陷阱

### 7.1 `</system-reminder>` 污染

**问题**: 从 system-reminder 文本块提取文件内容时，如果不剥离闭合标签，文件会带上 `</system-reminder>` 尾巴。

**解决**: 提取后检查并剥离尾部标签。受影响的是所有从 system context 提取的文件内容。

### 7.2 cmake configure 缺失

**问题**: 跳过 cmake 调试区间后，如果只保留了 `cmake --build`，缺少 `cmake -S . -B build` configure 步骤。

**解决**: 将 build 命令替换为 `configure + build` 的合并命令。

### 7.3 Bash 生成的非 Write 文件

**问题**: 部分文件 (如测试用例 JSON) 通过 Bash 命令生成而非 Write tool_call。从 SFT 数据集还原算子时无法自动恢复。

**解决**: 需额外记录这些文件，或在数据集中保留对应的 Bash 命令并在还原时解析执行。

### 7.4 tool_result 中 content 类型

`tool_result` 的 `content` 字段可能是 string 或 list (包含 text + image blocks)。转换时需统一处理:

```python
content = tr.get('content', '')
if isinstance(content, list):
    content = '\n'.join(
        b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text'
    )
```

---

## 8. 还原验证方法

从 sft_shortest.json 还原算子代码并验证数据集正确性:

### 8.1 提取文件

```python
for msg in messages:
    if msg['role'] == 'assistant' and msg.get('tool_calls'):
        for tc in msg['tool_calls']:
            if tc['function']['name'] == 'Write':
                path = tc['function']['arguments']['file_path']
                content = tc['function']['arguments']['content']
                # 写入文件
```

### 8.2 构建验证

```bash
cd <kernel_dir>
rm -rf build && mkdir -p build
ASCEND_CANN_PACKAGE_PATH=/usr/local/Ascend/cann-9.0.0 \
SOC_VERSION=Ascend910B2 cmake -S . -B build
cmake --build build -j
```

### 8.3 功能验证

运行算子验证脚本 (需测试用例文件)。

**关键**: 如果还原的算子能通过验证，则说明数据集中的文件内容是正确的。这是数据集质量的最终检验。

---

## 9. 脚本配置说明

脚本顶部有一个 `OP_CONFIG` 字典，每个算子只需修改这里:

```python
OP_CONFIG = {
    # 算子名，用于输出文件命名 → {name}_sft_shortest.json
    "name": "3_Add",

    # 对话链 trace_id，按时间顺序 (用户提供 session_id 后从 DB 查出)
    "chains": [
        "msg_825079f05cb14f0e91dd9570",   # 主对话
        "msg_d1f709486d8447f98b05745e",   # 续接对话 (如有)
    ],

    # tools schema 来源 (任意一个 tool_count > 0 的 trace_id)
    "tools_trace_id": "msg_58fa18fd55b14a18a6e1569d",

    # 最终文件版本 JSON (需提前准备好)
    "final_files_json": "final_all_files.json",

    # 最短路径: 要保留的消息索引列表
    "keep": [...],

    # 最短路径: Write 内容替换 {index: final_files_json 中的 key}
    "replace_files": {...},

    # 最短路径: Bash 命令替换 {index: 新命令}
    "replace_commands": {...},
}
```

新增算子流程:
1. 用户告知 session_id
2. AI 从 DB 中查出 trace_ids，分析消息流
3. 识别错误循环，确定 skip 范围或 keep 列表
4. 获取最终文件版本
5. 修改 `OP_CONFIG` 并运行脚本
6. 输出 `{算子名}_sft_shortest.json`
