# Claude Code Proxy

**让 Claude Code 通过 Anthropic API 的接口，使用 OpenAI、Gemini 或 Anthropic 的模型。**

Claude Code（Anthropic 官方出品）只认一种"语言"——**Anthropic Messages API 格式**。但你可能想用其他公司的大模型（比如 OpenAI 的 GPT-4、Google 的 Gemini），这些模型说的是不同的"语言"——**OpenAI Chat Completions API 格式**。Claude Code Proxy 作为一个中间代理，帮你完成格式翻译、模型映射和请求追踪。

```
Claude Code  ──(Anthropic 格式)──▶  server.py  ──(OpenAI 格式)──▶  GPT-4 / Gemini
                                       │
                                       │  同时记录所有请求到数据库
                                       ▼
                                  trace.db (Trace UI 可查看)
```

> [!Important] 版本说明：Claude Code 当前新版本（ 2.1.153 之后） 与 Deepseek v4 pro 的接口并不兼容。在Claude Code新版本下增加了新的特性：一个消息体内可以出现多次system prompt。后续支持需要等待 Deepseek 官方的接口适配，或者在启动时增加 `--bare` 选项。

---

## 1. 为什么会有两种 LLM 请求格式

大语言模型的 API 格式并没有统一标准。目前业界主要有两套"方言"：

- **Anthropic Messages API**：Anthropic 设计，Claude Code / Claude SDK 使用。消息内容以 `content` 数组组织，文本、图片、工具调用、工具结果都是数组中的"块（block）"，类型由 `type` 字段区分。
- **OpenAI Chat Completions API**：OpenAI 设计，由于 ChatGPT 的先发优势和开发生态，这套格式已经成为事实上的行业标准——绝大多数第三方模型提供商（包括 Google Gemini 的兼容模式、阿里通义千问、DeepSeek 等）都选择兼容 OpenAI 格式。

### 1.1 OpenAI API 端点的特征与普及度

OpenAI 的 `/v1/chat/completions` 端点是目前最广泛兼容的 LLM 调用接口：

| 提供商 | 是否原生支持 OpenAI 格式 | 备注 |
|--------|--------------------------|------|
| OpenAI (GPT-4, GPT-4.1) | ✅ 原生 | 格式的制定者 |
| Google Gemini | ✅ 兼容模式 | 也提供原生 Gemini API |
| 阿里通义千问 (Qwen) | ✅ 兼容 | 通过 DashScope 提供 |
| DeepSeek | ✅ 兼容 | 同时提供 Anthropic 兼容端点 |
| 月之暗面 (Moonshot) | ✅ 兼容 | |
| 智谱 (GLM) | ✅ 兼容 | |
| 大多数国产模型 | ✅ 兼容 | OpenAI 格式是标配 |

一套 OpenAI 格式的代码，几乎可以调用所有主流模型。这也就是为什么 Claude Code Proxy 选择以 OpenAI 格式作为"中间语言"——先把 Anthropic 格式转成 OpenAI 格式，再由 LiteLLM 路由到任意提供商。

### 1.2 为什么 Claude Code 不能直接接入 OpenAI API 端点

Claude Code 是 Anthropic 官方出品的 CLI 工具，它的代码中**硬编码**了 Anthropic Messages API 的请求和响应格式：

- 它向 `$ANTHROPIC_BASE_URL/v1/messages` 发送 Anthropic 格式的请求
- 它期望收到 Anthropic 格式的 SSE 流式响应（`message_start` → `content_block_start` → `content_block_delta` → `content_block_stop` → `message_delta` → `message_stop`）
- 它使用 Anthropic 特有的数据结构：`tool_use` / `tool_result` 块、`thinking` 块等

如果你直接把 `ANTHROPIC_BASE_URL` 指向 OpenAI 的端点，OpenAI 不认识 Anthropic 格式，会直接报错。所以需要一个**格式翻译层**——这就是 `server.py` 做的事情。

### 1.3 Anthropic vs OpenAI：格式差异一览

**User 消息**
```
Anthropic:
{ role: "user",
  content: [
    { type: "text", text: "你好" },
    { type: "image", source: {...} },
    { type: "tool_result", tool_use_id: "xxx", content: "结果" }
  ]
}

OpenAI:
{ role: "user", content: "你好" },              ← 纯文本消息
{ role: "tool", tool_call_id: "xxx", content: "结果" }  ← 工具结果单独一条消息！
```

关键区别：Anthropic 的 `tool_result` 嵌在 user 消息的 content 数组里，而 OpenAI 的 `tool_result` 是一个**独立的消息**，role 为 `"tool"`。

