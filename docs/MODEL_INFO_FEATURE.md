# Model Info Feature

## 概述

代理现在会在响应中包含实际模型的上下文窗口信息，让 Claude Code 客户端知道真实的模型限制。

## 功能说明

当代理将 Claude 模型映射到其他提供商的模型时（例如 `claude-3-5-sonnet` → `gpt-4o`），响应中会包含实际模型的上下文窗口信息：

```json
{
  "id": "msg_...",
  "model": "claude-3-5-sonnet-20241022",
  "role": "assistant",
  "content": [...],
  "usage": {...},
  "model_info": {
    "max_input_tokens": 128000,
    "max_output_tokens": 16384
  }
}
```

## 工作原理

1. **模型映射**：代理根据 `PREFERRED_PROVIDER`、`BIG_MODEL`、`SMALL_MODEL` 环境变量将 Claude 模型映射到实际使用的模型

2. **获取模型信息**：使用 `litellm.get_model_info()` 获取实际模型的上下文窗口大小

3. **添加到响应**：在响应中添加 `model_info` 字段，包含：
   - `max_input_tokens`: 最大输入 token 数
   - `max_output_tokens`: 最大输出 token 数

## 支持的响应类型

### 非流式响应
在 `MessagesResponse` 中直接包含 `model_info` 字段。

### 流式响应
在 `message_start` 事件的 `message` 对象中包含 `model_info` 字段：

```
event: message_start
data: {
  "type": "message_start",
  "message": {
    "id": "msg_...",
    "model": "claude-3-5-sonnet-20241022",
    "model_info": {
      "max_input_tokens": 128000,
      "max_output_tokens": 16384
    },
    ...
  }
}
```

## 示例

### 场景 1: Claude → OpenAI 映射

**配置**:
```bash
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
```

**请求**: `claude-3-5-sonnet-20241022`

**响应**:
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "model_info": {
    "max_input_tokens": 128000,
    "max_output_tokens": 16384
  }
}
```

### 场景 2: Claude → Gemini 映射

**配置**:
```bash
PREFERRED_PROVIDER=google
BIG_MODEL=gemini-2.5-pro
```

**请求**: `claude-3-5-sonnet-20241022`

**响应**:
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "model_info": {
    "max_input_tokens": 1000000,
    "max_output_tokens": 8192
  }
}
```

## 测试

运行测试脚本验证功能：

```bash
# 确保代理正在运行
python3 server.py

# 在另一个终端运行测试
python3 test_model_info.py
```

## 配置选项

### 环境变量

可以通过环境变量设置全局默认的上下文限制：

```bash
# .env 文件
DEFAULT_MAX_INPUT_TOKENS=128000
DEFAULT_MAX_OUTPUT_TOKENS=16384
```

### 优先级

模型信息的获取优先级：

1. **litellm 内置数据库**（最高优先级）
   - 如果模型在 litellm 的 2594 个模型数据库中，使用内置数据
   - 例如：`gpt-4o` → 128K/16K

2. **环境变量默认值**（备用）
   - 如果模型未知或 litellm 无法识别，使用环境变量
   - 适用于自定义模型、私有部署的模型

3. **返回 null**（最后）
   - 如果以上都没有，`model_info` 字段为 `null`

### 使用场景

#### 场景 1: 使用标准模型（无需配置）

```bash
# .env
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
```

结果：自动使用 litellm 内置的 gpt-4o 信息（128K/16K）

#### 场景 2: 使用自定义模型（需要配置默认值）

```bash
# .env
PREFERRED_PROVIDER=openai
BIG_MODEL=my-custom-model
DEFAULT_MAX_INPUT_TOKENS=100000
DEFAULT_MAX_OUTPUT_TOKENS=8192
```

结果：由于 `my-custom-model` 不在 litellm 数据库中，使用环境变量默认值（100K/8K）

#### 场景 3: 混合使用

```bash
# .env
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o              # 使用 litellm 内置数据
SMALL_MODEL=my-small-model    # 使用环境变量默认值
DEFAULT_MAX_INPUT_TOKENS=50000
DEFAULT_MAX_OUTPUT_TOKENS=4096
```

结果：
- `claude-3-5-sonnet` → `gpt-4o` → 128K/16K（litellm 数据）
- `claude-3-haiku` → `my-small-model` → 50K/4K（环境变量）

1. **透明性**：Claude Code 知道实际模型的限制
2. **避免错误**：防止发送超过模型上下文窗口的请求
3. **更好的用户体验**：客户端可以根据实际限制调整行为
4. **兼容性**：如果客户端不支持 `model_info`，可以安全忽略该字段

## 技术细节

### 代码变更

1. **新增 `ModelInfo` 类** (`server.py:387-390`):
   ```python
   class ModelInfo(BaseModel):
       max_input_tokens: Optional[int] = None
       max_output_tokens: Optional[int] = None
   ```

2. **新增 `get_model_context_info` 函数** (`server.py:410-420`):
   ```python
   def get_model_context_info(model_name: str) -> Optional[ModelInfo]:
       try:
           info = litellm.get_model_info(model_name)
           return ModelInfo(
               max_input_tokens=info.get("max_input_tokens"),
               max_output_tokens=info.get("max_output_tokens")
           )
       except Exception as e:
           logger.debug(f"Could not get model info for {model_name}: {e}")
           return None
   ```

3. **更新 `MessagesResponse`** (`server.py:403`):
   添加 `model_info: Optional[ModelInfo] = None` 字段

4. **更新 `convert_litellm_to_anthropic`**:
   调用 `get_model_context_info()` 并将结果添加到响应中

5. **更新 `handle_streaming`**:
   在 `message_start` 事件中包含 `model_info`

### 依赖

- `litellm`: 用于获取模型信息
- 使用 litellm 的本地模型数据库（不需要网络请求）

## 注意事项

1. 如果无法获取模型信息（例如模型未在 litellm 中注册），`model_info` 将为 `null`
2. 模型信息来自 litellm 的本地数据库，可能不是最新的
3. 该功能不影响现有客户端的兼容性
