# 3. 技术架构——开发者参考

> OpenCode 的技术栈选择与其他 Agent 差异最大：25 包 monorepo、Effect 框架、Drizzle ORM + SQLite、SolidJS Web 前端、Electron 桌面。本文分析其架构中对 Code Agent 开发者最有参考价值的设计。
>
> **Qwen Code 对标**：多客户端共享后端模式、SQLite 会话存储、21 种 Hook 类型、models.dev 动态 Provider 加载

## 为什么 OpenCode 的架构值得研究

### 核心差异

OpenCode 选择了一条与 Claude Code / Qwen Code 完全不同的技术路线：

| 设计决策 | OpenCode | Claude Code | Qwen Code |
|---------|---------|-------------|-----------|
| **项目结构** | 25 包 monorepo | 单体（~1800 文件） | 14 包 monorepo |
| **运行时** | Bun（有 Node 入口） | Bun → Rust 原生 | Node.js |
| **后端框架** | Effect（函数式编程） | 无框架（原生 TS） | 无框架 |
| **数据库** | SQLite + Drizzle ORM | JSONL 文件 | JSONL 文件 |
| **Web 前端** | SolidJS | 无（Remote Control 用 claude.ai） | React |
| **桌面** | Electron | 无 | 无 |
| **模型加载** | models.dev 动态 | 硬编码 Claude 模型 | 手动配置 Provider |
| **类型系统** | Zod + Effect Schema | Zod | Zod |

### 对 Qwen Code 最有参考价值的 3 个设计

**1. models.dev 动态 Provider 加载**
- 通过 `models.dev` API 动态拉取 100+ Provider 的模型信息（名称、定价、上下文窗口）
- 构建时生成 snapshot 供离线使用
- **Qwen Code 启示**：当前手动配置 Provider，可考虑接入 models.dev 或自建模型注册中心

**2. SQLite 会话持久化**
- Drizzle ORM + WAL 模式
- 支持复杂查询：按时间/项目/代理类型搜索历史会话
- 支持 Session Fork（从任意消息点分叉）和 Restore
- **Qwen Code 启示**：JSONL 文件难以支持复杂查询和分叉操作

**3. 21 种 Hook 类型**
- 比 Claude Code（27 事件但以工具生命周期为主）更聚焦扩展性
- 独有能力：`tool.definition`（运行时修改工具 Schema）、`experimental.chat.system.transform`（修改系统提示）、`experimental.session.compacting`（拦截压缩）
- **Qwen Code 启示**：`tool.definition` Hook 允许插件动态修改工具描述和参数——这是其他 Agent 都没有的能力

## 技术架构（源码分析）

### Monorepo 结构

```
opencode/                     # 25 个包
├── packages/opencode/        # 主入口包：CLI 命令/会话编排/服务器路由/插件宿主
├── packages/core/            # 核心引擎：工具/会话/权限/存储/Agent（Effect 化）
├── packages/cli/             # CLI 入口与命令
├── packages/server/          # HTTP/SSE 服务器
├── packages/tui/             # 终端 UI（OpenTUI + Solid.js）
├── packages/llm/             # LLM 集成层
├── packages/app/             # Web 应用前端（SolidJS）
├── packages/desktop/         # Electron 桌面应用
├── packages/console/         # 控制台
├── packages/sdk/             # JavaScript SDK
├── packages/ui/              # 共享 UI 组件库（含 37 种主题）
├── packages/plugin/          # 插件系统（21 种 Hook）
├── packages/enterprise/      # 企业功能
├── packages/identity/        # 认证/身份
├── packages/containers/      # 容器相关
├── packages/slack/           # Slack 集成
├── packages/stats/           # 统计
├── packages/http-recorder/   # HTTP 录制（测试/调试）
├── packages/effect-drizzle-sqlite/  # Effect × Drizzle × SQLite 适配
├── packages/effect-sqlite-node/     # Effect SQLite (Node) 驱动
├── packages/storybook/       # Storybook 组件文档
├── packages/docs/            # 文档
├── packages/web/             # Web 相关工具
├── packages/function/        # 函数处理
└── packages/script/          # 构建和工具脚本
```

### 核心架构

