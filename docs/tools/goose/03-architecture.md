# 3. Goose 技术架构

> 以下基于 v1.28.0 源码分析（commit `0ace570`，2026-03-21）。

## Crate 结构

```
goose/
├── crates/goose/              # 核心代理框架（~55k 行 Rust）
│   └── src/
│       ├── agents/            # Agent + ExtensionManager + Platform Extensions
│       │   ├── agent.rs       # 主代理逻辑
│       │   ├── extension.rs   # ExtensionConfig 枚举（7 种传输类型）
│       │   ├── extension_manager.rs  # 扩展生命周期管理
│       │   └── platform_extensions/  # 11 个内置 Platform Extension
│       ├── config/            # 配置、权限、模式
│       │   ├── goose_mode.rs  # 4 种运行模式
│       │   └── permission.rs  # 权限管理器
│       ├── permission/        # 权限系统
│       │   ├── permission_inspector.rs  # 权限检查管道
│       │   └── permission_judge.rs      # LLM 智能权限判断
│       ├── security/          # 安全系统
│       │   ├── mod.rs         # SecurityManager
│       │   ├── scanner.rs     # PromptInjectionScanner
│       │   ├── security_inspector.rs
│       │   └── adversary_inspector.rs   # LLM 对抗性审查
│       ├── recipe/            # Recipe 系统
│       ├── providers/         # 58+ LLM 提供商
│       └── tool_inspection.rs # ToolInspector 管道
├── crates/goose-cli/         # CLI 二进制
│   └── src/
│       ├── cli.rs             # clap 命令定义
│       ├── commands/          # 命令实现
│       └── session/           # 交互式会话 + 输入处理
├── crates/goose-mcp/         # 内置 MCP 服务器
│   └── src/
│       ├── autovisualiser/    # 图表可视化
│       ├── computercontroller/ # 计算机控制
│       ├── memory/            # 记忆管理
│       └── tutorial/          # 教程
├── crates/goose-server/      # HTTP 服务器（Axum）
├── crates/goose-acp/         # Agent Client Protocol
├── crates/goose-acp-macros/  # ACP 过程宏
├── crates/goose-test/        # 测试工具
├── ui/desktop/               # Electron 桌面应用
└── ui/acp/                   # ACP 类型包（npm）
```

## 核心架构

```
客户端（CLI / Desktop / Web）
    │
    ▼
goosed（Axum HTTP 服务器，crates/goose-server/）
    │
    ▼
AgentManager（LRU 缓存，最多 100 会话）
    │
    ▼
Agent（会话级代理，crates/goose/src/agents/agent.rs）
    ├── Provider（58+ LLM 提供商）
    ├── ExtensionManager（MCP 客户端管理）
    │   ├── Stdio 传输（子进程）
    │   ├── StreamableHttp 传输（远程）
    │   ├── Builtin 传输（进程内 DuplexStream）
    │   ├── Platform 传输（直接函数调用）
    │   ├── Frontend 传输（UI 桥接）
    │   └── InlinePython 传输（uvx 子进程）
    ├── ToolInspector 管道
    │   ├── SecurityInspector（注入检测）
    │   ├── AdversaryInspector（LLM 对抗审查）
    │   ├── PermissionInspector（权限检查）
    │   └── RepetitionInspector（重复检测）
    └── Scheduler（Cron 定时任务）
```

## MCP 原生架构

源码: `crates/goose/src/agents/extension.rs`（`ExtensionConfig` 枚举）

### 7 种传输类型

| 类型 | 传输方式 | 说明 |
|------|---------|------|
| `Stdio` | stdin/stdout | 生成子进程，通过标准输入输出通信 |
| `StreamableHttp` | HTTP Streamable MCP | 连接远程 MCP 服务器 |
| `Builtin` | `tokio::io::DuplexStream` | 进程内运行捆绑的 MCP 服务器 |
| `Platform` | 直接函数调用 | 进程内直接访问代理上下文（无 MCP 传输开销） |
| `Frontend` | UI 桥接 | 桌面 UI 提供的工具 |
| `InlinePython` | uvx 子进程 | 运行内联 Python 代码 |
| `Sse` | **已废弃** | 保留仅为配置兼容 |

### 扩展生命周期

源码: `crates/goose/src/agents/extension_manager.rs`

1. **配置解析**：`ExtensionConfig::resolve()` 合并环境变量、替换 keyring 密钥
2. **客户端创建**：根据传输类型创建对应客户端
3. **工具发现**：`list_tools()` 发现可用工具，带版本追踪缓存
4. **执行**：`call_tool()` 按工具名前缀分发到正确扩展
5. **环境变量清理**：`Envs` 结构阻止 31 个危险环境变量（PATH、LD_PRELOAD、PYTHONPATH 等）

