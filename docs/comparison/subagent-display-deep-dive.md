# SubAgent 展示 Deep-Dive——Claude Code vs Qwen Code

> **核心问题**：Claude Code 和 Qwen Code 在运行 SubAgent 时的 UI 展示有何差异？各自的设计哲学与借鉴机会是什么？
>
> 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)
>
> **2026-05-02 重大更新**：本文写作于 2026-04 中旬时 Qwen Code SubAgent 还**仅有嵌入式展示**；2026-04-27 → 2026-05-02 在 ~6 天内合并了 **9 个 PR**（PR#3471/3488/3642/3684/3687/3720/3721/3771/3739），Qwen Code 现已**完整实现真正后台并发 + pill+dialog UI + background agent resume + Phase C event monitor**——把原"Qwen 借鉴 Claude 的 3 个机会"清单基本兑现，部分设计还**反超 Claude**。文末"八、相关追踪 item"的状态全部更新为 ✓ 已实现。

## 零、最新动态（2026-04-27 → 2026-05-02 · Background tasks roadmap #3634 三阶段全部落地）

> **Background tasks roadmap (#3634) 三阶段**：Phase A = 后台 subagents（PR#3076 早期合并）；Phase B = managed background shell pool（PR#3642 ✓）；**Phase C = event monitor tool**（PR#3684 ✓ 2026-05-02）。三阶段加上 PR#3471/3488 控制面 + UI、PR#3687/3720 整合、PR#3739 resume 后形成**完整的多模态后台任务调度系统**。

| PR | 合并时间 | 内容 | 影响章节 |
|---|---|---|---|
| [PR#3471](https://github.com/QwenLM/qwen-code/pull/3471) | 2026-04-27 | 模型侧控制面：`task_stop` / `send_message` / per-agent transcript 工具 | §六.1 |
| [PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) | 2026-04-28 | UI 层：background-agent **pill**（状态行运行计数）+ **combined dialog**（Down 键打开）+ **detail view**（Enter 进详情）+ **cancel flow**（`x` 键）+ 4 状态分类（Running/Completed/Failed/Cancelled） | §六.1 / §六.3 |
| [PR#3642](https://github.com/QwenLM/qwen-code/pull/3642) | 2026-04-28 | **Phase B**：`/tasks` 命令 + managed background shell pool（+1025/-411），把后台 shell 也纳入统一调度 | §六.1 |
| [PR#3687](https://github.com/QwenLM/qwen-code/pull/3687) | 2026-04-29 | 后台 shell 接入 `task_stop` 工具，控制语义统一 | §六.1 |
| [PR#3720](https://github.com/QwenLM/qwen-code/pull/3720) | 2026-04-29 | **后台 shell 与 SubAgent 合并到统一 Background tasks dialog** —— 跨 Claude 设计 | §六.1 / 反超点 |
| [PR#3721](https://github.com/QwenLM/qwen-code/pull/3721) | 2026-04-29 | `fix(cli): bound SubAgent display by visual height to prevent flicker` (+1336/-57) | §五.2 显示稳定 |
| [PR#3771](https://github.com/QwenLM/qwen-code/pull/3771) | 2026-04-30 | `fix(cli): restore SubAgent shortcut focus` —— 焦点锁微调 | §五.3 |
| [PR#3739](https://github.com/QwenLM/qwen-code/pull/3739) | 2026-05-01 | **`Add background agent resume and continuation`**（**+4087/-165**）—— `BackgroundAgentResumeService` + paused 生命周期 + transcript-first fork resume + `SubagentStart` hook 重放 | §六 反超点（Claude 没有）|
| [PR#3684](https://github.com/QwenLM/qwen-code/pull/3684) | 2026-05-02 | **Phase C event monitor tool**（**+6297/-147 系列追踪以来最大单 PR**）—— 新增 `Monitor` 工具 spawn 长跑 shell 命令 + token-bucket 节流（burst=5/sustain=1/sec）把 stdout lines 作为事件返回 agent；`MonitorRegistry`（4 状态 + idle timeout + max events 自动停 + 独立 AbortController）；shell 层 sleep 拦截（前台 `sleep N`(N≥2) 阻塞并提示模型用 Monitor 或 `is_background`）。**设计上与 background subagents（Phase A）同构**：独立 AbortController（Ctrl+C 不杀 monitor）+ stdout/stderr 分离 + `<task-notification><kind>monitor</kind>` XML 信封 | §六.5 新增 |
| [PR#3784](https://github.com/QwenLM/qwen-code/pull/3784) | 2026-05-02 | Phase C 配套 Windows taskkill 兼容修复（+15/-18） | 配套 |

**关键 OPEN（追踪中）**：

| PR | 方向 |
|---|---|
| **[PR#3791](https://github.com/QwenLM/qwen-code/pull/3791)** 🟡 OPEN（2026-05-02 14:32 UTC，+357/-40 / 8 文件） | **`feat(cli): wire Monitor entries into combined Background tasks dialog`** —— 直接对应 PR#3684 自述的"未做"清单第 1 项。结构上是 PR#3720 的 Monitor 镜像版（kind framework 的第三个消费者：agent / shell / **monitor**）。**Before**：pill 只显示 `1 shell, 1 local agent`，monitor 不可见；**After**：`1 shell, 1 local agent, 2 monitors`，全部终止后塌陷为 `N tasks done`。Overlay 单 Background tasks 区域含三类，monitor 行前缀 `[monitor] <description>`；detail view 按 kind 派发新增 `MonitorDetailBody`（command / status / pid / event count / dropped lines）；`x` 键路由到 `monitorRegistry.cancel(monitorId)`（同步 settle，与 `task_stop` 的 monitor 路径一致）。**Core 改动**：`MonitorRegistry.setStatusChangeCallback` 镜像 `BackgroundShellRegistry` / `BackgroundTaskRegistry`。**意义**：验证 PR#3488 / PR#3720 引入的 kind framework 是真正 cross-kind 的 |
| [PR#3768](https://github.com/QwenLM/qwen-code/pull/3768) | route foreground subagents through pill+dialog while running —— 把前台 subagent 也接入 pill+dialog，与已合并的后台路径形成对偶 |
| [PR#3735](https://github.com/QwenLM/qwen-code/pull/3735) | auto-compact subagent context to prevent overflow —— subagent 上下文溢出前自动压缩 |
| ❌ monitor → `send_message` 集成 | PR#3684 自述"未做"清单第 2 项 —— `task_stop` 集成已经在 PR#3791 中完成（`x` 键路由 + `task_stop` 同步），但 `send_message` 暂未对接 |

---

## 一、两条不同的 UI 哲学

### Claude Code = 双模式
1. **Task 工具内联模式**（`AgentTool.tsx`）——主消息流内展示，完成即收
2. **Coordinator 后台面板**（`CoordinatorAgentStatus.tsx`）——独立 footer 上方常驻面板，多 agent 并发，30s TTL 自动驱逐

### Qwen Code = 双模式（2026-04-28 起）
1. **嵌入式 `AgentExecutionDisplay.tsx`**（原有）—— 作为工具结果嵌入消息流，三档可折叠展示（compact / default / verbose），Ctrl+E / Ctrl+F 切换
2. **Background tasks 调度面**（PR#3471/3488/3642 新增）—— 状态行 `BackgroundTasksPill` + 按 Down 键打开 `BackgroundTasksDialog` + Enter 进详情 + `x` 取消；**SubAgent 与后台 shell 共用同一调度面**

> **设计差异**：Claude footer 上方**常驻面板**（任何时候都能看见），Qwen 状态行**pill 提示 + 按需打开对话框**（默认折叠节省屏幕空间）。两种 UX 偏好不同：Claude 偏"持续可见"，Qwen 偏"需要时才占空间"。

---

## 二、逐维度对比

| 维度 | Claude Code | Qwen Code |
|---|---|---|
| **发起展示** | Task：内联 `⏺ Task(...)` ⎿ 摘要<br>Coordinator：footer 上方常驻面板 `◯ name · ▶ 0s` | 嵌入：工具组 `├─ agent_name ● Running`<br>**Background：状态行 pill + Down 键打开 dialog**（PR#3488）|
| **SubAgent 身份** | `AgentProgressLine.tsx:75` 彩色背景标签 | `AgentExecutionDisplay.tsx:148` 彩色 `agentColor` + StatusDot |
| **执行中实时性** | Task：spinner + 最终结果<br>Coordinator：仅最后一个工具 + 计数（1s tick）| 嵌入：**完整工具列表**（默认最后 5 个，verbose 全部）<br>**Dialog：Running/Completed/Failed/Cancelled 4 类状态**（PR#3488）|
| **展示模式切换** | Task 固定；Coordinator `↑↓`+Enter 导航 | 嵌入：**Ctrl+E / Ctrl+F 三档切**（compact ↔ default ↔ verbose）<br>Dialog：`↑↓` 导航 + Enter 进详情 + Left/Esc 关闭 |
| **并发布局** | Coordinator 垂直列表 `◯ A / ◯ B / ◯ C` | 嵌入：同工具组内 `.map()` 渲染<br>**Dialog：列表视图 + per-agent rolling tool activity buffer**（PR#3488）|
| **权限审批路由** | Task 内部黑盒；Coordinator 独立流 | **焦点锁**（`focusedSubagentRef` + `isWaitingForOtherApproval`）|
| **完成后摘要** | `RECENT_COMPLETED_TTL_MS = 30_000` 自动驱逐 | 嵌入：4 行执行摘要长期保留<br>**Dialog：完成后保持可见，用户主动管理**（与 Claude 不同选择，PR#3488）|
| **失败处理** | Coordinator `✕ Failed (Ns ago)` → 30s 后驱逐 | 嵌入：红色 `├─ ✕ Failed` 永久保留<br>**Dialog：4 状态分类 Running/Completed/Failed/Cancelled，明确区分非 GOAL 终止**（PR#3488）|
| **独立管理视图** | `/agents` + `AgentsMenu` / `AgentsList`（agent 定义）| `/tasks` 命令 + dialog（PR#3642，运行时管理）|
| **后台并发能力** | ✅ 真后台（`evictAfter` 驱动，独立 loop） | **✅ 真后台**（PR#3471 `task_stop` / `send_message` / per-agent transcript 控制面 + PR#3488 UI）|
| **后台 shell 与 SubAgent 调度面** | **分离**（BashOutput / Background shells 与 Coordinator panel 独立）| **统一**（PR#3720 把后台 shell + SubAgent 合并到同一 dialog · pill / 导航 / 详情视图共用）—— **超越 Claude** |
| **agent resume / continuation** | ✅ `tools/AgentTool/resumeAgent.ts:resumeAgentBackground()` | **✅ + transcript-first fork resume**（PR#3739 +4087/-165 · `BackgroundAgentResumeService` + paused 生命周期 + `SubagentStart` hook 重放）—— **比 Claude 更稳健** |
| **取消语义** | `x` 立即驱逐 | `x` 取消 + 状态变为 Cancelled（PR#3488 区分"取消"与"驱逐"）|

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

> **范围说明**：以下场景描述 Qwen Code **嵌入式** SubAgent 模式（`AgentExecutionDisplay`），不涉及 2026-04-28 后新增的 **Background tasks dialog**（`BackgroundTasksPill` + `BackgroundTasksDialog`）。两种模式当前并存——短任务走嵌入式（看到完整工具时间轴），长跑/后台任务走 dialog（pill 显示运行计数 + 按 Down 键打开 dialog）。

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

> **2026-05-02 更新**：Qwen 在 2026-04-27 → 2026-05-01 的 5 天内通过 6 个 PR 实现了真后台并发，本表的"Qwen Code"列已分成"嵌入式（原有）"和"Background tasks 调度面（新增）"两栏。

| | Claude Code | Qwen Code 嵌入式（原有）| Qwen Code Background tasks（PR#3471/3488/3642）|
|---|---|---|---|
| **模型** | Coordinator = footer 上方常驻面板（`AppState.tasks` 独立于主 loop，1s tick）| subagent 作为 tool result 在消息流内 | 状态行 pill + 按需打开 dialog（`task_stop` / `send_message` 控制面）|
| **生命周期** | `evictAfter` 时间戳控制可见性，30s TTL 自动驱逐 | 随消息树追加，tool 调用结束 = subagent 结束 | **保持可见，用户主动 `x` 取消**（4 状态：Running/Completed/Failed/Cancelled）|
| **能力** | 支持"最小化继续运行" | 必须在 tool 周期内完成（适合短任务）| **支持"最小化继续运行" + transcript-first fork resume**（PR#3739）|
| **代价** | AppState 内存占用 | 消息流可能变长 | dialog 状态需用户主动管理 |

**结论**：Qwen 现在**两种模式并存**——短任务嵌入消息流（用户能看到完整工具列表），长任务进入 background dialog（不阻塞主交互流）。这比 Claude 的"Task 内联 / Coordinator 独立"二分更灵活。

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

## 六、Qwen Code 已落地的 5 项 + 2 项反超 Claude

> **本节状态变化（2026-04 → 2026-05）**：原本列出 3 个"待借鉴机会"，到 2026-05-02 全部已通过 9 个 PR 落地，外加 Qwen 自己**新增了 2 个 Claude 没有的设计**（统一调度面 + transcript-first fork resume）+ Phase C event monitor tool。

### 🥇 已落地 1：真正后台并发 + UI 调度面（PR#3471/3488/3642）✓

**Claude 源码**：
- `CoordinatorAgentStatus.tsx:45-63` —— 1s tick 驱动 elapsed + 驱逐
- `TaskListV2.tsx:21` —— `RECENT_COMPLETED_TTL_MS = 30_000`
- `tasks/LocalAgentTask/LocalAgentTask.js` —— 任务状态机

**Qwen 落地状态**：

| 层 | PR | 实现 |
|---|---|---|
| 模型侧控制面 | [PR#3471](https://github.com/QwenLM/qwen-code/pull/3471) ✓ 2026-04-27 | `task_stop` / `send_message` / per-agent transcript 工具，对标 Claude `TaskStop` / `SendMessage` |
| UI 层 | [PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) ✓ 2026-04-28 | `BackgroundTasksPill`（状态行运行计数）+ `BackgroundTasksDialog`（Down 键打开）+ detail view（Enter 进详情）+ cancel flow（`x` 键）+ Running/Completed/Failed/Cancelled 4 状态 |
| `/tasks` 命令 + shell pool | [PR#3642](https://github.com/QwenLM/qwen-code/pull/3642) ✓ 2026-04-28 | managed background shell pool + `/tasks` 命令（CLI 入口）|

**与 Claude 的设计差异**：
- Claude **footer 上方常驻面板**；Qwen **状态行 pill + 按需打开 dialog**（默认折叠节省屏幕空间）
- Claude **30s TTL 自动驱逐已完成**；Qwen **保持可见，用户主动管理 + `x` 显式取消变为 Cancelled**
- Claude 4 状态：running / completed（隐式 success / failure）；Qwen **明确 4 类**：Running / Completed / Failed / Cancelled（区分非 GOAL 终止）—— **比 Claude 更显式**

**3 项超出 Claude 的设计**（PR#3488）：
1. ✨ **4 类状态分类**：明确区分 timeout / max-turn / errors 为 Failed
2. ✨ **per-agent rolling tool activity buffer**（feeds detail view Progress section）
3. ✨ **原始 prompt 保存到 detail view**（用户能看自己最初指令）

---

### 🥈 已落地 2：后台 shell 与 SubAgent 统一调度面（PR#3687/3720）✓ **超越 Claude**

**Claude 设计**：BashOutput / Background shells 与 Coordinator panel 是**两套相对独立的 UI** —— 用户视角下"后台 shell"和"后台 agent"是不同 mental model。

**Qwen 选择把它们合并**：

| PR | 层 | 内容 |
|---|---|---|
| [PR#3687](https://github.com/QwenLM/qwen-code/pull/3687) ✓ 2026-04-29 | 控制层 | 后台 shell 也接入 `task_stop` 工具，模型用单一动作能停 SubAgent + shell |
| [PR#3720](https://github.com/QwenLM/qwen-code/pull/3720) ✓ 2026-04-29 | UI 层 | 后台 shell 与 SubAgent 在 dialog 中合并（统一 pill / 统一导航 / 统一详情视图） |

**意义**：用户视角下"后台任务"是**单一 mental model**——不需要区分"是 shell 还是 agent"。这是 Qwen Code 团队**对 Claude 设计的一次有意识改进**。

---

### 🥉 已落地 3：background-agent resume + continuation（PR#3739）✓ **比 Claude 设计更稳健**

**Claude 源码**：`tools/AgentTool/resumeAgent.ts:resumeAgentBackground()`

**Qwen 落地**（[PR#3739](https://github.com/QwenLM/qwen-code/pull/3739) ✓ 2026-05-01 · **+4087/-165 单 PR 体量爆表**）：

| 能力 | 实现 |
|---|---|
| 持久化发现 | `BackgroundAgentResumeService` 扫描 `subagents/<sessionId>/` |
| 生命周期 | sidecar metadata 记录 `paused` 状态 + registry/UI 表现 |
| **Transcript-first fork resume** | fork bootstrap 写入 `system/agent_bootstrap` + 原始 launch prompt 写入 `system/agent_launch_prompt`，resume 时**从 transcript 历史重建 worker context** 而非从当前父 prompt/tool 状态重建 |
| Hook 重放 | resume 时**重新跑 `SubagentStart` hooks** + 并发 resume 自动 coalesce |
| 控制面 | `send_message` + `task_stop` 处理 paused background agent |
| UI | `/resume` 流程加载 paused tasks + 瞬态恢复提示 |
| 兼容兜底 | 无 bootstrap 记录的 legacy fork transcript 仍可见为 paused 并 abandonable，但**禁止 unsafe resume** |

**比 Claude 更稳健的点**：transcript-first fork resume 避免了父 prompt 漂移导致 fork worker context 重建错误——在多步 agent 链场景下显著降低恢复时的状态污染风险。

---

### 已落地 4：显示稳定性（PR#3721）✓

[PR#3721](https://github.com/QwenLM/qwen-code/pull/3721) ✓ 2026-04-29（+1336/-57）—— `bound SubAgent display by visual height to prevent flicker`。补足并发 subagent 长输出场景下的渲染稳定性。

---

### 已落地 5：Phase C event monitor tool（PR#3684）✓ 系列追踪以来最大单 PR

[PR#3684](https://github.com/QwenLM/qwen-code/pull/3684) ✓ 2026-05-02 12:57 UTC（**+6297/-147**）—— `feat(core): event monitor tool with throttled stdout streaming (Phase C)`。这是 Background tasks roadmap (#3634) 的第三阶段，与已合并的 Phase A（后台 subagents）+ Phase B（PR#3642 background shell pool）形成完整三件套。

**新增能力**：

| 组件 | 实现 |
|---|---|
| **`Monitor` 工具** | spawn 长跑 shell 命令 + **token-bucket 节流**（burst=5, sustain=1/sec）把 stdout lines 作为**事件**返回给 agent |
| **`MonitorRegistry`** | 4 状态生命周期（running/completed/failed/cancelled）+ idle timeout 自动停 + max events 自动停 + 独立 `AbortController`（Ctrl+C 不杀 monitor）|
| **shell 层 sleep 拦截** | 前台 `sleep N`(N≥2) 被阻塞 + 提示模型用 Monitor 或 `is_background` |
| **事件传输** | 复用 `<task-notification><kind>monitor</kind>` XML 信封 |
| **CLI wiring** | 同时覆盖 interactive (`useGeminiStream.ts`) + headless (`nonInteractiveCli.ts`) 路径 |

**与 Background subagent (Phase A) 的同构性**：

| 维度 | Phase A subagent | Phase C monitor |
|---|---|---|
| 独立 AbortController | ✓ | ✓ |
| stdout/stderr 分离 buffer | ✓ | ✓ |
| 4 状态生命周期 | ✓ | ✓ |
| `<task-notification>` 信封 | ✓（`<kind>subagent</kind>`）| ✓（`<kind>monitor</kind>`）|
| Idle/timeout 自动停 | partial | ✓ |

**未做项追踪**（PR#3684 自述清单的当前状态）：

| 未做项 | 状态 | 备注 |
|---|---|---|
| Footer pill / dialog 集成 | 🟡 **PR#3791 OPEN（2026-05-02 14:32 UTC）正在做** | +357/-40 · 8 文件 · 直接镜像 PR#3720（agent/shell→monitor 是 kind framework 第三个消费者）|
| `task_stop` 集成 | 🟡 **PR#3791 顺便覆盖** | `x` 键路由到 `monitorRegistry.cancel()`，同步 settle 与 `task_stop` 的 monitor 路径一致 |
| `send_message` 集成 | ❌ 仍缺 | 当前未在 PR#3791 范围内 |

PR#3791 合并后，monitor 将与 subagent / background shell 共享同一个 pill+dialog 调度面 —— 这将**完成 Phase C 与 PR#3471/3488 调度面的全部对接**，验证 kind framework 真正 cross-kind。

---

### 还有什么可以做？（剩余 gap）

虽然主体已落地，仍有 2 个值得追踪的方向：

1. **前台 subagent 也接入 pill+dialog**：[PR#3768](https://github.com/QwenLM/qwen-code/pull/3768) 🟡 OPEN —— 让前台 subagent 也用统一 UI，与已合并的后台路径形成对偶
2. **subagent 上下文自动压缩**：[PR#3735](https://github.com/QwenLM/qwen-code/pull/3735) 🟡 OPEN —— 防止长跑 subagent 上下文溢出
3. **`/agents --history` 归档对比视图**：当前 `BackgroundTasksDialog` 偏运行时管理；历史归档 + 对比 diff 仍未实现

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

| item | 方向 | 状态（2026-05-02 更新）|
|---|---|---|
| [item-56](./qwen-code-improvement-report-p2-stability.md#item-56) | 真正后台并发 + TTL 驱逐 | **✓ 已实现**（PR#3471 + PR#3488 + PR#3642 + PR#3687 + PR#3720 共 5 件套，且超出 Claude 设计）|
| [item-57](./qwen-code-improvement-report-p2-stability.md#item-57) | `/agents` 独立管理视图 | 🟡 部分（`/tasks` 命令 + dialog 已有运行时管理；历史归档/对比 diff 仍缺）|
| [item-58](./qwen-code-improvement-report-p2-stability.md#item-58) | Coordinator 协调器面板 | **✓ 已实现**（PR#3488 pill + combined dialog + detail view，与 Claude footer 常驻面板设计取舍不同）|
| [item-18](./qwen-code-improvement-report-p0-p1-engine.md#item-18) | Agent 恢复与续行 | **✓ 已实现**（PR#3739 +4087/-165，transcript-first fork resume 比 Claude 更稳健）|
| [p0-p1-engine item-14](./qwen-code-improvement-report-p0-p1-engine.md#item-14) | Coordinator/Swarm 多 Agent 编排 | 🟡 持续推进（PR#3433 ⚠️ revert，但 PR#3471/3488 已落地控制面 + UI）|

---

## 九、关键文件速查表（2026-05-02 更新）

| 技术 | Claude Code | Qwen Code |
|---|---|---|
| Coordinator/后台面板 | `components/CoordinatorAgentStatus.tsx:34-76`（footer 上方常驻）| **`packages/cli/src/ui/components/background-view/BackgroundTasksPill.tsx`**（状态行 pill）+ **`BackgroundTasksDialog.tsx`**（按需打开 dialog）|
| Agent 任务状态 | `tasks/LocalAgentTask/LocalAgentTask.js` | **`packages/cli/src/ui/contexts/BackgroundTaskViewContext.tsx`** + **`hooks/useBackgroundTaskView.ts`** |
| 模型侧控制工具 | `tools/TaskStop/TaskStopTool.ts` + `tools/SendMessage/SendMessageTool.ts` | **`packages/core/src/tools/agent/agent.ts`** 暴露 `task_stop` / `send_message` / per-agent transcript（PR#3471）|
| TTL 驱逐 | `TaskListV2.tsx:21` `RECENT_COMPLETED_TTL_MS = 30_000`（自动驱逐）| **保持可见，用户主动 `x` 取消**（PR#3488 设计差异）|
| 驱逐执行 | `utils/task/framework.js:evictTerminalTask` | dialog 内 `x` 键路由到 `task_stop` 工具 |
| Agent 进度行 | `components/AgentProgressLine.tsx` | dialog 内 list item + per-agent rolling tool activity buffer（PR#3488）|
| `/agents` 菜单 | `components/agents/AgentsMenu.tsx` + 10 文件子目录（agent 定义管理）| **`/tasks` 命令**（运行时管理，PR#3642）+ subagent 定义在 `subagents/` 目录 |
| 工具内联 | `tools/AgentTool/AgentTool.tsx` | `components/messages/ToolGroupMessage.tsx` |
| SubAgent 嵌入展示 | 无（Task 工具简洁展示）| `components/subagents/runtime/AgentExecutionDisplay.tsx` |
| 三档切换 | 无 | `AgentExecutionDisplay.tsx:124-140` |
| 焦点锁 | 无 | `ToolGroupMessage.tsx:99-123` + PR#3771 修复 |
| `/tasks` 命令 | 无（Claude 没有这个 CLI 入口）| **`packages/cli/src/ui/commands/tasksCommand.ts`**（PR#3642 · 显示 BackgroundShellEntry 状态）|
| Background agent resume | `tools/AgentTool/resumeAgent.ts:resumeAgentBackground()` | **`BackgroundAgentResumeService`**（PR#3739 +4087/-165）+ transcript-first fork resume + `system/agent_bootstrap` + `system/agent_launch_prompt` |
