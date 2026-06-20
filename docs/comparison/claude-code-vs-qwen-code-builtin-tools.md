# Claude Code vs Qwen Code 内置工具对比

> **数据来源**：
> - **Claude Code v2.1.139**：`/root/.local/share/claude/versions/2.1.139` 单文件 ELF (231MB, x86-64) `strings` 反编译 + [docs/tools/claude-code/04-tools.md](../tools/claude-code/04-tools.md)
> - **Qwen Code v0.15.10**：`/root/git/qwen-code/packages/core/src/tools/tool-names.ts` + tools 目录源码（截至 2026-05-12，commit 包含 PR#4002 + PR#4022 + PR#4041 + PR#4069）
> - **配套阅读**：[Tool-Search Deep-Dive](./tool-search-deep-dive.md) / [Tool-Parallelism Deep-Dive](./tool-parallelism-deep-dive.md) / [ReadFile Tool Deep-Dive](./read-file-tool-deep-dive.md) / [BriefTool Async Deep-Dive](./brieftool-async-user-messages-deep-dive.md)
> - **更新历史**：2026-05-12 修订 — 在二进制中确认 Claude Code 已内置 `Monitor` 工具（早期判断为 Qwen 独有不成立），同步修订 §3.3 / §3.11 / §六 / §八

## 一、TL;DR

| 维度 | Claude Code | Qwen Code |
|---|---|---|
| **内置工具总数** | **~32 内部 tool name + ~7 内部/条件 = ~39**（v2.1.139 binary `strings` 命中 30 项 + ReadMcpResourceTool / ListMcpResourcesTool + REPLTool / SleepTool / PowerShell 等条件）| **~21**（含 MCP 动态注册基础）|
| **加载策略** | ToolSearch 延迟（核心 ~10 始终加载 / ~20+ 延迟需 `ToolSearch("select:<name>")` 取 schema）| 部分延迟（PR#3589 + PR#4022 共 9 项 deferred）|
| **Monitor 工具** | ✅ 内置（v2.1.139 binary 确认，含 `persistent` 标志 + TaskStop 取消 + 200ms 批合并 + auto-stop 超额输出）| ✅ 内置（PR#3791 引入，`monitor.ts` 742 行）|
| **Task* 工具组** | TaskCreate / TaskList / TaskGet / TaskUpdate / TaskOutput / TaskStop（6 个细粒度工具）| TodoWrite + TaskStop（2 个，覆盖 create/update 路径）|
| **MCP 工具** | `mcp__<server>__<tool>` 动态注册 + ReadMcpResourceTool / ListMcpResourcesTool 桥接 | `mcp-tool.ts` 同款机制 |
| **System prompt 节省** | ~60%（15K → 6K tokens）| 部分（PR#3589 + PR#4022 等延迟落地）|
| **设计差异** | 工具数多 + 强分类 + 延迟加载 + Tool description 工程（"silence is not success" 等深度提示）| 工具数精简 + 4 kinds Background framework 统一抽象 |

## 二、工具数量对比

| 类别 | Claude Code | Qwen Code | 差异 |
|---|:---:|:---:|---|
| 核心（始终加载） | 10 | ~12 | Qwen 没有 ToolSearch / StructuredOutput 顶级工具 |
| 延迟（按需加载） | 25 | 9 | Claude 延迟池大得多 |
| 内部 / 条件 | 4 | 0 | Claude 有 REPLTool / SleepTool / PowerShell |
| MCP 动态 | ∞ | ∞ | 两者都支持 |
| **总计（不含 MCP）** | **~39** | **~21** | **Claude ~1.85x** |

## 三、详细 mapping table（Claude → Qwen 对应关系）

