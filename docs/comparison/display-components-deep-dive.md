# 显示组件深度对比——Qwen Code / Claude Code / OpenCode / Codex

> **核心问题**：四款 Code Agent 在终端 UI 的组件构成、渲染单位、输入输出原语上各走了哪条路？谁在哪一层做了自研，谁在应用层取巧？
>
> **范围界定**：本文不比较 UI 框架选型（那在 [终端 UI 对比](./terminal-ui-deep-dive.md)），而是聚焦"屏幕上显示的具体组件"——从顶层 App 树一路下钻到历史 Cell、**按工具结果类型分派的专用渲染器**（Todo / Plan / Diff / AgentResult / ANSI Shell 等）、输入 Composer、弹窗、Footer、Markdown 渲染器。

## 一、一图看清四种技术栈

| Agent | 渲染底座 | 组件语言 | 核心显示单位 | 自研程度 |
|-------|--------|--------|----------|--------|
| **Claude Code** | 自建 Ink fork（~6,800 LOC 渲染引擎） | React/TSX | `Box`/`Text` + 144 个 components | 渲染引擎 + 应用层全自研 |
| **Qwen Code** | 标准 `ink@6.2.3` | React/TSX | `Box`/`Text` + 102 个 components | 仅应用层自研（含 `MaxSizedBox` 限高） |
| **OpenCode** | `@opentui/core@0.1.99` + `@opentui/solid` | SolidJS/TSX | `BoxRenderable` / `ScrollBoxRenderable` / `TextareaRenderable` / `<markdown>` / `<code>` | 依赖 OpenTUI，应用层约 51 个路由/组件 |
| **Codex** | 自建 `custom_terminal.rs`（ratatui fork）+ crossterm | Rust trait | `Renderable` trait + `HistoryCell` + `ChatWidget`（单一巨型 widget） | 渲染层 + 应用层全自研（`chatwidget.rs` 11.6k LOC） |

> 源码验证：
> - Qwen Code 依赖 `"ink": "^6.2.3"`（源码: `/root/git/qwen-code/packages/cli/package.json`）
> - OpenCode 依赖 `"@opentui/core": "0.1.99"`、`"@opentui/solid": "0.1.99"`（源码: `/root/git/opencode/packages/opencode/package.json`）；2026-04-24 完成 "full opentui release" 提交，替换了历史上的 Go/Bubble Tea TUI
> - Codex 依赖 `ratatui` + `crossterm`（源码: `/root/git/codex/codex-rs/tui/Cargo.toml`），`custom_terminal.rs` 头部注释标注"derived from ratatui::Terminal"
> - Claude Code Ink fork ~6,800 LOC 分布在 `ink/ink.tsx` 1,722 + `ink/screen.ts` 1,486 + `ink/render-node-to-output.ts` 1,462 + `ink/output.ts` 797 + `ink/log-update.ts` 773 等（见 [11-终端渲染](../tools/claude-code/11-terminal-rendering.md)）

## 二、顶层 App 结构

### Claude Code — `components/REPL.tsx`

Ink render 的根是 `REPL.tsx`（见 `docs/tools/claude-code/03-architecture.md#334`）。其特征：
- 支持 `MoreRight` 右侧面板（宽屏场景启用，左对话 + 右 Diff/文件预览）
- 双入口：交互模式走 Ink render，非交互模式走纯 stdout 流
- 组件树有 ~144 个子组件

### Qwen Code — `App.tsx` → 双布局分叉

源码: `/root/git/qwen-code/packages/cli/src/ui/App.tsx`

```tsx
export const App = () => {
  const uiState = useUIState();
  const isScreenReaderEnabled = useIsScreenReaderEnabled();
  if (uiState.quittingMessages) return <QuittingDisplay />;
  return (
    <StreamingContext.Provider value={uiState.streamingState}>
      {isScreenReaderEnabled ? <ScreenReaderAppLayout /> : <DefaultAppLayout />}
    </StreamingContext.Provider>
  );
};
```

根据 `useIsScreenReaderEnabled()`（Ink 内置）分两条渲染路径：
- `DefaultAppLayout`：常规布局，`<MainContent>` + `<Composer>` + `<DialogManager>`
- `ScreenReaderAppLayout`：语义化布局，`Footer` 置顶便于读屏器优先朗读

### OpenCode — `app.tsx` → Route + Provider 金字塔

源码: `/root/git/opencode/packages/opencode/src/cli/cmd/tui/app.tsx`

App 组件嵌套了 20+ 层 Provider（SolidJS context）：

