# 工具文档

各个 Code Agent CLI 工具的详细文档。

## 商业工具

### [Claude Code](./claude-code.md)
**开发者：** Anthropic
**最适合：** 复杂推理、大上下文
**核心特性：** MCP 生态系统

### [GitHub Copilot CLI](./github-copilot-cli.md)
**开发者：** GitHub
**最适合：** GitHub 生态集成
**核心特性：** 企业功能

### [Cursor CLI](./cursor-cli.md)
**开发者：** Cursor
**最适合：** IDE 级 AI 编程体验
**核心特性：** Background Agent、多模型支持

### [Warp](./warp.md)
**开发者：** Warp Dot Dev
**最适合：** 现代终端体验
**核心特性：** 带 AI 的终端替代品

## 开源工具

### [Codex CLI](./codex-cli.md)
**开发者：** OpenAI
**最适合：** 安全沙箱执行
**核心特性：** 网络隔离沙箱，三种自主级别

### [Aider](./aider.md)
**开发者：** Paul Gauthier
**最适合：** Git 重度工作流
**核心特性：** Git 原生设计

### [Cline](./cline.md)
**开发者：** Cline
**最适合：** IDE 优先开发
**核心特性：** VS Code 集成

### [Goose](./goose.md)
**开发者：** Block
**最适合：** 模型灵活性
**核心特性：** Rust 原生、58+ 提供商、MCP 扩展

### [OpenCode](./opencode.md)
**开发者：** OpenCode AI
**最适合：** 终端优先
**核心特性：** 双代理设计

### [Continue](./continue.md)
**开发者：** Continue Dev
**最适合：** CI/CD 集成
**核心特性：** 源码控制的 AI

### [Gemini CLI](./gemini-cli.md)
**开发者：** Google
**最适合：** Google 生态
**核心特性：** ReAct 模式

## 国内工具

### [Qwen Code](./qwen-code.md)
**开发者：** 阿里云
**最适合：** 中文开发者、阿里云用户
**核心特性：** 每日 2000 次免费额度

### [Kimi CLI](./kimi-code.md)
**开发者：** 月之暗面
**最适合：** Kimi 用户、中文开发者
**核心特性：** 双模式交互、Ctrl-K 快捷键

## 研究项目

### [SWE-agent](./swe-agent.md)
**开发者：** Princeton NLP
**最适合：** 基准性能
**核心特性：** Agent-Computer Interface

### [OpenHands (OpenDevin)](./openhands.md)
**开发者：** OpenHands
**最适合：** 完全自主
**核心特性：** 复合 AI 系统

### [mini-swe-agent](./mini-swe-agent.md)
**开发者：** Princeton NLP
**最适合：** 学习
**核心特性：** 100 行实现

## 按用途分类

| 类别 | 工具 |
|------|------|
| 日常编程 | Claude Code, Aider, Cline |
| Git 工作流 | Aider, Claude Code, Copilot CLI |
| CI/CD | Continue, Claude Code |
| 自动化 | OpenHands, SWE-agent |
| 学习 | mini-swe-agent, SWE-agent |

## 按模型支持分类

| 模型 | 主要工具 |
|------|----------|
| Claude | Claude Code, Aider, Cline |
| GPT-4 | Copilot CLI, Continue, Goose |
| Gemini | Gemini CLI, OpenCode, Goose |
| 多模型 | Goose, Continue, OpenHands |

## 按许可证分类

| 许可证 | 工具 |
|---------|------|
| 开源 | Aider, SWE-agent, Cline, Goose, Continue, OpenHands |
| 专有 | Claude Code, Copilot CLI, Warp |

## 快速参考

```bash
# 安装命令
curl -fsSL https://claude.ai/install.sh | bash  # Claude Code
pip install aider-chat                         # Aider
gh extension install github/gh-copilot           # Copilot CLI
brew install --cask warp                       # Warp
npm install -g @google/gemini-cli              # Gemini CLI
```

## 相关文档

- [功能对比](../comparison/features.md)
- [入门指南](../guides/getting-started.md)
- [架构解析](../architecture/overview.md)
