# 3. Codex CLI 技术架构——开发者参考

> 本文分析 Codex CLI 的核心架构：Rust 原生二进制构建、多平台沙箱实现、App-Server IDE 集成协议、Cloud 执行模型、Feature Flag 系统。这些工程模式大多与模型无关，可在 Qwen Code 等 Agent 中参考借鉴。
>
> **Qwen Code 对标**：Rust vs TypeScript 技术栈选型、沙箱安全模型（默认启用 vs 可选）、App-Server 协议（IDE 集成标准化）、Cloud 执行（best-of-N）、Feature Flag（52 个运行时 vs 无）

## 为什么架构设计比模型选择更具参考价值

Codex CLI 的模型能力（GPT-5 系列、o-系列推理模型）是 OpenAI 独有的，不可复制。但它的**工程架构**——Rust 原生构建、多平台沙箱、JSON-RPC IDE 协议——是通用模式，适用于任何模型的 Code Agent。

### 关键架构差异

| 架构领域 | Codex CLI | Claude Code | Qwen Code | 差距影响 |
|---------|-----------|-------------|-----------|---------|
| 技术栈 | Rust 原生 + Node.js 薄层 | TypeScript + Bun 打包 | TypeScript + Node.js | 性能/安全/开发速度取舍 |
| 二进制体积 | ~137MB（静态 musl） | ~227MB（含 Bun 运行时） | npm 包（无原生二进制） | 分发 + 启动性能 |
| 沙箱 | 默认启用，3 平台原生 | 可选 | 可选（Seatbelt/Docker/Podman） | 安全性 |
| IDE 集成 | App-Server JSON-RPC（90+ 方法） | WebSocket/SSE Bridge | 无 | 编辑器生态 |
| Cloud 执行 | 实验性 best-of-N | Kairos（Always-On） | 无 | 长任务/批量任务 |
| Feature 管理 | 52 运行时 Flag | 22 build-time DCE | 无 | 实验性功能管理 |

### 竞品架构总览

| 组件 | Codex CLI | Claude Code | Gemini CLI | Qwen Code |
|------|----------|-------------|-----------|-----------|
| 运行时 | Rust 原生 | Bun → Rust 原生 | Node.js + esbuild | Node.js |
| UI 框架 | Rust TUI（ratatui 推测） | Ink（自建 fork） | Ink（fork） | Ink（标准） |
| 代码搜索 | 内置 ripgrep | file-index.node（Rust NAPI） | ripgrep 调用 | grep 调用 |
| 沙箱 | Seatbelt/Bubblewrap/Landlock/受限令牌 | 可选沙箱 | 可选沙箱 | 无 |
| 文件修改 | ApplyPatch（批量 diff） | Edit（逐文件替换） | Edit | Edit |

---

## 1. 包结构与启动流程

### npm 包结构

```
@openai/codex (npm)
├── bin/codex.js          # Node.js 启动脚本（~6KB）
├── bin/rg                # ripgrep 入口脚本
└── node_modules/
    └── @openai/codex-linux-x64/   # 平台特定包
        └── vendor/
            └── x86_64-unknown-linux-musl/
                └── codex/codex    # Rust 原生二进制（~137MB）
```

**启动流程**：`codex.js` 检测 `process.platform` + `process.arch` → 解析对应平台包 → `spawn()` 原生二进制并透传所有参数和信号。

### 平台二进制包

| 平台包 | 目标三元组 |
|--------|-----------|
| `@openai/codex-linux-x64` | `x86_64-unknown-linux-musl` |
| `@openai/codex-linux-arm64` | `aarch64-unknown-linux-musl` |
| `@openai/codex-darwin-x64` | `x86_64-apple-darwin` |
| `@openai/codex-darwin-arm64` | `aarch64-apple-darwin` |
| `@openai/codex-win32-x64` | `x86_64-pc-windows-msvc` |
| `@openai/codex-win32-arm64` | `aarch64-pc-windows-msvc` |