```
RouteProvider → ThemeProvider → KeybindProvider → SDKProvider
  → LocalProvider → SyncProvider → ProjectProvider → KVProvider
  → ArgsProvider → PromptRefProvider → TuiConfigProvider
  → ExitProvider → ToastProvider → DialogProvider → CommandProvider
  → PromptHistoryProvider → FrecencyProvider → PromptStashProvider
  → FrontendPluginProvider → EditorContextProvider
  → Switch/Match → Home route / Session route
```

路由系统仅两个顶层路由：`Home`（连接/会话列表）和 `Session`（对话界面）。

### Codex — `app.rs` → 唯一 ChatWidget

源码: `/root/git/codex/codex-rs/tui/src/chatwidget.rs#1765`

与前三者不同，Codex 的顶层 `App` 下只有一个巨型 `ChatWidget`（11,631 LOC），内部集中管理：

```rust
pub(crate) struct ChatWidget {
    // 已提交的 transcript cells
    history_cells: Vec<Box<dyn HistoryCell>>,
    // 流式中的 active cell（可原地 mutate）
    active_cell: Option<Box<dyn HistoryCell>>,
    // 底部输入区
    bottom_pane: BottomPane,
    // 其它协议状态...
}

impl Renderable for ChatWidget {
    fn render(&self, area: Rect, buf: &mut Buffer) { ... }
    fn desired_height(&self, width: u16) -> u16 { ... }
    fn cursor_pos(&self, area: Rect) -> Option<(u16, u16)> { ... }
}
```

> 设计权衡：Codex 用 Rust trait + 一个 God Widget，组件边界由 trait 切分；而 JS 阵营靠 React/Solid 的组件树。Codex 的组件复用度最低但性能最稳。

## 三、历史/消息的渲染单位

### Qwen Code — Ink `<Static>` + HistoryItemDisplay

源码: `/root/git/qwen-code/packages/cli/src/ui/components/MainContent.tsx#89`

```tsx
<Static
  key={`${uiState.historyRemountKey}-${uiState.currentModel}`}
  items={[
    <AppHeader key="app-header" version={version} />,
    <DebugModeNotification key="debug-notification" />,
    <Notifications key="notifications" />,
    ...mergedHistory.map((h) => <HistoryItemDisplay ... />),
  ]}
>
  {(item) => item}
</Static>
<OverflowProvider>
  <Box flexDirection="column">
    {pendingHistoryItems.map((item, i) => <HistoryItemDisplay ... isPending />)}
  </Box>
</OverflowProvider>
```

关键机制：
- **已完成条目走 `<Static>`**（append-only，Ink 不重绘），节省重渲染成本
- **流式中条目走普通 `<Box>`** + `OverflowProvider`
- **合并优化**：`mergeCompactToolGroups` 把连续 tool_group 合并为一个；检测到合并后调用 `refreshStatic()` bump key 强制 Static 全量重渲染
- `HistoryItemDisplay` 内按 `type` 分派到 `ToolGroupMessage` / `ToolMessage` / `CompactToolGroupDisplay` / `DiffRenderer` / `SummaryMessage` / `BtwMessage` 等（13 种消息组件，源码: `packages/cli/src/ui/components/messages/`）

### Claude Code — Ink fork `<Static>` + 硬件滚动

从 11-terminal-rendering 文档可知 Claude Code 在 Ink fork 层引入了 **DECSTBM 硬件滚动** + **Damage Tracking**，这让 Static 条目更新时不需要全屏重绘，而是仅标记变化的 cell。这是 Qwen Code 当前做不到的（标准 Ink 会在 Static 之外的区域触发全屏重绘导致闪烁）。

Claude Code 应用层同样是 Message 组件按类型分派，但渲染层的硬件滚动让 500 行 shell 输出不会卡顿。

### OpenCode — ScrollBoxRenderable + SolidJS `<For>`

源码: `/root/git/opencode/packages/opencode/src/cli/cmd/tui/routes/session/index.tsx`

```tsx
let scroll: ScrollBoxRenderable
// ...
<For each={messages()}>{(message) =>
  <For each={message.parts}>{(part) =>
    <Dynamic component={partComponent(part.type)} part={part} />
  }</For>
}</For>
```