**Assistant 消息（工具调用）**
```
Anthropic:
{ role: "assistant",
  content: [
    { type: "text", text: "我来帮你查..." },
    { type: "tool_use", id: "toolu_001", name: "search", input: {query: "..."} }
  ]
}

OpenAI:
{ role: "assistant",
  content: "我来帮你查...",
  tool_calls: [
    { id: "toolu_001", type: "function",
      function: { name: "search", arguments: '{"query":"..."}' }
    }
  ]
}
```

关键区别：Anthropic 的工具调用和文本都混在 `content` 数组里，而 OpenAI 把工具调用抽到独立的 `tool_calls` 字段，且参数是 JSON 字符串（不是对象）。

**SSE 流式事件格式**

| Anthropic SSE 事件 | OpenAI SSE 事件 |
|---------------------|-----------------|
| `message_start` |（无对应——直接从 delta 开始）|
| `content_block_start` |（无对应）|
| `content_block_delta` (text_delta) | `delta.content` |
| `content_block_delta` (input_json_delta) | `delta.tool_calls[].function.arguments` |
| `content_block_stop` |（无对应）|
| `message_delta` | `finish_reason` |
| `message_stop` | `[DONE]` |

可以看到，Anthropic 的流式协议比 OpenAI 的多了一层"content block"生命周期的概念（显式的 start / delta / stop），转换时需要人工管理这些事件的顺序。

---

## 2. 工作原理

**server.py 是一个"翻译官"**——接收 Claude Code 发来的请求（Anthropic 格式），翻译成 OpenAI/Gemini 能看懂的格式，发送给真正的 AI 模型，拿到回复后再翻译回 Anthropic 格式还给 Claude Code。

作为中转代理，Claude Code Proxy 还可以将请求记录到 SQLite 数据库，并提供 Trace UI 用于分析 Claude Code 的工作过程。

具体来说 server.py 帮你做三件事：

1. **格式转换**：Anthropic 格式 ↔ OpenAI 格式（或直通模式下原样转发 Anthropic 格式）
2. **模型映射**：把 `claude-sonnet` 这样的名字自动映射成你配置的实际模型（比如 `gpt-4.1`）
3. **请求追踪**：把所有请求记录到数据库，提供可视化 UI 查看历史和调用链

关键依赖：

| 依赖 | 作用 |
|------|------|
| **FastAPI** | Web 框架，处理 HTTP 请求/响应 |
| **LiteLLM** | 统一 LLM 调用接口——用同一套代码调用 OpenAI、Gemini、Anthropic 等 |
| **httpx** | HTTP 客户端——在直通模式下直接向 Anthropic API 发请求 |

---

## 3. 快速开始

### 3.1 环境准备

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) 包管理器
- 至少一个上游模型的 API Key（OpenAI / Gemini / Anthropic）

### 3.2 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/1rgs/claude-code-proxy.git
cd claude-code-proxy

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key 和模型偏好

# 3. 启动服务（基本启动）
uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

### 3.3 启动选项

所有配置都可以通过环境变量传入，无需修改 `.env` 文件。以下是常用组合：

**基础启动（使用 .env 中的配置）：**
```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

**关闭追踪记录（减少磁盘写入）：**
```bash
CC_TRACE_ENABLED=false uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

**指定追踪数据库存放目录：**
```bash
CC_TRACE_DIR=./traces uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

**测试模式：不调用真实模型，所有请求返回假回复（适合调试 Trace UI，不产生 API 费用）：**
```bash
CC_TRACE_ECHO_ONLY=true uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

**多 worker 生产部署 + 自定义端口：**
```bash
PORT=9090 WORKERS=8 CC_TRACE_DIR=./prod_traces uv run uvicorn server:app --host 0.0.0.0 --port 9090 --workers 8
```

