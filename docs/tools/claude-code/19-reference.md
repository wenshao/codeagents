# 19. 参考速查——数据结构、术语表、实体关系

> 开发者在阅读 Claude Code 架构时最常见的困惑不是功能太多，而是**分不清哪些概念属于哪一层**。本文提供三份速查表：核心数据结构、术语表、实体关系图。
>
> **Qwen Code 对标**：这些概念模型同样适用于 Qwen Code——两者共享工具调用 Agent 的基本架构范式。
>
> **致谢**：本文的概念框架参考了 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 项目的数据结构和术语整理。

## 一、核心数据结构速查

### 设计原则

1. **内容状态 vs 控制状态分离**：`messages`、`tool_result` 是内容状态；`turn_count`、`transition` 是控制状态
2. **持久状态 vs 运行时状态分离**：tasks、memory 是持久的；权限决策、MCP 连接是运行时的

### 查询与对话

| 数据结构 | 职责 | 所在层 |
|---------|------|--------|
| **Message** | 对话和工具往返历史 | messages 数组 |
| **NormalizedMessage** | 标准化后的消息（适配模型 API） | API 请求构建 |
| **QueryParams** | 启动一次查询的外部输入 | 查询引擎入口 |
| **QueryState** | 随轮次变化的可变状态 | 查询引擎内部 |
| **TransitionReason** | 解释为什么进入下一轮 | 查询边界 |
| **CompactSummary** | 压缩后的摘要上下文 | 上下文管理 |

### 提示与输入

| 数据结构 | 职责 | 所在层 |
|---------|------|--------|
| **SystemPromptBlock** | 一个稳定的提示片段 | 系统提示构建 |
| **PromptParts** | 分离的提示片段（组装前） | 提示管线 |
| **ReminderMessage** | 临时的单轮/单模式注入 | 消息管线 |

### 工具与控制平面

| 数据结构 | 职责 | 所在层 |
|---------|------|--------|
| **ToolSpec** | 模型对一个工具的认知（name + schema） | 工具注册表 |
| **ToolDispatchMap** | 名称到处理器的路由表 | 工具分发 |
| **ToolUseContext** | 工具执行时的共享环境 | 工具运行时 |
| **ToolResultEnvelope** | 标准化的工具返回结果 | 主循环 |
| **PermissionRule** | 权限策略（allow/deny/ask） | 权限层 |
| **PermissionDecision** | 权限门控的结构化输出 | 权限层 |
| **HookEvent** | 围绕循环发射的生命周期事件 | Hook 系统 |

### 持久工作状态

| 数据结构 | 职责 | 所在层 |
|---------|------|--------|
| **TaskRecord** | 持久工作图节点（目标 + 状态 + 依赖） | 任务面板 |
| **ScheduleRecord** | 描述何时触发工作的规则 | Cron 调度 |
| **MemoryEntry** | 跨会话保留的知识 | 记忆系统 |

### 运行时执行状态

| 数据结构 | 职责 | 所在层 |
|---------|------|--------|
| **RuntimeTaskState** | 后台/长时间工作的实时执行槽 | 运行时管理器 |
| **Notification** | 将运行时结果桥接回主循环 | 通知系统 |
| **RecoveryState** | 失败后用于连贯恢复的状态 | 错误恢复 |

### 团队与平台

| 数据结构 | 职责 | 所在层 |
|---------|------|--------|
| **TeamMember** | 持久队友身份 | 团队配置 |
| **MessageEnvelope** | 队友间的结构化消息 | 邮箱系统 |
| **RequestRecord** | 审批/关闭/交接等协议工作流 | 请求追踪器 |
| **WorktreeRecord** | 一个隔离执行通道的记录 | Worktree 索引 |
| **MCPServerConfig** | 一个外部能力 Provider 的配置 | MCP 配置 |

## 二、术语表

### 核心循环

