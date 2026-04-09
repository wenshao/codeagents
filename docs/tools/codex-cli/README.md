# Codex CLI 源码分析（面向 Code Agent 开发者）

> 本系列文档基于 Codex CLI v0.116.0 二进制逆向分析（137MB Rust ELF）和官方文档交叉验证，提炼出对 Qwen Code、Gemini CLI 等 Code Agent 开发者有参考价值的架构设计和实现模式。
>
> **阅读对象**：正在开发或改进 CLI Code Agent 的工程师
>
> **不是**：Codex CLI 用户手册或功能介绍

## 文档索引

| 文档 | 开发者关注点 | Qwen Code 对标 |
|------|------------|----------------|
| [01-概述与对标](./01-overview.md) | 核心能力矩阵、架构差异速查、可借鉴 vs 不可复制 | 功能差距一览 |
| [02-命令系统](./02-commands.md) | 15 CLI 子命令 + 28 斜杠命令 + 9 工具 + 52 Feature Flag + 配置体系 | review 子命令 + MCP 双向 + 会话 resume/fork |
| [03-技术架构](./03-architecture.md) | Rust 原生构建、多平台沙箱、App-Server JSON-RPC（90+ 方法）、Cloud 执行 | 沙箱安全模型 + IDE 集成 + Feature Flag |
| [EVIDENCE.md](./EVIDENCE.md) | 二进制分析原始证据 | — |

## 如何使用本系列

1. **快速定位差距**：从 [01-概述](./01-overview.md) 的能力矩阵找到你关心的领域
2. **深入架构**：进入对应章节查看 Codex CLI 的实现细节和 Qwen Code 对标分析
3. **对照改进**：每个章节的"Qwen Code 对标"段落提供具体实现建议
4. **查阅证据**：所有技术声明在 [EVIDENCE.md](./EVIDENCE.md) 中有二进制分析和官方文档支撑

## Codex CLI 核心数据

| 维度 | 数据 |
|------|------|
| **仓库** | [github.com/openai/codex](https://github.com/openai/codex) |
| **许可证** | Apache-2.0 |
| **Stars** | ~68k |
| **技术栈** | Rust 原生二进制（~137MB）+ Node.js 薄启动层（~6KB） |
| **默认模型** | gpt-5.1-codex |
| **CLI 子命令** | 15 个（exec, review, cloud, mcp, app-server, resume, fork 等） |
| **TUI 斜杠命令** | 28 个 |
| **代理工具** | 9 个（LocalShellCall, ApplyPatch, WebSearchCall 等） |
| **Feature Flag** | 52 个（10 stable, 4 experimental, 18 under-dev） |
| **审批模式** | 5 种（untrusted, on-request, on-failure, never, granular） |
| **沙箱级别** | 4 种（read-only, restricted-read-access, workspace-write, danger-full-access） |
| **App-Server** | 90+ JSON-RPC 方法 |

## Codex CLI 最具参考价值的 5 个特性

| 特性 | 为什么值得参考 | Qwen Code 现状 |
|------|-------------|---------------|
| **默认沙箱 + 网络隔离** | 唯一默认启用沙箱的主流 Agent，CI/CD 场景安全性最高 | 无沙箱 |
| **`codex review` 独立子命令** | 代码审查可脱离交互 TUI，CI 管道可脚本化调用 | 无审查功能 |
| **MCP 双向支持** | 既能调用外部工具，也能被其他 Agent 调用 | 仅 MCP 客户端 |
| **App-Server JSON-RPC** | IDE 集成标准化协议，90+ 方法覆盖全部能力 | 无 IDE 协议 |
| **会话 resume/fork** | 跨时间恢复工作 + 分叉探索不同方案 | 无会话持久化 |

## 分析方法

- **二进制分析**：v0.116.0 Rust ELF static-pie x86-64（137MB），通过 `strings`、`codex --help`、`codex features list` 等提取
- **官方文档**：[developers.openai.com/codex](https://developers.openai.com/codex)
- **源码仓库**：[github.com/openai/codex](https://github.com/openai/codex)（Apache-2.0 开源）

## 相关文档

- [Qwen Code 改进建议报告（Claude Code 对比）](../../../docs/comparison/qwen-code-improvement-report.md)
- [功能对比矩阵](../../comparison/features.md)
- [架构深度对比](../../comparison/architecture-deep-dive.md)
