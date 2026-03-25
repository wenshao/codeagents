# GitHub Copilot CLI

**开发者：** GitHub (Microsoft)
**许可证：** 专有
**仓库：** [github.com/github/copilot-cli](https://github.com/github/copilot-cli)
**文档：** [docs.github.com/copilot/concepts/agents/about-copilot-cli](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
**最后更新：** 2026-03

## 概述

GitHub Copilot CLI 是 GitHub 推出的终端原生 AI 编程代理。基于与 GitHub Copilot coding agent 相同的代理框架，提供代码构建、调试、重构等智能辅助能力，并深度集成 GitHub 工作流。以独立二进制形式运行（`copilot` 命令），支持 macOS、Linux 和 Windows。

## 核心功能

### 代理式编程
- **代码编辑**：通过自然语言对话构建、编辑、调试和重构代码
- **任务规划与执行**：能够规划和执行复杂的多步骤任务
- **上下文感知**：理解当前仓库代码和 Git 状态

### GitHub 集成
- **原生集成**：使用自然语言访问仓库、Issues 和 Pull Requests
- **GitHub 账户认证**：使用现有 GitHub 账户直接登录
- **企业功能**：SSO、审计日志、合规支持

### 扩展能力
- **MCP 支持**：内置 GitHub MCP 服务器，支持自定义 MCP 服务器扩展功能
- **LSP 支持**：集成语言服务器协议，提供智能代码跳转、悬停信息和诊断
- **多模型支持**：默认使用 Claude Sonnet 4.5，可切换 Claude Sonnet 4、GPT-5 等模型

### 实验性功能
- **Autopilot 模式**：按 `Shift+Tab` 切换，代理会持续工作直到任务完成

## 安装

```bash
# 方式一：安装脚本（macOS / Linux）
curl -fsSL https://gh.io/copilot-install | bash

# 方式二：Homebrew（macOS / Linux）
brew install copilot-cli

# 方式三：WinGet（Windows）
winget install GitHub.Copilot

# 方式四：npm（全平台）
npm install -g @github/copilot

# 启动
copilot
```

支持 PAT 认证：创建带 "Copilot Requests" 权限的 fine-grained PAT，通过 `GH_TOKEN` 或 `GITHUB_TOKEN` 环境变量传入。

## LSP 配置

支持用户级（`~/.copilot/lsp-config.json`）和仓库级（`.github/lsp.json`）配置：

```json
{
  "lspServers": {
    "typescript": {
      "command": "typescript-language-server",
      "args": ["--stdio"],
      "fileExtensions": {
        ".ts": "typescript",
        ".tsx": "typescript"
      }
    }
  }
}
```

## 架构

- **实现方式**：独立二进制（`copilot` 命令）
- **代理框架**：与 GitHub Copilot coding agent 共用相同的代理框架
- **默认模型**：Claude Sonnet 4.5（可选 Claude Sonnet 4、GPT-5）
- **工具协议**：支持 MCP（Model Context Protocol）

## 优势

1. **完整代理能力**：不再是简单的命令工具，具备代码编辑、调试、重构等完整代理能力
2. **GitHub 生态深度集成**：与仓库、Issues、PR、Actions 原生联动
3. **多模型选择**：支持 Claude 和 GPT 系列模型
4. **MCP 可扩展**：内置 GitHub MCP 服务器，支持自定义扩展
5. **LSP 集成**：提供智能代码分析能力
6. **企业支持**：企业级安全和合规
7. **操作确认**：所有操作需用户明确批准后执行

## 劣势

1. **需要 Copilot 订阅**：依赖付费的 GitHub Copilot 订阅
2. **消耗 premium requests 配额**：每次提交消耗一次 premium request
3. **需要 GitHub 账户**：依赖 GitHub 认证
4. **较新产品**：仍在快速迭代中，功能稳定性待验证

## 使用场景

- **最适合**：GitHub 重度用户、企业团队、需要 GitHub 集成的开发工作流
- **适合**：日常编码、调试、代码理解、跨语言开发
- **不太适合**：非 GitHub 用户、无 Copilot 订阅的用户

## 定价

- 包含在 GitHub Copilot 订阅中（每次提交消耗 premium request 配额）
- 详见 [Copilot 计划](https://github.com/features/copilot/plans)

## 资源链接

- [GitHub 仓库](https://github.com/github/copilot-cli)
- [官方文档](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [Premium Requests 说明](https://docs.github.com/copilot/managing-copilot/monitoring-usage-and-entitlements/about-premium-requests)
