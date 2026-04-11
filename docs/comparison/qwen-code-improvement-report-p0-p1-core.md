# Qwen Code 改进建议 — P0/P1 核心能力

> 核心能力改进项：上下文压缩、Subagent、Speculation、记忆系统、工具并行、启动优化等
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. 多层上下文压缩（P0）

**思路**：Claude Code 把上下文压缩设计为 **5 层递进式系统**——从最轻量到最重量级逐层升级，大多数情况下在前两层就解决问题，用户完全无感知：

| 层级 | 名称 | 触发条件 | 做什么 | 代价 |
|:----:|------|----------|--------|------|
| L1 | cache_edits | 每轮自动 | 通过 API 参数标记旧工具结果为"已删除"，服务端在缓存前缀上原地删除 | **零**——不破坏 prompt cache |
| L2 | Time-Based MicroCompact | 空闲 >1 小时（cache TTL 过期） | 将旧工具结果内容替换为 `[Old tool result content cleared]` | **极低**——仅清内容不改结构 |
| L3 | Session Memory Compact | token 达 ~83% 窗口 | 利用 Session Memory 的结构化笔记裁剪旧消息（保留最近 5 条文本消息 + 10K-40K token 预算） | **低**——不调用 LLM |
| L4 | Full Auto-Compact | L3 不够或失败 | 调用 LLM 生成 9 章节摘要（目标/概念/文件/错误/过程/用户消息/待办/当前工作/下一步），然后自动恢复最近 5 个文件 + 活跃 Skill + Plan | **中**——一次 LLM 调用（20K output token 预算） |
| L5 | Reactive PTL Recovery | API 返回 `prompt_too_long` | 裁剪最早的消息组后重试（最多 3 次），每次按 token 超限量或 20% 裁剪 | **高**——丢弃旧消息，但避免报错 |

**关键设计细节**：

- **8 种可清除工具**（MicroCompact 只清这些，保留 Agent/Skill/MCP 结果）：FileRead、Bash、Grep、Glob、WebSearch、WebFetch、FileEdit、FileWrite
- **自动触发阈值**：`有效窗口 - 13,000 token`（200K 窗口 ≈ 83.5%，1M 窗口 ≈ 98.7%）
- **断路器**：连续 3 次 auto-compact 失败后停止重试（曾造成 ~250K 次/天无效 API 调用）
- **压缩后自动恢复**：最近 5 个文件（50K token 预算，每文件 5K 上限）+ 活跃 Skill（25K 预算）+ Plan 文件
- **图片剥离**：压缩前先去掉图片（防止压缩请求本身触发 prompt_too_long）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/compact/microCompact.ts` (531行) | `COMPACTABLE_TOOLS` Set（8 种）、cache_edits 路径、time-based 路径 |
| `services/compact/autoCompact.ts` (351行) | `AUTOCOMPACT_BUFFER_TOKENS = 13_000`、`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3` 断路器 |
| `services/compact/compact.ts` (1705行) | `compactConversation()`、9 章节摘要模板、`POST_COMPACT_MAX_FILES_TO_RESTORE = 5` |
| `services/compact/sessionMemoryCompact.ts` (631行) | `minTokens: 10K`、`maxTokens: 40K`、`minTextBlockMessages: 5` |
| `services/compact/prompt.ts` | `NO_TOOLS_PREAMBLE`（防止模型在摘要时调用工具） |

**Qwen Code 现状**：单层压缩——用户手动触发 `/compress` 或 token 超 70% 阈值时一次性全量压缩。基于字符数（非 token 数）定位分割点，保留后 30% 历史。压缩后不恢复文件/Skill，用户需重新 read 文件。5 章节摘要模板（vs Claude 的 9 章节）。

**Qwen Code 修改方向**：① 新增 MicroCompact——每轮检查旧工具结果，替换为 `[cleared]`（最轻量）；② 阈值从 70% 改为 ~83%（给模型更多工作空间）；③ auto-compact 增加断路器（3 次失败停止）；④ 压缩后自动恢复最近 5 个文件 + 活跃 Skill；⑤ 增加 prompt_too_long 被动恢复（裁剪最早消息组后重试）。

**量化参考**：[RTK](https://github.com/rtk-ai/rtk) 的实测数据表明，仅对命令输出做过滤就能在 30 分钟会话中节省 80% token（118K→24K）。RTK 从**命令输出端**解决，而多层压缩从**上下文历史端**解决——两者互补。

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~800 行
- 开发周期：~7 天（1 人）
- 难点：MicroCompact 与 cache_edits API 集成

**相关文章**：[上下文压缩深度对比](./context-compression-deep-dive.md)

**意义**：长会话是 AI Agent 的核心使用场景——一个复杂重构可能持续 50+ 轮对话。
**缺失后果**：用户需手动 `/compress`，压缩后模型"失忆"——不知道刚才改了哪些文件。
**改进收益**：5 层自动压缩 = 用户零干预 + 压缩后自动恢复文件上下文——长会话无限延续。

---

<a id="item-2"></a>

### 2. Fork Subagent（P0）

**问题**：用户让 Agent 同时做 3 件事（如"研究 A、修改 B、测试 C"），Agent 需要启动 3 个 Subagent 并行执行。但每个 Subagent 都是"从零开始"——不知道之前对话聊了什么，也不知道项目上下文。用户必须在每个 Subagent 的 prompt 中重新描述完整背景。更严重的是，3 个 Subagent 各自向 API 发送完整的对话历史（比如 50K token），总共花 150K token——其中 ~100K 是重复的。

**Claude Code 的解决方案——隐式 Fork**：

省略 `subagent_type` 参数时，Agent 工具不创建新 Subagent，而是 **fork 当前对话**——子进程继承父进程的完整对话历史、系统提示、工具集。关键技巧是 **prompt cache 共享**：

```
父进程对话：[系统提示 | 工具定义 | 消息1 | 消息2 | ... | 消息N]
                          ↑ 这部分所有 fork 完全一致 ↑

