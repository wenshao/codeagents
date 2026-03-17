# Goose

**开发者：** Block
**许可证：** Apache-2.0
**仓库：** [github.com/block/goose](https://github.com/block/goose)
**文档：** [block.github.io/goose](https://block.github.io/goose/docs/quickstart/)
**Stars：** 约 27k+

## 概述

Goose 是一个开源、可扩展的 AI 代理，运行在你的机器上。它被设计为模型无关的，可与多个提供商集成。

## 核心功能

### 基础能力
- **模型无关**：适用于 Anthropic、OpenAI、Cursor、Google 模型
- **MCP 支持**：完整的模型上下文协议集成
- **本地运行**：在本地机器上运行
- **GUI + CLI**：图形界面和命令行界面
- **可扩展**：自定义工具的插件系统

### 独特功能
- **多提供商**：在 AI 提供商之间无缝切换
- **LSP 集成**：自动加载语言服务器
- **终端 + IDE**：跨不同环境工作
- **GitHub 集成**：原生 GitHub 工作流支持
- **雄心勃勃的设计**：比典型 CLI 工具更全面

## 安装

```bash
# 使用 npm
npm install -g @block/goose

# 使用 Homebrew
brew install block/tap/goose

# 或从发布版下载
# https://github.com/block/goose/releases
```

## 架构

- **语言：** TypeScript
- **支持的提供商：**
  - Anthropic (Claude)
  - OpenAI (GPT-4)
  - Google (Gemini)
  - Cursor
  - 本地模型

## 优势

1. **模型灵活性**：根据需要在提供商之间切换
2. **MCP 原生**：为模型上下文协议构建
3. **开源**：Apache-2.0 许可
4. **跨平台**：适用于 macOS、Linux、Windows
5. **现代**：采用当前最佳实践的近期项目

## 劣势

1. **较新项目**：不如 Aider 或 SWE-agent 成熟
2. **较小社区**：比主要工具用户少
3. **复杂性**：更多功能可能意味着更多复杂性

## CLI 命令

```bash
# 启动交互式会话
goose

# 使用特定模型
goose --model claude-opus-4

# 执行任务
goose "重构这个函数"

# 列出可用提供商
goose providers list

# 配置
goose config init
```

## 配置

```yaml
# ~/.goose/config.yaml
default_provider: anthropic
providers:
  anthropic:
    model: claude-opus-4
    api_key: ${ANTHROPIC_API_KEY}
```

## 使用场景

- **最适合**：想要模型灵活性的用户、MCP 用户
- **适合**：多提供商工作流、开源倡导者
- **不太适合**：想要简单、有主见的工具的用户

## 资源链接

- [快速入门](https://block.github.io/goose/docs/quickstart/)
- [GitHub](https://github.com/block/goose)
