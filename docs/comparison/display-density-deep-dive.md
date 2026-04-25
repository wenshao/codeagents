# 显示信息密度深度对比 — Claude Code / Qwen Code / OpenCode

> **核心问题**：用户报告 "Claude Code 看起来信息密度比 Qwen Code 高"。这是 UI 框架差异（都用 Ink/React），还是组件层的结构性"空间收税"？逐项源码追溯。OpenCode 用了 SolidJS + OpenTUI 的全新栈，在密度光谱上落在哪？
>
> **结论先行**：在标准 30×80 窄屏（很多用户的 tmux 分屏宽度）上，三者形成清晰光谱——Qwen Code 比 Claude Code **多消耗 ~40% 垂直空间**用于装饰性元素（边框/空行/banner/marginTop）；**OpenCode 落在中间**，用 single-side border + 背景着色替代了完整 box border，比 Qwen 省 ~25% 空间但仍多于 Claude。这不是字号或缩写问题，而是 4 类组件层的结构选择。

## 一、30×80 同场景对比（同一 prompt，3 个工具调用）

### Qwen Code（首屏布局）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1: ▄▄▄▄▄▄  ▄▄     ▄▄ ▄▄▄▄▄▄▄ ▄▄▄    ▄▄  ┌────────────────────────────────┐  │ ← 边框 + 空行 panel
│ 2:██╔═══██╗██║    ██║██╔════╝████╗  ██║ │ >_ Qwen Code (v0.15.2)         │  │
│ 3:██║   ██║██║ █╗ ██║█████╗  ██╔██╗ ██║ │                                │  │ ← 显式空行 padding
│ 4:██║▄▄ ██║██║███╗██║██╔══╝  ██║╚██╗██║ │ Qwen OAuth | qwen3-coder-plus  │  │
│ 5:╚██████╔╝╚███╔███╔╝███████╗██║ ╚████║ │ ~/work/proj                    │  │
│ 6: ╚══▀▀═╝  ╚══╝╚══╝ ╚══════╝╚═╝  ╚═══╝ └────────────────────────────────┘  │
│ 7:                                                                            │ ← logo 第 7 行（空白）
│ 8:Tips: Type / to see all available commands.                                │
│ 9:                                                                            │ ← marginTop=1
│10:> read package.json                                                         │ ← User message
│11:                                                                            │ ← marginTop=1
│12: ╭──────────────────────────────────────────────────────────────────────╮  │ ← borderStyle="round" 上
│13: │ ● ReadFile package.json                                                │ │
│14: │                                                                        │ │ ← gap={1}
│15: │ ● WriteFile main.ts (15 lines)                                         │ │
│16: │                                                                        │ │ ← gap={1}
│17: │ ● Bash npm install                                                     │ │
│18: ╰──────────────────────────────────────────────────────────────────────╯  │ ← border 下
│19:                                                                            │ ← marginBottom=1
│20:                                                                            │ ← HistoryItem marginTop=1
│21:│ Done. Updated package.json and ran npm install.                          │
│22:                                                                            │ ← marginTop=1 between items
│23:╭────────────────────────────────────────────────────────────────────────╮ │
│24:│ > █                                                                     │ │ ← Composer (3 行框)
│25:╰────────────────────────────────────────────────────────────────────────╯ │
│26:Status line line 1                                                          │ ← Footer 多行
│27:? for shortcuts        🔒 docker | 45% (89,234 / 200,000) | ✦ dreaming     │
└──────────────────────────────────────────────────────────────────────────────┘
   还能放下: ~3 行可见对话内容
