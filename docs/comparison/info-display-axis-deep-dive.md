# 信息展示轴 Deep-Dive —— Claude Code / Codex / Qwen Code / OpenCode

> **核心问题**：四款 Code Agent 把**哪些信息**放在用户面前？放在**哪一层**接触面？同等信息选不同接触面，背后的产品哲学差异是什么？
>
> 返回 [对比文档总览](./README.md)
>
> **范围界定**：本文聚焦 **信息内容（content）维度**，不重复 [显示组件 Deep-Dive](./display-components-deep-dive.md)（form 维度——组件树 / 渲染单位 / 分派机制）。两者**正交**：display-components 回答"用什么组件渲染"，本文回答"渲染什么内容、放在哪里"。

## 零、TL;DR

22 类信息 × 3 层接触面（顶层 always-on Footer / 中层 in-stream / 低层 on-demand dialog）的归属差异，四家代表四种 UI 哲学：

| 家 | 一句话 | 标志性证据 |
|---|---|---|
| **Claude Code** | "**信息分级 + 渲染层硬件加速**" | `TokenWarning.tsx` 2 档警告（warning/error）+ Ink fork 60fps 节流 + 右栏 `MoreRight` 驻留 diff |
| **Codex** | "**模式 + 键位是顶层抽象**" | `CollaborationModeIndicator` (Plan/Pair/Execute) + `GoalStatusIndicator` 4 态 + `Alt+,/.` 调档 + `Ctrl+T` transcript overlay |
| **OpenCode** | "**Footer 极简，深信息走 dialog**" | session footer 91 LOC + 31 个 Dialog + `/status` 集中元信息 + Stack-based Promise dialog；**subagent footer 唯一显示 USD 成本** |
| **Qwen Code** | "**能塞就塞 + 窄屏自适应 + 用户脚本可覆盖**" | 180 LOC footer + 5 个 pill + `useStatusLine` 用户脚本覆盖 + `ScreenReaderAppLayout` 可访问性 |

**最重要的反常识结论**：**Footer 几乎没人显示 cost (USD)**——除了 OpenCode 的 **subagent footer** 用 `Intl.NumberFormat` 显示当前 subagent session 成本。这是自费 API key 用户最关注的信号，却被 3/4 家完全忽略。

## 一、22 类信息 × Footer 显示矩阵

最高频接触面是 Footer——用户**每秒都在扫**的位置。四家在 Footer 上呈现的信息差异最大。

| 信息类别 | Qwen Code | OpenCode | Codex | Claude Code |
|---|:---:|:---:|:---:|:---:|
| Cwd（当前目录）| ✅ statusLine 左 | ✅ `directory()` 左 | ❌ | ✅ |
| Model 名 | ✅ statusLine | ❌（走 `/status`）| ❌ Footer 无 | ✅ `model.id` |
| Fast model | ✅ statusLine | ❌ | ❌ | ❌ |
| Sandbox 状态 | ✅ `🔒 seatbelt/docker` | ❌ | ⚠️ approval 含 | ✅ |
| Debug mode | ✅ `Debug Mode` 黄 | ❌ | ❌ | ❌ |
| **Context 使用 %** | ✅ `ContextUsageDisplay` 右 | ❌（走 `/status`）| ✅ key hints 区 | ✅ `TokenWarning` 触发 |
| Token 累计 | ❌ | ❌ session footer / ✅ subagent footer | ❌ Footer 无 | ❌ |
| **Cost (USD)** | ❌ | ❌ session / **✅ subagent footer 唯一**（`session().cost`）| ❌ | ❌ |
| **Goal 状态** | ✅ `GoalPill` 4 态 | ❌（无 `/goal`）| ✅ 4 态 `GoalStatusIndicator` | ⚠️ v2.1.139+ 位置待验证 |
| **Plan mode** | ❌ Footer 无 | ❌ | ✅ `Plan mode` 紫色 | ✅ |
| Background tasks | ✅ `BackgroundTasksPill` | ❌ | ❌ | ✅ |
| MCP 状态 | ✅ `MCPHealthPill` | ✅ `⊙ N MCP` + 错误红 | ❌（走 `/mcp`）| ✅ |
| **LSP 状态** | ❌ | ✅ `• N LSP` | ❌ | ❌ |
| Permission 待批 | ❌ Footer 无 | ✅ **`△ N Permission(s)` 黄** | ⚠️ `approval_overlay` 触发 | ✅ |
| Vim mode | ✅ `-- INSERT --` | ❌ | ❌ | ✅ |
| Shell mode | ✅ `ShellModeIndicator` | ❌ | ❌ | — |
| Approval mode (yolo/ask) | ✅ `AutoAcceptIndicator` | ❌（走 `/status`）| ⚠️ popup | ✅ |
| Custom statusLine 脚本 | ✅ `useStatusLine`（多行）| ❌ | ❌ | ✅ `settings.statusLine` |
| 退出/快捷键提示 | ✅ `? for shortcuts` / `Esc again to clear` | ✅ `/status` hint | ✅ 9 个 `FooterKeyHints` | ✅ |
| **Reasoning effort 调节** | ❌ | ❌ | ✅ **`Alt+, / Alt+.`** | ❌ |
| **Ctrl+T transcript** | ❌ | ❌ | ✅ `show_transcript` hint | — |
| 连接状态（远端）| ❌ | ✅ `connected()` + `welcome` 闪烁 | ❌ | — |