### 3.1 文件 / 搜索类

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `Read` | `read_file` (ReadFile) | ✅ 对齐 + Qwen 后来居上 | PR#3717 / 3774 / 3810 / 3932 / 4002 FileReadCache + prior-read 守卫链与 Claude 行为对齐 |
| `Write` | `write_file` (WriteFile) | ✅ 对齐 | partial-read 接受语义 PR#3932 / 4002 与 Claude 一致 |
| `Edit` | `edit` (Edit) | ✅ 对齐 | replace_all 模式 Qwen 也有 |
| `Glob` | `glob` (Glob) | ✅ 对齐 | — |
| `Grep` | `grep_search` (Grep) + `ripGrep`（独立 ts 文件）| ✅ 双实现 | Qwen 有 `grep.ts` 通用版 + `ripGrep.ts` 性能版 |
| `LS` (Claude 内部？) | `list_directory` (LS / ListFiles) | ✅ 对齐 | Qwen 独立工具 |

### 3.2 执行类

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `Bash` | `run_shell_command` (Shell) | ✅ 对齐 | Claude 12,411 LOC / 18 文件 / 23 项安全验证；Qwen `shell.ts` 含 AST 只读检测 |
| `PowerShell`（Windows 条件）| ❌ 无 | Qwen 缺 | Claude 仅 Windows 平台启用 |
| `REPLTool`（内部）| ❌ 无 | Qwen 缺 | Claude 内部使用 |
| `SleepTool`（内部）| ❌ 无 | Qwen 缺 | Claude 内部使用（睡眠 / 等待）|

### 3.3 Agent / 任务调度类

> **二进制确认**：v2.1.139 binary `strings` 命中以下 6 个 Task* tool name 字符串：`TaskCreate` / `TaskList` / `TaskGet` / `TaskUpdate` / `TaskOutput` / `TaskStop`，外加 `Agent` / `Monitor` / `PushNotification` / `ScheduleWakeup` / `RemoteTrigger` / `CronCreate` / `CronList` / `CronDelete`。

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `Agent` | `agent` (Agent) | ✅ 对齐 | Qwen 在 agent/ 子目录有 `agent.ts` + `fork-subagent.ts` |
| `TaskCreate` / `TaskList` / `TaskGet` / `TaskUpdate` / `TaskOutput`（6 个独立工具）| `todo_write` (TodoWrite) 单工具 | ⚠️ 粒度差异 | Claude 5 工具分离（create/list/get/update/output），细粒度便于 LLM 精确操作；Qwen 用 TodoWrite 单工具覆盖 create+update 两路径 |
| `TaskStop`（含 KillShell 别名）| `task_stop` (TaskStop) | ✅ 对齐 | Qwen 同款（PR#3642 + PR#3836 4 kinds dispatch）|
| `Monitor`（**v2.1.139 确认存在**）| `monitor` (Monitor) | ✅ **对齐**（早期文档误判为 Qwen 独有，2026-05-12 binary 反证修订）| 见 §3.12 详细对比 |
| `PushNotification`（延迟）| ❌ 无 | Qwen 缺 | Claude 异步推送通知工具 |
| `ScheduleWakeup`（延迟）| ❌ 无 | Qwen 缺 | Claude 调度未来唤醒（/loop 动态模式配套）|
| `RemoteTrigger`（延迟）| ❌ 无 | Qwen 缺 | Claude 远程触发能力（移到 §3.10）|
| `TodoWrite` | `todo_write` (TodoWrite) | ✅ 对齐 | Claude 已被 TaskCreate/Update 取代，Qwen 保留 |

### 3.4 Web / 抓取类

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `WebFetch` | `web_fetch` (WebFetch) | ✅ 对齐 | Claude 1,131 LOC |
| `WebSearch` | ❌ **缺**（PR#3502 移除 → PR#3844 OPEN 重新添加中）| Qwen 待补 | Qwen 之前移除过 WebSearch（PR#3502 −1830 行），社区报 #3841 引用 codeagents [web-search-tool-deep-dive](./web-search-tool-deep-dive.md) 推动 PR#3844 OPEN 回填 |
| `NotebookEdit` | ❌ 无 | Qwen 缺 | Claude 587 LOC，Jupyter `.ipynb` 编辑支持 |
| `WebFetch` Auto Clean | 有 prompt-injection 防御 | 有同款（PR#3844 设计）|

