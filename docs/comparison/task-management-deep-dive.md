# Qwen Code 改进建议 — 任务管理与多智能体协同 (Task Management System)

> 核心洞察：Claude Code 拥有一个完整的、支持多进程和依赖关系图的后台任务管理系统（Task System），用于支撑其 Swarm（多 Agent）架构。而 Qwen Code 目前仅提供单机的、无状态的 `TodoWriteTool`。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、架构对比

### 1. Claude Code 的任务协同架构
Claude Code 的任务系统（位于 `utils/tasks.ts` 和相关 Tools）专门为多 Agent 协同设计：
- **分布式锁与并发安全**：通过 `.highwatermark` 递增分配 ID，并通过文件锁（`lockfile.ts`）实现跨进程的任务并发安全读写，允许不同进程中的 Agent（Swarm）安全地认领和更新任务。
- **任务依赖图谱 (Dependency Graph)**：任务模型包含 `blocks`（阻塞哪些任务）和 `blockedBy`（被哪些任务阻塞），Agent 可以精确推断任务执行顺序。
- **归属与生命周期**：包含 `owner` 字段标记当前哪个 Agent 正在处理该任务，状态严格在 `pending`、`in_progress`、`completed` 之间流转。
- **细粒度工具集**：提供了 6 个独立工具（`TaskCreateTool`、`TaskGetTool`、`TaskListTool`、`TaskOutputTool`、`TaskStopTool`、`TaskUpdateTool`），支持对任务树的增删改查。
- **IPC 信号通知**：进程内使用 `tasksUpdated.emit()` 信号，UI 能够实时刷新任务列表和 Spinner 状态（`activeForm`）。

### 2. Qwen Code 的现状
Qwen Code 目前的任务管理仅限于 `packages/core/src/tools/todoWrite.ts`（TodoWriteTool）：
- 仅提供一个 `todo_write` 工具，每次操作需覆写整个 Todo 列表。
- 数据结构简单：仅包含 `id`、`content`、`status`，缺乏依赖关系和归属者概念。
- 不支持多智能体（Multi-Agent）协同认领任务，缺乏并发安全机制。

## 二、Qwen Code 的改进路径 (P1 优先级)

为了支持真正意义上的多智能体协作（Coordinator/Swarm），Qwen Code 必须重构其任务系统。

### 阶段 1：数据模型与底层支持 (Data Model & IPC)
1. **持久化与并发控制**：在项目级的 `.qwen` 目录中建立任务注册表。引入跨进程文件锁，保障多个 Qwen Agent 进程可以安全读写任务状态。
2. **丰富的任务 Schema**：
   ```typescript
   export interface Task {
     id: string;
     subject: string;
     description: string;
     activeForm?: string; // UI 渲染用的进行时动词，如 "Running tests"
     owner?: string;      // 执行该任务的 Agent ID
     status: 'pending' | 'in_progress' | 'completed' | 'failed';
     blocks: string[];    // 阻塞的其他任务 ID
     blockedBy: string[]; // 依赖的前置任务 ID
     metadata?: Record<string, unknown>;
   }
   ```
3. **事件驱动 (Event-Driven)**：实现 `TaskUpdate` 事件流，主节点（Coordinator）能够实时侦听子 Agent 更新任务状态并更新 TUI。

### 阶段 2：原子化 Tool 拆分 (Granular Tools)
废弃单一的 `todo_write` 覆写模式，拆分为原子化的 CRUD 工具：
- `TaskCreateTool`: 创建新任务并指定前置依赖。
- `TaskListTool`: 获取当前所有任务及状态拓扑。
- `TaskUpdateTool`: 认领任务（设置 `owner`）或更改状态。
- `TaskGetTool`: 获取单个任务的详细信息（包括 `metadata` 和长篇 `description`）。

### 阶段 3：Swarm 调度集成 (Coordinator Integration)
主控 Agent (Leader) 利用 `TaskCreateTool` 分解大任务并建立依赖关系，而后唤起（或等待）子 Agent (Worker)。子 Agent 读取 `pending` 且 `blockedBy` 为空的子任务，认领执行。执行完毕后，使用 `TaskUpdateTool` 标记完成，自动解锁下游任务。

## 三、改进收益评估
- **实现成本**：涉及核心架构变动，约 1000 行代码，需 1-2 周开发时间（高难度）。
- **直接收益**：
  1. **稳定性提升**：细粒度 Tool 减少了模型每次重写整个 Todo List 的 Token 开销和幻觉风险。
  2. **多并发解锁**：从底层打通了真正能够并行工作的多 Agent 架构。
  3. **可观测性**：UI 可以清晰渲染任务依赖树（Tree）及各个 Agent 的实时进度。