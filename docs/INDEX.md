# Claude Code Proxy - 完整文档索引

欢迎使用 Claude Code Proxy！这是一个功能强大的代理服务器，让你可以使用 Claude Code 客户端，但实际调用其他 LLM 提供商的 API。

## 📖 文档导航

### 🚀 快速开始

- **[README.md](README.md)** - 项目简介、快速安装和基础使用
  - 项目简介和架构
  - 5 分钟快速开始
  - 环境要求和安装步骤
  - 基础配置示例

### ⚙️ 配置指南

- **[CONFIGURATION.md](CONFIGURATION.md)** - 详细的配置说明
  - 环境变量完整列表
  - API Keys 配置
  - 模型映射规则
  - 性能调优参数
  - 各种场景的配置示例

### ✨ 功能特性

- **[FEATURES.md](FEATURES.md)** - 所有功能的详细说明
  - API 格式转换（Anthropic ↔ OpenAI）
  - 流式响应支持
  - 工具调用转换
  - 请求追踪 (Trace UI)
  - 自动重试机制
  - 模型映射详解

### 🔧 故障排查

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 常见问题诊断和解决
  - 重复请求问题
  - 连接错误
  - API Key 错误
  - 模型不支持
  - 流式响应中断
  - 工具调用失败
  - 性能问题
  - 内存泄漏
  - 日志分析指南

### ⚡ 性能优化

- **[PERFORMANCE.md](PERFORMANCE.md)** - 性能调优指南
  - Worker 配置策略
  - 并发限制优化
  - TCP 优化
  - 重试策略优化
  - 模型选择建议
  - 缓存优化
  - 网络优化
  - 内存优化
  - 监控和指标
  - 生产环境配置示例

### 👨‍💻 开发指南

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - 开发者文档
  - 项目结构
  - 核心模块说明
  - 添加新功能示例
  - 调试技巧
  - 测试方法
  - 代码风格指南
  - 性能分析
  - 部署方案

### ❓ 常见问题

- **[FAQ.md](FAQ.md)** - 30+ 个常见问题解答
  - 基础问题（项目用途、支持的提供商等）
  - 配置问题（如何配置各种提供商）
  - 功能问题（流式响应、工具调用等）
  - 性能问题（如何提高速度和并发）
  - 错误问题（各种错误的解决方案）
  - 高级问题（生产部署、监控、高可用等）

### 🐛 已知问题

- **[DUPLICATE_REQUEST_FIX.md](../DUPLICATE_REQUEST_FIX.md)** - 重复请求问题修复
  - 问题分析
  - 修复方案
  - 验证方法

---

## 📚 按场景查找文档

### 我是新手，想快速上手

1. 阅读 [README.md](README.md) 的"快速开始"部分
2. 按照步骤安装和配置
3. 运行测试脚本验证
4. 如遇问题，查看 [FAQ.md](FAQ.md)

### 我想配置特定的 LLM 提供商

1. 查看 [CONFIGURATION.md](CONFIGURATION.md) 的"API Keys 配置"部分
2. 参考 [FAQ.md](FAQ.md) 的 Q5-Q7
3. 查看 [FEATURES.md](FEATURES.md) 了解模型映射规则

### 我遇到了错误

1. 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 找到对应的错误类型
2. 按照诊断步骤排查
3. 如果是常见问题，查看 [FAQ.md](FAQ.md)
4. 启用详细日志进行调试

### 我想优化性能

1. 阅读 [PERFORMANCE.md](PERFORMANCE.md) 了解优化策略
2. 根据你的场景选择合适的配置
3. 使用 Trace UI 监控性能
4. 参考生产环境配置示例

### 我想开发新功能

1. 阅读 [DEVELOPMENT.md](DEVELOPMENT.md) 了解项目结构
2. 查看"添加新功能"示例
3. 编写测试
4. 提交 Pull Request

### 我想部署到生产环境

1. 阅读 [DEVELOPMENT.md](DEVELOPMENT.md) 的"部署"部分
2. 查看 [PERFORMANCE.md](PERFORMANCE.md) 的生产环境配置
3. 参考 [FAQ.md](FAQ.md) 的 Q20-Q25
4. 设置监控和告警