```

### Claude Code（首屏布局，等价 prompt）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1:✻ Welcome to Claude Code — claude-opus-4-7 — ~/work/proj                   │ ← 1 行 banner
│ 2:                                                                            │
│ 3:> read package.json                                                         │
│ 4:                                                                            │
│ 5:⏺ Read(package.json)                                                        │ ← 单行工具
│ 6:  ⎿ Read 23 lines                                                           │ ← 单行结果
│ 7:                                                                            │
│ 8:⏺ Write(main.ts)                                                            │
│ 9:  ⎿ Wrote 15 lines                                                          │
│10:                                                                            │
│11:⏺ Bash(npm install)                                                         │
│12:  ⎿ added 47 packages in 8s                                                 │
│13:                                                                            │
│14:Done. Updated package.json and ran npm install.                             │
│15:                                                                            │
│16:│ > █                                                                       │ ← Composer (1 行)
│17:                                                                            │
│18:                                                                            │
│       (~10 行可见上下文)                                                       │
│27:                                                                            │
│28: ~/work/proj  …(45% · 89.2k/200k)         ⏵⏵ accept edits  ? for shortcuts │ ← Footer 1 行
└──────────────────────────────────────────────────────────────────────────────┘
   还能放下: ~10 行可见对话内容
```

**净差异**：在同样的 30×80 屏 + 同样的对话内容下，Qwen 留给历史/对话的可见区域是 **~3 行**，Claude 是 **~10 行**——3 倍差距。

## 二、4 类结构性"空间收税"

### 收税点 1：启动 Banner（一次性，但首屏占比最大）

| 项 | Qwen Code | Claude Code |
|---|---|---|
| ASCII Logo | 7 行 `shortAsciiLogo`（源码: `AsciiArt.ts#9-16`） | 单行 `✻ Welcome to Claude Code` |
| Info Panel | 4 行（标题 + **显式空行** + auth/model + cwd）+ 上下 border = **6 行** | 内联在 banner 同一行 |
| Tips | 1 行（`Tips.tsx`，仅 `marginLeft=2 marginRight=2`，无 marginTop） | 不显示（已并入命令补全） |
| **总计** | **~8 行**（logo 与 panel 并排 max + tip） | **~1 行** |

源码：
- `Header.tsx#147-149`：`<Text> </Text> {/* Empty line for spacing */}` —— **代码注释直接承认是装饰性空行**
- `Header.tsx#108-115`：bordered info panel 用 `borderStyle="single" + paddingX=1`
- `AppHeader.tsx#67-72`：`<Header />` 后无条件 `<Tips />`（除非显式 `hideTips`）

**为什么 Claude 不需要这些**？因为模型/认证状态都已经放进了**永久存在的单行 Footer**，banner 只是"我活着"的视觉锚点，无需重复元数据。

### 收税点 2：工具组容器（每次 tool call 都付）

源码：`packages/cli/src/ui/components/messages/ToolGroupMessage.tsx#212-228`

```tsx
<Box
  flexDirection="column"
  borderStyle="round"        // ← 上下 border = 2 行
  width={contentWidth}
  gap={1}                    // ← 每个 tool 之间 1 行空隙
>
  {/* ... */}
</Box>
```

加上同文件 `staticHeight = /* border */ 2 + /* marginBottom */ 1 = 3` 行固定开销。

| N 个工具 | Qwen 占用 | Claude 占用 | Qwen 净开销 |
|---|---|---|---|
| 1 工具 | 1（border 上） + 1（content） + 1（border 下） + 1（marginBottom） = 4 | 1 行 `⏺` + 1 行 `⎿` = 2 | +2 |
| 3 工具 | 1 + 3 + 2（gap 间隔 = N-1） + 1 + 1 = 8 | 6 | +2 |
| 5 工具 | 1 + 5 + 4 + 1 + 1 = 12 | 10 | +2 |

实际 N 工具 Qwen 多 N+2 行（每多一个 tool 多一个 gap），Claude 平铺线性增长。

源码：`MainContent.tsx#89` 用 Ink `<Static>` 渲染 history items，每个 `HistoryItemDisplay` 还要套：

```tsx
// HistoryItemDisplay.tsx#81-95
const marginTop = item.type === 'gemini_content' || ... ? 0 : 1;
return (
  <Box
    marginTop={marginTop}     // ← 又 +1 行
    marginLeft={2}
    marginRight={2}
  >
```

→ 工具组前后各 +1 行（marginTop + marginBottom + 上一个 marginBottom 间隔），实际**单个工具组 ≥ 5 行**。

### 收税点 3：Footer 行高