### 3.5 LSP / Code Intelligence

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `LSP` | `lsp` (Lsp) | ✅ 对齐 | Qwen `lsp.ts` 完整实现 |

### 3.6 用户交互类

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `AskUserQuestion` | `ask_user_question` (AskUserQuestion) | ✅ 对齐 | PR#4041 把 Qwen 该工具从 deferred 改回 always-visible（防 prose fallback）|
| `SendMessage` | `send_message` (SendMessage) | ✅ 对齐 | 给 background task 发消息 |
| `Brief`（Claude 延迟工具）| ❌ 无 | Qwen 缺 | Claude `brieftool` 异步用户消息机制（[Brief Tool Deep-Dive](./brieftool-async-user-messages-deep-dive.md)）|
| `ExitPlanMode` | `exit_plan_mode` (ExitPlanMode) | ✅ 对齐 | — |
| `PlanMode*` 工具组 | 仅 `exit_plan_mode` | ⚠️ 不完全对齐 | Claude 有 PlanMode 多个相关工具，Qwen 只暴露 exit |

### 3.7 Cron / 调度类

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `Cron*` 工具组（CronCreate / CronList / CronDelete）| `cron_create` / `cron_list` / `cron_delete` (CronCreate / CronList / CronDelete) | ✅ **完全对齐** | Qwen 拆 3 个独立工具（PR#3589 ToolSearch 默认 deferred）|

### 3.8 Memory / Skills

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `Skill` | `skill` (Skill) | ✅ 对齐 | Qwen PR#3852 path-conditional 激活（基于 discovered 路径，比 Claude 更准）|
| `Memory` 系列（Claude 通过 services/memdir 而非工具）| `save_memory` (SaveMemory) | ⚠️ 实现位置不同 | Claude 把 memory 放在 services 层；Qwen 暴露为顶级 tool |

### 3.9 Worktree / Git 高级

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `EnterWorktree` / `ExitWorktree` | `enter_worktree` / `exit_worktree`（**PR#4073 MERGED 2026-05-14**）+ `agent` 工具 `isolation: 'worktree'` 参数 | ✅ **Qwen 已合并** | **PR#4073** (+1651/-4 · LaZzyMan · closes Phase A+B of #4056)——2 新工具直接对标 Claude 工具名 + agent 隔离参数 + worktree cleanup + dirty-state guard + slug validation；详见 [improvement-report 2026-05-12 第二轮](./qwen-code-improvement-report-changelog.md#2026-05-12-第二轮) |

### 3.10 Remote / Team / 全局工具

| Claude Code | Qwen Code | 状态 | 备注 |
|---|---|---|---|
| `RemoteTrigger`（v2.1.139 binary 确认存在，延迟）| ❌ 无 | Qwen 缺 | Claude 远程触发能力；可能对应于 PR#3929-3931 mobile UI / pairing token 的设计方向 |
| `Team*` 工具组（Claude 延迟）| ❌ 无 | Qwen 缺 | Claude 团队协作（多 user 共享）|
| `Config`（Claude 延迟）| ❌ 无 | Qwen 缺 | Claude 动态 settings 工具（[Config Tool Deep-Dive](./config-tool-dynamic-settings-deep-dive.md)）|
| `StructuredOutput`（Claude 核心）| 🟡 PR#4001 OPEN（feat: structured JSON schema output）| Qwen 实现中 | 对应 Claude 核心工具，Qwen 通过 CLI flag (`--json-schema`) 实现而非工具 |
| `ToolSearch`（v2.1.139 binary 确认存在，核心）| 🟡 PR#3589 部分实现 + PR#4069 加 `tools.toolSearch.enabled` 开关 | Qwen 部分 | Qwen ToolSearch 实现了延迟机制，但 PR#4069 揭示与 prefix cache 冲突（DeepSeek 用户报 +214% 成本）|
| `Skill`（v2.1.139 binary 确认存在）| `skill` (Skill) | ✅ 对齐 | 已在 §3.8 详述 |

