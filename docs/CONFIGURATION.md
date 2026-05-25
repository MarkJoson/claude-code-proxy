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

