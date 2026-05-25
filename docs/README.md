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

