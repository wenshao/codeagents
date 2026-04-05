# Qwen Code 改进建议 — InProcess 同进程多 Agent 隔离 (InProcess Agent Isolation)

> 核心洞察：当代码 Agent 发展到多 Agent（Swarm）协作架构时，主 Agent 往往需要拉起（Spawn）子 Agent（Worker）来并行处理子任务。最轻量、最快捷的拉起方式就是**同进程拉起（In-Process）**。然而，Node.js 的单进程模型和大量使用的全局变量（Global State）极易导致多个运行中的 Agent 上下文互相污染（例如：工作目录冲突、日志串台、Token 计数混乱）。Claude Code 通过 Node.js 的 `AsyncLocalStorage` 实现了优雅的“并发沙盒隔离”；而 Qwen Code 目前在状态管理上存在全局泄漏隐患，无法安全支持真正的同进程多 Agent 运行。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么多 Agent 需要上下文隔离？

想象以下场景：
你让 Qwen Code “重构后端 API 并同时更新前端调用”。
主 Agent 将任务分为两半，并在同一个 Node 进程中拉起了两个后台子 Agent：
- Agent A 处理后端（需将 `cwd` 设为 `./backend`，并使用特定的系统提示词）。
- Agent B 处理前端（需将 `cwd` 设为 `./frontend`）。

**未隔离的致命后果**：
由于 Qwen Code 的大部分配置（如 `Config` 单例、当前工作目录 `process.cwd()`、Telemetry Token 累加器）是全局共享的：
1. Agent A 刚刚把工作目录切到 `./backend`，Agent B 就来读取文件，导致 Agent B 找不到 `./frontend` 下的文件（目录污染）。
2. Agent A 报错抛出的日志，可能会被记录成 Agent B 的失败（标识符混淆）。
3. 多个 Agent 同时更新同一个对话历史文件，引发 JSON 解析崩溃（文件锁冲突）。

## 二、Claude Code 的隔离方案：AsyncLocalStorage

在 Claude Code 的源码中，它实现了一个高度成熟的 `InProcessBackend`（位于 `utils/swarm/backends/InProcessBackend.ts` 和 `spawnInProcess.ts`）。

它的核心隔离武器是 Node.js 原生的 `AsyncLocalStorage` (ALS)。

### 1. 什么是 AsyncLocalStorage？
ALS 允许我们在异步调用链中存储“局部全局变量”（类似于 Java/Thread 中的 `ThreadLocal`）。在 Node 单线程中，它可以让并发的不同 Promise 链拥有自己独立的数据副本。

### 2. Claude Code 中的应用
```typescript
// Claude Code: utils/swarm/inProcessRunner.ts
import { AsyncLocalStorage } from 'async_hooks';

// 创建 Agent 的上下文沙盒
const agentContextStorage = new AsyncLocalStorage<TeammateContext>();

export function runWithTeammateContext<T>(context: TeammateContext, fn: () => Promise<T>) {
    // 在这个 fn 执行的整个生命周期（以及它 await 产生的所有子异步调用）中，
    // getTeammateContext() 都会返回专属于当前子 Agent 的 context，而不是全局的。
    return agentContextStorage.run(context, fn);
}
```

**被隔离的关键上下文：**
- `cwd` 工作目录覆盖：主 Agent 也许在 `/root`，但 ALS 内的子 Agent `getCwd()` 会返回 `/root/backend`。
- `agentId` 和 `teamName`：用于独立路由 IPC 消息。
- `Telemetry` 和 `Workload` 标签：在 `services/analytics/metadata.ts` 和 `utils/workloadContext.ts` 中，日志会自动带上 ALS 中的当前 Agent 身份，绝不串台。

通过这套机制，Claude Code 能在单进程里同时运行 10 个子 Agent 且丝毫不乱。

## 三、Qwen Code 的改进路径 (P1 优先级)

Qwen Code 当前的 `Config`、`workspaceContext` 和 `debugLogger` 设计过于依赖单例或显式参数传递，要走向 Swarm 时代，必须重构状态管理。

### 阶段 1：引入 ALS 上下文管理器
1. 新建 `packages/core/src/core/agentContext.ts`。
2. 定义 `AgentContext` 接口，包含：`agentId`、`role`、`cwd`、`tokenBudget`。
3. 实例化 `new AsyncLocalStorage<AgentContext>()` 并导出获取方法 `getCurrentAgentContext()`。

### 阶段 2：消除全局状态污染
梳理 Qwen Code 中所有危险的“全局方法”，让它们优先尝试从 ALS 中取值：
1. **工作目录获取**：封装一个统一的 `getCwd()`。如果 `getCurrentAgentContext().cwd` 有值，则返回覆盖值，否则返回全局的 `config.getProjectRoot()`。
2. **日志打印**：修改 `debugLogger.ts`。在拼接日志前缀时，自动追加 `[Agent: ${getCurrentAgentContext()?.agentId ?? 'Main'}]`。
3. **Telemetry 计数**：修改 `uiTelemetryService.ts`，确保 Token 消耗分别累加到主/子 Agent 账上。

### 阶段 3：提供 Spawn 包裹器
在未来实现 `/subagent` 命令或 Agent 的工具能力时，使用 ALS 包裹执行：
```typescript
async function spawnInProcessWorker(taskPrompt: string, overrideCwd: string) {
    const workerContext = { agentId: generateId(), cwd: overrideCwd };
    
    // 安全拉起！
    return agentContextStorage.run(workerContext, async () => {
        const workerAgent = new AgentInteractive(...);
        await workerAgent.runReasoningLoop(...);
    });
}
```

## 四、改进收益评估
- **实现成本**：中。需要全盘审查全局单例的使用情况。
- **直接收益**：
  1. **解锁 Swarm 能力**：彻底消灭多 Agent 同进程运行的并发 BUG，这是向智能体集群进化的基础。
  2. **高内聚低耦合**：无需在成百上千的函数签名中层层传递 `agentId` 或 `cwd` 参数，代码更干净。
  3. **易于调试**：多并发环境下的错误日志能准确归因到具体的后台 Worker。