特点：
- **ScrollBoxRenderable**（来自 `@opentui/core`）提供**原生终端滚动**，不需要手工计算 scrollback
- SolidJS `<For>` 只做增量 DOM（这里是 Renderable tree）变更——新增消息不会重建既有节点
- `<Dynamic>` 按 part 类型动态选择渲染器：`TextPart` / `ToolPart` / `ReasoningPart`
- `TextPart` 进一步根据 `Flag.OPENCODE_EXPERIMENTAL_MARKDOWN` 选择 `<markdown>` 或 `<code filetype="markdown">`（见第七节）

### Codex — HistoryCell trait + 双层 cell 机制

源码: `/root/git/codex/codex-rs/tui/src/history_cell.rs`

```rust
pub(crate) trait HistoryCell: Renderable {
    fn transcript_lines(&self, width: u16) -> Vec<Line<'_>>;
    // 用于 Ctrl+T 打开的 transcript overlay
    fn transcript_animation_tick(&self) -> Option<Instant>;
    // 时间相关的 cell 返回下次 tick 时刻，用于驱动 cache 失效
    // ...
}
```

Codex 的独特设计是 **双层 cell**：
1. **committed cells**（`history_cells: Vec<Box<dyn HistoryCell>>`）——已完成，不再变
2. **active_cell**（`Option<Box<dyn HistoryCell>>`）——当前流式的 cell，**可原地 mutate**（即合并来自同一 tool call 的多段输出），常见于 exec/tool group

| Cell 类型 | LOC（约） | 用途 |
|--------|-------|----|
| `ExecCell`（`exec_cell/`） | ~800 | Bash 命令执行显示，含 stdout/stderr 流式 |
| `HistoryCell` 多种实现（`history_cell.rs`） | 4,921 | User/Assistant/Diff/Plan/MCP 各种条目 |
| `hook_cell.rs` | - | Hook 执行显示 |

`ExecCell` 硬编码了 `TOOL_CALL_MAX_LINES = 5`（`exec_cell/render.rs`）——shell 输出默认只显示最后 5 行，更多请按 Ctrl+T 看完整 transcript。

## 四、按结果类型分派的专用渲染器（Tool Result Dispatch）

第三节讲的是"历史条目"这个容器级单位，但每个 tool 的**执行结果**还需要按 `type` 再分派到不同的专用渲染器（Todo 列表长得像 Todo，文件 Diff 长得像 Diff，子 Agent 结果长得像时间轴）。这一层是组件体系中差异最大、代码量最大的部分，也是用户感知最直接的部分。

### Qwen Code — `DisplayRendererResult` 判别式联合

源码: `packages/cli/src/ui/components/messages/ToolMessage.tsx#50-110`

```tsx
type DisplayRendererResult =
  | { type: 'none' }
  | { type: 'todo';   data: TodoResultDisplay }      // → TodoDisplay.tsx
  | { type: 'plan';   data: PlanResultDisplay }      // → PlanSummaryDisplay.tsx
  | { type: 'string'; data: string }                 // → MarkdownDisplay / plain Text
  | { type: 'diff';   data: { fileDiff; fileName } } // → DiffRenderer.tsx
  | { type: 'task';   data: AgentResultDisplay }     // → AgentExecutionDisplay.tsx
  | { type: 'ansi';   data: AnsiOutput; stats?: ShellStatsBarProps }; // → AnsiOutput.tsx + ShellStatsBar

const useResultDisplayRenderer = (resultDisplay) => React.useMemo(() => {
  if (resultDisplay?.type === 'todo_list')       return { type: 'todo', data: ... };
  if (resultDisplay?.type === 'plan_summary')    return { type: 'plan', data: ... };
  if (resultDisplay?.type === 'task_execution')  return { type: 'task', data: ... };
  if (fileDiff && fileName)                      return { type: 'diff', data: ... };
  // ...
});
```

| 类型 | 专用组件 | 关键能力 |
|----|------|------|
| `todo` | `TodoDisplay.tsx` | 复选框列表、状态图标（pending/in_progress/completed） |
| `plan` | `PlanSummaryDisplay.tsx` | Plan 模式步骤概览 |
| `task` | `AgentExecutionDisplay.tsx`（`components/subagents/runtime/`） | **子 Agent 执行时间轴 + Ctrl+E/F 三档折叠** |
| `diff` | `DiffRenderer.tsx` | 文件 Diff 语法高亮 |
| `ansi` | `AnsiOutput.tsx` + `ShellStatsBar` | Shell 执行彩色输出 + 耗时/退出码 |
| `string` | `MarkdownDisplay.tsx` 或 `<Text>` | 根据 `renderAsMarkdown` flag |

