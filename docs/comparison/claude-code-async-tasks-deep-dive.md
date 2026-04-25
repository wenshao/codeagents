# Claude Code 异步任务深度分析 — 后台 Shell + Monitor

> **核心问题**：状态条上的 `1 shell, 1 monitor` 是什么？为什么只有 Claude Code 把"agent 异步任务"做成了一等公民？
>
> **结论先行**：Claude Code v2.1.120 把"agent 在后台还在干活"产品化为**两类计数 + 统一管理 UI + 通知机制**三件套。Qwen Code / OpenCode 都缺这套——后台 bash 只是工具的副作用，没有可见性也没有管理入口。

## 一、状态条上的 `1 shell, 1 monitor`

实测一个会话同时跑后台 bash + Monitor：

```
✻ Sautéed for 37s · 1 shell, 1 monitor still running          ← 每 turn 状态行
──────────────────────────────────────────────────────────────
❯
──────────────────────────────────────────────────────────────
  /tmp/cc-bg-test
  ⏵⏵ auto mode on · 1 shell, 1 monitor                         ← Footer 第二行
```

两个数字含义：

| 计数 | 来源 | 何时出现 |
|---|---|---|
| `N shell` | 后台 Bash 进程数 | 任意 `Bash(..., run_in_background: true)` |
| `N monitor` | 活跃 Monitor 工具实例数 | LLM 调用 `Monitor` 工具 |

实测原文件：[`screenshots/claude-code-bg-tasks-90x35.txt`](./screenshots/claude-code-bg-tasks-90x35.txt)

## 二、两类后台任务的差异

### Shell（后台 Bash）

来自 `Bash` 工具 + `run_in_background: true`，本质是**子进程托管**。常用场景：

- Dev 服务器：`npm run dev` / `vite` / `webpack --watch`
- 文件 watch：`tail -f` / `inotifywait -m`
- 长任务：`pytest` / `cargo build`

实测调用：

```
● Bash(tail -f /tmp/.../watched.log)
  ⎿ Running in the background (↓ to manage)

● Started tail -f /tmp/.../watched.log in the background (ID: b64zw7iij). 
  It will keep running and capture any lines appended to the file.
```

特征：
- **完成时单次通知**：agent 收到 `<task-notification>` `status: completed`（含 exit code），但**不在通知里携带 stdout 内容**
- **stdout 落盘**：完整输出写到 session 临时目录下的 task 输出文件（agent 通过 `Read` 工具读取该路径）
- **磁盘上限 5 GB**（`MAX_TASK_OUTPUT_BYTES`），超限 SIGKILL
- **结束方式**：自然退出 / 用户 `x` 停 / agent `TaskStop(shell_id=...)`（含 `KillShell` 别名）

### Monitor（事件流监听）

来自 `Monitor` 工具，本质是**长期监听 + 推送通知**。常用场景：

- 监听日志错误：`tail -f log | grep ERROR`
- 监听文件变化：`inotifywait -m --format '%e %f' /watched/dir`
- 轮询远端：`while true; do gh api ...; sleep 30; done`
- WebSocket 监听器

实测调用：

```
● Monitor(ERROR lines in /tmp/.../watched.log)
  ⎿ Monitor started · task bd4lm9aqb · persistent

● Monitor armed (ID: bd4lm9aqb) — tail -F piped through grep --line-buffered "ERROR" 
  on /tmp/.../watched.log. Each ERROR line that appears will arrive as a notification.
```

特征：
- **每事件通知**：每条 stdout 行的**内容直接进入 `<task-notification>`**（agent 不需另读文件）
- **200ms 内多行批量为一条通知**（"multiline output from a single event groups naturally"）
- **生命周期**：默认 `timeout_ms: 300000`（5 分钟）/ `persistent: true`（会话生命周期）
- **过量保护**：消息过多自动停止（避免 token 爆炸）
- **退出条件**：脚本自身 exit / timeout / `TaskStop(task_id=...)`

### 一表看清差异

| 维度 | Shell（Bash bg） | Monitor |
|---|---|---|
| 触发 | `Bash` + `run_in_background: true` | `Monitor` 工具 |
| 通知次数 | **1 次**（完成时，含 exit code） | **N 次**（每事件 1 条，200ms 批合） |
| stdout 内容 | 落盘到 task 输出文件，agent 用 `Read` 读 | 直接在 notification 里 |
| 生命周期默认 | 进程自然结束 | 5 分钟 timeout |
| 推送上限 | 仅完成 1 条 | 自动节流 + 过量自停 |
| 状态条计数 | `N shell` | `N monitor` |
| 终止 | `TaskStop(shell_id=...)` 或 `KillShell` 别名 | `TaskStop(task_id=...)` |

**关键洞察**：两者**都是 push 模式**，但 cardinality 不同——Shell 是"完成时通知一次"（适合 build / 测试），Monitor 是"每事件通知一次"（适合 watch / 日志监听）。这与 Monitor 工具描述里写的选择树一致：

> - **One**（"tell me when the server is ready / the build finishes"）→ use **Bash with `run_in_background`**
> - **One per occurrence, indefinitely** → Monitor with an unbounded command

## 三、状态条显示机制

Footer 的两行布局（v2.1.120）：

```
  /tmp/cc-bg-test                              ← Line 1: cwd
  ⏵⏵ auto mode on · 1 shell, 1 monitor         ← Line 2: mode + 异步任务计数
```

`auto mode on` 永久存在（除非用户切换），后续 `· 1 shell, 1 monitor` **按需附加**：

| 触发条件 | 显示 | 是否实测 |
|---|---|---|
| 无后台任务 | `⏵⏵ auto mode on (shift+tab to cycle)` | ✅ |
| 仅 1 个 bg shell | `⏵⏵ auto mode on · 1 shell` | ✅ |
| 都有 | `⏵⏵ auto mode on · 1 shell, 1 monitor` | ✅ |
| 仅 1 个 monitor | `⏵⏵ auto mode on · 1 monitor` | ⚠️ 推测（未单独测过纯 monitor） |
| 多个 | `⏵⏵ auto mode on · 3 shells, 2 monitors` | ⚠️ 推测（plurals 形式参考"2 active shells" UI 标题） |

