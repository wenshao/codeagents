# 显示信息密度对比 — Claude Code / Qwen Code / OpenCode

> **核心问题**：用户报告"Claude Code 看起来信息密度比 Qwen Code 高"。是真的吗？多大？为什么？OpenCode 的新栈又落在哪？
>
> **方法**：80×30 tmux 实测三家执行同一 prompt 的稳定布局，用同一指标——**30 行屏内可见对话内容（user message + tool 调用 + assistant 回复）**——量化对比。

## 一、实测三家（80×30 tmux，prompt: `list files in this directory`）

### Qwen Code v0.15.2 实测截图

`compactMode: true`（用户 `~/.qwen/settings.json` 的实际配置，已是省空间版）+ DashScope API：

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │ >_ Qwen Code (v0.15.2)                                                   │
  │                                                                          │
  │ API Key | gpt-5.4 (/model to change)                                     │
  │ /tmp/qwen-density-test                                                   │
  └──────────────────────────────────────────────────────────────────────────┘
  Tips: Try /insight to generate personalized insights from your chat history.

  > list files in this directory

  ╭──────────────────────────────────────────────────────────────────────────╮
  │✓  ListFiles  .                                                           │
  │Press Ctrl+O to show full tool output                                     │
  ╰──────────────────────────────────────────────────────────────────────────╯

  ✦  - hello.js

────────────────────────────────────────────────────────────────────────────────
>   Type your message or @path/to/file
────────────────────────────────────────────────────────────────────────────────
  root@iZbp156rdv13mmqs236b82Z:/tmp/qwen-density-test | gpt-5.4      6.0% used
```

**逐行账（30 行屏）**：

| 行号 | 内容 | 类型 |
|---|---|---|
| 1-6 | Bordered header panel（含显式空行 line 3） | 装饰 |
| 7 | `Tips: Try /insight ...` | 装饰 |
| 8, 10, 15, 17 | 空行（`marginTop=1` 散布） | 装饰 |
| 9 | `> list files in this directory` | 对话 |
| 11-14 | 圆角 border ToolGroup（4 行：上 border + 内容 2 + 下 border） | 对话+装饰 |
| 16 | `✦  - hello.js` 最终答复 | 对话 |
| 18-20 | Composer（上分隔 + 输入 + 下分隔，3 行） | 装饰 |
| 21 | Footer | 装饰 |
| 22-30 | 屏底空白 | 滚动余量 |

**结构性开销（固定占用）**：6（header panel）+ 1（Tips）+ 3（composer）+ 1（footer）= **11 行**
**留给对话区**：30 − 11 = **19 行**（含工具组 border 占用 ≥2 行）

完整文件：[`screenshots/qwen-code-session-80x30.txt`](./screenshots/qwen-code-session-80x30.txt)

> 注：用户已开启 `compactMode: true` —— **如果默认（compactMode=false）还会再多 7 行 ASCII Logo**（见 §三）。

### OpenCode v1.14.24 实测截图

默认配置 + Moonshot Kimi K2.6 model：

```
  ┃
  ┃  list files in this directory
  ┃

  ┃  Thinking: The user wants to list files in the current directory. I
  ┃  should use the bash tool to run ls command to list the files.

  ┃
  ┃  # List files in current directory
  ┃
  ┃  $ ls
  ┃
  ┃  hello.js
  ┃

  ┃  Thinking: The ls command returned "hello.js" as the only file in the
  ┃  current directory. I should present this information concisely to the
  ┃  user.

     hello.js

     ▣  Build · Kimi K2.6 · 6.3s

  ┃
  ┃
  ┃
  ┃  Build · Kimi K2.6 Kimi For Coding
  ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
                                                    9.7K (4%)  ctrl+p commands
