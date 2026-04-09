# 3. Goose 技术架构——开发者参考

> 本文分析 Goose 的核心架构：Rust + Tokio 异步运行时、MCP 原生扩展管线、4 层安全 Inspector 管道、SmartApprove 权限系统、Recipe 任务引擎、多客户端 HTTP 服务架构。这些模式体现了"系统语言构建 Agent"的工程权衡。
>
> **Qwen Code 对标**：MCP 传输抽象（7 种类型 vs 单一 Stdio）、安全管道（4 层 Inspector vs 权限规则）、SmartApprove（LLM 权限判断，Qwen Code 无对标）、Recipe 自动化（Qwen Code 无对标）

## 为什么 Goose 的架构值得研究

Goose 选择了一条与主流 Code Agent 完全不同的技术路线：

| 设计选择 | 主流方案（Claude Code/Qwen Code） | Goose 方案 | 工程影响 |
|---------|-------------------------------|-----------|---------|
| 语言 | TypeScript/Python | Rust | 性能优/开发慢/生态窄 |
| 工具架构 | 内嵌函数调用 | MCP 原生 | 互通好/开销略高 |
| 客户端架构 | CLI 直接嵌入 Agent | HTTP 服务（goosed） | 多客户端/额外延迟 |
| 权限判断 | 静态规则 | LLM 智能判断（SmartApprove） | 灵活/不确定性 |
| 任务自动化 | 无原生支持 | Recipe + Cron Schedule | 无人值守能力 |

这些选择不是"更好"或"更差"，而是不同的工程权衡。理解这些权衡，有助于 Qwen Code 开发者在自己的架构中做出有意识的选择。

> 以下基于 v1.28.0 源码分析（commit `0ace570`，2026-03-21）。

---

## 1. 运行时与二进制格式

| 项目 | 详情 |
|------|------|
| **语言** | Rust（~55k 行核心代码） |
| **异步运行时** | Tokio（多线程调度器） |
| **HTTP 框架** | Axum + Tower（中间件栈） |
| **MCP SDK** | rmcp（Rust 原生 MCP 实现） |
| **CLI 框架** | clap（derive 宏，编译期命令校验） |
| **Token 计算** | tiktoken-rs |
| **AST 解析** | tree-sitter（9 种语言：Rust/Python/TypeScript/Go/Java/C/C++/Ruby/JavaScript） |
| **本地推理** | candle（Whisper 语音识别）、llama-cpp-2（本地 LLM） |
| **密钥管理** | keyring（系统密钥链集成） |
| **二进制分发** | 单文件可执行（`cargo build --release`） |
| **安装方式** | Homebrew / Cargo / GitHub Release / Desktop installer |

### Rust 工程优势

```
性能对比（估算）:
  启动时间: Goose ~100ms vs Claude Code ~500ms (Bun) vs Qwen Code ~1s (Node.js)
  内存占用: Goose ~50MB vs TypeScript Agent ~150-300MB
  二进制大小: Goose ~30MB vs Claude Code ~227MB
```

> **注意**: 以上为估算值，实际因环境和版本而异。

**开发者启示**：Rust 的零成本抽象在 Agent 场景的优势主要体现在**启动速度**和**内存占用**。但 Agent 的主要延迟来自 LLM API 调用（通常 1-10 秒），启动时间优势在长会话中被稀释。Rust 的真正价值是**编译期安全**——类型系统在编译时捕获工具参数错误、权限逻辑错误等，减少运行时崩溃。

---

## 2. 多客户端 HTTP 服务架构

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  CLI Client  │  │Desktop(Elec)│  │  Web Client  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────┬───────┴────────┬───────┘
                │                │
        ┌───────▼────────┐      │
        │   goosed        │◄─────┘
        │ (Axum HTTP)     │
        │ REST API        │
        └───────┬─────────┘
                │
        ┌───────▼─────────┐
        │  AgentManager    │
        │ (LRU, max 100)  │
        └───────┬─────────┘
                │
        ┌───────▼─────────┐
        │     Agent        │
        │  (per-session)   │
        └─────────────────┘