**追踪相关环境变量一览：**

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CC_TRACE_ENABLED` | 是否开启请求追踪记录 | `true` |
| `CC_TRACE_DIR` | 追踪数据库（trace.db）存放目录 | 项目根目录 |
| `CC_TRACE_ECHO_ONLY` | 测试模式：不调模型，返回假回复 | `false` |
| `CC_TRACE_INCLUDE_SYSTEM_IN_PREFIX` | system prompt 是否参与前缀哈希 | `false` |

> **提示**：`python server.py --trace-disabled` 等价于 `CC_TRACE_ENABLED=false`。如果用 `python server.py` 启动，还支持 `--help` 查看完整的 uvicorn 参数说明。

### 3.4 配置 Claude Code

```bash
ANTHROPIC_BASE_URL=http://localhost:8082 claude
```

或者使用项目自带的启动脚本（会自动管理代理进程和追踪清理）：

```bash
scripts/claude_trace_ui.sh --clear-trace
```

这里提供一个 Claude 的 settings.json:
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8082",
    "ANTHROPIC_AUTH_TOKEN": "sk-1234",
    "CLAUDE_CODE_EFFORT_LEVEL": "max",
    "NODE_TLS_REJECT_UNAUTHORIZED": "0",
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  },
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(npm install)",
      "Bash(npm run dev)",
      "Bash(npm run build)",
      "Bash(npm run test:*)",
      "Bash(pnpm install)",
      "Bash(pnpm dev)",
      "Bash(pnpm build)",
      "Bash(pnpm test:*)",
      "Bash(yarn install)",
      "Bash(yarn dev)",
      "Bash(yarn build)",
      "Bash(yarn test:*)",
      "Bash(pytest:*)",
      "Bash(python:*)",
      "Bash(pip install:*)",
      "Read(~/.zshrc)",
      "Read(~/.bashrc)",
      "Read(./package.json)",
      "Read(./tsconfig.json)",
      "Read(./pyproject.toml)",
      "Read(./README.md)",
      "Edit(./src/**)",
      "Edit(./app/**)",
      "Edit(./pages/**)",
      "Edit(./components/**)",
      "Edit(./lib/**)",
      "Edit(./tests/**)",
      "Edit(./README.md)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(./config/credentials.json)",
      "Read(~/.ssh/**)",
      "Read(~/.aws/**)",
      "Read(~/.config/gcloud/**)",
      "Read(~/.npmrc)",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(rm -rf /)",
      "Bash(sudo:*)",
      "Bash(docker login:*)",
      "Bash(kubectl config:*)"
    ]
  },
  "cleanupPeriodDays": 20,
  "includeCoAuthoredBy": false,
  "forceLoginMethod": "console"
}
```

### 3.5 核心环境变量

所有环境变量详见 [.env.example](.env.example)，这里列出最关键的几个：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `GEMINI_API_KEY` | Gemini API Key | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key（直通模式用） | - |
| `PREFERRED_PROVIDER` | 首选提供商：`openai` / `google` / `anthropic` | `openai` |
| `BIG_MODEL` | 映射 Sonnet 的实际模型 | `gpt-4.1` |
| `SMALL_MODEL` | 映射 Haiku 的实际模型 | `gpt-4.1-mini` |
| `OPENAI_BASE_URL` | OpenAI 兼容 API 地址（用第三方/国内模型时修改） | `https://api.openai.com/v1` |
| `ANTHROPIC_BASE_URL` | Anthropic API 地址（直通模式用，也可指向 DeepSeek 等兼容端点） | `https://api.anthropic.com` |
| `PORT` | 服务端口 | `8082` |

**模型映射规则：**

| Claude Code 请求的模型 | `PREFERRED_PROVIDER=openai` | `PREFERRED_PROVIDER=google` | `PREFERRED_PROVIDER=anthropic` |
|------------------------|-----------------------------|-----------------------------|-------------------------------|
| 含 `haiku` | `openai/SMALL_MODEL` | `gemini/SMALL_MODEL` | 不映射（直通） |
| 含 `sonnet` | `openai/BIG_MODEL` | `gemini/BIG_MODEL` | 不映射（直通） |
| 其他 `claude-*`（如 opus） | `openai/BIG_MODEL` | `gemini/BIG_MODEL` | 不映射（直通） |

### 3.6 常见使用场景速查

**场景 1：用 OpenAI GPT 替代 Claude（最常用）**
```bash
PREFERRED_PROVIDER=openai
OPENAI_API_KEY=sk-...
# 默认用 OpenAI 官方，一般不需要改；用代理/中转时替换
OPENAI_BASE_URL=https://api.openai.com/v1
BIG_MODEL=gpt-4.1
SMALL_MODEL=gpt-4.1-mini
```

**场景 2：用 Google Gemini 替代 Claude（API Key 方式）**
```bash
PREFERRED_PROVIDER=google
GEMINI_API_KEY=your-google-key
BIG_MODEL=gemini-2.5-pro
SMALL_MODEL=gemini-2.5-flash
```

**场景 3：用 Google Gemini + Vertex AI（ADC 方式）**
```bash
PREFERRED_PROVIDER=google
USE_VERTEX_AUTH=true
VERTEX_PROJECT=your-gcp-project-id
VERTEX_LOCATION=us-central1
BIG_MODEL=gemini-2.5-pro
SMALL_MODEL=gemini-2.5-flash
```

