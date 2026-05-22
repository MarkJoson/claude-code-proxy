# Anthropic API Proxy for Gemini & OpenAI Models 🔄

**Use Anthropic clients (like Claude Code) with Gemini, OpenAI, or direct Anthropic backends.** 🤝

A proxy server that lets you use Anthropic clients with Gemini, OpenAI, or Anthropic models themselves (a transparent proxy of sorts), all via LiteLLM. 🌉


![Anthropic API Proxy](pic.png)

## Quick Start ⚡

### Prerequisites

- OpenAI API key 🔑
- Google AI Studio (Gemini) API key (if using Google provider) 🔑
- Google Cloud Project with Vertex AI API enabled (if using Application Default Credentials for Gemini) ☁️
- [uv](https://github.com/astral-sh/uv) installed.

### Setup 🛠️

#### From source

1. **Clone this repository**:
   ```bash
   git clone https://github.com/1rgs/claude-code-proxy.git
   cd claude-code-proxy
   ```

2. **Install uv** (if you haven't already):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   *(`uv` will handle dependencies based on `pyproject.toml` when you run the server)*

3. **Configure Environment Variables**:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your API keys and model configurations:

   *   `ANTHROPIC_API_KEY`: (Optional) Needed only if proxying *to* Anthropic models.
   *   `OPENAI_API_KEY`: Your OpenAI API key (Required if using the default OpenAI preference or as fallback).
   *   `GEMINI_API_KEY`: Your Google AI Studio (Gemini) API key (Required if `PREFERRED_PROVIDER=google` and `USE_VERTEX_AUTH=true`).
   *   `USE_VERTEX_AUTH` (Optional): Set to `true` to use Application Default Credentials (ADC) will be used (no static API key required). Note: when USE_VERTEX_AUTH=true, you must configure `VERTEX_PROJECT` and `VERTEX_LOCATION`.
   *   `VERTEX_PROJECT` (Optional): Your Google Cloud Project ID (Required if `PREFERRED_PROVIDER=google` and `USE_VERTEX_AUTH=true`).
   *   `VERTEX_LOCATION` (Optional): The Google Cloud region for Vertex AI (e.g., `us-central1`) (Required if `PREFERRED_PROVIDER=google` and `USE_VERTEX_AUTH=true`).
   *   `PREFERRED_PROVIDER` (Optional): Set to `openai` (default), `google`, or `anthropic`. This determines the primary backend for mapping `haiku`/`sonnet`.
   *   `BIG_MODEL` (Optional): The model to map `sonnet` requests to. Defaults to `gpt-4.1` (if `PREFERRED_PROVIDER=openai`) or `gemini-2.5-pro-preview-03-25`. Ignored when `PREFERRED_PROVIDER=anthropic`.
   *   `SMALL_MODEL` (Optional): The model to map `haiku` requests to. Defaults to `gpt-4.1-mini` (if `PREFERRED_PROVIDER=openai`) or `gemini-2.0-flash`. Ignored when `PREFERRED_PROVIDER=anthropic`.

   **Mapping Logic:**
   - If `PREFERRED_PROVIDER=openai` (default), `haiku`/`sonnet` map to `SMALL_MODEL`/`BIG_MODEL` prefixed with `openai/`.
   - If `PREFERRED_PROVIDER=google`, `haiku`/`sonnet` map to `SMALL_MODEL`/`BIG_MODEL` prefixed with `gemini/` *if* those models are in the server's known `GEMINI_MODELS` list (otherwise falls back to OpenAI mapping).
   - If `PREFERRED_PROVIDER=anthropic`, `haiku`/`sonnet` requests are passed directly to Anthropic with the `anthropic/` prefix without remapping to different models.

4. **Run the server**:
   ```bash
   uv run uvicorn server:app --host 0.0.0.0 --port 8082 --reload
   ```
   *(`--reload` is optional, for development)*

#### Docker

If using docker, download the example environment file to `.env` and edit it as described above.
```bash
curl -O .env https://raw.githubusercontent.com/1rgs/claude-code-proxy/refs/heads/main/.env.example
```

Then, you can either start the container with [docker compose](https://docs.docker.com/compose/) (preferred):

```yml
services:
  proxy:
    image: ghcr.io/1rgs/claude-code-proxy:latest
    restart: unless-stopped
    env_file: .env
    ports:
      - 8082:8082
```

Or with a command:

```bash
docker run -d --env-file .env -p 8082:8082 ghcr.io/1rgs/claude-code-proxy:latest
```

### Using with Claude Code 🎮

1. **Install Claude Code** (if you haven't already):
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **Connect to your proxy**:
   ```bash
   ANTHROPIC_BASE_URL=http://localhost:8082 claude
   ```

   For trace analysis, prefer the launcher script because it starts the gateway if needed and uses `--setting-sources local` so user/global Claude settings do not override the local gateway:

   ```bash
   scripts/claude_trace_ui.sh --clear-trace
   ```

   For Qwen/OpenAI-compatible backends, configure the upstream endpoint and mapped models before launching:

   ```bash
   OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \
   OPENAI_API_KEY=sk-... \
   CC_TRACE_BIG_MODEL=qwen-plus \
   CC_TRACE_SMALL_MODEL=qwen-turbo \
   scripts/claude_trace_ui.sh --clear-trace
   ```

3. **That's it!** Your Claude Code client will now use the configured backend models through the proxy. 🎯

### Trace Gateway UI

This branch records every `/v1/messages` (and `/v1/messages/count_tokens`) call into a SQLite database (`cc_traces/trace.db`) and serves a per-session analysis UI from the same FastAPI app. After starting the proxy and pointing Claude Code at it, open:

```bash
http://localhost:8082/trace
```

Useful trace settings:

- `CC_TRACE_ENABLED=false` disables recording.
- `CC_TRACE_DIR=cc_traces` changes where `trace.db` is stored.
- `CC_TRACE_INCLUDE_SYSTEM_IN_PREFIX=true` includes system prompts as the first prefix-hash step. By default, only conversation messages form the prefix.

The UI is organised around the Claude Code session (`x-claude-code-session-id`). The left column lists sessions; the middle has four tabs and the right shows the detail of whatever you click:

- **请求列表 (Requests)** – every `/v1/messages` call in the session, with role badge (`titler` / `main` / `subagent` / `external`), advertised tools, message count, mapped model, status and timing.
- **历史链 (History chain)** – parent/child links discovered from the `prefix_hashes` of conversation history. Strict-prefix is preferred, and small tail-drift fallbacks (1–2 messages of async tool noise) are also linked.
- **Agent 层级 (Agent hierarchy)** – pairs each main turn's `Agent`/`Task` `tool_use` with the subsequent `tool_result`, then attaches the subagent's `/v1/messages` calls under that `agent_call`; continuation main turns chain back via `parent_trace_id`.
- **时间线 (Timeline)** – LLM request starts, LLM responses, response-side `tool_use` and observed `tool_result` events, ordered by timestamp.

Clicking any row or node opens the matching detail on the right. Requests have sub-tabs (概览 / 消息序列 / 响应 / 工具事件 / System / 原始 JSON). Tool events show their input preview and link to their partner (paired `tool_use`/`tool_result`). Agent calls show the request that launched them and every child subagent request.

The HTTP API (`/api/v2`) is documented by the routes themselves:

- `GET /api/v2/stats` – snapshot counts.
- `GET /api/v2/sessions` – session listing + stats.
- `GET /api/v2/sessions/{session_id}` – session header + member requests + agent calls.
- `GET /api/v2/sessions/{session_id}/timeline` – timeline events.
- `GET /api/v2/sessions/{session_id}/history` – history-chain forest.
- `GET /api/v2/sessions/{session_id}/agents` – agent hierarchy forest.
- `GET /api/v2/requests?session_id=&role_kind=&api=` – flat request listing.
- `GET /api/v2/requests/{trace_id}` – full request detail (raw body, converted LiteLLM body, response, messages, tool events, parent/children).
- `GET /api/v2/tool_events/{event_id}` – single tool event detail (with paired partner).
- `GET /api/v2/agent_calls/{agent_call_id}` – Agent/Task call detail.
- `DELETE /api/v2/traces` – truncate the database.

To clear the current trace file before a run, click **清空** in the UI or call:

```bash
curl -X DELETE http://127.0.0.1:8082/api/v2/traces
```

With the proxy already running, run the Claude Agent SDK client test with:

```bash
uv run --dev python test_claude_sdk_trace.py --base-url http://127.0.0.1:8082
uv run --dev python test_claude_sdk_trace.py --base-url http://127.0.0.1:8082 --scenario tool-project --max-tokens 512
uv run --dev python test_claude_sdk_trace.py --base-url http://127.0.0.1:8082 --scenario multi-task --turns 3 --max-tokens 96
```

These tests do not send `x-claude-code-session-id`, so they are bucketed under a derived `ext-<client>-<ua>-<date>` session row instead of being dropped.

## Model Mapping 🗺️

The proxy automatically maps Claude models to either OpenAI or Gemini models based on the configured model:

| Claude Model | Default Mapping | When BIG_MODEL/SMALL_MODEL is a Gemini model |
|--------------|--------------|---------------------------|
| haiku | openai/gpt-4o-mini | gemini/[model-name] |
| sonnet | openai/gpt-4o | gemini/[model-name] |

### Supported Models

#### OpenAI Models
The following OpenAI models are supported with automatic `openai/` prefix handling:
- o3-mini
- o1
- o1-mini
- o1-pro
- gpt-4.5-preview
- gpt-4o
- gpt-4o-audio-preview
- chatgpt-4o-latest
- gpt-4o-mini
- gpt-4o-mini-audio-preview
- gpt-4.1
- gpt-4.1-mini

#### Gemini Models
The following Gemini models are supported with automatic `gemini/` prefix handling:
- gemini-2.5-pro
- gemini-2.5-flash

### Model Prefix Handling
The proxy automatically adds the appropriate prefix to model names:
- OpenAI models get the `openai/` prefix
- Gemini models get the `gemini/` prefix
- The BIG_MODEL and SMALL_MODEL will get the appropriate prefix based on whether they're in the OpenAI or Gemini model lists

For example:
- `gpt-4o` becomes `openai/gpt-4o`
- `gemini-2.5-pro-preview-03-25` becomes `gemini/gemini-2.5-pro-preview-03-25`
- When BIG_MODEL is set to a Gemini model, Claude Sonnet will map to `gemini/[model-name]`

### Customizing Model Mapping

Control the mapping using environment variables in your `.env` file or directly:

**Example 1: Default (Use OpenAI)**
No changes needed in `.env` beyond API keys, or ensure:
```dotenv
OPENAI_API_KEY="your-openai-key"
GEMINI_API_KEY="your-google-key" # Needed if PREFERRED_PROVIDER=google
# PREFERRED_PROVIDER="openai" # Optional, it's the default
# BIG_MODEL="gpt-4.1" # Optional, it's the default
# SMALL_MODEL="gpt-4.1-mini" # Optional, it's the default
```

**Example 2a: Prefer Google (using GEMINI_API_KEY)**
```dotenv
GEMINI_API_KEY="your-google-key"
OPENAI_API_KEY="your-openai-key" # Needed for fallback
PREFERRED_PROVIDER="google"
# BIG_MODEL="gemini-2.5-pro" # Optional, it's the default for Google pref
# SMALL_MODEL="gemini-2.5-flash" # Optional, it's the default for Google pref
```

**Example 2b: Prefer Google (using Vertex AI with Application Default Credentials)**
```dotenv
OPENAI_API_KEY="your-openai-key" # Needed for fallback
PREFERRED_PROVIDER="google"
VERTEX_PROJECT="your-gcp-project-id"
VERTEX_LOCATION="us-central1"
USE_VERTEX_AUTH=true
# BIG_MODEL="gemini-2.5-pro" # Optional, it's the default for Google pref
# SMALL_MODEL="gemini-2.5-flash" # Optional, it's the default for Google pref
```

**Example 3: Use Direct Anthropic ("Just an Anthropic Proxy" Mode)**
```dotenv
ANTHROPIC_API_KEY="sk-ant-..."
PREFERRED_PROVIDER="anthropic"
# BIG_MODEL and SMALL_MODEL are ignored in this mode
# haiku/sonnet requests are passed directly to Anthropic models
```

*Use case: This mode enables you to use the proxy infrastructure (for logging, middleware, request/response processing, etc.) while still using actual Anthropic models rather than being forced to remap to OpenAI or Gemini.*

**Example 4: Use Specific OpenAI Models**
```dotenv
OPENAI_API_KEY="your-openai-key"
GEMINI_API_KEY="your-google-key"
PREFERRED_PROVIDER="openai"
BIG_MODEL="gpt-4o" # Example specific model
SMALL_MODEL="gpt-4o-mini" # Example specific model
```

## How It Works 🧩

This proxy works by:

1. **Receiving requests** in Anthropic's API format 📥
2. **Translating** the requests to OpenAI format via LiteLLM 🔄
3. **Sending** the translated request to OpenAI 📤
4. **Converting** the response back to Anthropic format 🔄
5. **Returning** the formatted response to the client ✅

The proxy handles both streaming and non-streaming responses, maintaining compatibility with all Claude clients. 🌊

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request. 🎁