每个 turn 完成后还有**内联状态行**：

```
✻ Cooked for 7s · 1 shell still running
✻ Sautéed for 37s · 1 shell, 1 monitor still running
```

这是回答用户后展示的 timing + 后台任务提醒——**用户看完 LLM 的回复，紧接着就被提醒"还有 N 个任务在后台"**。这种"双重提示"避免被忽视。

## 四、触发方式

### 1. LLM 显式 `run_in_background: true`

最常见——LLM 判断"这是个长任务"主动后台化：

```
Bash({
  command: "npm run dev",
  run_in_background: true
})
```

这适用于明显的长任务（dev server / watch / sleep）。

### 2. 命令在 `COMMON_BACKGROUND_COMMANDS` 列表中且超时

对于 `npm` / `node` / `python` / `cargo` / `make` / `docker` / `webpack` / `vite` / `jest` / `pytest` 这些常见长命令，**超时时自动转后台**——避免占用 agent 主线程。

源码引用：[04-tools.md#643-655](../tools/claude-code/04-tools.md)

### 3. Kairos 模式 15 秒自动后台化

`ASSISTANT_BLOCKING_BUDGET_MS = 15_000` —— **assistant 模式下任何前台 bash 跑超 15 秒，自动甩到后台**。对 LLM 的"前台等待预算"严格 15 秒，超时即解放 agent。

```
启动 Bash → 2 秒后显示进度（PROGRESS_THRESHOLD_MS）
            ↓
        15 秒后自动后台化（Kairos 模式）
            ↓
        移出前台，进入 shell pool，状态条 +1 shell
```

### 4. 用户 `Ctrl+B` 手动后台化

前台 bash 跑得久，用户想干别的——按 Ctrl+B 立刻后台化，主提示符可继续接收下一条 prompt。

## 五、管理 UI（`/tasks` / `/bashes` / `↓` 键）

### 列表视图

按 `↓` 键或输入 `/tasks`（别名 `/bashes`）：

```
  Background tasks
  2 active shells

  ❯ ERROR lines in /tmp/.../watched.log (running)        ← Monitor (高亮)
    tail -f /tmp/.../watched.log (running)                ← Shell

  ↑/↓ to select · Enter to view · x to stop · ←/Esc to close
```

UI 标题用 `2 active shells` 把两类**统称为 shell**（命名沿用——Monitor 内部就是包装的 shell pipeline，如下面 Monitor 详情里 Script 字段所示），但 Footer 状态条**精确分类**为 `1 shell, 1 monitor`——以 Footer 为准。

### Shell 详情

选中 bash bg 项按 Enter：

```
  Shell details

  Status:   running
  Runtime:  32s
  Command:  sleep 60

  Output:
  No output available

  ← to go back · Esc/Enter/Space to close · x to stop
```

显示运行时长 + 命令字符串 + 累积 stdout 输出（截断）。

### Monitor 详情

选中 Monitor 项：

```
  Monitor details

  Status:   running
  Runtime:  1m 27s
  Script:   tail -F /tmp/.../watched.log | grep --line-buffered "ERROR"

  Output:
  No output available
```

显示完整 monitor 脚本——Monitor 工具内部把 `tail -f log | grep ERROR` 包成完整 bash 命令再执行，所以 Script 字段是**最终展开的 shell 脚本**。

## 六、Monitor 的通知机制（agent 视角）

Monitor 的"每行 stdout = 一条聊天通知"是它独特的设计。从 agent 视角：

```
Monitor 启动 → agent 继续干别的事 → Monitor 检测到 ERROR 行
                                          ↓
                  注入 <system-reminder><task-notification>:
                  脚本 stdout 行内容直接进入通知正文
                                          ↓
                  agent 在下一轮看到通知 + 内容，决策是否响应
```

**与 Bash bg 的差别**：Bash bg 的完成通知**只携带 status/exit code**，stdout 全文落到 `tasks/<id>.output` 文件，agent 想看完整输出还要再调一次 `Read`。Monitor 把内容直接塞进通知——零额外读取。

实现细节（来自 Monitor 工具的描述）：

> Stdout lines within 200ms are batched into a single notification, so multiline output from a single event groups naturally.
>
> Monitors that produce too many events are automatically stopped; restart with a tighter filter if this happens.

工程细节（同样来自工具描述）：
- 使用 `grep --line-buffered` 强制行缓冲（否则 pipe 缓冲延迟分钟级）
- 失败容错：`curl ... || true` 防止单次请求失败杀掉整个 monitor
- 轮询间隔建议：本地 0.5-1s / 远端 30s+（API 速率限制）

## 七、与 Bash 前台/后台的关系

```
Bash 工具调用
    │
    ├─ run_in_background=true 显式
    │    或
    │   命令属 COMMON_BACKGROUND_COMMANDS 且超时
    │    或
    │   Kairos 15s 自动后台化
    │    或
    │   用户 Ctrl+B
    │       ↓
    │   进入 shell pool
    │   Footer 显示 +1 shell
    │   完成时收到 1 条通知（含 exit code）
    │   stdout 落 session 临时目录，用 Read 读
    │   通过 TaskStop(shell_id=id) 终止
    │
    └─ 默认前台
        ↓
       直接同步等待退出
       PROGRESS_THRESHOLD_MS=2s 后显示进度条
```

```
Monitor 工具调用
    │
    └─ 总是后台 + 推送式
        ↓
       进入 monitor pool
       Footer 显示 +1 monitor
       每行 stdout 推送通知给 agent
       通过 TaskStop(task_id=id) 终止
```

两个 pool 共享 `/tasks` 管理 UI，但状态条计数分类。

## 八、其他 Agent 的对应能力

| 能力 | Claude Code v2.1.120 | Qwen Code v0.15.2 | OpenCode v1.14.24 |
|---|---|---|---|
| 后台 Bash 进程 | ✅ `run_in_background` + 自动后台化 + Ctrl+B + shell pool + 输出落盘 | ⚠️ 仅 fork-and-detach（`shell` 工具的 `is_background: true`，源码: `tools/shell.ts#54`），**无 pool / 无输出收集** | ✗ `bash` 工具**无 background 参数**（源码: `tool/bash.ts#53-59`） |
| 后台 Subagent | ✅ `Agent(..., run_in_background: true)` + 完成通知 | ✅ [PR#3076](https://github.com/QwenLM/qwen-code/pull/3076)（已合并 2026-04-17）`Agent` 工具支持后台 + lifecycle 事件 + headless/SDK 一致 | ✗ 无 |
| Monitor / 事件流 | ✅ 独立 `Monitor` 工具 + 200ms 节流 + 过量自停 | ✗ 无 | ✗ 无 |
| 状态条计数 | ✅ `N shell, M monitor` 实时分类 | ⚠️ [PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) OPEN 中（仅 background **subagent** pill，不含 Bash bg） | ✗ 无 |
| 统一管理 UI | ✅ `/tasks`（`/bashes` 别名）+ `↓` 键 + Shell/Monitor 各有详情视图 | ⚠️ PR#3488 OPEN：combined dialog 仅含 subagent | ✗ 无任务面板 |
| 通知推送（事件 → LLM） | ✅ `<task-notification>` 系统消息注入（subagent + shell + monitor 全部） | ✅ subagent 完成通知（PR#3076）；Bash bg ✗ | ✗ |

**Claude Code 是目前唯一把"agent 异步任务"完整产品化的 agent**。

### Qwen Code 的相关 PR（精确状态）

[PR#3076](https://github.com/QwenLM/qwen-code/pull/3076) `feat: background subagents with headless and SDK support`（**已合并 2026-04-17**）—— 给 **`Agent` 工具**加了 `run_in_background: true`，子 agent 异步启动，完成时 lifecycle 事件作为通知发回父 agent。**这是 subagent 后台，不是 Bash 后台**。

[PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) `feat(cli): background-agent UI — pill, combined dialog, detail view`（**OPEN**）—— 给 PR#3076 的 background subagent 加 UI：状态行 pill 计数 + 组合 dialog + 单 agent 详情。**仍仅覆盖 subagent，不含 Bash bg / Monitor**。

Qwen Code 的 `shell` 工具早就有 `is_background: true` 参数（源码 `tools/shell.ts#54-80`），但只是在 Linux 上简单加 `&` 让命令 fork-and-detach——**没有 shell pool、没有输出收集、没有状态指示、没有 TaskStop**。等同于"裸 shell 的 `&`"，不是 Claude 那种产品化方案。

完整对标 Claude Code 至少需要：
1. **Bash bg pool**（重写 `shell.ts`，把 `&` 改成可追踪的子进程注册）—— 无 PR
2. **统一 background task 管理面板**（PR#3488 在做，但仅 subagent 部分）
3. **状态条分类计数**（PR#3488 仅 subagent pill）
4. **Monitor / 事件流工具**（最大缺口）—— **目前没有任何 PR 涉及**

## 九、为什么这套设计重要

### 用户视角：避免"agent 偷偷干活"焦虑

如果没有状态条提醒：
- 你以为对话结束 → 实际还有 dev server 占着 8080 端口
- 你 Ctrl+D 退出 → 后台 task 默默 leak 到 OS（孤儿进程）
- Monitor 突然弹通知 → 你不知道为什么

`1 shell, 1 monitor` 的可见性把"被动透明度"变成"主动感知"——这与软件工程里"用户应该能看到系统状态"的 [Heuristic Evaluation 第一条](https://www.nngroup.com/articles/ten-usability-heuristics/) 一致。

### Agent 视角：异步并发解锁更复杂的工作流

**Bash bg + Monitor 组合**可以构建：

```
1. 启动 dev server (Bash bg)
2. 启动 log monitor 监听 ERROR (Monitor)
3. 同时跑 typecheck + 测试（前台）
4. 任一时刻，monitor 推回 ERROR 通知 → agent 立刻调试
```

这种"agent 边写代码边监控"的模式在 Qwen Code 里**根本无法实现**——Qwen 的 `is_background: &` 是 fork-and-detach（无 stdout 收集、无生命周期管理），更别说事件推送。Monitor 的事件推送给了 agent "中断"概念，让 agent 有了"等待外部条件"的原语，这是 Claude Code 异步能力的核心壁垒。

### 实现视角：至少需要的核心组件

从外部行为反推（非源码确认），完整方案至少包含：

1. **Shell pool**：子进程注册表 + lifecycle 管理（PID / 输出文件路径 / kill handle）
2. **Monitor pool**：watch script 注册 + stdout 流式过滤 + 通知去抖（200ms 批合）
3. **状态条聚合器**：跨两个 pool 计数 → 渲染到 Footer 的 `· N shell, M monitor`
4. **管理 UI**：列表视图 + 详情视图（Shell 显示 Command/Runtime/Output；Monitor 显示完整 Script）
5. **通知注入器**：把 shell 完成事件 + monitor stdout 行包成 `<task-notification>` 注入下一轮 LLM context

任何 agent 想抄这套，5 个组件都需要。**Qwen Code 通过 PR#3076/#3488 在补 1 + 4 + 5（仅 subagent 路径）**，剩余的 Bash pool / Monitor / 完整状态条至今无 PR 推进。

## 十、源码分析（基于 leaked source）

源码位置：`/root/git/claude-code-leaked/`（v2.1.x 反混淆源码，1934 文件）。以下逐项给出文件 + 行号 + 关键代码。

### 10.1 核心数据模型

**`tasks/LocalShellTask/guards.ts#9-33`** —— Shell 与 Monitor 共用同一类型，只用 `kind` 字段区分：

```ts
export type BashTaskKind = 'bash' | 'monitor'

export type LocalShellTaskState = TaskStateBase & {
  type: 'local_bash' // Keep as 'local_bash' for backward compatibility with persisted session state
  command: string
  result?: { code: number; interrupted: boolean }
  shellCommand: ShellCommand | null
  isBackgrounded: boolean
  agentId?: AgentId
  // UI display variant. 'monitor' → shows description instead of command,
  // 'Monitor details' dialog title, distinct status bar pill.
  kind?: BashTaskKind
}
```

源码注释直接说明：**Monitor 是 `local_bash` 任务的 UI display variant**，差异在于：
1. 列表里显示 description 而非 command
2. 详情 dialog 标题是 "Monitor details"
3. 状态条 pill 单独计数

### 10.2 状态条文本生成

**`tasks/pillLabel.ts#11-30`** —— `getPillLabel` 函数同时被 Footer pill + 内联 turn duration 行调用：

```ts
export function getPillLabel(tasks: BackgroundTaskState[]): string {
  const n = tasks.length
  const allSameType = tasks.every(t => t.type === tasks[0]!.type)
  if (allSameType) {
    switch (tasks[0]!.type) {
      case 'local_bash': {
        const monitors = count(
          tasks,
          t => t.type === 'local_bash' && t.kind === 'monitor',
        )
        const shells = n - monitors
        const parts: string[] = []
        if (shells > 0)
          parts.push(shells === 1 ? '1 shell' : `${shells} shells`)
        if (monitors > 0)
          parts.push(monitors === 1 ? '1 monitor' : `${monitors} monitors`)
        return parts.join(', ')
      }
      // ... 其他 6 种 task type
    }
  }
  return `${n} background ${n === 1 ? 'task' : 'tasks'}`
}
```

源码确认了**单复数处理**（`shells` / `monitors`）以及**混合显示**（`1 shell, 1 monitor` 用 `, ` 拼接）。

### 10.3 完整的 7 种 background task 类型

`tasks/types.ts#13-21` + `pillLabel.ts` 定义了 **7 种 task 类型**（不只是 shell + monitor）：

| 类型 | 来源 | Footer pill 文案 |
|---|---|---|
| `local_bash` (kind='bash') | Bash 工具 + run_in_background | `N shell(s)` |
| `local_bash` (kind='monitor') | Monitor 工具 | `N monitor(s)` |
| `local_agent` | Agent 工具 + run_in_background | `N local agent(s)` |
| `remote_agent` | Cloud sessions | `N cloud session(s)`，ultraplan 用 `◆ ultraplan ready` / `◇ ultraplan needs your input` |
| `in_process_teammate` | TeamCreate / 多 agent 协同 | `N team(s)` |
| `local_workflow` | （独立工作流类型，PR 估计是 swarm 相关） | `N background workflow(s)` |
| `monitor_mcp` | （MCP server 监控，**与 Monitor 工具不同**） | `N monitor(s)` |
| `dream` | Auto Dream 系统 | `dreaming`（无计数，单飞模式） |

**注意**：`monitor_mcp` 和 `local_bash kind=monitor` 都显示 `N monitor`，但**底层是不同任务类型**——前者是 MCP 服务器健康监控，后者是 Monitor 工具实例。

源码：`tasks/pillLabel.ts#34-67`

### 10.4 Bash 工具的后台逻辑

**`tools/BashTool/BashTool.tsx`** 关键常量（行号实测）：

```ts
const PROGRESS_THRESHOLD_MS = 2000;            // #55
const ASSISTANT_BLOCKING_BUDGET_MS = 15_000;   // #57
const COMMON_BACKGROUND_COMMANDS = [           // #265
  'npm', 'yarn', 'pnpm', 'node', 'python', 'python3',
  'go', 'cargo', 'make', 'docker', 'terraform',
  'webpack', 'vite', 'jest', 'pytest',
  'curl', 'wget', 'build', 'test', 'serve', 'watch', 'dev',
] as const;
```

注：**实际 22 项**（之前 [04-tools.md 摘录](../tools/claude-code/04-tools.md#L651) 只列了 10 项），完整列表包括 `yarn / pnpm / python3 / go / terraform / curl / wget` 等。

**Kairos 自动后台化触发**（`BashTool.tsx#974-985`）：

```ts
// blocking commands after ASSISTANT_BLOCKING_BUDGET_MS so the agent can keep
if (feature('KAIROS') && getKairosActive() && isMainThread &&
    !isBackgroundTasksDisabled && run_in_background !== true) {
  // ... setTimeout(..., ASSISTANT_BLOCKING_BUDGET_MS).unref()
}
```

仅在 Kairos 模式开启 + 主线程 + 用户没显式 `run_in_background: true` 时才自动后台化。

**Sleep 拦截 + Monitor 推荐**（`BashTool.tsx#525-530`）—— 当 Bash 命令含 `sleep > 2s` 时 Claude 直接 **拒绝执行**并返回错误，提示用 Monitor：

```ts
if (feature('MONITOR_TOOL') && !isBackgroundTasksDisabled && !input.run_in_background) {
  // ... if (sleepPattern) return Blocked
  message: `Blocked: ${sleepPattern}. Run blocking commands in the background with 
  run_in_background: true — you'll get a completion notification when done. 
  For streaming events (watching logs, polling APIs), use the Monitor tool. 
  If you genuinely need a delay (rate limiting, deliberate pacing), keep it under 2 seconds.`
}
```

这是实际错误消息文本——LLM 在写 `sleep 60` 时会被这条消息引导改用 Monitor 或 `run_in_background: true`。

### 10.5 MAX_TASK_OUTPUT_BYTES 落盘上限

**`utils/task/diskOutput.ts#30`**：

```ts
export const MAX_TASK_OUTPUT_BYTES = 5 * 1024 * 1024 * 1024  // 5 GB
```

### 10.6 TaskStopTool（含 KillShell 别名）

**`tools/TaskStopTool/TaskStopTool.ts#11-18, #38-46`**：

```ts
const inputSchema = lazySchema(() =>
  z.strictObject({
    task_id: z.string().optional().describe('The ID of the background task to stop'),
    // shell_id is accepted for backward compatibility with the deprecated KillShell tool
    shell_id: z.string().optional().describe('Deprecated: use task_id instead'),
  }),
)

export const TaskStopTool = buildTool({
  name: TASK_STOP_TOOL_NAME,
  searchHint: 'kill a running background task',
  // KillShell is the deprecated name - kept as alias for backward compatibility
  // with existing transcripts and SDK users
  aliases: ['KillShell'],
  // ...
})
```

`shell_id` 仅用于兼容 KillShell 时代旧 transcript 重放，**新 SDK 应只用 `task_id`**。

### 10.7 Monitor 工具的 lazy 加载

**`tools.ts#39-40, #237`**：

```ts
const MonitorTool = feature('MONITOR_TOOL')
  ? require('./tools/MonitorTool/MonitorTool.js').MonitorTool
  : undefined
// ...
...(MonitorTool ? [MonitorTool] : []),  // 加入 tools 列表
```

Monitor 工具实现文件 `tools/MonitorTool/` 在 leaked source 中**未包含**（feature-gate 后的 dead code elimination 移除了），但通过 `feature('MONITOR_TOOL')` 调用证实它是 GrowthBook feature flag 控制的。

### 10.8 Footer pill 渲染

**`components/PromptInput/PromptInputFooterLeftSide.tsx#17`** 导入 `BackgroundTaskStatus`：

```ts
import { BackgroundTaskStatus } from '../tasks/BackgroundTaskStatus.js';
```

**`components/tasks/BackgroundTaskStatus.tsx#10, #25-92`** 调用 `getPillLabel` 渲染 mainPill + teammatePills（多 team 时叠加显示）。

### 10.9 BackgroundTasksDialog（`/tasks` 管理 UI）

**`components/tasks/BackgroundTasksDialog.tsx#409`** —— UI 标题：

```ts
{runningBashCount !== 1 ? 'active shells' : 'active shell'}
```

注意只有 `runningBashCount`（local_bash 总数，含 monitor），其他 task type 单独统计。

**#414** 列出所有支持的 task type 用于键盘快捷键 `x` 终止：

```ts
...((currentSelection?.type === 'local_bash' || 
     currentSelection?.type === 'local_agent' || 
     currentSelection?.type === 'in_process_teammate' || 
     currentSelection?.type === 'local_workflow' || 
     currentSelection?.type === 'monitor_mcp' || 
     currentSelection?.type === 'dream' || 
     currentSelection?.type === 'remote_agent') && 
    currentSelection.status === 'running' 
  ? [<KeyboardShortcutHint key="kill" shortcut="x" action="stop" />] : [])
```

7 种 task type 都支持 `x` 键停止。

### 10.10 ShellDetailDialog（同时承载 Shell + Monitor 详情）

**`components/tasks/ShellDetailDialog.tsx#164`** —— 动态 title：

```ts
const t9 = isMonitor ? "Monitor details" : "Shell details";
```

**#177, #193, #253** —— 渲染 `Status:` / `Runtime:` / `Output:` 三个字段——同一组件，按 `isMonitor` 切换 title 即可。

### 10.11 内联 turn 状态行的 source

**`components/messages/SystemTextMessage.tsx#508, #568`**：

```ts
// #508 — 计算 backgroundTaskSummary
return running.length > 0 ? getPillLabel(running) : null;

// #568 — 拼接 turn timing + bg summary
const t8 = backgroundTaskSummary && ` · ${backgroundTaskSummary} still running`;
//                                    ↑ 中点 ·
const t7 = showTurnDuration && `${verb} for ${duration}`;
// 渲染：<Text dimColor>{t7}{budgetSuffix}{t8}</Text>
//   →  ✻ Cooked for 7s · 1 shell, 1 monitor still running
```

`getPillLabel` 同时驱动 Footer pill 和这里的 turn-end 状态行——两处显示**保证一致**（同一函数）。

## 十一、二进制分析（v2.1.119）

二进制：`/root/.local/share/claude/versions/2.1.119`，245 MB ELF Linux x86-64，**not stripped**（保留符号表 + JS 源码字符串）。

### 11.1 验证 UI 字符串

```bash
strings 2.1.119 | grep -E "^(1 shell|1 monitor|Monitor details|Shell details)$"
```

输出：

```
1 shell
1 monitor
Monitor details
Shell details
```

✅ 4 个 UI 字符串在二进制里**精确存在**。"Monitor details" / "Shell details" 各出现 6 次（不同代码路径）。

### 11.2 Monitor 工具描述

二进制内可找到完整 Monitor 工具 schema：

```js
var mL="Monitor",wH6='Start a background monitor that streams events from a long-running script. ...'
```

这是 LLM 看到的 Monitor 工具描述源串——证明 Monitor 工具确实在二进制中（即便 leaked source 没有 `tools/MonitorTool/` 目录）。

### 11.3 验证 COMMON_BACKGROUND_COMMANDS

```bash
strings 2.1.119 | grep -E "^(yarn|pnpm|webpack|vite|terraform|cargo)$" | sort -u
```

输出：`cargo / pnpm / terraform / vite / webpack / yarn`——这些 22 项命令名都以独立字符串存在二进制里（minifier 不展开数组字面量字符串）。

### 11.4 minifier 损耗

源码常量名 `ASSISTANT_BLOCKING_BUDGET_MS` / `MAX_TASK_OUTPUT_BYTES` / `PROGRESS_THRESHOLD_MS` 在二进制中**已被 esbuild 内联展开为字面量值**（15000 / 5368709120 / 2000），所以 grep 找不到名字。但 source map 可还原（如果有的话），且实测行为完全吻合源码定义的数字。

## 十二、其他 5 种 task 类型详解

§10.3 给了 7 种 task type 的概览表。本节深入讲剩余 5 种（除 `local_bash` 的 shell + monitor 双形态外）的能力、触发场景、源码细节。

### 12.1 `local_agent`（后台 Subagent）

**触发**：Agent 工具 + `run_in_background: true`：

```ts
Agent({
  description: "Research X in parallel",
  prompt: "...",
  subagent_type: "researcher",
  run_in_background: true   // ← 不阻塞父 agent
})
```

**特征**（[`tasks/LocalAgentTask/LocalAgentTask.tsx#33-110`](file:/root/git/claude-code-leaked/tasks/LocalAgentTask/LocalAgentTask.tsx)）：

```ts
export type AgentProgress = {
  toolUseCount: number;       // 子 agent 调用了多少次工具
  tokenCount: number;         // 累积 token
  currentActivity?: string;   // 当前正在做的事
  // ...
}

export type LocalAgentTaskState = TaskStateBase & {
  type: 'local_agent';
  // 含 progress tracker，实时上报到父 agent
}
```

**实时进度回流**：子 agent 每个 tool 调用都更新父 agent 看到的进度。Footer pill 显示 `1 local agent`，详情 dialog（`AsyncAgentDetailDialog.tsx`）显示 token 消耗 + 工具活动时间轴。

**完成时**：子 agent 最终回答 + token 总量 + 耗时通过 `<task-notification>` 推回父 agent，父 agent 在下一轮 context 看到。

**典型场景**：并行研究多个独立子任务（每子 agent 一个 worktree）、长任务委派（让子 agent 慢慢跑而父 agent 继续 coordinate）。

### 12.2 `remote_agent`（Cloud Sessions）

**触发**：以下斜杠命令之一：
- `/autofix-pr <PR>` — 修 PR 测试 / lint 错误
- `/ultrareview <PR>` — 多 agent 云端 review
- `/ultraplan` — 长 plan 推理
- 其它 `RemoteTaskType`（源码 `RemoteAgentTask.tsx` 内 `REMOTE_TASK_TYPES` 数组）

**特征**（[`tasks/RemoteAgentTask/RemoteAgentTask.tsx#21-50`](file:/root/git/claude-code-leaked/tasks/RemoteAgentTask/RemoteAgentTask.tsx)）：

```ts
export type RemoteAgentTaskState = TaskStateBase & {
  type: 'remote_agent';
  remoteTaskType: RemoteTaskType;  // autofix-pr / ultrareview / ultraplan / ...
  sessionId: string;               // 远程 session ID
  command: string;
  title: string;
  todoList: TodoList;              // 子 todo 实时回流
  log: SDKMessage[];               // 远程 SDK 消息流（pollRemoteSessionEvents）
  isLongRunning?: boolean;
  pollStartedAt: number;           // 防 restore 时的时钟漂移
  isRemoteReview?: boolean;        // /ultrareview 标记
  reviewProgress?: {                // <remote-review-progress> 心跳解析
    stage?: 'finding' | 'verifying' | 'synthesizing';
    bugsFound: number;
    bugsVerified: number;
    bugsRefuted: number;
  };
}
```

**远程执行**：任务在 Anthropic Cloud 容器跑，本地 `pollRemoteSessionEvents` 每 N 秒拉事件回填 `todoList` + `log`。即使本地 Claude Code 进程退出，远程任务**仍继续**——下次启动可 resume。

**ultraplan 特殊视觉**：[`tasks/pillLabel.ts#36-50`](file:/root/git/claude-code-leaked/tasks/pillLabel.ts) 用菱形符号区分阶段：

```
remote_agent + ultraplanPhase === 'plan_ready'      → ◆ ultraplan ready
remote_agent + ultraplanPhase === 'needs_input'     → ◇ ultraplan needs your input
remote_agent + ultraplanPhase === undefined         → ◇ ultraplan
```

`◆` 实心 = 等用户审阅 plan；`◇` 空心 = 还在跑或等输入。

### 12.3 `in_process_teammate`（同进程 Team 成员）

**触发**：`TeamCreate` 工具创建 team，team 成员通过 team definition 启动；或者通过 `/tasks` 中的 `f` 键 foreground 进 teammate 视图。

**特征**（[`tasks/InProcessTeammateTask/types.ts#13-50`](file:/root/git/claude-code-leaked/tasks/InProcessTeammateTask/types.ts)）：

```ts
export type TeammateIdentity = {
  agentId: string;          // "researcher@my-team"
  agentName: string;
  teamName: string;
  parentSessionId: string;  // Leader's session ID
  planModeRequired: boolean;
}

export type InProcessTeammateTaskState = TaskStateBase & {
  type: 'in_process_teammate'
  identity: TeammateIdentity;
  permissionMode: PermissionMode;     // ← 独立 cycle，Shift+Tab 切换
  awaitingPlanApproval: boolean;
  abortController?: AbortController;        // kill WHOLE teammate
  currentWorkAbortController?: AbortController;  // 仅 abort 当前 turn
  result?: AgentToolResult;
  progress?: AgentProgress;
}
```

**与 `local_agent` 的关键差异**：
1. **同进程 vs 子进程**：teammate 在主进程内 AsyncLocalStorage 隔离，subagent 是 fork 子进程
2. **独立 permission cycle**：每个 teammate 有自己的 `permissionMode`，Shift+Tab 切换不影响其他人
3. **可双向交互**：用户用 `f` 键 "foreground" 切到 teammate 视图，可直接发 prompt 给 teammate（subagent 不行）
4. **双层 abort**：`abortController` 杀整个 teammate；`currentWorkAbortController` 仅 abort 当前 turn 让 teammate 进新 turn

**典型场景**：多个并发协作的角色 agent（researcher / reviewer / writer），用户可在 leader 与各 teammate 视图间自由切换。

### 12.4 `local_workflow`（Anthropic 内部 only）

**门控**：`feature('WORKFLOW_SCRIPTS')` + `build_flags.yaml`，**外部 build 整个 dead-code 消除 ~1.3K 行 workflow 引擎**。源码注释：

```ts
// WORKFLOW_SCRIPTS is ant-only (build_flags.yaml). Static imports would leak
// ~1.3K lines into external builds. Gate with feature() + require so the
// bundler can dead-code-eliminate the branch.
```

**典型场景**（推测，未实测）：内部 release / build / deploy 自动化脚本，让 agent 触发预定义工作流。外部用户**无法触发也看不到这个 task type**。

leaked source 中 `tasks/LocalWorkflowTask/` 目录为空——证明 dead code elimination 把整个实现移除。仅 `Task.ts#11` 联合类型 + `BackgroundTasksDialog.tsx#82-86` UI 分支保留（用于将来支持时不破坏类型）。

### 12.5 `monitor_mcp`（MCP server 健康监控）

**这与 Monitor 工具不是一回事**——核心区别：

| 维度 | Monitor 工具 | `monitor_mcp` task |
|---|---|---|
| 内部 task type | `local_bash` + `kind='monitor'` | `monitor_mcp`（独立类型） |
| ID 前缀 | `b`（继承 local_bash） | `m` |
| 触发者 | LLM agent 调用 Monitor 工具 | MCP 客户端管理器自动产生 |
| 监控对象 | 任意脚本（`tail -f` / `inotifywait` / poll loop） | MCP server 启动状态 / 健康度 |
| Footer 文案 | `N monitor` | `N monitor`（**两者文案相同！**） |
| 详情 dialog | 复用 `ShellDetailDialog`（"Monitor details"） | 独立处理（`BackgroundTasksDialog#392`） |

**Footer 文案撞车的处理**：[`tasks/pillLabel.ts#67`](file:/root/git/claude-code-leaked/tasks/pillLabel.ts) 给 `monitor_mcp` 单独 case："1 monitor" / "N monitors"——但**当混合存在时**（local_bash:monitor + monitor_mcp 都有）pill 会显示 `N background tasks` 退化（因为 `allSameType` 判断失败）。

**典型场景**：MCP server 启动慢、断连重试、初始化进度。leaked source 没有 `tasks/MonitorMcpTask/` 实现（feature gate dead-coded），但 `BackgroundTasksDialog.tsx#198, #278, #392, #537` 4 处 reference 证明它在生产环境是激活的。

### 12.6 `dream`（Auto Dream 记忆整理）

**触发**：**完全自动**——Auto Dream 系统按"每 N 轮 / token 阈值"自动 fork 一个子 agent 整理用户的 `CLAUDE.md` memory。无需用户或 LLM 显式触发。

源码：[`tasks/DreamTask/DreamTask.ts#1-26`](file:/root/git/claude-code-leaked/tasks/DreamTask/DreamTask.ts)：

```ts
// Background task entry for auto-dream (memory consolidation subagent).
// Makes the otherwise-invisible forked agent visible in the footer pill and
// Shift+Down dialog. The dream agent itself is unchanged — this is pure UI
// surfacing via the existing task registry.

const MAX_TURNS = 30  // 仅显示最后 30 turn

// No phase detection — the dream prompt has a 4-stage structure
// (orient/gather/consolidate/prune) but we don't parse it. Just flip from
// 'starting' to 'updating' when the first Edit/Write tool_use lands.
export type DreamPhase = 'starting' | 'updating'

export type DreamTurn = {
  text: string
  toolUseCount: number  // tool 调用折叠为计数
}
```

**Dream agent 4 阶段** prompt（源码注释揭示，但 dream agent 本身不解析阶段，仅根据"是否出现 Edit/Write tool"切 starting → updating）：
1. **orient** —— 读现有 memory，建立认知
2. **gather** —— 搜集本轮新信息
3. **consolidate** —— 整合到 memory
4. **prune** —— 删除过时条目

**Footer 显示**：单飞 `dreaming`（无计数 N）—— `pillLabel.ts#65` 单独 case `case 'dream': return 'dreaming'`。

**典型场景**：长会话末尾 LLM 总结对话洞察 → 自动写入 `~/.claude/CLAUDE.md`。用户感知：突然出现 `dreaming` pill，几分钟后 `~/.claude/CLAUDE.md` 多了几条新记忆。

### 12.7 `LocalMainSessionTask`（Ctrl+B 两次后台主会话）

**这不是新 type，而是 `local_agent` 的特殊用法**——源码 [`tasks/LocalMainSessionTask.ts#1-10`](file:/root/git/claude-code-leaked/tasks/LocalMainSessionTask.ts)：

```ts
/**
 * LocalMainSessionTask - Handles backgrounding the main session query.
 *
 * When user presses Ctrl+B twice during a query, the session is "backgrounded":
 * - The query continues running in the background
 * - The UI clears to a fresh prompt
 * - A notification is sent when the query completes
 *
 * This reuses the LocalAgentTask state structure since the behavior is similar.
 */
```

**触发**：用户在主会话进行中**连按 Ctrl+B 两次**——整个 main session query 甩到后台，UI 立即清空可接收新 prompt。

**典型场景**：你给 agent 派了个长任务（如"重构整个模块"），跑了 30 秒还没完，但你想插一个新指令。Ctrl+B Ctrl+B 把当前 turn 后台化，开新对话——后台 turn 完成时通知回来。

这相当于**用户主动给自己 fork**——和 `local_agent`（agent 主动 fork 子 agent）相对应。

### 12.8 总结：异步能力光谱

按"agent 知道 vs 用户知道"分组：

| Task type | agent 主动产生 | 用户可触发 | 用户可独立交互 |
|---|---|---|---|
| `local_bash` (shell) | ✅ run_in_background=true | ✅ Ctrl+B（前台 → 后台） | ❌ 仅可 stop / 看 output |
| `local_bash` (monitor) | ✅ Monitor 工具 | ❌ | ❌ 仅可 stop |
| `local_agent` | ✅ Agent + run_in_background | ❌ | ❌ 仅可 stop / 看进度 |
| `LocalMainSessionTask` | ❌ | ✅ Ctrl+B Ctrl+B | ❌ |
| `remote_agent` | ❌ | ✅ /autofix-pr / /ultrareview / /ultraplan | ✅ Plan ready 时审阅 |
| `in_process_teammate` | ✅ TeamCreate | ✅ team 启动 | ✅ **`f` 键 foreground 直接交互** |
| `local_workflow` | （ant-only） | （ant-only） | ？ |
| `monitor_mcp` | ❌（系统自动） | ❌ | ❌ 仅可 stop |
| `dream` | ❌（系统自动） | ❌ | ❌ 仅可看进度 |

**最强能力**：`in_process_teammate`——既可后台并发，又可前台交互。其他要么纯被动，要么仅 stop/查看。

**最普通能力**：`local_bash` + `local_agent`——agent 主动 fork 的"小弟"，跑完报告。

**最云端**：`remote_agent`——本地下线远程也跑。

## 十三、实测复现命令

```bash
mkdir -p /tmp/cc-bg-test && cd /tmp/cc-bg-test
tmux new-session -d -s cc -x 90 -y 35 'cd /tmp/cc-bg-test && claude'
sleep 6
tmux send-keys -t cc Enter            # 信任目录

# 1. 触发 Bash bg
tmux send-keys -t cc "Run 'sleep 60' as a background bash command" Enter
sleep 8

# 2. 触发 Monitor
tmux send-keys -t cc "Use the Monitor tool to watch /tmp/cc-bg-test/watched.log for ERROR lines" Enter
sleep 30

# 3. 看状态条
tmux capture-pane -t cc -p | tail -5
# 应看到：
#   /tmp/cc-bg-test
#   ⏵⏵ auto mode on · 1 shell, 1 monitor

# 4. 打开管理 UI
tmux send-keys -t cc "/tasks" Enter
sleep 2
tmux capture-pane -t cc -p | tail -10

# 5. 清理
tmux kill-session -t cc
rm -rf /tmp/cc-bg-test
```

## 证据来源

### 实测

- Claude Code v2.1.120 在 tmux 90×35 内运行抓屏：[`screenshots/claude-code-bg-tasks-90x35.txt`](./screenshots/claude-code-bg-tasks-90x35.txt)

### 源码（leaked，v2.1.x，路径 `/root/git/claude-code-leaked/`）

| 文件 | 关键行号 | 内容 |
|---|---|---|
| `tasks/LocalShellTask/guards.ts` | 9, 33 | `BashTaskKind = 'bash' \| 'monitor'` + `kind?: BashTaskKind` 字段 + 注释 |
| `tasks/LocalShellTask/LocalShellTask.tsx` | 522 LOC | shell task 主实现 |
| `tasks/pillLabel.ts` | 11-30 | `getPillLabel` 状态条文本生成（含单复数） |
| `tasks/types.ts` | 13-21 | 7 种 BackgroundTaskState 联合类型 |
| `tools/BashTool/BashTool.tsx` | 55, 57, 241, 265, 525, 974 | 常量定义 + run_in_background schema + sleep 拦截 |
| `tools/TaskStopTool/TaskStopTool.ts` | 11-18, 38-46 | task_id / shell_id schema + `aliases: ['KillShell']` |
| `tools.ts` | 39-40, 237 | Monitor 工具 lazy load + `feature('MONITOR_TOOL')` 门控 |
| `utils/task/diskOutput.ts` | 30 | `MAX_TASK_OUTPUT_BYTES = 5 * 1024 * 1024 * 1024` |
| `components/messages/SystemTextMessage.tsx` | 508, 568 | 内联 turn 状态行使用 `getPillLabel` + ` · ... still running` |
| `components/tasks/BackgroundTaskStatus.tsx` | 10, 25-92 | Footer pill 组件 |
| `components/tasks/BackgroundTasksDialog.tsx` | 409, 414 | `/tasks` 管理 UI（`active shell(s)` 标题 + 7 task type 支持） |
| `components/tasks/ShellDetailDialog.tsx` | 164, 177-253 | Shell/Monitor 详情视图（共组件，`isMonitor ? "Monitor details" : "Shell details"`） |
| `components/PromptInput/PromptInputFooterLeftSide.tsx` | 17 | 导入 `BackgroundTaskStatus` 渲染到 Footer |

### 二进制（`/root/.local/share/claude/versions/2.1.119`，245 MB ELF）

| 验证项 | 命令 | 结果 |
|---|---|---|
| UI 字符串 | `strings 2.1.119 \| grep -E "^(1 shell\|1 monitor\|Monitor details\|Shell details)$"` | 4 项全部精确存在 |
| Monitor 工具名 | `strings 2.1.119 \| grep 'mL="Monitor"'` | `var mL="Monitor"` |
| Monitor 描述 | 完整工具 description 字符串 | 完整存在 |
| 22 项 background commands | `strings 2.1.119 \| grep -E "^(yarn\|pnpm\|webpack\|...)$"` | 全部精确存在 |
| 常量数字 | `nm -a 2.1.119` 或 source map | 已被 esbuild 内联，名字消失但数值（15000/5368709120/2000）保留 |

### 公开文档

- [04-tools.md §4.4.7 后台进程管理](../tools/claude-code/04-tools.md)、[03-architecture.md](../tools/claude-code/03-architecture.md)
- [EVIDENCE.md](../tools/claude-code/EVIDENCE.md)（基于较早 v2.1.x 二进制反编译）

### 相关 Qwen Code PR

- [PR#3076](https://github.com/QwenLM/qwen-code/pull/3076) `feat: background subagents`（已合并 2026-04-17，**仅 Agent 后台**）
- [PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) `feat(cli): background-agent UI`（OPEN，**仅 subagent pill**）

> **免责声明**：
> - 实测在 v2.1.120 binary，源码分析在 v2.1.x leaked dump（版本可能略有差异，但核心架构稳定）
> - 二进制反编译可能损失部分元数据（变量名混淆 / 死代码消除），文中 `tools/MonitorTool/` 目录就是被 feature gate 后 dead-code 消除的例子
> - leaked source 未必反映 v2.1.120 全部最新改动；7 种 task type 中 `local_workflow` / `monitor_mcp` 实际触发条件未在本文实测验证
