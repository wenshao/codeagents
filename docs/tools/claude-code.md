# Claude Code

**开发者：** Anthropic
**许可证：** 专有（Claude Pro/Max 订阅内含）
**仓库：** [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)（插件/示例仓库）
**文档：** [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code)

## 概述

Claude Code 是 Anthropic 官方的 AI 编程代理，运行在终端中。核心为闭源 Rust 原生二进制，通过原生安装（非 npm）分发。拥有业界最成熟的插件生态（13 个官方插件）、7 层企业设置、Prompt Hook（LLM 驱动决策）等独特能力。

## 核心功能

### 基础能力
- **Rust 原生二进制**：`curl install.sh | bash` 安装，npm 已 deprecated
- **14+ 内置工具**：Read、Write、Edit、Bash、Glob、Grep、WebFetch、WebSearch、Task（子代理）、Skill、TodoWrite、NotebookEdit 等
- **MCP 集成**：Stdio/SSE/HTTP/WebSocket 四种传输
- **Git 集成**：理解 Git 历史，创建提交/PR
- **上下文窗口**：最高 100 万 token（Opus 4.6）
- **会话恢复**：`--resume` 恢复中断会话

### 独特功能
- **13 个官方插件**：code-review（4 并行代理）、feature-dev（7 阶段流程）、security-guidance、hookify 等
- **Prompt Hook**：LLM 推理驱动的 Hook 决策（不只是脚本）
- **7 层设置**：企业→组织→用户→项目→本地→CLI→默认
- **沙箱执行**：文件系统隔离 + 网络域名限制
- **Teammates**：tmux/iTerm2 分屏多代理团队协作
- **Remote Control**：`/remote-control` 桥接到 claude.ai/code 浏览器
- **Voice 模式**：Push-to-talk 语音交互
- **Channels**：`--channels` 允许 MCP 服务器推送消息
- **`--bare` 模式**：脚本/CI 场景跳过 hooks/插件/LSP
- **CLAUDE.md**：项目级 AI 行为指令
- **Worktrees**：Git worktree 隔离并行分支
- **自动记忆**：跨会话学习用户偏好

## 安装

```bash
# 推荐方式（原生二进制）
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew
brew install --cask claude-code

# npm（已 deprecated）
npm install -g @anthropic-ai/claude-code
```

## 架构

- **语言**：Rust（闭源核心）+ 插件（Markdown/Python/Bash）
- **模型**：Claude Sonnet 4.6 / Opus 4.6 / Haiku 4.5
- **插件结构**：`.claude-plugin/plugin.json` + commands/ + agents/ + skills/ + hooks/ + `.mcp.json`

## 优势

1. **Rust 性能**：亚秒级冷启动，低内存占用
2. **插件生态**：13 个官方插件，marketplace 支持
3. **企业管控**：7 层设置 + managed-settings 远程下发
4. **Prompt Hook**：LLM 推理决策（超越脚本 Hook）
5. **推理能力**：SWE-bench 复杂问题领先

## 劣势

1. **模型锁定**：仅支持 Claude 模型
2. **闭源**：核心代码不可审计
3. **成本**：Claude Pro $20/月 或 API 按量付费
4. **无多提供商**：不支持切换到 GPT/Gemini

## CLI 命令

```bash
claude                              # 交互式会话
claude "重构这个函数"                # 直接提问
claude --resume                     # 恢复上次会话
claude --model claude-opus-4-6      # 指定模型
claude -p "修复 bug" --bare         # 脚本模式
claude --channels                   # 启用 MCP 消息推送
```

## 使用场景

- **最适合**：复杂重构、架构决策、企业部署
- **适合**：代码审查（code-review 插件）、多文件编辑
- **不太适合**：需要多模型切换、纯开源需求

## 资源链接

- [文档](https://docs.anthropic.com/en/docs/claude-code)
- [插件仓库](https://github.com/anthropics/claude-code)
- [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
