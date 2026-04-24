# 显示信息密度深度对比 — Claude Code vs Qwen Code

> **核心问题**：用户报告 "Claude Code 看起来信息密度比 Qwen Code 高"。这是 UI 框架差异（都用 Ink/React），还是组件层的结构性"空间收税"？逐项源码追溯。
>
> **结论先行**：在标准 30×80 窄屏（很多用户的 tmux 分屏宽度）上，Qwen Code 比 Claude Code **多消耗 ~40% 垂直空间**用于装饰性元素（边框/空行/banner/marginTop）。这不是字号或缩写问题，而是 4 类组件层的结构选择。

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

| 项目 | Qwen Code | Claude Code | 差额 |
|---|---|---|---|
| 启动 Banner | 8 行 | 1 行 | **-7** |
| 1 个工具组（3 工具） | 8 行 | 6 行 | **-2** |
| Footer | 2-3 行 | 1 行 | **-1~2** |
| 10 条消息间距 | +9 行 marginTop | +5 行（按需） | **-4** |
| Composer 框 | 3 行（边框） | 1 行 | **-2** |
| **首屏剩余可见对话内容** | **~3 行** | **~10 行** | **3.3×** |

> 注：Composer 框：Qwen 用 `borderStyle="round"`，Claude 用单行 `>` 提示符。

## 四、根因：组件库哲学差异

| 维度 | Qwen Code | Claude Code |
|---|---|---|
| **边框使用** | 大量 `borderStyle="round"`（ToolGroup / DiffRenderer / Composer / Header info panel / Memory badge），把每种类型视觉隔离 | 几乎不用 border，靠 **`⏺` / `⎿` / `│` 字符前缀** 做视觉层级 |
| **margin 默认** | HistoryItemDisplay 默认 `marginTop=1`，组件内部还有显式 `<Text> </Text>` 空行 | 紧贴默认，仅在语义切换处加间距 |
| **wrap 策略** | 有限 truncate，多数 Box 自然换行 | 全 `wrap="truncate"` + 响应式隐藏 |
| **响应式断点** | 仅 Footer 一处 `isNarrow ? column : row` | 多档：< 60 / < 80 / < 120 列分别显示不同字段 |
| **Tips/Banner 默认** | 每次启动都显示，需 `hideTips: true` 关 | 默认无 tips（命令补全里嵌入提示） |
| **状态栏显示策略** | 动态 statusLine 一行一条堆叠 | 单行内 carousel 切换 |

**核心区别**：Claude Code 把 TUI 当成**工程师的代码工作台**——每一寸像素优先给对话/代码内容；Qwen Code 把 TUI 当成**功能展示界面**——用边框/空行/Tips 做视觉引导。

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

## 六、为什么这事难落地（社区已有的尝试）

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