```
客户端 (TUI / Web App / Desktop-Electron)
    ↓
Hono HTTP 服务器 (localhost) + WebSocket + mDNS 服务发现
    ↓
代理系统 (Agent Layer) ← Skill 系统 / Plugin Hook
    ↓
Vercel AI SDK v6 → models.dev 动态模型注册 → 100+ LLM 提供商
    ↓
工具注册表 (16 工具) → 文件系统 / Shell / LSP / MCP
    ↓
SQLite（Drizzle ORM，WAL） — 关系表: session + message + part（+ todo）
    ↓
远程工作区（实验性）← Adaptor + SSE 事件同步
```

### 技术栈
- **语言**：TypeScript 5.8
- **运行时**：Bun 1.3.14（主要）/ Node.js 22+（兼容，已有入口和构建脚本）
- **TUI 框架**：OpenTUI + Solid.js（响应式信号驱动，packages/tui）
- **HTTP 框架**：Hono（轻量级）
- **数据库**：SQLite（Drizzle ORM，TypeScript ORM）
- **AI SDK**：Vercel AI SDK v6（统一 LLM 接口）+ models.dev 动态模型数据
- **MCP SDK**：@modelcontextprotocol/sdk（StreamableHTTP / SSE / Stdio）
- **桌面**：Electron（packages/desktop）
- **类型安全框架**：Effect（函数式效果系统，含 effect-drizzle-sqlite/effect-sqlite-node 专用包）

## 多客户端架构

OpenCode 提供三种客户端形态，共享同一后端：

- **TUI（终端）**：OpenTUI + SolidJS 响应式信号驱动，37 种主题，命令面板（Ctrl+P）
- **Web 控制台**：SolidJS 前端，支持 16 种 UI 语言
- **桌面应用**：Electron（packages/desktop，Vite + SolidJS）

客户端通过 Hono HTTP 服务器 + WebSocket 与后端通信，支持 mDNS 服务发现。

## LSP 集成

### 38 种 LSP 服务器

TypeScript、Deno、Python (Pyright + Ty)、Go (gopls)、Rust (rust-analyzer)、Java (JDTLS)、C/C++ (clangd)、C#、Razor、F#、Ruby、Elixir、Zig (zls)、Kotlin、Swift (sourcekit-lsp)、Haskell、Dart、OCaml、Lua、PHP (Intelephense)、Bash、Terraform、LaTeX (texlab)、Dockerfile、Gleam、Clojure、Nix (nixd)、Typst (tinymist)、Julia、Vue、Svelte、Astro、Prisma、YAML、ESLint、Biome、OxLint

### 26 种 Formatter

Prettier、Biome、gofmt、mix (Elixir)、oxfmt、shfmt、latexindent、zig、clang-format、ktlint、ruff (Python)、air (R)、uv (Python)、rubocop (Ruby)、standardrb (Ruby)、htmlbeautifier (Ruby)、dart、ocamlformat、terraform、gleam、nixfmt、rustfmt、pint (PHP)、ormolu (Haskell)、cljfmt (Clojure)、dfmt (D)

## ACP（Agent Client Protocol）IDE 集成

OpenCode 支持 **ACP（Agent Client Protocol）**——一个标准化代码编辑器与 AI 代理通信的开放协议。

```bash
# 以 ACP 模式启动（JSON-RPC over stdio）
opencode acp
```

### 支持的编辑器

| 编辑器 | 状态 | 说明 |
|--------|------|------|
| **Zed** | 原生支持 | 实时编辑、agent following |
| **JetBrains IDEs** | 通过 ACP Agent Registry | acp.json 配置 |
| **VS Code** | 自动安装扩展 | 从集成终端运行时自动激活 |
| **Avante.nvim** | Neovim 插件 | 完整 ACP 集成 |
| **CodeCompanion.nvim** | Neovim 插件 | 完整 ACP 集成 |

通过 ACP 可使用 OpenCode 的全部功能：工具、自定义工具、MCP 服务器、AGENTS.md、格式化器、代理、权限等。

## 认证系统

### 内置认证插件

OpenCode 通过插件系统提供多种认证方式：

- **GitHub Copilot**：OAuth 认证插件，支持 Copilot for Enterprise 多步认证
- **OpenAI Codex**：ChatGPT Plus/Pro OAuth 认证插件（与 Copilot 认证分开）
- **GitLab**：插件认证 + workflow model discovery
- **Anthropic OAuth**：v1.3.0 已移除

