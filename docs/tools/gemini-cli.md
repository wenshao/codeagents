# Gemini CLI

> **📌 本文档已拆分为多文件目录，内容更详尽。请访问 [gemini-cli/](./gemini-cli/) 查看最新版本。**
> 本单文件保留供向后兼容，可能与目录版本存在差异。

**开发者：** Google
**许可证：** Apache-2.0
**仓库：** [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)（npm: `@google/gemini-cli`）
**文档：** [geminicli.com](https://geminicli.com)
**Stars：** ~99k（100+ 贡献者，12.5k Forks）
**最后更新：** 2026-03

## 概述

Gemini CLI 是 Google 官方的开源 AI 编程代理，运行在终端中，基于 TypeScript + Ink/React 19 构建。采用 ReAct 模式驱动代理循环，主循环最多 100 轮对话，子代理默认 30 轮/10 分钟。项目于 2025 年 6 月 25 日首次公开发布（v0.1.0），当前稳定版为 v0.34.0（2026-03-17），采用每周二稳定/预览/夜间三通道发布模式。整体代码量约 22 万行 TypeScript（不含测试，含测试约 53 万行），是 GitHub 上增长最快的开源项目之一（不到一年从 0 到 ~99k Stars）。它也是 Qwen Code 的上游项目，其架构被广泛借鉴。

## 核心功能

### 基础能力
- **ReAct 代理循环**：推理 + 行动模式，主循环最多 100 轮，子代理默认 30 轮/10 分钟
- **23 种内置工具**（17 核心 + 6 任务追踪）：文件读写、编辑、Bash 执行、Grep 搜索、Web 搜索/抓取、记忆、规划、技能、任务追踪等
- **5 个内置代理**：generalist（通用）、codebase_investigator（代码库分析）、memory_manager（记忆管理）、cli_help（帮助）、browser（浏览器自动化）
- **MCP 支持**：完整的模型上下文协议（Stdio/SSE 传输），支持 OAuth 认证
- **事件驱动调度器**：并发工具调用，状态机管理生命周期（Validating → Scheduled → AwaitingApproval → Executing → Success/Error/Cancelled）
- **TOML 策略引擎**：灵活的权限控制，支持通配符和正则匹配，四种审批模式
- **11 种 Hook 事件**：BeforeTool、AfterTool、BeforeAgent、AfterAgent、BeforeModel、AfterModel、BeforeToolSelection、Notification、SessionStart、SessionEnd、PreCompress
- **扩展系统**：Git/Local/GitHub Release 安装，扩展可贡献 MCP 服务器、工具、主题、技能、代理、策略规则
- **流式输出**：实时显示 LLM 推理和工具执行结果
- **会话管理**：UUID 会话、压缩、恢复、检查点、回退（Rewind）
- **17 种内置主题**：Dark（9 种：Ayu Dark、Atom One Dark、Dracula、GitHub Dark、Solarized Dark 等）+ Light（7 种：Google Code、GitHub Light、Xcode 等）+ NoColor，支持自定义主题
- **多种沙箱**：macOS Seatbelt、Linux Bubblewrap/Seccomp、Docker、Podman、gVisor（runsc）、LXC、Windows Sandbox

### 独特功能
- **策略引擎（Policy Engine）**：TOML 格式的策略文件，支持优先级、通配符、正则参数匹配、工具注解匹配、审批模式过滤
- **安全检查器**：内置 `allowed-path`（路径验证）和 `conseca`（语义安全检查）+ 可外挂进程级安全检查
- **模型路由器**：7 种可插拔路由策略（Override、Fallback、ApprovalMode、Classifier、NumericalClassifier、Composite、Default），动态模型选择
- **检查点 & 回退（Checkpoint & Rewind）**：基于 Git 快照的检查点系统，`Esc Esc` 快速回退，带影响分析和确认 UI
- **浏览器代理**：Puppeteer 驱动的 Web 自动化代理，支持导航、点击、截图分析、域名限制
- **Token 缓存**：自动优化后续请求中的缓存 Token，减少处理量（API Key 用户可用）
- **A2A 服务器**：实验性 Agent-to-Agent 协议支持，Express.js 实现，HTTP/JSON 通信
- **Headless 模式**：CI/GitHub Actions/非 TTY 环境自动激活，支持 `-p` 标志
- **`.geminiignore`**：类似 `.gitignore` 的文件过滤，支持 glob、目录、否定模式
- **Qwen Code 上游**：其架构被阿里云 Qwen Code 分叉和扩展

## 技术架构（源码分析）

### Monorepo 结构

```
gemini-cli/                              # 7 个包
├── packages/cli/                        # 终端 UI（Ink + React 19），斜杠命令，TUI 组件
├── packages/core/                       # 核心引擎（代理、工具、策略、调度器、认证、Hook、路由、遥测）
├── packages/sdk/                        # 公共 SDK（编程式使用，导出 Config、Agent 等核心类型）
├── packages/a2a-server/                 # Agent-to-Agent 实验协议（Express.js 5.x）
├── packages/devtools/                   # 开发工具（WebSocket 服务器，DevTools 客户端通信）
├── packages/vscode-ide-companion/       # VS Code 扩展（Diff 编辑器，工作区上下文，需 VS Code 1.99+）
├── packages/test-utils/                 # 测试工具（node-pty 终端模拟，mock 实现）
├── evals/                               # 行为评估（25 个评估套件）
├── integration-tests/                   # 集成测试（Docker/Podman 沙箱）
├── schemas/                             # JSON Schema 定义
├── sea/                                 # Single Executable Application 构建
└── scripts/                             # 构建和发布脚本
```

### 核心架构

```
CLI (Ink + React 19)
    │
    ▼
AgentSession (AsyncIterable 事件流, 会话编排)
    │
    ▼
GeminiClient → GeminiChat (@google/genai SDK, 流式, 主循环最多 100 轮)
    │
    ▼
Scheduler (事件驱动调度器)
    │  Validating → Scheduled → AwaitingApproval → Executing → Success/Error/Cancelled
    │
    ├── PolicyEngine (TOML 策略, 多源优先级: Runtime > Project > User > System > Extensions)
    │   ├── 通配符匹配（*、mcp_*、mcp_serverName_*）
    │   ├── 正则参数匹配（argsPattern）
    │   ├── 工具注解匹配（toolAnnotations: readOnlyHint 等）
    │   └── SafetyChecker（InProcess: allowed-path/conseca + External: 子进程）
    │
    ├── HookSystem (11 种 Hook 事件)
    │   ├── Command Hooks（外部子进程）
    │   ├── Runtime Hooks（TypeScript 函数）
    │   └── Hook 决策：ask / block / deny / approve / allow
    │
    ├── ToolExecutor (工具执行)
    │   ├── 23 内置工具（ToolRegistry）
    │   ├── MCP 动态工具（mcp_{server}_{tool} 命名）
    │   ├── Discovered 工具（discovered_tool_ 前缀）
    │   └── 排序：Built-in (0) > Discovered (1) > MCP (2)
    │
    ├── ModelRouter (模型路由, 7 种策略)
    │   ├── OverrideStrategy（显式模型请求）
    │   ├── FallbackStrategy（错误自动回退）
    │   ├── ApprovalModeStrategy（按审批模式选模型）
    │   ├── ClassifierStrategy（ML Gemma 分类器）
    │   ├── NumericalClassifierStrategy（数值评分）
    │   ├── CompositeStrategy（组合链式策略）
    │   └── DefaultStrategy（最终兜底）
    │
    └── AgentRegistry (5 内置代理 + 自定义代理)
        ├── generalist（通用，全工具访问，继承主模型，20 轮）
        ├── codebase_investigator（代码分析，只读工具，Flash 模型）
        ├── memory_manager（记忆管理，读写 GEMINI.md，Flash 模型）
        ├── cli_help（CLI 帮助，查询内部文档，10 轮/3 分钟）
        └── browser（浏览器自动化，Puppeteer MCP，域名限制）
```

### 技术栈
- **语言**：TypeScript（ES2022 target）
- **运行时**：Node.js ≥20.0.0
- **CLI 框架**：Ink 6.4 + React 19
- **API SDK**：@google/genai@1.30.0（Gemini 官方）
- **MCP SDK**：@modelcontextprotocol/sdk@^1.23.0（Stdio/SSE）
- **A2A SDK**：@a2a-js/sdk@0.3.11
- **策略格式**：TOML（@iarna/toml）
- **Schema 验证**：Zod@^3.25.76
- **遥测**：OpenTelemetry 全套（Traces + Metrics + Logs，OTLP/GCP 导出）
- **AST 解析**：web-tree-sitter@^0.25.10 + tree-sitter-bash@^0.25.0
- **浏览器自动化**：puppeteer-core@^24.0.0
- **终端模拟**：@xterm/headless@5.5.0 + @lydell/node-pty
- **凭证存储**：keytar@^7.9.0（系统 Keychain）
- **构建**：esbuild@^0.25.0
- **测试**：Vitest@^3.2.4
- **Lint**：ESLint 9.x（零警告策略）

### 多代理系统

| 代理 | 类型 | 工具权限 | 模型 | 用途 |
|------|------|----------|------|------|
| **generalist** | 子代理 | 完全访问 | 继承主模型 | 通用多步骤任务，20 轮/10 分钟 |
| **codebase_investigator** | 子代理 | 只读（glob/grep/ls/read_file） | gemini-3-flash-preview（回退 gemini-2.5-pro） | 代码库分析和架构映射，10 轮/3 分钟 |
| **memory_manager** | 子代理（条件） | 读写（ask_user/edit/glob/grep/ls/read/write） | flash（gemini-3-flash-preview） | 记忆增删改、去重、组织，10 轮/5 分钟 |
| **cli_help** | 子代理 | get_internal_docs | flash（gemini-3-flash-preview） | 回答 CLI 功能问题，10 轮/3 分钟 |
| **browser** | 子代理（条件） | 浏览器 MCP 工具 | gemini-3-flash-preview（回退 gemini-2.5-flash） | Web 自动化（导航、点击、截图分析），50 轮/10 分钟 |

- browser 和 memory_manager 为**条件注册**代理，需在设置中启用
- 支持通过配置文件定义**自定义代理**（独立模型、提示、最大步数、工具过滤）
- 支持**远程代理**（A2A 协议，通过 agentCardUrl 注册）
- 代理终止模式：`GOAL`（成功）、`MAX_TURNS`、`TIMEOUT`、`ERROR`、`ABORTED`、`ERROR_NO_COMPLETE_TASK_CALL`

### 工具系统

注册在 ToolRegistry 中的工具（17 核心 + 6 任务追踪 = 23 内置）：

| 工具 | 显示名 | 用途 | 条件 |
|------|--------|------|------|
| **glob** | FindFiles | 文件模式匹配搜索 | 始终可用 |
| **read_file** | ReadFile | 读取文件内容（支持行范围） | 始终可用 |
| **write_file** | WriteFile | 创建/覆写文件 | 始终可用 |
| **replace** | Edit | 编辑文件（instruction 或 old/new string） | 始终可用 |
| **list_directory** | ReadFolder | 列出目录内容 | 始终可用 |
| **read_many_files** | ReadManyFiles | 批量读取多个文件 | 始终可用 |
| **grep_search** | SearchText | 正则内容搜索 | 始终可用 |
| **google_web_search** | GoogleSearch | Web 搜索（带 Grounding 引用） | 始终可用 |
| **web_fetch** | WebFetch | 抓取 URL 内容（HTML→Text，250KB 限制） | 始终可用 |
| **run_shell_command** | — | 执行 Shell 命令（支持后台/交互模式） | 始终可用 |
| **ask_user** | Ask User | 向用户提问（多种问题类型+选项） | 始终可用 |
| **save_memory** | MemoryTool | 存储事实到 GEMINI.md | 始终可用 |
| **get_internal_docs** | — | 检索内部文档 | 始终可用 |
| **activate_skill** | — | 按名称激活自定义技能 | 始终可用 |
| **write_todos** | — | 创建/更新任务列表 | 始终可用 |
| **enter_plan_mode** | — | 进入只读规划模式 | 始终可用 |
| **exit_plan_mode** | — | 退出规划模式（输出 plan 文件） | 始终可用 |
| **tracker_create_task** | — | 创建任务 | 始终可用 |
| **tracker_update_task** | — | 更新任务状态/内容 | 始终可用 |
| **tracker_get_task** | — | 获取任务详情 | 始终可用 |
| **tracker_list_tasks** | — | 列出所有任务 | 始终可用 |
| **tracker_add_dependency** | — | 添加任务依赖关系 | 始终可用 |
| **tracker_visualize** | — | 可视化任务层级 | 始终可用 |

此外，MCP 工具以 `mcp_{serverName}_{toolName}` 格式动态注册，支持通配符策略（`mcp_*`、`mcp_serverName_*`）。工具发现命令注册的工具以 `discovered_tool_` 前缀标识。

**Plan Mode 可用工具**：
- **自动允许**：glob、grep_search、read_file、list_directory、google_web_search、activate_skill、get_internal_docs、codebase_investigator、cli_help
- **需确认**：ask_user、save_memory、MCP 工具（readOnlyHint=true）
- **受限写入**：write_file/replace 仅限 `.gemini/tmp/.../plans/*.md` 文件

### 策略/权限系统

```toml
# .gemini/policies/my-rules.toml（策略目录下可有多个 .toml 文件）
[[rule]]
toolName = "run_shell_command"
decision = "ask_user"
priority = 10

[[rule]]
toolName = "read_file"
decision = "allow"
priority = 5

[[rule]]
toolName = "mcp_*"
decision = "ask_user"
priority = 3

[[rule]]
toolName = "*"
argsPattern = ".*\\.env.*"
decision = "deny"
denyMessage = "禁止访问 .env 文件"
priority = 100
```

**四种审批模式**（ApprovalMode）：
- **DEFAULT**：每个非只读工具调用都询问用户
- **AUTO_EDIT**：自动跳过编辑操作的确认
- **YOLO**：自动批准所有工具调用（无确认）
- **PLAN**：只读规划模式，仅允许只读工具

**策略规则字段**：
- `toolName` — 目标工具（支持 `*` 通配符）
- `mcpName` — MCP 服务器名称
- `argsPattern` — 正则表达式匹配参数
- `toolAnnotations` — 工具元数据匹配（如 `readOnlyHint`）
- `decision` — ALLOW / DENY / ASK_USER
- `priority` — 数值越大优先级越高
- `modes` — 审批模式过滤
- `interactive` — 交互/非交互环境过滤
- `allowRedirection` — 允许 Shell 重定向
- `denyMessage` — 自定义拒绝消息

**策略优先级**（5 级 Tier，从高到低）：Admin（Tier 5）→ User（Tier 4，含 settings 动态规则）→ Workspace/Project（Tier 3）→ Extension（Tier 2）→ Default（Tier 1）

**内置策略文件**（9 个）：conseca.toml、discovered.toml、memory-manager.toml、plan.toml、read-only.toml、sandbox-default.toml、tracker.toml、write.toml、yolo.toml

### Hook 系统

```jsonc
// settings.json 或 .gemini/settings.json
{
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "run_shell_command",
        "hooks": [
          { "type": "command", "command": "echo 检查命令安全性", "timeout": 5000 }
        ]
      }
    ],
    "AfterAgent": [
      {
        "hooks": [
          { "type": "command", "command": "echo 代理完成" }
        ]
      }
    ]
  }
}
```

**11 种 Hook 事件**：

| 事件 | 触发时机 | 可用操作 |
|------|----------|---------|
| **BeforeTool** | 工具执行前 | 修改输入参数、阻止/拒绝/批准执行 |
| **AfterTool** | 工具执行后 | 后处理 |
| **BeforeAgent** | 代理启动前 | 预处理 |
| **AfterAgent** | 代理完成后 | 后处理 |
| **BeforeModel** | LLM 调用前 | 修改请求 |
| **AfterModel** | LLM 响应后 | 后处理响应 |
| **BeforeToolSelection** | 工具选择前 | 覆盖工具选择 |
| **Notification** | 通知事件 | 自定义通知处理 |
| **SessionStart** | 会话开始 | 初始化 |
| **SessionEnd** | 会话结束 | 清理 |
| **PreCompress** | 上下文压缩前 | 预处理 |

**Hook 类型**：
- **Command**：执行外部子进程，支持环境变量和超时
- **Runtime**：TypeScript 函数（扩展内部使用）

**Hook 决策**：`ask`（询问用户）| `block`（阻止）| `deny`（拒绝）| `approve`（批准）| `allow`（允许）

### 会话管理

- **AgentSession**：实现 AsyncIterable 协议，支持事件流式订阅和回放
- **事件类型**：agent_start、agent_end、tool_call、thought
- **会话压缩**（源码：`chatCompressionService.ts`）：
  - 自动触发阈值：对话 token 数超过模型 token limit 的 50%（`DEFAULT_COMPRESSION_TOKEN_THRESHOLD = 0.5`）
  - 保留最近 30% 的对话（`COMPRESSION_PRESERVE_THRESHOLD = 0.3`）
  - 工具响应 token 预算：50,000 tokens（`COMPRESSION_FUNCTION_RESPONSE_TOKEN_BUDGET`）
  - 超出预算的旧工具响应截断为最后 30 行并保存到临时文件
  - 压缩模型选择：根据当前模型映射到对应的压缩配置别名（如 `chat-compression-2.5-pro`）
  - 分割策略：在 user role 的非 functionResponse 消息处分割，确保不在 function call/response 对中间断开
  - 也可通过 `/compress` 命令手动触发
- **会话恢复**：`gemini --resume <session-id>`
- **检查点（Checkpointing）**（源码：`checkpointing.md`、`rewindCommand.tsx`、`rewindFileOps.ts`）：
  - 默认关闭，需在 `settings.json` 中启用：`{ "general": { "checkpointing": { "enabled": true } } }`
  - 当批准文件修改工具（write_file/replace）时自动创建检查点
  - 每个检查点包含三部分：
    1. **Git 快照**：在影子 Git 仓库 `~/.gemini/history/<project_hash>` 中创建提交（不影响用户项目 Git）
    2. **对话历史**：完整会话上下文保存在 `~/.gemini/tmp/<project_hash>/checkpoints`
    3. **工具调用**：记录即将执行的工具调用参数
  - 恢复检查点（`/restore` 命令）：还原文件 + 恢复对话 + 重新提议原工具调用
- **回退（Rewind）**（源码：`rewindCommand.tsx`、`rewindFileOps.ts`、`docs/cli/rewind.md`）：
  - 触发方式：`/rewind` 命令或 `Esc Esc` 快捷键
  - 交互式 UI：上下箭头选择回退点，显示每步的用户提示和文件变更统计
  - 三种回退选项（`RewindOutcome` 枚举，源码确认）：
    1. **Cancel**：取消操作，仅移除组件
    2. **RevertOnly**：仅还原文件变更（调用 `revertFileChanges()`），保留对话历史
    3. **RewindAndRevert**：还原文件变更 + 回退对话历史（调用 `rewindConversation()` 设置 `client.setHistory()`、刷新 `contextManager`、重建 UI 历史）
  - 文件变更统计（`rewindFileOps.ts:calculateTurnStats()`）：基于工具调用结果的 diff 计算添加/删除行数和文件数
  - 限制：仅回退 AI 工具造成的文件修改，不回退手动编辑或 Shell 工具（`!`）执行的变更
  - 支持跨会话压缩点回退（从存储的 session 数据重建历史）

### 记忆系统（源码：`memoryTool.ts`、`memory.ts`、`memoryDiscovery.ts`）

**分层记忆结构**（`HierarchicalMemory` 接口，`config/memory.ts`）：
```typescript
{
  global: string    // ~/.gemini/GEMINI.md（全局记忆）
  extension: string // 扩展级记忆
  project: string   // ./GEMINI.md 或 .gemini/GEMINI.md（项目级记忆）
}
```

展平时按 `--- Global ---`、`--- Extension ---`、`--- Project ---` 区段拼接（`flattenMemory()` 函数）。

**GEMINI.md 层级**（`memoryDiscovery.ts`）：
1. `~/.gemini/GEMINI.md` — 全局（所有项目通用偏好）
2. 项目根目录 `GEMINI.md` — 项目级（提交到 Git 共享给团队）
3. 子目录 `GEMINI.md` — 目录特定规则
4. 文件名可自定义（`setGeminiMdFilename()`），支持数组配置多个文件名

**save_memory 工具**（`memoryTool.ts`）：
- 存储格式：Markdown 列表项（`- fact text`）
- 写入位置：全局 GEMINI.md（`~/.gemini/GEMINI.md`）
- 区段标记：`## Gemini Added Memories` 头部，追加写入
- 需用户确认（工具调用前显示 diff 预览）

**文件发现**（`memoryDiscovery.ts`）：
- BFS 搜索发现所有 GEMINI.md 文件
- 按文件标识（device + inode）去重（处理大小写不敏感文件系统和符号链接）
- 支持 `@import` 语法导入其他 Markdown 文件（`memoryImportProcessor.ts`）

**`/memory` 命令**（源码：`packages/cli/src/ui/commands/memoryCommand.ts`）：
- `/memory show`：调用 `showMemory(config)` 显示所有层级的记忆内容
- `/memory add <text>`：调用 `addMemory(args)` 返回 submit_prompt 类型触发 save_memory 工具
- `/memory reload`（别名: refresh）：调用 `refreshMemory(config)` 重新扫描并加载所有 GEMINI.md 文件
- `/memory list`：调用 `listMemoryFiles(config)` 列出当前生效的所有 GEMINI.md 文件路径

**记忆管理代理**：专用 memory_manager 代理（条件注册，需设置启用）处理增删改、去重、组织，使用 Flash 模型

### 技能系统（Agent Skills）

**技能定义结构**：
```typescript
{
  name: string        // 唯一标识
  description: string // 用户可见描述
  body: string        // 提示内容
  isBuiltin: boolean  // 是否内置
  disabled: boolean   // 管理控制
  location: string    // 文件路径
}
```

**技能加载层级**（优先级从低到高）：
1. 内置技能
2. 扩展技能
3. 用户技能（`~/.gemini/skills/` 或 `~/.agents/skills/`）
4. 项目技能（`.gemini/skills/` 或 `.agents/skills/`）

- **`/skills` 命令**：查看和管理技能
- **`activate_skill` 工具**：在代理对话中激活指定技能
- 技能管理器支持发现、启用/禁用、管理员覆盖

### 模型路由器

```
请求 → OverrideStrategy（显式模型指定）
      → FallbackStrategy（错误自动回退）
      → ApprovalModeStrategy（按审批模式选型）
      → ClassifierStrategy（ML Gemma 分类器）
      → NumericalClassifierStrategy（数值评分路由）
      → CompositeStrategy（组合多策略链）
      → DefaultStrategy（最终兜底）
```

**路由决策结构**：
```typescript
{
  model: string           // 选中的模型 ID
  metadata: {
    source: string        // 决策来源策略名
    latencyMs: number     // 路由延迟
    reasoning: string     // 选择理由
    error?: string        // 错误信息（可选）
  }
}
```

### MCP 集成

**协议支持**：Stdio、SSE 传输
**配置方式**：
```jsonc
// settings.json
{
  "mcp": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    }
  }
}
```

**MCP 工具命名**：`mcp_{serverName}_{toolName}`（如 `mcp_github_create_issue`）
**OAuth 支持**：MCPOAuthConfig，Token 存储支持 Keychain/文件/混合模式
**自动发现**：从配置、扩展、工作区自动发现并注册
**策略通配符**：`mcp_*`（所有 MCP）、`mcp_serverName_*`（特定服务器所有工具）

### A2A 协议（Agent-to-Agent）

- **框架**：Express.js 5.1.0
- **端口**：通过 `CODER_AGENT_PORT` 环境变量配置，默认自动分配
- **协议**：HTTP/JSON
- **认证方式**：API Key、OAuth2、Google Credentials、HTTP、Gateway
- **活动事件**：TOOL_CALL_START、TOOL_CALL_END、THOUGHT_CHUNK、ERROR
- **远程代理**：通过 `agentCardUrl` 注册，支持 HTTP 认证（v0.33.0+）

### 扩展系统

**扩展结构**：
```typescript
{
  name: string
  version: string
  isActive: boolean
  path: string
  installMetadata?: ExtensionInstallMetadata
  mcpServers?: Record<string, MCPServerConfig>  // MCP 服务器
  contextFiles: string[]                         // 上下文文件
  excludeTools?: string[]                        // 排除工具
  hooks?: { [K in HookEventName]?: HookDefinition[] }  // Hook
  settings?: ExtensionSetting[]                  // 设置项
  skills?: SkillDefinition[]                     // 技能
  agents?: AgentDefinition[]                     // 代理
  themes?: CustomTheme[]                         // 自定义主题
  rules?: PolicyRule[]                           // 策略规则
  checkers?: SafetyCheckerRule[]                 // 安全检查器
  plan?: { directory?: string }                  // 规划配置
}
```

**安装方式**：
- `git` — 从 Git 仓库
- `local` — 本地目录
- `link` — 符号链接
- `github-release` — GitHub Release 归档

**官方扩展**：CloudRun、Security（`/security:analyze`）、Hugging Face、Monday.com、ElevenLabs、Jules、Conductor、Endor Labs、Data Commons、AlloyDB、BigQuery、Cloud SQL 等数据库扩展

### 沙箱系统

通过 `GEMINI_SANDBOX` 环境变量或 `--sandbox` 标志配置，支持 7 种沙箱后端：

| 后端 | 命令 | 平台 | 说明 |
|------|------|------|------|
| **macOS Seatbelt** | `sandbox-exec` | macOS | 6 种配置文件（permissive-open/proxied、restrictive-open/proxied、strict-open/proxied） |
| **Bubblewrap** | `bwrap` | Linux | 用户命名空间 + Seccomp 系统调用过滤，原生轻量隔离 |
| **Docker** | `docker` | 跨平台 | 容器化隔离 |
| **Podman** | `podman` | 跨平台 | 无 daemon 容器化隔离（Docker 替代） |
| **gVisor** | `runsc` | Linux | 用户空间内核级隔离（最强安全性） |
| **LXC** | `lxc` | Linux | 完整系统容器隔离 |
| **Windows Sandbox** | — | Windows | C# 集成，原生隔离 |

**沙箱权限**：
```typescript
{
  fileSystem: { read: string[], write: string[] }  // 文件系统读写路径
  network: boolean                                  // 网络访问
  allowedPaths: string[]                           // 允许的路径
  forbiddenPaths: string[]                         // 禁止的路径
}
```

- macOS 支持动态扩展沙箱和 Worktree
- 默认不启用沙箱（带红色警告），推荐在生产环境启用
- v0.24.0 起默认文件夹信任设为 untrusted

### 认证方式

| 方式 | 类型标识 | 说明 |
|------|----------|------|
| **Google OAuth** | `oauth-personal` | OAuth 2.0 设备码流程，Token 存储在系统 Keychain |
| **Gemini API Key** | `gemini-api-key` | `GEMINI_API_KEY` 环境变量，免费层 250 req/day |
| **Vertex AI** | `vertex-ai` | GCP 项目 + 区域，使用 ADC 凭证 |
| **计算默认凭证** | `compute-default-credentials` | 服务账号 JSON Key |
| **企业网关** | `gateway` | 企业级 API 网关 |
| **Cloud Shell** | `cloud-shell` | Legacy，已弃用 |

## 安装

```bash
# npm（全局安装）
npm install -g @google/gemini-cli

# npx（免安装运行）
npx @google/gemini-cli

# Homebrew（macOS/Linux）
brew install gemini-cli

# MacPorts（macOS）
sudo port install gemini-cli

# Conda（受限环境）
conda install -c conda-forge gemini-cli

# 启动（首次会引导认证）
gemini
```

**发布通道**：
- **Stable**：每周二 UTC 20:00，完全验证
- **Preview**：每周二 UTC 23:59，已测试但未完全验证
- **Nightly**：每日 UTC 00:00，main 分支最新代码

## 支持的模型

| 模型系列 | 说明 |
|----------|------|
| **Gemini 3.1 Pro** | 最新预览模型（v0.31.0+ 可用） |
| **Gemini 3 Pro** | v0.29.0 起为所有用户默认模型 |
| **Gemini 3 Flash** | 轻量级快速模型（子代理默认使用） |
| **Gemini 2.5 Flash** | 上一代快速模型 |
| **Gemini 2.5 Pro** | 上一代专业模型 |
| **Gemini 2.0 Flash** | 基础模型（免费 API Key 用户可用） |

- 模型路由器根据任务复杂度自动在 Flash/Pro 间切换（v0.12.0+）
- 通过 `/model` 命令手动切换模型
- 1M Token 上下文窗口（Pro 模型）
- **仅支持 Gemini 系列模型**，Google 官方拒绝了所有第三方模型后端 PR

## 优势

1. **Google 官方**：第一方支持，与 Gemini 模型深度集成，1M Token 上下文
2. **极高免费额度**：Google 账号登录 1000 req/day/user，远超竞品
3. **架构优雅**：事件驱动调度器 + 声明式工具 + 可插拔策略引擎 + Hook 系统
4. **策略系统强大**：TOML 策略文件 + 双安全检查器 + 四种审批模式 + 优先级排序
5. **扩展生态**：v0.8.0 起支持扩展系统，官方和社区扩展丰富
6. **多代理架构**：5 个内置代理 + 自定义代理 + 远程 A2A 代理
7. **丰富沙箱**：7 种沙箱后端（Seatbelt/Bubblewrap/Docker/Podman/gVisor/LXC/Windows Sandbox）
8. **检查点 & 回退**：基于 Git 快照的安全网，`Esc Esc` 即时回退
9. **开源**：Apache-2.0 许可，~99k Stars，代码质量高
10. **生态影响力大**：Qwen Code 基于此分叉，众多社区衍生项目

## 劣势

1. **单模型锁定**：仅支持 Gemini 系列模型，Google 明确拒绝多模型支持
2. **文件编辑可靠性**：社区反映编辑操作有时会覆写文件而非精确编辑，消耗过多 Token
3. **速率限制问题**：用户报告在 29% 配额时即被限流，滥用缓解措施按许可类型优先排序
4. **认证复杂**：Code Assist 许可有时无法被 OAuth 识别
5. **无多客户端**：仅终端 TUI，无 Web 或桌面应用
6. **社区规模**：虽 Stars 高但活跃开发者社区比 Claude Code 小
7. **Git 集成问题**：偶有未经请求的 `git add` 非跟踪文件
8. **功能迭代快**：API 和功能变化较快，文档可能滞后

## CLI 命令

```bash
# 启动交互式会话
gemini

# 非交互模式（Headless）
gemini -p "解释这段代码"

# 恢复会话
gemini --resume <session-id>

# 查看版本
gemini --version
```

### 斜杠命令（会话内，源码验证 37 个命令 + 1 隐藏 + 1 开发专用）

以下命令均从源码 `packages/cli/src/ui/commands/` 目录逐一提取，列出每个命令的名称、别名、描述、子命令、autoExecute 属性及核心实现逻辑。

```bash
# ── 核心操作 ──
/help            # 显示帮助信息（autoExecute: true）
/clear           # 清除屏幕和对话历史（触发 SessionEnd hook，重置 injectionService，生成新 sessionId，调用 geminiClient.resetChat()）
/compress        # 压缩上下文（别名: /summarize, /compact）。调用 geminiClient.tryCompressChat() 强制压缩
/copy            # 复制最后一条 AI 输出到剪贴板（从 history 中取 role=model 的最后一条）
/quit            # 退出 CLI（别名: /exit）。计算 wallDuration 并显示
/commands        # 管理自定义命令。子命令: reload（重新加载 .toml 文件中的自定义命令定义）

# ── 代理 & 工具 ──
/agents          # 管理代理。子命令: list（列出所有本地和远程代理的 name/displayName/description/kind）、enable <name>、disable <name>（通过 SettingScope 持久化）
/tools           # 管理工具。子命令: list（列出非 MCP 的 Gemini 内置工具）、desc（带描述列出工具）
/skills          # 管理技能。子命令: list [--all] [--nodesc]、link <path> [--scope user|workspace]、enable <name>、disable <name>。link 需要用户 consent 确认
/plan            # 切换到 Plan Mode（设置 ApprovalMode.PLAN）。显示当前已批准的计划文件内容。子命令: copy（复制已批准计划到剪贴板）

# ── 记忆 & 会话 ──
/memory          # 管理记忆。子命令: show（显示当前记忆内容）、add <text>（添加记忆条目）、reload|refresh（从源文件重新加载，调用 refreshMemory()）、list（列出所有 GEMINI.md 文件路径）
/resume          # 浏览自动保存的会话（打开 sessionBrowser 对话框）。子命令: save <tag>（保存当前对话为检查点，含覆盖确认）、resume|load <tag>（恢复检查点）、list（列出已保存的手动检查点）、delete <tag>、export <path>
/restore         # 恢复 Git 检查点。读取 .gemini 目录中的检查点文件，调用 performRestore() 恢复 Git 状态和对话历史
/rewind          # 回退到特定消息并重启对话。打开 RewindViewer 组件，支持三种结果: Cancel、RevertOnly（仅恢复文件变更）、RewindAndRevert（恢复文件并回退对话历史）。调用 recordingService.rewindTo()、revertFileChanges()、client.setHistory()

# ── 配置 ──
/settings        # 打开设置对话框（isSafeConcurrent: true）
/model           # 管理模型。默认打开 model 对话框（先 refreshUserQuota）。子命令: set <model-name> [--persist]（设置模型，--persist 写入持久配置）、manage（打开对话框）
/theme           # 打开主题选择对话框
/permissions     # 管理文件夹信任设置。子命令: trust [<directory-path>]（信任指定目录，默认 cwd）
/policies        # 管理策略。子命令: list（按 Normal/AutoEdit/Yolo/Plan 四种模式分组显示所有活跃策略规则，显示 decision/toolName/argsPattern/priority/source）
/hooks           # 管理 Hook。默认打开 HooksDialog 面板（显示所有注册的 hook）。子命令: enable <name>、disable <name>（通过 hookSystem.setHookEnabled() 生效）
/auth            # 认证管理。子命令: signin|login（打开 auth 对话框）、signout|logout（清除缓存凭据、重置 selectedType 设置、strip thoughts from history）
/footer          # 配置底部状态栏显示项（别名: /statusline）。打开 FooterConfigDialog

# ── 扩展 & MCP ──
/extensions      # 管理扩展。子命令: list、update <names>|--all、explore（打开扩展画廊）、install、uninstall、enable、disable、config。使用 ExtensionManager 和 McpServerEnablementManager
/mcp             # 管理 MCP 服务器。子命令: list [desc] [schema]（显示所有 MCP 服务器状态/工具/prompts/resources/auth 状态/enablement 状态）、auth [<server-name>]（OAuth 认证，支持自动发现和手动配置）、enable、disable、restart

# ── 信息 & 调试 ──
/stats           # 查看统计信息（别名: /usage，isSafeConcurrent: true）。默认显示会话统计（含 quota/tier/creditBalance）。子命令: session、model（显示模型配额信息）、tools（显示工具使用统计）
/about           # 显示版本信息（autoExecute: true，isSafeConcurrent: true）。包含: OS、sandbox 环境、model 版本、CLI 版本、auth 类型、GCP 项目、IDE 客户端、用户邮箱
/bug             # 提交 Bug 报告。收集 OS/sandbox/model/CLI 版本/内存使用/IDE/终端信息，导出对话历史，用 open 打开 GitHub issue 页面
/docs            # 在浏览器中打开文档（URL: https://goo.gle/gemini-cli-docs）
/upgrade         # 打开升级页面（仅 Google 登录用户可用，已是 Ultra tier 则提示已最高级）

# ── IDE ──
/ide             # IDE 集成管理。显示连接状态（Connected/Connecting/Disconnected）。子命令: connect、disconnect、status、install（安装 Gemini CLI Companion 扩展）
/editor          # 打开外部编辑器偏好设置对话框

# ── 终端 ──
/shells          # 切换后台 Shell 视图（别名: /bashes）
/vim             # 切换 Vim 模式（isSafeConcurrent: true）
/terminal-setup  # 配置终端多行输入键绑定（自动检测 VS Code/Cursor/Windsurf）
/shortcuts       # 切换快捷键面板显示

# ── 项目初始化 ──
/init            # 分析项目并创建 GEMINI.md 文件（如不存在则先创建空文件，再提交分析 prompt）
/setup-github    # 设置 GitHub Actions 工作流。下载 gemini-dispatch/gemini-assistant/issue-triage/pr-review 等工作流和命令文件

# ── 其他 ──
/privacy         # 显示隐私通知对话框
/directory       # 目录管理。支持添加/删除包含目录，多文件夹信任对话框，自动 refreshServerHierarchicalMemory
/oncall          # 维护者专用。子命令: dedup（对 status/possible-duplicate 标签的 issue 去重分类）、triage（issue 分类）
/corgi           # 切换 corgi 模式（隐藏命令，hidden: true）
/profile         # 切换调试性能分析显示（仅开发模式可用，isDevelopment 为 true 时才注册）
```

**命令类型系统**（源码 `types.ts`）：
- `CommandKind.BUILT_IN`：所有内置命令均使用此类型
- `autoExecute`：true 表示无需参数立即执行，false 表示需要用户输入参数或确认
- `isSafeConcurrent`：true 表示可在 AI 响应过程中安全执行（如 /about、/settings、/stats、/vim）
- `SlashCommandActionReturn` 支持多种返回类型：`message`、`dialog`（内置对话框）、`custom_dialog`（自定义 React 组件）、`quit`、`submit_prompt`、`confirm_action`、`logout`

## 配置

```
~/.gemini/                    # 全局配置
├── settings.json             # 全局设置
├── policies/                 # 全局策略目录（含 *.toml 文件，auto-saved.toml 为自动保存）
├── GEMINI.md                 # 全局记忆/系统提示
├── sessions/                 # 会话存储
├── history/                  # 检查点历史
├── skills/                   # 用户技能
├── agents/                   # 用户代理定义
└── extensions/               # 已安装扩展

.gemini/                      # 项目级配置
├── settings.json             # 项目设置
├── policies/                 # 项目策略目录（含 *.toml 文件）
├── GEMINI.md                 # 项目自定义系统提示
├── skills/                   # 项目技能
└── agents/                   # 项目代理定义

.geminiignore                 # 项目根目录，文件过滤（类 .gitignore）
```

**设置结构**：
```jsonc
// settings.json
{
  "auth": {
    "defaultAuth": "oauth-personal",
    "apiKey": "YOUR_GEMINI_API_KEY"
  },
  "model": "gemini-3-pro",
  "approvalMode": "default",  // default | autoEdit | yolo | plan
  "agents": {
    "overrides": {
      "generalist": { "model": "gemini-3-flash" }
    },
    "browser": { /* 浏览器代理自定义配置 */ }
  },
  "mcp": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "mcp-server"],
      "env": {},
      "autoStart": true
    }
  },
  "hooks": {
    "BeforeTool": [{ "matcher": "...", "hooks": [...] }]
  },
  "telemetry": { /* OpenTelemetry 配置 */ },
  "accessibility": { /* 无障碍设置 */ },
  "plan": { /* 规划模式设置 */ },
  "extensions": [ /* 扩展列表 */ ],
  "general": {
    "checkpointing": { "enabled": true }
  }
}
```

**配置优先级**（从高到低）：
1. 远程管理员设置（Remote Admin）
2. CLI 标志 / 环境变量
3. 系统设置（平台系统配置路径，如 `/etc/gemini-cli/settings.json`）
4. 项目/工作区设置（`.gemini/settings.json`）
5. 用户设置（`~/.gemini/settings.json`）
6. 系统默认值（内置 Schema 默认值）
7. 扩展设置

## 定价/配额

| 计划 | 价格 | 请求限制 | 可用模型 |
|------|------|---------|---------|
| **Google 账号登录** | 免费 | 1,000 req/day, 60/min | Gemini Pro + Flash |
| **Gemini API Key（免费）** | 免费 | 250 req/day, 10/min | Flash only |
| **Code Assist Standard** | 付费 | 1,500 req/day, 120/min | Pro + Flash |
| **Code Assist Enterprise** | 付费 | 2,000 req/day, 120/min | Pro + Flash |
| **Vertex AI** | 按量付费 | 按 Token 计费 | 全系列 |
| **AI Pro / AI Ultra 订阅** | 固定月费 | 更高限额 | Pro + Flash |
| **Vertex AI Express Mode** | 90 天免费试用 | 试用期限额 | 全系列 |

## 使用场景

- **最适合**：Google Cloud 用户、需要大免费额度的开发者、Gemini 1M 上下文场景
- **适合**：需要策略引擎精细控制的安全敏感场景、CI/CD 自动化（Headless 模式）
- **不太适合**：需要多模型切换的用户、非 Google 生态用户、需要 Web/桌面客户端的用户

## 项目演进（2025.06 — 2026.03）

### 里程碑时间线

| 版本 | 日期 | 里程碑 |
|------|------|--------|
| **v0.1.0** | 2025-06-25 | **首次公开发布**，基础代理循环 + 文件工具 + Shell 执行 |
| v0.1.14 | 2025-07-25 | **P1 安全修复**：提示注入/命令劫持漏洞修复 |
| **v0.4.0** | 2025-09-01 | CloudRun + Security 扩展，智能编辑工具 |
| **v0.6.0** | 2025-09-15 | 数据库扩展（AlloyDB、BigQuery、Cloud SQL 等），聊天分享，提示历史 |
| **v0.8.0** | 2025-09-29 | **扩展系统上线**，geminicli.com 文档站 |
| **v0.9.0** | 2025-10-06 | **交互式 Shell**（vim、rebase、嵌套 gemini） |
| **v0.12.0** | 2025-10-27 | **模型路由**（Flash vs Pro），`/model` 命令，子代理 |
| **v0.16.0** | 2025-11-10 | **Gemini 3 模型发布** |
| v0.19.0 | 2025-11-24 | Zed 编辑器集成 |
| **v0.22.0** | 2025-12-22 | 免费层 Gemini 3 访问，预装到 Google Colab |
| **v0.23.0** | 2026-01-07 | **Agent Skills**（实验性） |
| **v0.26.0** | 2026-01-27 | Agent Skills 默认启用 |
| v0.28.0 | 2026-02-10 | Positron IDE 支持 |
| **v0.29.0** | 2026-02-17 | **Plan Mode**，Gemini 3 成为所有用户默认模型 |
| **v0.30.0** | 2026-02-25 | **SDK 包**，策略引擎 |
| v0.31.0 | 2026-02-27 | Gemini 3.1 Pro 预览，实验性浏览器代理 |
| v0.33.0 | 2026-03-11 | 远程代理 HTTP 认证（A2A） |
| **v0.34.0** | 2026-03-17 | Plan Mode 默认启用，原生 gVisor + LXC 沙箱 |
| v0.36.0-preview | 2026-03-24 | 最新预览版（Linux Bubblewrap/Seccomp 沙箱等） |

不到一年发布 **36 个主要版本**，从零开始成长为 ~99k Stars 的顶级开源项目。

### 开发节奏
- **总提交数**：8,910+
- **活跃开发天数**：339 天
- **峰值日**：2026-03-19（152 次提交）
- **发布频率**：每周稳定版 + 每日夜间版
- **Google Summer of Code 2026**：4 个项目被接受（性能监控、行为评估、测试套件优化、长上下文评估数据集）

### v0.34.0 关键变化（2026-03-17）
- **Plan Mode 默认启用**：新用户默认进入规划模式
- **原生 gVisor 沙箱**：用户空间内核级隔离（最强隔离）
- **LXC/LXD 沙箱**：完整系统容器（实验性）
- **Windows 原生沙箱**：无需第三方工具

### v0.29.0 ~ v0.30.0 关键变化（2026-02）
- **Plan Mode**：只读分析规划模式
- **SDK 包**：公共 SDK 支持编程式使用
- **策略引擎**：TOML 格式策略文件系统
- **Gemini 3 默认**：所有用户统一使用 Gemini 3

### v0.12.0 关键变化（2025-10-27）
- **模型路由**：可插拔策略自动在 Flash/Pro 间切换
- **子代理系统**：内置 generalist、codebase_investigator 等子代理
- **`/model` 命令**：手动模型切换

### v0.8.0 关键变化（2025-09-29）
- **扩展系统**：Git/Local/GitHub Release 安装
- **geminicli.com**：官方文档站上线

### v0.1.0 关键变化（2025-06-25，首发）
- **基础代理循环**：ReAct 模式
- **核心工具**：文件读写、Shell 执行、Grep 搜索
- **MCP 支持**：Stdio/SSE 传输
- **Google OAuth**：首次认证引导流程
- Google 官方博客公告，TechCrunch、InfoQ 等媒体报道

## IDE 集成

| 编辑器 | 状态 | 说明 |
|--------|------|------|
| **VS Code** | 官方扩展（Preview） | "Gemini CLI Companion"，需 VS Code 1.99+。工作区上下文（最近 10 文件、光标位置、选区最多 16KB）、原生 Diff 查看器、命令面板集成（Ctrl+S 接受 Diff） |
| **Zed** | 官方支持 | v0.19.0+ 集成 |
| **Positron IDE** | 官方支持 | v0.28.0+ 支持 |
| **Google Colab** | 预装 | v0.22.0+ 预装在 Colab 环境 |
| **Vertex AI Workbench** | 原生可用 | Cloud 环境直接使用 |
| **Neovim** | 社区插件 | nvim Gemini Companion、gemini-cli.nvim |

**VS Code 扩展命令**：
- `gemini.diff.accept`（Ctrl+S / Cmd+S）— 接受 Diff
- `gemini.diff.cancel` — 关闭 Diff 编辑器
- `gemini-cli.runGeminiCLI` — 启动 CLI
- `gemini-cli.showNotices` — 第三方通知

## 企业功能

- **Headless 模式**：CI/GitHub Actions 自动激活，支持脚本化工作流
- **多种沙箱**：Seatbelt / Bubblewrap / Docker / Podman / gVisor / LXC / Windows Sandbox
- **策略引擎**：项目级 TOML 策略文件，精细控制工具执行权限
- **可信文件夹**：按目录控制执行策略（v0.24.0+ 默认 untrusted）
- **Shell 命令白名单**：粒度化 Shell 命令许可（v0.24.0+）
- **遥测 & 监控**：OpenTelemetry GenAI 标准指标，OTLP/GCP 导出
- **Vertex AI 集成**：企业认证（ADC、服务账号）、SLA、区域数据驻留
- **Code Assist 许可**：Standard（1500 req/day）/ Enterprise（2000 req/day）层级
- **远程子代理**：A2A 协议 + HTTP 认证，跨服务代理通信
- **扩展系统**：企业可开发内部扩展，统一分发
- **安全扩展**：官方 `gemini-cli-extensions/security`，代码漏洞扫描（`/security:analyze`）

## 安全

**已修复漏洞**：
- **P1 提示注入漏洞**（2025-06-27 Tracebit 发现，v0.1.14 修复）：命令白名单绕过、空白字符视觉隐藏、通过 README.md/项目上下文文件注入，可导致静默任意代码执行
- **数据泄露漏洞**（已修复）：修复了可能导致静默数据外泄的缺陷

**安全特性**：
- **沙箱**：无沙箱（默认，带红色警告）→ Seatbelt / Bubblewrap / Docker / Podman / gVisor / LXC / Windows Sandbox（7 种后端可选）
- **安全扩展**：官方安全扩展，支持代码变更和 PR 的漏洞扫描
- **Shell 命令白名单**（v0.24.0+）
- **默认 untrusted 文件夹**（v0.24.0+）
- **所有 Shell 命令需权限**（v0.1.14+）
- **私有 IP 阻止**：web_fetch 工具阻止访问私有 IP 地址
- **`.env` 文件保护**：默认拒绝访问环境文件

## 评估框架

25 个行为评估套件（`/evals/`）：

| 评估 | 用途 |
|------|------|
| automated-tool-use | 工具执行准确性 |
| generalist_agent | 通用代理能力 |
| generalist_delegation | 通用代理委派 |
| subagents | 子代理集成 |
| model_steering | 模型选择路由 |
| save_memory | 记忆持久化 |
| hierarchical_memory | 分层记忆 |
| tool_output_masking | 输出保护 |
| validation_fidelity | Schema 验证 |
| validation_fidelity_pre_existing_errors | 已有错误下的验证 |
| grep_search_functionality | 搜索工具 |
| ask_user | 用户交互 |
| cli_help_delegation | 命令帮助 |
| answer-vs-act | 响应类型选择 |
| interactive-hang | 挂起预防 |
| concurrency-safety | 并行安全 |
| plan_mode | 规划模式 |
| edit-locations-eval | 编辑位置准确性 |
| shell-efficiency | Shell 效率 |
| frugalReads | 读取节约 |
| frugalSearch | 搜索节约 |
| gitRepo | Git 仓库操作 |
| sandbox_recovery | 沙箱恢复 |
| tracker | 任务追踪 |
| redundant_casts | 冗余转换检测 |

集成测试支持三种沙箱模式：无沙箱、Docker、Podman。

## 社区生态

### 主要分叉
- **Qwen Code**（`QwenLM/qwen-code`）：阿里云官方分叉，使用 Qwen3-Coder-480B，增加多提供商支持、免费 OAuth、6 语言国际化
- **LLxprt Code**：社区分叉，支持 Ollama/OpenAI/Anthropic/OpenRouter 多模型
- **qwen_cli_coder**、**easy-llm-cli**、**open-gemini-cli**、**ollama-code**：各类社区多模型分叉

### 社区项目
- **awesome-gemini-cli**（Piebald-AI）：扩展和资源精选列表
- **Tars**：本地优先长时间自主代理编排
- **hcom**：跨终端代理间消息通信
- **Gemini-flow**：多代理工作流
- **nvim Gemini Companion / gemini-cli.nvim**：Neovim 集成
- **iFlow CLI**：仓库分析 + 复杂工作流自动化

### 官方扩展
CloudRun、Security、Hugging Face、Monday.com、ElevenLabs、Jules、Conductor、Endor Labs、Data Commons，以及 AlloyDB、BigQuery、Cloud SQL 等数据库扩展。

### 社区活动
- **GitHub Discussions**：22,000+ 讨论
- **Google Summer of Code 2026**：4 个项目被接受
- 100+ 贡献者，活跃的 PR 周转

## 与 Qwen Code 的关系

Qwen Code 是 Gemini CLI 的分叉项目（Apache-2.0 合法），继承了：
- 代理循环架构（GeminiClient + Scheduler）
- 工具系统（声明式工具 + 注册表）
- 策略/权限模型
- Ink + React 终端 UI
- MCP 集成
- 会话管理

Qwen Code 在此基础上增加了：多提供商支持、免费 OAuth、6 语言国际化、多代理终端等。（初期版本曾残留 Gemini 品牌文档，引起了一些争议。）

## 资源链接

- [GitHub](https://github.com/google-gemini/gemini-cli)
- [官网 & 文档](https://geminicli.com)
- [安装指南](https://geminicli.com/docs/get-started/installation/)
- [配置参考](https://geminicli.com/docs/reference/configuration/)
- [工具参考](https://geminicli.com/docs/reference/tools/)
- [策略引擎文档](https://geminicli.com/docs/reference/policy-engine/)
- [扩展文档](https://geminicli.com/docs/cli/extensions/)
- [Agent Skills 文档](https://geminicli.com/docs/cli/skills/)
- [沙箱文档](https://geminicli.com/docs/cli/sandbox/)
- [IDE 集成](https://geminicli.com/docs/ide-integration/)
- [配额与定价](https://geminicli.com/plans/)
- [Changelog](https://geminicli.com/docs/changelogs/)
- [贡献指南](https://geminicli.com/docs/contributing/)
- [VS Code 扩展](https://marketplace.visualstudio.com/items?itemName=Google.gemini-cli-vscode-ide-companion)
- [npm 包](https://www.npmjs.com/package/@google/gemini-cli)
- [awesome-gemini-cli](https://github.com/Piebald-AI/awesome-gemini-cli)
- [安全扩展](https://github.com/gemini-cli-extensions/security)
- [Google 官方博客公告](https://blog.google/technology/developers/introducing-gemini-cli-open-source-ai-agent/)
