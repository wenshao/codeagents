# OpenCode vs Qwen Code：源码级深度对比

> 基于本地源码仓库的深入分析，揭示两个开源 CLI 编程代理的架构设计差异

## 项目概览

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **开发者** | SST / OpenCode AI | 阿里云 |
| **许可证** | MIT | Apache-2.0 |
| **语言** | TypeScript 5.8 | TypeScript 5.3+ |
| **运行时** | Bun 1.3（主）/ Node.js 22 | Node.js 20+ |
| **上游项目** | 原创 | Google Gemini CLI 分叉 |
| **核心定位** | 多客户端 AI 开发平台 | 终端编程代理 |

## 1. 项目结构

### OpenCode Monorepo

```
opencode/
├── packages/opencode/    # 核心 CLI + 代理后端（主包）
├── packages/console/     # Web 控制台（SolidJS Start）
├── packages/sdk/js/      # JavaScript SDK
├── packages/ui/          # 共享 UI 组件
├── packages/plugin/      # 插件系统
├── packages/desktop/     # Tauri 桌面应用
└── packages/script/      # 构建脚本
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
- OpenCode 将核心逻辑和 CLI 合并在 `packages/opencode` 中；Qwen Code 将 CLI（`packages/cli`）和核心（`packages/core`）严格分离
- OpenCode 有 Tauri 桌面应用；Qwen Code 有 VS Code 和 Zed 编辑器扩展
- Qwen Code 提供 Java SDK（面向企业集成）；OpenCode 只有 JS SDK

## 2. 核心架构

### OpenCode：客户端/服务器架构

```
客户端层 (TUI / Web / Desktop)
    │
    ▼
Hono HTTP 服务器 (localhost:4096) + WebSocket
    │
    ▼
代理系统 (Vercel AI SDK)
    │
    ▼
工具注册表 → 文件系统/Shell
    │
    ▼
