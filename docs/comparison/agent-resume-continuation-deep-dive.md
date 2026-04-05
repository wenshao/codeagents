# Qwen Code 改进建议 — Agent 恢复与续行 (Agent Resume & Continuation)

> 核心洞察：现代 AI 编程代理正在从“单次问答”走向“长驻后台任务”。当你让 Agent 帮你审查一个包含 50 个文件的拉取请求（PR）时，这可能需要它跑上十几分钟。如果在审查到第 30 个文件时，你的 VPN 突然掉线、SSH 断开或者你不小心关掉了终端标签页，当前所有开源 CLI Agent 的内存状态都会随之灰飞烟灭，你只能重新开一个 Agent 从头再来。Claude Code 通过底层 JSONL Transcript 的自动记录和极其健壮的“断点重建（Context Reconstruction）”算法，实现了让大模型 Agent 在遭遇任何硬中断后都能“起死回生”继续工作的能力；而 Qwen Code 目前执行完毕或中断即销毁，缺乏状态续行。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、状态蒸发带来的“全有或全无”风险

### 1. Qwen Code 的现状：脆弱的生命周期
在 Qwen Code 中，一个 Agent 的全部思考过程和上下文都保存在当前 Node.js 进程的 V8 堆内存中。
- **痛点一（意外中断的损失）**：一旦进程被 `SIGKILL` 或者网络掉线，刚才大模型耗费大量 Token 梳理出的项目代码逻辑图、变量映射表瞬间消失。
- **痛点二（跨设备的断层）**：如果开发者在公司的台式机上让 Agent 开始干活，下班回家后想在笔记本上继续让它往下查，这在目前的无状态架构下是不可能做到的。

### 2. Claude Code 的极客方案：基于 Transcript 的时空冻结
在 Claude Code 的 `services/SessionMemory/` 和 `utils/forkedAgent.ts` 中，作者不遗余力地打造了一个类似单机游戏“随时存档/读档”的系统。

#### 机制一：全量静默持久化
在 Agent 的推理循环（Run Reasoning Loop）中，每当产生一个新的 User Message 或是 Tool Result 时，系统不仅仅将其 `push` 进内存数组，还会通过 `appendFileSync` 以流式的方式瞬间写进磁盘上的 `transcript.jsonl` 文件中。

#### 机制二：上下文重构 (Context Reconstruction)
如果 Agent 意外死亡，用户通过 `SendMessage` 工具或者通过类似 `/resume` 的入口重新唤起这个 Agent 的任务 ID：
1. 引擎会找到那个 `.jsonl` 文件。
2. 引擎不会盲目把死之前的数组全扔给 API（那会触发 `400 Bad Request`）。它会调用 `resumeAgentBackground()`。
3. 它会进行一系列极为精妙的“清理手术”：
   - 剔除掉最后几条**因为崩溃而未接收到 `tool_result` 的孤立 `tool_use`** 块。
   - 剔除掉只包含 `<thinking>` 却没说完的废话。
4. 甚至，它还能重建内存中的临时状态：把上一次 `replace` 命令对某文件做的内存修改（Content Replacements）、以及 Agent 特有的系统提示词重新在内存中映射回来。

一旦手术完成，它会在末尾补上一句虚拟的用户旁白：“Continue your execution from where you left off.”。大模型苏醒后看到完整的上下文，会误以为自己刚才只是睡了一秒钟，立刻接上刚才没改完的代码继续干活！

## 二、Qwen Code 的改进路径 (P1 优先级)

让 Agent 变成具有“永生”能力的后台工作站。

### 阶段 1：实现 JSONL 事务日志
1. 在 `packages/core/src/agents/runtime/` 下改造 `geminiChat.ts` 或核心状态机。
2. 在处理每一轮对话（Round）时，必须异步且原子地将这一轮的 Messages 追加到 `.qwen/sessions/[session_id]/transcript.jsonl` 中。

### 阶段 2：开发 `resumeAgent()` 重建引擎
1. 编写从 JSONL 读取并反序列化回内存 `messages` 数组的逻辑。
2. 结合我们之前讨论过的 [消息规范化与配对修复](./message-normalization-deep-dive.md)，确保恢复出来的数组符合大模型 API 严格的交替规则。

### 阶段 3：工具层面的恢复点设计
大模型不仅需要记忆恢复，还需要**业务状态**恢复。
确保诸如 `TaskManagement`（任务队列）或 `FileSystemCache` 在重新启动时能正确反序列化。可以通过在 JSONL 中插入特殊的 `[Meta: State Checkpoint]` 事件来实现业务快照。

## 三、改进收益评估
- **实现成本**：中等偏高。核心在于各种中断边缘 Case 下的脏数据清理，代码重构量在 300-500 行。
- **直接收益**：
  1. **彻底解放长任务**：用户可以毫无顾虑地让 Qwen Code 去跑涉及几百个文件的大审查，不怕掉线，不怕休眠。
  2. **资源极大节约**：断点续传避免了从头再来，节省了成千上万原本被白白浪费的重试 Token。