| 项 | Qwen Code | Claude Code |
|---|---|---|
| 容器高度 | `flexDirection={isNarrow ? 'column' : 'row'}` 窄屏直接换行 | `<Box height={1}>` 强制单行 |
| 左列 | `<Box flexDirection="column">` —— statusLine 上 + hint/mode 下 = **总是 ≥ 2 行**当 statusLine 存在 | 单行截断 |
| 右列 | `flexShrink={0}` 永不压缩，多个 chip 用 `gap={1}` 横向排 | 条件渲染：< 60 列只显路径，< 80 列加 model，< 120 列加 token bar |
| `wrap` 策略 | `wrap="truncate"` 仅在 hint Text 上 | 全部 `wrap="truncate"` |
| 自定义 status 行 | 每行单独 `<Text>`，状态行越多越占行 | 单行内做 carousel 切换 |

源码：
- Qwen: `Footer.tsx#138-172` 双列布局 + 多 status line 堆叠
- Claude: 见 [紧凑状态栏 deep-dive](./compact-status-bar-deep-dive.md)，铁律 `<Box height={1}>` + 响应式条件渲染

### 收税点 4：消息间距（marginTop=1 默认到处发）

源码 `HistoryItemDisplay.tsx#81`：

```tsx
const marginTop =
  item.type === 'gemini_content' || item.type === 'gemini_thought_content'
    ? 0
    : 1;
```

**只有 assistant 主消息不加间距**。所有其他类型（user / notification / user_shell / tool_group / btw / dialog 等）每条都 `marginTop=1`。

10 条 history 项 = **额外 9 行空隙**。

Claude Code 等价位置只在工具组与回复之间留 1 行（不是每条都加）——10 条对话约多省 5-7 行。

## 三、量化对比（同样 30×80 屏，10 条对话 + 3 工具调用）

| 项目 | Qwen Code | OpenCode | Claude Code |
|---|---|---|---|
| 启动 Banner（活动会话） | 8 行 | 0 行（仅 Home 路由 4 行） | 1 行 |
| 1 个工具组（3 工具） | 8 行 | 7 行（左单边框 + bg 着色） | 6 行（字符前缀） |
| Footer | 2-3 行 | 1 行 | 1 行 |
| 10 条消息间距 | +9 行（无条件 marginTop） | +5 行（首条 0 + 智能） | +5 行（按需） |
| Composer 框 | 3 行（边框） | 2 行（左单边框） | 1 行 |
| **首屏剩余可见对话内容** | **~3 行** | **~7 行** | **~10 行** |
| 相对 Claude 的密度 | 30% | 70% | 100% |

> 注：Composer 框：Qwen `borderStyle="round"`（4 边）/ OpenCode `border=["left"]` + bg / Claude 单行 `>` 提示符。

## 四、根因：组件库哲学差异

| 维度 | Qwen Code | OpenCode | Claude Code |
|---|---|---|---|
| **边框策略** | 全 4 边 `borderStyle="round"`（ToolGroup / DiffRenderer / Composer / Header / Memory badge） | **左 1 边** `border=["left"]` + `customBorderChars` 仅 `┃` + `backgroundPanel` 着色 | 几乎不用 border，靠 `⏺` / `⎿` / `│` 字符前缀 |
| **margin 默认** | `HistoryItemDisplay marginTop=1` 无条件 + 显式 `<Text> </Text>` 装饰空行 | **首条 marginTop=0** + InlineTool `renderBefore` 智能计算（与多行邻接才加） | 紧贴默认，仅语义切换处加间距 |
| **wrap 策略** | 有限 truncate，多数 Box 自然换行 | OpenTUI 原生 `flexShrink=0` 控制 | 全 `wrap="truncate"` + 响应式隐藏 |
| **响应式断点** | 仅 Footer 一处 `isNarrow ? column : row` | 单一窗口宽度，无明显断点 | 多档：< 60 / < 80 / < 120 列分别字段 |
| **Banner 默认** | 每次启动 7 行 logo + 6 行 panel + Tips | **分路由**：Home 显示 4 行 logo / Session 完全不显示 | 单行 inline + 无独立 banner |
| **状态栏显示** | 动态 statusLine 一行一条堆叠 | 单行 row + carousel（5-10s 切换） | 单行内 carousel 切换 |
| **底层框架红利** | Ink 6 标准 `borderStyle` 全边框 prop | OpenTUI `border={["left"]}` 数组 + `customBorderChars` 自由组合 | 自建 Ink fork（含池化、damage tracking） |

