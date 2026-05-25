# 项目结构说明

## 📁 目录结构

```
claude-code-proxy/
├── server.py                      # 主服务器文件（FastAPI 应用）
├── trace_db.py                    # 追踪数据库模块（SQLite）
├── requirements.txt               # Python 依赖列表
├── pyproject.toml                 # 项目配置（uv）
├── .env                           # 环境变量配置（需创建）
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git 忽略文件
├── README.md                      # 项目主 README（英文）
├── DOCS_CN.md                     # 中文文档入口
├── DUPLICATE_REQUEST_FIX.md       # 重复请求问题修复说明
├── DOCUMENTATION_SUMMARY.md       # 文档创建总结
│
├── docs/                          # 📚 完整文档目录
│   ├── INDEX.md                   # 文档索引（导航中心）
│   ├── README.md                  # 快速开始
│   ├── CONFIGURATION.md           # 配置指南
│   ├── FEATURES.md                # 功能特性
│   ├── TROUBLESHOOTING.md         # 故障排查
│   ├── PERFORMANCE.md             # 性能优化
│   ├── DEVELOPMENT.md             # 开发指南
│   ├── FAQ.md                     # 常见问题
│   └── STRUCTURE.md               # 本文件
│
├── static/                        # 静态文件目录
│   └── trace.html                 # Trace UI 前端页面
│
├── scripts/                       # 脚本目录
│   └── claude_trace_ui.sh         # Claude Code 启动脚本
│
├── test_duplicate_requests.py     # 重复请求测试脚本
├── test_claude_sdk_trace.py       # Claude SDK 追踪测试
│
├── trace.db                       # SQLite 追踪数据库（运行时生成）
└── cc_traces/                     # 追踪数据目录（可配置）
    └── trace.db                   # 备用追踪数据库位置
```

## 📄 核心文件说明

### server.py
**主服务器文件**，包含：
- FastAPI 应用定义
- `/v1/messages` 端点（消息处理）
- `/v1/messages/count_tokens` 端点（Token 计数）
- API 格式转换逻辑
- 模型映射逻辑
- 流式响应处理
- Trace UI 路由

**关键函数**：
- `create_message()` - 处理消息请求
- `count_tokens()` - 计算 token 数量
- `convert_anthropic_to_litellm()` - Anthropic → LiteLLM 转换
- `convert_litellm_to_anthropic()` - LiteLLM → Anthropic 转换
- `handle_streaming()` - 流式响应处理
- `clean_gemini_schema()` - Gemini schema 清理

### trace_db.py
**追踪数据库模块**，包含：
- SQLite 数据库管理
- 请求记录和查询
- 会话管理
- 统计信息
- 可视化数据构建

**关键函数**：
- `record_request_started()` - 记录请求开始
- `record_request_completed()` - 记录请求完成
- `record_request_failed()` - 记录请求失败
- `get_request()` - 获取请求详情
- `list_sessions()` - 列出所有会话
- `build_timeline()` - 构建时间线
- `build_agent_tree()` - 构建 Agent 层级树

### requirements.txt
**Python 依赖列表**：
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服务器
- `litellm` - 统一 LLM API 接口
- `httpx` - HTTP 客户端
- `pydantic` - 数据验证
- `python-dotenv` - 环境变量管理

### .env
**环境变量配置文件**（需要创建）：
```bash
# API Keys
OPENAI_API_KEY=sk-proj-xxx
GEMINI_API_KEY=AIzaSyxxx
ANTHROPIC_API_KEY=sk-ant-xxx

# 模型配置
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini

# 性能配置
WORKERS=16
PORT=8082
LIMIT_CONCURRENCY=100
```

## 📚 文档文件说明

### docs/INDEX.md
**文档索引和导航中心**
- 所有文档的入口
- 按场景分类的快速查找
- 文档统计信息

### docs/README.md
**快速开始指南**
- 项目简介
- 安装步骤
- 基础配置
- 验证方法

