# OpenCode 遥测与安全分析证据

## 基本信息
- 仓库: sst/opencode, MIT, TypeScript（Bun 运行时）
- 版本: v1.17.8（源码: `packages/opencode/package.json`）
- 架构: TypeScript monorepo（Bun workspace，25 包）
- 最后分析: 2026-06（commit `355a0bcf5`，dev 分支）

> **注**: OpenCode v1.0 之前为 Go 项目（termai），v1.0+ 已完全重写为 TypeScript。
> v1.2.15 二进制分析显示为 Go ELF（Go 编译产物），这是因为 v1.0 之前的发行版本。
> 当前源码（v1.17.8）中 0 个 .go 文件，100% TypeScript。

> **免责声明**: 以下基于 2026-06 源码分析，可能已过时。

## 遥测系统

### 搜索方法论
对 `packages/opencode/` 目录递归搜索以下关键词：
- `telemetry`, `analytics`, `tracking`, `posthog`, `sentry`, `mixpanel`, `amplitude`, `segment`
- `UUID`, `machine.id`, `distinct_id`, `installation_id`
- 外发 HTTP 请求（非 LLM API）

### 搜索结果
- **无第三方遥测**：零匹配
- **无分析 SDK**：无 PostHog/Sentry/Mixpanel/Amplitude/Segment 集成
- **无 Machine ID**：不生成或采集任何设备标识符

### OpenTelemetry（用户可控，默认关闭）
- 源码: `packages/opencode/src/session/llm.ts#L282`
  ```typescript
  experimental_telemetry: { isEnabled: cfg.experimental?.openTelemetry }
  ```
- 源码: `packages/opencode/src/agent/agent.ts#L298`（同模式）
- 仅在用户显式设置 `experimental.openTelemetry: true` 时启用
- LSP 遥测能力: `packages/opencode/src/lsp/server.ts#L1582`（标准 LSP 协议的一部分）

### 结论
OpenCode **不采集任何遥测数据**。OpenTelemetry 为可选开发工具，默认禁用。

## 数据采集
- **不采集**: Machine ID、UUID、主机名、硬件指纹、MAC 地址
- **无外发分析请求**: 所有网络请求均为用户配置的 LLM API 调用
- `packages/opencode/src/env/`: 环境变量管理，仅用于本地功能适配

## 安全系统

### 权限系统
- 源码: `packages/opencode/src/permission/`
  - `index.ts` — 核心权限服务（ask/reply/list 接口，Effect-ts）
  - `evaluate.ts` — 规则评估引擎（匹配权限名 + 模式）
  - `arity.ts` — Bash 命令 arity 检测，智能权限分组
  - `schema.ts` — PermissionID 类型定义

**权限操作**: `ask`（提示用户）、`allow`（自动批准）、`deny`（阻止）

**可配置权限工具**（`packages/core/src/v1/config/permission.ts`）: `read`, `edit`, `glob`, `grep`, `list`, `bash`, `task`, `external_directory`, `todowrite`, `question`, `webfetch`, `websearch`, `lsp`, `doom_loop`, `skill`, `plan_enter`, `plan_exit`

**权限检查流程**:
1. Agent 级规则（来自配置 `agent.*.permission`）
2. Session 级规则（来自用户"始终允许"回答）
3. 均无匹配 → 通过 TUI 提示用户

### 外部目录保护
- 源码: `packages/core/src/tool/bash.ts`（`externalCommandDirectories`）
- 工具在访问项目目录外的路径前检查外部目录权限（`external_directory`）
- Bash 工具通过 token 解析（`shellTokens`）命令参数检测外部目录访问；tree-sitter / parser-based 解析在 `bash.ts` 中标记为 TODO，尚未实装

### 无沙箱机制
OpenCode 不提供沙箱执行隔离。依赖权限系统控制工具行为。

## 深度补充（源码级分析）

### 架构（TypeScript monorepo）

