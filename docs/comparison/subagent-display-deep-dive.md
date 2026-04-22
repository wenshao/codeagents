# SubAgent 展示 Deep-Dive——Claude Code vs Qwen Code

> **核心问题**：Claude Code 和 Qwen Code 在运行 SubAgent 时的 UI 展示有何差异？各自的设计哲学与借鉴机会是什么？
>
> 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、两条不同的 UI 哲学

### Claude Code = 双模式
1. **Task 工具内联模式**（`AgentTool.tsx`）——主消息流内展示，完成即收
2. **Coordinator 后台面板**（`CoordinatorAgentStatus.tsx`）——独立面板，多 agent 并发，30s TTL 自动驱逐

### Qwen Code = 单一嵌入式
**`AgentExecutionDisplay.tsx`** 作为工具结果嵌入消息流，三档可折叠展示（compact / default / verbose），Ctrl+E / Ctrl+F 切换。

---

## 二、逐维度对比

| 维度 | Claude Code | Qwen Code |
|---|---|---|
| **发起展示** | Task：内联 `⏺ Task(...)` ⎿ 摘要<br>Coordinator：独立面板 `◯ name · ▶ 0s` | 嵌入工具组 `├─ agent_name ● Running` |
| **SubAgent 身份** | `AgentProgressLine.tsx:75` 彩色背景标签 | `AgentExecutionDisplay.tsx:148` 彩色 `agentColor` + StatusDot |
| **执行中实时性** | Task：spinner + 最终结果<br>Coordinator：仅最后一个工具 + 计数（1s tick）| **完整工具列表**（默认最后 5 个，verbose 全部）|
| **展示模式切换** | Task 固定；Coordinator `↑↓`+Enter 导航 | **Ctrl+E / Ctrl+F 三档切**（compact ↔ default ↔ verbose）|
| **并发布局** | Coordinator 垂直列表 `◯ A / ◯ B / ◯ C` | 同工具组内 `.map()` 渲染 |
| **权限审批路由** | Task 内部黑盒；Coordinator 独立流 | **焦点锁**（`focusedSubagentRef` + `isWaitingForOtherApproval`）|
| **完成后摘要** | `RECENT_COMPLETED_TTL_MS = 30_000` 自动驱逐 | 4 行执行摘要（tokens / rounds / duration / success rate）长期保留 |
| **失败处理** | Coordinator `✕ Failed (Ns ago)` → 30s 后驱逐 | 红色 `├─ ✕ Failed` 永久保留可追溯 |
| **独立管理视图** | `/agents` + `AgentsMenu` / `AgentsList`（agent 定义）| 无 |
| **后台并发能力** | ✅ 真后台（`evictAfter` 驱动，独立 loop） | ❌ 无（subagent 必须在 tool 调用周期内完成）|

---

## 三、关键代码片段

### 3.1 Claude Coordinator Task Panel（`CoordinatorAgentStatus.tsx`）

**渲染条件**（文件头注释原文）：

> CoordinatorTaskPanel —— Steerable list of background agents.
> Renders below the prompt input footer whenever local_agent tasks exist.
> Visibility is driven by `evictAfter`: `undefined` (running/retained) shows always; a timestamp shows until passed. Enter to view/steer, x to dismiss.

**核心逻辑**：

```typescript
// L31-33：可见任务 = 非已驱逐 + 按 startTime 排序
export function getVisibleAgentTasks(tasks: AppState['tasks']): LocalAgentTaskState[] {
  return Object.values(tasks)
    .filter((t): t is LocalAgentTaskState => isPanelAgentTask(t) && t.evictAfter !== 0)
    .sort((a, b) => a.startTime - b.startTime)
}

// L45-63：1s tick：重渲染 elapsed + 驱逐过期任务
React.useEffect(() => {
  if (!hasTasks) return
  const interval = setInterval((tasksRef, setAppState, setTick) => {
    const now = Date.now()
    for (const t of Object.values(tasksRef.current)) {
      if (isPanelAgentTask(t) && (t.evictAfter ?? Infinity) <= now) {
        evictTerminalTask(t.id, setAppState)
      }
    }
    setTick(prev => prev + 1)
  }, 1000, tasksRef, setAppState, setTick)
  return () => clearInterval(interval)
}, [hasTasks, setAppState])

// L72-75：垂直列表：MainLine + N 个 AgentLine
return <Box flexDirection="column" marginTop={1}>
  <MainLine ... />
  {visibleTasks.map((task, i) => 
    <AgentLine task={task} onClick={() => enterTeammateView(task.id, setAppState)} />
  )}
</Box>
```

