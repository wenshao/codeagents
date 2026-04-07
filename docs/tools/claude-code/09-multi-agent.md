# 9. 多 Agent 系统——开发者参考

> Leader-Worker 协作、Swarm 三后端（InProcess/tmux/iTerm2）、文件邮箱 IPC、任务管理、Kairos 自治模式。Code Agent 多 Agent 编排的最复杂实现（~20,500 行）。
>
> **Qwen Code 对标**：Agent Team（PR#2886）、Fork Subagent（PR#2936）正在实现类似能力。本文的 InProcess 隔离（AsyncLocalStorage）、邮箱通信、任务拓扑管理是核心参考。
>
> **计数规则**：源码行数基于 TypeScript 文件的 `wc -l` 统计。

## 9.1 架构总览

### 9.1.1 子系统全景

| 子系统 | 目录总规模 | 核心文件（单文件 LOC） | 职责 |
|--------|-----------|----------------------|------|
| **Swarm 核心** | 7,548 LOC | `utils/swarm/inProcessRunner.ts` (1,552) | 进程内 teammate 执行引擎 |
| **Swarm 后端** | (含在 Swarm 核心) | `utils/swarm/backends/TmuxBackend.ts` (764) | tmux 分屏管理 |
| **Swarm 权限** | (含在 Swarm 核心) | `utils/swarm/permissionSync.ts` (928) | 文件级权限委托 |
| **Swarm 团队** | (含在 Swarm 核心) | `utils/swarm/teamHelpers.ts` (683) | 团队文件管理 |
| **Agent 工具** | 6,782 LOC | `tools/AgentTool/AgentTool.tsx` (1,397) | Agent 入口（3 种执行路径） |
| **Agent 执行** | (含在 Agent 工具) | `tools/AgentTool/runAgent.ts` (973) | 子代理执行引擎 |
| **Agent UI** | (含在 Agent 工具) | `tools/AgentTool/UI.tsx` (871) | React 进度/状态渲染 |
| **Agent 定义** | (含在 Agent 工具) | `tools/AgentTool/loadAgentsDir.ts` (755) | Agent 定义加载 |
| **邮箱通信** | 1,183 LOC | `utils/teammateMailbox.ts` (1,183) | 文件邮箱消息总线 |
| **任务管理** | 862 LOC | `utils/tasks.ts` (862) | 文件级任务列表、原子认领 |
| **发送消息** | 997 LOC | `tools/SendMessageTool/SendMessageTool.ts` (917) + prompt (49) + UI (30) + constants (1) | 跨代理消息路由 |
| **远程传送** | 2,020 LOC | `utils/teleport.tsx` (1,225) + UI 5 组件 (795) | 本地↔远程会话迁移 |
| **协调模式** | 369 LOC | `coordinator/coordinatorMode.ts` (369) | 纯协调者系统提示 |
| **团队生成** | 1,093 LOC | `tools/shared/spawnMultiAgent.ts` (1,093) | 3 后端 teammate 生成 |
| **代理 ID** | 99 LOC | `utils/agentId.ts` (99) | 确定性代理 ID 格式 |

### 9.1.2 Leader-Worker 模型

```
                    ┌────────────────────────────────────────────┐
                    │           Leader（team-lead）               │
                    │                                            │
                    │  Agent Tool ──▶ spawnTeammate()           │
                    │  SendMessage ──▶ mailbox 广播              │
                    │  TaskCreate/Update ──▶ 任务分配            │
                    │  Coordinator Mode（可选纯协调者）           │
                    └──────┬──────────┬──────────┬──────────────┘
                           │          │          │
                    ┌──────▼──┐ ┌─────▼───┐ ┌───▼──────┐
                    │ Worker 1 │ │ Worker 2 │ │ Worker N  │
                    │         │ │         │ │          │
                    │ Mailbox │ │ Mailbox │ │ Mailbox  │
                    │ Tasks   │ │ Tasks   │ │ Tasks    │
                    │ Worktree│ │ Worktree│ │ (共享)    │
                    └─────────┘ └─────────┘ └──────────┘
```

**三种后端**：

| 后端 | 适用环境 | 隔离级别 | 通信方式 |
|------|---------|---------|---------|
| **In-process** | 无终端分屏或 teammate-mode 配置 | `AsyncLocalStorage` 上下文隔离 | 内存 + 邮箱文件 |
| **Split-pane** | tmux / iTerm2 | 进程隔离（不同终端面板） | 邮箱文件 |
| **Separate-window** | tmux | 进程隔离（不同 tmux 窗口） | 邮箱文件 |

### 9.1.3 多代理生命周期

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  团队创建      │     │  Worker 生成  │     │  任务执行      │     │  清理/解散    │
│              │     │              │     │              │     │              │
│ TeamCreate   │────▶│ Agent Tool   │────▶│ 并行执行      │────▶│ TeamDelete   │
│ config.json  │     │ 3后端自动检测  │     │ Mailbox 通信  │     │ Worktree 清理│
│ 任务目录初始化 │     │ Worktree 分配 │     │ Task 认领/完成 │     │ PID 清理      │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

## 9.2 Agent 定义系统

### 9.2.1 AgentDefinition 类型层次

源码：`tools/AgentTool/loadAgentsDir.ts` (755 LOC)