### 扩展配置格式

```yaml
# ~/.config/goose/config.yaml
extensions:
  developer:
    enabled: true
    type: builtin
    name: developer
    display_name: Developer
    timeout: 300
    bundled: true
  my-server:
    enabled: true
    type: stdio
    name: my-server
    cmd: npx
    args: ["-y", "@my/mcp-server"]
    env_keys: ["API_KEY"]
    timeout: 60
```

## 安全系统（多层检查器管道）

源码: `crates/goose/src/tool_inspection.rs`（`ToolInspector` trait）

### SecurityManager

源码: `crates/goose/src/security/mod.rs`

- 管理延迟初始化的 `PromptInjectionScanner`
- 配置标志: `SECURITY_PROMPT_ENABLED`, `SECURITY_COMMAND_CLASSIFIER_ENABLED`, `SECURITY_PROMPT_CLASSIFIER_ENABLED`
- 阈值: 0.8（可通过 `SECURITY_PROMPT_THRESHOLD` 配置）

### PromptInjectionScanner

源码: `crates/goose/src/security/scanner.rs`

两种检测模式：
- **PatternMatcher**：预定义威胁模式匹配
- **ClassificationClient**（可选）：HuggingFace 兼容 ML 端点分类

### AdversaryInspector

源码: `crates/goose/src/security/adversary_inspector.rs`

- **Opt-in**：放置 `~/.config/goose/adversary.md` 文件激活
- 使用 LLM 审查工具调用是否对抗性
- 默认审查 `shell` 和 `computercontroller__automation_script`
- **Fail-open**：LLM 调用失败时允许工具执行

### RepetitionInspector

源码: `crates/goose/src/tool_monitor.rs`

- 追踪连续相同工具调用（相同名称 + 相同参数）
- 可配置 `max_repetitions`（`--max-tool-repetitions` CLI 参数）

### 权限检查管道

源码: `crates/goose/src/permission/permission_inspector.rs`

```
工具调用请求
    │
    ▼
检查 GooseMode：Auto = 全部允许；Chat = 跳过工具
    │
    ▼
检查用户自定义权限（PermissionLevel::AlwaysAllow/NeverAllow/AskBefore）
    │
    ▼
SmartApprove：检查工具注解（read_only_hint）或 LLM 判断
    │  PermissionJudge（LLM 分类只读/写入）
    │  结果缓存到 PermissionManager
    ▼
扩展管理操作始终需要确认
    │
    ▼
结果：approved / needs_approval / denied
```

### PermissionManager

源码: `crates/goose/src/config/permission.rs`

- 持久化到 `~/.config/goose/permission.yaml`
- 三级别: `AlwaysAllow`, `AskBefore`, `NeverAllow`
- 两类别: `user`（显式）, `smart_approve`（LLM 缓存）

## Recipe 系统

源码: `crates/goose/src/recipe/`

```yaml
version: "1.0.0"
title: "Recipe Title"
description: "What this recipe does"
instructions: |
  Detailed instructions for the model
extensions:
  - type: builtin
    name: developer
settings:
  goose_provider: openai
  goose_model: gpt-4o
parameters:
  - name: username
    type: string
    required: true
    default: "guest"
sub_recipes:
  - name: sub-recipe-name
    path: ./sub-recipe.yaml
```

**执行流程：**
1. 发现: `local_recipes.rs` 搜索本地目录
2. 模板渲染: `template_recipe.rs`（minijinja 解析 `{{param}}`）
3. 验证: `validate_recipe.rs`
4. 构建: `build_recipe.rs`

## 桌面应用

源码: `ui/desktop/`

| 组件 | 技术 |
|------|------|
| 框架 | Electron 41 + React 19 |
| 构建 | Electron Forge + Vite |
| UI | Radix UI + Tailwind CSS + Framer Motion |
| 路由 | React Router |
| 通信 | 通过 goose-server（Axum HTTP）的 REST API |
| 协议 | Agent Client Protocol（`crates/goose-acp/`） |
| 分发 | macOS (.app arm64/x64)、Linux (.deb/.rpm/.flatpak)、Windows (.zip) |
| 自定义协议 | `goose://` deeplink |

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Rust |
| 异步运行时 | Tokio |
| HTTP 框架 | Axum + Tower |
| MCP SDK | rmcp（Rust MCP） |
| Token 计算 | tiktoken-rs |
| AST 解析 | tree-sitter（9 种语言） |
| 本地推理 | candle（Whisper）、llama-cpp-2 |
| 密钥管理 | keyring（系统密钥链） |
| CLI 框架 | clap（derive 宏） |
| 桌面 | Electron 41 + React 19 |
