# Goose

**开发者：** Block
**许可证：** Apache-2.0
**仓库：** [github.com/block/goose](https://github.com/block/goose)
**文档：** [block.github.io/goose](https://block.github.io/goose/docs/quickstart/)
**Stars：** 约 27k+
**最后更新：** 2026-03

## 概述

Goose 是 Block（原 Square）开发的开源 AI 代理框架，**完全用 Rust 编写**（核心 ~55k 行 Rust）。它支持 58+ LLM 提供商，基于 MCP（模型上下文协议）构建扩展系统，提供 CLI、Web、桌面（Electron）三种客户端。

## 核心功能

### 基础能力
- **Rust 原生**：高性能单二进制分发
- **58+ LLM 提供商**：Anthropic、OpenAI、Google、AWS Bedrock、Azure、Ollama 等
- **MCP 原生扩展**：所有工具通过 MCP 服务器提供
- **多客户端**：CLI（goose-cli）、HTTP 服务器（goosed）、Electron 桌面应用
- **Recipe 系统**：YAML/JSON 定义的可复用任务模板
- **调度系统**：Cron 定时执行 Recipe

### 独特功能
- **Agent Communication Protocol (ACP)**：自研代理通信协议
- **Smart Approve 模式**：仅敏感操作需要确认
- **Recipe 参数化**：模板变量 + JSON Schema 验证
- **安全检查器**：对抗性输入检测、重复行为监控
- **多格式文件解析**：内置 DOCX、PDF、XLSX 解析
- **本地 AI 推理**：Whisper 语音、llama.cpp 本地模型

## 技术架构（源码分析）

### 项目结构

```
goose/
├── crates/
│   ├── goose/           # 核心代理框架（~55k 行 Rust）
│   ├── goose-cli/       # CLI 入口
│   ├── goose-server/    # HTTP/WebSocket 服务器（goosed）
│   ├── goose-acp/       # Agent Communication Protocol
│   ├── goose-mcp/       # 内置 MCP 服务器实现
│   └── goose-test/      # 测试工具
└── ui/desktop/          # Electron 桌面应用
```

### 核心架构

```
客户端 (CLI / Desktop / Web)
    │
    ▼
goosed (Axum HTTP 服务器)
    │
    ▼
AgentManager (LRU 缓存, 最多 100 会话)
    │
    ▼
Agent (会话级代理)
    ├── Provider (58+ LLM 提供商)
    ├── ExtensionManager (MCP 客户端管理)
    │   ├── Stdio 传输（子进程）
    │   ├── StreamableHttp 传输
    │   └── Builtin 传输（进程内）
    ├── ToolExecution (权限检查 + 执行)
    └── Scheduler (Cron 定时任务)
```

### 技术栈
- **语言**：Rust
- **异步运行时**：Tokio
- **HTTP 框架**：Axum + Tower
- **MCP SDK**：rmcp（Rust MCP）
- **Token 计算**：tiktoken-rs
- **AST 解析**：tree-sitter（Go/Java/JS/Kotlin/Python/Ruby/Rust/Swift/TS）
- **本地推理**：candle（Whisper）、llama-cpp-2
- **密钥管理**：keyring（系统密钥链）
- **桌面**：Electron

### 四种运行模式

| 模式 | 说明 |
|------|------|
| **Auto** | 自动批准所有工具调用 |
| **Approve** | 每个工具调用都需确认 |
| **SmartApprove**（默认） | 仅敏感操作需确认 |
| **Chat** | 仅聊天，不执行工具 |

### 安全系统

- **环境变量白名单**：31 个危险变量被禁止注入（PATH、LD_PRELOAD 等）
- **AdversaryInspector**：对抗性输入检测
- **RepetitionInspector**：重复行为监控
- **权限管理器**：AllowOnce / AlwaysAllow / NeverAllow

## 安装

```bash
# Homebrew（推荐）
brew install block/tap/goose

# 或从 GitHub Release 下载
# https://github.com/block/goose/releases

# 启动
goose
```

## 支持的提供商（58+）

| 类别 | 提供商 |
|------|--------|
| **主要** | Anthropic, OpenAI, Google Gemini |
| **云服务** | AWS Bedrock, Azure, GCP Vertex AI, Databricks |
| **推理** | Groq, Cerebras, Together, DeepInfra |
| **兼容** | OpenRouter, LiteLLM, Ollama |
| **其他** | GitHub Copilot, xAI, Venice, Snowflake |

## 优势

1. **Rust 性能**：启动快、内存低、单二进制分发
2. **提供商最多**：58+ LLM 提供商支持
3. **MCP 原生**：所有扩展基于标准协议
4. **Recipe 系统**：可复用任务模板 + 定时调度
5. **安全设计**：环境变量白名单 + 对抗性检测
6. **Apache-2.0**：企业友好许可

## 劣势

1. **Rust 生态**：插件开发门槛高
2. **无 Git 原生集成**：依赖 MCP 扩展实现
3. **文档不足**：相比代码能力，文档覆盖有限
4. **复杂性**：功能丰富但学习曲线较陡

## CLI 命令

```bash
# 启动交互式会话
goose

# 使用特定模型
goose --model claude-opus-4

# 执行 Recipe
goose run recipe.yaml

# 配置
goose config

# 管理扩展
goose extension list
goose extension add <name>

# 调度任务
goose schedule create --recipe task.yaml --cron "0 9 * * *"
```

## 配置

```yaml
# ~/.config/goose/config.yaml
provider: anthropic
model: claude-sonnet-4
mode: smart_approve
extensions:
  - name: developer
    type: builtin
  - name: memory
    type: builtin
```

## 使用场景

- **最适合**：需要多提供商灵活性、MCP 生态用户、自动化 Recipe
- **适合**：企业部署（Rust 性能 + Apache 许可）
- **不太适合**：想要简单工具的用户、需要深度 Git 集成

## 资源链接

- [快速入门](https://block.github.io/goose/docs/quickstart/)
- [GitHub](https://github.com/block/goose)
- [Recipe 文档](https://block.github.io/goose/docs/recipes/)

## 交互式斜杠命令（16 个，源码：`crates/goose-cli/src/session/input.rs`）

> 从 `handle_slash_command()` 函数和 `print_help()` 函数提取。

| 命令 | 用途 |
|------|------|
| `/help`, `/?` | 显示帮助信息 |
| `/exit`, `/quit` | 退出会话 |
| `/t` | 切换主题（Light/Dark/Ansi 循环） |
| `/t <name>` | 设置指定主题（light/dark/ansi） |
| `/r` | 切换完整工具输出（显示未截断的工具参数） |
| `/mode <name>` | 设置模式（Auto/Approve/SmartApprove/Chat） |
| `/plan <message>` | 进入规划模式，创建执行计划 |
| `/endplan` | 退出规划模式 |
| `/compact` | 压缩对话上下文 |
| `/clear` | 清除聊天历史 |
| `/extension <command>` | 添加 stdio 扩展 |
| `/builtin <names>` | 添加内置扩展 |
| `/prompts [--extension <name>]` | 列出可用提示模板 |
| `/prompt <n> [--info] [key=value...]` | 执行或查看提示模板 |
| `/recipe [filepath]` | 从当前对话生成 Recipe |
| `/summarize` | 压缩上下文（已弃用，用 `/compact`） |

> 来源: `handle_slash_command()` in `crates/goose-cli/src/session/input.rs`