```

源码: `crates/goose-server/`（Axum 路由定义）

**与 Claude Code 的关键差异**：Claude Code 的 CLI 直接嵌入 Agent 进程——用户输入 → Agent 循环 → 输出，零网络开销。Claude Code 后来通过 WebSocket Bridge 添加了远程控制能力，但这是在 CLI-first 架构上的补丁。

Goose 从一开始就将 Agent 放在 HTTP 服务后面（`goosed` 进程），所有客户端通过 REST API 通信。这意味着：
- CLI、Desktop、Web 共享同一个 Agent 实例和会话
- 多客户端同时连接（如桌面端和 IDE 插件）
- Agent 进程独立于客户端生命周期

**Qwen Code 对标**：如果 Qwen Code 计划支持 IDE 插件或 Web 界面，Goose 的 HTTP 服务架构值得参考——前期多投入一层 HTTP 抽象，后期多客户端集成的成本显著降低。

### AgentManager

源码: `crates/goose-server/`

- LRU 缓存，最多维护 100 个活跃会话
- 每个会话拥有独立的 Agent 实例
- Agent 创建时初始化 Provider + ExtensionManager + Inspector 管道

---

## 3. MCP 原生扩展管线

源码: `crates/goose/src/agents/extension.rs`（`ExtensionConfig` 枚举）

### 7 种传输类型的实现

| 类型 | 传输方式 | 实现细节 | 典型延迟 |
|------|---------|---------|---------|
| `Platform` | 直接函数调用 | Agent 进程内，共享内存上下文 | ~0ms |
| `Builtin` | `tokio::io::DuplexStream` | 进程内 MCP 服务器，双向流通信 | ~1ms |
| `Stdio` | stdin/stdout | 子进程标准 I/O，JSON-RPC 2.0 | ~10ms |
| `StreamableHttp` | HTTP Streamable MCP | 远程 MCP 服务器，支持 SSE 流 | ~50ms+ |
| `Frontend` | UI 桥接 | 桌面 UI 提供的工具（截图、剪贴板等） | — |
| `InlinePython` | uvx 子进程 | 通过 `uvx` 运行内联 Python 代码 | ~100ms+ |
| `Sse` | **已废弃** | 保留仅为配置兼容，运行时转为 StreamableHttp | — |

**开发者启示**：`Platform` 传输是 Goose 在 MCP 原生架构中保留性能的关键设计。它允许核心工具（developer、analyze 等）以零开销运行在 Agent 进程内，同时对外暴露 MCP 兼容接口。`Builtin` 传输则使用 Tokio 的 `DuplexStream`——进程内双向流，避免了子进程创建和 I/O 序列化的开销，比 `Stdio` 快约 10 倍。

### ExtensionManager 生命周期

源码: `crates/goose/src/agents/extension_manager.rs`

```
配置加载（config.yaml）
    │
    ▼
ExtensionConfig::resolve()
    ├── 合并环境变量
    ├── 替换 keyring 密钥引用
    └── 阻止 31 个危险环境变量（Envs 结构）
    │
    ▼
创建 MCP 客户端（按传输类型）
    │
    ▼
list_tools() → 工具发现（带版本追踪缓存）
    │
    ▼
call_tool() → 按工具名前缀分发到正确扩展
```

### 环境变量安全

源码: `crates/goose/src/agents/extension_manager.rs`（`Envs` 结构）

ExtensionManager 阻止 31 个危险环境变量传递到扩展进程：

```
PATH, LD_PRELOAD, LD_LIBRARY_PATH, DYLD_LIBRARY_PATH,
PYTHONPATH, NODE_PATH, GOPATH, CARGO_HOME,
HOME, USER, SHELL, TERM, TMPDIR, ...
```

**Qwen Code 对标**：这个白名单机制简单有效——防止 MCP 扩展通过环境变量获取用户敏感信息或篡改运行时路径。Qwen Code 的 MCP 扩展目前未过滤环境变量，建议参考实现。

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
    env_keys: ["API_KEY"]   # 从 keyring 注入
    timeout: 60
  remote-api:
    enabled: true
    type: streamable_http
    name: remote-api
    url: "https://api.example.com/mcp"
    headers:
      Authorization: "Bearer ${API_TOKEN}"
```

---

## 4. 安全系统——4 层 Inspector 管道

源码: `crates/goose/src/tool_inspection.rs`（`ToolInspector` trait）

Goose 的安全系统是一个**可组合的 Inspector 管道**——每个工具调用依次通过 4 层检查器，任何一层可以 `approved`、`RequireApproval`（需确认）或 `denied`（拒绝）。

