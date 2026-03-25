# 20. OpenCode vs Qwen Code：源码级深度对比

> 基于本地源码仓库的深入分析，揭示两个开源 CLI 编程代理的架构设计差异

## 项目概览

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **开发者** | Anomaly Innovations | 阿里云 |
| **许可证** | MIT | Apache-2.0 |
| **语言** | TypeScript 5.8 | TypeScript 5.3+ |
| **运行时** | Bun 1.3.11（主）/ Node.js 22（兼容） | Node.js 20+ |
| **上游项目** | 原创 | Google Gemini CLI 分叉 |
| **核心定位** | 多客户端 AI 开发平台（v1.3.0） | 终端编程代理 |

## 1. 项目结构

### OpenCode Monorepo（19 个包）

```
opencode/
├── packages/opencode/         # 核心 CLI/TUI + 代理后端（主包）
├── packages/app/              # Web 应用前端（SolidJS）
├── packages/console/          # 控制台（含 app/core/function/mail/resource）
├── packages/desktop/          # Tauri 桌面应用（Vite + SolidJS + Tauri v2）
├── packages/desktop-electron/ # Electron 桌面应用（备选平台）
├── packages/sdk/js/           # JavaScript SDK
├── packages/ui/               # 共享 UI 组件库（37 种主题）
├── packages/plugin/           # 插件系统
├── packages/enterprise/       # 企业功能
├── packages/identity/         # 认证/身份
├── packages/extensions/       # 扩展支持
├── packages/containers/       # 容器相关
├── packages/slack/            # Slack 集成
├── packages/storybook/        # Storybook 组件文档
├── packages/docs/             # 文档
├── packages/web/              # Web 工具
├── packages/function/         # 函数处理
├── packages/util/             # 工具函数
└── packages/script/           # 构建脚本
```

### Qwen Code Monorepo

```
qwen-code/
├── packages/cli/           # CLI 界面（Ink/React）
├── packages/core/          # 核心引擎和工具（分离）
├── packages/sdk-typescript/ # TypeScript SDK
├── packages/sdk-java/      # Java SDK
├── packages/test-utils/    # 测试工具
├── packages/vscode-ide-companion/  # VS Code 扩展
├── packages/webui/         # Web UI
└── packages/zed-extension/ # Zed 编辑器扩展
```

**关键差异**：
- OpenCode 19 个包，将核心逻辑和 CLI 合并在 `packages/opencode` 中；Qwen Code 将 CLI（`packages/cli`）和核心（`packages/core`）严格分离
- OpenCode 有 Tauri + Electron 双桌面平台；Qwen Code 有 VS Code 和 Zed 编辑器扩展
- OpenCode 有企业（enterprise）、Slack 集成、容器（containers）等独立包；Qwen Code 提供 Java SDK（面向企业集成）
- OpenCode 有 Storybook 组件文档系统

## 2. 核心架构

### OpenCode：客户端/服务器架构

```
客户端层 (TUI / Web / Desktop-Tauri / Desktop-Electron)
    │
    ▼
Hono HTTP 服务器 (localhost) + WebSocket + MDNS 服务发现
    │
    ▼
代理系统 (7 内置代理) ← Skill 系统 / Plugin Hook
    │
    ▼
Vercel AI SDK v5 → models.dev 动态模型注册 → 100+ LLM 提供商
    │
    ▼
工具注册表 (18 工具) → 文件系统/Shell/LSP(37)/MCP
    │
    ▼
SQLite (Drizzle ORM, WAL) + Git Snapshot 快照系统
    │
    ▼
远程工作区（实验性）← Adaptor + SSE 事件同步
```

- 通过 HTTP + WebSocket 解耦客户端和服务器
- 支持 MDNS 服务发现，可远程连接
- 所有客户端共享同一个后端进程
- Effect 框架逐步迁移（核心服务 Effect 化）

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
| **UI 库** | OpenTUI + Solid.js | Ink 6.2 + React 19 |
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
| OpenRouter | ✓ | ✗ |
| Cloudflare Workers AI | ✓ | ✗ |
| SAP AI Core | ✓ | ✗ |
| Qwen/DashScope | ✗ | ✓ |
| ModelScope | ✗ | ✓ |
| GitHub Copilot | ✓（插件认证） | ✗ |
| GitLab | ✓（插件 + Agent Platform） | ✗ |
| 免费 OAuth | ✗ | ✓（通义账号） |

