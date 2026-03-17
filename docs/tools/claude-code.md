# Claude Code

**开发者：** Anthropic
**许可证：** 专有（提供免费层级）
**仓库：** [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)
**文档：** [code.claude.com/docs](https://code.claude.com/docs)

## 概述

Claude Code 是 Anthropic 官方的 AI 编程代理，运行在你的终端中。它被设计为一个代理式编程工具，能够理解你的代码库，并通过执行例行任务帮助你更快地编码。

## 核心功能

### 基础能力
- **原生终端体验**：从零开始构建的 CLI 工具
- **代码编辑**：直接文件编辑，带差异预览
- **多文件操作**：可同时编辑多个文件
- **Bash 执行**：可运行终端命令和脚本
- **Git 集成**：理解 Git 历史并可创建提交/PR
- **MCP 支持**：模型上下文协议，扩展能力
- **Skills 系统**：可自定义斜杠命令执行常见任务
- **子代理**：可生成专门的代理进行并行工作
- **计划模式**：执行前进行交互式规划

### 独特功能
- **Hooks**：通过前置/后置工具钩子自动化工作流
- **Worktrees**：实验性的 Git worktree 支持隔离工作
- **权限系统**：精细控制代理可以做什么
- **沙箱**：网络控制和执行限制

## 安装

```bash
# 使用 npm（推荐）
npm install -g @anthropic-ai/claude-code

# 或使用安装脚本
curl -fsSL https://code.claude.com/install.sh | sh
```

## 架构

- **语言：** Rust
- **模型：** Claude 4.5 (Sonnet) / Claude 4.6 (Opus)
- **上下文窗口：** 最高 100 万 token (Opus 4.6)

## 优势

1. **卓越的推理能力**：在 SWE-bench 复杂问题解决上领先
2. **优秀的文档**：全面的文档和指南
3. **MCP 生态**：不断增长的 MCP 服务器社区
4. **精心设计**：由了解开发者的人员构建
5. **隐私选项**：敏感代码可使用本地模式

## 劣势

1. **模型锁定**：只能使用 Claude 模型
2. **无原生 IDE 集成**：CLI 优先（VS Code 扩展测试中）
3. **专有软件**：非开源
4. **成本**：重度使用时 Claude API 费用会累积

## CLI 命令

```bash
# 启动交互式会话
claude

# 直接提问
claude "如何重构这个函数？"

# 审查 PR
claude "审查 PR #123"

# 在指定目录运行
claude --cwd ./src

# 使用特定模型
claude --model claude-opus-4-6
```

## 使用场景

- **最适合**：复杂重构、架构决策、代码审查
- **适合**：多文件编辑、测试生成、文档编写
- **不太适合**：快速单行补全、实时建议

## 社区

- **GitHub 讨论**：[github.com/anthropics/claude-code/discussions](https://github.com/anthropics/claude-code/discussions)
- **更新日志**：[code.claude.com/docs/changelog](https://code.claude.com/docs/changelog)

## 替代品

- **Aider**：更好的 Git 集成，开源
- **Cursor CLI**：IDE 集成
- **GitHub Copilot CLI**：GitHub 生态集成

## 资源链接

- [CLI 参考](https://code.claude.com/docs/en/cli-reference)
- [高级设置](https://code.claude.com/docs/en/setup)
- [完整指南](https://blakecrosley.com/guides/claude-code)
