# GitHub Copilot CLI

**开发者：** GitHub (Microsoft)
**许可证：** 专有
**仓库：** [github.com/github/copilot-cli](https://github.com/github/copilot-cli)
**文档：** [docs.github.com/copilot](https://docs.github.com/copilot)

## 概述

GitHub Copilot CLI 将 GitHub 的 AI 驱动编码助手直接带到你的终端。它与 GitHub 生态系统无缝集成。

## 核心功能

### 基础能力
- **终端集成**：直接在命令行中获得 AI 帮助
- **命令解释**：`??` 解释 shell 命令
- **命令生成**：自然语言到 CLI 命令
- **GitHub 工作流**：与 GitHub issues、PR、Actions 集成
- **多代理**：可处理复杂的多步任务
- **上下文感知**：理解你的仓库和 Git 历史

### 独特功能
- **GitHub 集成**：原生访问 GitHub issues 和 PR
- **Copilot 扩展**：使用自定义工具扩展
- **企业就绪**：SSO、审计日志、合规功能
- **工作流集成**：与 GitHub Actions 配合工作

## 安装

```bash
# 使用官方安装程序
# 从 https://github.com/github/copilot-cli/releases 下载

# 或使用 Homebrew（macOS/Linux）
brew install copilot-cli

# 登录
copilot-cli auth login
```

## 架构

- **语言：** TypeScript
- **模型：** GPT-4（通过 OpenAI）
- **平台：** 跨平台（macOS、Linux、Windows）

## 优势

1. **GitHub 生态**：与 GitHub.com 无缝集成
2. **企业支持**：企业级安全和合规
3. **命令解释**：非常适合学习 shell 命令
4. **简单界面**：易于上手
5. **Microsoft 支持**：Microsoft 资源支持

## 劣势

1. **模型锁定**：仅 GPT 模型
2. **需要 GitHub**：需要 GitHub 账户
3. **隐私顾虑**：代码发送到 GitHub/Microsoft
4. **功能较弱**：对于复杂任务不如 Claude Code 或 Aider

## CLI 命令

```bash
# 解释命令
gh copilot explain "docker run -p 8080:80 nginx"

# 生成命令
gh copilot suggest "查找所有 python 文件并统计行数"

# 交互模式
gh copilot

# Git 集成
gh copilot resolve "修复失败的测试"
```

## 使用场景

- **最适合**：GitHub 用户、企业团队、命令解释
- **适合**：快速命令生成、GitHub 工作流自动化
- **不太适合**：复杂的多文件重构

## 资源链接

- [入门指南](https://docs.github.com/copilot/how-tos/copilot-cli/cli-getting-started)
- [命令参考](https://docs.github.com/copilot/reference/cli-command-reference)
- [安装指南](https://docs.github.com/copilot/how-tos/set-up/install-copilot-cli)

## 定价

- **个人**：包含在 GitHub Copilot 订阅中（10 美元/月）
- **企业**：包含在 GitHub Enterprise 中