**开发者启示**：Codex 的"薄 Node.js 启动层 + 原生 Rust 二进制"模式是一个值得关注的分发架构。用户通过 `npm install -g @openai/codex` 安装，npm 的 `optionalDependencies` 自动选择平台包，`codex.js` 透明地 spawn 原生二进制。这比 Claude Code 的"Bun 编译单文件"方式更清晰，但安装体积更大（137MB 原生包 + npm 元数据）。

**Qwen Code 对标**：Qwen Code 目前是纯 TypeScript/Node.js 包。如果需要提升性能（如文件索引、代码搜索），可以考虑"核心 TypeScript + 关键路径 Rust NAPI 模块"的混合方案，而非全量 Rust 重写。Claude Code 的 `file-index.node`（Rust NAPI fzf）就是这种路线。

---

## 2. 沙箱安全模型——Codex CLI 最大差异化

Codex CLI 的沙箱是其最大的架构差异化——**默认启用，网络默认阻断**。这是其他主流 Agent 都没有做到的。

### 沙箱级别

| 模式 | 网络 | 文件写入 | 文件读取 | 适用场景 |
|------|------|---------|---------|---------|
| `read-only` | 阻断 | 禁止 | 允许（系统路径） | 代码审查、分析 |
| `restricted-read-access` | 阻断 | 禁止 | 受限（Seatbelt 策划） | macOS 专用增强 |
| `workspace-write` | 阻断 | 仅 `$PWD` + `$TMPDIR` | 允许 | 日常开发（`--full-auto` 默认） |
| `danger-full-access` | 允许 | 完全 | 完全 | 仅限测试环境 |

### macOS 沙箱（Seatbelt）

使用 `sandbox-exec` + seatbelt profiles 实现隔离：

| 维度 | 策略 | 说明 |
|------|------|------|
| **网络** | `deny network*` | 完全阻断 |
| **文件写入** | 仅 `$PWD` + `$TMPDIR` | 严格限制 |
| **文件读取** | 系统路径只读 | 允许读取依赖 |
| **进程创建** | 允许 | 在沙箱内 |

### Linux 沙箱

| 方案 | 工具 | 特点 | 适用场景 |
|------|------|------|---------|
| **Bubblewrap**（默认） | `bwrap` | 命名空间隔离，无需 root | 用户空间，兼容性好 |
| **Landlock**（遗留） | 内核 LSM | 内核级文件控制 | 需要内核 5.13+，权限精细 |

### Windows 沙箱（实验性）

使用受限令牌（restricted token）实现隔离，目前为实验性支持。

