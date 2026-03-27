# Goose 源码深度分析证据

## 基本信息
- 仓库: block/goose, Apache-2.0, Rust, 33k+ stars
- 版本: v1.28.0（源码: `ui/desktop/package.json`，`Cargo.toml` workspace）
- 架构: MCP 原生（所有工具通过 MCP 协议）
- SDK: rmcp (Rust MCP SDK)
- 已捐赠给 Linux Foundation Agentic AI Foundation (AAIF)
- 最后分析: 2026-03-28（commit `0ace570`）

> **免责声明**: 以下基于 2026-03-28 源码分析，可能已过时。

## 遥测系统（源码: crates/goose-cli/src/posthog.rs）

### PostHog
- API key: `phc_RyX5CaY01VtZJCQyhSR5KFh6qimUy81YwxsEpotAftT`
- 端点: `https://us.i.posthog.com/capture/`
- **默认关闭（opt-in）**

### Machine ID
- 生成: `Uuid::new_v4()` 持久化到 `telemetry_installation.json`
- 用作 PostHog distinct_id

### 采集数据（session_started 事件）
- os, arch, version, platform_version
- install_method (homebrew/cargo/desktop/binary)
- interface (CLI/desktop)
- provider, model
- extensions_count, extensions (名称列表)
- session_number, total_sessions, total_tokens
- db_schema_version

### 隐私保护
- 错误消息清洗: 用户路径/API keys/emails/bearer tokens/UUIDs → [REDACTED]
- 属性过滤: key/token/secret/password/credential 键自动移除
- 仅 session_started 和 onboarding_* 事件活跃（error/custom 已禁用）

### Opt-out
- `GOOSE_TELEMETRY_OFF=1` 环境变量
- `GOOSE_TELEMETRY_ENABLED=false` 配置
- Onboarding 事件绕过 opt-in（追踪漏斗）

## 安全系统（源码: crates/goose/src/security/）

### SecurityManager（源码: `security/mod.rs`）
- 管理延迟初始化的 `PromptInjectionScanner`（`OnceLock`）
- 配置标志: `SECURITY_PROMPT_ENABLED`, `SECURITY_COMMAND_CLASSIFIER_ENABLED`, `SECURITY_PROMPT_CLASSIFIER_ENABLED`
- 阈值: 0.8（可通过 `SECURITY_PROMPT_THRESHOLD` 配置）

### PromptInjectionScanner（源码: `security/scanner.rs`）
- 两种检测模式:
  - **PatternMatcher**: 预定义威胁模式匹配
  - **ClassificationClient**: HuggingFace 兼容 ML 端点分类（可选）
- 仅扫描 `shell` 工具调用

### AdversaryInspector（源码: `security/adversary_inspector.rs`）
- **Opt-in**: 放置 `~/.config/goose/adversary.md` 文件激活
- 使用 LLM 审查工具调用是否对抗性
- 默认审查 `shell` 和 `computercontroller__automation_script`
- **Fail-open**: LLM 调用失败时允许工具执行

### RepetitionInspector（源码: `tool_monitor.rs`）
- 追踪连续相同工具调用（相同名称 + 相同参数）
- 可配置 `max_repetitions`（`--max-tool-repetitions` CLI 参数）

### SecurityInspector（源码: `security/security_inspector.rs`）
- 实现 `ToolInspector` trait
- 将 `SecurityResult` 转换为 `InspectionResult`
- 超过阈值时产生 `RequireApproval`

## 权限系统

### GooseMode（源码: `config/goose_mode.rs`）
- 4 种模式: Auto, Approve, SmartApprove (默认), Chat

### PermissionInspector（源码: `permission/permission_inspector.rs`）
检查流程:
1. GooseMode: Auto = 全部允许; Chat = 跳过工具
2. 用户自定义权限（PermissionLevel::AlwaysAllow/NeverAllow/AskBefore）
3. SmartApprove: 工具注解（read_only_hint）或 LLM 判断
4. 扩展管理操作始终需要确认

### PermissionJudge（源码: `permission/permission_judge.rs`）
- 使用 LLM 分类工具调用为只读 vs 写入
- 创建合成工具 `platform__tool_by_tool_permission` 用于结构化输出
- 结果缓存到 PermissionManager

### PermissionManager（源码: `config/permission.rs`）
- 持久化到 `~/.config/goose/permission.yaml`
- 三级别: `AlwaysAllow`, `AskBefore`, `NeverAllow`
- 两类别: `user`（显式）, `smart_approve`（LLM 缓存）
- 31 个危险环境变量阻止列表

## MCP 原生架构（源码: `crates/goose/src/agents/`）

### 7 种传输类型（源码: `agents/extension.rs` — `ExtensionConfig` 枚举）