```typescript
type AgentDefinition =
  | BuiltInAgentDefinition
  | CustomAgentDefinition
  | PluginAgentDefinition

interface BaseAgentDefinition {
  agentType: string
  whenToUse: string
  tools?: string[]
  disallowedTools?: string[]
  model?: 'sonnet' | 'opus' | 'haiku' | 'inherit'
  effort?: string
  permissionMode?: string
  maxTurns?: number
  mcpServers?: Record<string, MCPServerConfig>
  hooks?: Record<string, HookConfig[]>
  skills?: SkillDefinition[]
  color?: string
  isolation?: 'worktree' | 'remote'
  memory?: { scope: 'user' | 'project' | 'local' }
}

interface BuiltInAgentDefinition extends BaseAgentDefinition {
  getSystemPrompt(): string
}

interface CustomAgentDefinition extends BaseAgentDefinition {
  source: SettingSource
  getSystemPrompt(): string
}

interface PluginAgentDefinition extends BaseAgentDefinition {
  source: 'plugin'
  pluginMetadata: PluginMeta
}
```

### 9.2.2 内置 Agent

源码：`tools/AgentTool/builtInAgents.ts` (72 LOC)

| Agent | 类型 | 工具集 | 模型 | 启用条件 |
|-------|------|--------|------|---------|
| **general-purpose** | 通用 | 全部 | 默认 | 始终启用 |
| **statusline-setup** | 配置 | Read, Edit | Sonnet | 始终启用 |
| **explore** | 搜索 | Glob/Grep/Read/Bash（只读） | Haiku（外部）/ Inherit（内部） | `BUILTIN_EXPLORE_PLAN_AGENTS` 编译标志 + `tengu_amber_stoat` GrowthBook（默认开） |
| **plan** | 规划 | 同 explore | Inherit | 同 explore |
| **claude-code-guide** | 指南 | Read/WebFetch/WebSearch + Glob/Grep（Ant-native 变体用 Bash 替代 Glob/Grep） | Haiku | 非 SDK 入口点（排除 sdk-ts/sdk-py/sdk-cli） |
| **verification** | 验证 | 全部（禁止编辑/写入） | Inherit | `VERIFICATION_AGENT` 编译标志 + `tengu_hive_evidence` GrowthBook（默认关） |

**Coordinator agents**：当 `COORDINATOR_MODE` 启用时，`getBuiltInAgents()` 替换为 `getCoordinatorAgents()`（动态 `require('../../coordinator/workerAgent.js')`，源码中仅有编译产物路径，`.ts` 源文件未包含在泄露仓库中），上述 6 个 Agent 均不加载。

**SDK 覆盖**：`CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS=1` 可在非交互模式下禁用所有内置 Agent。

**Feature flag 类型**：

| Flag | 类型 | 默认值 | 影响范围 |
|------|------|--------|---------|
| `BUILTIN_EXPLORE_PLAN_AGENTS` | 编译时 (`bun:bundle`) | 视构建 | explore / plan |
| `VERIFICATION_AGENT` | 编译时 (`bun:bundle`) | 视构建 | verification |
| `COORDINATOR_MODE` | 编译时 (`bun:bundle`) | 视构建 | coordinator 全套 |
| `tengu_amber_stoat` | 运行时 (GrowthBook) | `true` | explore / plan |
| `tengu_hive_evidence` | 运行时 (GrowthBook) | `false` | verification |

### 9.2.3 自定义 Agent 加载

源码：`tools/AgentTool/loadAgentsDir.ts` (755 LOC) + `utils/markdownConfigLoader.ts`

Agent 定义从 4 个文件系统位置加载 `.md` 文件，外加 1 个 CLI 注入路径（优先级从低到高）：

| 来源 | 路径 | SettingSource | 说明 |
|------|------|---------------|------|
| **内置** | `builtInAgents.ts` | `builtIn` | 硬编码，最低优先级 |
| **插件** | 插件目录 | `plugin` | 第三方扩展 |
| **用户** | `~/.claude/agents/*.md` | `userSettings` | 私人全局 |
| **项目** | `.claude/agents/*.md` | `projectSettings` | 团队共享（提交到 Git） |
| **CLI 注入** | `--agents` 参数（JSON） | `flagSettings` | 程序化注入 |
| **Policy** | 管理员配置目录 | `policySettings` | 企业策略强制（最高优先级） |

**文件加载机制**：`loadMarkdownFilesForSubdir('agents', cwd)` 扫描上述目录中的 `.md` 文件。同 `agentType` 名称的高优先级条目覆盖低优先级（`Map.set()`）。

**CLI 注入路径**：`parseAgentsFromJson()` 解析 JSON 格式的 Agent 定义（`--agents` 参数），字段与 frontmatter 镜像。

每个 `.md` 文件使用 frontmatter 格式定义 Agent：

```markdown
---
name: my-custom-agent
description: When you need to perform custom analysis
tools: [Glob, Grep, Read, Bash]
model: sonnet
maxTurns: 10
memory: project
---

You are a custom analysis agent. Focus on...
```

**必需字段**：`name`（成为 `agentType`）、`description`（成为 `whenToUse`）。frontmatter 之后的正文内容成为系统提示。缺少 `name` 字段的文件会被静默跳过（视为参考文档）。

