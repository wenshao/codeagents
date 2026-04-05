# Qwen Code 改进建议 — Coordinator/Swarm 多 Agent编排模式 (Swarm Orchestration)

> 核心洞察：当我们让大语言模型处理“修改当前函数的一个 Bug”时，单体 Agent 绰绰有余。但当指令变成“帮我把这个项目里所有的 CommonJS 引用全部重构为 ESM 导入”，涉及上百个文件的全局重构时，单体 Agent 的串行处理会遭遇上下文污染、Token 爆顶和耗时数小时的灾难。Claude Code 最具野心的架构设计就是基于 Leader/Worker 团队模型的 **Coordinator/Swarm 多 Agent 并发编排**，能将宏观重构任务化整为零，在终端幕后拉起一支“无形的代码工程连”；而 Qwen Code 目前在多模态和单兵能力上发力，但在集群编排上略显单薄（目前仅有实验性质的 Arena 对打模式）。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么我们需要大模型“包工头”？

### 1. Qwen Code 的现状：孤独的单线程
如果用户在当前的框架下提交一个跨越多目录的架构重构指令：
- **瓶颈一（串行耗时）**：Agent 只能老老实实读第一个文件、思考、替换；接着读第二个文件、思考、替换。100 个文件，如果每个文件来回消耗 5 秒，总计需要近 10 分钟的静默等待。
- **瓶颈二（上下文崩溃）**：随着修改历史的堆积，大模型脑子里的 Prompt Context 越来越大。到了第 50 个文件时，它极易陷入幻觉，把前面修改过的废弃逻辑又写回到了后面的代码里，或者是被极其昂贵的 API 费用账单直接切断（Token Limit Reached）。

### 2. Claude Code 的工业级调度：Leader-Worker Swarm
Claude Code 拥有一个被极度保密的 `coordinator/` 和 `utils/swarm/` 目录群，里面实现了一套惊为天人的 Map-Reduce 任务分发机制。

#### 机制一：Leader (包工头) 的任务拆解
当识别到大规模任务时，当前交互的大模型（旗舰模型如 Opus）会自动升格为 `Leader`。
它**不写一行代码**！它只会疯狂扫描整个仓库的目录树，理清文件依赖，然后把庞大的重构目标切分成 10 份。
比如：
> Task 1: Refactor `src/auth/*.js`
> Task 2: Refactor `src/utils/*.js`

#### 机制二：三种后端（Backend）自动路由
Leader 产生切片任务后，需要把它分发给打工的 `Worker` 模型（通常更廉价、极速如 Haiku 模型）。Claude Code 设计了三种执行引擎来拉起 Worker：
1. **Tmux Pane**：如果用户正好处于 Tmux 环境，它会直接通过 Shell 钩子，把终端屏幕横向劈开 5 个窗格，你能亲眼看到 5 个 Agent 在并行刷屏写代码！
2. **iTerm2**：如果是 macOS，它会利用 AppleScript 自动拉起 5 个独立分屏。
3. **InProcess**：作为通用底座，它利用 Node.js 原生的 `AsyncLocalStorage` 在当前单线程进程内，隔离出多个上下文安全的并发协程。

#### 机制三：TeamFile 与并发防踩踏
如果两个 Worker 不小心同时修改到了同一个入口文件 `index.ts` 怎么办？
系统引入了 `TeamFile`（团队黑板）。它通过操作系统的底层文件锁 (`proper-lockfile`) 保证安全。Leader 在这里分发每个 Worker 的负责路径边界（Allowed Paths），严格防止 Worker 之间发生跨界代码踩踏冲突。最终由 Leader 回收所有人执行的统计结果并向人类复命。

## 二、Qwen Code 的改进路径 (P1 优先级)

如果要把 Qwen Code 卖给企业级客户，处理宏大工程结构的能力是最值钱的杀手锏。

### 阶段 1：构建 `Leader` 模式基础
1. 在 `packages/core/src/agents/` 下新增 `CoordinatorAgent` 角色。
2. 为其特化 System Prompt：“Your ONLY job is to plan and delegate. Do NOT edit files. Use the `spawn_subagent` tool to create workers for specific sub-directories or files.”

### 阶段 2：完善 `spawn_subagent` 工具
1. 结合我们之前讨论的 [InProcess 隔离技术](./in-process-agent-isolation-deep-dive.md)。
2. 这个工具允许传入 `task_description`、`allowed_directories` 以及 `model_type`。
3. 引擎在后台拉起子代理执行（并发受到 `p-limit` 如最大 5 路的限制以防封 IP）。

### 阶段 3：建立汇聚总线 (Aggregator)
子代执行完毕后，必须有一个途径将自己遭遇的报错或者成功的结果回传。
利用我们在之前深入研究过的 [Agent 邮箱系统与 SendMessageTool](./multi-agent-deep-dive.md)，让 Worker 将 `[SUCCESS: refactored 5 files in src/auth]` 的报告发回 Leader，最终由 Leader 通知主界面的使用者。

## 三、改进收益评估
- **实现成本**：极高。这涉及重构 TUI 的多状态展示、处理严苛的文件锁以及多并发请求隔离。
- **直接收益**：
  1. **指数级的生产力跃迁**：将大面积重构的时间从几十分钟压缩至几十秒，这是能够写在发布会 PPT 首页的重磅特性。
  2. **算力成本的最优组合**：Leader 使用最高配的最聪明模型（确保不搞错方向），并发的 20 个 Worker 全部使用响应最快、最廉价的小模型进行格式化劳作，在质量和开销上做到了真正的黄金平衡。