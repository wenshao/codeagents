# Gemini CLI

**开发者：** Google
**许可证：** Apache-2.0
**仓库：** [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
**文档：** [geminicli.com](https://geminicli.com)
**Stars：** 约 1k+

## 概述

Gemini CLI 是 Google 官方的命令行界面，用于与 Gemini AI 模型交互。它将 Gemini 的功能直接带到你的终端。

## 核心功能

### 基础能力
- **官方 Google 工具**：第一方 Gemini CLI
- **ReAct 循环**：推理和行动模式
- **MCP 支持**：与本地和远程 MCP 服务器配合
- **GitHub 集成**：设置和管理 GitHub 工作流
- **轻量级**：最小资源占用

### 独特功能
- **内置工具**：预配置的工具集
- **Google 集成**：深度 Google Cloud 集成
- **ReAct 模式**：复杂的代理行为
- **多平台**：Windows、Linux、macOS

## 安装

```bash
# 使用 npm
npm install -g @google/gemini-cli

# 或使用设置脚本
npm install -g @google/gemini-cli
gemini-cli setup

# 配置
export GOOGLE_GEMINI_API_KEY="your-key"
```

## 架构

- **语言：** TypeScript
- **主要模型**：Google Gemini 2.0 / 2.5
- **模式**：ReAct（推理 + 行动）

## 优势

1. **官方支持**：Google 支持
2. **Google 生态**：与 Google Cloud 集成
3. **MCP 原生**：为模型上下文协议构建
4. **开源**：Apache-2.0 许可
5. **ReAct 模式**：复杂的代理行为

## 劣势

1. **较新工具**：不如竞争对手成熟
2. **Gemini 专注**：仅适用于 Google 模型
3. **较小社区**：比 Claude/Copilot 用户少
4. **文档**：不如主要工具全面

## CLI 命令

```bash
# 启动交互式会话
gemini-cli

# 提问
gemini-cli "解释这段代码"

# 设置 GitHub 集成
gemini-cli /setup-github

# 使用特定工具
gemini-cli --tools browser,filesystem

# MCP 服务器模式
gemini-cli --mcp-server
```

## 配置

```bash
# ~/.gemini-cli/config.json
{
  "model": "gemini-2.5-pro",
  "tools": ["browser", "filesystem", "github"],
  "mcpServers": [...]
}
```

## 使用场景

- **最适合**：Google Cloud 用户、Gemini 用户
- **适合**：Google 生态集成
- **不太适合**：偏好 Claude/GPT 模型的用户

## 资源链接

- [安装指南](https://geminicli.com/docs/get-started/installation/)
- [CLI 参考](https://geminicli.com/docs/reference/commands/)
- [GitHub](https://github.com/google-gemini/gemini-cli)