**可选字段**：`tools`、`disallowedTools`、`model`、`effort`、`permissionMode`、`maxTurns`、`color`、`background`、`memory`、`isolation`、`mcpServers`、`hooks`、`skills`、`initialPrompt`。

## 9.3 Agent 工具（3 种执行路径）

### 9.3.1 输入参数

源码：`tools/AgentTool/AgentTool.tsx` (1,397 LOC)

```typescript
interface AgentToolInput {
  description: string       // 必填，3-5 词任务摘要
  prompt: string            // 必填，完整任务描述
  subagent_type?: string    // Agent 定义名（省略 = fork 路径）
  model?: 'sonnet' | 'opus' | 'haiku'  // 模型覆盖
  run_in_background?: boolean  // 异步启动
  name?: string             // teammate 名（+ team_name = swarm 路径）
  team_name?: string        // 团队名
  mode?: string             // 权限模式
  isolation?: 'worktree' | 'remote'  // 隔离方式
  cwd?: string              // 工作目录覆盖
}
```

### 9.3.2 三路径路由

```typescript
// AgentTool.call() 核心路由逻辑（伪代码）
if (input.name && input.team_name) {
  // 路径 1: Swarm/Teammate 生成
  return spawnTeammate(config, context)
} else if (!input.subagent_type && isForkSubagentEnabled()) {
  // 路径 2: Fork 子代理（selectedAgent = FORK_AGENT, 调用 runAgent()）
  return runAgent(forkContext)
} else {
  // 路径 3: 标准子代理（查找 effectiveType, 调用 runAgent()）
  return runAgent(standardContext)
}
```

### 9.3.3 路径对比

| 特性 | Swarm/Teammate | Fork 子代理 | 标准子代理 |
|------|---------------|------------|-----------|
| **触发条件** | `name` + `team_name` | `subagent_type` 省略 + feature gate | 显式 `subagent_type` |
| **上下文** | 完全独立会话 | 继承父级对话（cache-identical 前缀） | 新建独立会话 |
| **执行** | 异步，后台运行 | 异步，后台运行 | 同步或异步 |
| **通信** | Mailbox + SendMessage | 无（一次性） | 无（一次性） |
| **生命周期** | 持久（可多次交互） | 一次性 | 一次性 |
| **隔离** | 可选 worktree/remote | 无 | 无 |
| **输出** | `teammate_spawned` | `async_launched` | `completed` / `async_launched` |

### 9.3.4 Fork 子代理

源码：`tools/AgentTool/forkSubagent.ts` (210 LOC)

Fork 子代理通过 `buildForkedMessages()` 构建 **prompt cache 完全相同**的消息前缀：

```typescript
const FORK_AGENT: BuiltInAgentDefinition = {
  agentType: 'fork',
  // 严格规则：
  // - 无元评论（"I'm a sub-agent"）
  // - 保持在指定范围内
  // - 500 词以内回复
}
```

**关键设计**：fork 复用父级 API 消息前缀，使 prompt cache 命中率最大化，降低 token 成本。

### 9.3.5 Agent Memory

源码：`tools/AgentTool/agentMemory.ts` (177 LOC) + `agentMemorySnapshot.ts` (197 LOC)

子代理可通过 `memory` 字段声明持久化记忆，实现跨会话知识积累。Agent Memory 独立于 07-session.md 描述的全局 Memory 系统，是每个 Agent 定义的**局部私有记忆**。

**作用域**：

| Scope | 存储路径 | 跨项目 | VCS |
|-------|---------|--------|-----|
| `user` | `~/.claude/agent-memory/{agentType}/` | ✅ | ❌ |
| `project` | `{cwd}/.claude/agent-memory/{agentType}/` | ❌ | ✅（提交到 Git） |
| `local` | `{cwd}/.claude/agent-memory-local/{agentType}/` | ❌ | ❌ |

**定义方式**：在 Agent 定义的 frontmatter 中声明：

```markdown
---
agentType: security-reviewer
memory: project
---

You are a security review agent. Remember vulnerability patterns...
```

**Prompt 注入**：`loadAgentMemoryPrompt()` 在 Agent 系统提示中注入记忆指令：
- **user scope**：保持通用性建议，因跨项目共享
- **project scope**：鼓励项目特定知识记录，通过 Git 与团队共享
- **local scope**：记录机器特定配置，不进入 VCS

记忆文件为 `MEMORY.md`，存放在对应 scope 目录下。Agent 在每次会话中可读写此文件以积累经验。

**Snapshot 系统**：

源码：`tools/AgentTool/agentMemorySnapshot.ts` (197 LOC)

项目维护者可通过 `.claude/agent-memory-snapshots/{agentType}/` 提供种子记忆：

| 动作 | 触发条件 | 行为 |
|------|---------|------|
| `initialize` | 本地无记忆文件 | 从 snapshot 复制 `.md` 文件 |
| `prompt-update` | snapshot 更新时间 > 已同步时间 | 设置 `pendingSnapshotUpdate` 标志 |
| `none` | 已同步或无 snapshot | 无操作 |

**Feature gate**：`feature('AGENT_MEMORY_SNAPSHOT') && isAutoMemoryEnabled()`