```

**逐行账（30 行屏）**：

| 行号 | 内容 | 类型 |
|---|---|---|
| **无 header** | 直接进入对话 | — |
| 1-3 | User message（`┃` 左单边，3 行带上下 padding） | 对话 |
| 4-7 | 第 1 段 Thinking（`┃` 左单边，2 行内容 + 邻接空行） | 对话 |
| 8-14 | BlockTool: 标题 + 命令 + 输出（共用 `┃`） | 对话 |
| 15-19 | 第 2 段 Thinking（3 行内容 + 邻接空行） | 对话 |
| 20-22 | Final answer + spinner status | 对话 |
| 23 | 空行 | 装饰 |
| 24-26 | Composer（`┃` 单边 3 行） | 装饰 |
| 27 | Mode/model 行 | 装饰 |
| 28-29 | 分隔线 + Footer | 装饰 |

**结构性开销（固定占用）**：0（无 header）+ 0（无 Tips）+ 6（composer 区，含 mode 行）= **6 行**
**留给对话区**：30 − 6 = **24 行**（含 `┃` 字符前缀占 1 列宽，无垂直占用）

完整文件：[`screenshots/opencode-session-80x30.txt`](./screenshots/opencode-session-80x30.txt)

### Claude Code（基于源码格式重建，无实测）

Claude Code 闭源且需 OAuth，没有现成 API 跑实测。下面是基于 [11-终端渲染](../tools/claude-code/11-terminal-rendering.md) + [SubAgent 展示](./subagent-display-deep-dive.md) 等已知组件格式重建的等价布局：

```
✻ Welcome to Claude Code — claude-opus-4-7 — /tmp/test

> list files in this directory

⏺ Bash(ls)
  ⎿ hello.js

The directory contains a single file: `hello.js`.














 /tmp/test                       ⏵⏵ accept edits   ? for shortcuts
```

**结构性开销（推算）**：1（inline banner）+ 1（composer）+ 1（footer）= **3 行**
**留给对话区**：30 − 3 = **~27 行**

> ⚠️ Claude Code 闭源 + OAuth 限制，本布局基于 [11-终端渲染](../tools/claude-code/11-terminal-rendering.md) 等公开文档的格式重建；与真实输出可能有 1-2 行偏差，**整体趋势成立**。

### 一图总结（同 80×30 屏）

| Agent | 实测/构造 | 结构性开销 | 留给对话 | 单工具组开销 |
|---|---|---|---|---|
| **Qwen Code** v0.15.2（compactMode=true） | ✅ 实测 | 11 行 | **19 行** | 4 行（圆角全 4 边） |
| **OpenCode** v1.14.24 | ✅ 实测 | 6 行 | **24 行** | 0 行额外（共用 `┃` 前缀） |
| **Claude Code** | ⚠️ 推算 | 3 行 | **~27 行** | 0 行额外（`⏺`/`⎿` 字符前缀） |

> **关键发现**：即使 Qwen 已开启 `compactMode: true`，对话区仍只有 OpenCode 的 **79%**、Claude Code 的 **70%**。**主要差距来自 6 行 header panel + 4 行 tool 圆角框**——两者都是 hard-coded 在组件里的视觉装饰。
>
> 如果 Qwen 关闭 compactMode（出厂默认），头部还要再多 ~7 行 ASCII logo，对话区进一步压缩到 **~12 行**——差距扩大到 OpenCode 的 50%。

## 二、四个"空间收税点"——源码追溯

每一寸屏幕都被 4 类组件层选择决定。

### 收税点 1：Banner

| Agent | 默认 banner | 何时显示 | 源码 |
|---|---|---|---|
| Qwen Code（默认） | 7 行 ASCII logo + 6 行 bordered info panel + 1 行 Tips = **14 行** | 每次启动 | `Header.tsx#56-150`、`AsciiArt.ts#9-16` |
| Qwen Code（compactMode=true） | 5 行 info panel + Tips + update notice = **7 行**（隐藏 ASCII logo） | 每次启动 | 同上 + `compactMode` 检测 |
| OpenCode | 4 行 logo（仅 Home 路由）/ **0 行**（Session 路由） | 仅初始连接屏，进会话即消失 | `routes/home.tsx#62`、`cli/logo.ts#1-4` |
| Claude Code | 1 行 inline `✻ Welcome — model — cwd` | 每次启动 | （闭源） |