```
工具调用请求
    │
    ▼
┌─ SecurityInspector ─────────────────────────────┐
│  PromptInjectionScanner                         │
│  ├── PatternMatcher: 预定义威胁模式匹配          │
│  └── ClassificationClient: HuggingFace ML 分类   │
│  阈值: 0.8 (SECURITY_PROMPT_THRESHOLD)          │
│  仅扫描 shell 工具调用                           │
│  超阈值 → RequireApproval                        │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─ AdversaryInspector ────────────────────────────┐
│  Opt-in: ~/.config/goose/adversary.md 激活       │
│  使用 LLM 审查工具调用是否对抗性                  │
│  审查范围: shell + computercontroller             │
│  Fail-open: LLM 失败时允许执行                    │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─ PermissionInspector ───────────────────────────┐
│  1. 检查 GooseMode (Auto=全允许, Chat=跳过工具)  │
│  2. 用户自定义权限 (AlwaysAllow/NeverAllow/Ask)  │
│  3. SmartApprove: read_only_hint 或 LLM 判断     │
│  4. 扩展管理操作始终需确认                        │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─ RepetitionInspector ───────────────────────────┐
│  追踪连续相同工具调用（名称+参数完全一致）        │
│  超过 max_repetitions → 阻止                    │
│  CLI: --max-tool-repetitions                     │
└─────────────────────────────────────────────────┘
    │
    ▼
ExtensionManager.call_tool() → 执行
```

### 与 Claude Code 安全模型对比

| 维度 | Goose | Claude Code |
|------|-------|-------------|
| **注入检测** | Pattern + ML 分类器 | 23 项 Bash 安全检查（tree-sitter AST） |
| **对抗审查** | LLM AdversaryInspector（opt-in） | 无单独对抗审查 |
| **权限模型** | 4 种模式 + LLM SmartApprove | 5 层设置 + 沙箱 + 24 种 Hook |
| **重复检测** | RepetitionInspector | 无 |
| **环境隔离** | 环境变量白名单（31 个） | macOS sandbox-exec / Linux 容器 |
| **架构模式** | Inspector 管道（可组合） | 分散在各工具内部 |

**Qwen Code 对标**：Goose 的 Inspector 管道模式值得借鉴——将安全检查定义为统一的 `ToolInspector` trait，每个检查器独立实现、可组合、可测试。相比将安全逻辑分散在各工具内部（Claude Code 的 BashTool 23 项检查），管道模式更容易添加新的安全层。

### SmartApprove 详解

源码: `crates/goose/src/permission/permission_judge.rs`

SmartApprove 是 Goose 最创新的权限机制：

1. **首次调用**：创建合成工具 `platform__tool_by_tool_permission`，将工具调用信息发送给 LLM，获取只读/写入分类
2. **结构化输出**：LLM 返回 `{ "classification": "read_only" | "write" }` 格式
3. **缓存**：分类结果持久化到 `~/.config/goose/permission.yaml`（`smart_approve` 类别）
4. **后续调用**：相同工具+相似参数直接查缓存，不再调用 LLM

```yaml
# ~/.config/goose/permission.yaml 示例
permissions:
  - tool: "developer__shell"
    level: "AlwaysAllow"
    category: "user"          # 用户显式设置
  - tool: "developer__shell"
    args_pattern: "ls *"
    level: "AlwaysAllow"
    category: "smart_approve"  # LLM 判断并缓存
```

---

## 5. Recipe 系统——YAML 任务自动化

源码: `crates/goose/src/recipe/`

Recipe 是 Goose 的可复用任务模板系统，用 YAML 定义"做什么"，用 minijinja 模板引擎做参数化。

### Recipe 格式

```yaml
version: "1.0.0"
title: "Code Review"
description: "自动审查 PR 代码质量"
instructions: |
  请审查 {{branch}} 分支的代码变更，重点关注：
  1. 安全问题
  2. 性能问题
  3. 代码风格
extensions:
  - type: builtin
    name: developer
settings:
  goose_provider: anthropic
  goose_model: claude-sonnet-4-20250514
parameters:
  - name: branch
    type: string
    required: true
    default: "main"
sub_recipes:
  - name: lint-check
    path: ./lint-recipe.yaml
```

### 执行流程

