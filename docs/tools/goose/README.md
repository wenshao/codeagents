# Goose 源码分析（面向 Code Agent 开发者）

> 本系列文档基于 Goose v1.28.0 开源 Rust 源码完整分析，提炼出对 Qwen Code、Gemini CLI 等 Code Agent 开发者有参考价值的架构设计和实现模式。重点关注 MCP 原生架构、4 层 Inspector 安全管道、SmartApprove 权限系统等 Goose 独有设计。
>
> **阅读对象**：正在开发或改进 CLI Code Agent 的工程师
>
> **不是**：Goose 用户手册或功能介绍

## 文档索引

| 文档 | 开发者关注点 | Qwen Code 对标 |
|------|------------|----------------|
| [01-概述与对标](./01-overview.md) | 核心能力矩阵、MCP 原生哲学、Rust 工程权衡 | MCP 标准化 + 安全管道 |
| [02-命令系统](./02-commands.md) | 14 CLI 命令 + 16 斜杠命令 + Recipe/Schedule 子命令 | 命令系统 + 任务自动化 |
| [03-技术架构](./03-architecture.md) | Rust + Tokio、MCP 7 种传输、4 层 Inspector、SmartApprove、Recipe、HTTP 服务架构 | MCP 传输抽象 + 安全管道 + 权限判断 |
| [04-扩展与工具](./04-extensions.md) | 11 个 Platform Extension、4 个 MCP 内置服务器、工具执行管线 | 工具注册 + MCP 兼容接口 |
| [EVIDENCE.md](./EVIDENCE.md) | 源码分析证据（PostHog、SecurityManager、MCP） | -- |

## 如何使用本系列

1. **快速定位差距**：从 [01-概述](./01-overview.md) 的能力矩阵找到你关心的领域
2. **深入架构**：进入对应章节查看 Goose 的实现细节和工程权衡
3. **对照改进**：每个章节的"Qwen Code 对标"分析提供具体的实现建议
4. **查阅证据**：所有技术声明在 [EVIDENCE.md](./EVIDENCE.md) 中有源码路径支撑

## 核心数据

| 指标 | 数值 |
|------|------|
| **核心代码** | ~55k 行 Rust |
| **CLI 命令** | 14 个 |
| **斜杠命令** | 16 个 |
| **Platform Extension** | 11 个（~20 个工具） |
| **MCP Builtin Server** | 4 个（~18 个工具） |
| **MCP 传输类型** | 7 种 |
| **安全 Inspector** | 4 层管道 |
| **LLM 提供商** | 58+ |
| **运行模式** | 4 种（含 SmartApprove） |

## 分析方法

- **源码分析**：Apache-2.0 开源仓库完整 Rust 源码分析（~55k 行核心代码）
- **官方文档**：[block.github.io/goose](https://block.github.io/goose/docs/quickstart/)
- **EVIDENCE.md**：关键数据点的源码路径和配置值记录

## 相关文档

- [Qwen Code 改进建议报告（Claude Code 对比）](../../../docs/comparison/qwen-code-improvement-report.md)
- [功能矩阵对比](../../../docs/comparison/features.md)

**仓库：** [github.com/block/goose](https://github.com/block/goose)
**Stars：** 34k | **许可证：** Apache-2.0 | **语言：** Rust
**治理：** 已捐赠 Linux Foundation Agentic AI Foundation (AAIF)