**设计精妙之处**：
- `evictAfter` 作为**数据驱动的可见性**，不是"已完成"而是"过期时间戳"——支持 `x` 键立即驱逐（`evictAfter = 0`）、30s 延迟驱逐、永久保留（`undefined`）
- 1s `setInterval` 同时负责**elapsed time 刷新** + **驱逐**，单一 tick 源避免多定时器竞争
- `tasksRef` + `setTick` 解耦——`useEffect` 依赖只有 `hasTasks`，不依赖 `tasks` 避免每次 task 变化重建 interval

### 3.2 Qwen Code `AgentExecutionDisplay` 三档切换

```typescript
// AgentExecutionDisplay.tsx:124-140
useKeypress((key) => {
  if (key.ctrl && key.name === 'e') {
    // compact ↔ default
    setDisplayMode(current => current === 'compact' ? 'default' : 'compact')
  } else if (key.ctrl && key.name === 'f') {
    // default ↔ verbose
    setDisplayMode(current => current === 'default' ? 'verbose' : 'default')
  }
}, { isActive: true })
```

**三档信息密度**：

| 模式 | 显示内容 | 用途 |
|---|---|---|
| `compact`（默认）| Agent 名 + status + 当前工具 + `+N more tool calls (ctrl+e to expand)` | 平静浏览 |
| `default`（Ctrl+E）| 任务描述 + 最后 5 个工具 + 执行摘要 | 查看进展 |
| `verbose`（Ctrl+F）| 完整任务 + 全部工具 + 详细统计 | 深度调试 |

### 3.3 Qwen Code `ToolGroupMessage` 焦点锁

```typescript
// ToolGroupMessage.tsx:99-123
const subagentsAwaitingApproval = useMemo(
  () => toolCalls.filter(tc => isAgentWithPendingConfirmation(tc.resultDisplay)),
  [toolCalls],
)

const focusedSubagentRef = useRef<string | null>(null)
const stillPending = subagentsAwaitingApproval.some(
  tc => tc.callId === focusedSubagentRef.current,
)
if (!stillPending) {
  // 焦点移交给第一个等待中的 subagent（first-come first-served）
  focusedSubagentRef.current = subagentsAwaitingApproval[0]?.callId ?? null
}

// 渲染（L256-287）
{toolCalls.map(tool => {
  const isSubagentFocused = isFocused && !toolAwaitingApproval && focusedSubagentCallId === tool.callId
  const isWaitingForOtherApproval = isAgentWithPendingConfirmation(tool.resultDisplay) 
    && focusedSubagentCallId !== null 
    && focusedSubagentCallId !== tool.callId
  return <ToolMessage {...tool} isFocused={isSubagentFocused} isWaitingForOtherApproval={isWaitingForOtherApproval} />
})}
```

**效果**：3 个并发 subagent 都需要审批时，用户只看到**一个审批 prompt**，其他显示 `⏳ Waiting for other approval...`，按序轮转。

---

## 四、典型场景逐帧对比

### 场景 A：单 SubAgent 10 秒任务

**Claude Code Task 模式**：

```
⏺ Task(Research X)
  ⎿ researcher is thinking...
  ⎿ Running web_search (2s)
  ⎿ Running parse_results (1s)
  ⎿ Done (10s · 1.5K tokens)
     Found 3 relevant sources about...
```

**Qwen Code compact 模式（默认）**：

```
├─ researcher ● Running
│  Task: Research X
│  ⊷ web_search  (ctrl+e to expand)
│  +2 more tool calls
```

10 秒后完成：
```
├─ researcher ✓ Completed  
│  Execution Summary: 3 tool uses · 10s · 1,500 tokens
```

**差异**：Claude 展示**时间轴**（每个工具一行带时长），Qwen 展示**状态摘要**（当前+计数，点击展开）。

---

### 场景 B：3 个并发 SubAgent，第 2 个触发权限审批

**Claude Code Coordinator 模式**：

```
[底部面板]
◯ main
◯ researcher-A · ▶ 2s · 200 tokens
◯ researcher-B · ▶ 2s · 150 tokens  ⚠ needs approval
◯ researcher-C · ▶ 2s · 100 tokens
```

用户按 `↓↓` 选中 B，按 Enter 进入详情视图：
```
researcher-B
├─ Task: Research B
├─ Running web_fetch
└─ ⚠ Approval required: Allow web access to example.com?
   [y/n/s/d]
```

审批后按 ESC 回主视图。

**Qwen Code 嵌入模式**：

