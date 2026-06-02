# 使用示例：模型上下文信息

## 快速开始

### 1. 配置环境变量

编辑 `.env` 文件：

```bash
# 使用 OpenAI 作为后端
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，使用自定义端点
```

### 2. 启动代理

```bash
python3 server.py
```

### 3. 发送请求

```bash
curl -X POST http://localhost:8082/v1/messages \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### 4. 查看响应

响应将包含 `model_info` 字段：

```json
{
  "id": "msg_abc123",
  "model": "claude-3-5-sonnet-20241022",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello! How can I help you today?"
    }
  ],
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 15,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0
  },
  "model_info": {
    "max_input_tokens": 128000,
    "max_output_tokens": 16384
  }
}
```

## 不同提供商的对比

### OpenAI (gpt-4o)

```json
"model_info": {
  "max_input_tokens": 128000,
  "max_output_tokens": 16384
}
```

### OpenAI (gpt-4)

```json
"model_info": {
  "max_input_tokens": 8192,
  "max_output_tokens": 4096
}
```

### Gemini (gemini-2.5-pro)

```json
"model_info": {
  "max_input_tokens": 1000000,
  "max_output_tokens": 8192
}
```

### Anthropic (claude-3-opus-20240229)

```json
"model_info": {
  "max_input_tokens": 200000,
  "max_output_tokens": 4096
}
```

## 在 Claude Code 中使用

配置 Claude Code 使用代理：

```bash
# 设置 API 端点
export ANTHROPIC_API_URL=http://localhost:8082

# 或者在 Claude Code 配置中设置
claude config set api_url http://localhost:8082
```

现在 Claude Code 会：
1. 发送请求到代理（使用 Claude 模型名）
2. 代理将其映射到配置的模型（如 gpt-4o）
3. 响应中包含实际模型的上下文窗口信息
4. Claude Code 可以根据实际限制调整行为

## Python 客户端示例

```python
import anthropic

# 配置客户端使用代理
client = anthropic.Anthropic(
    api_key="dummy",  # 代理会使用自己的 API key
    base_url="http://localhost:8082"
)

# 发送请求
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

# 检查模型信息
if hasattr(response, 'model_info') and response.model_info:
    print(f"实际模型上下文限制:")
    print(f"  最大输入: {response.model_info.max_input_tokens} tokens")
    print(f"  最大输出: {response.model_info.max_output_tokens} tokens")
else:
    print("响应中没有模型信息")
```

## 流式响应示例

```python
import anthropic

client = anthropic.Anthropic(
    api_key="dummy",
    base_url="http://localhost:8082"
)

# 流式请求
with client.messages.stream(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Count to 10"}
    ]
) as stream:
    # 第一个事件是 message_start，包含 model_info
    for event in stream:
        if event.type == "message_start":
            message = event.message
            if hasattr(message, 'model_info') and message.model_info:
                print(f"模型上下文限制:")
                print(f"  输入: {message.model_info.max_input_tokens}")
                print(f"  输出: {message.model_info.max_output_tokens}")
            break
    
    # 继续处理其他事件
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

## 故障排除

### model_info 为 null

如果 `model_info` 为 `null`，可能的原因：

1. **模型未在 litellm 中注册**
   - 检查日志：`Could not get model info for {model_name}`
   - 解决方案：使用 litellm 支持的模型名

2. **自定义模型名**
   - 如果使用自定义模型名，litellm 可能无法识别
   - 解决方案：在 `.env` 中使用标准模型名

### 验证功能

运行测试脚本：

```bash
python3 test_model_info.py
```

预期输出：

```
============================================================
Testing model_info in proxy responses
============================================================
Testing non-streaming response...
✓ Response received
  Model: claude-3-5-sonnet-20241022
✓ model_info present:
  max_input_tokens: 128000
  max_output_tokens: 16384

Testing streaming response...
✓ Streaming response started
✓ model_info present in message_start:
  max_input_tokens: 128000
  max_output_tokens: 16384

============================================================
Tests completed!
============================================================
```

## 环境变量参考

```bash
# 提供商选择
PREFERRED_PROVIDER=openai  # openai, google, anthropic

# 模型映射
BIG_MODEL=gpt-4o           # Sonnet/Opus 映射到此模型
SMALL_MODEL=gpt-4o-mini    # Haiku 映射到此模型

# 全局默认上下文限制（可选）
# 当 litellm 无法识别模型时使用这些默认值
DEFAULT_MAX_INPUT_TOKENS=128000
DEFAULT_MAX_OUTPUT_TOKENS=16384

# API Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...

# OpenAI 自定义端点（可选）
OPENAI_BASE_URL=https://your-endpoint.com/v1

# Vertex AI 配置（使用 Gemini 时）
VERTEX_PROJECT=your-project
VERTEX_LOCATION=us-central1
USE_VERTEX_AUTH=true
```

## 全局默认值说明

### 何时使用

当你使用的模型不在 litellm 的内置数据库中时（例如自定义模型、私有部署的模型），可以设置全局默认值：

```bash
DEFAULT_MAX_INPUT_TOKENS=100000
DEFAULT_MAX_OUTPUT_TOKENS=8192
```

### 优先级

1. **litellm 内置数据**（优先）- 如果模型在 litellm 数据库中，使用内置数据
2. **环境变量默认值**（备用）- 如果模型未知，使用环境变量
3. **返回 null**（最后）- 如果都没有，`model_info` 为 `null`

### 示例

```bash
# .env 配置
PREFERRED_PROVIDER=openai
BIG_MODEL=my-custom-gpt-model
DEFAULT_MAX_INPUT_TOKENS=150000
DEFAULT_MAX_OUTPUT_TOKENS=10000
```

当请求 `claude-3-5-sonnet` 时：
- 映射到 `my-custom-gpt-model`
- litellm 不认识这个模型
- 使用环境变量默认值：150K/10K