**场景 4：纯 Anthropic 代理（用真 Claude，只做追踪记录）**
```bash
PREFERRED_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
# 默认连 Anthropic 官方；也可指向 DeepSeek 的 Anthropic 兼容端点:
# ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_BASE_URL=https://api.anthropic.com
# BIG_MODEL / SMALL_MODEL 会被忽略
```

**场景 5：用阿里云百炼的通义千问（Qwen）**
```bash
PREFERRED_PROVIDER=openai
OPENAI_API_KEY=sk-你的阿里云key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BIG_MODEL=qwen-plus
SMALL_MODEL=qwen-turbo
```

**场景 6：用 DeepSeek**
```bash
PREFERRED_PROVIDER=openai
OPENAI_API_KEY=sk-你的deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com
BIG_MODEL=deepseek-chat
SMALL_MODEL=deepseek-chat
```

### 3.7 Docker 部署

```bash
docker run -d --env-file .env -p 8082:8082 ghcr.io/1rgs/claude-code-proxy:latest
```

---

## 4. API 接口

`/v1/messages` 是对外提供服务的核心端点，Claude Code 通过它接入代理。代理根据模型前缀将请求转换并转发到上游。

```
                          ┌─────────────────────────────┐
                          │         server.py            │
                          │                              │
  Claude Code ──────────▶ │  POST /v1/messages           │
  (Anthropic 格式)        │  POST /v1/messages/count_    │──────▶  GPT-4
                          │       tokens                 │   (通过 LiteLLM)
                          │                              │──────▶  Gemini
                          │  GET  /trace (Trace UI)      │   (通过 LiteLLM)
                          │  GET  /api/v2/* (API)        │
                          │                              │──────▶  Anthropic
                          │  trace_db.py ─── trace.db    │   (直通模式)
                          └─────────────────────────────┘
```

### 完整端点列表

**对外服务端点（供 Claude Code 使用）：**

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/v1/messages` | **核心**——处理聊天请求，支持流式和非流式 |
| `POST` | `/v1/messages/count_tokens` | 计算消息的 token 数量 |
| `GET` | `/` | 健康检查 |

**Trace UI 和数据分析端点：**

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/trace` | Trace 可视化 UI 页面 |
| `GET` | `/api/v2/stats` | 请求统计概览 |
| `GET` | `/api/v2/sessions` | 列出所有会话 |
| `GET` | `/api/v2/sessions/{id}` | 查看某个会话详情 |
| `GET` | `/api/v2/sessions/{id}/timeline` | 会话时间线（按时间排列的事件） |
| `GET` | `/api/v2/sessions/{id}/history` | 会话历史链（对话如何一路延续） |
| `GET` | `/api/v2/sessions/{id}/agents` | Agent 层级树（主 Agent 与子 Agent 关系） |
| `POST` | `/api/v2/sessions/{id}/archive` | 归档会话 |
| `POST` | `/api/v2/sessions/{id}/unarchive` | 取消归档 |
| `GET` | `/api/v2/requests` | 列出所有请求（可按 session/role/api 筛选） |
| `GET` | `/api/v2/requests/{id}` | 查看某个请求的完整详情 |
| `GET` | `/api/v2/tool_events/{id}` | 查看工具调用事件 |
| `GET` | `/api/v2/agent_calls/{id}` | 查看 Agent 调用详情 |
| `GET` | `/api/v2/trace/enabled` | 查看追踪功能是否开启 |
| `POST` | `/api/v2/trace/enabled` | 开启/关闭追踪功能 |
| `DELETE` | `/api/v2/traces` | 清空所有追踪数据 |

### Trace UI

服务启动后访问 `http://localhost:8082/trace`，提供四个分析视图：

- **请求列表**：每次 API 调用的模型映射、工具数量、状态码、耗时
- **历史链**：通过 `prefix_hashes` 自动发现对话的父子延续关系
- **Agent 层级**：主 Agent 的工具调用 → 子 Agent 请求的归属关系树
- **时间线**：LLM 请求开始/响应/工具调用事件按时间轴排列

---

## 5. 一个请求的完整旅程

当 Claude Code 说"帮我写一段代码"，`server.py` 内部的处理流程：

