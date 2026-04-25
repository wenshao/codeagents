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

### Claude Code v2.1.120 实测截图

第 2 轮对话稳定状态（首屏 welcome banner 11 行，会随对话累计向上滚动）：

```
│       Opus 4.7 (1M context) · Claude Max ·         │                         │
│       nigolaschao777@gmail.com's Organization      │                         │
│                    /tmp/cc-test2                   │                         │
╰──────────────────────────────────────────────────────────────────────────────╯

❯ list files

  Listed 1 directory (ctrl+o to expand)

● Files in /tmp/cc-test2:
  - f1.txt, f2.txt, f3.txt, f4.txt, f5.txt (10 bytes each)
  - hello.js (20 bytes)

✻ Churned for 4s

❯ show f1.txt content

  Read 1 file (ctrl+o to expand)

● f1.txt:
  // file 1

✻ Brewed for 3s

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  /tmp/cc-test2
  ⏵⏵ auto mode on (shift+tab to cycle)
```

**逐行账（30 行屏）**：

| 行号 | 内容 | 类型 |
|---|---|---|
| 1-4 | Welcome banner 末尾 4 行（首屏占 11 行，正向上滚动消失） | 装饰（首轮才占满） |
| 5, 7, 9, 13, 15, 17, 19, 22, 24 | 段间空行（每段间隔 1 行） | 装饰 |
| 6 | `❯ list files` 第 1 轮提问 | 对话 |
| 8 | `  Listed 1 directory (ctrl+o to expand)` 工具描述 **单行** | 对话 |
| 10-12 | `● Files in ...` 答复（3 行） | 对话 |
| 14 | `✻ Churned for 4s` 时间提示 | 对话 |
| 16 | 第 2 轮提问 | 对话 |
| 18 | 工具描述 单行 | 对话 |
| 20-21 | 答复（2 行） | 对话 |
| 23 | 时间提示 | 对话 |
| 25-27 | Composer（上分 + ❯ + 下分） | 装饰 |
| 28 | cwd | 装饰 |
| 29 | `⏵⏵ auto mode on` | 装饰 |
| 30 | 空 | — |

**结构性开销**：banner 11 行（首轮）/ 0 行（多轮后已滚出）+ 3 composer + 2 footer = **5 行（多轮稳态）/ 16 行（首轮）**
**留给对话区**：30 − 5 = **~25 行（多轮稳态）**

完整文件：[`screenshots/claude-code-session-80x30.txt`](./screenshots/claude-code-session-80x30.txt)

> **修正**：之前推算把 Claude banner 写成 1 行（`✻ Welcome to Claude Code — model — cwd`），实测**首屏是 11 行 2 列圆角面板**（左：欢迎语 + 4 行 ASCII + auth + cwd，右：Tips + Recent activity）。Claude 的"密度优势"不在于 banner 短，**而在于 banner 不 sticky——会随对话滚出**，加上工具描述用单行 `Listed 1 directory (ctrl+o to expand)` 而非框 + 段间仅 1 行间距。

### 一图总结（同 80×30 屏，多轮稳态）

| Agent | 实测/构造 | 结构性开销 | 留给对话 | 单工具组开销 |
|---|---|---|---|---|
| **Qwen Code** v0.15.2（compactMode=true） | ✅ 实测 | 11 行（header sticky） | **19 行** | 4 行（圆角全 4 边） |
| **OpenCode** v1.14.24 | ✅ 实测 | 6 行（无 header） | **24 行** | 0 行额外（`┃` 共线） |
| **Claude Code** v2.1.120 | ✅ 实测 | 5 行（多轮后 banner 滚出） | **~25 行** | **1 行**（单行描述 + ctrl+o 展开） |

