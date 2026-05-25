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