| 术语 | 含义 |
|------|------|
| **Query** | 一次完整的"用户输入→Agent 处理→输出"过程，可能跨多轮 |
| **Turn** | Query 内的一轮：模型响应 + 工具执行 |
| **Transition** | 从当前轮到下一轮的原因（工具完成/token 截断/压缩/重试/Hook 拦截） |
| **End Turn** | 模型决定停止（`stop_reason: end_turn`） |
| **Mid-Turn Drain** | 工具批次之间检查用户是否有新输入 |
| **Continuation** | Query 仍然存活并应继续推进（但原因各异） |

### 工具系统

| 术语 | 含义 |
|------|------|
| **Tool Spec** | 工具的 Schema 定义（发送给模型的 JSON Schema） |
| **Tool Dispatch** | 将模型返回的 tool_use 路由到实际处理器 |
| **Tool Control Plane** | 工具的注册/发现/过滤/权限——不是执行本身 |
| **Tool Execution Runtime** | 工具实际执行时的调度/并发/进度/合并规则 |
| **ToolSearch** | 延迟加载：模型通过搜索发现不常用工具 |
| **Streaming Tool Execution** | 在 API 流式返回工具调用时就开始解析和准备执行 |

### 上下文管理

| 术语 | 含义 |
|------|------|
| **Compact** | 上下文压缩（裁剪旧工具输出 + 生成摘要） |
| **Cache Edits** | 最轻量的压缩——只裁剪缓存前缀内的旧编辑 |
| **Prompt Cache** | API 端缓存匹配的前缀 token，节省成本 |
| **Static/Dynamic Boundary** | 系统提示中不变部分和易变部分的分界线 |
| **System Reminder** | 临时注入的 `<system-reminder>` 标签上下文 |

### 多 Agent

| 术语 | 含义 |
|------|------|
| **Subagent** | 由主 Agent 派生的子 Agent |
| **Fork** | 继承父 Agent 完整上下文的 Subagent |
| **Coordinator** | Leader-Worker 模式的协调者 |
| **Swarm** | 多 Agent 协作系统（InProcess/tmux/iTerm2 后端） |
| **Teammate** | Swarm 中的一个 Agent 实例 |
| **Mailbox** | 文件 IPC 的邮箱系统（Teammate 间通信） |
| **Kairos** | Always-On 自治 Agent 模式 |

### Hook 系统

| 术语 | 含义 |
|------|------|
| **PreToolUse** | 工具执行前触发的 Hook 事件 |
| **Prompt Hook** | 用 LLM 做决策的 Hook 类型（Claude Code 独有） |
| **Agent Hook** | 创建临时 Agent 做深度验证的 Hook 类型 |
| **hookify** | 从对话中自动生成 Hook 规则的机制 |

## 三、实体关系速查

```
┌─────────────────────────────────────────────────────────┐
│                    用户层                                │
│  UserInput → QueryParams → ProcessSlashCommand         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 查询引擎层                               │
│  QueryState ←→ TransitionReason                         │
│       │                                                 │
│       ├─→ SystemPromptBlock[] → PromptParts             │
│       ├─→ NormalizedMessage[] → API Request             │
│       └─→ ReminderMessage (临时注入)                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               工具控制平面                                │
│  ToolSpec → ToolDispatchMap → ToolUseContext             │
│       │                                                 │
│       ├─→ PermissionRule → PermissionDecision            │
│       ├─→ HookEvent (PreToolUse/PostToolUse)            │
│       └─→ ToolResultEnvelope → 回到 QueryState          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              持久状态层                                   │
│  TaskRecord (工作图) ←→ RuntimeTaskState (执行槽)        │
│  MemoryEntry (跨会话) ←→ CompactSummary (压缩)           │
│  ScheduleRecord (Cron) ←→ Notification (结果桥接)        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               团队/平台层                                 │
│  TeamMember → MessageEnvelope → Mailbox IPC              │
│  WorktreeRecord → 隔离执行通道                            │
│  MCPServerConfig → CapabilityRoute                       │
└─────────────────────────────────────────────────────────┘
```
