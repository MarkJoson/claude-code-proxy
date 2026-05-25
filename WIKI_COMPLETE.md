# Claude Code Proxy - 完整使用手册

> **版本**: 1.0  
> **更新日期**: 2024-05-25  
> **总字数**: 52,000+  
> **文档类型**: 完整 Wiki（单文件版）

---

## 📚 完整目录

### 第一部分：入门指南
- [1. 项目简介](#1-项目简介)
- [2. 快速开始](#2-快速开始)

### 第二部分：配置与使用
- [3. 配置指南](#3-配置指南)
- [4. 功能特性](#4-功能特性)

### 第三部分：问题解决
- [5. 故障排查](#5-故障排查)
- [6. 常见问题 FAQ](#6-常见问题-faq)

### 第四部分：高级主题
- [7. 性能优化](#7-性能优化)
- [8. 开发指南](#8-开发指南)
- [9. 项目结构](#9-项目结构)

---
# Claude Code Proxy - 完整使用手册

> 版本：1.0 | 更新日期：2024-05-25 | 总字数：52,000+

---

## 📚 目录

- [1. 项目简介](#1-项目简介)
- [2. 快速开始](#2-快速开始)
- [3. 配置指南](#3-配置指南)
- [4. 功能特性](#4-功能特性)
- [5. 故障排查](#5-故障排查)
- [6. 性能优化](#6-性能优化)
- [7. 开发指南](#7-开发指南)
- [8. 常见问题 FAQ](#8-常见问题-faq)
- [9. 项目结构](#9-项目结构)

---

# 1. 项目简介

Claude Code Proxy 是一个代理服务器，用于将 Anthropic Claude API 请求转发到其他 LLM 提供商（OpenAI、Google Gemini 等）。

## 核心功能

- ✅ **API 格式转换**：Anthropic API → OpenAI/Gemini API
- ✅ **模型映射**：Claude 模型 → 其他提供商模型
- ✅ **流式/非流式支持**：完整支持 SSE 流式响应
- ✅ **工具调用转换**：Anthropic tool_use ↔ OpenAI tool_calls
- ✅ **请求追踪**：内置 trace UI，可视化请求链路
- ✅ **自动重试**：处理瞬态错误（速率限制、超时等）
- ✅ **多 worker 支持**：高并发处理能力

## 架构图

```
Claude Code Client
       ↓
  [Anthropic API Format]
       ↓
Claude Code Proxy (localhost:8082)
  - 格式转换
  - 模型映射
  - 请求追踪
       ↓
  [OpenAI/Gemini API Format]
       ↓
Upstream LLM Provider
  - OpenAI
  - Google Gemini
  - 其他兼容提供商
```

## 使用场景

- ✅ 使用 Claude Code 界面，但调用更便宜的模型
- ✅ 地区限制，无法访问 Anthropic API
- ✅ 使用自己部署的 LLM 服务
- ✅ 追踪和分析 Claude Code 的请求
- ✅ 测试不同 LLM 的效果

---

# 2. 快速开始

## 环境要求

- Python 3.8+
- pip 或 conda

## 安装步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 必需：至少配置一个 API Key
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# 可选：自定义 OpenAI 端点
OPENAI_BASE_URL=https://api.openai.com/v1

# 可选：模型映射
PREFERRED_PROVIDER=openai  # openai, google, anthropic
BIG_MODEL=gpt-4.1
SMALL_MODEL=gpt-4.1-mini
```

# Claude Code Proxy - 完整使用文档

## 📚 目录

1. [项目简介](#项目简介)
2. [快速开始](#快速开始)
3. [配置指南](#配置指南)
4. [功能特性](#功能特性)
5. [故障排查](#故障排查)
6. [性能优化](#性能优化)
7. [开发指南](#开发指南)
8. [常见问题 FAQ](#常见问题-faq)

---

## 项目简介

Claude Code Proxy 是一个代理服务器，用于将 Anthropic Claude API 请求转发到其他 LLM 提供商（OpenAI、Google Gemini 等）。

### 核心功能

- ✅ **API 格式转换**：Anthropic API → OpenAI/Gemini API
- ✅ **模型映射**：Claude 模型 → 其他提供商模型
- ✅ **流式/非流式支持**：完整支持 SSE 流式响应
- ✅ **工具调用转换**：Anthropic tool_use ↔ OpenAI tool_calls
- ✅ **请求追踪**：内置 trace UI，可视化请求链路
- ✅ **自动重试**：处理瞬态错误（速率限制、超时等）
- ✅ **多 worker 支持**：高并发处理能力

### 架构图

```
Claude Code Client
       ↓
  [Anthropic API Format]
       ↓
Claude Code Proxy (localhost:8082)
  - 格式转换
  - 模型映射
  - 请求追踪
       ↓
  [OpenAI/Gemini API Format]
       ↓
Upstream LLM Provider
  - OpenAI
  - Google Gemini
  - 其他兼容提供商
```

---

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip 或 conda

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# 必需：至少配置一个 API Key
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# 可选：自定义 OpenAI 端点
OPENAI_BASE_URL=https://api.openai.com/v1

# 可选：模型映射
PREFERRED_PROVIDER=openai  # openai, google, anthropic
BIG_MODEL=gpt-4.1
SMALL_MODEL=gpt-4.1-mini

# 可选：Vertex AI 配置
USE_VERTEX_AUTH=false
VERTEX_PROJECT=your-project-id
VERTEX_LOCATION=us-central1

# 可选：性能调优
WORKERS=16
PORT=8082
BACKLOG=2048
LIMIT_CONCURRENCY=100

# 可选：重试配置
LITELLM_MAX_RETRIES=3
LITELLM_RETRY_BASE_DELAY=2

# 可选：测试模式（不调用上游 API）
CC_TRACE_ECHO_ONLY=false
```

### 4. 启动服务器

```bash
python server.py
```

或使用 uvicorn：

```bash
uvicorn server:app --host 0.0.0.0 --port 8082 --workers 4
```

### 5. 配置 Claude Code

在 Claude Code 中设置 API 端点：

```bash
# 方法 1：环境变量
export ANTHROPIC_API_KEY=any-value
export ANTHROPIC_BASE_URL=http://localhost:8082

# 方法 2：Claude Code 配置
claude config set api.baseUrl http://localhost:8082
```

### 6. 验证安装

```bash
# 测试非流式请求
python test_duplicate_requests.py

# 访问 Trace UI
open http://localhost:8082/trace
```

---

## 配置指南

### 环境变量详解

#### API Keys 配置

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `OPENAI_API_KEY` | 条件必需 | OpenAI API 密钥 | `sk-proj-xxx` |
| `GEMINI_API_KEY` | 条件必需 | Google Gemini API 密钥 | `AIzaSyxxx` |
| `ANTHROPIC_API_KEY` | 条件必需 | Anthropic API 密钥（用于直连） | `sk-ant-xxx` |

**注意**：至少需要配置一个 API Key。

#### 模型映射配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PREFERRED_PROVIDER` | `openai` | 首选提供商：`openai`, `google`, `anthropic` |
| `BIG_MODEL` | `gpt-4.1` | 大模型映射（对应 Claude Opus/Sonnet） |
| `SMALL_MODEL` | `gpt-4.1-mini` | 小模型映射（对应 Claude Haiku） |

**映射规则**：

```
Claude 模型                → 映射结果
─────────────────────────────────────────
claude-opus-*             → BIG_MODEL
claude-sonnet-*           → BIG_MODEL
claude-haiku-*            → SMALL_MODEL
claude-3-*                → BIG_MODEL
```

**示例配置**：

```bash
# 使用 OpenAI 模型
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4.1
SMALL_MODEL=gpt-4.1-mini

# 使用 Gemini 模型
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-pro
SMALL_MODEL=gemini-2.5-flash

# 直连 Anthropic（不转换）
PREFERRED_PROVIDER=anthropic
```

#### OpenAI 自定义端点

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_BASE_URL` | 无 | 自定义 OpenAI API 端点 |

**使用场景**：
- OpenAI 兼容的第三方服务（如 Qwen、DeepSeek）
- 企业内部 OpenAI 代理
- 本地部署的 LLM 服务

**示例**：

```bash
# Qwen API
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-xxx

# 本地 Ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
```

#### Vertex AI 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `USE_VERTEX_AUTH` | `false` | 是否使用 Vertex AI（ADC 认证） |
| `VERTEX_PROJECT` | `unset` | GCP 项目 ID |
| `VERTEX_LOCATION` | `unset` | GCP 区域（如 `us-central1`） |

**使用 Vertex AI**：

```bash
# 1. 配置 GCP 认证
gcloud auth application-default login

# 2. 设置环境变量
USE_VERTEX_AUTH=true
VERTEX_PROJECT=my-project-id
VERTEX_LOCATION=us-central1
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-pro
```

#### 性能调优配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PORT` | `8082` | 监听端口 |
| `WORKERS` | `16` | Worker 进程数（多核并行） |
| `BACKLOG` | `2048` | TCP 连接队列大小 |
| `LIMIT_CONCURRENCY` | 无 | 每个 worker 最大并发请求数 |

**性能建议**：

```bash
# 低负载（个人使用）
WORKERS=1
LIMIT_CONCURRENCY=10

# 中等负载（小团队）
WORKERS=4
LIMIT_CONCURRENCY=50

# 高负载（生产环境）
WORKERS=16
BACKLOG=4096
LIMIT_CONCURRENCY=100
```

#### 重试配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LITELLM_MAX_RETRIES` | `3` | 最大重试次数 |
| `LITELLM_RETRY_BASE_DELAY` | `2` | 基础延迟（秒），指数退避 |

**重试策略**：
- 仅对瞬态错误重试（429, 5xx, 超时）
- 使用指数退避：2s, 4s, 8s...
- 非瞬态错误（4xx）立即失败

#### 测试模式

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CC_TRACE_ECHO_ONLY` | `false` | 仅记录请求，不调用上游 API |

**用途**：
- 测试 Claude Code 集成
- 调试请求格式
- 压力测试（不消耗 API 配额）

```bash
CC_TRACE_ECHO_ONLY=true
python server.py
```

---

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

## 故障排查

### 常见问题诊断

#### 1. 重复请求问题

**症状**：
- 每个请求被发送两次到上游 API
- 日志中看到相同的请求出现两次
- API 配额消耗翻倍

**原因**：
- 客户端请求流式响应，但服务器返回非流式格式
- 客户端认为第一次请求失败，发起第二次重试

**诊断方法**：

```bash
# 1. 运行测试脚本
python test_duplicate_requests.py

# 2. 查看服务器日志
# 正常情况：每个测试只看到一次完整流程
🔴 MIDDLEWARE: Incoming request to POST /v1/messages
🔵 ENDPOINT ENTRY: /v1/messages - trace_id=msg_xxx
🟡 STREAMING MODE: trace_id=msg_xxx
🟢 UPSTREAM STREAMING CALL START: trace_id=msg_xxx
🟢 UPSTREAM STREAMING CALL SUCCESS: trace_id=msg_xxx
🔴 MIDDLEWARE: Response from POST /v1/messages, status=200

# 异常情况：看到两次请求
🔴 MIDDLEWARE: Incoming request (第1次)
🔵 ENDPOINT ENTRY
🟡 STREAMING MODE
🟢 UPSTREAM STREAMING CALL START
🟢 UPSTREAM STREAMING CALL SUCCESS
🔴 MIDDLEWARE: Response

🔴 MIDDLEWARE: Incoming request (第2次 - 重复！)
🔵 ENDPOINT ENTRY
🟡 NON-STREAMING MODE
🟢 UPSTREAM CALL START
🟢 UPSTREAM CALL SUCCESS
🔴 MIDDLEWARE: Response
```

**解决方案**：

已在最新代码中修复：
- ✅ 尊重客户端的 `stream` 参数
- ✅ 流式请求返回 SSE 格式
- ✅ 非流式请求返回 JSON 格式

**验证修复**：

```bash
# 重启服务器
pkill -f "python server.py"
python server.py

# 运行测试
python test_duplicate_requests.py
```

---

#### 2. 连接被拒绝

**症状**：
```
Connection refused to localhost:8082
```

**诊断步骤**：

```bash
# 1. 检查服务器是否运行
ps aux | grep server.py

# 2. 检查端口是否被占用
lsof -i :8082
netstat -tuln | grep 8082

# 3. 检查防火墙
sudo ufw status
```

**解决方案**：

```bash
# 启动服务器
python server.py

# 或使用不同端口
PORT=8083 python server.py

# 或杀死占用端口的进程
kill -9 $(lsof -t -i:8082)
```

---

#### 3. API Key 错误

**症状**：
```
401 Unauthorized
Invalid API key
```

**诊断步骤**：

```bash
# 1. 检查环境变量
echo $OPENAI_API_KEY
echo $GEMINI_API_KEY
echo $ANTHROPIC_API_KEY

# 2. 检查 .env 文件
cat .env | grep API_KEY

# 3. 测试 API Key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**解决方案**：

```bash
# 1. 重新设置 API Key
export OPENAI_API_KEY=sk-proj-xxx

# 2. 或更新 .env 文件
echo "OPENAI_API_KEY=sk-proj-xxx" >> .env

# 3. 重启服务器
pkill -f "python server.py"
python server.py
```

---

#### 4. 模型不支持

**症状**：
```
Model not found
Invalid model
```

**诊断步骤**：

```bash
# 1. 检查模型映射配置
echo $PREFERRED_PROVIDER
echo $BIG_MODEL
echo $SMALL_MODEL

# 2. 查看服务器日志中的模型映射
# 应该看到类似：
📌 MODEL MAPPING: 'claude-sonnet-4-6' ➡️ 'openai/gpt-4.1'
```

**解决方案**：

```bash
# 1. 使用支持的模型
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini

# 2. 或使用 Gemini
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-pro
SMALL_MODEL=gemini-2.5-flash

# 3. 重启服务器
python server.py
```

---

#### 5. 流式响应中断

**症状**：
- 流式响应突然停止
- 收到部分响应后连接断开
- 客户端超时

**诊断步骤**：

```bash
# 1. 测试流式响应
curl -N -X POST http://localhost:8082/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 1000,
    "stream": true,
    "messages": [{"role": "user", "content": "Write a long story"}]
  }'

# 2. 检查服务器日志
# 查找错误或异常
```

**常见原因**：

1. **上游 API 超时**
   ```bash
   # 增加超时时间
   # 在 server.py 中修改 uvicorn 配置
   timeout_keep_alive=300  # 5分钟
   ```

2. **网络不稳定**
   ```bash
   # 增加重试次数
   LITELLM_MAX_RETRIES=5
   ```

3. **Worker 进程崩溃**
   ```bash
   # 减少并发
   WORKERS=1
   LIMIT_CONCURRENCY=10
   ```

---

#### 6. 工具调用失败

**症状**：
- 工具调用格式错误
- 工具结果无法解析
- Claude Code 报告工具执行失败

**诊断步骤**：

```bash
# 1. 查看 Trace UI
open http://localhost:8082/trace

# 2. 检查工具调用日志
# 应该看到：
Processing tool calls: [...]
Adding tool_use block: id=toolu_xxx, name=Read, input={...}

# 3. 检查工具结果格式
```

**常见问题**：

1. **工具参数格式错误**
   - 确保 `input_schema` 正确
   - 检查 Gemini schema 清理是否正确

2. **工具结果内容格式错误**
   ```python
   # 错误：返回对象
   {"type": "tool_result", "content": {"data": "..."}}
   
   # 正确：返回字符串
   {"type": "tool_result", "content": "..."}
   ```

---

#### 7. 性能问题

**症状**：
- 响应缓慢
- 请求排队
- CPU/内存占用高

**诊断步骤**：

```bash
# 1. 检查系统资源
top
htop

# 2. 检查并发请求数
# 查看 Trace UI 统计信息
curl http://localhost:8082/api/v2/stats

# 3. 检查 worker 数量
ps aux | grep "uvicorn worker" | wc -l
```

**优化方案**：

```bash
# 1. 增加 worker 数量（多核 CPU）
WORKERS=16

# 2. 限制并发（防止过载）
LIMIT_CONCURRENCY=100

# 3. 增加 TCP backlog
BACKLOG=4096

# 4. 使用更快的模型
BIG_MODEL=gpt-4o-mini
SMALL_MODEL=gpt-4o-mini
```

---

#### 8. 内存泄漏

**症状**：
- 内存使用持续增长
- 长时间运行后崩溃
- OOM (Out of Memory) 错误

**诊断步骤**：

```bash
# 1. 监控内存使用
watch -n 1 'ps aux | grep server.py'

# 2. 检查 trace 数据库大小
ls -lh trace.db

# 3. 检查是否有大量未清理的 trace
curl http://localhost:8082/api/v2/stats
```

**解决方案**：

```bash
# 1. 定期清理 trace 数据
curl -X DELETE http://localhost:8082/api/v2/traces

# 2. 重启服务器（临时方案）
pkill -f "python server.py"
python server.py

# 3. 使用 cron 定期重启
# 添加到 crontab
0 3 * * * pkill -f "python server.py" && cd /path/to/proxy && python server.py
```

---

### 日志分析

#### 启用详细日志

```python
# 修改 server.py
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
)
```

#### 关键日志标记

| 标记 | 含义 | 示例 |
|------|------|------|
| 🔴 | 中间件/HTTP 层 | `🔴 MIDDLEWARE: Incoming request` |
| 🔵 | 端点入口 | `🔵 ENDPOINT ENTRY: /v1/messages` |
| 🟡 | 模式选择 | `🟡 STREAMING MODE` |
| 🟢 | 上游调用 | `🟢 UPSTREAM CALL START` |
| 📌 | 模型映射 | `📌 MODEL MAPPING: 'claude' ➡️ 'gpt-4'` |
| ⚠️ | 警告 | `⚠️ No prefix or mapping rule` |
| ⏳ | 重试 | `⏳ Transient error, retrying` |
| ✅ | 成功 | `✅ RESPONSE RECEIVED` |

---

## 性能优化

### 1. Worker 配置

#### 单 Worker vs 多 Worker

**单 Worker**（默认）：
```bash
WORKERS=1
```

**优点**：
- 简单，易于调试
- 内存占用低
- 适合个人使用

**缺点**：
- 无法利用多核 CPU
- 并发能力有限

**多 Worker**：
```bash
WORKERS=16
```

**优点**：
- 充分利用多核 CPU
- 高并发处理能力
- 适合生产环境

**缺点**：
- 内存占用高（每个 worker 独立进程）
- 调试复杂
- 模块级状态不共享

#### 最佳实践

```bash
# CPU 核心数
CORES=$(nproc)

# 推荐配置：2 * CPU 核心数
WORKERS=$((CORES * 2))

# 示例：8核 CPU
WORKERS=16
```

### 2. 并发限制

#### 配置并发上限

```bash
# 每个 worker 最多处理 100 个并发请求
LIMIT_CONCURRENCY=100
```

**作用**：
- 防止过载
- 保护上游 API
- 避免内存耗尽

**计算方法**：

```
总并发能力 = WORKERS × LIMIT_CONCURRENCY

示例：
WORKERS=16
LIMIT_CONCURRENCY=100
总并发 = 16 × 100 = 1600 个请求
```

#### 根据场景调整

| 场景 | WORKERS | LIMIT_CONCURRENCY | 总并发 |
|------|---------|-------------------|--------|
| 个人开发 | 1 | 10 | 10 |
| 小团队 | 4 | 50 | 200 |
| 中型团队 | 8 | 100 | 800 |
| 生产环境 | 16 | 100 | 1600 |

### 3. TCP 优化

#### Backlog 配置

```bash
# TCP 连接队列大小
BACKLOG=2048
```

**作用**：
- 处理突发流量
- 减少连接拒绝
- 提高吞吐量

**推荐值**：

| 负载 | BACKLOG |
|------|---------|
| 低 | 1024 |
| 中 | 2048 |
| 高 | 4096 |

#### Keep-Alive 配置

```python
# server.py 中的 uvicorn 配置
uvicorn_kwargs = {
    "timeout_keep_alive": 75,  # 保持连接 75 秒
}
```

**优点**：
- 减少连接建立开销
- 提高响应速度
- 适合频繁请求

### 4. 重试优化

#### 减少不必要的重试

```bash
# 降低重试次数（快速失败）
LITELLM_MAX_RETRIES=1

# 减少重试延迟
LITELLM_RETRY_BASE_DELAY=1
```

**适用场景**：
- 上游 API 稳定
- 对延迟敏感
- 不希望长时间等待

#### 增加重试容错

```bash
# 增加重试次数（提高成功率）
LITELLM_MAX_RETRIES=5

# 增加重试延迟（避免速率限制）
LITELLM_RETRY_BASE_DELAY=3
```

**适用场景**：
- 上游 API 不稳定
- 频繁遇到速率限制
- 对成功率要求高

### 5. 模型选择优化

#### 使用更快的模型

```bash
# 使用小模型（更快，更便宜）
BIG_MODEL=gpt-4o-mini
SMALL_MODEL=gpt-4o-mini

# 或使用 Gemini Flash（极快）
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-flash
SMALL_MODEL=gemini-2.5-flash
```

#### 模型性能对比

| 模型 | 速度 | 成本 | 质量 |
|------|------|------|------|
| gpt-4.1 | 慢 | 高 | 最高 |
| gpt-4o | 中 | 中 | 高 |
| gpt-4o-mini | 快 | 低 | 中 |
| gemini-2.5-pro | 中 | 中 | 高 |
| gemini-2.5-flash | 极快 | 极低 | 中 |

### 6. 缓存优化

#### Prompt Caching（上游 API）

某些提供商支持 prompt caching：

```python
# Anthropic 原生支持
# OpenAI 不支持
# Gemini 支持（context caching）
```

**优化建议**：
- 使用支持缓存的提供商
- 保持 system prompt 稳定
- 重用相同的上下文

### 7. 网络优化

#### 使用本地/区域端点

```bash
# 使用地理位置更近的端点
OPENAI_BASE_URL=https://api.openai.com/v1  # 美国
# 或
OPENAI_BASE_URL=https://api.openai-proxy.com/v1  # 国内代理

# Vertex AI 选择最近的区域
VERTEX_LOCATION=asia-northeast1  # 东京
```

#### 连接池优化

LiteLLM 自动管理连接池，但可以调整：

```python
# 在 server.py 中添加
import httpx

# 自定义 HTTP 客户端
litellm.client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

### 8. 内存优化

#### 定期清理 Trace 数据

```bash
# 方法 1：API 清理
curl -X DELETE http://localhost:8082/api/v2/traces

# 方法 2：删除数据库文件
rm trace.db

# 方法 3：定时任务
# 每天凌晨 3 点清理
0 3 * * * curl -X DELETE http://localhost:8082/api/v2/traces
```

#### 限制 Trace 数据大小

```python
# 在 trace_db.py 中添加
MAX_TRACES = 1000  # 最多保留 1000 条记录

# 自动清理旧数据
def cleanup_old_traces():
    # 删除最旧的记录
    pass
```

### 9. 监控和指标

#### 实时监控

```bash
# 1. 查看统计信息
curl http://localhost:8082/api/v2/stats | jq

# 2. 监控系统资源
watch -n 1 'ps aux | grep server.py'

# 3. 监控网络连接
watch -n 1 'netstat -an | grep 8082 | wc -l'
```

#### 关键指标

| 指标 | 命令 | 正常范围 |
|------|------|----------|
| CPU 使用率 | `top` | < 80% |
| 内存使用 | `free -h` | < 80% |
| 并发连接数 | `netstat -an \| grep 8082 \| wc -l` | < LIMIT_CONCURRENCY |
| 响应时间 | Trace UI | < 5s |

### 10. 生产环境配置示例

#### 高性能配置

```bash
# .env.production
PORT=8082
WORKERS=16
BACKLOG=4096
LIMIT_CONCURRENCY=100

# 使用快速模型
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-flash
SMALL_MODEL=gemini-2.5-flash

# 快速失败
LITELLM_MAX_RETRIES=2
LITELLM_RETRY_BASE_DELAY=1

# 网络优化
VERTEX_LOCATION=asia-northeast1
```

#### 高可靠性配置

```bash
# .env.production
PORT=8082
WORKERS=8
BACKLOG=2048
LIMIT_CONCURRENCY=50

# 使用稳定模型
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini

# 增强重试
LITELLM_MAX_RETRIES=5
LITELLM_RETRY_BASE_DELAY=3
```

#### 低成本配置

```bash
# .env.production
PORT=8082
WORKERS=4
BACKLOG=1024
LIMIT_CONCURRENCY=20

# 使用便宜模型
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-flash
SMALL_MODEL=gemini-2.5-flash

# 快速失败（减少重试成本）
LITELLM_MAX_RETRIES=1
LITELLM_RETRY_BASE_DELAY=1
```

---

## 开发指南

### 项目结构

```
claude-code-proxy/
├── server.py              # 主服务器文件
├── trace_db.py           # 追踪数据库模块
├── requirements.txt      # Python 依赖
├── .env                  # 环境变量配置
├── .env.example          # 环境变量示例
├── trace.db              # SQLite 追踪数据库
├── static/
│   └── trace.html        # Trace UI 前端
├── docs/                 # 文档目录
│   ├── README.md
│   ├── CONFIGURATION.md
│   ├── FEATURES.md
│   ├── TROUBLESHOOTING.md
│   ├── PERFORMANCE.md
│   └── DEVELOPMENT.md
└── test_duplicate_requests.py  # 测试脚本
```

### 核心模块

#### 1. server.py

**主要功能**：
- FastAPI 应用定义
- API 端点实现
- 请求/响应转换
- 模型映射逻辑
- 流式响应处理

**关键函数**：

```python
# 消息端点
@app.post("/v1/messages")
async def create_message(request: MessagesRequest, raw_request: Request)

# Token 计数端点
@app.post("/v1/messages/count_tokens")
async def count_tokens(request: TokenCountRequest, raw_request: Request)

# 格式转换
def convert_anthropic_to_litellm(anthropic_request: MessagesRequest) -> Dict
def convert_litellm_to_anthropic(litellm_response, original_request) -> MessagesResponse

# 流式处理
async def handle_streaming(response_generator, original_request: MessagesRequest)

# Schema 清理（Gemini）
def clean_gemini_schema(schema: Any) -> Any
```

#### 2. trace_db.py

**主要功能**：
- SQLite 数据库管理
- 请求追踪记录
- 会话管理
- 统计信息

**关键函数**：

```python
# 记录请求
def record_request_started(trace_id, api, method, path, headers, client, body_json, mapped_model)
def record_request_completed(trace_id, status_code, duration_ms, converted_request, response, extra)
def record_request_failed(trace_id, status_code, duration_ms, converted_request, error)

# 查询
def get_request(trace_id)
def list_requests(filters)
def get_session(session_id)
def list_sessions()

# 统计
def snapshot_stats()

# 可视化
def build_timeline(session_id)
def build_agent_tree(session_id)
def build_time_trajectory(session_id)
```

### 添加新功能

#### 示例：添加新的模型提供商

**步骤 1：添加模型列表**

```python
# server.py
CUSTOM_MODELS = [
    "custom-model-1",
    "custom-model-2"
]
```

**步骤 2：更新模型映射逻辑**

```python
# server.py - validate_model_field 函数
elif clean_v in CUSTOM_MODELS and not v.startswith('custom/'):
    new_model = f"custom/{clean_v}"
    mapped = True
```

**步骤 3：配置 API Key**

```python
# server.py
CUSTOM_API_KEY = os.environ.get("CUSTOM_API_KEY")

# 在 create_message 函数中
elif request.model.startswith("custom/"):
    litellm_request["api_key"] = CUSTOM_API_KEY
    litellm_request["api_base"] = "https://api.custom.com/v1"
```

**步骤 4：测试**

```bash
# .env
CUSTOM_API_KEY=xxx
PREFERRED_PROVIDER=custom
BIG_MODEL=custom-model-1

# 测试
python test_duplicate_requests.py
```

#### 示例：添加自定义中间件

```python
# server.py
@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    # 请求前处理
    start_time = time.time()
    
    # 添加自定义 header
    request.state.custom_id = str(uuid.uuid4())
    
    # 处理请求
    response = await call_next(request)
    
    # 响应后处理
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Custom-ID"] = request.state.custom_id
    
    return response
```

#### 示例：添加新的 API 端点

```python
# server.py
@app.get("/api/v2/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@app.post("/api/v2/batch")
async def batch_messages(requests: List[MessagesRequest]):
    """批量处理消息"""
    results = []
    for req in requests:
        try:
            result = await create_message(req, None)
            results.append({"success": True, "data": result})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    return {"results": results}
```

### 调试技巧

#### 1. 启用详细日志

```python
# server.py
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# 查看 LiteLLM 日志
litellm.set_verbose = True
```

#### 2. 使用 Python 调试器

```python
# server.py - 在需要调试的地方添加
import pdb; pdb.set_trace()

# 或使用 ipdb（更友好）
import ipdb; ipdb.set_trace()
```

#### 3. 请求/响应日志

```python
# server.py - create_message 函数中
logger.debug(f"Request body: {json.dumps(body_json, indent=2)}")
logger.debug(f"Converted request: {json.dumps(litellm_request, indent=2)}")
logger.debug(f"Response: {json.dumps(anthropic_response.dict(), indent=2)}")
```

#### 4. 使用测试模式

```bash
# 不调用上游 API，仅记录请求
CC_TRACE_ECHO_ONLY=true python server.py
```

### 测试

#### 单元测试

```python
# test_server.py
import pytest
from server import convert_anthropic_to_litellm, MessagesRequest

def test_convert_anthropic_to_litellm():
    request = MessagesRequest(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": "Hello"}]
    )
    result = convert_anthropic_to_litellm(request)
    
    assert result["model"].startswith("openai/")
    assert len(result["messages"]) > 0
    assert result["max_tokens"] == 100

def test_model_mapping():
    # 测试模型映射逻辑
    pass
```

#### 集成测试

```python
# test_integration.py
import requests

def test_messages_endpoint():
    response = requests.post(
        "http://localhost:8082/v1/messages",
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["role"] == "assistant"

def test_streaming():
    response = requests.post(
        "http://localhost:8082/v1/messages",
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 100,
            "stream": True,
            "messages": [{"role": "user", "content": "Hello"}]
        },
        stream=True
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
```

#### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行测试
pytest test_server.py
pytest test_integration.py

# 运行特定测试
pytest test_server.py::test_convert_anthropic_to_litellm

# 显示详细输出
pytest -v -s
```

### 代码风格

#### Python 风格指南

遵循 PEP 8：

```bash
# 安装 linter
pip install flake8 black isort

# 检查代码风格
flake8 server.py

# 自动格式化
black server.py
isort server.py
```

#### 类型注解

```python
from typing import Dict, List, Optional, Union, Any

def convert_anthropic_to_litellm(
    anthropic_request: MessagesRequest
) -> Dict[str, Any]:
    """
    Convert Anthropic API request to LiteLLM format.
    
    Args:
        anthropic_request: Anthropic format request
        
    Returns:
        LiteLLM compatible request dict
    """
    pass
```

### 性能分析

#### 使用 cProfile

```python
# profile_server.py
import cProfile
import pstats
from server import app

def profile_endpoint():
    # 模拟请求
    pass

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 运行代码
    profile_endpoint()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

#### 使用 memory_profiler

```bash
# 安装
pip install memory_profiler

# 使用
python -m memory_profiler server.py
```

### 部署

#### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8082

CMD ["python", "server.py"]
```

```bash
# 构建镜像
docker build -t claude-code-proxy .

# 运行容器
docker run -d \
  -p 8082:8082 \
  -e OPENAI_API_KEY=xxx \
  -e PREFERRED_PROVIDER=openai \
  --name claude-proxy \
  claude-code-proxy
```

#### Systemd 服务

```ini
# /etc/systemd/system/claude-proxy.service
[Unit]
Description=Claude Code Proxy
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/claude-code-proxy
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/claude-code-proxy/.env
ExecStart=/usr/bin/python3 /opt/claude-code-proxy/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl enable claude-proxy
sudo systemctl start claude-proxy
sudo systemctl status claude-proxy
```

---

## 常见问题 FAQ

### 基础问题

#### Q1: 这个项目是做什么的？

**A:** Claude Code Proxy 是一个代理服务器，允许你使用 Claude Code 客户端，但实际调用其他 LLM 提供商（如 OpenAI、Google Gemini）的 API。它会自动转换 API 格式和模型名称。

**使用场景**：
- 你想用 Claude Code 的界面，但使用更便宜的模型
- 你的地区无法访问 Anthropic API
- 你想使用自己部署的 LLM 服务
- 你想追踪和分析 Claude Code 的请求

---

#### Q2: 支持哪些 LLM 提供商？

**A:** 支持所有 LiteLLM 兼容的提供商：

| 提供商 | 配置方式 | 示例模型 |
|--------|----------|----------|
| OpenAI | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini |
| Google Gemini | `GEMINI_API_KEY` | gemini-2.5-pro, gemini-2.5-flash |
| Anthropic | `ANTHROPIC_API_KEY` | claude-opus-4-7, claude-sonnet-4-6 |
| Azure OpenAI | `AZURE_API_KEY` | azure/gpt-4 |
| AWS Bedrock | AWS 凭证 | bedrock/claude-v2 |
| Vertex AI | GCP 凭证 | vertex_ai/gemini-pro |
| 自定义端点 | `OPENAI_BASE_URL` | 任何 OpenAI 兼容 API |

---

#### Q3: 会消耗我的 Anthropic API 配额吗？

**A:** 不会！代理会将请求转发到你配置的其他提供商（如 OpenAI），不会调用 Anthropic API。

**配额消耗**：
- ❌ 不消耗：Anthropic API 配额
- ✅ 消耗：你配置的提供商的配额（如 OpenAI）

---

#### Q4: 需要 Anthropic API Key 吗？

**A:** 不需要！你只需要配置目标提供商的 API Key。

```bash
# 只需要这个
OPENAI_API_KEY=sk-proj-xxx

# 不需要这个
# ANTHROPIC_API_KEY=sk-ant-xxx
```

但是，Claude Code 客户端可能要求你设置 `ANTHROPIC_API_KEY` 环境变量，你可以设置任意值：

```bash
export ANTHROPIC_API_KEY=dummy
export ANTHROPIC_BASE_URL=http://localhost:8082
```

---

### 配置问题

#### Q5: 如何配置使用 OpenAI？

**A:**

```bash
# .env
OPENAI_API_KEY=sk-proj-xxx
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini
```

然后启动服务器：

```bash
python server.py
```

---

#### Q6: 如何配置使用 Gemini？

**A:**

```bash
# .env
GEMINI_API_KEY=AIzaSyxxx
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-pro
SMALL_MODEL=gemini-2.5-flash
```

---

#### Q7: 如何使用自定义的 OpenAI 兼容端点？

**A:** 设置 `OPENAI_BASE_URL`：

```bash
# Qwen API
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-xxx

# DeepSeek
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_API_KEY=sk-xxx

# 本地 Ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
```

---

#### Q8: 模型映射是如何工作的？

**A:** 代理会自动将 Claude 模型名称映射到你配置的模型：

```
Claude Code 请求          → 实际调用
─────────────────────────────────────────
claude-opus-4-7          → openai/gpt-4o
claude-sonnet-4-6        → openai/gpt-4o
claude-haiku-4-5         → openai/gpt-4o-mini
```

你可以自定义映射：

```bash
BIG_MODEL=gpt-4.1        # Opus/Sonnet 映射到这个
SMALL_MODEL=gpt-4.1-mini # Haiku 映射到这个
```

---

### 功能问题

#### Q9: 支持流式响应吗？

**A:** 完全支持！代理会自动检测客户端请求的模式：

- 客户端请求流式 → 返回 SSE 流式响应
- 客户端请求非流式 → 返回 JSON 响应

---

#### Q10: 支持工具调用（Tool Use）吗？

**A:** 完全支持！代理会自动转换工具调用格式：

```
Anthropic tool_use ↔ OpenAI tool_calls
```

所有 Claude Code 的工具（Read, Write, Bash 等）都能正常工作。

---

#### Q11: 如何查看请求详情？

**A:** 访问内置的 Trace UI：

```bash
http://localhost:8082/trace
```

功能：
- 查看所有请求和响应
- 查看工具调用详情
- 查看时间线和性能统计
- 导出请求数据

---

#### Q12: 如何清理追踪数据？

**A:**

```bash
# 方法 1：API
curl -X DELETE http://localhost:8082/api/v2/traces

# 方法 2：删除数据库
rm trace.db

# 方法 3：重启服务器（数据保留）
pkill -f "python server.py"
python server.py
```

---

### 性能问题

#### Q13: 为什么响应很慢？

**A:** 可能的原因：

1. **上游 API 慢**
   - 解决：使用更快的模型（如 gpt-4o-mini, gemini-flash）

2. **网络延迟**
   - 解决：使用地理位置更近的端点

3. **Worker 不足**
   - 解决：增加 worker 数量
   ```bash
   WORKERS=16
   ```

4. **并发过高**
   - 解决：限制并发
   ```bash
   LIMIT_CONCURRENCY=50
   ```

---

#### Q14: 如何提高并发能力？

**A:**

```bash
# 增加 worker 数量
WORKERS=16

# 增加每个 worker 的并发限制
LIMIT_CONCURRENCY=100

# 增加 TCP backlog
BACKLOG=4096

# 总并发能力 = 16 × 100 = 1600
```

---

#### Q15: 内存占用太高怎么办？

**A:**

1. **减少 worker 数量**
   ```bash
   WORKERS=4
   ```

2. **定期清理 trace 数据**
   ```bash
   curl -X DELETE http://localhost:8082/api/v2/traces
   ```

3. **使用 cron 定期重启**
   ```bash
   # 每天凌晨 3 点重启
   0 3 * * * pkill -f "python server.py" && cd /path && python server.py
   ```

---

### 错误问题

#### Q16: 为什么看到 "Connection refused"？

**A:**

1. **服务器未启动**
   ```bash
   python server.py
   ```

2. **端口被占用**
   ```bash
   # 检查
   lsof -i :8082
   
   # 使用其他端口
   PORT=8083 python server.py
   ```

3. **防火墙阻止**
   ```bash
   sudo ufw allow 8082
   ```

---

#### Q17: 为什么看到 "401 Unauthorized"？

**A:**

1. **API Key 未设置**
   ```bash
   echo $OPENAI_API_KEY
   # 如果为空，设置它
   export OPENAI_API_KEY=sk-proj-xxx
   ```

2. **API Key 错误**
   ```bash
   # 测试 API Key
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **使用了错误的提供商**
   ```bash
   # 检查配置
   echo $PREFERRED_PROVIDER
   ```

---

#### Q18: 为什么看到重复请求？

**A:** 这是已知问题，已在最新版本修复。

**原因**：客户端请求流式响应，但服务器返回非流式格式，导致客户端重试。

**解决方案**：
1. 更新到最新代码
2. 重启服务器
3. 运行测试验证：
   ```bash
   python test_duplicate_requests.py
   ```

详见：[DUPLICATE_REQUEST_FIX.md](../DUPLICATE_REQUEST_FIX.md)

---

#### Q19: 为什么工具调用失败？

**A:**

1. **检查 Trace UI**
   ```bash
   http://localhost:8082/trace
   ```
   查看工具调用的输入输出

2. **检查模型是否支持工具调用**
   - ✅ 支持：gpt-4o, gpt-4o-mini, gemini-2.5-pro
   - ❌ 不支持：某些小模型

3. **检查工具参数格式**
   - 确保 `input_schema` 正确
   - Gemini 需要特殊的 schema 清理（自动处理）

---

### 高级问题

#### Q20: 如何在生产环境部署？

**A:** 推荐使用 Docker + Nginx：

```bash
# 1. 构建 Docker 镜像
docker build -t claude-proxy .

# 2. 运行容器
docker run -d \
  -p 8082:8082 \
  -e OPENAI_API_KEY=xxx \
  --restart always \
  --name claude-proxy \
  claude-proxy

# 3. 配置 Nginx 反向代理
# /etc/nginx/sites-available/claude-proxy
server {
    listen 80;
    server_name proxy.example.com;
    
    location / {
        proxy_pass http://localhost:8082;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

#### Q21: 如何监控服务健康状态？

**A:**

```bash
# 1. 检查进程
ps aux | grep server.py

# 2. 检查端口
netstat -tuln | grep 8082

# 3. 健康检查端点
curl http://localhost:8082/

# 4. 查看统计信息
curl http://localhost:8082/api/v2/stats

# 5. 使用监控工具
# Prometheus + Grafana
# 或 Datadog, New Relic 等
```

---

#### Q22: 如何实现负载均衡？

**A:** 使用 Nginx 或 HAProxy：

```nginx
# Nginx 配置
upstream claude_proxy {
    least_conn;
    server 127.0.0.1:8082;
    server 127.0.0.1:8083;
    server 127.0.0.1:8084;
}

server {
    listen 80;
    location / {
        proxy_pass http://claude_proxy;
    }
}
```

---

#### Q23: 如何实现高可用？

**A:**

1. **多实例部署**
   ```bash
   # 实例 1
   PORT=8082 python server.py &
   
   # 实例 2
   PORT=8083 python server.py &
   
   # 实例 3
   PORT=8084 python server.py &
   ```

2. **使用负载均衡器**（见 Q22）

3. **健康检查和自动重启**
   ```bash
   # systemd 配置
   Restart=always
   RestartSec=10
   ```

4. **数据库备份**
   ```bash
   # 定期备份 trace.db
   0 */6 * * * cp trace.db trace.db.backup
   ```

---

#### Q24: 如何限制访问？

**A:**

1. **IP 白名单**（Nginx）
   ```nginx
   location / {
       allow 192.168.1.0/24;
       deny all;
       proxy_pass http://localhost:8082;
   }
   ```

2. **API Key 认证**（自定义中间件）
   ```python
   @app.middleware("http")
   async def auth_middleware(request: Request, call_next):
       api_key = request.headers.get("X-API-Key")
       if api_key != "your-secret-key":
           return JSONResponse(
               status_code=401,
               content={"error": "Unauthorized"}
           )
       return await call_next(request)
   ```

3. **使用 VPN**
   - 只允许 VPN 内部访问

---

#### Q25: 如何调试问题？

**A:**

1. **启用详细日志**
   ```python
   # server.py
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **使用测试模式**
   ```bash
   CC_TRACE_ECHO_ONLY=true python server.py
   ```

3. **查看 Trace UI**
   ```bash
   http://localhost:8082/trace
   ```

4. **运行测试脚本**
   ```bash
   python test_duplicate_requests.py
   ```

5. **检查日志标记**
   - 🔴 中间件层
   - 🔵 端点入口
   - 🟡 模式选择
   - 🟢 上游调用
   - 📌 模型映射

---

### 其他问题

#### Q26: 支持哪些 Claude Code 版本？

**A:** 支持所有使用 Anthropic API 的 Claude Code 版本：
- Claude Code CLI
- Claude Code Desktop
- Claude Code Web
- VS Code / JetBrains 扩展

---

#### Q27: 会影响 Claude Code 的功能吗？

**A:** 不会！所有功能都正常工作：
- ✅ 工具调用（Read, Write, Bash 等）
- ✅ 流式响应
- ✅ 多轮对话
- ✅ 图片输入
- ✅ 长上下文

唯一的区别是使用不同的 LLM 模型，可能在响应质量上有差异。

---

#### Q28: 如何贡献代码？

**A:**

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 发起 Pull Request

**贡献指南**：
- 遵循 PEP 8 代码风格
- 添加测试
- 更新文档
- 详细的 commit 信息

---

#### Q29: 在哪里获取帮助？

**A:**

1. **查看文档**
   - [README.md](README.md)
   - [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
   - [FAQ.md](FAQ.md)

2. **查看日志**
   ```bash
   tail -f server.log
   ```

3. **使用 Trace UI**
   ```bash
   http://localhost:8082/trace
   ```

4. **提交 Issue**
   - 描述问题
   - 附上日志
   - 说明环境信息

---

#### Q30: 项目的未来计划？

**A:**

- [ ] 支持更多 LLM 提供商
- [ ] 改进 Trace UI
- [ ] 添加缓存层
- [ ] 支持请求队列
- [ ] 添加 Prometheus metrics
- [ ] 支持多租户
- [ ] Web 管理界面
- [ ] 自动化测试

---

# 项目结构说明

## 📁 目录结构

```
claude-code-proxy/
├── server.py                      # 主服务器文件（FastAPI 应用）
├── trace_db.py                    # 追踪数据库模块（SQLite）
├── requirements.txt               # Python 依赖列表
├── pyproject.toml                 # 项目配置（uv）
├── .env                           # 环境变量配置（需创建）
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git 忽略文件
├── README.md                      # 项目主 README（英文）
├── DOCS_CN.md                     # 中文文档入口
├── DUPLICATE_REQUEST_FIX.md       # 重复请求问题修复说明
├── DOCUMENTATION_SUMMARY.md       # 文档创建总结
│
├── docs/                          # 📚 完整文档目录
│   ├── INDEX.md                   # 文档索引（导航中心）
│   ├── README.md                  # 快速开始
│   ├── CONFIGURATION.md           # 配置指南
│   ├── FEATURES.md                # 功能特性
│   ├── TROUBLESHOOTING.md         # 故障排查
│   ├── PERFORMANCE.md             # 性能优化
│   ├── DEVELOPMENT.md             # 开发指南
│   ├── FAQ.md                     # 常见问题
│   └── STRUCTURE.md               # 本文件
│
├── static/                        # 静态文件目录
│   └── trace.html                 # Trace UI 前端页面
│
├── scripts/                       # 脚本目录
│   └── claude_trace_ui.sh         # Claude Code 启动脚本
│
├── test_duplicate_requests.py     # 重复请求测试脚本
├── test_claude_sdk_trace.py       # Claude SDK 追踪测试
│
├── trace.db                       # SQLite 追踪数据库（运行时生成）
└── cc_traces/                     # 追踪数据目录（可配置）
    └── trace.db                   # 备用追踪数据库位置
```

## 📄 核心文件说明

### server.py
**主服务器文件**，包含：
- FastAPI 应用定义
- `/v1/messages` 端点（消息处理）
- `/v1/messages/count_tokens` 端点（Token 计数）
- API 格式转换逻辑
- 模型映射逻辑
- 流式响应处理
- Trace UI 路由

**关键函数**：
- `create_message()` - 处理消息请求
- `count_tokens()` - 计算 token 数量
- `convert_anthropic_to_litellm()` - Anthropic → LiteLLM 转换
- `convert_litellm_to_anthropic()` - LiteLLM → Anthropic 转换
- `handle_streaming()` - 流式响应处理
- `clean_gemini_schema()` - Gemini schema 清理

### trace_db.py
**追踪数据库模块**，包含：
- SQLite 数据库管理
- 请求记录和查询
- 会话管理
- 统计信息
- 可视化数据构建

**关键函数**：
- `record_request_started()` - 记录请求开始
- `record_request_completed()` - 记录请求完成
- `record_request_failed()` - 记录请求失败
- `get_request()` - 获取请求详情
- `list_sessions()` - 列出所有会话
- `build_timeline()` - 构建时间线
- `build_agent_tree()` - 构建 Agent 层级树

### requirements.txt
**Python 依赖列表**：
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服务器
- `litellm` - 统一 LLM API 接口
- `httpx` - HTTP 客户端
- `pydantic` - 数据验证
- `python-dotenv` - 环境变量管理

### .env
**环境变量配置文件**（需要创建）：
```bash
# API Keys
OPENAI_API_KEY=sk-proj-xxx
GEMINI_API_KEY=AIzaSyxxx
ANTHROPIC_API_KEY=sk-ant-xxx

# 模型配置
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini

# 性能配置
WORKERS=16
PORT=8082
LIMIT_CONCURRENCY=100
```

## 📚 文档文件说明

### docs/INDEX.md
**文档索引和导航中心**
- 所有文档的入口
- 按场景分类的快速查找
- 文档统计信息

### docs/README.md
**快速开始指南**
- 项目简介
- 安装步骤
- 基础配置
- 验证方法

### docs/CONFIGURATION.md
**配置指南**
- 环境变量详解
- API Keys 配置
- 模型映射规则
- 性能调优参数

### docs/FEATURES.md
**功能特性说明**
- API 格式转换
- 流式响应
- 工具调用
- 请求追踪
- 自动重试

### docs/TROUBLESHOOTING.md
**故障排查指南**
- 8 大类常见问题
- 诊断步骤
- 解决方案
- 日志分析

### docs/PERFORMANCE.md
**性能优化指南**
- Worker 配置
- 并发优化
- 网络优化
- 内存优化
- 生产环境配置

### docs/DEVELOPMENT.md
**开发指南**
- 项目结构
- 核心模块
- 添加新功能
- 测试方法
- 部署方案

### docs/FAQ.md
**常见问题解答**
- 30+ 个 FAQ
- 按类别分组
- 详细解答

## 🧪 测试文件说明

### test_duplicate_requests.py
**重复请求测试脚本**
- 测试流式请求
- 测试非流式请求
- 验证是否有重复调用
- 查看调试日志

**使用方法**：
```bash
python test_duplicate_requests.py
```

### test_claude_sdk_trace.py
**Claude SDK 追踪测试**
- 测试 Claude Agent SDK 集成
- 验证追踪功能
- 多场景测试

**使用方法**：
```bash
uv run --dev python test_claude_sdk_trace.py --base-url http://127.0.0.1:8082
```

## 🎨 静态文件说明

### static/trace.html
**Trace UI 前端页面**
- 会话列表
- 请求详情
- 时间线视图
- Agent 层级树
- 历史链视图

**访问方式**：
```bash
http://localhost:8082/trace
```

## 📜 脚本文件说明

### scripts/claude_trace_ui.sh
**Claude Code 启动脚本**
- 自动启动代理服务器
- 配置环境变量
- 启动 Claude Code
- 清理追踪数据

**使用方法**：
```bash
scripts/claude_trace_ui.sh --clear-trace
```

## 🗄️ 数据文件说明

### trace.db
**SQLite 追踪数据库**
- 存储所有请求记录
- 会话信息
- 工具调用事件
- Agent 调用记录

**位置**：
- 默认：项目根目录
- 可配置：`CC_TRACE_DIR` 环境变量

**清理方法**：
```bash
# API 清理
curl -X DELETE http://localhost:8082/api/v2/traces

# 或直接删除
rm trace.db
```

## 🔧 配置文件说明

### pyproject.toml
**项目配置文件**（uv）
- 项目元数据
- 依赖管理
- 构建配置

### .gitignore
**Git 忽略文件**
- `.env` - 环境变量（包含密钥）
- `trace.db` - 追踪数据库
- `__pycache__/` - Python 缓存
- `*.pyc` - 编译文件

## 📊 文件大小参考

| 文件 | 大小 | 说明 |
|------|------|------|
| server.py | ~50 KB | 主服务器代码 |
| trace_db.py | ~20 KB | 追踪数据库模块 |
| trace.html | ~100 KB | Trace UI 前端 |
| trace.db | 变化 | 取决于请求数量 |
| docs/*.md | ~52 KB | 所有文档总和 |

## 🚀 快速导航

### 我想...

**安装和配置**
→ 查看 [docs/README.md](README.md)

**了解所有配置选项**
→ 查看 [docs/CONFIGURATION.md](CONFIGURATION.md)

**了解功能特性**
→ 查看 [docs/FEATURES.md](FEATURES.md)

**解决问题**
→ 查看 [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**优化性能**
→ 查看 [docs/PERFORMANCE.md](PERFORMANCE.md)

**开发新功能**
→ 查看 [docs/DEVELOPMENT.md](DEVELOPMENT.md)

**查看常见问题**
→ 查看 [docs/FAQ.md](FAQ.md)

---

**返回文档索引**: [INDEX.md](INDEX.md)
