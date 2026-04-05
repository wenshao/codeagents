# Qwen Code 改进建议 — Ghost Text 输入补全 (Inline Ghost Text Completion)

> 核心洞察：CLI Agent 的易用性极大受限于终端的交互形式。当开发者频繁输入长长的项目目录路径或生僻命令时，如果缺乏图形化 IDE 的提示框，会导致打字极度疲劳且容易拼错。Claude Code 在其定制的终端输入框（InputPrompt）中实现了三层基于上下文的智能“幽灵补全 (Ghost Text)”（历史记录补全、文件路径补全、命令模糊匹配），极大地提升了交互速度；而 Qwen Code 目前的输入框几乎是裸的终端 STDIN。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么终端需要智能补全？

### 1. Qwen Code 现状：沉重的纯键盘输入
如果你在一个深度嵌套的项目中想让 Agent 修改某个文件：
`> 请帮我检查一下 src/components/layout/Sidebar/navigation.tsx`
- **痛点**：在传统的 Shell 中，你可以按 `Tab` 补全路径。但在 Agent 的交互循环（如使用 Ink 构建的输入框）中，默认并不支持路径探测补全。你需要凭记忆一个字一个字地敲完这一长串绝对路径，一旦拼错，Agent 会在一两分钟后抱歉地告诉你“未找到该文件”。

### 2. Claude Code 解决方案：幽灵文字 (Ghost Text)
Claude Code 在 `hooks/useTextInput.ts` 和 `utils/suggestions/` 中，完全重写了终端的输入体验。
当用户打字时，输入框的光标后方会实时出现**灰色的虚影提示（Ghost Text）**。

它背后由三层强大的 Suggestion 引擎驱动：
1. **Shell 历史补全** (`shellHistoryCompletion.ts`)：
   它会在后台静默读取用户的 `~/.bash_history` 或 `.zsh_history`。如果你刚在另一个窗口跑了 `pytest tests/integration/auth_test.py`，然后在 Claude 里敲下 `pyt`... 后面立刻会浮现这行长长的历史命令。按一下 `Right Arrow` (右方向键) 或 `Tab` 就可全部接受。
2. **文件路径补全** (`directoryCompletion.ts`)：
   一旦用户输入了类似 `/` 或 `./`，后台引擎立刻非阻塞地读取当前目录结构并模糊匹配最近的文件。
3. **命令自动建议** (`commandSuggestions.ts`)：
   针对 `/` 开头的内置命令（如 `/review`，`/compact`）提供补全。

这种极其流畅的体验，让在命令行里操控 Agent 变得像在现代代码编辑器（如 VSCode 或 Fish Shell）里一样舒适。

## 二、Qwen Code 的改进路径 (P1 优先级)

改善交互体验是提升用户留存率的第一生产力。Qwen Code 需要改造其 `InputPrompt` 组件以支持这一特性。

### 阶段 1：构建 Ghost Text 渲染层
1. 修改使用 React/Ink 构建的 `InputPrompt.tsx`。
2. 在原有的用户输入 `<Text>` 字符串之后，追加一个 `<Text dimColor>{ghostText}</Text>`。
3. 接管按键事件：当 `ghostText` 不为空时，如果用户按下 `Tab` 或 `Right Arrow`，则将当前输入值补齐为 `inputValue + ghostText`。

### 阶段 2：实现按需异步探测器 (Completion Providers)
新建 `packages/core/src/utils/suggestions/` 模块，实现以下探测器：
1. `commandProvider`: 判断输入以 `/` 开头时，从已注册的命令库中查找前缀匹配。
2. `pathProvider`: 判断当前输入单词以 `/` 或 `./` 或 `../` 开头时，调用 `fs.promises.readdir` 获取对应层级的文件，返回最可能匹配的剩余部分。
3. `historyProvider`: 在进程启动时预读取全局及局部的 Agent 会话历史文件，构建一颗 Trie 树用于毫秒级前缀匹配。

### 阶段 3：防阻塞与防抖动控制
- 这些探测器的执行必须是**非阻塞的**，否则一边打字屏幕一边卡顿。
- 使用简单的 `debounce` (防抖，比如 50ms) 包裹文件探测器，确保高速打字时不引发 I/O 阻塞事件循环。

## 三、改进收益评估
- **实现成本**：中。需要深入理解 React Ink 的按键接管，并处理多平台下的文件路径补全边界情况。
- **直接收益**：
  1. **极大的效率提升**：告别了极其痛苦的长路径手动拼写，操作行云流水。
  2. **消除无谓的 API 开销**：消灭了因为文件名“拼错一个字母”导致的无用大模型交互与错误工具调用。
  3. **降低命令记忆负担**：斜杠命令可以盲打前两个字母按 Tab，降低了心智负担。