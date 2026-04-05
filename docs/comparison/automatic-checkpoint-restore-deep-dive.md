# Qwen Code 改进建议 — 自动检查点默认启用 (Automatic Checkpoint by Default)

> 核心洞察：AI 辅助编程最大的痛点不是“AI 写不出来”，而是“AI 写对了一半，然后突然发神经把另一半写坏了”。在一个包含 5 次连续编辑的文件重构任务中，如果 Agent 在第 4 步达到了完美状态，但在第 5 步意外删除了核心引用，用户通常别无选择——只能通过 `git checkout` 撤销该文件的所有改动，连同前 4 步正确的成果也一并付之东流。Claude Code 把“文件历史快照”做成了整个架构的隐形底座，默认在每次工具执行前后全自动打点，并提供了 `/restore` 任意快照的能力；而 Qwen Code 目前在此类防呆设计上是缺失的。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、全盘撤销带来的挫败感

### 1. Qwen Code 现状：没有后悔药
当你使用 Qwen Code 让它帮你优化一段核心业务逻辑时：
- **痛点一（高昂的纠错成本）**：AI Agent 改了 5 处代码，前 4 处都极其精妙，但最后一处引入了一个编译错误。在现有的 CLI 中，你不能对 AI 说“退回上一步”。由于文件在物理磁盘上已经被修改，如果用户自己没用 Git Commit 暂存过，他就只能咬着牙手动把那一行错的代码改回来（而且往往他根本不知道 AI 刚才删了什么）。
- **痛点二（信任危机）**：因为撤销的代价太大，老手开发者根本不敢让 AI 一次性执行跨越好几个文件的长流程重构，严重制约了 Agent 的生产力。

### 2. Claude Code 的极客防线：无感级别的自动快照
在 Claude Code 的内部机制中，所有的文件写操作工具（如 `FileEditTool`、`FileWriteTool` 甚至 `BashTool`）都被包裹了一层安全网。

#### 机制一：高频静默快照 (Implicit Checkpointing)
在引擎执行大模型的写入命令**之前**和**之后**，它会在极低的 I/O 开销下，把目标文件的内容备份到 `.claude/checkpoints/` 目录下，并以文件的 SHA-256 以及当前时间戳命名。
这一切都是静默发生的，最多保留最近的 100 个历史版本（超出自动 LRU 回收），用户几乎感知不到存储和耗时的增加。

#### 机制二：时光机交互 (`/restore`)
当用户发现代码被改乱了，只需在终端输入 `/restore` 或者 `/rewind`。
React Ink 终端会弹出一个精美的时光机列表：
```text
Select a checkpoint to restore:
> [10:45 AM] (FileEditTool) src/utils.ts - Replaced JWT logic
  [10:42 AM] (BashTool) src/utils.ts - Formatted file
  [10:35 AM] (FileWriteTool) src/utils.ts - Initial creation
```
用户可以通过上下键翻阅，选中后按下回车，这一个文件瞬间时光倒流，精准回退到 10 分钟前它最完美的那一刻。而且这完全不影响项目里的其他文件！

## 二、Qwen Code 的改进路径 (P1 优先级)

对于生产力工具而言，“能无伤试错”就是第一生产力。

### 阶段 1：开发全局文件快照服务 (Snapshot Service)
1. 在 `packages/core/src/utils/` 创建 `checkpointManager.ts`。
2. 设置持久化存储目录（如 `.qwen/checkpoints/`），并实现一个异步方法 `createCheckpoint(filepath: string, label: string)`。
3. 为防止硬盘爆满，每次保存时执行清理逻辑，确保每个 Session 或者全局最多保留 100 个临时副本。

### 阶段 2：拦截写工具生命周期
重构所有具有破坏性的工具（如 `replace`, `write_file`, `shell` 工具的执行阶段）：
在真正的系统 `fs.promises.writeFile` 执行前，强制插入一行 `await checkpointManager.createCheckpoint(targetPath, "Before " + toolName)`。

### 阶段 3：提供 `/restore` CLI 界面
1. 增加 `/restore` 或者 `/rewind` Slash 命令。
2. 利用 TUI 列表组件，列出按时间倒序排列的快照日志。
3. 如果可能，集成 Diff 渲染引擎，在用户高亮某一条快照时，在屏幕右侧或者下方即时预览“现在的代码和那个快照相差了什么”，帮助用户做出绝不后悔的选择。

## 三、改进收益评估
- **实现成本**：小到中等。核心是文件的复制备份和清理逻辑，代码量大约 200 行。
- **直接收益**：
  1. **指数级增加用户安全感**：彻底消灭了用户“怕 AI 把我原有代码搞崩”的恐慌，鼓励用户更大胆地使用全自动模式（YOLO Mode）。
  2. **从脚本跃升为 IDE**：这种细粒度的本地历史记录功能，是现代高级编辑器（如 WebStorm Local History）才有的重型武器，直接让 Qwen Code 的护城河变深。