```
第 1 步：接收请求
┌──────────────────────────────────────────────────────────┐
│  Claude Code 发送 POST /v1/messages                      │
│  请求体是 Anthropic 格式，包含 messages、model、tools 等  │
│  例如: { model: "claude-sonnet-4-20250514",              │
│          messages: [{role:"user", content:"写段代码"}] }  │
└────────────────────┬─────────────────────────────────────┘
                     ▼
第 2 步：模型映射
┌──────────────────────────────────────────────────────────┐
│  Pydantic 的 @field_validator 自动触发                    │
│  "claude-sonnet" → 根据 PREFERRED_PROVIDER 映射:         │
│    - 如果是 openai  → "openai/gpt-4.1"                   │
│    - 如果是 google  → "gemini/gemini-2.5-pro"             │
│    - 如果是 anthropic → "anthropic/claude-sonnet-..."     │
└────────────────────┬─────────────────────────────────────┘
                     ▼
第 3 步：选择处理路径
┌──────────────────────────────────────────────────────────┐
│  检查 model 是否以 "anthropic/" 开头:                     │
│    ✅ 是 → 走直通模式（第 4a 步）                        │
│    ❌ 否 → 走 LiteLLM 转换模式（第 4b 步）              │
└────────────────────┬─────────────────────────────────────┘
                     ▼
第 4a 步：Anthropic 直通模式
┌──────────────────────────────────────────────────────────┐
│  不经过 LiteLLM 转换，直接把原始请求转发给 Anthropic API  │
│  完整保留 Anthropic 特性（thinking block 等）             │
└──────────────────────────────────────────────────────────┘

第 4b 步：LiteLLM 转换模式
┌──────────────────────────────────────────────────────────┐
│  1. convert_anthropic_to_litellm()                       │
│     Anthropic 格式 → OpenAI 格式                          │
│     - System prompt 提取（取最长的一条）                    │
│     - 消息块重组（tool_result → role:"tool" 消息）         │
│     - 工具定义转换（Anthropic tools → OpenAI functions）    │
│                                                          │
│  2. litellm.acompletion() 发送给真正的模型                 │
│     带上对应的 API Key                                    │
│                                                          │
│  3. convert_litellm_to_anthropic()                       │
│     OpenAI 格式 → Anthropic 格式                          │
│     - finish_reason "stop" → "end_turn"                  │
│     - tool_calls → tool_use 块                           │
└────────────────────┬─────────────────────────────────────┘
                     ▼
第 5 步：流式 vs 非流式
┌──────────────────────────────────────────────────────────┐
│  stream=true  → StreamingResponse (SSE 流，逐块转换)      │
│  stream=false → JSONResponse (等待完整回复后一次性返回)    │
└────────────────────┬─────────────────────────────────────┘
                     ▼
第 6 步：追踪记录
┌──────────────────────────────────────────────────────────┐
│  无论成功还是失败，记录到 trace.db:                        │
│    - trace_request_started()                             │
│    - trace_request_completed()  /  trace_request_failed()│
└──────────────────────────────────────────────────────────┘
```

---

## 6. 流式 vs 非流式

| 模式 | 条件 | 特点 |
|------|------|------|
| **流式（Streaming）** | `stream=true`（默认） | 模型一边生成一边返回，打字机效果；响应快 |
| **非流式（Non-streaming）** | `stream=false` | 等模型生成完，一次性返回完整 JSON；响应慢 |

流式处理（`handle_streaming()` 函数）是整个 `server.py` 中最复杂的部分，因为它需要：

1. **逐块接收** OpenAI 的 SSE 流
2. **实时转换**每个 chunk 为 Anthropic 的 SSE 事件格式
3. **处理混合内容**——模型可能在同一段流中交替输出文本和工具调用
4. **管理 content block 生命周期**——Anthropic 的 SSE 协议有显式的 `content_block_start` → `content_block_delta` → `content_block_stop` 状态机

**流式事件格式对比：**

```
OpenAI SSE:                     Anthropic SSE:
                                event: message_start
data: {"choices":[{"delta":     data: {...}
       {"content":"你"}}]}      event: content_block_start
                                data: {"index":0, ...}
data: {"choices":[{"delta":     event: content_block_delta
       {"content":"好"}}]}      data: {"index":0,
                                       "delta":{"type":"text_delta",
data: {"choices":[{                     "text":"你好"}}
       "finish_reason":"stop"}]}event: content_block_stop
data: [DONE]                    data: {"index":0}
                                event: message_delta
                                data: {...}
                                event: message_stop
                                data: {...}
                                data: [DONE]
```

---

## 7. 直通模式

### 为什么需要直通模式？

LiteLLM 在 Anthropic ↔ OpenAI 格式转换时，有些 Anthropic 特有功能会**丢失或变形**：
- **Thinking blocks**（思考块）—— Anthropic 特有，OpenAI 不支持
- **Server-side tools**——服务器端工具
- **某些 tool_use / tool_result 的精确语义**