#### 主要源码目录（`packages/opencode/src/`）

> 注：v1.17.8 已将大量引擎逻辑下沉到 `packages/core/src/`（如 `filesystem`、`flag`、`global`、权限 schema、`models-dev`、多个工具实现）。下表为 `packages/opencode/src/` 的代表性目录。

| 目录 | 用途 |
|------|------|
| `account/` | 账户管理（企业/组织） |
| `acp/` | Agent Control Plane |
| `agent/` | 代理定义（build, plan, general, explore, title, summary, compaction） |
| `auth/` | 认证存储（OAuth, API key, well-known） |
| `bus/` | 事件总线系统 |
| `cli/` | CLI 入口 + TUI（SolidJS + opentui） |
| `command/` | 命令系统（init, review, 自定义命令, MCP prompts, skills） |
| `config/` | 配置加载（全局/项目/managed/remote） |
| `control-plane/` | Workspace 服务器适配器 |
| `effect/` | Effect-ts 辅助（实例状态、运行服务） |
| `file/` | 文件操作、ripgrep 封装、文件监视 |
| `filesystem/` | 文件系统工具（读/写/状态/MIME 类型） |
| `flag/` | 功能标志（基于环境变量） |
| `global/` | 全局路径（数据/缓存/配置目录） |
| `ide/` | IDE 集成 |
| `lsp/` | LSP 客户端、服务器定义、启动 |
| `mcp/` | MCP 客户端 |
| `permission/` | 权限系统 |
| `plugin/` | 插件系统（内部 + 外部）、Auth 插件 |
| `project/` | 项目实例、worktree 管理 |
| `provider/` | LLM 提供商抽象、模型加载、认证 |
| `server/` | HTTP 服务器（Hono，端口 4096） |
| `session/` | 会话管理、LLM 流式传输、压缩 |
| `share/` | 会话分享 |
| `skill/` | Skill 加载系统 |
| `snapshot/` | 文件系统快照/撤销系统 |
| `storage/` | SQLite 数据库（Drizzle ORM） |
| `tool/` | 工具定义和注册表 |
| `worktree/` | Git worktree 管理 |

#### Monorepo 包结构（`packages/`，25 包）

| 包 | 用途 |
|---|------|
| `opencode/` | 主入口包：CLI 命令/会话编排/服务器/插件宿主 |
| `core/` | 核心引擎：工具/会话/权限/存储/Agent（Effect 化） |
| `cli/` | CLI 入口与命令 |
| `server/` | HTTP/SSE 服务器 |
| `tui/` | 终端 UI（OpenTUI + Solid.js） |
| `llm/` | LLM 集成层 |
| `app/` | Web 应用（SolidJS） |
| `desktop/` | 桌面应用（Electron） |
| `console/` `sdk/` `ui/` `plugin/` | 控制台 / JS SDK / UI 组件 / 插件 API 类型 |
| `enterprise/` `identity/` `containers/` `slack/` `stats/` | 企业 / 身份 / 容器 / Slack / 统计 |
| `http-recorder/` `effect-drizzle-sqlite/` `effect-sqlite-node/` | HTTP 录制 / Effect-SQLite 适配 |
| `storybook/` `docs/` `web/` `function/` `script/` | Storybook / 文档 / Web 工具 / 函数 / 构建脚本 |

### 代理系统（7 个内置代理）

源码: `packages/opencode/src/agent/`

| 代理 | 用途 |
|------|------|
| general | 通用任务 |
| build | 代码生成（默认代理） |
| plan | 任务规划 |
| explore | 代码库探索 |
| title | 会话标题生成 |
| summary | 摘要生成 |
| compaction | 上下文压缩 |

### 工具系统（16 个 = 13 无条件 + 3 有条件）

源码: `packages/opencode/src/tool/registry.ts`（`Tool.init(...)` 注册，`builtin[]` 数组）

