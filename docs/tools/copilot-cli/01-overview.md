# 1. GitHub Copilot CLI 概述

**开发者：** GitHub (Microsoft)
**许可证：** 专有
**仓库：** [github.com/github/copilot-cli](https://github.com/github/copilot-cli)
**文档：** [docs.github.com/copilot/concepts/agents/about-copilot-cli](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
**源码版本：** npm 包 v0.0.403（`@github/copilot`），原生二进制 v1.0.11
**最后更新：** 2026-03

## 概述

GitHub Copilot CLI 是 GitHub 推出的终端原生 AI 编程代理。基于与 GitHub Copilot coding agent 相同的代理框架，提供代码构建、调试、重构等智能辅助能力，并深度集成 GitHub 工作流。以独立二进制形式运行（`copilot` 命令），支持 macOS、Linux 和 Windows。内置 12 个核心工具、21 个浏览器工具、48 个 GitHub 平台工具、3 个内置代理和 14 个模型。

## 核心功能

### 代理式编程

- 12 个核心工具（bash、文件操作、搜索等）
- 3 个内置代理（code-review、explore、task）
- 代码搜索子代理

### GitHub 集成

- 48 个 GitHub 平台工具
- Actions、PR、Issues、代码扫描、密钥扫描原生联动
- SSO、审计日志、合规、安全扫描集成

### 扩展能力

- 21 个浏览器工具（基于 Playwright）
- MCP 服务器支持
- LSP 语言服务器集成
- 自定义代理（`.agent.md` / `.agent.yaml`）

### 实验性功能

- 自动驾驶模式（AUTOPILOT_MODE）
- 委派子代理（CCA_DELEGATE）
- 计划命令（PLAN_COMMAND）
- 插件系统（PLUGIN_COMMAND）

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

## MCP 配置

通过 `/mcp` 命令或 `COPILOT_MCP_JSON` 环境变量配置 MCP 服务器，支持 stdio 和 SSE 传输。

## 优势

1. **完整代理能力**：12 个核心工具 + 21 个浏览器工具 + 48 个 GitHub 工具
2. **GitHub 生态深度集成**：Actions、PR、Issues、代码扫描、密钥扫描原生联动
3. **多模型选择**：14 个模型，涵盖 Claude、GPT、Gemini 系列
4. **内置代理系统**：code-review、explore、task 三个专用代理
5. **浏览器自动化**：基于 Playwright 的完整浏览器控制能力
6. **MCP + LSP 可扩展**：支持自定义 MCP 服务器和语言服务器
7. **多格式指令兼容**：同时读取 CLAUDE.md、GEMINI.md、AGENTS.md
8. **企业支持**：SSO、审计日志、合规、安全扫描集成
9. **免费模型可用**：gpt-5-mini 和 gpt-4.1 为 0x 免费模型

## 劣势

1. **需要 Copilot 订阅**：依赖付费的 GitHub Copilot 订阅（免费模型除外）
2. **消耗 premium requests 配额**：高倍率模型（如 claude-opus-4.5 为 3x）消耗较快
3. **需要 GitHub 账户**：依赖 GitHub 认证
4. **部分功能需功能标志**：CUSTOM_AGENTS、PLAN_COMMAND 等需手动启用
5. **较新产品**：仍在快速迭代中，实验性功能较多

## 使用场景

- **最适合**：GitHub 重度用户、企业团队、需要 GitHub Actions/PR/Issues 集成的开发工作流
- **适合**：日常编码、调试、代码审查、浏览器测试自动化、代码库探索
- **不太适合**：非 GitHub 用户、无 Copilot 订阅的用户

## 定价

- 包含在 GitHub Copilot 订阅中（每次提交消耗 premium request 配额，倍率因模型而异）
- gpt-5-mini 和 gpt-4.1 为免费模型（0x 倍率）
- 详见 [Copilot 计划](https://github.com/features/copilot/plans)

## 资源链接

- [GitHub 仓库](https://github.com/github/copilot-cli)
- [官方文档](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [Premium Requests 说明](https://docs.github.com/copilot/managing-copilot/monitoring-usage-and-entitlements/about-premium-requests)