**Qwen Code 对标**：Codex 的沙箱实现为每个平台使用原生隔离机制，这在 Rust 中实现相对自然（直接调用系统 API）。对于 TypeScript/Node.js 的 Qwen Code，实现等效沙箱有两条路线：
1. **轻量路线**：spawn 子进程时使用 `bwrap`（Linux）或 `sandbox-exec`（macOS）包裹，不需要 Rust
2. **完整路线**：参考 Codex 的 [linux-sandbox](https://github.com/openai/codex/blob/main/codex-rs/linux-sandbox/README.md) Rust 实现，编译为 NAPI 模块嵌入

---

## 3. Feature Flag 系统（52 个）

> 证据：`codex features list` 实时输出，详见 [EVIDENCE.md](./EVIDENCE.md)

Codex CLI 拥有完善的 Feature Flag 系统——52 个标志分为 5 种状态，是 Claude Code（22 个 build-time DCE Flag）之外唯一有系统化 Feature Flag 管理的 Agent。

### 按状态分布

| 状态 | 数量 | 代表性 Flag | 管理方式 |
|------|:----:|-------------|---------|
| **stable** | 10 | shell_tool, fast_mode, multi_agent, enable_request_compression | 默认开启（8 个）或关闭（2 个） |
| **experimental** | 4 | guardian_approval, js_repl, apps, tui_app_server | 用户可手动启用 |
| **under dev** | 18 | codex_hooks, voice_transcription, memories, plugins, enable_fanout | 开发中，默认关闭 |
| **removed** | 8 | collaboration_modes, search_tool, remote_models | 已移除 |
| **deprecated** | 2 | web_search_cached, web_search_request | 已弃用 |

### 完整 Flag 清单

| Flag | 状态 | 默认 | 说明 |
|------|------|------|------|
| `shell_tool` | stable | true | Shell 工具 |
| `shell_snapshot` | stable | true | Shell 状态快照 |
| `fast_mode` | stable | true | 快速模式 |
| `personality` | stable | true | 人格自定义 |
| `multi_agent` | stable | true | 多代理支持 |
| `skill_mcp_dependency_install` | stable | true | Skill MCP 依赖自动安装 |
| `unified_exec` | stable | true | 统一执行模式 |
| `enable_request_compression` | stable | true | 请求压缩 |
| `undo` | stable | false | 撤销功能 |
| `use_legacy_landlock` | stable | false | 旧版 Landlock 沙箱 |
| `guardian_approval` | experimental | false | Guardian 审批系统（安全审查子代理） |
| `js_repl` | experimental | false | JavaScript REPL |
| `prevent_idle_sleep` | experimental | false | 防止空闲休眠 |
| `apps` | experimental | false | ChatGPT Apps/Connectors |
| `tui_app_server` | experimental | false | App-Server 驱动的 TUI |
| `codex_hooks` | under dev | false | Hook 系统 |
| `voice_transcription` | under dev | false | 语音转录 |
| `realtime_conversation` | under dev | false | 实时对话 |
| `memories` | under dev | false | 记忆系统 |
| `plugins` | under dev | false | 插件系统 |
| `enable_fanout` | under dev | false | 扇出并行 |
| `code_mode` | under dev | false | 代码模式 |
| `image_generation` | under dev | false | 图片生成 |
| `apply_patch_freeform` | under dev | false | 自由格式 ApplyPatch |
| `child_agents_md` | under dev | false | 子代理 AGENTS.md |
| `request_permissions_tool` | under dev | false | 权限请求工具 |
| `tool_call_mcp_elicitation` | under dev | false | MCP 交互式参数征询 |
| `collaboration_modes` | removed | true | 协作模式（已移除） |
| `search_tool` | removed | false | 搜索工具（已移除） |
| `web_search_cached` | deprecated | false | 缓存 Web 搜索（已弃用） |

**管理命令**：

```bash
codex features list                          # 查看所有标志
codex features enable realtime_conversation  # 启用指定标志
codex features disable multi_agent           # 禁用指定标志
```

### Codex vs Claude Code Feature Flag 对比

| 维度 | Codex CLI | Claude Code |
|------|----------|-------------|
| 数量 | 52 个 | 22 个 |
| 管理方式 | **运行时**（`codex features enable/disable`） | **编译时** DCE（`bun:bundle` 的 `feature()` 函数） |
| 用户可见 | 全部可见 + 可切换 | 不可见（编译后不存在） |
| 远程控制 | 无 | GrowthBook 远程灰度 |
| 安全性 | 低（`strings` 可提取所有 flag） | 高（未启用的代码在二进制中不存在） |

**Qwen Code 对标**：Qwen Code 缺少统一的 Feature Flag 系统。Codex 的运行时方案更适合开源项目（用户可自行探索实验性功能），Claude Code 的编译时方案更适合商业产品（防止逆向分析未发布功能）。建议 Qwen Code 至少实现运行时 Feature Flag 管理。

---

## 4. App-Server 协议（IDE 集成）

`codex app-server` 启动 JSON-RPC 2.0 服务器，为 IDE 插件提供完整的 Codex 能力接口。支持 stdio（默认）和 WebSocket（`ws://`）两种传输方式。

```bash
codex app-server                              # 启动（stdio 传输）
codex app-server --listen ws://0.0.0.0:8080   # WebSocket 传输
codex app-server generate-ts                  # 生成 TypeScript 类型定义
codex app-server generate-json-schema         # 生成 JSON Schema
```

### 协议方法（90+，二进制提取）

| 命名空间 | 关键方法 | 功能 |
|----------|---------|------|
| `thread/*` | `start`, `resume`, `fork`, `rollback`, `archive`, `compact/start`, `name/set` | 会话线程完整管理（20+ 方法） |
| `turn/*` | `start`, `interrupt`, `steer`, `diff/updated`, `plan/updated` | 对话回合管理 |
| `item/*` | `started`, `completed`, `plan/delta`, `tool/call` | 对话项事件与工具调用 |
| `command/*` | `exec`, `resize`, `terminate`, `write` | 命令执行、终端交互 |
| `account/*` | `read`, `login/start`, `login/completed`, `logout` | 账户认证 |
| `config/*` | `read`, `value/write`, `batchWrite`, `mcpServer/*` | 配置读写 |
| `review/*` | `start` | 代码审查 |
| `tasks/*` | `get`, `list`, `cancel`, `result` | Cloud 任务管理 |
| `fs/*` | `copy`, `remove`, `readDirectory` | 文件系统操作 |
| `model/*` | `list`, `rerouted` | 模型管理 |
| `skills/*` | `list`, `changed`, `config/write` | 技能管理 |
| `plugin/*` | `install`, `list`, `read`, `uninstall` | 插件管理 |
| `notifications/*` | `message`, `progress`, `tools/list_changed` | 通知推送 |
| `resources/*` | `list`, `read`, `subscribe` | MCP 资源管理 |
| `tools/*` | `list`, `call` | 工具列表与调用 |
| `prompts/*` | `list`, `get` | 提示词管理 |

```bash
# 生成类型定义供 IDE 插件开发使用
codex app-server generate-ts > codex-protocol.ts
codex app-server generate-json-schema > codex-protocol.json
```

**开发者启示**：Codex 的 App-Server 提供了 Code Agent IDE 集成的参考标准——90+ 方法覆盖会话管理、工具调用、配置读写、任务管理等全部能力。Claude Code 使用 WebSocket/SSE Bridge 实现类似功能，但协议不如 JSON-RPC 标准化。

**Qwen Code 对标**：Qwen Code 目前无 IDE 集成协议。如果要支持 VS Code 扩展，可以参考 Codex 的 JSON-RPC 方案——特别是 `thread/*`（会话管理）、`turn/*`（对话回合）、`item/*`（工具调用事件）三个核心命名空间。`generate-json-schema` 自动生成类型定义是一个很好的工程实践。

---

## 5. Cloud 执行模型（实验性）

```bash
codex cloud exec "fix all failing tests"   # 提交任务到云端
codex cloud status <TASK_ID>               # 查看任务状态
codex cloud list                           # 列出所有云端任务
codex cloud apply <TASK_ID>                # 将结果 diff 应用到本地
codex cloud diff <TASK_ID>                 # 查看 unified diff
```

**架构**：每个 Cloud 任务在 OpenAI 云端创建隔离环境，执行 best-of-N 尝试（N=1-4），完成后可将 diff 拉回本地应用。

### 与 Claude Code Kairos 的对比

| 维度 | Codex Cloud | Claude Code Kairos |
|------|-------------|-------------------|
| 执行模式 | "提交-拉取"：提交任务 → 等待完成 → 拉取结果 | "持续运行"：Always-On 自治 |
| 结果形式 | unified diff | 直接修改文件 |
| 重试策略 | best-of-N（N=1-4） | 模型自主重试 |
| 状态 | 实验性 | 内部使用 |
| 基础设施 | OpenAI Cloud | Anthropic 基础设施 |

**Qwen Code 对标**：Cloud 执行需要后端基础设施，短期内不可复制。但 best-of-N 的思路可以在本地实现——对关键任务（如大规模重构）并行执行多次，比较 diff 质量后选择最优结果。

---

## 6. MCP 双向支持

Codex CLI 是唯一同时支持 MCP 客户端和服务器模式的主流 CLI Agent。

### 作为 MCP 客户端

```bash
codex mcp list                                    # 列出所有已配置服务器
codex mcp add <name> <command> [args...]           # 添加服务器
codex mcp remove <name>                            # 移除服务器
codex mcp login <name>                             # OAuth 认证（HTTP MCP）
```

配置文件声明（`~/.codex/config.toml`）：

```toml
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "ghp_xxx" }
```

### 作为 MCP 服务器

```bash
codex mcp-server    # 以 stdio MCP 服务器模式运行
```

支持 MCP 协议版本 `2024-11-05`，暴露 tools、resources、prompts 能力。其他 Agent（如 Claude Code、Cursor）可通过 MCP 协议调用 Codex 的代理能力。

**Qwen Code 对标**：Qwen Code 仅支持 MCP 客户端模式。增加 MCP 服务器模式可以让 Qwen Code 被其他 Agent 调用，形成 Agent 组合——例如 Claude Code 调用 Qwen Code 作为"代码生成后端"。

---

## 7. 模型支持与定价

### 默认与推荐模型

| 模型 | 定位 | 输入价格/M tokens | 输出价格/M tokens |
|------|------|-------------------|-------------------|
| `gpt-5.1-codex` | 当前默认，Codex 优化版 | — | — |
| `o4-mini` | 曾为默认，快速且经济 | $1.10 | $4.40 |
| `gpt-4.1` | 大上下文窗口 | $2.00 | $8.00 |

### 本地模型支持

```bash
codex --oss --local-provider lmstudio "分析代码"
codex --oss --local-provider ollama "写一个函数"
```

### 自定义端点

```bash
export OPENAI_BASE_URL="https://your-proxy.example.com/v1"
codex --model your-model "任务"
```

**开发者分析**：Codex 主要支持 OpenAI 模型，通过 `--oss` 和 `--local-provider` 提供有限的本地模型支持。相比之下，Qwen Code 的多模型支持更灵活。模型锁定是 Codex 的最大劣势之一。

---

## 8. 竞品架构对比

| 特性 | Codex CLI | Claude Code | Qwen Code | Aider | Gemini CLI |
|------|----------|-------------|-----------|-------|------------|
| **开源** | Apache-2.0 | 闭源 | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| **技术栈** | **Rust + Node.js** | TypeScript + Bun | TypeScript | Python | TypeScript/Ink |
| **默认模型** | gpt-5.1-codex | Claude Sonnet | Qwen3 | 多模型 | Gemini 2.5 Pro |
| **多模型支持** | OpenAI + OSS | 仅 Claude | 多模型 | 多模型 | 仅 Gemini |
| **沙箱** | **默认启用** | 可选 | 可选 | 无 | 可选 |
| **网络隔离** | **默认阻断** | 可选 | 无 | 无 | 无 |
| **MCP** | **客户端+服务器** | 客户端 | 客户端 | 无 | 客户端 |
| **Git 集成** | review 子命令 | /review 命令 | 无 | 自动提交 | 无 |
| **会话持久化** | **resume/fork** | 崩溃恢复 | 无 | 无 | resume |
| **IDE 集成** | **App-Server JSON-RPC** | WebSocket Bridge | 无 | 无 | 无 |
| **Cloud 执行** | **实验性 best-of-N** | Kairos（内部） | 无 | 无 | 无 |
| **Feature Flag** | **52 个运行时** | 22 个 build-time | 无 | 无 | 无 |
| **二进制体积** | ~137MB | ~227MB | npm 包 | pip 包 | npm 包 |
| **项目指令** | CODEX.md/AGENTS.md | CLAUDE.md | — | .aider* | GEMINI.md |
| **定价模式** | API 按量 | API 按量/订阅 | API 按量 | 免费+API | API 按量 |

> **免责声明**：以上数据基于 2026 年 Q1 分析，可能已过时。

---

## 验证记录

**二进制分析（v0.116.0，137MB ELF static-pie x86-64 Rust）：**
- 系统身份：确认 "You are Codex, based on GPT-5."
- App-Server 协议：通过 IPC 消息字符串提取确认 90+ 方法
- Feature flags：通过 `codex features list` 确认 52 个
- 沙箱实现：通过 `codex sandbox` 子命令和 Seatbelt profile 字符串确认

**官方文档验证：**
- [Linux 沙箱](https://github.com/openai/codex/blob/main/codex-rs/linux-sandbox/README.md)
- [审批与安全](https://developers.openai.com/codex/agent-approvals-security)
- [CLI 参考](https://developers.openai.com/codex/cli/reference)