当 `PREFERRED_PROVIDER=anthropic`（即你确实在用 Claude 模型本身）时，不需要经过 LiteLLM 转换——直接把原始请求转发给 Anthropic API 即可。

### 直通模式的处理流程

```
请求进来（model 以 anthropic/ 开头）
  │
  ├─ 去掉 "anthropic/" 前缀（上游 API 不需要这个前缀）
  ├─ 重建请求体：替换 model 为去除前缀后的名称
  ├─ 清理 headers：移除不需要转发的头（host、content-length 等），
  │   替换为代理自己的 x-api-key 和 anthropic-version
  ├─ 直接 POST 到 ANTHROPIC_BASE_URL/v1/messages
  │
  └─ 流式：逐字节转发 SSE 事件（同时解析事件重建响应用于追踪）
     非流式：等待完整响应后返回 JSON
```

### 与 LiteLLM 模式的对比

| 维度 | LiteLLM 模式 | Anthropic 直通模式 |
|------|-------------|-------------------|
| 适用场景 | 用 GPT/Gemini 替代 Claude | 用真正的 Claude 模型 |
| 格式转换 | 需要 Anthropic ↔ OpenAI 转换 | 不需要，原样转发 |
| Thinking block | 不支持 | 完整保留 |
| 请求追踪 | ✅ 支持 | ✅ 支持 |
| 自动重试 | ✅ 支持（指数退避） | ❌ 没有（直接透传上游错误） |
| 多提供商 | ✅ 可路由到任意 LiteLLM 支持的提供商 | ❌ 仅 Anthropic 兼容端点 |

---

## 8. 请求追踪系统

### 追踪了什么？

每一次 `/v1/messages` 和 `/v1/messages/count_tokens` 请求都记录到 SQLite 数据库（`trace.db`），包含：

- 请求原始体（Claude Code 发来的 JSON）
- 转换后请求（发送给上游模型的 JSON）
- 响应体（上游模型返回的内容）
- 模型映射关系（原始模型 → 实际调用模型）
- 时间戳和耗时
- 成功/失败状态
- 会话 ID（来自 `x-claude-code-session-id` 请求头）
- 工具调用事件（tool_use / tool_result 配对）

### 追踪配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `CC_TRACE_ENABLED` | 是否开启追踪记录 | `true` |
| `CC_TRACE_DIR` | 追踪数据库存放目录 | 项目根目录 |
| `CC_TRACE_ECHO_ONLY` | 测试模式：不调用真实模型，返回假回复 | `false` |
| `CC_TRACE_INCLUDE_SYSTEM_IN_PREFIX` | system prompt 是否参与前缀哈希 | `false` |

- 启动参数 `--trace-disabled` 可以在启动时关闭追踪记录
- 通过 API `DELETE /api/v2/traces` 或 UI 中的"清空"按钮可以清除所有记录

### 性能指标采集

当上游为 OpenAI 兼容端点（如 vLLM）且请求为流式时，Proxy 会自动记录每个 `/v1/messages` 请求的推理性能指标，写入 `requests.extra_json`：

| 指标 | 字段 | 说明 |
|------|------|------|
| `prefill_tokens` | prompt 总 token 数 | 来自上游 usage 的 `prompt_tokens` |
| `cached_tokens` | 前缀缓存命中 token 数 | 来自 `prompt_tokens_details.cached_tokens` |
| `output_tokens` | 生成 token 总数 | 来自 `completion_tokens` |
| `decode_tokens` | 同 `output_tokens` | 便于后续按 decode 阶段统计 |
| `ttft_ms` | Time To First Token | 请求发出到首个内容 token 的毫秒数 |
| `prefill_ms` | 同 `ttft_ms` | prefill 阶段 wall-clock 耗时 |
| `prefill_toks_per_sec` | prefill 吞吐 | `prefill_tokens / prefill_ms * 1000` |
| `decode_ms` | decode 阶段耗时 | 首 token 到末 token 的毫秒数 |
| `tpot_ms` | Time Per Output Token | `decode_ms / (output_tokens - 1)` |
| `decode_toks_per_sec` | decode 吞吐 | `(output_tokens - 1) / decode_ms * 1000` |

导出与分析：

```bash
# 打印汇总
python scripts/export_perf.py --db cc_traces/trace.db

# 导出逐请求 JSONL / CSV
python scripts/export_perf.py --db cc_traces/trace.db --output perf.jsonl --csv perf.csv

# 导出逐任务统计 CSV（含 prefill/output 的 min/avg/max）
python scripts/export_perf.py --db cc_traces/trace.db --tasks-csv tasks.csv

# 生成交互式 HTML 看板（推荐）
python scripts/export_dashboard.py --db cc_traces/trace.db --output perf_dashboard.html
```