```
├─ Tool Group
│  ├─ researcher-A ● Running
│  │  ⏳ Waiting for other approval...
│  ├─ researcher-B ● Running  ← (focused)
│  │  ┤ Confirm: Allow web access to example.com?
│  │  └─ [y/n/s/d]
│  ├─ researcher-C ● Running
│  │  ⏳ Waiting for other approval...
```

用户在**主视图直接输入 y/n**，无需导航切换。审批后焦点自动切到下一个 subagent。

**差异**：
- Claude = **空间分离**（面板 vs 详情），需要 `↓↓ Enter` + `ESC`
- Qwen = **时间分离**（焦点锁排队），无需导航

---

### 场景 C：SubAgent 失败 + 30s 后

**Claude Code Coordinator**：

```
t=0:  ◯ researcher · ✕ Failed (Network timeout)
t=30: [行消失，被驱逐]
```

用户想看失败详情需要从日志找。

**Qwen Code**：

```
├─ researcher ✕ Failed
│  Failed: Network timeout
│  Attempted 2 tools · 500 tokens · 5s
│  [永久保留在历史中]
```

---

### 场景 D：用户 Ctrl+C 中断 SubAgent

**Claude Code**：取消信号通过 `AbortController` 传递到后台任务；Coordinator 面板状态变为 `canceled`。

**Qwen Code**：Ctrl+C 取消当前工具调用（包括 subagent），UI 显示 `Command was cancelled`。

---

## 五、三大设计哲学差异

### 1. 后台 vs 嵌入

| | Claude Code | Qwen Code |
|---|---|---|
| **模型** | Coordinator = **真后台并发**（`AppState.tasks` 独立于主 loop，1s tick 驱动）| **嵌入式**（subagent 作为 tool result 在消息流内）|
| **生命周期** | `evictAfter` 时间戳控制可见性，可**永久保留** | 随消息树追加，tool 调用结束 = subagent 结束 |
| **能力** | 支持"最小化继续运行" | 必须在 tool 周期内完成 |
| **代价** | AppState 内存占用 | 消息流可能变长 |

### 2. 多模态展示

| | Claude Code | Qwen Code |
|---|---|---|
| **切换方式** | 两种视图，`↑↓ Enter ESC` 导航 | 同视图三档 `Ctrl+E / Ctrl+F` 即切 |
| **信息密度** | 面板行固定格式；详情页完整 | 按需调整（compact → verbose）|

**判断**：**Qwen 的"按键即切档"在这个维度超越 Claude**。`useKeypress` 注册全局快捷键，无需离开当前上下文。

### 3. 权限审批路由

| | Claude Code | Qwen Code |
|---|---|---|
| **机制** | Task 工具内**黑盒**（主 agent 等待）；Coordinator 独立审批流 | `focusedSubagentRef` 焦点锁，一等公民 |
| **并发体验** | 无明确排队机制，多 subagent 权限竞争 | **串行化轮转**，其他 subagent 显式 `⏳ Waiting...` |

**判断**：Qwen 的并发审批 UX 更清晰——用户始终知道"现在处理 B，A/C 等着"。

---

## 六、Qwen Code 借鉴 Claude 的 3 个机会

### 🥇 优先级 1：真正后台并发 + TTL 驱逐

**Claude 源码**：
- `CoordinatorAgentStatus.tsx:45-63` —— 1s tick 驱动 elapsed + 驱逐
- `TaskListV2.tsx:21` —— `RECENT_COMPLETED_TTL_MS = 30_000`
- `tasks/LocalAgentTask/LocalAgentTask.js` —— 任务状态机

**Qwen 现状**：SubAgent 嵌入 tool 调用周期内，tool 返回 = subagent 结束。用户无法启动"长研究"后继续其他工作。

**借鉴路径**：
1. 新增 `LocalAgentTask` 数据结构（与 tool 解耦），持久到 `AppState.tasks`
2. 新增 `ui.backgroundAgentPanel: true` settings，启用时 footer 上方显示面板
3. `/agents --spawn "task" --background` 命令启动后台 subagent
4. 1s tick + `evictAfter`（默认 30s）驱逐已完成
5. `x` 键立即驱逐（`evictAfter = 0`）；`Enter` 进入详情视图

**成本**：~2-3 周。**难点**：主 loop 与后台 agent 的 AbortController 分离、消息流与后台 task 的同步、生命周期管理。

**价值**：长时任务"最小化 → 继续跑"体验，对 research / data analysis 场景极有价值。

---

### 🥈 优先级 2：`/agents` 独立管理视图（subagent 历史/归档）