Fork A：[...消息N | 占位结果 | "请研究 A"]  ← 共享前缀 cache
Fork B：[...消息N | 占位结果 | "请修改 B"]  ← 共享前缀 cache
Fork C：[...消息N | 占位结果 | "请测试 C"]  ← 共享前缀 cache
```

所有 fork 使用**相同的占位 tool_result 文本**（`FORK_PLACEHOLDER_RESULT`），确保 API 请求的前缀字节完全一致。这样 Anthropic API 的 prompt cache 只需缓存一次前缀，3 个 fork 共享这份缓存——**省 80%+ token 费用**。

**工作原理**：

| 步骤 | 做什么 |
|------|--------|
| 1. 模型调用 Agent 工具（省略 `subagent_type`） | 触发隐式 fork |
| 2. `buildForkedMessages()` 构建子消息 | 克隆父进程最后一条 assistant message + 统一占位 tool_result |
| 3. Fork 以后台任务运行 | `permissionMode: 'bubble'`——权限请求冒泡到父终端 |
| 4. Fork 使用 `CacheSafeParams` | 确保系统提示/工具/模型与父进程字节一致 |
| 5. Fork 完成后返回结果 | 通过 `<task-notification>` 通知父进程 |

**关键约束**：
- Fork 子进程**不能再 fork**（检测 `isInForkChild()` 防止递归）
- 与 Coordinator 模式互斥（Coordinator 有自己的 Worker 机制）
- 权限审批冒泡到父终端（fork 没有自己的 UI）
- 工具集完全继承（`useExactTools: true`，不做过滤）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/AgentTool/forkSubagent.ts` (210行) | `isForkSubagentEnabled()`、`FORK_AGENT` 定义、`FORK_PLACEHOLDER_RESULT`、`buildForkedMessages()` |
| `tools/AgentTool/AgentTool.tsx` (1397行) | fork vs 常规 Subagent 决策树（L318-L356） |
| `utils/forkedAgent.ts` (689行) | `CacheSafeParams`（确保 cache 一致性）、`saveCacheSafeParams()` |

**Qwen Code 现状**：`AgentTool` 要求必须指定 `subagent_type`，Subagent 从零开始——不继承父对话历史，无 prompt cache 共享。5 个 Subagent = 5× 完整 prompt 费用。

**Qwen Code 修改方向**：① `subagent_type` 改为可选——省略时触发 fork；② 新增 `forkSubagent.ts`——克隆父 assistant message + 统一占位 tool_result；③ `CacheSafeParams` 确保 fork 请求前缀一致；④ `isInForkChild()` 防止递归 fork。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~400 行
- 开发周期：~5 天（1 人）
- 难点：保证 prompt cache 前缀字节一致性