SQLite (Drizzle ORM)
```

- 通过 HTTP + WebSocket 解耦客户端和服务器
- 支持 MDNS 服务发现，可远程连接
- 所有客户端共享同一个后端进程

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
| **状态管理** | 实例级 State + Event Bus | React Context |
| **渲染** | OpenTUI 自定义终端渲染 | Ink 适配 Yoga 布局 |
| **主题** | 背景色检测（亮/暗） | 主题系统 |

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
| XAI | ✓ | ✗ |
| DeepInfra | ✓ | ✗ |
| Qwen/DashScope | ✗ | ✓ |
| ModelScope | ✗ | ✓ |
| GitHub Copilot | ✓（插件） | ✗ |
| GitLab | ✓（插件） | ✗ |
| 免费 OAuth | ✗ | ✓（通义账号） |

### SDK 策略

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **统一 SDK** | Vercel AI SDK v5 | 无（各自 SDK） |
| **抽象层** | 单一 `streamText()` API | ContentGenerator 接口 |
| **提供商适配** | `transform.ts` 统一处理 | 各 Generator 独立实现 |
| **模型信息** | models.dev 自动拉取 | 硬编码 `constants.ts` |

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

### OpenCode 多代理

| 代理 | 权限 | 用途 |
|------|------|------|
| build | 完全访问 | 代码开发 |
| plan | 只读 | 分析规划 |
| general | 受限（子代理） | 多步骤研究 |
| explore | 只读（子代理） | 快速搜索 |
| compaction | 内部 | 会话压缩 |
| title/summary | 内部 | 标题生成 |

- 用户可通过 `opencode.json` 定义自定义代理
- `@general`、`@explore` 通过消息 @ 引用调用
- 每个代理有独立的模型、温度、系统提示配置

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
| **输出截断** | 32K tokens 默认 | 可配置 |
| **注册** | `registry.ts` 动态加载 | `tool-registry.ts` 集中管理 |
| **外部工具** | 配置目录 `tools/*.ts` | MCP + 扩展 |

### 内置工具对比

| 工具 | OpenCode | Qwen Code |
|------|----------|-----------|
| edit | ✓ | ✓ |
| write | ✓ | ✓ (write_file) |
| read | ✓ | ✓ (read_file) |
| bash | ✓ | ✓ (run_shell_command) |
| grep | ✓ | ✓ (grep_search) |
| glob | ✓ | ✓ |
| ls | ✓ | ✓ (list_directory) |
| apply_patch | ✓（GPT 专用） | ✗ |
| web_fetch | ✓ | ✓ |
| web_search | ✓（Exa） | ✓（Tavily） |
| codesearch | ✓（Exa） | ✗ |
| lsp | ✓ | ✓ |
| agent/task | ✓ | ✓ |
| skill | ✓ | ✓ |
| question | ✓ | ✓ (ask_user_question) |
| todo | ✓ | ✓ (todo_write) |
| save_memory | ✗ | ✓ |
| exit_plan_mode | ✗ | ✓ |
| batch | ✓（实验性） | ✗ |

**关键差异**：
- OpenCode 有 `apply_patch`（为 GPT 模型优化的差异格式）和 `codesearch`（Exa 代码搜索）
- Qwen Code 有 `save_memory`（持久记忆）和 `exit_plan_mode`（规划模式退出）
- 两者 Web 搜索后端不同：OpenCode 用 Exa，Qwen Code 用 Tavily

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
// Hook 类型
auth        // 认证中间件
event       // 事件监听
tool        // 工具定义
chat.*      // 聊天参数/头/系统提示转换

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

**关键差异**：OpenCode 的插件更底层（可修改聊天参数、认证流程）；Qwen Code 的扩展更面向用户（技能、代理、Hook），且能转换其他工具的扩展格式。

## 11. 国际化

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **UI 语言** | 仅英文 | 6 种（中/英/日/德/俄/葡） |
| **自定义语言包** | 不支持 | ✓（~/.qwen/locales/） |
| **模型输出语言** | 跟随系统 | 可独立配置 |
| **语言检测** | 无 | Intl API + 环境变量 |

这是 Qwen Code 的显著优势，特别对非英语开发者。

## 12. 独特技术特性对比

### 仅 OpenCode 有

| 特性 | 说明 |
|------|------|
| **Tree-sitter Bash 分析** | AST 级别解析 bash 命令，精准权限判断 |
| **多客户端架构** | TUI + Web + Desktop 共享后端 |
| **Doom Loop 保护** | 3 次连续拒绝自动中断循环 |
| **文件时间锁** | 检测编辑期间文件外部修改 |
| **MDNS 服务发现** | 远程连接支持 |
| **apply_patch 工具** | GPT 模型专用的 diff 格式 |
| **Exa 代码搜索** | 语义级代码搜索 |

### 仅 Qwen Code 有

| 特性 | 说明 |
|------|------|
| **免费 OAuth** | 通义账号每天 1000 次免费 |
| **Plan 模式** | 显式规划→审批→执行流程 |
| **多代理终端** | Tmux/iTerm2 分屏显示并行代理 |
| **扩展格式转换** | Claude/Gemini 扩展自动转换 |
| **6 语言国际化** | 完整 UI 多语言支持 |
| **save_memory 工具** | 持久化记忆到 Markdown |
| **Loop 检测** | Levenshtein 距离检测重复调用 |
| **Java SDK** | 企业 Java 集成 |

## 13. 性能与资源

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **启动时间** | 较慢（Hono 服务器 + SQLite 初始化） | 较快（单进程直连） |
| **内存占用** | 较高（HTTP 服务器 + 数据库连接） | 较低（纯 CLI） |
| **安装体积** | 较大（Monorepo 依赖链） | 中等（esbuild 打包） |
| **并发能力** | 强（HTTP 多客户端） | 弱（单进程） |

## 14. 适用场景总结

| 场景 | 推荐 | 原因 |
|------|------|------|
| **多 LLM 提供商** | OpenCode | 20+ 提供商统一接入 |
| **免费使用** | Qwen Code | 每天 1000 次免费 OAuth |
| **中文开发** | Qwen Code | 6 语言 UI + 中文模型优化 |
| **企业部署** | OpenCode | 远程配置 + 多客户端 + MIT 许可 |
| **插件开发** | OpenCode | 更底层的 Hook 系统 |
| **扩展迁移** | Qwen Code | Claude/Gemini 扩展格式转换 |
| **多代理协作** | Qwen Code | Tmux/iTerm2 可视化并行 |
| **简单上手** | Qwen Code | 单进程 + 免费额度 |

## 15. 代码质量

| 维度 | OpenCode | Qwen Code |
|------|----------|-----------|
| **类型安全** | Zod 4 + TypeScript strict | TypeScript strict + 部分 Zod |
| **测试** | Bun test + Playwright E2E | Vitest + msw/memfs mock |
| **代码风格** | Prettier (120 字符，无分号) | 标准 TS 风格 |
| **文档** | 配置注释为主 | JSDoc + 部分中文注释 |

---

*分析基于本地源码仓库，截至 2026 年 3 月。两个项目均在快速迭代中，具体实现可能已更新。*
