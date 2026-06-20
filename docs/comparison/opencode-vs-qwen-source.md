# 20. OpenCode vs Qwen Code：源码级深度对比

> 基于本地源码仓库的深入分析，揭示两个开源 CLI 编程代理的架构设计差异

## 项目概览

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **开发者** | Anomaly Innovations | 阿里云 |
| **许可证** | MIT | Apache-2.0 |
| **语言** | TypeScript 5.8 | TypeScript 5.3+ |
| **运行时** | Bun 1.3.14（主）/ Node.js 22+（兼容） | Node.js 20+ |
| **上游项目** | 原创 | Google Gemini CLI 分叉 |
| **核心定位** | 多客户端 AI 开发平台（v1.17.8） | 终端编程代理 |

## 1. 项目结构

### OpenCode Monorepo（25 个包）

```
opencode/
├── packages/opencode/         # 主入口包：CLI 命令/会话编排/服务器路由/插件宿主
├── packages/core/             # 核心引擎：工具/会话/权限/存储/Agent（Effect 化）
├── packages/cli/              # CLI 入口与命令
├── packages/server/           # HTTP/SSE 服务器
├── packages/tui/              # 终端 UI（OpenTUI + Solid.js）
├── packages/llm/              # LLM 集成层
├── packages/app/              # Web 应用前端（SolidJS）
├── packages/desktop/          # Electron 桌面应用
├── packages/console/          # 控制台
├── packages/sdk/              # JavaScript SDK
├── packages/ui/               # 共享 UI 组件库（37 种主题）
├── packages/plugin/           # 插件系统（21 种 Hook）
├── packages/enterprise/       # 企业功能
├── packages/identity/         # 认证/身份
├── packages/containers/       # 容器相关
├── packages/slack/            # Slack 集成
├── packages/stats/            # 统计
├── packages/http-recorder/    # HTTP 录制（测试/调试）
├── packages/effect-drizzle-sqlite/  # Effect × Drizzle × SQLite 适配
├── packages/effect-sqlite-node/     # Effect SQLite (Node) 驱动
├── packages/storybook/        # Storybook 组件文档
├── packages/docs/             # 文档
├── packages/web/              # Web 工具
├── packages/function/         # 函数处理
└── packages/script/           # 构建脚本
```

### Qwen Code Monorepo（14 个包）

```
qwen-code/
├── packages/cli/             # CLI 界面（Ink 7 / React 19）
├── packages/core/            # 核心引擎和工具（分离）
├── packages/sdk-typescript/  # TypeScript SDK
├── packages/sdk-java/        # Java SDK
├── packages/sdk-python/      # Python SDK
├── packages/test-utils/      # 测试工具
├── packages/vscode-ide-companion/  # VS Code 扩展
├── packages/zed-extension/   # Zed 编辑器扩展
├── packages/webui/           # Web UI
├── packages/web-shell/       # Web Shell UI（qwen serve 提供）
├── packages/web-templates/   # Web 模板
├── packages/desktop/         # 桌面应用
├── packages/acp-bridge/      # Agent Client Protocol 桥接
└── packages/channels/        # 渠道/通道集成
```

**关键差异**：
- 两者都把 CLI 与核心引擎分离：OpenCode 已从早期的单一 `packages/opencode` 拆出 `core`/`cli`/`server`/`tui`/`llm` 等包；Qwen Code 一直是 `packages/cli` + `packages/core` 分离
- 两者都在向多客户端扩展：OpenCode 有 Electron 桌面 + Web 应用（`app`）共享后端；Qwen Code 新增 `desktop`/`web-shell`/`web-templates`（`qwen serve` 提供 Web Shell UI）+ `acp-bridge`（Agent Client Protocol）
- OpenCode 有企业（enterprise）、身份（identity）、Slack、容器（containers）、统计（stats）等独立包，并有 `effect-drizzle-sqlite`/`effect-sqlite-node` 专用 Effect 适配包；Qwen Code 提供 Java + Python 双 SDK
- OpenCode 有 Storybook 组件文档系统

## 2. 核心架构

### OpenCode：客户端/服务器架构

