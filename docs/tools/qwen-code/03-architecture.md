# 3. Qwen Code 技术架构

> 以下基于 v0.13.0 源码分析（commit `0b8ff03f8`，2026-03-26）。

## Monorepo 结构

```
qwen-code/
├── packages/cli/                   # CLI 界面（Ink/React TUI）
│   └── src/
│       ├── gemini.tsx              # 主入口（交互模式）
│       ├── nonInteractiveCli.ts    # 非交互模式入口
│       ├── ui/commands/            # 41 个斜杠命令实现
│       ├── services/               # 命令加载、会话管理
│       ├── config/                 # 设置加载、schema、迁移
│       └── i18n/                   # 6 种语言国际化
├── packages/core/                  # 核心引擎
│   └── src/
│       ├── core/                   # 客户端、调度器、内容生成器
│       │   ├── client.ts           # GeminiClient 主客户端
│       │   ├── geminiChat.ts       # 聊天会话管理
│       │   ├── coreToolScheduler.ts # 工具调度器（1790 行）
│       │   ├── baseLlmClient.ts    # LLM 客户端基类
│       │   └── contentGenerator.ts # AuthType 枚举 + 多后端
│       ├── tools/                  # 16 个内置工具
│       ├── config/                 # 核心配置（config.ts 2200+ 行）
│       ├── hooks/                  # Hook 系统（15 个文件）
│       ├── skills/                 # Skill 系统
│       ├── subagents/              # 子代理系统
│       ├── agents/                 # Agent 运行时 + Arena
│       ├── extension/              # 扩展管理器 + 转换器
│       ├── permissions/            # 权限系统
│       ├── qwen/                   # Qwen 专用（OAuth、内容生成器）
│       ├── mcp/                    # MCP 客户端 + OAuth
│       ├── telemetry/              # 遥测（OpenTelemetry + RUM）
│       └── services/               # 会话、压缩、循环检测等
├── packages/webui/                 # Web UI 组件
├── packages/sdk-typescript/        # TypeScript SDK
├── packages/sdk-java/              # Java SDK
├── packages/vscode-ide-companion/  # VS Code 扩展
├── packages/zed-extension/         # Zed 编辑器扩展
├── packages/web-templates/         # Web 模板
└── packages/test-utils/            # 测试工具
```

## 核心架构

```
CLI (Ink/React TUI)
    │
    ▼
GeminiClient (packages/core/src/core/client.ts)
    │  管理聊天历史、发送消息
    ▼
GeminiChat (packages/core/src/core/geminiChat.ts)
    │  LLM 聊天会话
    ▼
ContentGenerator（多后端抽象）
    ├── GeminiContentGenerator       # Google Gemini API
    ├── OpenAIContentGenerator       # OpenAI 兼容 API
    ├── QwenContentGenerator         # Qwen 专用（扩展 OpenAI）
    └── AnthropicContentGenerator    # Anthropic Claude API
    │
    ▼
CoreToolScheduler (packages/core/src/core/coreToolScheduler.ts)
    │  工具调度、确认、执行、结果处理（1790 行）
    ▼
PermissionManager (packages/core/src/permissions/)
    │  deny > ask > allow > default 优先级
    ▼
ToolRegistry → Tool 执行 → 文件系统/Shell
```

## Agent Loop（工具执行循环）

源码: `packages/core/src/core/coreToolScheduler.ts`

```
用户输入 → LLM 生成响应（含工具调用）
  → 参数校验 (validating)
  → 权限检查 (getDefaultPermission)
  → Hook 触发 (PreToolUse)
  → 用户确认 (awaiting_approval)
  → 工具执行 (executing)
  → Hook 触发 (PostToolUse)
  → 结果返回 LLM
  → 重复直到 LLM 不再生成工具调用
```

## 内容生成器（LLM 后端）

| 后端 | 类 | 源码 |
|------|------|------|
| OpenAI 兼容 | `OpenAIContentGenerator` | `core/openaiContentGenerator/openaiContentGenerator.ts` |
| Qwen（扩展 OpenAI） | `QwenContentGenerator` | `qwen/qwenContentGenerator.ts` |
| Google Gemini | `GeminiContentGenerator` | `core/geminiContentGenerator/geminiContentGenerator.ts` |
| Anthropic | `AnthropicContentGenerator` | `core/anthropicContentGenerator/anthropicContentGenerator.ts` |