**Claude 源码**：
- `components/agents/AgentsMenu.tsx` / `AgentsList.tsx` —— Agent 定义管理
- `components/agents/AgentDetail.tsx` / `AgentEditor.tsx` —— 查看/编辑
- `components/agents/new-agent-creation/CreateAgentWizard.tsx` + 10 个 wizard step —— 创建向导

**Qwen 现状**：subagent 历史只能在消息流中找，无专用归档/对比视图。

**借鉴路径**：
1. `/agents` 命令打开独立菜单（agent 定义管理已有基础？需要确认）
2. `/agents --history` 列出最近 N 个 subagent 运行（按时间 / 按 agent name 过滤）
3. 详情视图支持对比（两次运行的 tool 列表 diff）

**成本**：~1-1.5 周。**前置**：是否已有 agent 定义管理（Qwen 的 `subagents/` 目录）。

**价值**：中等——补齐 subagent "历史追溯"能力。

---

### 🥉 优先级 3：Coordinator 协调器面板（footer 上方）

**Claude 源码**：`CoordinatorAgentStatus.tsx` 整体 + `coordinator/coordinatorMode.ts`

**Qwen 现状**：Arena 偏"比赛"（多个 agent 独立跑同一 prompt 比结果），无"团队管理"视图。

**借鉴路径**：
1. Footer 上方渲染 `CoordinatorTaskPanel`（依赖优先级 1 的 LocalAgentTask）
2. `↑↓` 导航多个后台 subagent，`Enter` 进入详情，`x` 驱逐
3. 每行展示 `agent_name · status · elapsed · tokens`

**成本**：~3-5 天（前置优先级 1 完成后）。

**价值**：中等——并发 subagent 场景的"协同视角"，与优先级 1 互补。

---

## 七、Claude Code 可借鉴 Qwen 的 3 个机会（反向）

### 1. Ctrl+E / Ctrl+F 三档展示切换

**Qwen 源码**：`AgentExecutionDisplay.tsx:124-140`

**价值**：Claude Task 工具当前固定格式，加入按键切档能极大提升信息密度调节能力。

### 2. 焦点锁并发审批

**Qwen 源码**：`ToolGroupMessage.tsx:99-123, 256-287`

**价值**：Claude 多 subagent 触发审批时目前无明确排队机制，焦点锁可大幅改善 UX。

### 3. 执行摘要 4 行信息长期保留

**Qwen 源码**：`AgentExecutionDisplay.tsx:464-526`

**价值**：Claude Coordinator 30s 驱逐太激进——用户 30s 后无法回顾刚完成的任务。保留摘要行（不保留全部 tool list）是折中方案。

---

## 八、相关追踪 item

| item | 方向 | 状态 |
|---|---|---|
| [item-56](./qwen-code-improvement-report-p2-stability.md#item-56)（本次新增）| 真正后台并发 + TTL 驱逐 | 新增 |
| [item-57](./qwen-code-improvement-report-p2-stability.md#item-57)（本次新增）| `/agents` 独立管理视图 | 新增 |
| [item-58](./qwen-code-improvement-report-p2-stability.md#item-58)（本次新增）| Coordinator 协调器面板 | 新增 |
| [p0-p1-engine item-14](./qwen-code-improvement-report-p0-p1-engine.md#item-14) | Coordinator/Swarm 多 Agent 编排 | PR#3433 ⚠️ 已 revert |

---

## 九、关键文件速查表

| 技术 | Claude Code | Qwen Code |
|---|---|---|
| Coordinator 面板 | `components/CoordinatorAgentStatus.tsx:34-76` | 无 |
| Agent 任务状态 | `tasks/LocalAgentTask/LocalAgentTask.js` | `AppState` 内嵌 |
| TTL 驱逐 | `TaskListV2.tsx:21` `RECENT_COMPLETED_TTL_MS = 30_000` | 无 |
| 驱逐执行 | `utils/task/framework.js:evictTerminalTask` | 无 |
| Agent 进度行 | `components/AgentProgressLine.tsx` | 无对应 |
| `/agents` 菜单 | `components/agents/AgentsMenu.tsx` + 10 文件子目录 | 部分（`subagents/`）|
| 工具内联 | `tools/AgentTool/AgentTool.tsx` | `components/messages/ToolGroupMessage.tsx` |
| SubAgent 嵌入展示 | 无（Task 工具简洁展示）| `components/subagents/runtime/AgentExecutionDisplay.tsx` |
| 三档切换 | 无 | `AgentExecutionDisplay.tsx:124-140` |
| 焦点锁 | 无 | `ToolGroupMessage.tsx:99-123` |