### 认证管理

```bash
# 登录指定 provider
opencode auth login anthropic

# MCP OAuth 认证
opencode mcp list  # 查看已配置的 MCP 服务器
```

支持通过 `opencode.json` 配置 API Key：
```jsonc
{
  "provider": {
    "anthropic": { "apiKey": "${ANTHROPIC_API_KEY}" }
  }
}
```

## 工作区 & 协作系统

### 远程工作区（实验性，`OPENCODE_EXPERIMENTAL_WORKSPACES`）

```
Control Plane ──SSE──→ Workspace Server ──git worktree──→ 隔离环境
     ↑                        ↓
GlobalBus ←── 文件变更/状态事件（10 秒心跳 + 自动重连）
```

- **Adaptor 模式**：可插拔的工作区类型，当前实现 worktree 适配器
- **Worktree 适配器**：基于 `git worktree`，随机人性化命名（如 "brave-cabin"）
- **Workspace Server**：独立 HTTP + SSE 服务，通过 `x-opencode-directory` header 路由请求
- 数据库表 `WorkspaceTable` 持久化工作区记录

### SQLite 存储系统（`packages/core/src/session/sql.ts`）

> OpenCode 是少数使用**结构化数据库**（而非 JSON 文件）管理会话数据的 Code Agent。

**技术栈：** Drizzle ORM + Bun SQLite（`bun:sqlite` + `@effect/sql-sqlite-bun`，默认 WAL 模式）

**主要关系表：**

| 表 | 用途 |
|---|------|
| `session` | 会话（子会话 parentID、token/费用统计、压缩摘要关联） |
| `message` | 消息（role、模型、时间戳） |
| `part` | 消息内容分块（文本 / 工具调用 / 工具结果等） |
| `todo` | 会话级待办列表 |
| `session_message` / `session_input` | 会话-消息映射 / 输入记录 |
| `session_context_epoch` | 上下文 epoch（压缩/截断追踪） |

**设计亮点：**
- **关系建模**：消息拆分为 `message` + `part`，可结构化查询工具调用、文本、推理等不同部分
- **子会话支持**：`session.parentID` 允许从已有会话分叉（`task` 子代理、`/fork`）
- **WAL 并发**：写前日志模式支持多客户端并发读写
- **撤销/压缩关联**：会话支持 revert/unrevert 与压缩摘要追踪

**与其他工具的存储方式对比：**

| Agent | 存储方式 | 会话数据 | 文件版本 |
|------|---------|---------|---------|
| **OpenCode** | **SQLite（关系表）** | 结构化查询（SQL） | git 快照 |
| Claude Code | JSON 文件（`~/.claude/projects/`） | 文件系统 | 无 |
| Aider | Git 提交历史 | 无持久化 | Git 版本管理 |
| Gemini CLI | JSON + Git 快照（`~/.gemini/history/`） | JSON 文件 | Git 对象 |
| Kimi CLI | Wire JSONL 格式 | JSONL 流式文件 | 无 |
| Copilot CLI | 内部格式（`session-state/`） | 闭源 | 无 |
| Codex CLI | JSON + SQLite（`codex.db`） | SQLite | 无 |

> **关键差异：** OpenCode 用 SQLite 做结构化会话存储 + git 快照做文件版本追踪，二者结合支持跨会话历史查询与按消息回退（Restore-to-Message）。Codex CLI 也使用 SQLite，但主要用于会话索引。

### Git-backed Session Review

- 基于 git 对象的快照系统，存储在 `~/.local/share/opencode/snapshot/{project_id}`（XDG data 目录）
- `git write-tree` 捕获状态，`git diff` 计算变更
- 侧面板支持 unified diff 和 split diff 两种视图
- 支持行内注释，懒加载 diff
- VCS 监听 `HEAD` 文件变更，发布 `BranchUpdated` 事件

### Session Fork & Restore

- **Fork**：`Session.fork()` 创建新会话，复制目标消息前所有内容，保留消息关系映射
- **Restore-to-Message**：`SessionRevert.revert()` 收集目标消息后的所有 Patch，执行 `git checkout {hash} -- {file}` 恢复文件
- 支持 unrevert（撤销回退）和 cleanup（永久删除回退点后消息）