### 3.11 Qwen 独有（修订后）

| Qwen Code | Claude Code | 状态 | 备注 |
|---|---|---|---|
| `save_memory` (SaveMemory) | 不暴露为工具（走 services/memdir 层）| ⚠️ 接口位置差异 | 见 §六 |
| `4 kinds Background tasks framework`（agent/shell/monitor/dream 统一调度）| 未发现同等抽象（各 background 类型独立路径）| **Qwen 独有架构** | PR#3642 + PR#3720 + PR#3791 + PR#3836 4 PR 系列；Claude 没有统一的 background 类型调度框架（Agent + Monitor + Bash run_in_background 各自实现）|

> **关键修订**（2026-05-12）：早先列为 "Qwen 独有" 的 `monitor` 工具在 Claude Code v2.1.139 二进制中确认存在（`strings` 命中字符串 `JW="Monitor"`、完整 tool description 含 "Start a background monitor that streams events from a long-running script"、`persistent: true` 参数等），故从 Qwen 独有列表移除，对比详见下方 §3.12。

### 3.12 Monitor 工具：Claude vs Qwen 详细对比

| 维度 | Claude Code Monitor | Qwen Code monitor |
|---|---|---|
| **工具名** | `Monitor`（PascalCase）| `monitor`（snake_case 别名 `Monitor`）|
| **核心定位** | "Start a background monitor that streams events from a long-running script. Each stdout line is an event"（描述原文） | 同款语义，描述基本一致 |
| **stdout → 通知映射** | 每条 stdout 行 → 一条 chat notification（200ms 内多行批合并）| 同款（throttling 防 stdout 洪泛）|
| **不要用 unbounded 命令求单次通知** | 描述明确警告：`tail -f log \| grep -m 1` 在 SIGPIPE 缺失时会挂；应改用 Bash `run_in_background` + `until` 循环 | Qwen 描述未发现等价警告（设计可借鉴）|
| **Coverage warning（"silence is not success"）** | 描述明确：filter 需匹配 every terminal state 而非仅 happy path；建议宽 `grep -E "elapsed_steps=\|Traceback\|Error\|FAILED\|assert\|Killed\|OOM"` | Qwen 描述未发现等价警告（设计可借鉴）|
| **stdout 缓冲建议** | 强制建议 `grep --line-buffered`；poll loop 用 `\|\| true` 处理 transient failure | Qwen 描述无明确指引 |
| **轮询频率建议** | 远程 API 30s+；本地 0.5-1s | Qwen 由用户自由设置 |
| **持久标志** | `persistent: true` → 整个 session 存活（直到 TaskStop 或会话结束）| `max_events` + `idle_timeout_ms` 自动停止 |
| **取消机制** | `TaskStop`（统一 task 取消接口）| 同款 |
| **stdout 200ms 批合并** | 描述明确（avoid event flooding）| Qwen `monitor.ts` 也有 throttling |
| **超额输出自动停止** | 描述明确："Monitors that produce too many events are automatically stopped" | Qwen `max_events` 默认 100 |
| **stderr 路由** | stderr → output file（Read 可读），不触发通知；建议 `2>&1` merge | Qwen `monitor.ts` 同款（输出文件可读）|
| **LOC（估算）** | 未拆出独立文件大小，但 description 文本量 ~6KB（含 6 个 example block）| `monitor.ts` 742 行 |
| **加载策略** | 始终加载（在 deferred-tool 列表里，需 ToolSearch 才能取得 schema）| PR#4022 后移入 deferred（与 Claude 对齐）|