> **关键发现（修正版）**：
> - **Qwen 的 header panel 是 sticky 的** ——永远占据顶部 6 行不滚动，加上 Tips + 4 行 tool 框，结构性开销固定 11 行。
> - **OpenCode 完全无 header**（活动会话路由），只有 composer/footer 占 6 行，对话区天然最大。
> - **Claude 的 welcome banner 首轮 11 行，但是非 sticky**——随对话滚动消失，多轮稳态后对话区 ~25 行接近 OpenCode。
> - **工具描述差距巨大**：Claude `Listed 1 directory (ctrl+o to expand)` 单行 → OpenCode `┃` 块共线（无额外行） → Qwen 圆角 4 行框（每个工具组都付）。

## 二、四个"空间收税点"——源码追溯

每一寸屏幕都被 4 类组件层选择决定。

### 收税点 1：Banner

| Agent | 默认 banner | 何时显示 | 源码 |
|---|---|---|---|
| Qwen Code（默认） | 7 行 ASCII logo + 6 行 bordered info panel + 1 行 Tips = **14 行** | 每次启动 | `Header.tsx#56-150`、`AsciiArt.ts#9-16` |
| Qwen Code（compactMode=true） | 5 行 info panel + Tips + update notice = **7 行**（隐藏 ASCII logo） | 每次启动 | 同上 + `compactMode` 检测 |
| OpenCode | 4 行 logo（仅 Home 路由）/ **0 行**（Session 路由） | 仅初始连接屏，进会话即消失 | `routes/home.tsx#62`、`cli/logo.ts#1-4` |
| Claude Code | 11 行圆角双列面板（welcome + 4 行 ASCII + tips + recent activity） | 每次启动，**但会随对话滚出**（非 sticky） | （闭源 v2.1.120 实测） |

**关键差异**：
- **Qwen 的 panel sticky**——`<Static>` 渲染的顶部内容永不滚动，每次都占据 6-7 行
- **Claude 的 panel 非 sticky**——首屏占 11 行但会随对话滚走，**净成本为 0**（仅首轮可见）
- **OpenCode 直接路由分离**——logo 只在 home 路由，session 路由完全无 banner

OpenCode 的策略最激进，Claude 的策略最巧妙（用一次性的 visual 锚点而不持续吃空间），Qwen 的 sticky 是**最贵且对后续会话最不友好**的方案。

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

## 三、其他对比维度（一字之差，密度差几倍）

除了上面 4 个收税点，三家还有**几个非空间但显著影响阅读体验**的差异。

### 3.1 工具描述的"字数密度"

同一个 `ls` 工具，三家显示文字差距巨大：

| Agent | 显示形式（去掉 border） | 字符数 | 折算行数 |
|---|---|---|---|
| **Claude Code** | `Listed 1 directory (ctrl+o to expand)` | 38 字符 | 1 行 |
| **OpenCode** | `# List files in current directory\n$ ls\nhello.js` | 49 字符 | 6 行（含命令 + 输出 + 4 个空行 padding） |
| **Qwen Code** | `✓ ListFiles  .\nPress Ctrl+O to show full tool output` | 56 字符 | 4 行（含上下圆角 border） |

Claude 的核心思路：**工具结果默认折叠为单行摘要**（`Listed N directories`、`Read N files`、`Edited N files`），用 `ctrl+o` 展开看详情。OpenCode 默认展开命令 + 输出（更直观但占空间）。Qwen 用框包住"工具名 + 参数"但 hide 输出（Ctrl+O 看），结果是**最坏的两边**——既占框空间又不展示输出。

### 3.2 Reasoning 块可见性

```
Qwen Code  : 不显示（assistant 消息直接出最终答复）
Claude Code: 不显示（仅状态栏 ✻ Crunched for Xs 提示）
OpenCode   : 显示（Reasoning 用 ┃ 共线展开，2-5 行/段）
```

OpenCode 显示 reasoning 让用户知道 LLM 在想什么，但代价是**每个 turn 多出 2-10 行空间**。第一节的 OpenCode 截图里 2 段 reasoning 就吃掉 8 行（行 5-7 + 16-19）。

如果 model 启用 thinking（如 Claude 的 extended thinking 或 Qwen 的 `enable_thinking`），三家都会显示，但**只有 OpenCode 默认展开**——Qwen/Claude 默认折叠。