### docs/CONFIGURATION.md
**配置指南**
- 环境变量详解
- API Keys 配置
- 模型映射规则
- 性能调优参数

### docs/FEATURES.md
**功能特性说明**
- API 格式转换
- 流式响应
- 工具调用
- 请求追踪
- 自动重试

### docs/TROUBLESHOOTING.md
**故障排查指南**
- 8 大类常见问题
- 诊断步骤
- 解决方案
- 日志分析

### docs/PERFORMANCE.md
**性能优化指南**
- Worker 配置
- 并发优化
- 网络优化
- 内存优化
- 生产环境配置

### docs/DEVELOPMENT.md
**开发指南**
- 项目结构
- 核心模块
- 添加新功能
- 测试方法
- 部署方案

### docs/FAQ.md
**常见问题解答**
- 30+ 个 FAQ
- 按类别分组
- 详细解答

## 🧪 测试文件说明

### test_duplicate_requests.py
**重复请求测试脚本**
- 测试流式请求
- 测试非流式请求
- 验证是否有重复调用
- 查看调试日志

**使用方法**：
```bash
python test_duplicate_requests.py
```

### test_claude_sdk_trace.py
**Claude SDK 追踪测试**
- 测试 Claude Agent SDK 集成
- 验证追踪功能
- 多场景测试

**使用方法**：
```bash
uv run --dev python test_claude_sdk_trace.py --base-url http://127.0.0.1:8082
```

## 🎨 静态文件说明

### static/trace.html
**Trace UI 前端页面**
- 会话列表
- 请求详情
- 时间线视图
- Agent 层级树
- 历史链视图

**访问方式**：
```bash
http://localhost:8082/trace
```

## 📜 脚本文件说明

### scripts/claude_trace_ui.sh
**Claude Code 启动脚本**
- 自动启动代理服务器
- 配置环境变量
- 启动 Claude Code
- 清理追踪数据

**使用方法**：
```bash
scripts/claude_trace_ui.sh --clear-trace
```

## 🗄️ 数据文件说明

### trace.db
**SQLite 追踪数据库**
- 存储所有请求记录
- 会话信息
- 工具调用事件
- Agent 调用记录

**位置**：
- 默认：项目根目录
- 可配置：`CC_TRACE_DIR` 环境变量

**清理方法**：
```bash
# API 清理
curl -X DELETE http://localhost:8082/api/v2/traces

# 或直接删除
rm trace.db
```

## 🔧 配置文件说明

### pyproject.toml
**项目配置文件**（uv）
- 项目元数据
- 依赖管理
- 构建配置

### .gitignore
**Git 忽略文件**
- `.env` - 环境变量（包含密钥）
- `trace.db` - 追踪数据库
- `__pycache__/` - Python 缓存
- `*.pyc` - 编译文件

## 📊 文件大小参考

| 文件 | 大小 | 说明 |
|------|------|------|
| server.py | ~50 KB | 主服务器代码 |
| trace_db.py | ~20 KB | 追踪数据库模块 |
| trace.html | ~100 KB | Trace UI 前端 |
| trace.db | 变化 | 取决于请求数量 |
| docs/*.md | ~52 KB | 所有文档总和 |

## 🚀 快速导航

### 我想...

**安装和配置**
→ 查看 [docs/README.md](README.md)

**了解所有配置选项**
→ 查看 [docs/CONFIGURATION.md](CONFIGURATION.md)

**了解功能特性**
→ 查看 [docs/FEATURES.md](FEATURES.md)

**解决问题**
→ 查看 [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**优化性能**
→ 查看 [docs/PERFORMANCE.md](PERFORMANCE.md)

**开发新功能**
→ 查看 [docs/DEVELOPMENT.md](DEVELOPMENT.md)

**查看常见问题**
→ 查看 [docs/FAQ.md](FAQ.md)

---

**返回文档索引**: [INDEX.md](INDEX.md)