**集成点**：
- 权限系统（`utils/permissions/filesystem.ts`）：`isAgentMemoryPath()` 放行 Agent 记忆路径
- 记忆检测（`utils/memoryFileDetection.ts`）：分类 Agent 记忆文件用于折叠/徽章显示
- 附件系统（`utils/attachments.ts`）：`@agent-` 提及时搜索对应 Agent 记忆目录
- 工具注入：`isAutoMemoryEnabled()` 时自动将文件读/写/编辑工具加入 Agent 的 allowed tools

## 9.4 Swarm 架构

### 9.4.1 生成引擎

源码：`tools/shared/spawnMultiAgent.ts` (1,093 LOC)

**`spawnTeammate()` 核心流程**：

```
spawnTeammate(config, context)
  ├── 1. 生成确定性 agentId: agentName@teamName
  ├── 2. 解析模型: inherit → leader模型, undefined → 默认
  ├── 3. 去重名称: 已存在时追加 -2, -3 后缀
  ├── 4. 后端选择:
  │   ├── In-process (AsyncLocalStorage) ─── teammate-mode 或无后端可用
  │   ├── Split-pane (tmux 30/70 分屏) ─── tmux 或 iTerm2 可用
  │   └── Separate-window (独立 tmux 窗口) ─── 旧模式
  ├── 5. 生成 Worktree（如果 isolation: 'worktree'）
  ├── 6. 分配颜色（round-robin from AGENT_COLORS）
  ├── 7. 注册到 TeamFile config.json
  ├── 8. 传播 CLI 标志（model, settings, permissions）
  └── 9. 发送初始 prompt 到 Mailbox
```

**模型解析链**：`resolveTeammateModel(inputModel, leaderModel)`
- `'inherit'` → 使用 leader 的模型（`leaderModel ?? getDefaultTeammateModel()`）
- `undefined` → `getDefaultTeammateModel(leaderModel)`（provider-aware 默认值，考虑 leader 模型）
- 显式指定 → 使用指定模型

**CLI 标志传播**：`buildInheritedCliFlags()` 将 `--dangerously-skip-permissions`、`--permission-mode`、`--model`、`--settings`、`--plugin-dir`、`--chrome`/`--no-chrome`、`--teammate-mode` 从 leader 传播到 teammate。

### 9.4.2 后端注册与检测

源码：`utils/swarm/backends/registry.ts` (464 LOC)

**后端检测优先级**：

```
detectAndGetBackend():  // Pane 后端检测（tmux/iTerm2）
  ├── isInsideTmux() → tmux 内嵌套 → TmuxBackend
  ├── isInITerm2() && isIt2CliAvailable() → iTerm2 原生 → ITermBackend
  ├── isTmuxAvailable() → 外部 tmux → TmuxBackend
  └── 无可用后端 → throw Error（安装指引）

isInProcessEnabled():  // In-process 独立判断
  ├── teammate-mode 配置 → in-process
  ├── CLAUDE_CODE_TEAMMATE_COMMAND 环境变量 → in-process
  └── detectAndGetBackend() 抛出异常时 → in-process fallback
```

### 9.4.3 Tmux 后端

源码：`utils/swarm/backends/TmuxBackend.ts` (764 LOC)

**布局策略**：Leader 占左侧 30%，teammates 占右侧 70%。每个 teammate 在右侧区域内分割。

| 操作 | tmux 命令 |
|------|----------|
| 创建面板 | `split-window`（水平/垂直） |
| 隐藏面板 | `break-pane` → `join-pane`（移到隐藏窗口） |
| 显示面板 | `join-pane` 回主窗口 |
| 着色边框 | `select-pane -P 'bg=...'` |
| 标题设置 | `select-pane -T "name"` |

### 9.4.4 In-Process 后端

源码：`utils/swarm/inProcessRunner.ts` (1,552 LOC) + `spawnInProcess.ts` (328 LOC)

进程内 teammate 使用 `AsyncLocalStorage` 实现上下文隔离：

```typescript
// 每个 teammate 拥有独立上下文
const context = {
  abortController: new AbortController(),    // 独立中断
  taskState: new InProcessTeammateTaskState(), // 独立状态
  // 共享：API client、MCP connections
}
```

**执行引擎** `startInProcessTeammate()` 包含：
- **Progress tracking**：进度上报到 leader UI
- **Idle notification**：回合完成时自动通知 leader
- **Plan mode approval**：通过 leader UI 桥接审批
- **Permission handling**：通过 `leaderPermissionBridge` 在 leader UI 弹出权限请求
- **Mailbox polling**：定期检查消息和关闭请求
- **Auto-compact**：上下文超阈值时自动压缩
- **Perfetto tracing**：性能追踪

### 9.4.5 权限委托

源码：`utils/swarm/permissionSync.ts` (928 LOC)

Worker 发起权限请求 → Leader 审批的文件级协议：

```
Worker                                    Leader
  │                                         │
  │─── PermissionRequest ──────────────────▶│ (写入 leader mailbox)
  │                                         │ (弹出 UI 确认)
  │◀── PermissionResponse ─────────────────│ (写入 worker mailbox)
  │                                         │
```

**支持类型**：
- 标准权限请求（文件读写、命令执行）
- 沙箱权限请求（网络访问）

**文件锁保护**：所有请求/响应文件使用 `proper-lockfile` 保护，防止并发写入冲突。

### 9.4.6 团队文件管理

源码：`utils/swarm/teamHelpers.ts` (683 LOC)

**TeamFile 结构**：