### Session 分享

- `ShareNext.create()` → 云端 API 返回 `{ id, url, secret }`
- 订阅 GlobalBus 事件（session/message/part/diff），1 秒防抖批量同步
- 支持组织级 OAuth bearer token 认证
- 可通过 `OPENCODE_DISABLE_SHARE=true` 禁用

## 项目演进（最近一年：2025.03 — 2026.03）

### 里程碑时间线

| 时间 | 版本 | 里程碑 |
|------|------|--------|
| 2026-03-22 | **v1.3.0** | **GitLab Agent Platform**、**Git-backed Session Review**、**多步认证**、**交互式更新流程**、Node.js 正式支持 |
| 2026-02 ~ 03 | v1.2.x | 27 次 patch release；Windows ARM64、Node.js 兼容、远程工作区 |
| 2026-02-14 | **v1.2.0** | SQLite 迁移、Branded ID 类型安全、SolidJS 桌面重构 |
| 2026-01 ~ 02 | v1.1.x | 65 次 patch release；**权限系统重构**（pattern-based）、**14+ 语言国际化**、Skill 系统、Plan 模式、Codex 认证 |
| 2025-10 ~ 2026-01 | v1.0.x | 209 次 patch release（至 v1.0.224）；Web/桌面应用雏形、多 provider 稳定化 |
| 2025-10-31 | **v1.0.0** | **完全重写 TUI**：Go+Bubbletea → OpenTUI + SolidJS；会话压缩、命令面板 (Ctrl+P)、可切换侧边栏 |
| 2025-09 ~ 10 | v0.6 → v0.15 | 快速迭代到 1.0；主题系统、Provider 扩展、Zen 模式 |
| 2025-08 | v0.3 → v0.5 | 首批 releases；会话管理、Context Path、格式化器 |
| 2025-03 ~ 07 | 开发期 | Go + Bubbletea TUI 启动（原名 termai），Go→TypeScript 渐进重写，无 release |

一年内发布 **450+ releases**，从 Go TUI 原型成长为 ~133k Stars 的多客户端 AI 编程平台。

### v1.3.0 关键变化（2026-03-22）

- **GitLab Agent Platform**：自动发现 workflow models
- **Git-backed Session Review**：基于 git 快照的变更追踪和 diff 可视化
- **多步认证**：TUI 和桌面端支持需要多步问答的 provider（如 GitHub Copilot for Enterprise）
- **交互式更新流程**：非 patch 更新提供确认对话框，支持跳过版本
- **Node.js 正式支持**：不再强制依赖 Bun
- **Breaking**：移除 Anthropic OAuth 插件

### v1.2.x 关键变化（2026-02 ~ 03）

- **SQLite 迁移**：数据库 schema 升级，新增 workspace 表
- **Branded ID 类型安全**：SessionID、WorkspaceID、ProviderID 等 Effect branded types
- **Windows ARM64**：CLI 和桌面端新增 ARM64 release targets
- **Node.js 兼容**：替换 Bun-specific API 为可移植方案，新增 Node.js 入口
- **远程工作区**（实验性）：workspace-serve 命令 + Adaptor 模式

### v1.1.x 关键变化（2026-01 ~ 02）

- **权限系统大重构**：从 `tools` config 迁移到 `permission` 模式，支持 pattern-based 粒度控制
- **国际化**：Web/桌面应用新增 14+ 种语言
- **Skill 系统**：SKILL.md 定义文件，支持从 `.opencode/skills/`、`~/.config/opencode/skills/`、`.claude/skills/` 发现
- **Plan 模式**：plan_enter/exit 工具，只读分析
- **Codex 认证**：OpenAI ChatGPT Plus/Pro OAuth 认证插件（与 Copilot 认证分开）

### v1.0.0 关键变化（2025-10-31）

OpenCode 1.0 是一次**完全重写**：
- TUI 框架从 Go + Bubbletea 迁移到自研的 **OpenTUI**（SolidJS 响应式信号）
- 新增**会话压缩**（自动和手动 compact）
- 新增**命令面板**（Ctrl+P 快速操作）
- 新增**可切换的 session 侧边栏**
- 主题和键绑定格式 breaking change