`export_perf.py` 与 `export_dashboard.py` 同时兼容历史轨迹：没有 `extra_json.perf` 的记录会自动从 `response_usage_json` 提取 prefill/output 长度和缓存命中信息，TTFT/TPOT 等流式阶段指标会留空。

HTML 看板特性：

- 以「任务（task / session）」为核心：每个任务独立统计、独立查看，不会混在一起
- 任务列表卡片：一眼看到每个任务的请求数、总耗时、**prefill/output 的 min/avg/max**、缓存命中率、平均 TTFT/TPOT
- 点击任意任务进入单任务视图：TTFT vs prefill、TPOT 分布、该任务各轮次的 token/缓存/延迟曲线
- 全局视图：所有任务的横向对比（总耗时、总 token、平均 TTFT/TPOT）
- 完全离线：所有数据嵌入单个 HTML，用浏览器直接打开即可
- 深色 / 浅色主题切换
- 按任务、模型、role_kind 实时筛选
- 模型对比卡片
- 原始数据表格（前 500 条）

---

## 9. 代码结构速览

```
server.py（约 2250 行）

第 1-45 行   │ 导入语句（含 trace_db 模块）
第 47-115 行 │ 日志系统配置（过滤器、颜色格式化）
第 116 行    │ app = FastAPI()
第 118-156 行│ 环境变量读取 + TRACE_ECHO_ONLY 开关
第 158-201 行│ 模型列表（OPENAI_MODELS / GEMINI_MODELS）+ Gemini Schema 清理
第 203-339 行│ 📦 Pydantic 数据模型（MessagesRequest 含模型映射验证器）
第 344-410 行│ TokenCountRequest + TokenCountResponse
第 436-496 行│ 工具函数（token 估算、模型信息查询、Echo 响应构建）
第 498-518 行│ HTTP 中间件（请求日志）
第 522-565 行│ parse_tool_result_content() —— 工具结果内容解析
──────────────────────────────────────────────────
第 566-783 行│ 🔄 convert_anthropic_to_litellm()
             │   Anthropic 请求 → OpenAI 格式
第 784-944 行│ 🔄 convert_litellm_to_anthropic()
             │   OpenAI 响应 → Anthropic 格式
第 946-1318 行│ 🌊 handle_streaming()
             │   流式响应实时转换（最复杂的函数）
──────────────────────────────────────────────────
第 1320-1689 行│ ⭐ POST /v1/messages 主处理函数
              │   自动重试、流式/非流式分发、错误处理
第 1692-1943 行│ 🔀 Anthropic 直通模式
              │   _handle_anthropic_passthrough() + _stream_anthropic_passthrough()
第 1946-2059 行│ POST /v1/messages/count_tokens
第 2061-2167 行│ 其他 API 端点（sessions / requests / trace / stats）
──────────────────────────────────────────────────
第 2169-2212 行│ log_request_beautifully() —— 美化日志输出
第 2214-2254 行│ __main__ 启动入口（uvicorn 参数配置）
```

---

## 10. 调试技巧

### 10.1 看懂日志颜色标记

```python
🔴 MIDDLEWARE     # 中间件层——请求进入/离开
🔵 ENDPOINT ENTRY  # 进入 /v1/messages 处理函数
🟡 STREAMING / NON-STREAMING  # 流式/非流式模式
🟢 UPSTREAM CALL   # 真正调用上游模型
📌 MODEL MAPPING   # 模型名称映射
📋 MODEL VALIDATION # 模型验证
⚠️  警告
⏳ 重试中...
```

### 10.2 关键日志搜索词

| 想排查什么 | 搜索关键词 |
|-----------|-----------|
| 请求是否到达 | `MIDDLEWARE: Incoming request` |
| 模型映射是否正确 | `MODEL MAPPING` |
| 上游调用是否成功 | `UPSTREAM CALL SUCCESS` |
| 上游调用失败原因 | `UPSTREAM CALL START` 附近的异常 |
| 流式处理异常 | `Error processing chunk` 或 `Error in streaming` |
| 格式转换异常 | `Error converting response` |
| 直通模式上游错误 | `passthrough upstream error` |

### 10.3 快速验证服务是否正常

```bash
# 健康检查
curl http://localhost:8082/

# 查看统计
curl http://localhost:8082/api/v2/stats

# 查看追踪开关
curl http://localhost:8082/api/v2/trace/enabled

# 查看最近会话
curl http://localhost:8082/api/v2/sessions
```

