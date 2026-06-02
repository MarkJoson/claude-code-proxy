# 重复请求问题修复

## 问题分析

你提到的问题很可能是：**Claude Code 发送流式请求，但服务器强制返回非流式响应，导致客户端认为失败并重试**。

### 原始问题

1. **客户端行为**：Claude Code 默认使用流式请求（`stream: true`）
2. **服务器行为**：代码中强制设置 `stream: False`（第614行）
3. **响应不匹配**：
   - 客户端期望：SSE 流式响应（`text/event-stream`）
   - 服务器返回：普通 JSON 响应
4. **结果**：客户端认为第一次请求失败，发起第二次请求（可能是非流式）

### 互联网资料的说法

你提到的"一次流式一次非流式"正是这个问题的表现：
- **第一次**：客户端请求流式（`stream: true`），但得到错误的响应格式
- **第二次**：客户端重试，可能改用非流式（`stream: false`）

## 修复方案

### 1. 尊重客户端的 stream 参数

**修改位置**：`server.py` 第614行

```python
# 修改前
litellm_request = {
    "stream": False,  # 强制非流式
}

# 修改后
litellm_request = {
    "stream": anthropic_request.stream,  # 尊重客户端选择
}
```

### 2. 根据 stream 参数返回正确的响应格式

**修改位置**：`server.py` 第1288-1370行

```python
# 流式请求：返回 StreamingResponse
if request.stream:
    litellm_response = await litellm.acompletion(**litellm_request)
    return StreamingResponse(
        handle_streaming(litellm_response, request),
        media_type="text/event-stream"
    )

# 非流式请求：返回 JSON
else:
    litellm_response = await litellm.acompletion(**litellm_request)
    anthropic_response = convert_litellm_to_anthropic(litellm_response, request)
    return anthropic_response
```

### 3. 添加调试日志

为了验证修复效果，添加了以下日志：

- 🔴 **MIDDLEWARE**：记录每个进入的 HTTP 请求
- 🔵 **ENDPOINT ENTRY**：记录每次进入 `/v1/messages` 端点
- 🟡 **STREAMING/NON-STREAMING MODE**：记录使用的模式
- 🟢 **UPSTREAM CALL START/SUCCESS**：记录实际的上游 API 调用

## 验证方法

### 运行测试脚本

```bash
python test_duplicate_requests.py
```

### 预期结果

**正常情况**（每个测试只应该看到一次）：
```
🔴 MIDDLEWARE: Incoming request to POST /v1/messages
🔵 ENDPOINT ENTRY: /v1/messages - trace_id=msg_xxx
🟡 STREAMING MODE: trace_id=msg_xxx
🟢 UPSTREAM STREAMING CALL START: trace_id=msg_xxx, attempt=1/4
🟢 UPSTREAM STREAMING CALL SUCCESS: trace_id=msg_xxx, attempt=1
🔴 MIDDLEWARE: Response from POST /v1/messages, status=200
```

**异常情况**（如果看到两次，说明有重复请求）：
```
🔴 MIDDLEWARE: Incoming request to POST /v1/messages  ← 第1次
🔵 ENDPOINT ENTRY: /v1/messages - trace_id=msg_xxx
🟡 STREAMING MODE: trace_id=msg_xxx
🟢 UPSTREAM STREAMING CALL START: trace_id=msg_xxx
🟢 UPSTREAM STREAMING CALL SUCCESS: trace_id=msg_xxx
🔴 MIDDLEWARE: Response from POST /v1/messages, status=200

🔴 MIDDLEWARE: Incoming request to POST /v1/messages  ← 第2次（重复！）
🔵 ENDPOINT ENTRY: /v1/messages - trace_id=msg_yyy
🟡 NON-STREAMING MODE: trace_id=msg_yyy
🟢 UPSTREAM CALL START: trace_id=msg_yyy
🟢 UPSTREAM CALL SUCCESS: trace_id=msg_yyy
🔴 MIDDLEWARE: Response from POST /v1/messages, status=200
```

## 其他可能的原因

如果修复后仍然有重复请求，可能是：

1. **Claude Code 客户端的重试逻辑**：客户端可能有内置的重试机制
2. **网络层问题**：反向代理、负载均衡器的重试配置
3. **超时设置**：如果响应太慢，客户端可能超时重试
4. **多 worker 竞争**：当前配置了 16 个 worker，但这不应该导致重复请求

## 下一步

1. 运行测试脚本验证修复
2. 查看服务器日志，确认每个请求只调用一次上游 API
3. 如果仍有问题，检查 Claude Code 客户端的配置和日志
