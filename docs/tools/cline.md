# Cline

**开发者：** Cline
**许可证：** Apache-2.0
**仓库：** [github.com/cline/cline](https://github.com/cline/cline)
**网站：** [cline.bot](https://cline.bot/)
**Stars：** 约 58k+

## 概述

Cline 是一个直接在 IDE 中运行的自主编码代理（主要是 VS Code）。它被超过 500 万开发者信任，是最流行的开源 AI 编程助手之一。

## 核心功能

### 基础能力
- **IDE 集成**：原生 VS Code/Cursor 扩展
- **自主操作**：可创建/编辑文件、运行命令、浏览网页
- **计划/执行模式**：复杂任务的结构化工作流
- **MCP 集成**：模型上下文协议支持
- **浏览器访问**：可使用浏览器进行研究
- **终端集成**：完整的命令执行能力

### 独特功能
- **基于权限**：每个操作都需要用户批准
- **多步规划**：分解复杂任务
- **上下文感知**：理解整个项目
- **Claude Sonnet 4**：针对最新 Claude 模型优化
- **VS Code 原生**：深度 VS Code 集成

## 安装

```bash
# 从 VS Code Marketplace 安装
1. 打开 VS Code
2. 转到扩展（Ctrl/Cmd + Shift + X）
3. 搜索 "Cline"
4. 安装并使用 GitHub 登录

# 或从 VSIX
code --install-extension cline.cline
```

## 架构

- **语言：** TypeScript
- **平台：** VS Code / Cursor / Antigravity
- **主要模型：** Claude Sonnet 4.0

## 优势

1. **IDE 原生**：专为 VS Code 构建
2. **权限模式**：安全 - 更改前始终询问
3. **大社区**：500 万+ 用户
4. **MCP 支持**：通过模型上下文协议扩展
5. **自主**：可独立处理多步任务

## 劣势

1. **依赖 IDE**：主要是 VS Code（非纯 CLI）
2. **仅 Claude**：专注于 Claude 模型
3. **权限疲劳**：快速任务可能繁琐
4. **Git 集成较少**：不如 Aider 专注于 Git

## 使用方法

```bash
# VS Code 命令面板中
Cline: Start New Task
Cline: Continue Conversation

# 让 Cline 做点什么
"Cline，用 hooks 重构这个组件"

# 多步任务
"Cline，创建一个带测试的新 API 端点"
```

## 配置

```json
// .vscode/settings.json
{
  "cline.apiProvider": "anthropic",
  "cline.model": "claude-sonnet-4-20250514",
  "cline.autoApproval": false
}
```

## 使用场景

- **最适合**：VS Code 用户、全功能开发
- **适合**：多文件编辑、自主任务完成
- **不太适合**：快速 CLI 交互、非 VS Code 用户

## Fork 和变体

- **Clare**：tot-ra 的分支，带有修改

## 资源链接

- [文档](https://docs.cline.bot/)
- [GitHub](https://github.com/cline/cline)
- [网站](https://cline.bot/)