### SDK 策略

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **统一 SDK** | Vercel AI SDK v5 | 无（各自 SDK） |
| **抽象层** | 单一 `streamText()` API | ContentGenerator 接口 |
| **提供商适配** | `transform.ts` 统一处理 + `@ai-sdk/openai-compatible` 默认适配 | 各 Generator 独立实现 |
| **模型信息** | [models.dev](https://models.dev) 动态拉取（含定价、能力、modalities） | 硬编码 `constants.ts` |
| **Provider 管理** | `enabled_providers` / `disabled_providers` 白黑名单 | 固定列表 |

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
| explore | 子代理 | 只读（grep/glob/read/bash/web） | 快速搜索，支持 quick/medium/thorough |
| compaction | 隐藏 | 全部 deny | 会话压缩 |
| title | 隐藏 | 内部 | 自动标题生成 |
| summary | 隐藏 | 内部 | 自动摘要生成 |

- 用户可通过 `opencode.json` 定义自定义代理（独立模型、温度、系统提示、最大步数）
- 子代理通过 `@general`、`@explore` 消息引用调用
- 新增 **Skill 系统**：原生 Agent Skill + 权限系统 + per-agent 过滤

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
| **内置工具数** | 18（14 无条件 + 4 有条件） | ~20 |

### 内置工具对比

| Agent | OpenCode | Qwen Code |
|------|----------|-----------|
| edit | ✓ | ✓ |
| write | ✓ | ✓ (write_file) |
| read | ✓ | ✓ (read_file) |
| bash | ✓ | ✓ (run_shell_command) |
| grep | ✓ | ✓ (grep_search) |
| glob | ✓ | ✓ |
| ls | 定义但未注册 | ✓ (list_directory) |
| apply_patch | ✓（GPT 专用） | ✗ |
| multiedit | ✓（定义但未注册，预留） | ✗ |
| web_fetch | ✓ | ✓ |
| web_search | ✓（Exa） | ✓（Tavily/Google/DashScope） |
| codesearch | ✓（Exa） | ✗ |
| lsp | ✓（实验性，37 种 LSP 服务器） | ✓ |
| agent/task | ✓ | ✓ |
| skill | ✓（原生 Skill + 权限） | ✓ |
| question | ✓ | ✓ (ask_user_question) |
| todo | ✓（仅 todowrite 注册；todoread 定义但未注册） | ✓ (todo_write) |
| plan_enter/exit | plan_exit 有条件注册；plan_enter 定义但未注册 | ✓ |
| save_memory | ✗ | ✓ |
| batch | ✓（实验性） | ✗ |
| invalid | ✓（无效工具标记） | ✗ |

**关键差异**：
- OpenCode 有 `apply_patch`（GPT 优化的 diff 格式）、`codesearch`（Exa 代码搜索）、`batch`（批量执行，实验性）
- Qwen Code 有 `save_memory`（持久记忆到 Markdown）
- OpenCode 的 plan_enter/exit 内置于工具系统；Qwen Code 的 exit_plan_mode 类似
- 两者 Web 搜索后端不同：OpenCode 用 Exa，Qwen Code 支持 Tavily/Google/DashScope 三种后端
- OpenCode LSP 工具支持 37 种语言服务器 + 26 种 Formatter

## 7. 权限系统

### OpenCode

```
规则优先级：远程 → 全局 → 项目 → .opencode → 内联
权限类型：edit, write, read, bash, question, external_directory,
          plan_enter, plan_exit, doom_loop

特色：
- Tree-sitter AST 解析 bash 命令
- 自动提取命令中的目录和操作
- Doom Loop 保护（3 次连续拒绝自动中断）
- 文件时间锁（检测外部修改冲突）
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

**核心差异**：OpenCode 的 Tree-sitter bash 分析更深入（AST 级别），而 Qwen Code 的语义解析更轻量。两者都支持分层配置，但 OpenCode 增加了远程配置（企业级）。

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
// Hook 类型（共 17 种）
event                                    // 事件监听
config                                   // 配置修改
auth                                     // 认证中间件
tool                                     // 工具定义（注册自定义工具）
tool.definition                          // 修改工具描述/参数
tool.execute.before                      // 工具执行前拦截
tool.execute.after                       // 工具执行后处理
chat.message                             // 消息接收处理
chat.params                              // LLM 参数修改（温度等）
chat.headers                             // LLM 请求头修改
permission.ask                           // 权限请求拦截
command.execute.before                   // 命令执行前拦截
shell.env                                // Shell 环境变量注入
experimental.chat.messages.transform     // 消息变换
experimental.chat.system.transform       // 系统提示变换
experimental.session.compacting          // compaction 前上下文注入
experimental.text.complete               // 自定义补全

// 内置插件
CodexAuthPlugin, CopilotAuthPlugin, GitlabAuthPlugin

// 加载方式
npm install opencode-plugin-xxx
// 或 file:///path/to/plugin
```

### Qwen Code 扩展

```typescript
// 扩展类型
MCP 服务器, Skills, Subagents, Hooks

// 安装方式
Git clone / Release 下载

// 兼容性
Qwen Code 原生扩展
Claude 插件转换 (claude-converter.ts)
Gemini 扩展转换 (gemini-converter.ts)

// Hook 事件
PreToolUse, PostToolUse, SessionStart, SessionEnd,
UserPromptSubmit, SubagentStart/Stop, PermissionRequest
```

**关键差异**：OpenCode 有 17 种 hook（可修改 LLM 参数/请求头、拦截权限请求、注入 shell 环境变量、compaction 行为等），且有 Skill 系统（原生 Agent Skill）；Qwen Code 的扩展更面向用户（技能、代理、12 种事件 Hook），且能转换其他工具的扩展格式。

## 11. 国际化

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **UI 语言** | Web/桌面 16 种（TUI 仅英文） | 6 种（中/英/日/德/俄/葡） |
| **自定义语言包** | 不支持 | ✓（~/.qwen/locales/） |
| **模型输出语言** | 跟随系统 | 可独立配置 |
| **语言检测** | 无 | Intl API + 环境变量 |

OpenCode Web/桌面应用支持 16 种语言，但 TUI 仅英文；Qwen Code CLI 原生支持 6 语言。对非英语的纯终端用户，Qwen Code 仍有优势。

## 12. 独特技术特性对比

### 仅 OpenCode 有

| 特性 | 说明 |
|------|------|
| **Tree-sitter Bash 分析** | AST 级别解析 bash 命令，精准权限判断 |
| **多客户端架构** | TUI + Web + Desktop (Tauri + Electron) 共享后端 |
| **Doom Loop 保护** | 3 次连续拒绝自动中断循环 |
| **文件时间锁** | 检测编辑期间文件外部修改 |
| **MDNS 服务发现** | 远程连接支持 |
| **apply_patch 工具** | GPT 模型专用的 diff 格式 |
| **Exa 代码搜索** | 语义级代码搜索 |
| **远程工作区** | Adaptor 模式 + SSE 实时同步（实验性） |
| **Git-backed Session Review** | 基于 git 快照的变更追踪，侧面板 diff 可视化 + 行内注释 |
| **Session Fork & Restore** | 从任意消息分叉会话，或回退到历史消息恢复文件 |
| **Session 分享** | 同步到云端生成公开链接，SSR 渲染 diff |
| **37 种 LSP 服务器** | 覆盖主流及小众语言（含 Typst、Gleam、Julia 等） |
| **26 种 Formatter** | 从 Prettier 到 ormolu (Haskell)、cljfmt (Clojure) |
| **37 种主题** | 含 AMOLED、调色板生成 |
| **Prompt Stashing** | 暂存 prompt |
| **models.dev 动态模型** | 自动拉取最新模型信息和定价 |
| **Effect 框架** | 核心服务逐步迁移到 Effect 类型安全 |
| **Skill 系统** | 原生 Agent Skill + 权限 + per-agent 过滤 |

### 仅 Qwen Code 有

| 特性 | 说明 |
|------|------|
| **免费 OAuth** | 通义账号每天 1000 次免费 |
| **Plan 模式** | 显式规划→审批→执行流程 |
| **多代理终端** | Tmux/iTerm2 分屏显示并行代理 |
| **扩展格式转换** | Claude/Gemini 扩展自动转换 |
| **CLI 6 语言国际化** | 终端 CLI 原生多语言支持（OpenCode TUI 仅英文） |
| **save_memory 工具** | 持久化记忆到 Markdown |
| **Loop 检测** | Levenshtein 距离检测重复调用 |
| **Java SDK** | 企业 Java 集成 |

## 13. 性能与资源

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **启动时间** | 较慢（Hono 服务器 + SQLite + LSP 发现） | 较快（单进程直连） |
| **内存占用** | 较高（HTTP 服务器 + 数据库 + LSP 进程） | 较低（纯 CLI） |
| **安装体积** | 较大（19 包 Monorepo） | 中等（esbuild 打包） |
| **并发能力** | 强（HTTP 多客户端 + 远程工作区） | 弱（单进程） |

## 14. 适用场景总结

| 场景 | 推荐 | 原因 |
|------|------|------|
| **多 LLM 提供商** | OpenCode | 100+ 提供商通过 models.dev 动态接入 |
| **免费使用** | Qwen Code | 每天 1000 次免费 OAuth |
| **中文开发** | Qwen Code | 6 语言 UI + 中文模型优化 |
| **企业部署** | OpenCode | 远程配置 + 多客户端 + 企业包 + MIT 许可 |
| **插件开发** | OpenCode | 更底层的 Hook 系统 + Skill 系统 |
| **扩展迁移** | Qwen Code | Claude/Gemini 扩展格式转换 |
| **多代理协作** | Qwen Code | Tmux/iTerm2 可视化并行 |
| **简单上手** | Qwen Code | 单进程 + 免费额度 |

## 15. 代码质量

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **类型安全** | Zod 4 + Effect Schema + TypeScript strict | TypeScript strict + 部分 Zod |
| **测试** | Bun test + Playwright E2E | Vitest + msw/memfs mock |
| **代码风格** | Prettier (120 字符，无分号) | 标准 TS 风格 |
| **文档** | Storybook + 配置注释 | JSDoc + 部分中文注释 |
| **品牌化 ID** | ProviderID、ModelID、SessionID 等 Effect branded types | 字符串 ID |

---

*分析基于本地源码仓库，截至 2026 年 3 月。两个项目均在快速迭代中，具体实现可能已更新。*
