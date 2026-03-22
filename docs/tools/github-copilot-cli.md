# GitHub Copilot CLI

**开发者：** GitHub (Microsoft)
**许可证：** 专有
**文档：** [docs.github.com/copilot/using-github-copilot/using-github-copilot-in-the-command-line](https://docs.github.com/en/copilot/using-github-copilot/using-github-copilot-in-the-command-line)

## 概述

GitHub Copilot CLI 是 GitHub 的 AI 终端助手，作为 `gh` CLI 的扩展（`gh copilot`）运行。主要功能是命令解释和生成，而非完整的代理式编程。适合 GitHub 生态用户进行快速命令查找和工作流自动化。

## 核心功能

### 基础能力
- **命令解释**：`gh copilot explain "command"` 解释 shell 命令
- **命令建议**：`gh copilot suggest "自然语言描述"` 生成命令
- **GitHub 集成**：与 Issues、PR、Actions 原生联动
- **上下文感知**：理解当前仓库和 Git 状态

### 独特功能
- **GitHub 生态原生**：直接操作 Issues、PR、Actions
- **企业功能**：SSO、审计日志、合规
- **Copilot Extensions**：第三方工具扩展

## 安装

```bash
# 安装 gh CLI
brew install gh

# 安装 copilot 扩展
gh extension install github/gh-copilot

# 登录
gh auth login

# 使用
gh copilot explain "docker run -p 8080:80 nginx"
gh copilot suggest "查找所有 python 文件并统计行数"
```

## 架构

- **实现方式**：`gh` CLI 扩展（非独立二进制）
- **模型**：GPT-4（通过 GitHub/OpenAI）

## 优势

1. **GitHub 生态**：与 GitHub.com 无缝集成
2. **企业支持**：企业级安全和合规
3. **命令解释**：学习 shell 命令的好工具
4. **低门槛**：已有 GitHub 账户即可使用

## 劣势

1. **非代理式**：主要是命令解释/生成，不是自主编程代理
2. **模型锁定**：仅 GPT 模型
3. **功能较窄**：相比 Claude Code 或 Aider 功能有限
4. **需要 GitHub 账户**：依赖 GitHub 认证

## 使用场景

- **最适合**：GitHub 用户、企业团队、命令学习
- **适合**：快速命令生成、GitHub 工作流
- **不太适合**：复杂多文件重构、自主编程

## 定价

- 包含在 GitHub Copilot 订阅中（个人 $10/月，企业 $19/月）

## 资源链接

- [文档](https://docs.github.com/en/copilot/using-github-copilot/using-github-copilot-in-the-command-line)
- [gh CLI](https://cli.github.com/)
