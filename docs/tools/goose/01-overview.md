# 1. Goose 概述

**开发者：** Block（原 Square）
**许可证：** Apache-2.0
**仓库：** [github.com/block/goose](https://github.com/block/goose)
**文档：** [block.github.io/goose](https://block.github.io/goose/docs/quickstart/)
**版本：** v1.28.0（源码: `ui/desktop/package.json`，`Cargo.toml` workspace version 1.0.0）
**最后更新：** 2026-03

> **免责声明**: 以下数据基于 2026-03-28 源码分析（commit `0ace570`），可能已过时。
> Goose 已捐赠给 Linux Foundation Agentic AI Foundation (AAIF)。

## 概述

Goose 是 Block（原 Square）开发的开源 AI 代理框架，**完全用 Rust 编写**（核心 ~55k 行）。它支持 58+ LLM 提供商，基于 MCP（模型上下文协议）构建扩展系统，提供 CLI、Web、桌面（Electron）三种客户端。核心设计理念是 **MCP 原生**：所有工具通过 MCP 服务器提供，实现标准化的工具生态。

主要特点：
- **Rust 原生**：高性能单二进制分发，启动快、内存低
- **MCP 原生架构**：所有工具通过 MCP 协议提供，标准化扩展
- **58+ LLM 提供商**：业界最广泛的模型支持
- **11 个 Platform Extension**：内置开发者工具（shell、edit、write、tree 等）
- **4 个 MCP 内置服务器**：autovisualiser、computercontroller、memory、tutorial
- **Recipe 系统**：YAML 定义的可复用任务模板 + 定时调度
- **安全系统**：多层检查器管道（Pattern + ML + LLM 审查 + 重复检测）
- **Smart Approve**：LLM 辅助的智能权限判断

## 核心功能

### 基础能力
- **Rust 原生性能**：单二进制分发，Tokio 异步运行时（源码: `crates/goose/`）
- **MCP 原生扩展**：7 种传输类型（Stdio、StreamableHttp、Builtin、Platform、Frontend、InlinePython、SSE[已废弃]）
- **58+ LLM 提供商**：Anthropic、OpenAI、Google、AWS Bedrock、Azure、Ollama 等
- **多客户端**：CLI（`goose-cli`）、HTTP 服务器（`goose-server`，Axum）、Electron 桌面应用
- **Recipe 系统**：YAML/JSON 定义任务模板，支持参数化、子 Recipe、deeplink
- **调度系统**：Cron 定时执行 Recipe（源码: `crates/goose-cli/src/commands/schedule.rs`）
- **ACP 协议**：Agent Client Protocol，桌面/IDE 集成标准

### 独特功能
- **Platform Extension**：进程内直接访问代理上下文，无需 MCP 传输开销
- **AdversaryInspector**：LLM 审查工具调用的对抗性（opt-in，`~/.config/goose/adversary.md`）
- **PermissionJudge**：LLM 自动判断工具调用只读/写入属性
- **Recipe DeepLink**：`goose://` 协议触发 Recipe 执行
- **Gateway**：外部平台集成（pair 命令配对）
- **Term 模式**：终端集成会话（`goose term`）
- **本地推理**：Whisper 语音、llama.cpp 本地模型（candle）

## 安装

```bash
# Homebrew（推荐）
brew install block/tap/goose

# Cargo
cargo install goose-cli

# 或从 GitHub Release 下载
# https://github.com/block/goose/releases

# 启动交互式会话
goose

# 使用特定模型
goose --model claude-opus-4
```

## 四种运行模式

| 模式 | 行为 | 源码 |
|------|------|------|
| **Auto**（默认） | 自动批准所有工具调用 | `crates/goose/src/config/goose_mode.rs` |
| **Approve** | 每个工具调用都需确认 | 同上 |
| **SmartApprove**（推荐） | LLM 判断只读/写入，仅写入操作需确认 | `crates/goose/src/permission/permission_judge.rs` |
| **Chat** | 仅聊天，不执行工具 | 同上 |

## 优势

1. **Rust 性能**：启动快、内存低、单二进制分发
2. **提供商最多**：58+ LLM 提供商支持
3. **MCP 原生**：所有扩展基于标准协议
4. **Recipe 系统**：可复用任务模板 + 定时调度
5. **安全设计**：环境变量白名单 + 对抗性检测 + ML 分类器
6. **Apache-2.0**：企业友好许可（已捐赠 Linux Foundation）
7. **桌面应用**：Electron 跨平台 GUI

## 劣势

1. **Rust 生态**：插件开发门槛高于 TypeScript/Python
2. **无 Git 原生集成**：依赖 shell 工具实现 Git 操作
3. **文档不足**：相比代码能力，文档覆盖有限
4. **复杂性**：功能丰富但学习曲线较陡

## 使用场景

- **最适合**：需要多提供商灵活性、MCP 生态用户、自动化 Recipe
- **适合**：企业部署（Rust 性能 + Apache 许可）
- **不太适合**：想要简单工具的用户、需要深度 Git 集成

## 资源链接

- [快速入门](https://block.github.io/goose/docs/quickstart/)
- [GitHub](https://github.com/block/goose)
- [Recipe 文档](https://block.github.io/goose/docs/recipes/)