```typescript
interface TeamFile {
  leadAgentId: string       // "team-lead@{teamName}"
  leadSessionId: string
  hiddenPaneIds: string[]
  teamAllowedPaths: string[]
  members: TeamMember[]     // 成员列表
}

interface TeamMember {
  agentId: string           // "agentName@teamName"
  name: string
  model: string
  tmuxPaneId?: string
  backendType: BackendType  // 'tmux' | 'iterm2' | 'in-process'
  isActive: boolean
  mode?: string             // 权限模式
  subscriptions?: string[]  // PR 订阅
  worktreePath?: string     // 隔离 worktree 路径
}
```

**存储位置**：`~/.claude/teams/{team-name}/config.json`

### 9.4.7 颜色分配

源码：`utils/swarm/teammateLayoutManager.ts` (107 LOC)

**调色板** `AGENT_COLORS`：red, blue, green, yellow, purple, orange, pink, cyan（8 色）

Round-robin 分配，leader 恒为默认色。颜色用于：
- Tmux 面板边框着色
- UI 中的 agent 标识
- 消息中嵌入的颜色标记

## 9.5 邮箱通信系统

### 9.5.1 架构

源码：`utils/teammateMailbox.ts` (1,183 LOC)

每个 agent 拥有一个 JSON 格式的收件箱文件：

```
~/.claude/teams/{team}/inboxes/{agent}.json
```

**消息结构**：

```typescript
interface TeammateMessage {
  from: string        // 发送者 agent 名
  text: string        // 消息内容
  timestamp: number   // 时间戳
  read: boolean       // 是否已读
  color?: string      // 发送者颜色
  summary?: string    // 消息摘要
}
```

### 9.5.2 结构化消息类型

邮箱支持 **14 种结构化协议消息**：

| 消息类型 | 方向 | 用途 |
|---------|------|------|
| `TeammateMessage` | 双向 | 纯文本消息 |
| `IdleNotificationMessage` | Worker → Leader | 空闲通知 |
| `PermissionRequestMessage` | Worker → Leader | 权限请求 |
| `PermissionResponseMessage` | Leader → Worker | 权限响应 |
| `SandboxPermissionRequestMessage` | Worker → Leader | 沙箱网络权限请求 |
| `SandboxPermissionResponseMessage` | Leader → Worker | 沙箱网络权限响应 |
| `PlanApprovalRequestMessage` | Worker → Leader | 计划审批请求 |
| `PlanApprovalResponseMessage` | Leader → Worker | 审批结果 |
| `ShutdownRequestMessage` | Leader → Worker | 关闭请求 |
| `ShutdownApprovedMessage` | Worker → Leader | 接受关闭 |
| `ShutdownRejectedMessage` | Worker → Leader | 拒绝关闭 |
| `TaskAssignmentMessage` | Leader → Worker | 任务分配通知 |
| `TeamPermissionUpdateMessage` | Leader → 广播 | 权限规则变更 |
| `ModeSetRequestMessage` | Leader → Worker | 切换权限模式 |

### 9.5.3 并发保护

所有邮箱操作使用 `proper-lockfile` 保护：

| 操作 | 重试次数 | 退避策略 |
|------|---------|---------|
| 读取 | 无锁 | — |
| 写入 | 10 次 | 指数退避 |
| 标记已读 | 10 次 | 指数退避 |
| 清空 | 10 次 | 指数退避 |

### 9.5.4 SendMessage 工具

源码：`tools/SendMessageTool/SendMessageTool.ts` (917 LOC)

**输入**：`{ to: string, summary?: string, message: string | StructuredMessage }`

**特殊路由**：

| 目标格式 | 路由方式 |
|---------|---------|
| `agentName` | 直接邮箱投递 |
| `*` | 广播到所有 teammates（跳过自己） |
| `uds:/path/to.sock` | Unix 域套接字（跨会话） |
| `bridge:session_...` | Remote Control 桥接（跨机器） |

**自动恢复**：发送消息给已停止的 agent 时，自动通过 `resumeAgentBackground` 恢复执行。

**权限模型**：Bridge 消息需要显式用户同意（安全检查，不可自动审批）。

## 9.6 任务管理系统

### 9.6.1 任务数据结构

源码：`utils/tasks.ts` (862 LOC)

```typescript
interface Task {
  id: number               // 单调递增整数
  subject: string          // 任务标题
  description?: string     // 详细描述
  activeForm?: string      // 进行时描述（UI 显示）
  owner?: string           // 认领者 agentId
  status: 'pending' | 'in_progress' | 'completed'
  blocks: string[]         // 阻塞的任务 ID 列表
  blockedBy: string[]      // 被哪些任务阻塞
  metadata?: Record<string, unknown>
}
```

**存储位置**：`~/.claude/tasks/{team-name}/{id}.json`

### 9.6.2 原子认领

```typescript
claimTaskWithBusyCheck(taskListId, taskId, claimantId):
  // 1. 获取任务列表级文件锁
  // 2. 检查 claimant 是否已有 in_progress 任务
  // 3. 检查任务是否被 blockedBy 中的未完成任务阻塞
  // 4. 原子更新 status → in_progress, owner → claimantId
  // 5. 释放锁
```

**TOCTOU 防护**：使用任务列表级锁确保「检查 + 认领」的原子性，防止多个 agent 同时认领同一任务。

### 9.6.3 依赖图

任务支持双向依赖：

