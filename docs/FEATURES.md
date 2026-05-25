## 功能特性

### 1. API 格式转换

#### Anthropic → OpenAI 转换

**消息格式**：

```python
# Anthropic 格式
{
  "role": "user",
  "content": [
    {"type": "text", "text": "Hello"},
    {"type": "image", "source": {...}}
  ]
}

# 转换为 OpenAI 格式
{
  "role": "user",
  "content": [
    {"type": "text", "text": "Hello"},
    {"type": "image", "source": {...}}
  ]
}
```

**工具调用转换**：

```python
# Anthropic tool_use
{
  "type": "tool_use",
  "id": "toolu_xxx",
  "name": "get_weather",
  "input": {"city": "Beijing"}
}

# 转换为 OpenAI tool_calls
{
  "tool_calls": [{
    "id": "toolu_xxx",
    "type": "function",
    "function": {
      "name": "get_weather",
      "arguments": "{\"city\": \"Beijing\"}"
    }
  }]
}
```

**工具结果转换**：

```python
# Anthropic tool_result
{
  "type": "tool_result",
  "tool_use_id": "toolu_xxx",
  "content": "Temperature: 20°C"
}

# 转换为 OpenAI tool message
{
  "role": "tool",
  "tool_call_id": "toolu_xxx",
  "content": "Temperature: 20°C"
}
```

#### System Prompt 处理

Anthropic 支持多个 system 块，代理会自动选择最长的一个：

```python
# Anthropic 格式
{
  "system": [
    {"type": "text", "text": "Short instruction"},
    {"type": "text", "text": "Very long detailed system prompt..."}
  ]
}

# 转换为 OpenAI 格式（选择最长的）
{
  "messages": [
    {"role": "system", "content": "Very long detailed system prompt..."}
  ]
}
```

### 2. 流式响应支持

#### 非流式请求

```bash
curl -X POST http://localhost:8082/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 100,
    "stream": false,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**响应**：

```json
{
  "id": "msg_xxx",
  "type": "message",
  "role": "assistant",
  "content": [{"type": "text", "text": "Hello! How can I help?"}],
  "model": "claude-sonnet-4-6",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 8
  }
}
```

#### 流式请求

```bash
curl -X POST http://localhost:8082/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 100,
    "stream": true,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**响应**（SSE 格式）：

```
event: message_start
data: {"type":"message_start","message":{...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: ping
data: {"type":"ping"}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"!"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":8}}

event: message_stop
data: {"type":"message_stop"}

data: [DONE]
```

### 3. 请求追踪 (Trace UI)

#### 访问 Trace UI

```bash
# 浏览器打开
http://localhost:8082/trace
```

#### 功能特性

- **会话列表**：查看所有 Claude Code 会话
- **请求详情**：查看每个请求的完整信息
- **时间线视图**：可视化请求链路
- **工具调用追踪**：查看工具调用的输入输出
- **性能统计**：请求耗时、token 使用量

#### API 端点

```bash
# 获取统计信息
GET /api/v2/stats

# 列出所有会话
GET /api/v2/sessions

# 获取会话详情
GET /api/v2/sessions/{session_id}

# 获取会话时间线
GET /api/v2/sessions/{session_id}/timeline

# 列出所有请求
GET /api/v2/requests

# 获取请求详情
GET /api/v2/requests/{trace_id}

# 清除所有追踪数据
DELETE /api/v2/traces
```

### 4. 自动重试机制

#### 重试策略

**触发条件**（仅瞬态错误）：
- HTTP 429（速率限制）
- HTTP 5xx（服务器错误）
- 超时错误
- 连接错误

**不重试的错误**：
- HTTP 4xx（除 429 外）：客户端错误
- 认证失败
- 无效请求

**退避策略**：

```
尝试 1: 立即
尝试 2: 等待 2 秒
尝试 3: 等待 4 秒
尝试 4: 等待 8 秒
```

#### 配置示例

```bash
# 最多重试 5 次
LITELLM_MAX_RETRIES=5

# 基础延迟 1 秒
LITELLM_RETRY_BASE_DELAY=1
```

### 5. 模型映射

#### 自动映射规则

```
客户端请求              → 实际调用
─────────────────────────────────────────
claude-opus-4-7         → openai/gpt-4.1
claude-sonnet-4-6       → openai/gpt-4.1
claude-haiku-4-5        → openai/gpt-4.1-mini
claude-3-opus-20240229  → openai/gpt-4.1
```

#### 自定义映射

```bash
# 映射到 Gemini
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-pro
SMALL_MODEL=gemini-2.5-flash

# 映射到自定义模型
PREFERRED_PROVIDER=openai
OPENAI_BASE_URL=https://api.deepseek.com/v1
BIG_MODEL=deepseek-chat
SMALL_MODEL=deepseek-chat
```

### 6. Gemini 特殊处理

#### Schema 清理

Gemini 不支持某些 JSON Schema 字段，代理会自动清理：

```python
# 原始 schema
{
  "type": "object",
  "properties": {...},
  "additionalProperties": false,  # ← 移除
  "default": {...}                # ← 移除
}

# 清理后
{
  "type": "object",
  "properties": {...}
}
```

#### Thinking 模式映射

```python
# Anthropic thinking
{"thinking": {"type": "adaptive"}}

# 映射为 Qwen3 格式
{"thinking": {"type": "auto"}}
```

---