`AgentExecutionDisplay`（用户点名的 `AgentResultDisplay` 消费端）位于 `subagents/runtime/` 子目录，包含完整的子 Agent 执行记录（工具调用列表、token/时长统计、焦点锁机制），不与其他消息组件混在一起 —— 这是 Qwen Code 的一个独立设计，具体参见 [SubAgent 展示 Deep-Dive](./subagent-display-deep-dive.md)。

### OpenCode — `ToolPart` Switch + 15 个 per-tool 函数组件

源码: `routes/session/index.tsx#1516-1609`

```tsx
function ToolPart(props) {
  return <Switch>
    <Match when={part.tool === "bash"}>       <Bash {...toolprops} />       </Match>
    <Match when={part.tool === "read"}>       <Read {...toolprops} />       </Match>
    <Match when={part.tool === "edit"}>       <Edit {...toolprops} />       </Match>
    <Match when={part.tool === "write"}>      <Write {...toolprops} />      </Match>
    <Match when={part.tool === "grep"}>       <Grep {...toolprops} />       </Match>
    <Match when={part.tool === "glob"}>       <Glob {...toolprops} />       </Match>
    <Match when={part.tool === "webfetch"}>   <WebFetch {...toolprops} />   </Match>
    <Match when={part.tool === "websearch"}>  <WebSearch {...toolprops} />  </Match>
    <Match when={part.tool === "codesearch"}> <CodeSearch {...toolprops} /> </Match>
    <Match when={part.tool === "task"}>       <Task {...toolprops} />       </Match>
    <Match when={part.tool === "apply_patch"}><ApplyPatch {...toolprops} /> </Match>
    <Match when={part.tool === "todowrite"}>  <TodoWrite {...toolprops} />  </Match>
    <Match when={part.tool === "question"}>   <Question {...toolprops} />   </Match>
    <Match when={part.tool === "skill"}>      <Skill {...toolprops} />      </Match>
    <Match when={true}>                       <GenericTool {...toolprops} /></Match>
  </Switch>
}
```

OpenCode 的分派更激进——**按工具名**而非按结果形状分派。每个 per-tool 组件内部再用 `<InlineTool>` 或 `<BlockTool>` 两个 layout 原语包一层：

- `InlineTool`：单行摘要，适合 read/glob/grep 等结果不大的
- `BlockTool`：带标题的块，适合 TodoWrite / Question / ApplyPatch 等有丰富状态的

子 Agent 对应 `Task` 组件（`index.tsx#1969-2037`），有跳转子会话的能力（`navigate({ type: "session", sessionID })`）——这是 OpenCode 独有的"点击进入子 Agent 详情"交互。

### Codex — 20+ 个独立 Cell struct + `new_*` 工厂

源码: `tui/src/history_cell.rs`

Codex 不走 switch/match 分派，而是**把每种消息类型做成独立的 Rust struct**，由工厂函数构造：

| Cell struct | LOC 文件 | 用途 |
|---|---|---|
| `UserHistoryCell` | - | 用户输入消息 |
| `AgentMessageCell` | - | Assistant 回复 |
| `ReasoningSummaryCell` | - | 思维链摘要 |
| `UnifiedExecInteractionCell` | - | Bash/exec 执行（对应 Qwen 的 `ansi` + `ShellStatsBar`） |
| `PatchHistoryCell` | - | 文件 Patch（对应 Qwen 的 `diff`） |
| `McpToolCallCell` | - | MCP 工具调用 |
| `WebSearchCell` | - | Web 搜索 |
| `ProposedPlanCell` / `ProposedPlanStreamCell` | - | Plan 提议（对应 Qwen 的 `plan`） |
| `PlanUpdateCell` | - | Plan 步骤更新 |
| `RequestUserInputResultCell` | - | 用户问答（对应 OpenCode 的 `Question`） |
| `SessionInfoCell` / `SessionHeaderHistoryCell` | - | 会话元信息 |
| `McpInventoryLoadingCell` | - | MCP 启动进度 |
| `CompositeHistoryCell` | - | 多 cell 组合容器 |
| `CyberPolicyNoticeCell` / `DeprecationNoticeCell` | - | 告示 |
| `PlainHistoryCell` / `PrefixedWrappedHistoryCell` / `UpdateAvailableHistoryCell` | - | 通用容器 |

`history_cell.rs` 4,921 LOC 里定义了 40+ 个 `new_*` 工厂函数（`new_unified_exec_interaction`、`new_approval_decision_cell`、`new_session_info`、`new_user_prompt`、`new_active_mcp_tool_call`、`new_plan_update`、`new_proposed_plan`、`new_patch_event` 等），每个函数接受协议事件输出对应 Cell。

