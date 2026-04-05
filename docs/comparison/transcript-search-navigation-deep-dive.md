# Qwen Code 改进建议 — Transcript Search 会话内容搜索 (Transcript Navigation)

> 核心洞察：随着大上下文窗口模型的普及，开发者在单次 CLI Session 中与 Agent 进行几百个回合（Turns）的讨论变得越来越常见。当会话进行到中后段时，用户经常需要找回昨天或者半小时前大模型输出的某个报错信息、一条具体的 SQL 语句或架构推演。然而，终端界面的局限性让人难以忍受：你只能用鼠标滚轮或者 `PageUp` 疯狂往上翻，在几百屏的日志里寻找那一点关键信息。Claude Code 直接在交互终端中内置了媲美 Vim 的 `/` 搜索模式，支持关键词高亮和跨匹配项的极速跳转；而 Qwen Code 的历史会话目前完全是一片黑盒，无法进行任何原地检索。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、迷失在终端滚动条中的痛点

### 1. Qwen Code 现状：只能靠肉眼翻查
如果用户在当前的 Qwen Code 中跑了一个极长的重构任务：
- **痛点一（大海捞针）**：你想复制一下大模型在第 15 轮对话时列出的那个“优化建议清单”。你只能用鼠标慢慢往上滚。由于终端在滚动时会受到缓冲池（Scrollback Buffer）大小的限制，如果你开了 Tmux 或者 iTerm，超过一万行的日志可能早就被操作系统从缓冲区裁掉了。
- **痛点二（极高的视觉噪音）**：各种工具调用的日志、长代码块混杂在一起，纯靠肉眼去找一行 `UnhandledPromiseRejection` 简直是对开发者视力的折磨。

### 2. Claude Code 解决方案：Vim 级别的内置搜索流
在 Claude Code 的 `components/Messages.tsx` 的深处，它把整个终端做成了带搜索功能的富文本编辑器。

#### 机制一：无缝切入搜索模式
在主交互界面下，当系统并没有处于正在输入长提示词的焦点时，用户按下 `/` 键，底部的输入框会瞬间切换到 `Search Mode` 状态。

#### 机制二：实时全屏高亮 (Real-time Highlighting)
随着用户敲击搜索词（如 `/TypeError`），React Ink 引擎会立刻遍历当前的 `Message` 历史数组。它不仅仅是定位，而且会修改渲染树，将历史屏幕中所有命中的 `TypeError` 单词加上极其醒目的底色高亮（Highlight）。

#### 机制三：按键导航 (n / N Navigation)
完美致敬 Vim！搜索出 15 个匹配项后，底部的状态栏会显示 `[Match 1 of 15]`。
用户直接按 `n` 键（Next），终端的虚拟滚动组件就会瞬间将视口（Viewport）锁定并平滑滚动到下一个命中点；按 `Shift + N` (或者大写 `N`) 就会滚回上一个命中点。
这让你能在一秒钟内，把上百轮对话中所有提到特定报错的上下文连起来看一遍！

## 二、Qwen Code 的改进路径 (P2 优先级)

让大模型的长文本输出具有“可索引、可直达”的高级工业品手感。

### 阶段 1：状态机改造，接入搜索输入
1. 在 CLI 的主控状态机（如 `KeypressContext` 或 `InputPrompt.tsx`）中，拦截 `/` 键的敲击事件（当输入框为空或者未聚焦时）。
2. 将全局模式从 `chat` 切换到 `search`，底部输入框变为 `Search Transcript: _`。

### 阶段 2：开发高亮渲染包裹器 (Highlight Wrapper)
1. 给现有的 `MessageDisplay` 组件引入一个 Context 变量：`searchQuery`。
2. 在渲染最终的字符串到终端前，使用正则表达式 `new RegExp(searchQuery, 'gi')` 将匹配的子串用 ANSI 颜色包裹（例如 `chalk.bgYellow.black(match)`），实现全局的高亮染色。

### 阶段 3：引入虚拟滚动跳转机制
配合在 P3 级别优化的 [虚拟滚动视口](./virtual-scrolling-deep-dive.md)：
1. 找出所有包含 `searchQuery` 的 Message 的 Index 数组。
2. 监听 `n` 和 `N` 键的按击事件，动态改变当前视口的 `scrollOffset`，实现瞬间对焦（Jump-to-Index）。

## 三、改进收益评估
- **实现成本**：中等偏高。在 React Ink 中处理跨组件的滚动定位、状态机接管以及避免高亮正则误伤 ANSI 转义符（颜色代码被截断），是一项极其考察前端功底的微操。
- **直接收益**：
  1. **填补 CLI 的致命缺陷**：它直接弥补了终端在呈现长文本时“无法全局 `Cmd+F` 搜索”的最大短板，让命令行界面的信息查阅效率比肩甚至超越网页端。
  2. **开发者好感度拉满**：对于深谙终端之道的极客来说，这种纯键盘驱动、极其干脆的 `n/N` 搜索流体验，会带来无与伦比的极客快感。