### 各家 Footer LOC 对照

| Footer | LOC | 平均信息密度 |
|---|---|---|
| **Qwen Code** `Footer.tsx` | 180 | 高（15+ 类信息可同屏）|
| **Codex** `bottom_pane/footer.rs` | 2017 | 极高（键位密集 + 模式 indicator + Goal 4 态）|
| **OpenCode** `routes/session/footer.tsx` | **91** | **极简（5 类信息）** |
| **OpenCode** `routes/session/subagent-footer.tsx` | 133 | 中（subagent 专用：label / siblings / tokens / **cost** / model）|
| **Claude Code** `components/StatusLine.tsx` | 323 | 高（含用户脚本覆盖管道）|

## 二、三层接触面 × 信息归属

把信息按"**用户对该信息的紧迫度**"分类，看每家**放在哪一层**：

```
顶层 always-on    : Footer / StatusBar         (每秒扫一次)
中层 in-stream    : 内联消息 / 工具结果 cell  (按需展开)
低层 on-demand    : /status dialog / Ctrl+T   (主动查询)
```

### 关键信息层级归属

| 信息 | Qwen | OpenCode | Codex | Claude |
|---|---|---|---|---|
| Model 名 | **顶层** statusLine | **低层** `/status` | **低层** `/status` | **顶层** |
| Context % | **顶层** | **低层** `/status` | **顶层** | **顶层**（仅 warning 时）|
| Cost (USD) | **不显示** | 低层 `/status` + **subagent 顶层** | **不显示** | 中层（`TokenWarning` 触发隐含）|
| Tool 执行进度 | 中层 `AnsiOutput` | 中层 per-tool 组件 | 中层 `ExecCell` 5 行限 | 中层 |
| Diff | 中层 `DiffRenderer` | 中层 `ApplyPatch` 组件 | 中层 `PatchHistoryCell` | 中层 **+ 右栏 `MoreRight` 驻留** |
| Reasoning / Thinking | 中层 `ReasoningDisplay` | 中层 `ReasoningPart` | 中层 **+ 顶层 `Alt+,/.` 实时调档** | 中层 + effort 设定 |
| Subagent 状态 | **独立 tab** `agent-view/` 950 LOC + pill | 中层 `Task` 组件**可跳转子 session** | 中层 + `multi_agents.rs` picker + collab 协议 | 中层 `CoordinatorAgentStatus` |
| Error / Warning | toast + 顶层 pill | toast + 顶层颜色 | history cell（`CyberPolicyNoticeCell`, `DeprecationNoticeCell`）| toast + 顶层 |
| Permission queue | dialog | **顶层 `△ N`** | dialog | dialog |
| Session 元数据 | 低层 `/about` | 低层 `/status` | 低层 `SessionInfoCell` | 低层 |
| MCP 健康 | **顶层 pill** | **顶层 pill** | 低层 `/mcp` | 顶层 |
| Goal 状态 | **顶层 pill** | — | **顶层 indicator 4 态** | **顶层** |

### 关键观察