子 Agent 在 Codex 里对应的是 **`multi_agents.rs`** 里的 Collab Agent 机制，不是一个单独的 cell 类型——Codex 的子 Agent 开一个独立 ChatWidget thread，在主界面只留摘要。

### Claude Code — 应用层 144 组件 + 文档已另述

从现有文档可提取的专用渲染器：
- `AgentTool.tsx` —— Task 工具内联模式（类似 Qwen 的 `AgentExecutionDisplay` 但更简洁）
- `CoordinatorAgentStatus.tsx` —— Coordinator 多 agent 后台面板（Qwen/OpenCode 都没有对等物）
- `AgentProgressLine.tsx` —— agent 带色身份标签
- `TokenWarning.tsx` —— Token 使用分级警告
- `DiffRenderer`（组件名从 02/04 文档推断）
- `TodoDisplay` / Todo 相关组件
- `MoreRight` —— 右侧面板（对 ToolPart 结果做"驻留展示"）

详细分析见 [SubAgent 展示 Deep-Dive](./subagent-display-deep-dive.md) 和 [Token 警告](./token-warning-deep-dive.md)（如存在）。

### 分派机制对比

| 维度 | Qwen Code | OpenCode | Codex | Claude Code |
|---|---|---|---|---|
| 分派依据 | 结果 `type` 字段 | 工具名 `tool` 字段 | 事件类型 → 工厂函数 | 推断为 `type` 字段 |
| 分派形式 | `useMemo` 判别式联合 | SolidJS `<Switch>` | Rust struct + `new_*` 工厂 | React 条件渲染 |
| 新增工具成本 | 扩 `DisplayRendererResult` + 新增 Display 组件 | 扩 `<Switch>` + 新增函数组件 | 新增 struct + new_ 工厂 + impl HistoryCell | 新增 React 组件 |
| Layout 原语 | `Box` 直接用 | `InlineTool` / `BlockTool` 二选一 | Renderable trait 自由组合 | Ink Box/Text |
| 子 Agent 专用组件 | `AgentExecutionDisplay`（独立子目录） | `Task` 函数（内嵌路由） | `multi_agents.rs`（独立模块） | `AgentTool` + `CoordinatorAgentStatus` 双模式 |

**关键洞察**：
- **Qwen Code 和 Codex 按"结果形状"分派**——Todo 列表不管是哪个工具产出的都走同一渲染器。这符合"数据驱动 UI"。
- **OpenCode 按"工具名"分派**——即便两个工具产出同一种结果，也要各自写 per-tool 组件。这更直观但重复更多。
- **Codex 的 struct + factory 在编译期强类型保证**——新增 cell 类型编译器会提示所有相关位置，JS 阵营靠 TypeScript 联合类型达到类似效果（Qwen 做到了，OpenCode 的 ToolProps 也做到了）。

## 五、输入 Composer / Prompt

| Agent | 文件 | LOC | 关键能力 |
|------|----|-----|-------|
| Qwen Code | `Composer.tsx` + `BaseTextInput.tsx` | 155 + - | 基础文本输入 + `/` 命令 + `@` 文件引用 + vim 模式 |
| Claude Code | `components/Composer.tsx`（未公开） | - | 自建 text-input，支持 vim 模式（`/vim`）、剪贴板粘贴、IME、候选建议 |
| OpenCode | `component/prompt/index.tsx` | 1,415 | 基于 `TextareaRenderable`（OpenTUI 原语）+ paste event 解码 + autocomplete + frecency + stash |
| Codex | `bottom_pane/chat_composer.rs` | **9,147** | 自建 textarea + slash popup + file_search popup + mention popup + history search + paste_burst |

Codex 的 Composer 异常庞大，因为它把**所有弹窗状态**（`chat_composer`、`command_popup`、`file_search_popup`、`paste_burst`）都塞在 bottom_pane 下。`chat_composer.rs` 开头就声明了它的路由逻辑：

```rust
//! - Routing keys to the active popup (slash commands, file search, skill/apps mentions).
//! popup-specific handler if a popup is visible and otherwise to
//! [`ChatComposer::handle_key_event_without_popup`].
```

OpenCode 则利用 OpenTUI 自带的 `TextareaRenderable` 原语 + `PasteEvent`/`decodePasteBytes`，省去了逐键重建文本 buffer 的成本。