**三家哲学**：
- **Claude Code**：TUI 是**工程师的代码工作台**——每一寸像素优先给对话/代码内容
- **OpenCode**：TUI 是**轻量化设计稿**——用最低成本视觉分组（1 字符 + 背景色）替代完整边框
- **Qwen Code**：TUI 是**功能展示界面**——用边框/空行/Tips 做视觉引导

## 五、给 Qwen Code 的具体改进点

按收益从高到低：

| 优先级 | 改动 | 文件 + 行 | 预计省 |
|---|---|---|---|
| **P0** | 移除 ToolGroupMessage 的 `borderStyle="round"`，改用 `⎿` / `│` 字符前缀做视觉层级 | `messages/ToolGroupMessage.tsx#214` | 每工具组 -3 行 |
| **P0** | Footer 强制 `<Box height={1}>` + 全 `wrap="truncate"`，statusLine 多行改成单行 carousel | `Footer.tsx#138-172` | 每屏 -1~2 行 |
| **P1** | HistoryItemDisplay 把 `marginTop=1` 改成"按相邻项类型决定"（连续 tool 不加间距） | `HistoryItemDisplay.tsx#81-85` | 10 条对话 -4~6 行 |
| **P1** | Header info panel 移除 `<Text> </Text>` 显式空行 + 改用单行 horizontal layout（参考 Claude `✻ Welcome to Claude Code — model — cwd`） | `Header.tsx#147-149` | 启动 -3~5 行 |
| **P2** | Tips 默认 `hideTips: true`，改成首次安装时 `--show-tips` 一次性显示 | `AppHeader.tsx#48-49` | 启动 -1 行 |
| **P2** | DiffRenderer 移除外层 `borderStyle="round"`，改用左侧 `│` 单字符 gutter | `messages/DiffRenderer.tsx` | 每 diff -2 行 |
| **P3** | Composer 移除外层 border，改成 `> ` 单行（聚焦时下划线指示） | `Composer.tsx` | 每屏 -2 行 |

如果全部落地，30×80 窄屏可见对话区可从 **~3 行扩到 ~12 行（4×）**——这是用户感知"信息密度"的根本来源。

## 六、OpenCode 的中间路线

OpenCode（v1.14.x，2026-04 完成 OpenTUI 迁移）选了一条**结构介于 Qwen 和 Claude 之间**的路径——既不像 Claude 那样纯字符前缀，也不像 Qwen 那样四面边框。源码：`/root/git/opencode/packages/opencode/src/cli/cmd/tui/`。

### 6.1 Banner——分路由策略（Claude 风格）

OpenCode 把 banner 拆成**两条路由**：

| 路由 | 何时显示 Logo | Logo 大小 | 位置 |
|---|---|---|---|
| `routes/home.tsx` | 仅初始连接/会话列表 | 4 行（`logo.left/right` 各 4 字符串） | 屏幕中央，flex-grow 撑满 |
| `routes/session/index.tsx`（活动会话） | **不显示 banner** | — | 直接进入对话 |

源码：
- `cli/logo.ts#1-4`：Logo 数据 4 行
- `routes/session/index.tsx#1056-1077`：Session 路由 `<scrollbox>` 后直接 `<box height={1} />` + `<For each={messages()}>`，**没有 Welcome banner**

这与 Claude 一致（Claude 的 `✻ Welcome` 也只是单行内联，对话开始就消失），但比 Qwen 的 "每次启动都展示 7 行 logo + 6 行 info panel" 节省 6-7 行首屏空间。

### 6.2 工具组——左侧单边框 + 背景着色（创新）