**关键差异**：OpenCode + Claude 把"模型/认证状态"放在永久存在的 Footer 里，banner 只是"我活着"信号；Qwen 在 banner 里重复了同样信息（model/auth/cwd），结果两边都占空间。

源码证据：`Header.tsx#147-149` 注释直接写 `{/* Empty line for spacing */}`——**装饰性空行被 hard-coded 在组件里**。

### 收税点 2：工具组容器

| Agent | 容器策略 | 单工具组开销（不含内容） | 源码 |
|---|---|---|---|
| Qwen Code | `borderStyle="round"` 全 4 边 + `gap=1` between tools + `marginBottom=1` | **+3 行固定**（border 2 + marginBottom 1） + N-1 行 gap | `ToolGroupMessage.tsx#214` |
| OpenCode `BlockTool` | `border={["left"]}` 仅竖线 + `paddingTop/Bottom=1` + `marginTop=1` | **+3 行**（pad + margin），但**邻接 box 共线视觉融合** | `routes/session/index.tsx#1741-1786` |
| OpenCode `InlineTool` | 无 border + 智能 `marginTop`（`renderBefore` 计算） | **0 行**（与单行邻居贴紧） | 同 #1649-1737 |
| Claude Code | `⏺` / `⎿` 字符前缀，无 border、无 padding | **0 行**（仅 `⎿` 单字符空间） | （闭源） |

OpenCode 的`InlineTool` 的智能 marginTop 算法值得单独看：

```tsx
// routes/session/index.tsx#1691-1720
renderBefore={function () {
  const el = this as BoxRenderable
  if (el.height > 1) { setMargin(1); return }              // 自己多行 → 1
  const previous = children[index - 1]
  if (!previous) { setMargin(0); return }                  // 第一个 → 0
  if (previous.height > 1 || previous.id.startsWith("text-")) {
    setMargin(1); return                                    // 邻居多行/文本 → 1
  }
  // 否则 margin = 0（连续单行 inline tool 贴紧）
}}
```

**只在与多行内容相邻时才加间距**。Qwen 的 `HistoryItemDisplay#81` 是无条件 `marginTop=1`（除 `gemini_content` 外），10 条 history 项 = **9 行额外空隙**。

### 收税点 3：Footer

| Agent | 行数 | 行为 | 源码 |
|---|---|---|---|
| Qwen Code | 1-3 行（`isNarrow ? column : row`，statusLine 多行堆叠） | 自适应换行 | `Footer.tsx#138-172` |
| OpenCode | **严格 1 行** + carousel 切换 | `flexDirection="row" flexShrink={0}` 不换行 | `routes/session/footer.tsx#52-91` |
| Claude Code | **严格 1 行** + 响应式条件渲染 | `<Box height={1}>` + 60/80/120 列分档 | [紧凑状态栏](./compact-status-bar-deep-dive.md) |

OpenCode 的 carousel 模式：未连接时每 5-10 秒在 "Get started /connect" 与其他 hint 间切换，**单行内时间维度切换**而非空间维度堆叠。

### 收税点 4：消息间距

| Agent | 默认 marginTop | 源码 |
|---|---|---|
| Qwen Code | `HistoryItemDisplay marginTop=1` 无条件（除 `gemini_content` 外） | `HistoryItemDisplay.tsx#81` |
| OpenCode（user msg） | `marginTop={index === 0 ? 0 : 1}` —— 首条 0 | `routes/session/index.tsx#1282` |
| OpenCode（InlineTool） | `renderBefore` 智能计算（仅多行邻接才加） | 见上节 |
| Claude Code | 仅语义切换处加间距 | （闭源） |

10 条 history 在 Qwen 是 +9 行空隙；OpenCode 视邻接关系而定，约 +5 行；Claude 类似。

## 三、给 Qwen Code 的 5 项改进（按收益）