### 10.4 开启更详细的日志

在代码中将日志级别从 `WARNING` 改为 `DEBUG`：

```python
# server.py 第 61 行
logging.basicConfig(
    level=logging.DEBUG,  # 原来是 WARNING
    ...
)
```

---

## 11. 常见问题 Q&A

### Q1: 什么时候走直通模式，什么时候走 LiteLLM 转换？

看模型名前缀：
- `anthropic/claude-sonnet-4-20250514` → 直通模式（`PREFERRED_PROVIDER=anthropic`）
- `openai/gpt-4.1` → LiteLLM 转换模式
- `gemini/gemini-2.5-flash` → LiteLLM 转换模式

### Q2: 流式和非流式能同时支持吗？

可以。`server.py` 根据客户端请求中的 `stream` 字段自动选择处理方式。Claude Code 默认使用流式。

### Q3: 追踪数据存在哪里？

默认在当前目录的 `trace.db`（SQLite 文件）。可以通过 `CC_TRACE_DIR` 修改位置，通过 `CC_TRACE_ENABLED=false` 关闭记录。

### Q4: 遇到 Claude 版本更新后上游返回 422 错误怎么办？

Anthropic 有时会更新 API 的 `anthropic-version` 头。检查 `.env` 中 `ANTHROPIC_BASE_URL` 是否正确，以及直通模式下的 `anthropic-version` 请求头是否被正确转发（默认转发客户端发来的版本号）。

如果使用的是 OpenAI 兼容的第三方端点，检查 `OPENAI_BASE_URL` 配置是否正确——某些第三方端点的路径不完全兼容 `/v1/chat/completions`。

### Q5: 如何查看某次请求的详细内容？

访问 `http://localhost:8082/trace`，点击左侧会话列表中的会话，中间会列出该会话的所有请求。点击任意请求行，右侧会展开详情面板，包含：
- **概览**：请求摘要（模型、状态码、耗时等）
- **消息序列**：完整的对话消息链
- **响应**：模型返回的完整响应
- **工具事件**：该请求关联的工具调用和结果
- **原始 JSON**：未经转换的原始请求体

也可以通过 API 查看：`GET /api/v2/requests/{trace_id}`。

### Q6: 为什么不直接用 OpenAI 的 SDK？

Claude Code 是 Anthropic 的官方 CLI 工具，它的代码库中大量使用了 Anthropic 特有的数据结构（`tool_use`、`tool_result`、`thinking` 块等）。如果直接修改 Claude Code 的源码来支持 OpenAI 格式，维护成本极高——每次 Claude Code 更新都需要重新适配。

代理方案的好处是**对 Claude Code 完全透明**：Claude Code 以为自己连的是 Anthropic 服务器，实际上后端可以是任何模型。

### Q7: 如何选择合适的 WORKERS 数量？

- **调试/开发**：`WORKERS=1`，方便打断点和看日志
- **个人使用**：`WORKERS=2~4`，足够日常编码
- **团队共用**：`WORKERS=8~16`，避免排队

每个 worker 是独立进程，多 worker 之间不共享内存（trace.db 通过 SQLite 的 WAL 模式支持并发写入）。

### Q8: TRACE_ECHO_ONLY 模式有什么用？

设置 `CC_TRACE_ECHO_ONLY=true` 后，代理不会真正调用 AI 模型，而是直接返回一个假的回复 `"TRACE_GATEWAY_ECHO_OK"`。这个模式用于：
- 测试 Trace UI 功能而不消耗 API 额度
- 验证请求格式转换是否正确（看 trace.db 中的记录）
- 调试前端展示逻辑

---

## 12. 开发与贡献

### 运行测试

```bash
# 安装开发依赖
uv sync --dev

# 运行 Claude SDK 集成测试
uv run python test_claude_sdk_trace.py --base-url http://127.0.0.1:8082
uv run python test_claude_sdk_trace.py --base-url http://127.0.0.1:8082 --scenario tool-project --max-tokens 512
uv run python test_claude_sdk_trace.py --base-url http://127.0.0.1:8082 --scenario multi-task --turns 3 --max-tokens 96
```

### 项目结构

```
claude-code-proxy/
├── server.py          # 主程序（FastAPI 应用 + 格式转换 + 路由）
├── trace_db.py        # 追踪数据库模块（SQLite 操作）
├── static/trace.html  # Trace UI 前端页面
├── scripts/           # 辅助脚本
├── tests/             # 测试文件
└── docs/              # 补充文档（开发指南等）
```

---

## License

MIT