**进展**：[PR#2936](https://github.com/QwenLM/qwen-code/pull/2936)（open）— 省略 `subagent_type` 参数触发隐式 fork，继承父对话上下文并在后台运行。

**相关文章**：[Fork Subagent Deep-Dive](./fork-subagent-deep-dive.md)

**意义**：大型任务需拆分给多个 Subagent 并行处理——上下文传递效率决定成本和准确率。
**缺失后果**：每个 Subagent 独立上下文 = 5× 完整 prompt 费用 + 需重复描述背景 + 可能遗漏关键上下文。
**改进收益**：Fork = 完整上下文继承（零丢失）+ prompt cache 共享（5 个 Subagent 省 80%+ token）。

---

<a id="item-3"></a>

### 3. Speculation 默认启用（P1）

**思路**：Agent 在每轮工具执行结束后，会向用户展示"下一步建议"（如"要不要运行测试？"）。用户按 Tab 接受后，当前的交互流程是：

1. 用户按 Tab 接受建议
2. Agent 发送完整 API 请求（2-5 秒）
3. 模型返回工具调用指令
4. 执行工具（1-5 秒）
5. 用户才看到结果

问题在于：步骤 2-3 纯属浪费——建议内容是 Agent 自己生成的，模型大概率原样执行。Claude Code 的做法是 **Speculation（预测执行）**：在建议展示给用户的同时，后台已经启动 API 调用和工具执行。用户按 Tab 时，结果已经准备好，实现零延迟响应。

Qwen Code v0.15.0 已实现完整 speculation 系统（包括 overlay 文件系统确保预测执行不影响真实环境），但 `enableSpeculation` 默认关闭。核心工作是评估安全性后默认开启，并扩大 `speculationToolGate` 中 safe 工具的覆盖范围（目前只对少数只读工具启用预测，应扩展到更多无副作用工具）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/PromptSuggestion/speculation.ts` (991行) | `startSpeculation()`、`acceptSpeculation()`、overlay 文件系统 |
| `services/PromptSuggestion/promptSuggestion.ts` | `shouldFilterSuggestion()`（12 条过滤规则） |

**Qwen Code 现状**：speculation 系统已实现但默认关闭（`enableSpeculation: false`）。用户必须手动在配置中启用。safe 工具列表覆盖不足，多数场景不会触发预测执行。

**Qwen Code 修改方向**：`settingsSchema.ts` 中 `enableSpeculation` 默认值 `false` → `true`；`speculationToolGate.ts` 扩大 safe 工具列表。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~10 行
- 开发周期：~1 天（1 人）
- 难点：安全性评估（哪些场景不能 speculate）

**相关文章**：[Prompt Suggestions](../tools/claude-code/10-prompt-suggestions.md)、[输入队列](./input-queue-deep-dive.md) | **进展**：[PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓

**意义**：用户接受建议后的等待时间是交互体验的关键瓶颈。
**缺失后果**：每次 Tab 接受后等 2-10 秒完整 API + 工具执行。
**改进收益**：Tab 接受零延迟——建议展示时预执行已完成，支持连续 Tab-Tab-Tab。

---

<a id="item-4"></a>

### 4. 会话记忆 SessionMemory（P1）

**思路**：开发者在同一个项目上反复使用 Agent。典型场景：你花了 30 分钟告诉 Agent "这个项目用 monorepo 结构"、"测试用 Vitest 不用 Jest"、"`/api` 目录下的路由需要鉴权中间件"。关掉终端，第二天重新打开——Agent 全忘了，你需要重新解释一遍。

Claude Code 的解决方案是 **Session Memory**——session 结束时自动提取关键信息（技术栈、架构决策、已知陷阱），持久化到本地文件。下次启动时检索相关记忆并注入系统提示：

| 阶段 | 做什么 |
|------|--------|
| Session 结束 | 调用 LLM 从对话中提取关键决策/文件结构/技术栈，写入 `.claude/memory/` |
| 新 Session 启动 | `findRelevantMemories()` 按当前工作目录和最近文件检索相关记忆 |
| 注入系统提示 | `loadMemoryPrompt()` 将记忆拼入 system prompt（上限 200 行 / 25KB） |
| 压缩协同 | compact 时保留已提取记忆——压缩不会丢失跨 session 知识 |

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/SessionMemory/sessionMemory.ts` | 会话记忆提取 + 存储 |
| `services/SessionMemory/prompts.ts` | 记忆提取 Prompt |
| `memdir/findRelevantMemories.ts` | 相关性检索 |
| `memdir/memdir.ts` | `loadMemoryPrompt()`（200 行 / 25KB 截断） |

**Qwen Code 现状**：无跨 session 记忆机制。每次新 session 的系统提示只包含 `QWEN.md` 静态规则，不包含之前 session 中学到的项目知识。

**Qwen Code 修改方向**：新建 `services/sessionMemoryService.ts`；在 session 结束的 hook 中调用提取逻辑；`prompts.ts` 的 `getCustomSystemPrompt()` 注入检索结果。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~600 行
- 开发周期：~5 天（1 人）
- 难点：记忆相关性检索算法

**相关文章**：[记忆系统深度对比](./memory-system-deep-dive.md)

**意义**：开发者在同一项目上反复使用 Agent，跨 session 知识断层导致效率低下。
**缺失后果**：每次新 session 从零开始——反复告知项目背景、编码规范、已知坑点。
**改进收益**：新 session 自动注入相关记忆——Agent"记住"项目上下文，无需反复说明。

---

<a id="item-5"></a>

### 5. Auto Dream 自动记忆整理（P1）

**思路**：有了 Session Memory（第 4 项）后，记忆文件会随使用不断膨胀。一个活跃项目用了 50 个 session 后，记忆中可能出现：

- **重复**：5 条都说"项目用 TypeScript + Vitest"
- **过时**："数据库用 MySQL"（三周前已迁移到 PostgreSQL）
- **矛盾**：早期记忆说"API 不需要鉴权"，近期记忆说"所有 API 需要 JWT"

这些问题不处理，模型会收到互相矛盾的指令，行为变得不可预测。

Claude Code 的做法是 **Auto Dream**——在 session 启动时检查两个门控条件（距上次整理 >24 小时 **且** 已积累 >5 个新 session），满足时在后台 fork 一个只读 Agent 执行记忆整理：

| 步骤 | 做什么 |
|------|--------|
| 1. 门控检查 | 距上次整理 >24h 且 >5 个新 session |
| 2. 获取文件锁 | 防止多个终端实例同时整理 |
| 3. Fork 后台 Agent | 只读模式，不影响当前 session |
| 4. 整理操作 | 合并重复、删除过时、解决矛盾 |

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/autoDream/autoDream.ts` (324行) | 门控逻辑、forked agent 调度 |
| `services/autoDream/consolidationPrompt.ts` | 整理 Prompt 模板 |
| `services/autoDream/consolidationLock.ts` | 文件锁防并发 |

**Qwen Code 现状**：无记忆整理机制。即使实现了 Session Memory，记忆文件也会无限增长，开发者无法手动维护。

**Qwen Code 修改方向**：新建 `services/autoDream/`；在 `SessionStart` hook 中检查门控条件；满足时 fork 后台 agent 执行整理。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：记忆合并冲突解决

**相关文章**：[记忆系统深度对比](./memory-system-deep-dive.md)

**意义**：记忆文件随使用膨胀，陈旧/矛盾记忆导致模型行为异常。
**缺失后果**：记忆无限增长占满 token 预算，旧决策与新决策矛盾共存。
**改进收益**：后台自动整理——合并重复、删除过时、解决矛盾，记忆始终精简。

---

<a id="item-6"></a>

### 6. Mid-Turn Queue Drain（P0）

**思路**：你让 Agent 重构一个模块，它计划执行 8 个工具调用（读 3 个文件、改 3 个文件、运行测试、提交）。执行到第 2 步时，你发现它理解错了需求——但你的纠正消息只能排队等待，必须等全部 8 步完成后才会被模型看到。第 3-8 步做的全是无用功，甚至可能需要手动撤销。

Claude Code 的解决方案是 **Mid-Turn Queue Drain**——在推理循环中，每个工具批次执行完后、下一次 API 调用前，检查用户输入队列：

```
工具批次1执行完 → 检查队列（有新消息？）→ 注入 toolResults → API 调用2
                        ↑ 用户纠正在这里被模型看到
```

输入队列分三个优先级：

| 优先级 | 含义 | 典型用途 |
|--------|------|----------|
| `now` | 立即注入 | Escape 中断 |
| `next` | 下个工具批次前注入 | 用户补充指令 |
| `later` | 当前 turn 结束后注入 | 排队消息 |

关键在于用户不需要中断 Agent——消息在后台排队，Agent 在下一个 step 自然看到并调整方向。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `query.ts` (L1550-L1643) | `getCommandsByMaxPriority()`、`getAttachmentMessages()`、`removeFromQueue()` |
| `utils/messageQueueManager.ts` | 优先级队列（`now`/`next`/`later`）、`dequeue()` 带 filter |

**Qwen Code 现状**：用户输入在 Agent 执行期间被阻塞，只能通过 Escape 完全中断。没有"排队后自然注入"机制。

**Qwen Code 修改方向**：在 `agent-core.ts` 的 `processFunctionCalls()` 返回后、下一轮 `while` 迭代前，调用 `queue.dequeue()` 并将消息注入到下一次 API 调用的 history 中。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~3 天（1 人）
- 难点：中断安全性（不能在写操作中途中断）

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md) | **进展**：[PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) ✓ 已合并

**意义**：用户在 Agent 执行多步操作时发现方向错误，无法及时纠正。
**缺失后果**：必须等所有步骤完成后才能发送新指令——已完成的错误工作需撤销。
**改进收益**：用户输入在当前 turn 的下一个 step 即被模型看到——避免无用工作。

---

<a id="item-7"></a>

### 7. 智能工具并行（P1）

**思路**：Agent 在探索代码时，模型经常一次返回多个工具调用：比如"读 `package.json`、读 `tsconfig.json`、grep 搜索 `import` 语句、glob 查找 `*.test.ts`"。这 4 个操作都是只读的、互不依赖，但当前 Qwen Code 串行执行——每个等上一个完成才开始。4 个各 500ms 的 I/O 操作，总计花 2 秒。如果并行执行，只需 500ms。

Claude Code 的做法是 **智能分批**——每个工具声明自己是否并发安全（`isConcurrencySafe()`），运行时将连续的安全工具合并为一个并行批次：

```
模型返回: [Read A, Grep B, Glob C, FileEdit D, Read E, Read F]
          ╰──── 并行批次1 ────╯   ╰串行╯   ╰─ 并行批次2 ─╯

执行顺序: 批次1 并行(3个) → D 串行 → 批次2 并行(2个)
```

关键设计：
- 并行批次上限 10 个（防止资源耗尽）
- 遇到写操作（FileEdit、Bash 等）立即切为串行
- 并行批次中如果某个 Bash 命令失败，通过 `siblingAbortController` 级联取消同批次的其他 Bash 调用
- 并行期间的上下文修改队列化，批次结束后串行应用

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/tools/toolOrchestration.ts` (188行) | `partitionToolCalls()`、`runToolsConcurrently()`、`runToolsSerially()` |
| `services/tools/StreamingToolExecutor.ts` (530行) | `canExecuteTool()`、Bash 错误级联（`siblingAbortController`） |
| `Tool.ts` (L402) | `isConcurrencySafe()` 接口 |

**Qwen Code 现状**：所有工具调用串行执行（`coreToolScheduler.ts` 中 `otherCalls` 逐个 await）。没有并发安全标记，无法区分只读和写入操作。

**Qwen Code 修改方向**：`coreToolScheduler.ts` 中将 `otherCalls` 的顺序执行改为按 `kind` 分批并行；在 `tools.ts` 基类新增 `isConcurrencySafe` 属性（read 工具默认 true）。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：上下文修改的队列化与串行应用

**相关文章**：[工具并行执行](./tool-parallelism-deep-dive.md) | **进展**：[PR#2864](https://github.com/QwenLM/qwen-code/pull/2864)

**意义**：代码探索场景（多个 Read + Grep + Glob）是最常见的 Agent 操作之一。
**缺失后果**：7 个只读工具串行执行 = 7× 延迟。
**改进收益**：只读工具并行 = 1× 延迟，I/O 密集任务快 5-10×。

---

<a id="item-8"></a>

### 8. 启动优化（P1）

**思路**：开发者打开终端敲 `qwen-code`，进入 REPL 后立刻开始打字。两个常见的体验问题：

1. **首次 API 调用慢**：用户发第一条消息时，HTTP 客户端才开始 TCP 连接 + TLS 握手（100-200ms）。这个延迟完全可以提前消除——在启动初始化阶段就预建连接。
2. **启动打字丢失**：REPL 界面需要 200-500ms 初始化（加载配置、渲染 UI）。用户在这期间打的字全部丢失——只能等界面就绪后重新输入。

Claude Code 用两个独立优化解决这两个问题：

| 优化 | 做什么 | 效果 |
|------|--------|------|
| **API Preconnect** | 启动时 fire-and-forget HEAD 请求预热 TCP+TLS | 首次 API 调用省 100-200ms |
| **Early Input** | REPL 未就绪时用 raw mode 捕获键盘输入，就绪后预填充到输入框 | 启动打字不丢失 |

Preconnect 实现极简（71 行）——发一个不等响应的 HEAD 请求，纯粹为了让操作系统完成 TCP 三次握手和 TLS 协商。Early Input 稍复杂——需要处理退格、方向键、粘贴等输入事件，确保预填充内容与用户预期一致。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/apiPreconnect.ts` (71行) | `preconnectAnthropicApi()`（fire-and-forget HEAD） |
| `utils/earlyInput.ts` (191行) | `startCapturingEarlyInput()`、`consumeEarlyInput()`、`processChunk()` |

**Qwen Code 现状**：无 preconnect 机制，首次 API 调用承担完整握手延迟。无 early input 捕获，REPL 初始化期间的用户输入丢失。

**Qwen Code 修改方向**：`gemini.tsx` 入口最早处调用 preconnect（DashScope/Gemini 端点）；新增 `earlyInput.ts` 在 `process.stdin.setRawMode(true)` 下捕获，`AppContainer` mount 时 consume。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：确保 preconnect 与首次请求使用同一连接池

**相关文章**：[启动阶段优化](./startup-optimization-deep-dive.md)

**意义**：启动体验是用户对工具的第一印象。
**缺失后果**：首次 API 需完整 TCP+TLS 握手（+100-200ms），启动打字丢失。
**改进收益**：preconnect 省 150ms + 启动打字不丢失——感知启动更快。

---

<a id="item-9"></a>

### 9. 按路径自动注入上下文规则（P1）

**用户痛点**：

当前 Qwen Code 只有一个全局 `QWEN.md`——所有指令塞在一起，不管 Agent 操作什么文件都全部加载。这导致两个问题：

1. **Token 浪费**：操作 Python 文件时，TypeScript 规范也在系统提示中
2. **规则互相矛盾**：前端规范"用函数式"和后端规范"用 class"同时存在，模型困惑

这不只是编码规范的问题——**任何与特定文件/目录相关的上下文指令**都有同样的痛点：数据库迁移的安全规则、API 端点的安全检查、测试文件的编写规范、部署配置的运维规则……全部挤在一个文件里。

**Claude Code 的解决方案**：

在 `.claude/rules/` 目录下创建多个规则文件，每个文件用 YAML frontmatter 的 `paths:` 字段指定**生效路径**——本质是**按文件路径过滤的上下文注入机制**：

```markdown
<!-- .claude/rules/frontend.md — 编码规范 -->
---
paths:
  - "packages/frontend/**/*.tsx"
  - "packages/frontend/**/*.ts"
---

React 组件必须用函数式写法，禁止 class component。
使用 Tailwind CSS，不要写内联样式。
```

```markdown
<!-- .claude/rules/database-safety.md — 数据库迁移安全规则 -->
---
paths:
  - "**/migrations/**"
  - "**/models/**"
---

大表（>100万行）禁止 NOT NULL 加列不带默认值。
必须先加列后回填，不要在迁移中 UPDATE 全表。
索引用 CREATE INDEX CONCURRENTLY。
```

```markdown
<!-- .claude/rules/api-security.md — API 安全检查 -->
---
paths:
  - "**/api/**"
  - "**/routes/**"
---

所有用户输入必须参数化，禁止字符串拼接 SQL。
文件上传必须校验 MIME type + 文件头魔数。
敏感端点必须加 rate limiting。
```

```markdown
<!-- .claude/rules/test-patterns.md — 测试规范 -->
---
paths:
  - "**/*.test.ts"
  - "**/*.spec.ts"
---

用 describe/it 而非 test()。
Mock 外部依赖，不 Mock 内部模块。
每个 test 只断言一个行为。
```

**加载规则**：
- 有 `paths:` 的规则 → Agent 操作匹配文件时才加载（惰加载）
- 没有 `paths:` 的规则 → session 启动时加载（急加载）
- HTML 注释 `<!-- ... -->` 自动剥离，不占 token

**效果**：Agent 编辑数据库迁移文件时自动注入安全规则；编辑 API 路由时注入安全检查；编辑测试文件时注入测试规范——每种场景只加载相关的指令，精准且省 token。

**Claude Code 参考**：

- 官方文档：[Memory - Organize rules with .claude/rules](https://code.claude.com/docs/en/memory#organize-rules-with-clauderules)
- 源码：`utils/claudemd.ts`（1,479 行）`processMdRules()` + `utils/frontmatterParser.ts` `paths:` glob 解析

**Qwen Code 现状**：仅支持单一 `QWEN.md` 全局指令文件，无条件加载机制。所有规则始终注入系统提示。

**Qwen Code 修改方向**：
1. 支持 `.qwen/rules/` 目录 + YAML frontmatter `paths:` 字段
2. `memoryDiscovery.ts` 区分急/惰加载
3. 文件操作时触发条件规则匹配

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~3 天（1 人）

**相关文章**：[指令文件加载](./instruction-loading-deep-dive.md)

---

<a id="item-10"></a>

### 10. Team Memory 组织级记忆（P1）

**思路**：一个 5 人团队协作开发同一个项目。开发者 A 在使用 Agent 过程中发现"这个项目的 CI 必须先跑 `pnpm build` 再跑测试，否则类型检查会失败"——这条知识保存在 A 的个人记忆中。开发者 B 遇到同样的坑，又花 10 分钟排查。新成员 C 入职，所有坑都要重新踩一遍。

问题本质：Session Memory（第 4 项）是个人级别的，团队知识无法共享。

Claude Code 的解决方案是 **Team Memory**——per-repo 级别的团队记忆同步。记忆分为 `private/`（个人）和 `team/`（共享）两个目录，team 目录通过 API 在团队成员间同步：

| 机制 | 做什么 |
|------|--------|
| Delta Sync | 只上传变更的 key（非全量），ETag + SHA256 per-key 校验和防冲突 |
| 实时推送 | fs.watch 监控 team 目录，2s debounce 后自动上传 |
| 密钥扫描 | 上传前用 29 条 gitleaks 规则扫描，防止 API Key/密码等敏感信息泄露 |
| 批次限制 | 单次上传最大 200KB（`MAX_PUT_BODY_BYTES`） |

开发者 A 执行 `/memory --team add "CI 必须先 build 再 test"` 后，团队其他成员下次启动 session 时自动拉取这条知识。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/teamMemorySync/index.ts` | delta sync 编排、`MAX_PUT_BODY_BYTES = 200KB` 批次 |
| `services/teamMemorySync/secretScanner.ts` | 29 条 gitleaks 规则 |
| `services/teamMemorySync/watcher.ts` | fs.watch + 2s debounce |
| `memdir/teamMemPrompts.ts` | private + team 双目录提示构建 |

**Qwen Code 现状**：记忆系统仅支持个人级别，无团队共享机制。团队成员各自积累的项目知识无法同步。

**Qwen Code 修改方向**：新建 `services/teamMemorySync/`；API 端点对接阿里云/自建后端；`memoryTool.ts` 扩展为 private/team 双目录。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~500 行
- 开发周期：~5 天（1 人）
- 难点：并发同步冲突解决 + 密钥扫描

**相关文章**：[Team Memory 深度对比](./team-memory-deep-dive.md)

**意义**：团队协作项目中，个人发现的项目知识无法共享是效率瓶颈。
**缺失后果**：团队成员各自维护独立记忆——项目知识孤岛，新成员从零积累。
**改进收益**：一人学到的知识自动同步全团队 + 29 条规则防止密钥泄露。

---

<a id="item-11"></a>

### 11. 工具动态发现 ToolSearchTool（P1）

**思路**：Agent 接入 MCP 后，可用工具数量会急剧增长——核心内置工具 ~15 个，加上用户配置的 MCP server（数据库查询、Slack 发消息、Jira 管理等），总工具数可达 39+。每个工具的 schema（名称、描述、参数定义）需要注入系统提示，让模型知道有哪些工具可用。问题：39 个工具 schema 占 ~15K+ token，在 200K 窗口中看似不多，但这是**每次 API 调用都重复发送**的固定开销。

Claude Code 的做法是 **延迟加载（Deferred Tools）**——系统提示中只注入核心工具（~10 个，如 Read、Edit、Bash、Grep），其余工具只列名称（不含完整 schema）。模型需要使用非核心工具时，先调用 `ToolSearch`：

```
模型："我需要查询数据库"
  → 调用 ToolSearch("database query")
  → 返回匹配的 MCP 工具完整 schema
  → 模型用返回的 schema 调用该工具
```

ToolSearch 支持两种查询模式：
- **关键词搜索**：`ToolSearch("slack send message")` —— 按相关性评分返回匹配工具
- **精确选择**：`ToolSearch("select:SlackSend,JiraCreate")` —— 按名称直接加载

MCP 工具始终标记为 deferred（因为数量不可控），内置工具中标记 `alwaysLoad` 的豁免。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/ToolSearchTool/ToolSearchTool.ts` (472行) | keyword 评分（MCP 12/6分, 普通 10/5分）、`select:` 直接选择 |
| `tools/ToolSearchTool/prompt.ts` | `isDeferredTool()` 分类逻辑、`alwaysLoad` 豁免 |

**Qwen Code 现状**：所有工具（包括 MCP 工具）的完整 schema 在 session 启动时全部注入系统提示。没有延迟加载机制。

**Qwen Code 修改方向**：工具注册表新增 `deferred: boolean` 属性；新建 `tools/toolSearch.ts`；`coreToolScheduler.ts` 在工具 schema 注入时过滤 deferred 工具。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~3 天（1 人）
- 难点：工具相关性排序算法

**相关文章**：[工具搜索与延迟加载](./tool-search-deep-dive.md)

**意义**：39+ 工具 schema 全部注入系统提示占用大量 token——尤其 MCP 工具。
**缺失后果**：系统提示 ~15K+ tokens 被工具 schema 占满，留给用户内容的空间减少。
**改进收益**：仅加载核心工具（~10 个），其余按需搜索——系统提示 token 减少 50%+。

---

<a id="item-12"></a>

### 12. Commit Attribution（P1）

**思路**：开发者用 Agent 写了一个功能，Agent 修改了 5 个文件后执行 `git commit`。三个月后，团队做代码审计时需要回答："这段代码是人写的还是 AI 生成的？AI 贡献了多少？"——看 git log 完全无法区分。

这在两个场景下特别关键：
- **开源项目**：越来越多的开源社区要求披露 AI 生成内容
- **企业合规**：安全审计需要知道哪些代码经过人类审查、哪些是 AI 直接生成的

Claude Code 的做法是 **自动归因**——跟踪每个文件中 AI vs 人类的字符贡献比例，并在 commit 时自动注入元数据：

| 机制 | 做什么 |
|------|--------|
| 字符归因 | 对比 diff 的前缀/后缀，计算每个文件中 AI 贡献的字符比例 |
| Co-Authored-By | commit 消息自动追加 `Co-Authored-By: Claude <noreply@anthropic.com>` |
| Git Notes | 详细的 per-file 归因元数据存入 git notes（不影响 commit 历史） |
| 模型名清理 | 内部模型代号（如 `claude-opus-4-20250514`）在外部仓库自动替换为公开名 |

开发者无需手动操作——Agent 检测到 `git commit` 命令时自动注入 trailer 和 notes。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/commitAttribution.ts` (961行) | 按文件字符归因、`INTERNAL_MODEL_REPOS` 清理 |
| `utils/attributionTrailer.ts` | Co-Authored-By 注入 |

**Qwen Code 现状**：无 commit 归因机制。Agent 执行的 `git commit` 与人类手动提交在 git 历史中无法区分。

**Qwen Code 修改方向**：新建 `utils/commitAttribution.ts`；在 `shell.ts` 检测到 `git commit` 时注入 trailer。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：准确计算 AI vs 人类代码比例

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

**意义**：AI 生成代码的透明度和可追溯性是开源社区和企业合规的核心关注。
**缺失后果**：git 历史无法区分 AI 和人类代码——合规审计困难。
**改进收益**：commit 自动标注 AI 贡献比例——满足开源 AI 披露和企业审计要求。

---

<a id="item-13"></a>

### 13. 会话分支 /branch（P1）

**问题场景**：你和 Agent 讨论了 20 轮，决定用"方案 A"重构认证模块。Agent 已经改了 5 个文件。但你突然想到："如果用方案 B（JWT 替换 Session）会不会更好？" 现在你面临两难：

- **继续方案 A**：放弃探索方案 B 的可能
- **尝试方案 B**：让 Agent 撤销方案 A 的所有修改，从头开始——但如果方案 B 不好，方案 A 的工作全部丢失
- **手动保存**：手动 `git stash`、复制对话历史……太繁琐

**Claude Code 的方案——/branch 命令**：从当前对话的任意位置创建一个"分支"，就像 git 分支一样——原始对话保留不动，分支独立探索：

```
原始 session（方案 A）：
  轮次 1 → 轮次 2 → ... → 轮次 20 → [继续方案 A]
                                    ↘
分支 session（方案 B）：              轮次 20 → "试试 JWT 方案" → ...
                                    （完整继承前 20 轮上下文）
```

**工作原理**：

| 步骤 | 做什么 |
|------|--------|
| 1. 用户输入 `/branch` | 触发分支创建 |
| 2. 复制 transcript JSONL | 完整对话历史复制到新文件 |
| 3. 写入溯源元数据 | `forkedFrom: { sessionId, messageUuid }` |
| 4. 自动命名 | 原名 + " (Branch)"，支持去重 |
| 5. 切换到分支 | 分支成为当前活跃 session |
| 6. 原始可恢复 | 随时 `--resume` 回到方案 A |

**改进前后对比**：
- **改进前**：想尝试替代方案 → 要么丢弃当前进度，要么手动保存/恢复
- **改进后**：`/branch` → 分支继承完整上下文独立探索 → 不满意随时切回原始

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/branch/branch.ts` (296行) | `getUniqueForkName()`、transcript 复制 + `forkedFrom` 元数据 |

**Qwen Code 现状**：没有 `/branch` 命令。用户想探索替代方案只能：手动 `git stash` 保存文件变更 → 开新 session → 重新描述上下文 → 尝试新方案 → 不满意再手动恢复。

**Qwen Code 修改方向**：① 新建 `/branch` 命令；② `sessionService.ts` 新增 `forkSession()` 方法（复制 JSONL + 写入 `forkedFrom` 元数据）；③ 自动命名 + 去重（`getUniqueForkName()`）；④ `/resume` 命令支持列出原始和分支 session。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：JSONL transcript 的高效复制（大 session 可能有数 MB）

**进展**：[PR#3022](https://github.com/QwenLM/qwen-code/pull/3022)（open）— `/branch` 命令，会话分叉为独立副本，标题防碰撞命名（"My Task (Branch)"），`/resume {sessionId}` 支持直接跳转。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

**意义**：探索替代方案是软件开发的日常——架构选型、算法对比、重构策略 A/B 测试。
**缺失后果**：探索替代方案必须丢弃当前进度——开发者不敢轻易尝试。
**改进收益**：`/branch` = 零风险探索——不满意切回原始，满意继续分支，两边进度都保留。

---