Qwen Code 最简单，因为它直接复用 Ink 生态的 `ink-text-input` 思路（自写在 `BaseTextInput.tsx`）。

## 六、弹窗 / 对话框系统

### Qwen Code — `DialogManager.tsx` 路由

源码: `packages/cli/src/ui/components/DialogManager.tsx`

集中式 DialogManager，按 `uiState.dialogsVisible` 与当前对话框类型分派到具体 Dialog 组件：`ApprovalModeDialog`、`FolderTrustDialog`、`EditorSettingsDialog`、`AskUserQuestionDialog`、`ToolConfirmationMessage` 等。

### OpenCode — Stack-based Dialog Provider

源码: `component/dialog-provider.tsx` + `ui/dialog.tsx`

OpenCode 实现了**基于栈的对话框**系统——每个 dialog 是一个 Promise 的异步调用：

```tsx
void DialogGoUpsell.show(dialog).then((dontShowAgain) => { ... })
```

dialog stack 支持多层叠放，`dialog.stack.length > 0` 可判断当前是否有弹窗。已知 20+ 个 Dialog 组件：

```
DialogAgent, DialogCommand, DialogConsoleOrg, DialogGoUpsell, DialogMcp,
DialogModel, DialogProvider, DialogSessionDeleteFailed, DialogSessionList,
DialogSessionRename, DialogSkill, DialogStash, DialogStatus, DialogTag,
DialogThemeList, DialogVariant, DialogWorkspaceCreate, DialogWorkspaceUnavailable,
DialogAlert, DialogConfirm, DialogExportOptions, DialogHelp, DialogPrompt,
DialogSelect, DialogTimeline, DialogForkFromTimeline, DialogMessage, DialogSubagent
```

源码目录: `component/dialog-*.tsx`（22 个） + `ui/dialog-*.tsx`（6 个） + `routes/session/dialog-*.tsx`（3 个）。

### Codex — bottom_pane/*_view.rs

源码: `/root/git/codex/codex-rs/tui/src/bottom_pane/`

Codex 把所有弹窗都作为 `bottom_pane` 的子 view：

```
approval_overlay.rs       - 审批弹窗
command_popup.rs          - 斜杠命令 popup
file_search_popup.rs      - 文件搜索 popup（@ 触发）
custom_prompt_view.rs     - 自定义 prompt 编辑
experimental_features_view.rs
feedback_view.rs          - 反馈提交
list_selection_view.rs    - 列表选择
mcp_server_elicitation.rs - MCP server 配置
memories_settings_view.rs
multi_select_picker.rs    - 多选
pending_input_preview.rs  - 粘贴预览
paste_burst.rs            - 大量粘贴防抖
```

每个 view 都实现 `BottomPaneView` trait（`bottom_pane_view.rs`），由 `bottom_pane/mod.rs`（2,352 LOC）统一管理焦点路由。

### Claude Code

从公开文档可知 Claude Code 有类似 `TokenWarning.tsx`、`ExitWarning`、各类 approval dialog，但由于闭源，无法枚举完整列表。从 `components/` 目录有 144 个文件可推断弹窗组件数量在 Qwen Code（约 15 个 dialog）和 OpenCode（31 个 dialog）之间。

## 七、Footer / 状态栏

| Agent | 文件 | LOC | 内容 |
|-----|----|-----|----|
| Qwen Code | `Footer.tsx` | 172 | Cwd + Model + ContextUsageDisplay + AutoAcceptIndicator + ShellModeIndicator + Dream 运行指示 |
| Claude Code | `components/StatusBar.*`（未公开） | - | Token 警告（分级黄/红）+ VimMode + Context 压缩状态 + 动态更新指示 |
| OpenCode | `routes/session/footer.tsx` + `subagent-footer.tsx` | - | 双 Footer（主会话 + 子 agent） |
| Codex | `bottom_pane/footer.rs` | - | 快捷键提示 + 模式指示 |

Qwen Code 的 Footer 用了 `useSyncExternalStore` 订阅 MemoryManager 的变化（`useDreamRunning`），零轮询开销；这是 React 18 推荐的外部 store 接入方式。

## 八、Markdown & 语法高亮

**这是四者差异最大的一层。**