| 工具 (id) | 源码 | 用途 | 关键参数 |
|------|------|------|---------|
| `invalid` | `tool/invalid.ts` | 无效工具调用后备 | `tool`, `error` |
| `bash` | `tool/shell.ts` | Shell 命令执行 | `command`, `cwd?`, `env?` |
| `read` | `tool/read.ts` | 读取文件/目录 | `filePath`, `offset?`, `limit?` |
| `glob` | `tool/glob.ts` | 文件模式搜索 | `pattern`, `path?` |
| `grep` | `tool/grep.ts` | 正则内容搜索 | `pattern`, `path?` |
| `edit` | `tool/edit.ts` | 精确文本替换 | `filePath`, `oldString`, `newString` |
| `write` | `tool/write.ts` | 写入文件 | `filePath`, `content` |
| `task` | `tool/task.ts` | 委派给子代理 | `description`, `prompt`, `subagent_type` |
| `webfetch` | `tool/webfetch.ts` | URL 内容抓取 | `url`, `format?` |
| `todowrite` | `tool/todo.ts` | 写入待办列表 | `todos[]` |
| `websearch` | `tool/websearch.ts` | Web 搜索（Exa / Parallel） | `query`, `numResults?` |
| `skill` | `tool/skill.ts` | 加载技能 | `name` |
| `apply_patch` | `tool/apply_patch.ts` | 统一补丁格式 | `patchText` |
| `question` | `tool/question.ts` | 向用户提问 | `questions[]` |
| `lsp` | `tool/lsp.ts` | LSP 操作 | `operation`, `filePath`, `line`, `character` |
| `plan_exit` | `tool/plan.ts` | 退出规划模式 | （无） |

**条件激活（3 个有条件 + 模型/后端相关）：**
- `question`: 仅 app/cli/desktop 客户端 或 `enableQuestionTool` flag
- `lsp`: 仅 `experimentalLspTool` flag
- `plan_exit`: 仅 `experimentalPlanMode` flag 且 CLI 客户端
- `apply_patch` ↔ `edit`/`write`: 按模型互斥——`modelID.includes("gpt-") && !modelID.includes("oss") && !modelID.includes("gpt-4")` 时用 `apply_patch`，否则用 `edit`/`write`
- `websearch`: 需 Exa 或 Parallel 后端启用（`flags.enableExa` / `flags.enableParallel`），或 provider 为 `opencode`

> 早期文档列出的 `ls`/`multiedit`/`todoread`/`codesearch`/`batch` 工具在当前源码中已不存在。

### 斜杠命令系统

源码: `packages/opencode/src/cli/cmd/tui/app.tsx`（L362-600）+ `routes/session/index.tsx`（L359-870）

**内置命令（服务端）：**

| 命令 | 用途 | 源码 |
|------|------|------|
| `/init` | 创建/更新 AGENTS.md | `packages/opencode/src/command/index.ts` |
| `/review` | 代码审查 | `packages/opencode/src/command/index.ts` |

模板: `packages/opencode/src/command/template/initialize.txt`, `review.txt`

**TUI 斜杠命令（23 个）：**

| 命令 | 别名 | 用途 |
|------|------|------|
| `/sessions` | resume, continue | 切换会话 |
| `/workspaces` | — | 管理工作区（实验性） |
| `/new` | clear | 新建会话 |
| `/models` | — | 切换模型 |
| `/agents` | — | 切换代理 |
| `/mcps` | — | 切换 MCP |
| `/connect` | — | 连接提供商 |
| `/status` | — | 查看状态 |
| `/themes` | — | 切换主题 |
| `/help` | — | 帮助 |
| `/exit` | quit, q | 退出 |
| `/share` | — | 分享会话 |
| `/rename` | — | 重命名会话 |
| `/timeline` | — | 跳转到消息 |
| `/fork` | — | 从消息分叉 |
| `/compact` | summarize | 压缩会话 |
| `/unshare` | — | 取消分享 |
| `/undo` | — | 撤销上一消息 |
| `/redo` | — | 重做 |
| `/timestamps` | toggle-timestamps | 显示/隐藏时间戳 |
| `/thinking` | toggle-thinking | 显示/隐藏思考过程 |
| `/editor` | — | 打开编辑器 |
| `/skills` | — | 列出技能 |

