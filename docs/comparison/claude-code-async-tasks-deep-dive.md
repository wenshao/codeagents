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
- **被动型**：进程自己跑，agent 不需主动读
- **结果通过 `BashOutput(bashId)` 拉取**（按需）
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
- **主动型**：每条 stdout 行 = 一条聊天消息推回 LLM（agent 不需轮询）
- **200ms 内多行批量为一条通知**（避免噪声）
- **生命周期**：默认 `timeout_ms: 300000`（5 分钟）/ `persistent: true`（会话生命周期）
- **过量保护**：消息过多自动停止（避免 token 爆炸）
- **退出条件**：脚本自身 exit / timeout / `TaskStop(task_id=...)`

### 一表看清差异

| 维度 | Shell（Bash bg） | Monitor |
|---|---|---|
| 触发 | `Bash` + `run_in_background: true` | `Monitor` 工具 |
| 数据流向 | LLM 主动 `BashOutput()` 拉 | 每行 stdout 自动推送给 LLM |
| 生命周期默认 | 进程自然结束 | 5 分钟 timeout |
| 推送上限 | 无（按需拉取） | 自动节流（多行 200ms 批合） |
| 状态条计数 | `N shell` | `N monitor` |
| 终止 | `TaskStop(shell_id=...)` 或 `KillShell` 别名 | `TaskStop(task_id=...)` |

**关键洞察**：Shell 是"子进程托管"，Monitor 是"事件总线"——前者**冷数据**（输出在那等你拉），后者**热数据**（事件来了主动推）。

## 三、状态条显示机制

Footer 的两行布局（v2.1.120）：

```
  /tmp/cc-bg-test                              ← Line 1: cwd
  ⏵⏵ auto mode on · 1 shell, 1 monitor         ← Line 2: mode + 异步任务计数
```

`auto mode on` 永久存在（除非用户切换），后续 `· 1 shell, 1 monitor` **按需附加**：

| 触发条件 | 显示 |
|---|---|
| 无后台任务 | `⏵⏵ auto mode on (shift+tab to cycle)` |
| 仅 1 个 bg shell | `⏵⏵ auto mode on · 1 shell` |
| 仅 1 个 monitor | `⏵⏵ auto mode on · 1 monitor` |
| 都有 | `⏵⏵ auto mode on · 1 shell, 1 monitor` |
| 多个 | `⏵⏵ auto mode on · 3 shells, 2 monitors` |

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

UI 标题 `2 active shells` 把两类**统称为 shell**（历史包袱），但 Footer 状态条**精确分类**为 `1 shell, 1 monitor`——以 Footer 为准。

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
Monitor 启动 → agent 继续干别的事 → Monitor 检测到 ERROR
                                          ↓
                 注入 system message：脚本 stdout 行作为通知
                                          ↓
                 agent 在下一轮看到通知，决策是否响应
```

**这与 BashOutput 拉模式正相反**——Bash bg 的输出 agent 必须主动 `BashOutput(id)` 拉；Monitor 是**事件来了被动通知**。

实现细节（来自 Monitor 工具的描述）：

> 200ms 内的多行 stdout 批量为一条通知（避免泛洪）。Monitor 自动停止条件：消息过多 → 强制停（避免 token 爆炸）。

工程细节：
- 使用 `grep --line-buffered` 强制行缓冲（否则 pipe 缓冲延迟分钟级）
- 失败容错：`curl ... || true` 防止单次失败杀掉整个 monitor
- 轮询间隔：本地 0.5-1s / 远端 30s+（API 速率限制）

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
    │   通过 BashOutput(id) 拉输出
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
| 后台 Bash 进程 | ✅ `run_in_background` + 自动后台化 + Ctrl+B | ⚠️ 部分（[PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) OPEN 中：background-agent UI） | ⚠️ Bash 工具有 `run_in_background` 参数但**无统一管理 UI** |
| Monitor / 事件流 | ✅ 独立 `Monitor` 工具 + 200ms 节流 | ✗ 无 | ✗ 无 |
| 状态条计数 | ✅ `N shell, M monitor` 实时分类 | ✗ 无 | ✗ 无 |
| 统一管理 UI | ✅ `/tasks`（`/bashes` 别名）+ `↓` 键 | ✗ 无任务面板 | ✗ 无 |
| 通知推送（事件 → LLM） | ✅ `<task-notification>` 系统消息注入 | ✗ 无（仅同步工具调用） | ✗ 无 |

**Claude Code 是目前唯一把"agent 异步任务"完整产品化的 agent**。

### Qwen Code 的相关 PR

[PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) `feat(cli): background-agent UI — pill, combined dialog, detail view`（OPEN）—— 对标 Claude 的 `/tasks` 面板，但目前还在 review，且仅覆盖**Agent 后台**（Task tool 异步），不覆盖 Bash bg。

[PR#3076](https://github.com/QwenLM/qwen-code/pull/3076) 已经做了 `run_in_background` 参数，但用户**看不到状态指示**——参数在但无可见性。

完整对标至少需要：
1. Bash bg pool（已有）
2. 统一 background task 管理面板（PR#3488 在做）
3. 状态条分类计数（无 PR）
4. **Monitor / 事件流工具（最大缺口）**——目前没有任何 PR 涉及

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

这种"agent 边写代码边监控"的模式在 Qwen Code 里需要 LLM 主动**反复轮询** `BashOutput`——浪费 token，且响应延迟。Monitor 的事件推送让 agent 有了"中断"概念。

### 实现视角：核心是 5 个组件

1. **Shell pool**：进程注册表 + lifecycle 管理（PID / IO buffer / kill handle）
2. **Monitor pool**：watch script 注册 + stdout 流式 grep + 通知去抖
3. **状态条聚合器**：跨两个 pool 计数 → 渲染到 Footer
4. **管理 UI**：列表视图 + 详情视图（Shell / Monitor 各有不同字段）
5. **通知注入器**：把 monitor stdout 行包成 `<task-notification>` 注入 LLM context

任何 agent 想抄这套，5 个组件都要做。最小 MVP 也要 4-6k 行代码。

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