```
客户端层 (TUI / Web App / Desktop-Electron)
    │
    ▼
Hono HTTP 服务器 (localhost) + WebSocket + mDNS 服务发现
    │
    ▼
代理系统 (7 内置代理) ← Skill 系统 / Plugin Hook
    │
    ▼
Vercel AI SDK v6 → models.dev 动态模型注册 → 100+ LLM 提供商
    │
    ▼
工具注册表 (16 工具) → 文件系统/Shell/LSP(38)/MCP
    │
    ▼
SQLite (Drizzle ORM, WAL) + Git Snapshot 快照系统
    │
    ▼
远程工作区（实验性）← Adaptor + SSE 事件同步
```

- 通过 HTTP + WebSocket 解耦客户端和服务器
- 支持 mDNS 服务发现，可远程连接
- 所有客户端共享同一个后端进程
- 核心已拆分为 `core`/`server`/`cli`/`tui`/`llm` 多包，并向 Effect 框架迁移（含 `effect-drizzle-sqlite`/`effect-sqlite-node` 专用适配包）

### Qwen Code：单进程直连架构

```
CLI (Ink/React)
    │
    ▼
GeminiClient (会话编排)
    │
    ▼
ContentGenerator (多提供商抽象)
    │
    ▼
CoreToolScheduler (工具调度)
    │
    ▼
PermissionManager → 工具执行
    │
    ▼
JSONL 文件存储
```

- 单进程运行，CLI 直接调用核心库
- 无独立 HTTP 服务器
- 会话存储为 JSONL 文件

**设计哲学差异**：
- OpenCode 追求 **平台化**（多客户端共享后端）
- Qwen Code 追求 **简洁性**（单进程，快速启动）

## 3. TUI 框架

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **UI 库** | OpenTUI + Solid.js（packages/tui） | Ink 7 + React 19 |
| **响应式** | Solid.js 信号 | React Hooks |
| **状态管理** | 实例级 State + Event Bus (GlobalBus) | React Context |
| **渲染** | OpenTUI 自定义终端渲染 | Ink 适配 Yoga 布局 |
| **主题** | 37 种主题（含 AMOLED、调色板生成） | 主题系统 |

OpenCode 选择 Solid.js 是为了更细粒度的响应式更新（信号级而非组件级）；Qwen Code 使用 React 生态更成熟，Ink 社区更大。

## 4. LLM 集成

### 提供商支持

| 提供商 | OpenCode | Qwen Code |
|--------|----------|-----------|
| Anthropic | ✓ | ✓ |
| OpenAI | ✓ | ✓ |
| Google Gemini | ✓ | ✓ |
| Vertex AI | ✓ | ✓ |
| Amazon Bedrock | ✓ | ✗ |
| Mistral | ✓ | ✗ |
| Groq | ✓ | ✗ |
| Cohere | ✓ | ✗ |
| XAI | ✓（Responses API） | ✗ |
| DeepInfra | ✓ | ✗ |
| Cerebras | ✓ | ✗ |
| Together AI | ✓ | ✗ |
| Perplexity | ✓ | ✗ |
| OpenRouter | ✓ | ✓（内置预设） |
| Cloudflare Workers AI | ✓（插件认证） | ✗ |
| Snowflake Cortex | ✓（插件认证） | ✗ |
| SAP AI Core | ✓ | ✗ |
| Qwen/DashScope | ✓（@ai-sdk/alibaba） | ✓（含 Qwen OAuth） |
| ModelScope | ✗ | ✓ |
| DeepSeek / MiniMax / Z.ai / Idealab | ✓（models.dev/兼容） | ✓（内置预设） |
| GitHub Copilot | ✓（插件认证） | ✗ |
| GitLab | ✓（插件 + Agent Platform） | ✗ |
| OpenAI 兼容 BYOK | ✓（`@ai-sdk/openai-compatible` 默认适配） | ✓（custom provider 预设） |
| 第一方免费层 | ✗ | ✗（Qwen OAuth 免费层 2026-04-15 已停，现需订阅/BYOK） |