| Agent | Markdown 渲染器 | 语法高亮引擎 | 流式支持 |
|-----|------------|----------|------|
| **Qwen Code** | 自写 `MarkdownDisplay.tsx` + `InlineMarkdownRenderer.tsx` | 无（Text 组件静态样式） | ✗ |
| **Claude Code** | React 自写 | （未公开） | ✓（自建 Ink fork 60fps 节流） |
| **OpenCode** | OpenTUI 原生 `<markdown>` 元素 + tree-sitter WASM 解析器 | **tree-sitter**（~30 种语言，`parsers-config.ts`：Python/Rust/Go/TS/JS/Markdown/HTML/CSS/YAML/JSON/…） | ✓（`streaming={true}` 属性） |
| **Codex** | `markdown_render.rs`（1,136 LOC）+ `markdown_stream.rs`（725 LOC） | **syntect + two_face**（~250 种语言，32 个主题） | ✓（markdown_stream 专门处理流式） |

OpenCode 的 markdown 切换在会话组件里：

```tsx
<Switch>
  <Match when={Flag.OPENCODE_EXPERIMENTAL_MARKDOWN}>
    <markdown
      syntaxStyle={syntax()}
      streaming={true}
      content={props.part.text.trim()}
    />
  </Match>
  <Match when={!Flag.OPENCODE_EXPERIMENTAL_MARKDOWN}>
    <code filetype="markdown" drawUnstyledText={false} streaming={true} ... />
  </Match>
</Switch>
```

> 源码: `routes/session/index.tsx#1480-1500`。`<markdown>` 和 `<code>` 都是 OpenTUI 原生 JSX 元素，底层由 tree-sitter 实现。

Codex 的 syntect 覆盖面最广（250+ 语言 vs OpenCode 的 30+），但需要把语法语法包编译进二进制，体积较大。

## 九、溢出 / 限高策略

| Agent | 策略 | 层级 |
|-----|----|---|
| **Qwen Code** | `MaxSizedBox.tsx`（视觉裁剪，渲染后 slice） | 应用层 |
| **Claude Code** | DECSTBM 硬件滚动 + Damage Tracking | 渲染引擎层 |
| **OpenCode** | `ScrollBoxRenderable` 原生滚动 | OpenTUI 原语层 |
| **Codex** | `TOOL_CALL_MAX_LINES = 5` 硬上限 + Ctrl+T transcript overlay 查看完整 | 应用层 + 独立 overlay |

Qwen Code 的应用层限高是**视觉裁剪**——数据已经渲染，只是不显示超出部分；这会导致 Ink 仍然要布局全部行，大输出仍然卡。Claude Code 在 Ink fork 层改造了布局引擎，这是真正的底层方案。

OpenCode 依赖 OpenTUI 的 ScrollBox 原生支持终端滚动，不需要手工计算。

Codex 的 `TOOL_CALL_MAX_LINES = 5` 更激进——**默认只显示 5 行 shell 输出**，剩余要看 Ctrl+T 的 transcript overlay（这是 Codex 特有的"双视图"设计）。

## 十、主题系统

| Agent | 主题切换 | 主题数量 | 实现 |
|-----|-------|-------|----|
| Qwen Code | `/theme` 命令 | ~10（继承 Gemini CLI） | `semantic-colors.ts` |
| Claude Code | `/theme` + `/color` | Dark/Light/Daltonized | （未公开） |
| OpenCode | `/theme` + DialogThemeList | **37 种** | `ThemeProvider` SolidJS context |
| Codex | `/themes` 命令 | 32（来自 two_face bundle） | `render/highlight.rs#set_theme_override` |

OpenCode 的 37 个主题最多，来自社区贡献；Codex 的 32 个主题质量最高（two_face 精选）。

## 十一、无障碍（Accessibility）

| Agent | 读屏器支持 |
|-----|-------|
| **Qwen Code** | ✓ `ScreenReaderAppLayout`（Footer 顶置、无 Static、去除装饰元素）|
| **Claude Code** | ✓（Ink 内建 `useIsScreenReaderEnabled`）|
| **OpenCode** | ✗ 明确支持 |
| **Codex** | ✗ 明确支持 |

Qwen Code 的 `ScreenReaderAppLayout.tsx` 是所有四者中**唯一**有专用读屏器布局的：
- 移除 `<Static>` 的 append-only 行为（读屏器需要重新朗读历史）
- Footer 置顶便于读屏器优先发现
- 对话框直接嵌入主流

这继承自 Gemini CLI，其它三家暂未发现类似设计。

## 十二、ANSI / 颜色处理

