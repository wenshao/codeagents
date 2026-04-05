# Qwen Code 改进建议 — 动态状态栏 (Dynamic Status Bar)

> 核心洞察：在终端环境中，当 Agent 执行耗时极长的任务（例如全量检索 500 个文件，或者运行一个需要 30 秒的端到端测试脚本）时，传统的终端往往只会显示一个单调的“加载圈 (Spinner)”。这种**缺乏进度反馈的黑盒状态**会让用户陷入焦虑，甚至误以为程序已经卡死（Hang）而强制按 `Ctrl+C` 中断。Claude Code 巧妙地在全局状态库中引入了 `statusLineText`，允许底层的工具甚至大模型在执行途中实时更新终端底部的文字；而 Qwen Code 目前在工具执行期间缺乏细粒度的进度广播机制。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、黑盒等待带来的焦虑感

### 1. Qwen Code 现状：静态的 Spinner
目前，当 Qwen Code 调用一个工具时，界面通常显示为：
`[ ⠧ ] Running shell command...`
- **痛点**：如果这个 shell 命令是 `npm run build`，它可能要跑 1 分钟。在这 1 分钟内，屏幕上的信息完全静止。用户不知道系统是在下载依赖，还是在编译代码，亦或是底层已经抛出了需要用户输入的 `(y/n)` 提示从而死锁。

### 2. Claude Code 解决方案：全局贯通的进度插槽
在 Claude Code 的 `state/AppStateStore.ts` 和 `components/StatusLine.tsx` 中，存在一个贯穿整个应用生命周期的全局状态。

#### 机制一：底层的细粒度更新 (Granular Progress Updates)
Claude Code 的底层工具执行器（例如 `FileReadTool` 或者 `GrepTool`）被赋予了修改全局 UI 状态的权限。
当 `GrepTool` 正在遍历一个庞大的工程时，它会在一个非阻塞的循环中定期调用 `setAppState({ statusLineText: 'Searching src/components/...' })`。
在 UI 层，Spinner 的旁边会高频闪过这些具体的子任务进度。这让用户吃了一颗定心丸：“它没卡住，它正在努力干活”。

#### 机制二：防抖与节流 (Debounced Rendering)
为了防止底层工具在一秒内更新 100 次 `statusLineText` 导致 React Ink 引擎重绘爆栈，Claude Code 在状态分发层做了精准的防抖过滤。只有当文本真正发生语义改变，或者距离上次重绘超过一定间隔时，才会将新文本刷入 TUI。

#### 机制三：自定义脚本挂载
Claude Code 甚至允许高阶用户在 `settings.json` 中配置自定义的 Shell 命令（比如 `git branch --show-current`）。状态栏会定期在后台静默运行这个脚本，并将执行结果（如当前的 Git 分支、甚至股票价格）挂载在状态栏的右侧。

## 二、Qwen Code 的改进路径 (P3 优先级)

让“自动化的黑盒”变得透明、可知、可控。

### 阶段 1：打通状态事件总线 (Event Bus)
1. 在 `packages/core/src/agents/runtime/agent-events.ts` 中新增一个事件：`AgentEventType.TOOL_PROGRESS`。
2. 允许工具的 `execute` 方法接收一个可选的 `onProgress(text: string)` 回调函数。

### 阶段 2：重写 TUI 状态栏组件
1. 修改 CLI 前端的 `Spinner` 或 `Footer` 组件，订阅 `TOOL_PROGRESS` 事件。
2. 将原本固定的文字 `Running Tool...` 升级为 `Running: [最新的 progress text]`。

### 阶段 3：工具层的适配接入
针对耗时工具进行改造：
- **Shell 工具**：可以结合此前讨论过的 `Shell Output FD Bypass`，将提取到的最后一条 `stdout` 的前 50 个字符截断后作为 `progress text`。
- **Grep / Glob 工具**：在遍历目录流时，每隔 500ms 抽出当前正在处理的文件夹名称抛出。

## 三、改进收益评估
- **实现成本**：低。无需更改大模型的交互逻辑，只需梳理状态上报通道，几十行代码即可实现。
- **直接收益**：
  1. **极 致 的 安 全 感**：彻底消除长任务期间的“不知道程序在干啥”的用户焦虑。
  2. **方便死锁排查**：当程序真的因为某个文件权限卡住时，屏幕上最后定格的 `statusLineText` 能让开发者瞬间定位到肇事文件。