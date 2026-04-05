# Qwen Code 改进建议 — 自定义快捷键与 Multi-Chord (Custom Keybindings)

> 核心洞察：CLI 工具的重度用户（如 Vim/Emacs 极客）对快捷键有着极其固执的肌肉记忆。强制使用系统硬编码的快捷键不仅会引起用户的极度反感，还经常会与终端模拟器（如 iTerm2/Tmux）自带的组合键发生冲突。Claude Code 在这方面做到了极致：它内置了一个极尽巧思的 `keybindings.json` 引擎，并实现了支持像 `Ctrl+K Ctrl+S` 这样的 Multi-chord（多键组合连击）状态机，让用户能完全重塑交互手感；而 Qwen Code 目前的按键绑定是写死在 React Ink 的代码里的。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、硬编码快捷键的痛点

### 1. Qwen Code 现状：缺乏灵活性的按键映射
在 Qwen Code 的 TUI（终端用户界面）交互中，像退出、换行、历史记录翻页等快捷键通常是写死的。
- **痛点一（键位冲突）**：Qwen Code 可能使用了 `Ctrl+N` 来作为下一条历史记录，但在某些用户的 Tmux 配置中，`Ctrl+N` 是切换窗口的快捷键。这会导致严重的功能冲突，且用户无能为力。
- **痛点二（缺乏极客定制）**：VS Code 用户习惯用 `Ctrl+Enter` 提交，而 Vim 用户可能更喜欢设置一个自己习惯的按键来触发“清除上下文”或“开启新的 Subagent”。目前 Qwen 无法满足这类定制诉求。

### 2. Claude Code 解决方案：全面配置化与 Multi-chord
在 Claude Code 的按键拦截引擎中，它不仅支持简单的修饰键，甚至引入了状态机来实现高级快捷键：

#### 机制一：声明式的 keybindings.json
它允许用户在 `~/.claude/keybindings.json` 中定义一个完全兼容 VS Code 风格的 JSON：
```json
{
  "bindings": [
    { "key": "ctrl+k ctrl+s", "command": "openSettings" },
    { "key": "ctrl+space", "command": "submitAndContinue" }
  ]
}
```

#### 机制二：Multi-chord 状态机
当终端按键流触发时，如果用户按下了 `Ctrl+K`，系统并不会立刻认为这是一个无效输入，而是进入一种 `Chord Pending` (等待连击) 状态。如果接下来 500ms 内用户按下了 `Ctrl+S`，则触发 `openSettings` 动作；如果按了其他的，则打断状态机并将按键退回给标准输入缓冲。这种高级特性让终端工具拥有了图形化 IDE 一样的快捷键扩展深度！

#### 机制三：保留键与安全校验
为了防止用户作死把 `Ctrl+C` 给绑掉了导致程序无法退出，引擎硬编码了极少数的不可重绑键（Reserved keys）。同时在 `/doctor` 诊断命令中，会专门校验用户的 `keybindings.json` 是否有语法或冲突错误。

## 二、Qwen Code 的改进路径 (P2 优先级)

对于 CLI 工具，手感就是一切。

### 阶段 1：剥离硬编码按键
1. 找出所有在使用 React Ink 的 `useInput` 钩子中写死的键位判定（如 `if (key.ctrl && input === 'c')` 之外的业务快捷键）。
2. 构建一个单例 `KeybindingManager`，初始化时读取 `.qwen/keybindings.json`。

### 阶段 2：实现键盘状态机引擎
1. 编写一个按键解析器，将诸如 `shift+up`, `alt+enter` 等文本映射为 Ink 发出的底层按键对象。
2. 加入 `Chord Pending` 状态队列。如果在超时窗口内接收到完整的按键序列，则向事件总线 `EventEmitter` 发出对应的 `COMMAND_TRIGGERED` 信号。

### 阶段 3：暴露快捷键给插件系统
在未来，如果允许用户编写自定义的 Agent Hook 或小工具，可以通过这套机制将用户的自定义命令绑定到某个酷炫的 Multi-chord 快捷键上。

## 三、改进收益评估
- **实现成本**：中等。实现 Multi-chord 的状态机在处理 Node.js 的 Raw Mode 输入流时需要考虑不少边缘 Case。
- **直接收益**：
  1. **极佳的开发者口碑**：定制快捷键是极客圈子的“加分神器”，能极大提升从 Vim 或 VS Code 迁移过来的用户的粘性。
  2. **解决平台级按键冲突**：将解决冲突的权利交还给用户，系统维护者不用再去为“Windows 下该用哪个键不冲突”而头疼。