```
blockTask(taskListId, fromId, toId):
  // fromId 阻塞 toId
  // fromId.blocks.push(toId)
  // toId.blockedBy.push(fromId)
```

**认领前置检查**：`claimTaskWithBusyCheck` 在认领前验证所有 `blockedBy` 任务是否已完成。

### 9.6.4 任务列表 ID 解析

```typescript
getTaskListId() 优先级:
  1. CLAUDE_CODE_TASK_LIST_ID 环境变量
  2. teammate 上下文中的 teamName
  3. leader 的 teamName
  4. sessionId（非团队模式的 fallback）
```

### 9.6.5 任务工具集

| 工具 | LOC | 功能 |
|------|-----|------|
| `TaskCreateTool` | 195 | 创建任务（支持 hook 拦截） |
| `TaskGetTool` | — | 查询单个任务 |
| `TaskListTool` | — | 列出所有任务 |
| `TaskUpdateTool` | — | 更新任务状态/描述 |

**Feature gate**：`isTodoV2Enabled()`（非交互模式或 V2 启用时可用）。

## 9.7 协调者模式

### 9.7.1 概述

源码：`coordinator/coordinatorMode.ts` (369 LOC)

**启用条件**：`feature('COORDINATOR_MODE')` **且** `process.env.CLAUDE_CODE_COORDINATOR_MODE=1`

协调者模式下，Leader **永远不会直接编辑代码**，仅作为纯粹的编排者：
- 分配任务给 Worker
- 综合研究结果
- 决定继续 Worker 对话 vs 生成新 Worker

### 9.7.2 协调者工具集

| 工具 | 用途 |
|------|------|
| `Agent` | 生成 Worker（`subagent_type: "worker"`） |
| `SendMessage` | 继续运行中的 Worker 对话 |
| `TaskStop` | 停止 Worker |
| `subscribe_pr_activity` / `unsubscribe_pr_activity` | PR 活动监控 |

### 9.7.3 四阶段工作流

> **注意**：以下四阶段是协调者系统提示中的建议工作流，非正式的代码级架构模式。源码中的相关描述仅为 prompt 注释中的非正式提及（如 "research, implementation, or verification"）。

```
┌───────────────────┐     ┌───────────────────┐
│ 1. 研究阶段        │     │ 2. 综合阶段        │
│                   │     │                   │
│ 多个 Worker 并行   │────▶│ 协调者汇总发现      │
│ 搜索/分析/理解     │     │ 识别关键文件        │
│                   │     │ 制定实施计划        │
└───────────────────┘     └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │ 3. 实施阶段        │
                          │                   │
                          │ Worker 执行修改     │
                          │ 协调者分配任务      │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │ 4. 验证阶段        │
                          │                   │
                          │ Worker 运行测试     │
                          │ 检查类型/构建       │
                          └───────────────────┘
```

**核心原则**（源码 prompt 原文）："Parallelism is a superpower"——研究阶段启动多个并行 Worker 可大幅提升效率。

### 9.7.4 Continue vs Spawn 决策矩阵

源码：`coordinator/coordinatorMode.ts` — Section 5 "Choose continue vs. spawn by context overlap"

协调者系统提示内置 6 种场景的决策表：

| 场景（源码原文） | 决策 | 理由 |
|------|------|------|
| Research explored exactly the files that need editing | **Continue** | Worker already has the files in context AND now gets a clear plan |
| Research was broad but implementation is narrow | **Spawn fresh** | Avoid dragging along exploration noise; focused context is cleaner |
| Correcting a failure or extending recent work | **Continue** | Worker has the error context and knows what it just tried |
| Verifying code a different worker just wrote | **Spawn fresh** | Verifier should see the code with fresh eyes, not carry implementation assumptions |
| First implementation attempt used the wrong approach entirely | **Spawn fresh** | Wrong-approach context pollutes the retry; clean slate avoids anchoring |
| Completely unrelated task | **Spawn fresh** | No useful context to reuse |

**核心原则**（源码原文）："There is no universal default. Think about how much of the worker's context overlaps with the next task. High overlap → continue. Low overlap → spawn fresh."

**关键规则**：Worker 无法看到协调者的对话。每个 prompt 必须**自包含**——不能说"基于你之前的发现"，而要包含所有必要上下文。

## 9.8 远程传送

### 9.8.1 概述

源码：`utils/teleport.tsx` (1,225 LOC)

Teleport 实现本地↔远程 Claude Code Runtime (CCR) 的会话迁移，支持 Agent 工具的 `isolation: "remote"` 路径。

### 9.8.2 传送流程

**上传（本地 → 远程）**：

```
teleportToRemote():
  1. Haiku 生成标题和分支名
  2. git bundle 创建代码快照
  3. 上传到 Anthropic API
  4. 远程 CCR 环境启动
  5. 返回远程 session ID
```

**下载（远程 → 本地）**：

```
resumeFromTeleport():
  1. 获取远程 session 日志
  2. 重建对话历史
  3. checkout 远程分支到本地
  4. 恢复 session 状态
```

### 9.8.3 Teleport UI 组件

