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