认证类型枚举（源码: `packages/core/src/core/contentGenerator.ts`）：
- `openai` — OpenAI 兼容 API（API Key）
- `qwen-oauth` — Qwen OAuth2 + PKCE（设备码流程）
- `gemini` — Google Gemini
- `vertex-ai` — Google Vertex AI
- `anthropic` — Anthropic Claude

## Arena 多模型竞争模式

源码: `packages/core/src/agents/arena/`

| 组件 | 文件 | 用途 |
|------|------|------|
| ArenaManager | `ArenaManager.ts`（1649 行） | 编排多模型竞争执行 |
| ArenaAgentClient | `ArenaAgentClient.ts` | 单个 Arena 代理客户端 |
| 类型定义 | `types.ts` | ArenaConfig, ArenaAgentState |
| 事件 | `arena-events.ts` | SESSION_START, AGENT_START, AGENT_COMPLETE 等 |

**工作流程：**
1. 用户通过 `/arena start --models model1,model2 "task"` 启动
2. ArenaManager 为每个模型创建独立 Git worktree
3. 每个模型在并行子进程中运行（`AgentHeadless` 非交互运行时）
4. 用户通过 `/arena select` 选择最佳结果，合并 diff

**后端**（源码: `packages/core/src/agents/backends/`）：
- `TmuxBackend` — tmux 面板运行
- `InProcessBackend` — 进程内运行（SDK 模式）
- `ITermBackend` — iTerm2 集成
- 后端自动检测: `backends/detect.ts`

## MCP 集成

源码: `packages/core/src/tools/`

| 组件 | 文件 | 用途 |
|------|------|------|
| McpClientManager | `mcp-client-manager.ts` | 管理所有 MCP 连接 |
| McpClient | `mcp-client.ts`（1451 行） | 单个 MCP 客户端 |
| DiscoveredMCPTool | `mcp-tool.ts` | MCP 工具包装 |
| MCP OAuth | `../mcp/oauth-provider.ts`（960 行） | OAuth2/OIDC + PKCE |
| MCP Token 存储 | `../mcp/oauth-token-storage.ts` | 持久化令牌 |

**传输协议：** Stdio、SSE、Streamable-HTTP、SDK Control（IDE 集成）

## 扩展系统

源码: `packages/core/src/extension/`

| 组件 | 文件 | 用途 |
|------|------|------|
| ExtensionManager | `extensionManager.ts`（1392 行） | 安装/加载/管理扩展 |
| Claude 转换器 | `claude-converter.ts`（824 行） | Claude Code 插件 → Qwen 格式 |
| Gemini 转换器 | `gemini-converter.ts` | Gemini CLI 扩展 → Qwen 格式 |
| Marketplace | `marketplace.ts` | GitHub 仓库安装 |

**扩展能力：** MCP 服务器、Hooks、命令、Skills、子代理、输出样式、LSP 服务器

## Hook 系统

源码: `packages/core/src/hooks/`（15 个文件）

**事件类型（14 种）：**

| 事件 | 触发时机 |
|------|---------|
| PreToolUse | 工具执行前 |
| PostToolUse | 工具执行后 |
| PostToolUseFailure | 工具执行失败后 |
| Notification | 通知 |
| UserPromptSubmit | 用户提交输入 |
| SessionStart | 会话开始 |
| SessionEnd | 会话结束 |
| Stop | 代理停止 |
| SubagentStart | 子代理启动 |
| SubagentStop | 子代理停止 |
| PreCompact | 上下文压缩前 |
| PermissionRequest | 权限请求 |

**Hook 类型：** 命令式（执行 Shell 命令）

## Skill 系统

源码: `packages/core/src/skills/`

| 组件 | 文件 | 用途 |
|------|------|------|
| SkillManager | `skill-manager.ts` | 管理技能生命周期 |
| Skill Loader | `skill-load.ts` | 从磁盘加载 |
| Types | `types.ts` | SkillConfig, SkillLevel |