源码：`routes/session/index.tsx#1741-1786` 的 `BlockTool` 组件：

```tsx
<box
  border={["left"]}                   // ← 只画左边一条线
  customBorderChars={SplitBorder.customBorderChars}  // ← 仅 vertical: "┃"
  paddingTop={1}
  paddingBottom={1}
  paddingLeft={2}
  marginTop={1}
  gap={1}
  backgroundColor={hover() ? theme.backgroundMenu : theme.backgroundPanel}
  borderColor={theme.background}
>
```

OpenTUI 的 `border` prop 接受**数组指定哪些边**，OpenCode 选 `["left"]`——只画一条 `┃` 竖线 + 用 `backgroundPanel` 微妙背景色做视觉分组。**没有上/下边框，没有右边框**。

对比：

| Agent | 工具组容器 | 占用 | 视觉手段 |
|---|---|---|---|
| Qwen Code | `borderStyle="round"` 全 4 边 + `gap=1` + `marginBottom=1` | N+5 行 | 完整边框 |
| **OpenCode** | `border=["left"]` 单边 + `paddingTop/Bottom=1` + `marginTop=1` + `backgroundPanel` 着色 | N+4 行 | 左 1 字符 + 背景色 |
| Claude Code | `⏺` / `⎿` / `│` 字符前缀，无 border | 2N 行 | 纯字符前缀 |

OpenCode 做出了一个有意思的权衡——**比 Claude 多 1 个 paddingTop 和 1 个 paddingBottom**（共 +2 行 / 工具组），但**比 Qwen 少 1 整个底部 border + 没有 round-corner 的视觉重量**。

另外 OpenCode 还有 `InlineTool`（`#1649-1737`），用于 read/glob/grep 等单行结果的工具——**完全没有 border + paddingTop=0 + 智能 marginTop**：

```tsx
renderBefore={function () {
  const el = this as BoxRenderable
  // ...
  if (el.height > 1) { setMargin(1); return }       // 自己是多行 → margin=1
  const previous = children[index - 1]
  if (!previous) { setMargin(0); return }
  if (previous.height > 1 || previous.id.startsWith("text-")) {
    setMargin(1); return                              // 上一个是多行/文本 → margin=1
  }
  // 否则 margin=0
}}
```

这是**条件 marginTop**——**只有在与多行内容相邻时才加间距**，连续的 InlineTool 之间贴紧。Qwen 的 `HistoryItemDisplay` 是无条件 `marginTop=1`，OpenCode 这套相当于把 Qwen 浪费的 marginTop 智能化了。

### 6.3 Footer——单行（Claude 风格）

源码：`routes/session/footer.tsx#52-91`

```tsx
<box flexDirection="row" justifyContent="space-between" gap={1} flexShrink={0}>
  <text fg={theme.textMuted}>{directory()}</text>
  <box gap={2} flexDirection="row" flexShrink={0}>
    {/* LSP 计数 + MCP 计数 + 权限警告 + /status */}
  </box>
</box>
```

**严格单行**——`flexDirection="row"`、`flexShrink={0}` 阻止换行。状态信息（LSP / MCP / Permission / /status）水平排列，不像 Qwen 那样多行堆叠。

未连接时还有 carousel 行为：每 5-10 秒在 "Get started /connect" 与其他提示间切换（`onMount` 里的 `tick()` 函数）——**单行内时间维度切换**而非空间维度堆叠，这与 Claude 风格相同。

### 6.4 用户消息——左边框 + 背景着色

源码：`#1280-1300`：

```tsx
<box
  border={["left"]}
  customBorderChars={SplitBorder.customBorderChars}
  marginTop={props.index === 0 ? 0 : 1}              // ← 第一条 0，其余 1
  paddingTop={1}
  paddingBottom={1}
  paddingLeft={2}
  backgroundColor={hover() ? theme.backgroundElement : theme.backgroundPanel}
>
```

仍是 `border={["left"]}` 单边 + `backgroundPanel`，与 BlockTool 一致的视觉语言。**首条消息 marginTop=0** 这点比 Qwen 的"无条件 +1"更好。