**评估**：**Claude Monitor 在 prompt 工程层面（warning / coverage / buffer 提示）远比 Qwen `monitor` 严谨**——Claude 把 LLM 调用监控工具的常见错误模式（求单次通知用了 unbounded 命令、grep 不带 `--line-buffered` 导致延迟、filter 只匹配 happy path）都写进 description 里直接教给模型。这正是 Anthropic 在 Tool Description Engineering 上的成熟度优势。Qwen `monitor` 实现完整、行为对齐，但 description 文案明显简短，**有较大借鉴空间**（可直接将 Claude 的 6 段 example + 3 项 quality 警告译入 Qwen `monitor.ts` description）。

## 四、加载策略对比

### 4.1 Claude Code: ToolSearch 延迟加载

- **核心 10 个工具始终加载到系统提示**（约 ~6K tokens）
- **25 个延迟工具**（`shouldDefer: true`）不在初始 prompt——模型通过 `ToolSearch("keyword")` 动态拉取 schema
- **节省**：系统提示从 ~15K → ~6K tokens（**~60%**）

```
ToolSearch 工作流：
  模型: "需要编辑 Jupyter notebook"
  ↓
  ToolSearch("notebook edit") → 返回 NotebookEdit schema
  ↓
  下一轮模型: NotebookEdit({...})
```

### 4.2 Qwen Code: 部分延迟

- **PR#3589** 引入 ToolSearch 机制，最初延迟 5 项：`cron_create`, `cron_list`, `cron_delete`, `ask_user_question`, `exit_plan_mode`, `lsp`, MCP 相关
- **PR#4022** (2026-05-11) 扩展延迟 4 项：`monitor`, `send_message`, `task_stop`, `web_fetch` — 与 Claude 延迟策略对齐
- **PR#4041** (2026-05-11) 反向修复：`ask_user_question` 强制 `shouldDefer=false`（deferred 后模型用 prose 代替结构化 multi-choice）
- **PR#4069** (2026-05-12 OPEN) 新增 `tools.toolSearch.enabled` 全局开关 + `deepseek-v4-*` 自动 disable（防 prefix cache 冲突）

### 4.3 设计权衡：token 节省 vs cache hit

