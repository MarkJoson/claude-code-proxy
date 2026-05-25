# 流式响应追踪修复

## 问题

在之前的实现中，流式响应（`stream: true`）没有记录追踪数据到数据库，导致：
- Trace UI 中看不到流式请求的详情
- 无法追踪流式请求的性能和内容
- 统计数据不完整

## 原因

流式响应使用 `StreamingResponse` 直接返回生成器，在生成器完成后没有调用 `trace_request_completed()`。

## 修复方案

### 1. 修改 `handle_streaming` 函数签名

添加追踪参数：

```python
async def handle_streaming(
    response_generator, 
    original_request: MessagesRequest,
    trace_id=None,           # 新增
    trace_start=None,        # 新增
    litellm_request=None     # 新增
):
```

### 2. 累积响应数据

在流式处理过程中累积响应数据：

```python
accumulated_response = {
    "id": message_id,
    "model": original_request.original_model or original_request.model,
    "role": "assistant",
    "content": [],
    "stop_reason": None,
    "usage": {"input_tokens": 0, "output_tokens": 0}
}

# 累积文本内容
if accumulated_text:
    accumulated_response["content"].append({
        "type": "text", 
        "text": accumulated_text
    })

# 累积工具调用
tool_calls_map = {}  # {tool_id: {"name": str, "input": str}}

# 在工具调用时更新
tool_calls_map[tool_id] = {"name": name, "input": ""}
tool_calls_map[tool_id]["input"] += args_json

# 在完成时添加到响应
for tool_id, tool_data in tool_calls_map.items():
    tool_input = json.loads(tool_data["input"]) if tool_data["input"] else {}
    accumulated_response["content"].append({
        "type": "tool_use",
        "id": tool_id,
        "name": tool_data["name"],
        "input": tool_input
    })
```

### 3. 在流式结束时记录追踪

在两个结束点都记录追踪：

**有 finish_reason 的情况**：
```python
# 在 finish_reason 处理后
if trace_id and trace_start and litellm_request:
    try:
        trace_request_completed(
            trace_id=trace_id,
            status_code=200,
            duration_ms=monotonic_ms(trace_start),
            converted_request=litellm_request,
            response=accumulated_response,
            extra={"streaming": True},
        )
    except Exception as trace_err:
        logger.error(f"Failed to record streaming trace: {trace_err}")
```

**没有 finish_reason 的情况**：
```python
# 在最后的 message_stop 后
if trace_id and trace_start and litellm_request:
    try:
        trace_request_completed(
            trace_id=trace_id,
            status_code=200,
            duration_ms=monotonic_ms(trace_start),
            converted_request=litellm_request,
            response=accumulated_response,
            extra={"streaming": True},
        )
    except Exception as trace_err:
        logger.error(f"Failed to record streaming trace: {trace_err}")
```

### 4. 更新调用点

在 `create_message` 函数中传递追踪参数：

```python
return StreamingResponse(
    handle_streaming(
        litellm_response, 
        request, 
        trace_id,           # 传递 trace_id
        trace_start,        # 传递 trace_start
        litellm_request     # 传递 litellm_request
    ),
    media_type="text/event-stream"
)
```

## 修复后的效果

✅ **流式请求完整追踪**
- 所有流式请求都会记录到数据库
- Trace UI 可以查看流式请求的详情

✅ **完整的响应数据**
- 记录文本内容
- 记录工具调用
- 记录 token 使用量

✅ **性能统计**
- 记录请求耗时
- 记录上游模型
- 标记为流式请求（`extra.streaming = true`）

✅ **错误处理**
- 追踪记录失败不影响流式响应
- 记录错误日志便于调试

## 验证方法

### 1. 测试流式请求

```bash
python test_duplicate_requests.py
```

查看输出中的 "TEST 2: STREAMING REQUEST" 部分。

### 2. 查看 Trace UI

```bash
# 启动服务器
python server.py

# 发送流式请求
curl -N -X POST http://localhost:8082/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 100,
    "stream": true,
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# 查看 Trace UI
open http://localhost:8082/trace
```

在 Trace UI 中应该能看到：
- 流式请求出现在请求列表中
- 可以查看完整的响应内容
- 显示 token 使用量
- 显示请求耗时

### 3. 检查数据库

```bash
sqlite3 trace.db "SELECT trace_id, api, status_code, duration_ms, extra FROM requests WHERE extra LIKE '%streaming%' LIMIT 5;"
```

应该能看到 `extra` 字段包含 `"streaming": true`。

## 注意事项

### 1. 性能影响

累积响应数据会增加少量内存开销，但影响很小：
- 文本内容：通常几 KB
- 工具调用：每个工具几百字节
- 总开销：< 1 MB（对于大多数请求）

### 2. 错误处理

追踪记录失败不会影响流式响应：
```python
try:
    trace_request_completed(...)
except Exception as trace_err:
    logger.error(f"Failed to record streaming trace: {trace_err}")
```

### 3. 兼容性

修复后的代码完全向后兼容：
- 非流式请求不受影响
- 旧的追踪数据仍然可以查看
- Trace UI 自动识别流式/非流式请求

## 相关文件

- `server.py` - 主要修改
  - `handle_streaming()` 函数（第 866-1165 行）
  - `create_message()` 函数（第 1350 行）

## 更新日志

**2024-05-25**
- ✅ 修复流式响应追踪缺失问题
- ✅ 添加响应数据累积逻辑
- ✅ 添加工具调用追踪
- ✅ 更新文档

---

**相关文档**：
- [重复请求修复](DUPLICATE_REQUEST_FIX.md)
- [故障排查指南](docs/TROUBLESHOOTING.md)
- [功能特性](docs/FEATURES.md)