```
Recipe 发现 (local_recipes.rs)
    │ 搜索当前目录 + ~/.config/goose/recipes/
    ▼
模板渲染 (template_recipe.rs)
    │ minijinja 解析 {{param}} → 值替换
    ▼
验证 (validate_recipe.rs)
    │ 检查 schema、required 参数、扩展有效性
    ▼
构建 (build_recipe.rs)
    │ 合并 sub_recipes、解析扩展配置
    ▼
执行 (Agent.reply())
    │ 按 instructions 执行任务
    ▼
输出 (text/json/stream-json)
```

**Qwen Code 对标**：Recipe 系统解决了一个常见痛点——Agent 完成了复杂任务后，用户无法轻松复用。Claude Code 通过 Skill 文件部分解决了这个问题，但 Skill 是 prompt 级别的复用。Goose 的 Recipe 是**完整任务定义**——包含模型选择、扩展配置、参数化、子任务编排，加上 Cron Schedule 实现定时执行。对 Qwen Code 来说，Recipe 级别的任务模板比 Skill 更适合企业自动化场景。

---

## 6. 桌面应用架构

源码: `ui/desktop/`

| 组件 | 技术 |
|------|------|
| 框架 | Electron 41 + React 19 |
| 构建 | Electron Forge + Vite |
| UI 库 | Radix UI + Tailwind CSS + Framer Motion |
| 路由 | React Router |
| 通信 | 通过 `goosed` HTTP API（REST） |
| 协议 | Agent Client Protocol（`crates/goose-acp/`） |
| 分发 | macOS (.app arm64/x64)、Linux (.deb/.rpm/.flatpak)、Windows (.zip) |
| DeepLink | `goose://` 自定义协议 |

**架构特点**：桌面应用纯粹是 `goosed` HTTP 服务的前端——所有 Agent 逻辑在 Rust 后端运行，Electron 仅负责 UI 渲染和用户交互。这与 Cursor（Electron 内嵌 Agent 逻辑）形成对比，Goose 的方案更容易测试和调试后端逻辑。

---

## 7. 可观测性

### OpenTelemetry

- 完整 OTLP 支持：traces + metrics + logs
- 通过标准 `OTEL_*` 环境变量配置
- 默认禁用（需配置端点）

### Langfuse（可选 LLM 可观测）

- `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` 配置
- 每 5 秒批量发送 trace 数据
- 追踪 LLM 调用延迟、token 消耗、工具执行时间

### PostHog 遥测

- **默认关闭（opt-in）**
- 采集：OS、架构、版本、provider、model、extensions_count、session 统计
- 隐私保护：用户路径/API keys/emails 自动清洗为 `[REDACTED]`
- Opt-out：`GOOSE_TELEMETRY_OFF=1` 或 `GOOSE_TELEMETRY_ENABLED=false`

**Qwen Code 对标**：Goose 的可观测性栈（OpenTelemetry + Langfuse + PostHog）覆盖了三个层面——系统级指标（OTLP）、LLM 调用分析（Langfuse）、产品使用统计（PostHog）。这为 Qwen Code 提供了完整的可观测性参考架构。特别是 Langfuse 集成——它让开发者可以分析 LLM 调用的 cost/latency/quality，这对模型选择和 prompt 优化非常有价值。

---

## 8. 架构总结对比

| 维度 | Goose | Claude Code | Qwen Code |
|------|-------|-------------|-----------|
| **语言** | Rust (~55k 行) | TypeScript (~1800 文件) | TypeScript (~500 文件) |
| **运行时** | Tokio (Rust) | Bun → Rust 原生 | Node.js |
| **工具架构** | MCP 原生（7 种传输） | 内嵌 + MCP 扩展 | 内嵌 + MCP 扩展 |
| **客户端** | HTTP 服务 (goosed) | CLI 直接嵌入 | CLI 直接嵌入 |
| **安全** | 4 层 Inspector 管道 | 沙箱 + 23 项 Bash 检查 | 权限规则 |
| **权限** | SmartApprove (LLM) | 5 层设置体系 | 4 种模式 |
| **任务自动化** | Recipe + Cron | Skill + Kairos | Skill |
| **可观测性** | OTLP + Langfuse + PostHog | 内部遥测 | 基础日志 |
| **LLM 支持** | 58+ 提供商 | Claude only | ~10 提供商 |
| **桌面** | Electron | 无（CLI only） | 无（CLI only） |