| 类型 | 传输方式 | 说明 |
|------|---------|------|
| `Stdio` | stdin/stdout | 子进程标准输入输出 |
| `StreamableHttp` | HTTP Streamable MCP | 远程 MCP 服务器 |
| `Builtin` | `tokio::io::DuplexStream` | 进程内捆绑 MCP 服务器 |
| `Platform` | 直接函数调用 | 进程内直接访问（无 MCP 传输开销） |
| `Frontend` | UI 桥接 | 桌面 UI 提供的工具 |
| `InlinePython` | uvx 子进程 | 运行内联 Python 代码 |
| `Sse` | **已废弃** | 保留仅为配置文件兼容 |

### ExtensionManager（源码: `agents/extension_manager.rs`）
- 配置解析: `ExtensionConfig::resolve()` 合并环境变量、替换 keyring 密钥
- 客户端创建: 根据传输类型创建对应客户端
- 工具发现: `list_tools()` + 版本追踪缓存
- 执行: `call_tool()` 按工具名前缀分发
- 环境变量清理: `Envs` 结构阻止 31 个危险变量

## Platform Extension（源码: `crates/goose/src/agents/platform_extensions/mod.rs`）

| 扩展 | 默认启用 | 工具 | 源码 |
|------|---------|------|------|
| **developer** | ✅ | `write`, `edit`, `shell`, `tree` | `platform_extensions/developer/` |
| **analyze** | ✅ | `analyze` | `platform_extensions/analyze/mod.rs` |
| **todo** | ✅ | `todo_write` | `platform_extensions/todo.rs` |
| **apps** | ✅ | `create_app`, `iterate_app`, `delete_app`, `list_apps` | `platform_extensions/apps.rs` |
| **summon** | ✅ | `load`, `delegate` | `platform_extensions/summon.rs` |
| **extensionmanager** | ✅ | `manage_extensions`, `search_available_extensions`, `read_resource`, `list_resources` | `platform_extensions/ext_manager.rs` |
| **tom** | ✅ | （无工具，注入上下文） | `platform_extensions/tom.rs` |
| **chatrecall** | ❌ | `search_sessions` | `platform_extensions/chatrecall.rs` |
| **summarize** | ❌ | `summarize` | `platform_extensions/summarize.rs` |
| **code_execution** | ❌（feature-gated） | 代码执行工具 | `platform_extensions/code_execution.rs` |
| **orchestrator** | ❌（隐藏） | Agent 管理工具 | `platform_extensions/orchestrator.rs` |

## MCP 内置服务器（源码: `crates/goose-mcp/src/`）

| 服务器 | 工具 | 源码 |
|--------|------|------|
| **autovisualiser** | `show_chart`, `render_sankey`, `render_radar`, `render_donut`, `render_treemap`, `render_chord`, `render_map`, `render_mermaid` | `autovisualiser/mod.rs` |
| **computercontroller** | `web_scrape`, `automation_script`, `computer_control`, `xlsx_tool`, `docx_tool`, `pdf_tool` | `computercontroller/mod.rs` |
| **memory** | `remember_memory`, `retrieve_memories`, `remove_memory_category`, `remove_specific_memory` | `memory/mod.rs` |
| **tutorial** | 教程引导工具 | `tutorial/mod.rs` |

## OpenTelemetry
- 完整 OTLP: traces + metrics + logs
- 通过标准 OTEL_* 环境变量配置
- 默认禁用（需配置端点）

## Langfuse（可选 LLM 可观测）
- LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY
- 每 5 秒批量发送 trace 数据
- 默认禁用

## Recipe 系统（源码: `crates/goose/src/recipe/`）
- YAML 定义的任务模板
- `goose run recipe.yaml` 执行
- 支持变量替换（minijinja）、子 Recipe、参数化
- CLI 命令: `goose recipe validate/deeplink/open/list`

## 桌面应用（源码: `ui/desktop/`）
- 框架: Electron 41 + React 19 + Radix UI + Tailwind CSS
- 通信: goose-server（Axum HTTP）REST API
- 协议: Agent Client Protocol（`crates/goose-acp/`）
- 分发: macOS (.app)、Linux (.deb/.rpm/.flatpak)、Windows (.zip)
- 自定义协议: `goose://` deeplink

## Crate 结构

| Crate | 用途 |
|-------|------|
| `crates/goose` | 核心代理框架（~55k 行 Rust） |
| `crates/goose-cli` | CLI 二进制（clap 命令定义） |
| `crates/goose-mcp` | 内置 MCP 服务器（autovisualiser 等） |
| `crates/goose-server` | HTTP 服务器（Axum） |
| `crates/goose-acp` | Agent Client Protocol |
| `crates/goose-test` | 测试工具 |

来源: GitHub 源码 `crates/goose/src/`, `crates/goose-cli/src/` (Rust)
