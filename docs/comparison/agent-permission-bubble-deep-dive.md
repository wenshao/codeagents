# Qwen Code 改进建议 — Agent 权限冒泡与审批路由 (Agent Permission Bubble)

> 核心洞察：当我们赋予 AI Agent 并行拉起后台子代（Subagent）的能力后，安全审查逻辑就面临了严峻的挑战。当一个运行在后台、不可见的 Subagent 决定去删除一个文件时，由于它没有自己独立的终端窗口，它的权限申请对话框（Confirmation Prompt）该弹在哪里？在目前大多数 CLI 框架中，由于缺乏跨层级的 UI 桥接机制，这种请求会直接导致后台任务永久死锁（静默挂起）。Claude Code 在这方面展现了大师级的并发治理，构建了 `leaderPermissionBridge` 将子代理的致命危险操作“冒泡（Bubble）”回主交互终端供人类审批；而 Qwen Code 尚未解决多 Agent 的安全接力。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、后台代理的致命死锁

### 1. Qwen Code 现状：孤立的 Sandbox
如果我们给 Qwen Code 加上衍生代理（Spawn Agent）的能力：
- **痛点一（静默阻塞）**：当子 Agent A 尝试写入 `src/config.json` 时，安全策略（Yolo 模式未开启）要求人类输入 `y/n` 确认。由于 Agent A 在后台（Background），没有绑定 `stdin/stdout`，它发出的 `[Y/n]` 提示永远不会显示在屏幕上。
- **痛点二（状态丢失）**：用户在主终端只能看到 Spinner 永远转圈，任务进度彻底卡死，甚至不知道是因为什么卡住了。如果用户等得不耐烦强制退出了主程序，这个未被正常清理的挂起操作还可能导致文件被锁。

### 2. Claude Code 解决方案：跨进程/跨层级的状态冒泡
在 Claude Code 的深水区（`utils/swarm/leaderPermissionBridge.ts` 和 `utils/swarm/permissionSync.ts`），针对多 Agent 协作网络建立了一套名为 `PermissionMode: 'bubble'` 的路由协议。

#### 机制一：子节点的主动上浮 (Bubble Up)
当创建任何一个内部同进程队友（InProcess Teammate）时，引擎会自动将其权限模式覆盖为 `bubble`：
```typescript
const subagentConfig = {
   ...config,
   permissionMode: 'bubble', // 强制冒泡
}
```
当这个子节点触发高危工具时，底层的 `promptForToolUse` 钩子不会尝试在自己的控制台上画 `Yes/No` 弹窗。相反，它会将本次 Tool Use 的参数、文件内容甚至意图，封装成一个 JSON 对象，通过 `sendPermissionRequestViaMailbox` 或直接推给 `leaderPermissionBridge` 队列。然后**暂停执行，并在本地 `await` 返回结果**。

#### 机制二：主交互节点的 UI 挂载 (Leader Queue)
在人类开发者所在的那个可见的主终端（Leader REPL 屏幕）上，有一个常驻的轮询器或事件监听器。
当它收到来自 `Agent-Auth-Refactor-01` 的高危权限请求时：
它会在主屏幕上暂停当前的对话，立刻弹出一个最高优先级的 Modal（对话框）：
> **[Subagent Request]** Agent "Auth-Refactor-01" wants to run `rm -rf ./old_keys/`.
> View Diff | Approve (y) | Deny (n)

#### 机制三：结果回传与执行恢复
一旦用户在这个主终端敲下了 `Y` 批准，主引擎会通过底层的事件总线将 `Approved: true` 的信号发射回去。挂起的子节点收到信号瞬间解冻，执行真正的底层删除操作。

## 二、Qwen Code 的改进路径 (P2 优先级)

如果 Qwen 想真正支持“包工头-打工人”的复杂任务树，权限路由必不可少。

### 阶段 1：重构 `ApprovalMode` (权限模式)
1. 在现有的权限枚举（如 `Auto`, `Ask` 等）中，新增一个状态 `Bubble`。
2. 剥离执行工具（Execute Tool）与询问 UI（Ask UI）的耦合。当模式为 `Bubble` 时，工具拦截器不渲染界面，而是生成一个 `PermissionRequestEvent` 对象丢进全局单例。

### 阶段 2：开发 Leader 桥接器 (`PermissionBridge`)
1. 在 `packages/core/src/utils/` 下开发全局的 `leaderPermissionBridge.ts` 队列。
2. 为 UI 框架暴露一个 Hooks，例如 `useLeaderPermissionQueue()`。
3. 在顶层的 TUI（如 `App.tsx` 或 `CLI Main Loop`）中全局监听此队列。一旦有数据，中断常规输入框，强行渲染高亮的安全审计弹窗。

### 阶段 3：进程间通信降级 (File Mailbox)
如果要支持跨进程（如 Fork 出去的真正脱机 Node.js 进程）的冒泡：
系统应当支持将 `PermissionRequestEvent` 序列化写入到一个约定好的临时文件池中，主进程定期扫这个文件夹来实现跨进程的安全审批。

## 三、改进收益评估
- **实现成本**：中等。核心是解耦现有的阻塞式控制台 Prompt 组件，改成基于发布/订阅（Event Emitter）或者 Promise 挂起的异步队列机制，代码量约 200 行。
- **直接收益**：
  1. **消灭死锁，解锁并行**：彻底盘活后台 Agent，让它们在安全受控的情况下全速运转。
  2. **企业级权限合规**：确保无论系统生成了多少个复杂的嵌套子任务，所有的毁灭性操作依然必须强制流经“唯一的人类监督者节点”。