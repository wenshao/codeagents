# Qwen Code 改进建议 — 记忆与附件异步预取 (Async Memory Prefetch)

> 核心洞察：在目前大多数 AI Agent 的执行架构中，所有的前置上下文准备（比如收集系统信息、搜索相关的记忆节点）都发生在**用户按下回车之后、大模型请求发起之前**。这会造成每一次交互都会附带上几百毫秒甚至一两秒的隐性延迟（Overhead）。如果在长对话中，这种积累的延迟会严重打断开发者的“心流（Flow）”。Claude Code 的工程团队敏锐地捕捉到了这一点，他们把网络开发中常用的“预取（Prefetch）”思想引入到了 Agent 状态机中：通过在工具执行的间隙**异步并发**地去后台扫描并准备相关的记忆节点，实现了交互过程中的“零感知耗时”；而 Qwen Code 目前依然遵循着死板的串行收集模型。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、串行阻塞带来的迟钝感

### 1. Qwen Code 的现状：步步为营的等候
如果在 Qwen Code 中启用了复杂的长期记忆功能：
1. 大模型返回了一个工具调用（例如 `read_file("src/main.ts")`）。
2. Qwen 执行完读取后。
3. 它需要构建下一个发给大模型的 Context。此时，它会**停下来**，同步去调用记忆检索模块，根据刚才读出的内容去向量库或者本地索引里翻找相关的项目规则。
4. 找完之后，组装好，再发请求。
**痛点**：步骤 3 可能是纯磁盘甚至网络 I/O。这就意味着大模型的两次呼吸之间，不仅有工具执行的时间，还叠加了上下文构建的时间。如果找资料花了 300ms，用户的直观感受就是工具执行完后，程序卡了一下才开始转圈圈。

### 2. Claude Code 解决方案：在子弹飞行的同时填装弹药
在 Claude Code 的 `utils/attachments.ts` 和核心 `query.ts` 循环中，作者极其巧妙地利用了 JavaScript 事件循环（Event Loop）的非阻塞特性。

#### 机制一：Fire-and-Forget 的异步句柄 (Prefetch Handle)
当用户的输入刚刚抵达，或者大模型刚刚生成完一段计划、正准备要去**执行一个耗时 2-3 秒的文件读写工具**时。
主控调度器（Scheduler）并不会干等着。
它会极其前瞻性地调用 `startRelevantMemoryPrefetch()`。这个函数不会阻塞主线程，而是返回一个异步句柄（Promise Handle），并立刻进入后台默默翻查记忆库、向量库，甚至是异步加载某些需要冷启动的 Skill 插件。

#### 机制二：结算时的无缝注入 (Settled Injection)
当那个耗时 2 秒的底层工具（比如 `BashTool(npm install)`）终于跑完时。
主控调度器会转身去看刚才那个后台扔出的句柄：
- **如果已经跑完（Settled）**：极其完美！刚才等工具的时候，几十 KB 的相关记忆材料早就神不知鬼不觉地查好了放在内存里。系统瞬间把它们拼在一起扔给大模型，中间没有任何 Overhead！
- **如果没跑完**：也不强等，果断跳过或者用降级的小片段塞入，绝不让用户感知到为了查资料而发生的额外死锁。

#### 机制三：基于“转折点”的技能嗅探 (Write-Pivot Discovery)
同样的逻辑被用于技能插件（Skill）的发现上。当大模型从“疯狂看文件（Read-only）”的状态突然转向“我要改文件了（Write-pivot）”时，系统会在执行第一个 Write 工具的后台间隙，瞬间启动与重构、测试相关 Skill 的异步预取，确保它在执行完写操作需要下一步建议时，那些重量级插件早已热身完毕。

## 二、Qwen Code 的改进路径 (P1 优先级)

天下武功唯快不破，消除一切可被并行的等待时间。

### 阶段 1：开发异步预取层
1. 在 `packages/core/src/services/` 创建 `memoryPrefetch.ts`。
2. 封装现有的上下文和记忆召回逻辑，使其脱离 `await` 链条，返回封装状态的 Promise 句柄对象（包含 `isSettled`, `data`, `error`）。

### 阶段 2：修改 Agent 核心调度环 (Event Loop)
在 `agent-interactive.ts` 或者核心的 Tool Scheduler 内部：
```typescript
// 1. 发射工具执行指令
const toolPromise = executeTool(toolCall);
// 2. 同时发射下一次可能需要的记忆查询！
const prefetchHandle = startRelevantMemoryPrefetch({ ...context });

// 3. 等待最慢的那个，通常是工具执行
const toolResult = await toolPromise;

// 4. 工具结束了，看记忆查没查好
if (prefetchHandle.isSettled) {
    injectIntoNextContext(prefetchHandle.data);
}
```

### 阶段 3：设定预取预算边界
异步不是毫无节制的。因为记忆可能会非常庞大，规定 `MemoryPrefetch` 每次收集回来的内容不能超过预设的 `~20KB` 的预算（Budget Limit），避免预取到的垃圾信息反而击穿大模型的 Token 限制。

## 三、改进收益评估
- **实现成本**：中等。核心在于重构调度器状态机，处理好主线程和后台 Promise 的竞态条件（Race Condition），代码量在 200 行左右。
- **直接收益**：
  1. **极致的跟手感**：消除每轮工具切换时固有的几百毫秒顿挫感，让 Agent 从一个机械的串行脚本，变成一个真正多线程满载运转的超跑。
  2. **从容地塞入重型分析**：有了预取机制兜底，开发者就可以放心地把哪怕耗时 1 秒的超大型知识库检索或 RAG 系统挂在后台，而完全不用担心用户抱怨系统变慢。