# Code Agent 索引

## 深度分析目录（多文件）

| Agent | 目录 | 文件数 | 内容 |
|------|------|--------|------|
| [Claude Code](./claude-code/) | 9 文件 | 概述/79 命令/架构(反编译)/工具/Skill+13 插件/设置+安全监控/会话+MCP |
| [Copilot CLI](./copilot-cli/) | 5 文件 | 概述/34 命令+67 工具/架构(SEA 反编译)+57 CLI 参数 |
| [Codex CLI](./codex-cli/) | 5 文件 | 概述/28 命令+52 flags/架构(Rust 二进制)+review+cloud |
| [Gemini CLI](./gemini-cli/) | 7 文件 | 概述/39 命令/架构+7 策略路由/23 工具+5 代理/策略引擎 |
| [Kimi CLI](./kimi-cli/) | 5 文件 | 概述/28 命令(双注册表)/架构+Wire 协议+18 工具 |
| [Aider](./aider/) | 5 文件 | 概述/42 命令/架构+PageRank RepoMap+14 编辑格式 |
| [OpenCode](./opencode/) | 5 文件 | 概述/18 工具+7 代理/多客户端架构+LSP |
| [Qwen Code](./qwen-code/) | 6 文件 | 概述/41 命令/架构(Gemini CLI 分叉)+16 工具/Arena+扩展系统 |
| [Goose](./goose/) | 5 文件 | 概述/16 斜杠命令+15 CLI 命令/MCP 原生架构/11 Platform Extension |
| [Hermes Agent](./hermes-agent/) | 6 文件 | 概述/架构/**闭环学习系统**/28+ 工具+14 渠道+6 执行环境/EVIDENCE（Nous Research，369K Python） |

## 单文件 Agent（基础分析）

| Agent | 文件 | 行数 | 特色 |
|------|------|------|------|
| [Cursor CLI](./cursor-cli.md) | 单文件 | 476 | AI 原生 IDE，Background Agent，Rules 系统 |
| [Warp](./warp.md) | 单文件 | 382 | Warp 2.0 ADE，Oz 代理，16 命令 |
| [Qwen Code](./qwen-code.md) | 单文件 | 332 | Gemini CLI 分叉，免费 1000 次/天，40 命令 |
| [Goose](./goose.md) | 单文件 | 208 | MCP 原生，16 命令，Recipe 模板 |
| [Continue](./continue.md) | 单文件 | 190 | VS Code/JetBrains，68 提供商，37 上下文 |
| [SWE-agent](./swe-agent.md) | 单文件 | 178 | SWE-bench 74%+，Docker 沙箱 |
| [Cline](./cline.md) | 单文件 | 151 | VS Code 扩展，24+ 工具，子代理系统 |
| [OpenHands](./openhands.md) | 单文件 | 144 | SWE-bench 77.6%，浏览器操作，Docker |
| [Oh My OpenAgent](./oh-my-openagent.md) | 单文件 | — | OpenCode Harness 层，7~10 Discipline Agent 编排，~45K Stars |
| [mini-swe-agent](./mini-swe-agent.md) | 单文件 | 93 | 教学用，SWE-bench 74%+ |

## 相关：Agent Framework 对比（开发者侧）

> Code Agent（本页）= 用户直接运行的编程助手；Agent Framework = 开发者写代码构建 agent 的 SDK。两者对比维度不同。
>
> **[Agent Framework 章节](../frameworks/)** —— 6 款 SDK 对比（AgentScope 源码级 + LangGraph/CrewAI/AG2/MAF/LangChain 文档级）

## 对比文档

- [功能对比矩阵](../comparison/features.md)
- [内置命令深度对比](../comparison/slash-commands-deep-dive.md)
- [隐私与遥测对比](../comparison/privacy-telemetry.md)
- [功能性内部机制对比](../comparison/functional-internals.md)
- [版本迭代与社区数据](../comparison/evolution-community.md)
- [架构深度对比](../comparison/architecture-deep-dive.md)

## 指南

- [入门指南](../guides/getting-started.md)
- [实操工作流教程](../guides/workflows.md)
- [迁移指南](../guides/migration.md)
- [故障排查](../guides/troubleshooting.md)

## 新增 Agent

| Agent | 形态 | 深度 | 特色 |
|------|------|------|------|
| [Qoder CLI](./qoder-cli/) | 目录 | 多文件 | Go 原生，Quest 模式，Claude Code 兼容，信用制 |

## 增强系统

| 项目 | 文件 | 特色 |
|------|------|------|
| [Everything Claude Code](./everything-claude-code.md) | 单文件 | 28 Agent + 125 Skill + 60 命令，跨 Claude Code/Cursor/Codex/OpenCode |