- **OpenCode 把元信息（Model/Cost/MCP/Approval）几乎全推到 `/status` 弹窗**——Footer 只承载"导航锚点"
- **Qwen 把环境信息（Cwd/Model/Sandbox/Debug）全塞 statusLine + 多 pill**——Footer 承载即时全景
- **Codex 把模式（Plan/Goal）+ 操作键位（Alt+,/. / Ctrl+T / Ctrl+R）做成顶层抽象**——Footer 是动作锚点而非信息板
- **Claude 把 Token 信号做成分级 trigger**（仅紧张时才入顶层）——其他时间 Footer 干净

## 三、5 个显著差异

### ① 「成本可视化」基本缺失 —— OpenCode subagent footer 是唯一例外

**Footer 显示 cost (USD/¥) 的只有 OpenCode 的 subagent footer**。

```tsx
// opencode/.../routes/session/subagent-footer.tsx
const cost = session()?.cost ?? 0
const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
})
// ... display money.format(cost) in footer
```

Claude 间接通过 `TokenWarning` 分级（context % 触发）暗示成本压力。其他三家根本不算钱。这跟 GitHub Copilot CLI 的 `/usage`、Cursor 的 token bar 形成鲜明对比。**对自费 API key 用户是个明显空缺**——本可以做个 `BalancePill` 或 `CostToday` pill。

**为什么 OpenCode 只在 subagent footer 显示**？合理推测：subagent 是"短任务 / 临时 spawn"场景，用户对单次成本敏感；主 session 是长会话，连续显示成本反而干扰。这个产品判断值得借鉴。

### ② 「Goal pill」是 Footer 新热门趋势

| 家 | Goal Footer 表现 | 状态机 |
|---|---|---|
| Codex | `GoalStatusIndicator` 4 态 | Active / Paused / BudgetLimited / Complete |
| Qwen | `GoalPill` 4 态（`POLL_INTERVAL_MS=1000`）| set / achieved / aborted / cleared |
| Claude | v2.1.139 引入 `/goal`，位置待验证 | active / cleared |
| OpenCode | 无 `/goal` 命令 | — |

三家收敛在"**Footer Pill 是表达长 session 任务状态的最佳接触面**"。可预测的趋势是 `/plan` pill 也会进入 footer（Codex 已有）。

**Codex 的 Goal pill 子态最完整**：
- `Active { usage }` — 带耗用量
- `Paused` — `(/goal resume)` 提示
- `BudgetLimited { usage }` — 显式 `Goal unmet` / `Goal abandoned`
- `Complete { usage }` — `Goal achieved`