**四级技能：** `bundled` > `project`（`.qwen/skills/`）> `user`（`~/.qwen/skills/`）> `extension`

**技能格式：** `SKILL.md`（YAML frontmatter + Markdown 正文），通过 `skill` 工具注入 LLM 上下文。

## 子代理系统

源码: `packages/core/src/subagents/` + `packages/core/src/agents/`

| 组件 | 文件 | 用途 |
|------|------|------|
| SubagentManager | `subagents/subagent-manager.ts` | 管理子代理配置 |
| BuiltinAgentRegistry | `subagents/builtin-agents.ts` | 内置代理注册 |
| AgentHeadless | `agents/runtime/agent-headless.ts` | 无头运行时 |
| AgentInteractive | `agents/runtime/agent-interactive.ts` | 交互运行时 |
| AgentCore | `agents/runtime/agent-core.ts` | 核心代理逻辑 |

**内置代理：**
- `general-purpose` — 研究、搜索、多步骤任务
- `Explore` — 快速代码库探索（只读）

**代理级别：** `session` > `project` > `user` > `extension` > `builtin`

## 会话管理

| 服务 | 文件 | 用途 |
|------|------|------|
| SessionService | `services/sessionService.ts` | JSONL 格式会话持久化 |
| ChatCompressionService | `services/chatCompressionService.ts` | 上下文压缩 |
| LoopDetectionService | `services/loopDetectionService.ts` | 重复循环检测 |
| ChatRecordingService | `services/chatRecordingService.ts` | 聊天记录 |
| GitWorktreeService | `services/gitWorktreeService.ts` | Arena 的 Git worktree |

## 配置系统

**存储路径（源码: `packages/core/src/config/storage.ts`）：**

| 路径 | 用途 |
|------|------|
| `~/.qwen/settings.json` | 全局设置 |
| `<project>/.qwen/settings.json` | 项目设置 |
| `~/.qwen/memory.md` | 全局记忆 |
| `~/.qwen/commands/*.md` | 全局自定义命令 |
| `~/.qwen/agents/` | 全局子代理 |
| `~/.qwen/skills/` | 全局技能 |
| `<project>/.qwen/skills/` | 项目技能 |
| `<project>/.qwen/agents/` | 项目代理 |
| `QWEN.md` / `AGENTS.md` | 项目上下文文件 |
| `~/.qwen/oauth_creds.json` | OAuth 凭据 |
| `~/.qwen/oauth_creds.lock` | 跨进程令牌锁 |

**设置 Schema：** `packages/cli/src/config/settingsSchema.ts` + 版本化迁移（`migration/`）

**配置优先级：** managed > user > project > environment variables

## 认证系统

### Qwen OAuth2（源码: `packages/core/src/qwen/qwenOAuth2.ts`，1018 行）

- 设备码流程 + PKCE（RFC 7636）
- 端点: `https://chat.qwen.ai/api/v1/oauth2/device/code`
- Client ID: `f0304373b74a44d2b584a3fb70ca9e56`
- 共享令牌管理器: `sharedTokenManager.ts`
- 凭据存储: `~/.qwen/oauth_creds.json`

### MCP OAuth（源码: `packages/core/src/mcp/oauth-provider.ts`，960 行）

- 完整 OAuth2 授权码流程 + PKCE
- 动态客户端注册
- 令牌存储: `~/.qwen/mcp-oauth-tokens.json`

## 权限系统

源码: `packages/core/src/permissions/`

- 权限级别: `allow` / `ask` / `deny`
- Shell 命令语义分析（`extractShellOperations`）
- 路径/命令模式匹配
- 审批模式: `default` / `plan` / `auto_edit` / `yolo`

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | TypeScript 5.3+（严格模式） |
| 运行时 | Node.js 20+ |
| CLI 框架 | Ink 6.2 + React 19 |
| 构建 | esbuild |
| 模型 SDK | Google Genai SDK + OpenAI SDK + Anthropic SDK |
| MCP SDK | @modelcontextprotocol/sdk v1.25 |
| 数据库 | JSONL（会话存储） |
| 测试 | Vitest |
