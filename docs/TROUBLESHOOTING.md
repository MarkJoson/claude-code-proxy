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