| 组件 | LOC | 功能 |
|------|-----|------|
| `TeleportError.tsx` | 188 | 前置条件检查（登录、stash） |
| `TeleportResumeWrapper.tsx` | 166 | 恢复加载编排 |
| `TeleportProgress.tsx` | 139 | 5 步进度指示 |
| `TeleportStash.tsx` | 115 | Git stash 对话框 |
| `TeleportRepoMismatchDialog.tsx` | 103 | 仓库不匹配对话框 |
| `useTeleportResume.tsx` | 84 | 恢复状态管理 Hook |

**进度步骤**：`validating` → `fetching_logs` → `fetching_branch` → `checking_out` → `done`

### 9.8.4 认证

使用 OAuth 进行身份验证，支持 Anthropic 账户授权。

## 9.9 代理 ID 系统

源码：`utils/agentId.ts` (99 LOC)

### 9.9.1 ID 格式

| ID 类型 | 格式 | 示例 |
|---------|------|------|
| Agent ID | `{agentName}@{teamName}` | `researcher@my-project` |
| Request ID | `{type}-{timestamp}@{agentId}` | `shutdown-1702500000000@researcher@my-project` |

**确定性**：相同的 `agentName` + `teamName` 始终产生相同的 `agentId`。

**约束**：`@` 是保留分隔符——agent 名称会被净化以移除 `@` 字符。

### 9.9.2 ID 作用

- **会话恢复**：崩溃/重启后通过确定性 ID 重新关联 teammate
- **邮箱路由**：`~/.claude/teams/{team}/inboxes/{agentName}.json`
- **任务归属**：`Task.owner` 字段使用 agentId
- **调试追踪**：Perfetto trace 中的 agent 标识

## 9.10 集成点

### 9.10.1 与会话系统

源码：`utils/swarm/reconnection.ts` (119 LOC) + `teammateInit.ts` (129 LOC)

- `computeInitialTeamContext()` 在 `main.tsx` 中注入团队上下文到初始 React 状态
- Teammate 初始化时注册 Stop hook，回合结束时发送空闲通知
- `parentSessionId` 关联每个 teammate 到 leader 的 session UUID

### 9.10.2 与工具系统

- `AgentTool` 是 Swarm 的主入口（07-session.md 已描述）
- `SendMessage` 处理所有跨代理通信
- `TeamCreateTool` / `TeamDeleteTool` 管理团队生命周期
- `TaskCreateTool` / `TaskUpdateTool` 管理任务列表
- `TaskStopTool` 停止运行中的 agent
- In-process teammate 的权限请求通过 `leaderPermissionBridge` 路由到 leader UI

### 9.10.3 与远程控制

- Teleport 启用 `isolation: "remote"` 路径
- `RemoteAgentTask` 管理远程 agent 生命周期
- `CLAUDE_CODE_REMOTE` 环境变量传播到 pane-based teammate
- Bridge 消息通过 Remote Control 基础设施路由

### 9.10.4 与 Worktree 隔离

- `isolation: 'worktree'` 为 teammate 创建独立 git worktree
- Worktree 清理在 team 解散时自动触发
- Fail-closed 策略：有未提交变更时拒绝删除

## 9.11 常量参考

### 9.11.1 Swarm 常量

源码：`utils/swarm/constants.ts` (33 LOC)

| 常量 | 值 | 用途 |
|------|---|------|
| `TEAM_LEAD_NAME` | `"team-lead"` | Leader 的默认名称 |
| `SWARM_SESSION_NAME` | `"claude-swarm"` | tmux 会话名 |
| `CLAUDE_CODE_TEAMMATE_COMMAND` | 环境变量 | 自定义 teammate 启动命令 |
| `CLAUDE_CODE_AGENT_COLOR` | 环境变量 | 自定义 agent 颜色 |
| `CLAUDE_CODE_PLAN_MODE_REQUIRED` | 环境变量 | 强制 plan mode |

### 9.11.2 邮箱常量

| 常量 | 值 | 用途 |
|------|---|------|
| 锁重试次数 | 10-30 | `proper-lockfile` 退避 |
| 退避范围 | 5-100ms | 指数退避区间 |

### 9.11.3 Tmux 布局

| 参数 | 值 | 说明 |
|------|---|------|
| Leader 面板比例 | 30% | 左侧 |
| Teammates 面板比例 | 70% | 右侧 |

### 9.11.4 Agent 颜色调色板

| 颜色 | 使用场景 |
|------|---------|
| red, blue, green, yellow, purple, orange, pink, cyan | Round-robin teammate 分配 |

## 9.12 实现者 Checklist

### Agent 定义
- [ ] 类型化 AgentDefinition 层次（内置/自定义/插件）
- [ ] 支持多位置加载（全局/项目/插件/策略）
- [ ] Frontmatter 格式的 Markdown 定义文件
- [ ] Feature gate 控制内置 agent 启用
- [ ] Agent Memory 局部持久化（3 scope + snapshot 种子）

### 多代理生成
- [ ] 三后端架构（in-process / split-pane / separate-window）
- [ ] 环境自动检测与 fallback
- [ ] 确定性 agent ID（支持崩溃恢复）
- [ ] CLI 标志传播（模型、设置、权限）
- [ ] 名称去重（追加后缀）

### 通信系统
- [ ] 文件邮箱（JSON 格式，锁保护）
- [ ] 10+ 结构化消息类型（覆盖所有协议需求）
- [ ] 广播、直接消息、跨会话路由
- [ ] 自动恢复已停止 agent

