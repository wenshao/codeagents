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

## 十、实测复现命令

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

- 实测：Claude Code v2.1.120 在 tmux 90×35 内运行，截图保存于 [`screenshots/claude-code-bg-tasks-90x35.txt`](./screenshots/claude-code-bg-tasks-90x35.txt)
- 后台机制：[04-tools.md §4.4.7 后台进程管理](../tools/claude-code/04-tools.md)、[03-architecture.md](../tools/claude-code/03-architecture.md)
- TaskStopTool / KillShell 别名：[EVIDENCE.md](../tools/claude-code/EVIDENCE.md)
- 相关 Qwen Code PR：[PR#3488](https://github.com/QwenLM/qwen-code/pull/3488)（background-agent UI，OPEN）、[PR#3076](https://github.com/QwenLM/qwen-code/pull/3076)（run_in_background，已合并）
- Monitor 工具规格：本会话内 ToolSearch 加载的 Monitor schema

> **免责声明**：实测基于 v2.1.120（2026-04-25）。Monitor 工具未出现在公开 [04-tools.md](../tools/claude-code/04-tools.md) 39 项工具表中——可能是新加入的工具或归在其他类目。状态条 `N shell, M monitor` 文本格式可能随版本变化。
