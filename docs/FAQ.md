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