### 3.3 状态指示文案 / Spinner

| Agent | 等待中文案样式 | 完成提示 |
|---|---|---|
| **Claude Code** | `· Orbiting…` / `Pondering…` / `Brewing…` / `Churning…` 数十种动词随机 | `✻ Crunched for 4s` / `✻ Brewed for 3s` 同动词时态变化 |
| **Qwen Code** | `⠹ Asking the magic conch shell... (0s · esc to cancel)` | 无独立完成提示，靠 `✦` 答复符号 |
| **OpenCode** | `▣ Build · Kimi K2.6 · 6.3s` model 名 + 已用时长 | 状态行实时更新 |

Claude 的随机动词带个性，但**信息含量低**（不知道在做什么）。Qwen 的 "magic conch" 是文化梗。OpenCode 最实用——直接显示 model 和时长，**首屏占 1 行也不浪费**。

### 3.4 答复符号

```
Claude  : ●  Files in /tmp/...           ← 实心圆点
Qwen    : ✦  - hello.js                  ← 四角星
OpenCode: hello.js                       ← 无符号，仅 paddingLeft=3
```

Claude/Qwen 用单字符标记 assistant 角色，OpenCode 干脆**不加任何符号**——靠位置（无 `┃` 边框 + 缩进 3）区分于工具/reasoning（都有 `┃`）。

### 3.5 Time/Token 显示位置

| Agent | 单 turn 时长 | 总用量 |
|---|---|---|
| **Claude Code** | `✻ Crunched for 4s` 每 turn 后单独一行 | 无（需 `/cost`） |
| **Qwen Code** | 无 | Footer `6.0% used`（实时） |
| **OpenCode** | `▣ Build · Kimi K2.6 · 6.3s` 状态行 | Footer `9.7K (4%)` |

**Claude 的"每 turn 一行 timing"占空间但便于对账**（用户能看到哪一步慢）；Qwen/OpenCode 把信息放 Footer，省空间但单 turn 历史不可追溯。

### 3.6 首次启动 vs 多轮稳态

> 这是最容易被忽视的维度——**用户看 demo 的首屏 ≠ 实际用 1 小时后的体验**。

| Agent | 首屏装饰 | 是否 sticky | 第 N 轮稳态装饰 |
|---|---|---|---|
| **Claude Code** | 11 行 welcome（圆角双列面板 + ASCII + tips + recent activity） | ❌ 滚出 | ~5 行（composer + footer） |
| **Qwen Code** | 6 行 panel + 1 行 Tips（compactMode=true）/ 14 行（默认） | ✅ **sticky** 永不滚出 | 11 行（panel + Tips + composer + footer） |
| **OpenCode** | 4 行 logo（仅 home 路由）→ 0 行（session 路由） | N/A 路由切换 | 6 行（composer + footer） |

**Qwen 的 sticky panel 是最贵的设计**——每次进入对话都吃 6-7 行，并且**永远不还给用户**。Claude 的 banner 虽然首轮很大（11 行），但**会滚出**，用一次性的 visual 锚点换掉后续的空间收税——这是公平的成本/收益。

### 3.7 Composer 视觉重量

```
Claude  : ──────────...                    ← 上下分隔线
          ❯
          ──────────...
          (3 行)

Qwen    : ──────────...
          >  Type your message
          ──────────...
          (3 行，与 Claude 几乎一致)

OpenCode: ┃                                ← 左侧 ┃
          ┃                                
          ┃
          ┃  Build · Kimi K2.6 ...        ← 紧贴一行 mode/model
          ╹▀▀▀▀▀                          ← 单分隔线
          (5 行)
```

OpenCode composer 占 5 行（含 mode/model 行 + ╹ 分隔），比 Claude/Qwen 多 2 行——这是 OpenCode 唯一**比对手更费空间**的地方。但相比 OpenCode 在 banner / tool 上省的空间，仍是净赢。

## 四、给 Qwen Code 的 5 项改进（按收益）