### 6.5 三家光谱定位

```
最稀疏 ─────────────────────────────────────────────────────── 最密集
Claude Code            OpenCode              Qwen Code
（纯字符前缀）         （单边框+着色）        （全边框+空行）
   2N 行/N 工具         N+4 行/N 工具          N+5 行/N 工具
   Footer 1 行          Footer 1 行            Footer 2-3 行
   无 banner            分路由 banner          全屏 banner
   无 marginTop         智能 marginTop         无条件 marginTop
```

**OpenCode 的策略本质**：用 OpenTUI 提供的 `border={["left"]}` + `customBorderChars` + `backgroundColor` 三件套，把传统的"圆角矩形容器"分解成**最低成本的视觉分组**——只用 1 个字符宽度换 4 边框的视觉效果。这是 OpenTUI 框架带来的能力（标准 Ink 的 `borderStyle` prop 不能选边）。

### 6.6 给 Qwen Code 的额外启示（从 OpenCode 学）

| 改动 | 何处可借鉴 |
|---|---|
| 把 `borderStyle="round"` 替换成 ink 的部分边框（如果 Ink 支持的话）或 `▏` 单字符 gutter | OpenCode `BlockTool` |
| `marginTop={index === 0 ? 0 : 1}` 模式 —— 首项不加间距 | OpenCode UserMessage `#1282` |
| 智能 marginTop：相邻多行才加间距 | OpenCode `InlineTool#1691-1720` 的 `renderBefore` 逻辑 |
| Banner 分路由：仅在初始 home/连接界面显示，进入对话后消失 | OpenCode `routes/home.tsx` vs `routes/session/index.tsx` |
| Footer 严格单行 + carousel 切换 | OpenCode `footer.tsx#52` + `tick()` |

> **限制**：Ink 6 的 `borderStyle` 是全边框 prop，不像 OpenTUI 的 `border={["left"]}` 数组；想完整借鉴 6.2 节的"单边框 + 背景着色"需要等 Ink 升级或自己 fork。但**首条消息 marginTop=0、智能 marginTop、Footer 单行 carousel** 这三项**今天就能在 Ink 上实现**，零成本。

## 七、为什么这事难落地（社区已有的尝试）

参考 [PR#3591 fix(cli): add TUI flicker foundation fixes](https://github.com/QwenLM/qwen-code/pull/3591)（2026-04 OPEN）—— supersedes 已关闭的 #3584/#3586/#3587/#3588，方向是 throttle + ANSI 切片 + 视觉高度切片。**这些都是闪烁修复，不动密度**。

社区目前没有专门的"减少边框/空行"PR，主要因为：

1. **审美分歧**：部分用户喜欢边框带来的视觉清晰感
2. **向后兼容**：很多自动化测试基于现有布局（`__snapshots__/` 含大量 ASCII 框框）
3. **Gemini CLI 上游**：Qwen 大量布局逻辑继承自 Gemini CLI，单方面改会增加 sync 成本

最现实的路径是**加配置开关**：`ui.compactMode: true` 时关掉所有装饰性元素（borders/marginTop/Tips/banner），保持默认行为不变。这与现有的 `CompactModeContext`（`compactMode` 仅影响 tool group 合并）正交，可叠加。

## 证据来源

- Qwen Code: `/root/git/qwen-code/packages/cli/src/ui/` 全量源码（v0.15.2）
- Claude Code: [11. 终端渲染](../tools/claude-code/11-terminal-rendering.md)、[紧凑状态栏](./compact-status-bar-deep-dive.md)、[动态状态栏](./dynamic-status-bar-deep-dive.md)、[SubAgent 展示](./subagent-display-deep-dive.md)、[紧凑工具组合并](./compact-tool-group-display.md)（如存在）
- 30×80 ASCII 渲染基于源码 margin/padding/border 算术，未实际抓屏；不同主题可能略有偏差

> **免责声明**：本文针对 Qwen Code v0.15.2（2026-04-24 之前版本）。后续若 Qwen Code 接入 `ui.compactMode` 配置或调整默认 marginTop，本文论断需要更新。