### 任务管理
- [ ] 单调递增整数 ID（高位水印 + 文件锁）
- [ ] 双向依赖图（blocks / blockedBy）
- [ ] 原子认领（TOCTOU 防护）
- [ ] 忙碌检查（防止同时执行多个任务）

### 协调模式
- [ ] 纯编排者（永不直接编辑代码）
- [ ] Continue vs Spawn 决策矩阵
- [ ] 自包含 prompt（Worker 无法看到协调者对话）
- [ ] 四阶段工作流（研究 → 综合 → 实施 → 验证）

### 隔离与安全
- [ ] Worktree 隔离（独立 git 工作区）
- [ ] 远程隔离（CCR 环境传送）
- [ ] 权限委托（Worker → Leader UI 桥接）
- [ ] Bridge 消息需显式用户同意

### 清理与恢复
- [ ] 团队解散时清理 worktree、PID、mailbox
- [ ] Fail-closed 策略（有活跃成员时拒绝解散）
- [ ] 会话恢复时重建 team context

## 9.13 设计哲学与架构权衡

### 9.13.1 核心权衡矩阵

| 决策 | 选择 | 替代方案 | 权衡 |
|------|------|----------|------|
| 通信方式 | 文件邮箱 | 消息队列 / 共享内存 | 无需额外依赖、跨进程安全；延迟略高 |
| 生成后端 | 三后端 + 自动检测 | 单一后端 | 最大兼容性；实现复杂度高 |
| 协调模式 | 纯编排者 | 可编辑的半协调者 | 避免协调者与 Worker 职责模糊；增加 Worker 生成成本 |
| Agent ID | 确定性字符串 | UUID | 可读性好、支持崩溃恢复；名称冲突需去重 |
| 任务系统 | 文件级 + 高位水印 | 数据库 | 无需额外依赖；并发依赖文件锁性能 |
| Fork 子代理 | 共享 prompt cache 前缀 | 完全独立会话 | 降低 token 成本；上下文可能过重 |
| 权限委托 | Leader UI 桥接 | 自动审批 | 安全性高；增加用户交互 |
| Agent Memory | 3-scope 文件存储 | 全局 KV 存储 | 代码级隔离清晰；文件粒度较粗 |
| 上下文隔离 | AsyncLocalStorage | 独立进程 | 共享 API/MCP 资源；实现复杂 |

### 9.13.2 文件邮箱 vs 消息队列

源码：`utils/teammateMailbox.ts`

Claude Code 选择基于文件的邮箱而非 IPC 消息队列（如 Unix socket、gRPC）：

- **优势**：零额外依赖；tmux/iTerm2 后端天然无法共享内存；JSON 格式便于调试（直接 `cat` 邮箱文件）；进程崩溃后消息不丢失
- **代价**：文件锁（`proper-lockfile`）引入 10-30 次重试的并发开销；写入延迟受文件系统影响（通常 <1ms）；高频消息场景下性能瓶颈

### 9.13.3 三后端兼容性策略

源码：`utils/swarm/backends/registry.ts` (464 LOC)

后端检测优先级（tmux 嵌套 > iTerm2 原生 > tmux 外部 > in-process fallback）体现了"最大兼容性"原则：

- **In-process**：最低门槛，但共享进程资源
- **Split-pane**：最佳体验（可视多面板），但依赖 tmux/iTerm2
- **Separate-window**：旧模式，保持向后兼容

实现复杂度的代价：`spawnMultiAgent.ts` (1,093 LOC) 是多代理子系统第二大的文件，主要因为需要同时处理 3 种后端的差异化逻辑。

### 9.13.4 Fork 子代理的 Prompt Cache 优化

源码：`tools/AgentTool/forkSubagent.ts` (210 LOC)

Fork 子代理是 Claude Code 多代理系统中最精细的成本优化设计：

- **原理**：`buildForkedMessages()` 构建与父级完全相同的消息前缀，使 Anthropic API 的 prompt cache 命中率最大化
- **约束**：Fork Agent 的系统提示要求"500 词以内回复"，避免过长输出抵消 cache 节省
- **⚠️ 推断**：这个设计暗示 Anthropic API 的 prompt cache 按**前缀匹配**计费，前缀越长 cache 节省越大

### 9.13.5 确定性 ID 的崩溃恢复语义

源码：`utils/agentId.ts` (99 LOC)

`agentName@teamName` 格式不是随意选择——它使得会话恢复时无需持久化 ID 映射：

- **恢复流程**：进程崩溃后，重启的 teammate 通过相同的 `agentName + teamName` 重新生成 agentId，自动匹配到 `~/.claude/teams/{team}/inboxes/{agentName}.json` 中未读消息
- **代价**：名称冲突需要去重逻辑（追加 -2, -3 后缀），但这是一次性成本

### 9.13.6 纯协调者 vs 可编辑半协调者

源码：`coordinator/coordinatorMode.ts` (369 LOC)

协调者模式选择"永不编辑代码"而非"可以介入编辑"：

- **优势**：避免协调者与 Worker 之间的职责模糊；协调者专注于编排，所有代码修改可追踪到具体 Worker
- **代价**：简单任务（如改一个配置值）也需要生成 Worker，增加 token 成本和延迟
- **设计信号**：决策矩阵的 6 个场景中有 4 个选择 Spawn fresh，反映"干净上下文 > 上下文复用"的偏好