| # | 改动 | 源码位置 | 预计省 |
|---|---|---|---|
| **P0** | `ToolGroupMessage` 移除 `borderStyle="round"`，用 `┃` 单字符竖线（学 OpenCode `BlockTool`） | `messages/ToolGroupMessage.tsx#214` | 每工具组 -2~3 行 |
| **P0** | Footer 强制 `<Box height={1}>` + 全 `wrap="truncate"`，statusLine 多行改单行 carousel | `Footer.tsx#138-172` | 每屏 -1~2 行 |
| **P1** | `HistoryItemDisplay marginTop` 改成"按相邻项类型决定"（连续 tool 不加间距） | `HistoryItemDisplay.tsx#81-85` | 10 条对话 -4~6 行 |
| **P1** | `Header` info panel 移除 `<Text> </Text>` 显式空行 + 改成 Claude 风格单行 inline | `Header.tsx#147-149` | 启动 -3~5 行 |
| **P2** | `compactMode=true` 默认开启 + 加 `ui.densityMode: "compact" \| "comfortable"` 选项（向后兼容） | `AppHeader.tsx` + 全局 | 用户开箱即用紧凑 |

**前 3 项今天就能在 Ink 6 上实现**（OpenCode 的 P0 单边框需要 OpenTUI 的 `border={["left"]}` 数组语法，Ink 6 的 `borderStyle` 是全边框 prop）。

如全部落地，Qwen 的对话区可从 **19 行扩到 ~25 行**，与 OpenCode/Claude 同档。

## 五、为什么 Qwen Code 没改

社区已有 [PR#3591 fix(cli): add TUI flicker foundation fixes](https://github.com/QwenLM/qwen-code/pull/3591)，方向是 throttle + ANSI 切片——**修闪烁，不动密度**。

3 个落地阻力：

1. **审美分歧**：部分用户喜欢边框带来的视觉清晰感
2. **测试 snapshot 锁定**：`__snapshots__/` 含大量 ASCII 框框，改布局要重新生成
3. **Gemini CLI 上游 sync 成本**：Qwen 大量布局逻辑继承自 Gemini CLI，单方面改增加 sync 成本

最现实的路径是**加配置开关 + 让现有 `compactMode` 做更多事**：当前 `compactMode` 仅影响 tool group 合并和隐藏 ASCII Logo，不动 marginTop / borderStyle / Footer 多行。扩展它即可——零破坏性。

## 证据来源

- Qwen Code: `/root/git/qwen-code/packages/cli/src/ui/`（v0.15.2 实测，compactMode=true）
- OpenCode: `/root/git/opencode/packages/opencode/src/cli/cmd/tui/`（v1.14.24 实测）
- Claude Code v2.1.120 实测（在 tmux 内运行 `claude` CLI 抓取）+ [11. 终端渲染](../tools/claude-code/11-terminal-rendering.md) 等公开文档
- 截图原始文件：[`screenshots/qwen-code-session-80x30.txt`](./screenshots/qwen-code-session-80x30.txt)、[`screenshots/opencode-home-80x30.txt`](./screenshots/opencode-home-80x30.txt)、[`screenshots/opencode-session-80x30.txt`](./screenshots/opencode-session-80x30.txt)、[`screenshots/claude-code-session-80x30.txt`](./screenshots/claude-code-session-80x30.txt)

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

# Claude Code（多轮稳态）
mkdir -p /tmp/cc-test && cd /tmp/cc-test
for i in 1 2 3 4 5; do echo "// file $i" > "f$i.txt"; done
tmux new-session -d -s cc -x 80 -y 30 'claude'
sleep 6
tmux send-keys -t cc Enter             # 信任目录
sleep 3
tmux send-keys -t cc "list files" Enter
sleep 8
tmux send-keys -t cc "show f1.txt content" Enter
sleep 8
tmux capture-pane -t cc -p
```

> **免责声明**：实测基于 Qwen Code v0.15.2 + compactMode=true，OpenCode v1.14.24 默认配置，Claude Code v2.1.120 默认配置。布局逻辑随版本更新可能变化，2026-04-25 快照。
