# 📚 完整中文文档

本项目提供了详细的中文文档，涵盖安装、配置、使用、故障排查、性能优化等各个方面。

## 📖 文档索引

**👉 [点击这里查看完整文档索引](docs/INDEX.md)**

### 快速导航

| 文档 | 说明 |
|------|------|
| [快速开始](docs/README.md) | 详细的安装和配置指南 |
| [配置指南](docs/CONFIGURATION.md) | 所有环境变量和配置选项 |
| [功能特性](docs/FEATURES.md) | 功能详解和使用示例 |
| [故障排查](docs/TROUBLESHOOTING.md) | 常见问题诊断和解决方案 |
| [性能优化](docs/PERFORMANCE.md) | 性能调优和生产环境配置 |
| [开发指南](docs/DEVELOPMENT.md) | 开发者文档和 API 说明 |
| [常见问题](docs/FAQ.md) | 30+ 个常见问题解答 |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# .env
OPENAI_API_KEY=sk-proj-xxx
PREFERRED_PROVIDER=openai
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini
```

### 3. 启动服务器

```bash
python server.py
```

### 4. 配置 Claude Code

```bash
export ANTHROPIC_API_KEY=dummy
export ANTHROPIC_BASE_URL=http://localhost:8082
```

## 🔍 按场景查找

### 我是新手
👉 [快速开始](docs/README.md)

### 我遇到了问题
👉 [故障排查](docs/TROUBLESHOOTING.md) | [常见问题](docs/FAQ.md)

### 我想优化性能
👉 [性能优化](docs/PERFORMANCE.md)

### 我想开发新功能
👉 [开发指南](docs/DEVELOPMENT.md)

## 📊 文档统计

- **总文档数**: 7 个主要文档
- **总字数**: 约 50,000 字
- **FAQ 数量**: 30+ 个问题
- **覆盖主题**: 安装、配置、功能、排错、优化、开发

## 🆘 获取帮助

1. 查看[完整文档](docs/INDEX.md)
2. 查看[常见问题](docs/FAQ.md)
3. 查看[故障排查](docs/TROUBLESHOOTING.md)
4. 提交 Issue

---

**开始阅读**: [docs/INDEX.md](docs/INDEX.md) 📖