| # | 改动 | 源码位置 | 预计省 |
|---|---|---|---|
| **P0** | `ToolGroupMessage` 移除 `borderStyle="round"`，用 `┃` 单字符竖线（学 OpenCode `BlockTool`） | `messages/ToolGroupMessage.tsx#214` | 每工具组 -2~3 行 |
| **P0** | Footer 强制 `<Box height={1}>` + 全 `wrap="truncate"`，statusLine 多行改单行 carousel | `Footer.tsx#138-172` | 每屏 -1~2 行 |
| **P1** | `HistoryItemDisplay marginTop` 改成"按相邻项类型决定"（连续 tool 不加间距） | `HistoryItemDisplay.tsx#81-85` | 10 条对话 -4~6 行 |
| **P1** | `Header` info panel 移除 `<Text> </Text>` 显式空行 + 改成 Claude 风格单行 inline | `Header.tsx#147-149` | 启动 -3~5 行 |
| **P2** | `compactMode=true` 默认开启 + 加 `ui.densityMode: "compact" \| "comfortable"` 选项（向后兼容） | `AppHeader.tsx` + 全局 | 用户开箱即用紧凑 |

**前 3 项今天就能在 Ink 6 上实现**（OpenCode 的 P0 单边框需要 OpenTUI 的 `border={["left"]}` 数组语法，Ink 6 的 `borderStyle` 是全边框 prop）。

如全部落地，Qwen 的对话区可从 **19 行扩到 ~25 行**，与 OpenCode/Claude 同档。

## 四、为什么 Qwen Code 没改

社区已有 [PR#3591 fix(cli): add TUI flicker foundation fixes](https://github.com/QwenLM/qwen-code/pull/3591)，方向是 throttle + ANSI 切片——**修闪烁，不动密度**。

3 个落地阻力：

1. **审美分歧**：部分用户喜欢边框带来的视觉清晰感
2. **测试 snapshot 锁定**：`__snapshots__/` 含大量 ASCII 框框，改布局要重新生成
3. **Gemini CLI 上游 sync 成本**：Qwen 大量布局逻辑继承自 Gemini CLI，单方面改增加 sync 成本

最现实的路径是**加配置开关 + 让现有 `compactMode` 做更多事**：当前 `compactMode` 仅影响 tool group 合并和隐藏 ASCII Logo，不动 marginTop / borderStyle / Footer 多行。扩展它即可——零破坏性。

## 证据来源

- Qwen Code: `/root/git/qwen-code/packages/cli/src/ui/`（v0.15.2 实测，compactMode=true）
- OpenCode: `/root/git/opencode/packages/opencode/src/cli/cmd/tui/`（v1.14.24 实测）
- Claude Code: [11. 终端渲染](../tools/claude-code/11-terminal-rendering.md)、[紧凑状态栏](./compact-status-bar-deep-dive.md)、[SubAgent 展示](./subagent-display-deep-dive.md) （基于源码格式构造，无实测）
- 截图原始文件：[`screenshots/qwen-code-session-80x30.txt`](./screenshots/qwen-code-session-80x30.txt)、[`screenshots/opencode-home-80x30.txt`](./screenshots/opencode-home-80x30.txt)、[`screenshots/opencode-session-80x30.txt`](./screenshots/opencode-session-80x30.txt)

**复现命令**：

```bash
# Qwen Code
mkdir -p /tmp/qw-test && cd /tmp/qw-test && echo "// hello" > hello.js
tmux new-session -d -s qw -x 80 -y 30 'qwen'
sleep 5
tmux send-keys -t qw "list files in this directory" Enter
sleep 8
tmux capture-pane -t qw -p

# OpenCode
mkdir -p /tmp/oc-test && cd /tmp/oc-test && echo "// hello" > hello.js
tmux new-session -d -s oc -x 80 -y 30 'opencode -m kimi-for-coding/k2p6'
sleep 5
tmux send-keys -t oc "list files in this directory" Enter
sleep 8
tmux capture-pane -t oc -p
```

> **免责声明**：实测基于 Qwen Code v0.15.2 + compactMode=true，OpenCode v1.14.24 默认配置。Claude Code 部分为源码格式推算。布局逻辑随版本更新可能变化，2026-04-25 快照。
