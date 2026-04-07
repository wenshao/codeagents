# OpenCode 源码分析（面向 Code Agent 开发者）

> 本系列文档基于 OpenCode v1.3.0 开源源码分析（MIT 许可，19 包 TypeScript monorepo），提炼出对 Qwen Code 等 Code Agent 开发者有参考价值的架构设计和实现模式。
>
> **阅读对象**：正在开发或改进 CLI Code Agent 的工程师
>
> **OpenCode 的独特价值**：多客户端架构（TUI + Web + Desktop 共享后端）、17 种 Hook 类型、37 种 LSP 集成、100+ Provider 动态加载。这些是 Qwen Code 和 Claude Code 都没有的设计。

## 文档索引

| 文档 | 开发者关注点 | Qwen Code 对标 |
|------|------------|----------------|
| [01-概述与对标](./01-overview.md) | 能力矩阵、架构差异、独特设计 | 功能差距 + 可借鉴模式 |
| [02-命令与工具](./02-commands.md) | 18 工具 + 7 代理 + 命令面板 | 工具/代理架构 |
| [03-技术架构](./03-architecture.md) | 多客户端、LSP 集成、认证、插件 Hook | 插件系统 + LSP + 多客户端路线 |
| [EVIDENCE.md](./EVIDENCE.md) | 源码分析原始证据 | — |

## OpenCode vs 其他 Agent：定位差异

| 维度 | OpenCode | Claude Code | Qwen Code | Gemini CLI |
|------|---------|-------------|-----------|-----------|
| **定位** | 多客户端平台 | 终端深度 Agent | 终端 Agent（Gemini fork） | 终端 Agent |
| **客户端** | TUI + Web + Desktop | TUI + Remote Control | TUI + WebUI + VSCode | TUI |
| **Provider 数** | 100+（models.dev 动态） | 1（Claude） | 10+（多 Provider） | 1（Gemini） |
| **LSP 集成** | 37 种语言 | 实验性 | 实验性 | 无 |
| **Formatter** | 26 种 | 无 | 无 | 无 |
| **Hook 类型** | 17 种 | 27 事件 × 6 处理器 | ~12 事件 × command | ~11 事件 × command |
| **许可证** | MIT | 专有 | Apache 2.0 | Apache 2.0 |

## 源码位置

- 仓库：[github.com/anomalyco/opencode](https://github.com/anomalyco/opencode)
- 许可证：MIT
- 版本：v1.3.0