### SDK 策略

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **统一 SDK** | Vercel AI SDK v6 | 无（各自 SDK） |
| **抽象层** | 单一 `streamText()` API | ContentGenerator 接口 |
| **提供商适配** | `transform.ts` 统一处理 + `@ai-sdk/openai-compatible` 默认适配 | 各 Generator 独立实现 |
| **模型信息** | [models.dev](https://models.dev) 动态拉取（含定价、能力、modalities） | 预设内置（`all-providers.ts`）+ custom |
| **Provider 管理** | models.dev 动态注册 + `enabled_providers`/`disabled_providers` 白黑名单 + 认证插件（Codex/Copilot/GitLab/Azure/Cloudflare/Snowflake/Xai 等 10 个） | 预设 provider + custom BYOK |

OpenCode 通过 Vercel AI SDK 实现 **一次编写，多提供商运行**；Qwen Code 为每个提供商编写独立的 ContentGenerator 实现，灵活但代码量大。

### 重试与限流

```
OpenCode:
- 无明确的统一重试策略文档
- 依赖 Vercel AI SDK 内置重试

Qwen Code:
- 速率限制：最多 10 次重试，60 秒间隔
- 无效流：最多 2 次重试，2 秒初始延迟
- 与 Claude Code 对齐的重试参数
```

## 5. 代理系统

### OpenCode 多代理（7 内置）

| 代理 | 类型 | 权限 | 用途 |
|------|------|------|------|
| build | 主代理 | 完全访问 + question + plan_enter | 默认代理，代码开发 |
| plan | 主代理 | 只读（edit deny）+ plan_exit | 分析规划，只能写 plan 文件 |
| general | 子代理 | 受限（无 todo） | 复杂多步骤研究，支持并行 |
| explore | 子代理 | 只读（grep/glob/read/bash/web） | 快速搜索，支持 quick/medium/very thorough |
| compaction | 隐藏 | 全部 deny | 会话压缩 |
| title | 隐藏 | 内部 | 自动标题生成 |
| summary | 隐藏 | 内部 | 自动摘要生成 |

- 用户可通过 `opencode.json` 或 `.opencode/agent/*.md`（frontmatter + 提示）定义自定义代理（独立模型、温度、系统提示、最大步数）
- 子代理通过 `task` 工具（`subagent_type`）调用，TUI 中也可用 `@general`/`@explore` 引用
- **Skill 系统**：原生 Agent Skill + 权限系统 + per-agent 过滤

### Qwen Code 代理/子代理

- **主代理**：GeminiClient 实例
- **子代理**：通过 `agent` 工具生成
  - 支持 builtin / user / project / session / extension 五个级别
  - 每个子代理可配置独立工具白名单、系统提示、模型
- **Arena 模式**（实验性）：
  - Team / Swarm / Arena 三种协作模式
  - Tmux / iTerm2 / 进程内 三种后端
  - 可在终端分屏显示多个并行代理

**Qwen Code 的多代理终端是独特亮点**，OpenCode 没有类似的可视化多代理并行能力。

## 6. 工具系统

### 工具注册

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **定义方式** | `Tool.define()` 包装器 | `DeclarativeTool` 抽象类 |
| **校验** | Zod schema | FunctionDeclaration (Gemini 格式) |
| **输出截断** | truncate.ts 截断 + truncation-dir | 可配置 |
| **注册** | `registry.ts` 动态加载 | `tool-registry.ts` 集中管理 |
| **外部工具** | MCP + Plugin Hook + Skill | MCP + 扩展 |
| **内置工具数** | 16（13 无条件 + 3 有条件） | 34（ToolNames 枚举）+ 可选 computer-use 套件（~35） |

### 内置工具对比

| 工具 | OpenCode | Qwen Code |
|------|----------|-----------|
| edit | ✓ | ✓ |
| write | ✓ | ✓ (write_file) |
| read | ✓ | ✓ (read_file) |
| bash | ✓ (shell) | ✓ (run_shell_command) |
| grep | ✓ | ✓ (grep_search) |
| glob | ✓ | ✓ |
| list_directory | ✗（ls 工具已移除） | ✓ (list_directory) |
| apply_patch | ✓（按模型：`gpt-` 且非 `oss`/`gpt-4` 时替代 edit/write） | ✗ |
| web_fetch | ✓ | ✓ |
| web_search | ✓（Exa / Parallel，需启用） | ✗（仅 web_fetch；web_search 非内置） |
| lsp | ✓（实验性 flag，38 种 LSP 服务器） | ✓ |
| agent/task | ✓ (task) | ✓ (agent) |
| skill | ✓（原生 Skill + 权限） | ✓ |
| question | ✓（按客户端启用） | ✓ (ask_user_question) |
| todo | ✓ (todowrite) | ✓ (todo_write) |
| save_memory | ✗ | ✓ |
| notebook_edit | ✗ | ✓ (notebook_edit) |
| plan_enter/exit | ✓ plan_exit（实验性 flag + CLI） | ✓ (enter/exit_plan_mode) |
| invalid（无效工具标记） | ✓ | ✗ |
| 编排/调度工具 | ✗ | ✓（cron 定时 ×3、task 后台队列 ×4、team 多代理 ×2、worktree 隔离 ×2、workflow、monitor、send_message、loop_wakeup、tool_search 等十余个） |
| computer-use 套件 | ✗ | ✓（~35，flag 控制） |

**关键差异**：
- OpenCode 的工具注册表是 16 个工具（13 无条件 + 3 有条件）。`apply_patch`（GPT 优化的 diff 格式）按模型与 `edit`/`write` 互斥（`gpt-` 且非 `oss`/`gpt-4` 时启用）；`web_search` 需启用 Exa 或 Parallel 后端；`lsp`/`plan_exit` 受实验性 flag 控制
- 早期文档列出的 `ls`/`multiedit`/`todoread`/`codesearch`/`batch` 工具在当前源码中已不存在
- Qwen Code 内置工具显著扩张：除文件/Shell/搜索类外，新增 `save_memory`（持久记忆到 Markdown）、`notebook_edit`，以及一整套 harness 编排工具（cron 定时、task 后台队列、team 多代理、worktree 隔离、workflow 编排、monitor、tool_search）和可选的 computer-use 套件——对标进阶 Agent harness
- Web 搜索：OpenCode 用 Exa/Parallel；Qwen Code 当前内置工具中无 `web_search`（仅 `web_fetch`），联网搜索改由 MCP 等外部工具提供
- OpenCode LSP 工具支持 38 种语言服务器 + 26 种 Formatter

## 7. 权限系统

### OpenCode

```
规则优先级：远程 → 全局 → 项目 → .opencode → 内联
权限类型：edit, write, read, bash, question, external_directory,
          plan_enter, plan_exit, doom_loop

特色：
- token 级 bash 命令解析（`shellTokens`），自动提取命令中的外部目录做权限判断
  （tree-sitter/parser-based 解析在 `bash.ts` 中标记为 TODO，尚未实装）
- Doom Loop 保护（`DOOM_LOOP_THRESHOLD=3`，连续 3 步重复循环触发 `doom_loop` 权限询问）
- 文件时间锁（`StaleContentError`，检测编辑期间文件被外部修改）
```

### Qwen Code

```
规则优先级：deny > ask > allow > default
配置源：settings.json > 代理默认 > SDK 参数

特色：
- Shell 命令语义解析（extractShellOperations）
- 模式匹配（路径和命令）
- 会话级和持久化规则
- Hook 系统可拦截权限请求
```

**核心差异**：两者当前都对 Shell 命令做 token/语义级解析（OpenCode 的 tree-sitter AST 解析仍是源码 TODO，未实装；Qwen Code 用 `extractShellOperations` 做语义解析）。两者都支持分层配置，但 OpenCode 增加了远程配置（企业级）。

## 8. 存储系统

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **数据库** | SQLite + Drizzle ORM | JSONL 文件 |
| **会话存储** | 关系表（Session/Message/Part） | 单文件 JSONL |
| **查询** | SQL 查询 | 文件读取 + 分页 |
| **并发** | WAL 模式 | 文件锁 |
| **迁移** | Drizzle Kit 迁移 | 无（追加写入） |
| **备份** | 内置导出/导入 | 文件拷贝 |

OpenCode 的 SQLite 方案更适合大量会话和复杂查询；Qwen Code 的 JSONL 方案更简单、可移植。

## 9. 配置系统

### OpenCode

```
优先级（低→高）：
1. 远程 .well-known/opencode（企业）
2. 全局 ~/.config/opencode/opencode.json
3. OPENCODE_CONFIG 环境变量
4. 项目 opencode.json
5. .opencode/opencode.json
6. OPENCODE_CONFIG_CONTENT 内联 JSON
```

### Qwen Code

```
优先级（低→高）：
1. 内置默认值
2. ~/.qwen/settings.json
3. .qwen/settings.json（项目级）
4. 环境变量
5. CLI 参数
```

两者都支持分层配置。OpenCode 多了远程配置和内联 JSON 支持（企业场景），Qwen Code 更简洁。

## 10. 扩展/插件系统

### OpenCode 插件

```typescript
// Hook 类型（共 21 种，packages/plugin/src/index.ts）
dispose                                  // 插件卸载
event                                    // 事件监听
config                                   // 配置修改
tool                                     // 工具定义（注册自定义工具）
auth                                     // 认证中间件
provider                                 // 提供商中间件
chat.message                             // 消息接收处理
chat.params                              // LLM 参数修改（温度等）
chat.headers                             // LLM 请求头修改
permission.ask                           // 权限请求拦截
command.execute.before                   // 命令执行前拦截
tool.execute.before                      // 工具执行前拦截
shell.env                                // Shell 环境变量注入
tool.execute.after                       // 工具执行后处理
tool.definition                          // 修改工具描述/参数
experimental.chat.messages.transform     // 消息变换
experimental.chat.system.transform       // 系统提示变换
experimental.provider.small_model        // 小模型选择
experimental.session.compacting          // compaction 前上下文注入
experimental.compaction.autocontinue     // compaction 后自动续写控制
experimental.text.complete               // 自定义补全

// 内置认证插件
CodexAuthPlugin, CopilotAuthPlugin, GitlabAuthPlugin,
AzureAuthPlugin, CloudflareWorkersAuthPlugin, CloudflareAIGatewayAuthPlugin,
SnowflakeCortexAuthPlugin, XaiAuthPlugin

// 加载方式
npm install opencode-plugin-xxx
// 或 file:///path/to/plugin
```

### Qwen Code 扩展

```typescript
// 扩展类型
MCP 服务器, Skills, Subagents, Hooks, Channels

// 安装方式
Git clone / Release 下载

// 兼容性
Qwen Code 原生扩展
Claude 插件转换 (claude-converter.ts)
Gemini 扩展转换 (gemini-converter.ts)

// Hook 事件（共 20 种，packages/core/src/hooks/types.ts）
PreToolUse, PostToolUse, PostToolUseFailure, PostToolBatch,
UserPromptSubmit, UserPromptExpansion, SessionStart, SessionEnd,
Stop, StopFailure, SubagentStart, SubagentStop,
PreCompact, PostCompact, PermissionRequest, PermissionDenied,
Notification, TodoCreated, TodoCompleted, InstructionsLoaded
```

**关键差异**：OpenCode 有 21 种 hook（可修改 LLM 参数/请求头、拦截权限请求、注入 shell 环境变量、控制 compaction 行为等），且有 Skill 系统（原生 Agent Skill）；Qwen Code 的扩展更面向用户（技能、代理、20 种事件 Hook、Channels），且能转换 Claude/Gemini 的扩展格式。

## 11. 国际化

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **UI 语言** | Web/桌面 16 种（TUI 仅英文） | 9 种（简中/繁中/英/日/德/法/俄/葡/加泰罗尼亚） |
| **自定义语言包** | 不支持 | ✓（~/.qwen/locales/） |
| **模型输出语言** | 跟随系统 | 可独立配置 |
| **语言检测** | 无 | Intl API + 环境变量 |

OpenCode Web/桌面应用支持 16 种语言，但 TUI 仅英文；Qwen Code CLI 原生支持 9 语言。对非英语的纯终端用户，Qwen Code 仍有优势。

## 12. 独特技术特性对比

### 仅 OpenCode 有

| 特性 | 说明 |
|------|------|
| **客户端/服务器架构** | TUI + Web App + Desktop(Electron) 经 HTTP/WS 共享同一后端 |
| **Doom Loop 保护** | `DOOM_LOOP_THRESHOLD=3`，连续重复循环触发 `doom_loop` 权限询问 |
| **文件时间锁** | `StaleContentError` 检测编辑期间文件外部修改 |
| **mDNS 服务发现** | 远程连接支持 |
| **apply_patch 工具** | 按模型替代 edit/write（`gpt-` 且非 `oss`/`gpt-4`）的 diff 格式 |
| **远程工作区** | Adaptor 模式 + SSE 实时同步（实验性） |
| **Git-backed Session Review** | 基于 git 快照的变更追踪，侧面板 diff 可视化 + 行内注释 |
| **Session Fork & Restore** | 从任意消息分叉会话，或回退到历史消息恢复文件 |
| **Session 分享** | 同步到云端生成公开链接，SSR 渲染 diff |
| **38 种 LSP 服务器** | 覆盖主流及小众语言（含 Typst、Gleam、Julia 等） |
| **26 种 Formatter** | 从 Prettier 到 ormolu (Haskell)、cljfmt (Clojure) |
| **37 种主题** | 含 AMOLED、调色板生成 |
| **Prompt Stashing** | 暂存 prompt（TUI `stash`） |
| **models.dev 动态模型** | 自动拉取最新模型信息和定价 |
| **Effect 框架** | 核心服务迁移到 Effect（含 `effect-drizzle-sqlite`/`effect-sqlite-node` 专用包） |
| **Skill 系统** | 原生 Agent Skill + 权限 + per-agent 过滤 |

### 仅 Qwen Code 有

| 特性 | 说明 |
|------|------|
| **Plan 模式** | 显式规划→审批→执行流程（enter/exit_plan_mode） |
| **多代理终端** | Arena/Team/Swarm 模式 × Tmux/iTerm2/进程内 后端，分屏显示并行代理 |
| **Harness 编排工具** | cron 定时、task 后台队列、worktree 隔离、workflow 编排、monitor、tool_search 等内置工具 |
| **computer-use 套件** | ~35 个计算机操作工具（flag 控制） |
| **扩展格式转换** | Claude/Gemini 扩展自动转换（claude-converter/gemini-converter） |
| **CLI 9 语言国际化** | 终端 CLI 原生多语言支持（OpenCode TUI 仅英文） |
| **save_memory 工具** | 持久化记忆到 Markdown |
| **Loop 检测** | 多维阈值启发式（工具调用/内容/思维重复等），非 Levenshtein |
| **Java + Python SDK** | 企业级多语言 SDK |
| **Web Shell / 桌面** | `qwen serve` 提供 Web Shell UI，另有 desktop、acp-bridge 包 |

## 13. 性能与资源

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **启动时间** | 较慢（Hono 服务器 + SQLite + LSP 发现） | 较快（单进程直连） |
| **内存占用** | 较高（HTTP 服务器 + 数据库 + LSP 进程） | 较低（纯 CLI） |
| **安装体积** | 较大（25 包 Monorepo） | 中等（esbuild 打包） |
| **并发能力** | 强（HTTP 多客户端 + 远程工作区） | 弱（单进程） |

## 14. 适用场景总结

| 场景 | 推荐 | 原因 |
|------|------|------|
| **多 LLM 提供商** | OpenCode | 100+ 提供商通过 models.dev 动态接入 |
| **开源 + 灵活成本** | Qwen Code | Apache-2.0 + BYOK 任意 provider（含 DeepSeek 等低成本模型） |
| **中文开发** | Qwen Code | 9 语言 UI + 中文模型优化 |
| **企业部署** | OpenCode | 远程配置 + 多客户端 + 企业包 + MIT 许可 |
| **插件开发** | OpenCode | 更底层的 Hook 系统 + Skill 系统 |
| **扩展迁移** | Qwen Code | Claude/Gemini 扩展格式转换 |
| **多代理协作** | Qwen Code | Tmux/iTerm2 可视化并行 |
| **简单上手** | Qwen Code | 单进程直连 + 开箱即用 |

## 15. 代码质量

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **类型安全** | Zod 4 + Effect Schema + TypeScript strict | TypeScript strict + 部分 Zod |
| **测试** | Bun test + Playwright E2E | Vitest + msw/memfs mock |
| **代码风格** | Prettier (120 字符，无分号) | 标准 TS 风格 |
| **文档** | Storybook + 配置注释 | JSDoc + 部分中文注释 |
| **品牌化 ID** | ProviderID、ModelID、SessionID 等 Effect branded types | 字符串 ID |

---

*分析基于本地源码仓库（OpenCode `dev`、Qwen Code `main`），截至 2026 年 6 月。两个项目均在快速迭代中，具体实现可能已更新。*