[PR#4069 揭示的根本矛盾](./qwen-code-improvement-report-changelog.md#2026-05-12)（来自真实用户 [discussions/4065](https://github.com/QwenLM/qwen-code/discussions/4065)）：

| 维度 | ToolSearch 之前 | ToolSearch 之后 |
|---|---|---|
| Initial tool list | 全部 ~30 工具 | 核心 ~10 工具 + 动态发现 |
| Token 数 | 较高 | 减少 ~46% |
| Cache prefix | 稳定 → cache hit 97.5% | 动态 → cache hit **81.5%** |
| DeepSeek 日成本 | $1.05 | **$3.30**（+214%） |

DeepSeek `cache_hit` 定价是 `cache_miss` 的 1/120，失去 cache hit = 输入 token 价格涨 120 倍，远超 ToolSearch 节省的 46% token 数。**Claude 因模型架构差异（prompt cache 工作机制不同）不受此影响**。

## 五、Claude 独有工具（Qwen 可借鉴）

| 工具 | Claude LOC | 用途 | Qwen 借鉴优先级 |
|---|---|---|---|
| **WebSearch** | 569 | 搜索引擎查询 | 🌟 **P0**（PR#3844 OPEN 回填中）|
| **NotebookEdit** | 587 | Jupyter `.ipynb` 编辑 | 🟡 P1（数据科学场景）|
| ~~Worktree*~~ | — | git worktree 切换 / 多分支并行 | ✅ **已 OPEN**（[PR#4073](https://github.com/QwenLM/qwen-code/pull/4073) 2026-05-12 LaZzyMan +1651/-4 · `enter_worktree` / `exit_worktree` + agent `isolation: 'worktree'` · Phase A+B of #4056） |
| **Brief** | — | 异步用户消息批量收集 | 🟡 P1（[Brief Tool Deep-Dive](./brieftool-async-user-messages-deep-dive.md)）|
| **RemoteTrigger** | — | 远程触发 | 🔴 P3（对应 PR#3929-3931 remote-control 方向）|
| **Team*** | — | 团队协作工具组 | 🔴 P3（企业部署）|
| **Config** | — | 动态 settings 工具 | 🟡 P2（[Config Tool Deep-Dive](./config-tool-dynamic-settings-deep-dive.md)）|
| **SleepTool** | — | 等待 / 节流（内部）| 🔴 P3（内部使用）|
| **PowerShell** | — | Windows 平台 shell | 🟡 P2（跨平台 Windows 支持）|

## 六、Qwen 独有工具（Claude 没有）

> **修订记录（2026-05-12）**：原表中 `monitor` 工具基于 v2.1.139 binary 反证已确认 Claude 同样内置，从本节移除至 §3.12 详细对比。

| 工具 | LOC | 用途 | 设计亮点 |
|---|---|---|---|
| **save_memory**（顶级 tool）| ~300 | 写入用户级 memory（cross-session）| Claude 通过 services/memdir 层 + 自动 memory 系统（在 system prompt 内置 "auto memory" 规则块）实现；Qwen 暴露为顶级 tool 调用门更低，但缺少 Claude 的自动书写规则 |
| **4 kinds Background tasks framework** | - | agent/shell/monitor/dream 4 类 background 任务统一调度 | PR#3642 + PR#3720 + PR#3791 + PR#3836 4 PR 系列；Claude 各 background 类型实现独立，未统一抽象 |

## 七、共同工具但实现差异

### 7.1 Read 工具：Qwen 后来居上

| 维度 | Claude Code | Qwen Code |
|---|---|---|
| LOC | 1,602 | 440 (read-file.ts) |
| Cache 机制 | LRU 1000 条 + mtime 失效 | session-scoped FileReadCache（`(dev, ino)` key）|
| Prior-read 守卫 | 内置 | PR#3774 + PR#3932 + PR#4002 完整对齐 |
| 二进制检测 | mime + 扩展名 + 4KB sample | PR#4002 同款（KNOWN_TEXT_EXTENSIONS 50+ + mime + sample 3-step）|
| Partial read | 接受 | PR#3932 Edit 路径接受 |
| Image 压缩 | 有 token 上限 | 🟡 部分（参考 [ReadFile Tool Deep-Dive](./read-file-tool-deep-dive.md) 12 项可借鉴）|

**评估**：Qwen 经过 5 PR 跨 13 天系列（PR#3717→3810→3774→3932→4002）已与 Claude 行为对齐。详见 [item-2 文件读取缓存](./qwen-code-improvement-report-p0-p1-engine.md#item-2)。

### 7.2 Bash / Shell：Claude 更严格

| 维度 | Claude Code | Qwen Code |
|---|---|---|
| LOC | 12,411 (18 文件) | 3,652 (单文件 shell.ts) |
| 安全验证 | 23 项 | AST 只读检测 + 命令白名单 |
| 沙箱机制 | 有 | NoSandbox 默认（[§06 §五 External Reference 沙箱](./qwen-code-daemon-design/06-roadmap.md) External 范畴）|
| 后台运行 | `run_in_background` 字段 | PR#3642 BackgroundShellRegistry + PR#3894 Ctrl+B promote |
| Sed 模拟 | `_simulatedSedEdit` 直接编辑不经 shell | ❌ 无 |
| `dangerouslyDisableSandbox` | 有 | ❌ 无（无沙箱）|

**评估**：Claude Bash 在安全验证 / 沙箱 / 命令分类维度成熟度远超 Qwen，但 Qwen 4 kinds Background framework（PR#3642 + PR#3720 + PR#3791 + PR#3836）是 Claude 没有的 background tasks 统一调度面。

### 7.3 Cron：Qwen 更精细

| 维度 | Claude Code | Qwen Code |
|---|---|---|
| 工具数 | Cron* 一组 | 拆 3 个独立：CronCreate / CronList / CronDelete |
| 持久化 | settings | `~/.qwen/crons.json` |
| 加载方式 | 延迟 | 延迟（PR#3589） |

### 7.4 Skill：Qwen 路径条件激活更准

| 维度 | Claude Code | Qwen Code |
|---|---|---|
| Path-conditional 激活 | 基于 tool 输入路径 | **PR#3852 基于 discovered 路径**（更广覆盖：glob / grep / ripGrep 结果路径都触发激活）|
| 防伪造路径 | — | PR#3852 仅信任 filesystem 工具的 result-side metadata + structured ripgrep |
| 热重载 slash 命令 | — | **PR#3923 (2026-05-08)** `SkillManager.addChangeListener` 触发 slash commands 重载 |
| Symlink 支持 | — | **PR#3915 (2026-05-07)** 允许 symlink 指向 skills 目录外 |

**评估**：Qwen Skill 在 path-conditional 激活精度 + 热重载 + symlink 灵活性 3 项**反超 Claude**。

## 八、一句话总结

**Claude Code 内置工具数 ~39 vs Qwen Code ~21**（不含 MCP 动态注册），Claude 在工具数量 / ToolSearch 延迟加载策略 / Bash 23 项安全验证 / 工具子组（**Task* 6 个** / Cron* / Worktree* / Team* / PlanMode*）细粒度上更成熟，且**包含完整的 Monitor 工具**（早先误判为 Qwen 独有，2026-05-12 binary 反证修订）；**Qwen 在 FileReadCache + prior-read 守卫链（5 PR 跨 13 天与 Claude 对齐）/ 4 kinds Background tasks framework（agent/shell/monitor/dream 统一调度抽象）/ Skill path-conditional 激活（基于 discovered 路径）/ 热重载 + symlink 灵活性 4 项独有优势上反超 Claude**。

**关键设计借鉴方向**：
- 🌟 **Qwen → Claude**：4 kinds Background tasks framework 统一调度抽象（Claude 各 background 类型实现仍独立）；Skill 基于 discovered 路径激活；FileReadCache prior-read 守卫链 5 PR 完整闭环
- 🌟 **Claude → Qwen**：WebSearch 回填（PR#3844 OPEN）；NotebookEdit / Worktree* / Brief / Config 工具组；**Monitor 工具 description 工程**（"silence is not success"、`grep --line-buffered` 强制提示、unbounded 命令求单次通知的反模式警告 3 项 Qwen `monitor.ts` 文案可直接借鉴）；ToolSearch 与 prefix cache 的 cost-aware 协调（PR#4069 揭示并修复 DeepSeek +214% 成本回归）

## 九、附：Claude Code v2.1.139 二进制反编译工具清单（截至 2026-05-12）

`strings /root/.local/share/claude/versions/2.1.139` 命中的内部 tool name 注册（按字母序，30 项）：

```
Agent  AskUserQuestion  Bash  CronCreate  CronDelete  CronList
Edit  EnterPlanMode  EnterWorktree  ExitPlanMode  ExitWorktree
Glob  Grep  Monitor  NotebookEdit  PushNotification  Read
RemoteTrigger  ScheduleWakeup  Skill  TaskCreate  TaskGet  TaskList
TaskOutput  TaskStop  TaskUpdate  ToolSearch  WebFetch  WebSearch  Write
```

外加 `ReadMcpResourceTool` / `ListMcpResourcesTool`（MCP 桥接），合计 **~32 个内置 tool name**（不含 MCP 动态注册的 `mcp__<server>__<tool>` 命名空间）。

> 注：这里清点的是**内部 tool name 字符串**，不区分 always-loaded 与 deferred；某些 tool（如 `ScheduleWakeup`、`Monitor`、`TaskCreate`、`CronCreate` 等）按 ToolSearch 策略默认 deferred，需通过 `ToolSearch("select:<name>")` 获取 schema 后方可调用。