### LSP 集成（38 语言服务器）

源码: `packages/opencode/src/lsp/server.ts`

支持语言: TypeScript, JavaScript, Vue, Go, Ruby, Python, Elixir, Zig, C#, Razor, F#, Swift, Rust, C/C++, Svelte, Astro, Java, Kotlin, YAML, Lua, PHP, Prisma, Dart, OCaml, Bash, Terraform, LaTeX, Dockerfile, Gleam, Clojure, Nix, Typst, Haskell, Julia 等

LSP 工具操作: `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls`

语言映射: `packages/opencode/src/lsp/language.ts`（~120 文件扩展名 → 语言 ID）

### 认证插件（10 个：内置 8 + 外部 npm 2）

源码: `packages/opencode/src/plugin/index.ts`（`internalPlugins`）

| 插件 | 提供商 | 源码 |
|------|--------|------|
| CodexAuthPlugin | `openai` | `plugin/openai/codex.ts` |
| CopilotAuthPlugin | `github-copilot` | `plugin/github-copilot/copilot.ts` |
| AzureAuthPlugin | `azure` | `plugin/azure.ts` |
| CloudflareWorkersAuthPlugin | `cloudflare-workers-ai` | `plugin/cloudflare.ts` |
| CloudflareAIGatewayAuthPlugin | `cloudflare-ai-gateway` | `plugin/cloudflare.ts` |
| SnowflakeCortexAuthPlugin | `snowflake-cortex` | `plugin/snowflake-cortex.ts` |
| DigitalOceanAuthPlugin | `digitalocean` | `plugin/digitalocean.ts` |
| XaiAuthPlugin | `xai` | `plugin/xai.ts` |
| GitlabAuthPlugin | `gitlab` | `opencode-gitlab-auth`（外部 npm） |
| PoeAuthPlugin | `poe` | `opencode-poe-auth`（外部 npm） |

### 模型支持（100+ 提供商）

源码: `packages/core/src/models-dev.ts`

- 通过 models.dev API 动态加载（`https://models.dev/api.json`）
- 缓存: `~/.cache/opencode/models.json`
- 回退: 捆绑快照（`./models-snapshot`）
- 每 60 分钟自动刷新
- 环境变量: `OPENCODE_MODELS_URL`, `OPENCODE_MODELS_PATH`, `OPENCODE_DISABLE_MODELS_FETCH`

### 配置优先级

源码: `packages/opencode/src/config/config.ts`

```
1. Remote .well-known/opencode（组织默认）
2. Global config（~/.config/opencode/opencode.json{,c}）
3. Custom config（OPENCODE_CONFIG 环境变量）
4. Project config（opencode.json{,c}）
5. .opencode 目录（.opencode/agents/, .opencode/commands/, etc.）
6. Inline config（OPENCODE_CONFIG_CONTENT 环境变量）
7. Enterprise managed（/etc/opencode/opencode.json）
```

### 会话管理

源码: `packages/opencode/src/session/`
- SQLite 数据库（Drizzle ORM）
- 支持 undo/redo（`revert.ts`）
- 上下文压缩（`compaction.ts`）
- 会话分享（`share/`）
- 子会话（task 工具创建，有 parent session）

### TUI 架构

源码: `packages/opencode/src/cli/cmd/tui/`
- SolidJS + `@opentui/core` + `@opentui/solid`
- 通过内部 HTTP 服务器通信（Hono，端口 4096）
- SDK 客户端封装 HTTP 调用（`@opencode-ai/sdk`）

来源: GitHub 源码 `packages/opencode/`（TypeScript + Bun）