| Agent | 颜色模型 | ANSI 字节流处理 |
|-----|-------|------------|
| **Qwen Code** | Ink 的命名颜色 + hex | `AnsiOutput.tsx` 将 ANSI token 流转为 Ink Text tree（90 LOC） |
| **Claude Code** | Ink fork StylePool + CharPool（缓存复用） | `ink/output.ts` 自建 CharCache |
| **OpenCode** | `RGBA` + `TextAttributes`（OpenTUI 类型） | 由 OpenTUI 底层处理；paste 走 `decodePasteBytes` |
| **Codex** | ratatui `Color` + `Style` + `Modifier` | `codex_ansi_escape::ansi_escape_line` 将 ANSI 转 `Span` |

Qwen Code 的 `AnsiOutput.tsx` 简单直接，但每次都要重新构造组件树（没有 pool 复用），大输出开销大。Claude Code 在 fork 层加了缓存池化。

## 十三、取舍总结

### 按"自研层级"排序

| 层级 | Claude Code | Codex | OpenCode | Qwen Code |
|-----|---|---|---|---|
| 渲染引擎层 | **自建 Ink fork** | **自建 ratatui Terminal** | 依赖 OpenTUI | 依赖 Ink |
| 组件原语 | Ink Box/Text | `Renderable` trait | OpenTUI BoxRenderable/ScrollBox/Textarea | Ink Box/Text |
| 应用组件 | ~144 个 React 组件 | `chatwidget.rs` 单体 + 10+ cell 类型 | ~51 个 SolidJS 组件 | ~102 个 React 组件 |
| Markdown | 自写 React 渲染器 | syntect + markdown_render | tree-sitter via OpenTUI | 自写 MarkdownDisplay |

### 设计哲学

- **Claude Code / Codex = "我全都要"**：底层渲染引擎和应用组件全自建，换来最佳性能和完全控制，代价是高维护成本（Claude Code 的 Ink fork 无法合并 Ink 上游更新；Codex 的 chatwidget.rs 11.6k LOC 单文件）。
- **OpenCode = "押注新框架"**：深度依赖 OpenTUI（v0.1.x 仍在剧烈演进），2026-04 刚完成 "full opentui release" 迁移；换来 SolidJS 的细粒度响应式和原生 tree-sitter 高亮，但框架变动风险显著（仓库里能看到 `pin opentui` → revert → `upgrade opentui to 0.1.102` → `roll back` 的反复）。
- **Qwen Code = "标准生态 + 应用层补丁"**：用标准 Ink 6 降低维护负担，大输出问题靠 `MaxSizedBox` 视觉裁剪。这是成本最低的方案但也是性能最弱的——当 Gemini CLI 上游做出 `SlicingMaxSizedBox`（渲染前裁剪）改进时 Qwen Code 立即受益，但渲染层的闪烁仍无法根治。

### 给 Qwen Code 的启示（已在 [11-终端渲染](../tools/claude-code/11-terminal-rendering.md) 详述）

- 不必立即 fork Ink；可先补齐 `SlicingMaxSizedBox`（渲染前裁剪）对齐 Gemini CLI 上游
- ScrollBox-like 原语是值得研究的中间方案（OpenCode 已经证明可行性）
- Markdown 渲染器升级到 tree-sitter 或 syntect 级别可大幅提升体验

### 给其它 Agent 的启示

- **Codex 的双层 cell**（committed + active）值得 Ink 阵营借鉴：目前 Qwen/Claude Code 的 "Static + pending" 二元划分是类似思路，但 Codex 的 trait + 原地 mutate 在性能上更优
- **OpenCode 的 Stack-based Dialog Promise** 是极佳的 UX 模式，React 阵营可参考（Claude Code 已类似实现）
- **Qwen Code 的 ScreenReaderAppLayout** 是可访问性标杆，建议其它三家跟进

## 证据来源

- Qwen Code: `/root/git/qwen-code/packages/cli/src/ui/` 全量源码
- Claude Code: [11. 终端渲染](../tools/claude-code/11-terminal-rendering.md)、[03. 架构](../tools/claude-code/03-architecture.md)、[EVIDENCE.md](../tools/claude-code/EVIDENCE.md)（反编译分析）
- OpenCode: `/root/git/opencode/packages/opencode/src/cli/cmd/tui/` 全量源码 + `parsers-config.ts` + git log（opentui 迁移历史）
- Codex: `/root/git/codex/codex-rs/tui/src/` 全量源码

> **免责声明**：基于 2026-04-24 各仓库主分支快照。OpenCode 的 OpenTUI 集成仍在 v0.1.x 阶段，后续可能有重大变动。Claude Code 的应用层组件名部分来自反编译，可能与官方命名有微小差异。