---

## 🔍 快速查找

### 配置相关

| 问题 | 文档位置 |
|------|----------|
| 如何配置 OpenAI？ | [CONFIGURATION.md](CONFIGURATION.md) → API Keys 配置 |
| 如何配置 Gemini？ | [CONFIGURATION.md](CONFIGURATION.md) → API Keys 配置 |
| 如何自定义模型映射？ | [CONFIGURATION.md](CONFIGURATION.md) → 模型映射配置 |
| 如何使用自定义端点？ | [CONFIGURATION.md](CONFIGURATION.md) → OpenAI 自定义端点 |
| 如何调整性能参数？ | [CONFIGURATION.md](CONFIGURATION.md) → 性能调优配置 |

### 功能相关

| 问题 | 文档位置 |
|------|----------|
| 如何使用流式响应？ | [FEATURES.md](FEATURES.md) → 流式响应支持 |
| 如何查看请求详情？ | [FEATURES.md](FEATURES.md) → 请求追踪 |
| 工具调用如何工作？ | [FEATURES.md](FEATURES.md) → API 格式转换 |
| 如何配置重试？ | [FEATURES.md](FEATURES.md) → 自动重试机制 |

### 问题排查

| 问题 | 文档位置 |
|------|----------|
| 重复请求 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → 重复请求问题 |
| 连接被拒绝 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → 连接被拒绝 |
| API Key 错误 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → API Key 错误 |
| 响应缓慢 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → 性能问题 |
| 内存占用高 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → 内存泄漏 |

### 性能优化

| 问题 | 文档位置 |
|------|----------|
| 如何提高并发？ | [PERFORMANCE.md](PERFORMANCE.md) → Worker 配置 |
| 如何降低延迟？ | [PERFORMANCE.md](PERFORMANCE.md) → 模型选择优化 |
| 如何减少内存？ | [PERFORMANCE.md](PERFORMANCE.md) → 内存优化 |
| 生产环境配置？ | [PERFORMANCE.md](PERFORMANCE.md) → 生产环境配置示例 |

---

## 📊 文档统计

- **总文档数**: 7 个主要文档
- **总字数**: 约 50,000 字
- **覆盖主题**: 
  - 安装配置
  - 功能特性
  - 故障排查
  - 性能优化
  - 开发指南
  - 常见问题
- **FAQ 数量**: 30+ 个问题

---

## 🆘 获取帮助

### 文档没有解决你的问题？

1. **查看日志**
   ```bash
   # 启用详细日志
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **使用 Trace UI**
   ```bash
   http://localhost:8082/trace
   ```

3. **运行测试**
   ```bash
   python test_duplicate_requests.py
   ```

4. **提交 Issue**
   - 描述问题
   - 附上日志
   - 说明环境信息（OS、Python 版本、配置等）

### 联系方式

- **GitHub Issues**: 提交 bug 报告或功能请求
- **Pull Requests**: 贡献代码或文档改进

---

## 📝 文档更新日志

### 2024-05-25
- ✅ 创建完整文档体系
- ✅ 添加 README.md（快速开始）
- ✅ 添加 CONFIGURATION.md（配置指南）
- ✅ 添加 FEATURES.md（功能特性）
- ✅ 添加 TROUBLESHOOTING.md（故障排查）
- ✅ 添加 PERFORMANCE.md（性能优化）
- ✅ 添加 DEVELOPMENT.md（开发指南）
- ✅ 添加 FAQ.md（常见问题）
- ✅ 修复重复请求问题
- ✅ 添加调试日志

---

## 🎯 下一步

### 刚开始使用？

👉 从 [README.md](README.md) 开始

### 遇到问题？

👉 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 或 [FAQ.md](FAQ.md)

### 想要优化？

👉 阅读 [PERFORMANCE.md](PERFORMANCE.md)

### 想要开发？

👉 参考 [DEVELOPMENT.md](DEVELOPMENT.md)

---

**祝你使用愉快！** 🚀