参 [`/goal` 命令深度对比](./goal-command-deep-dive.md)（独立专题）+ [`qwen-code-improvement-report.md` 2026-05-16 增量](./qwen-code-improvement-report-changelog.md#2026-05-16-增量goal-系列收官)（时间线演进）。

### ③ 信息密度光谱

```
极简                                                                极密
OpenCode (5项) ──────── Codex (键位密集) ──────── Qwen (15+项 + statusLine) ──── Claude (分级)
   91 LOC                  2017 LOC                    180 LOC                 323 LOC
```

不同密度对应不同**对终端用户认知负荷的假设**：

- **OpenCode**：用户**不需要每秒看到环境信息**——Footer 是导航锚点，深信息走主动查询。配合 31 个 Dialog 实现"按需展开"。
- **Codex**：用户**需要看到操作能力（键位）+ 当前模式语义**——Footer 是动作仪表盘。环境信息（cwd/model）属于 `/status`。
- **Qwen**：用户**不会主动查询**——Footer 是即时全景。窄屏走 `isNarrowWidth(terminalWidth)` 收起非关键项。
- **Claude**：用户**需要的信息分级**——平时 footer 干净，token 紧张时升级提示，关键信息靠 `MoreRight` 右栏驻留。

### ④ Codex 独有「键位实时调档」

Codex `FooterKeyHints` 含 9 个键位，最特别的是 `reasoning_down: Alt+,` / `reasoning_up: Alt+.`——**实时调节推理强度**直接显示在 footer。

```rust
// codex-rs/tui/src/bottom_pane/footer.rs
pub(crate) struct FooterKeyHints {
    pub(crate) toggle_shortcuts: Option<KeyBinding>,    // ?
    pub(crate) queue: Option<KeyBinding>,               // Tab
    pub(crate) insert_newline: Option<KeyBinding>,      // Ctrl+J
    pub(crate) external_editor: Option<KeyBinding>,     // Ctrl+G
    pub(crate) edit_previous: Option<KeyBinding>,       // Esc
    pub(crate) show_transcript: Option<KeyBinding>,     // Ctrl+T
    pub(crate) history_search: Option<KeyBinding>,      // Ctrl+R
    pub(crate) reasoning_down: Option<KeyBinding>,      // Alt+,
    pub(crate) reasoning_up: Option<KeyBinding>,        // Alt+.
}
```

**没有其他家把"调参"作为常驻 footer 元素**。其他三家都把 effort 设置藏在 `/effort` 或 model dialog 里。这是 Codex "推理可调档"哲学（详 [reasoning-effort-deep-dive.md](./reasoning-effort-deep-dive.md)）的 UI 体现。

### ⑤ Qwen `useStatusLine` 兼容 Claude `statusLine` 设置

Qwen Footer line 32：

```ts
const { lines: statusLineLines, useThemeColors } = useStatusLine();
```

支持加载**用户自定义脚本输出的多行 status line**——这跟 Claude Code 的 `settings.statusLine` 配置完全对齐（同一 spec）。这是 [statusline-setup](https://claude.ai/code) skill 的 Qwen 端等价物，**`display-components-deep-dive.md` 完全没提**。

Claude 端配套：`components/StatusLine.tsx:34` `settings?.statusLine !== undefined` 检查 + `executeStatusLineCommand` 调用用户脚本。

## 四、缺失项分析（4 家共有的盲区）

### ① Cost 可视化缺失

3/4 家完全无 USD 显示，OpenCode 也只在 subagent footer 有。**对自费 API key / pay-as-you-go 用户是显著盲区**。

可能的设计：
- `BalancePill` —— provider 账户余额（Anthropic/OpenAI 都有 API）
- `CostToday` —— 当日累计 token cost
- `CostThisSession` —— 当前 session 成本（OpenCode subagent footer 已做）
- 月度预算 + 进度条

### ② 「上下文压缩」过程不可视

四家都做 auto-compaction（详 [PR#4127](https://github.com/QwenLM/qwen-code/pull/4127) / [PR#4186](https://github.com/QwenLM/qwen-code/pull/4186)），但**没人在 footer 显示"正在压缩"或"上次压缩了 N tokens"**。

Claude 的 `TokenWarning` 在 `showAutoCompactWarning` 时显示 `autocompactLabel`，但仍是 trigger-based，不是常驻 pill。

### ③ 「跨 session 总成本」无累计

没有 `~/.<tool>/cost-history.json` 之类的跨 session 成本积累显示。每个 session 都是从零开始算。

### ④ 「最近编辑文件」无 footer 提示

四家都不在 footer 显示"刚改了哪些文件"（虽然主流编辑器都有）。这是工具中性的反馈机制空缺——只有 stream 里的 diff 才能感知，session 中段往后看就忘了。

### ⑤ 「LSP 错误数」只 OpenCode 显示

OpenCode `• N LSP` 显示已连接 LSP 数。但**没人显示当前 LSP 报告的 error 数 / warning 数**。对于"AI 写完代码我不知道有没有编译错"这个高频痛点，Footer 是天然位置。

## 五、各家信息哲学总结

| 家 | 哲学 | 核心证据 |
|---|---|---|
| **Claude Code** | "**信息分级 + 渲染层硬件加速**"——平时 footer 干净，紧张时升级，关键信息（diff）专门右栏驻留 | `TokenWarning` 2 档（warning/error，触发显示 `Context low (N% remaining) · Run /compact`）+ Ink fork 60fps + `MoreRight` 右栏 |
| **Codex** | "**模式 + 键位是顶层抽象**"——Footer 是动作仪表盘，环境信息属低层 | `CollaborationModeIndicator` (Plan/Pair/Execute) + `GoalStatusIndicator` 4 态 + 9 个 `FooterKeyHints` + `Alt+,/.` 调档 |
| **OpenCode** | "**Footer 极简，深信息走 dialog**"——91 LOC footer，5 类信息封顶；subagent footer 唯一显示 cost | 91 LOC session footer + 31 Dialog + Stack-based Promise dialog + subagent footer USD |
| **Qwen Code** | "**能塞就塞 + 窄屏自适应 + 用户脚本可覆盖**"——Footer 即时全景，但渐进降级 | 180 LOC footer + 5 个 pill (`Goal`/`MCPHealth`/`BackgroundTasks`/`AutoAccept`/`ShellMode`) + statusLine + `isNarrowWidth` + `ScreenReaderAppLayout` |

## 六、4 家相互借鉴清单

### Qwen Code 可借鉴

| 来源 | 借鉴项 | 优先级 |
|---|---|---|
| Codex | **`Alt+,/.` reasoning effort 实时调档**（footer hint）| P1 |
| Codex | **`Ctrl+T` transcript overlay**（独立查看完整 shell 输出，对应 Qwen 的 `MaxSizedBox` 限高场景）| P1 |
| Codex | `CollaborationModeIndicator` (Plan mode 顶层 pill) | P1 |
| OpenCode | **subagent footer 显示 USD cost**（agent-view 多 tab 场景特别匹配——已 spawn 多 agent，每个成本独立显示）| P0 |
| OpenCode | **`△ N Permission(s)` 顶层 pill**（permission queue 待批时） | P1 |
| OpenCode | LSP 数量 pill（如果接入 LSP 后）| P2 |
| Claude | **TokenWarning 2 档分级**（warning/error，触发 `Context low (N% remaining)`）| P1 |
| Claude | **右栏 `MoreRight` 驻留 diff**（宽屏场景）| P2 |

### Codex 可借鉴

| 来源 | 借鉴项 |
|---|---|
| Qwen | `useStatusLine` 用户脚本覆盖（兼容 Claude `settings.statusLine`） |
| Qwen | `ScreenReaderAppLayout` 可访问性布局 |
| Qwen | `Sandbox` 显式显示（`🔒 seatbelt/docker`） |
| OpenCode | LSP 数量 pill |

### OpenCode 可借鉴

| 来源 | 借鉴项 |
|---|---|
| Qwen | `useStatusLine` 用户脚本覆盖（兼容 Claude `settings.statusLine`） |
| Codex | `Alt+,/.` reasoning effort 实时调档 |
| 全员 | `/goal` slash command + GoalPill |

### Claude Code 可借鉴

| 来源 | 借鉴项 |
|---|---|
| OpenCode | session cost USD 显示（**自费用户场景**） |
| Codex | `Ctrl+T` transcript overlay |
| Qwen | `ScreenReaderAppLayout` 可访问性 |

## 七、相关文档

- [显示组件 Deep-Dive](./display-components-deep-dive.md) —— **本文 form 维度对照**（组件树 / 渲染单位 / 分派机制）
- [终端 UI Deep-Dive](./terminal-ui-deep-dive.md) —— Ink / OpenTUI / ratatui 框架选型对比
- [显示密度 Deep-Dive](./display-density-deep-dive.md) —— 单 cell 信息密度
- [SubAgent 展示 Deep-Dive](./subagent-display-deep-dive.md) —— subagent 运行状态展示
- [Reasoning Effort Deep-Dive](./reasoning-effort-deep-dive.md) —— Codex `Alt+,/.` 调档机制源
- [Qwen Code `agent-view` 多 tab UI Deep-Dive](./qwen-code-agent-view-deep-dive.md) —— Qwen 多 subagent tab 形态
- [Claude Code `/agents` 命令 Deep-Dive](./claude-code-agents-command-deep-dive.md) —— Claude 定义管理 UI

---

> **数据来源**：四家 2026-05-17 源码核实。Qwen Code `packages/cli/src/ui/components/Footer.tsx` (180 LOC) + `GoalPill.tsx` (85 LOC) + `ContextUsageDisplay.tsx` (58 LOC)；OpenCode `packages/opencode/src/cli/cmd/tui/routes/session/footer.tsx` (91 LOC) + `subagent-footer.tsx` (133 LOC)；Codex `codex-rs/tui/src/bottom_pane/footer.rs` (2017 LOC)；Claude Code `components/StatusLine.tsx` (323 LOC) + `components/TokenWarning.tsx` (178 LOC)。
