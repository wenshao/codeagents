# Qwen Code 改进建议 — GitHub Code Review 多 Agent 审查 (Multi-Agent Code Review)

> 核心洞察：随着大模型上下文窗口的激增，把整个 Pull Request 的 Diff 扔给大模型做 Code Review 已经不是难事。但是，一个涵盖了 30 个文件、上千行改动的巨型重构 PR，如果只丢给一个单一的大模型（Agent）去从头看到尾，它极容易犯“只看宏观不看细节”的毛病。往往会漏掉隐藏在角落里的逻辑死锁或者极其微小的安全漏洞。Claude Code 采用了一种重型工业级的解法：对于复杂 PR，它不在单一进程内苦干，而是动态派生（Fork）出多个带有不同“审查人格”的 Agent 并发阅读，最后将审查意见交叉验证、去重后形成最终的高质量总结返回；而 Qwen Code 目前还是传统的单线单模型审阅。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、单一 Agent 面对巨型 PR 的力不从心

### 1. Qwen Code 现状：走马观花的审查者
如果我们在 CI 流水线中让 Qwen Code 审查一个数百行改动的 PR：
- **痛点一（注意力漂移）**：大语言模型（LLM）的“Lost in the Middle（中部注意力丢失）”现象依然存在。当它在试图理解一个横跨 5 个模块的业务流改造时，它很难同时兼顾去检查某个深层 Util 函数有没有发生越界读取（Out of Bounds）的小错误。
- **痛点二（极高的误报率）**：很多简单直接的审查脚本，会让大模型产生一堆诸如“这个变量名拼写建议修改”、“这里可以用解构赋值”的微不足道（Nitpick）的评论，满屏都是这种没营养的话，会让真正干活的开发者极其反感，甚至干脆关掉 AI 审查。

### 2. Claude Code 的专家会诊模式：Multi-Agent 并发过滤
在 Claude Code 后端的 Code Review 官方插件及工作流配置中，审查一个 PR 并不是一次 API 请求能结束的，而是一个小型的“医生会诊”。

#### 机制一：人格拆分与并行扫描 (Parallel Auditing)
系统并不是只拉起一个通用的审查者，而是根据 PR 文件的类型和数量，并行拉起多个带有专一指令的小 Agent（比如使用速度极快、极便宜的 Haiku 模型）：
- **Agent A (安全卫士)**：你的眼里只有 SQL 注入、XSS、鉴权越权等安全漏洞。不要看代码风格！
- **Agent B (逻辑推演)**：你只负责检查新增的 API 接口是不是涵盖了边界条件和 Error 捕获。
- **Agent C (架构专家)**：只看这 30 个文件之间的引入关系有没有产生循环依赖。

这些 Agent 同时开工，大大缩短了整体等待时间，也极高地压榨出了特定领域的 Bug。

#### 机制二：基于 `REVIEW.md` 的对齐
类似于告诉模型项目编码规范的 `CLAUDE.md`，它允许项目在根目录放一个专有的 `REVIEW.md`。这里面写满了“当前团队 Review 绝不能触碰的红线”和特殊术语。所有并行审查的 Agent 都必须把它作为宪法读入。

#### 机制三：二次验证与去重 (Validation & Deduplication)
这是最关键的一环。
前面那群打工仔（Subagents）查出了 20 个疑似问题。
系统会启动最后一道防线——一个极其聪明的主模型（Leader Agent，如 Opus 或 Sonnet）。它会拿着这 20 个疑似问题再去原始代码里**反向验证（Double Check）**。
- 如果发现某个问题其实在别的文件里已经有解了，直接**过滤（Filter）**掉。
- 如果发现三个问题其实说的是同一件事，直接**合并去重（Deduplication）**。
- 最后，它会对筛选后仅存的 3 个真正的核心 Bug 进行分级（Severity: 🔴 Important / 🟡 Nit / 🟣 Pre-existing），并调用 `gh api` 极其精准地把带有高亮的评论发表在 GitHub PR 的**对应代码行（Inline Comment）**上。

## 二、Qwen Code 的改进路径 (P1 优先级)

如果想让企业客户愿意为 AI Review 掏钱，就必须把“专家会诊”架构搬进 Qwen Code。

### 阶段 1：开发基础的多 Agent 并行框架
1. 利用我们在 [Coordinator/Swarm 编排模式](./coordinator-swarm-orchestration-deep-dive.md) 中提过的技术底座。
2. 编写 `commands/review/multiAgentReview.ts`。接收一个 PR 号，将其文件 Diff 按照数量或类型切分成 N 块。

### 阶段 2：定义专门的审查提示模板
为不同的审查 Agent 设置独立的 System Prompt Sections。例如编写专用的 `PromptTemplates.SecurityAuditor` 和 `PromptTemplates.LogicValidator`。

### 阶段 3：引入结果聚合器与验证流
在所有子进程 Promise 返回后，不要立刻打印。
1. 将返回的结果数组拼成一个巨大的 JSON 列表。
2. 给主控 Agent 发送最后一次验证请求：“这是从代码中挑出的潜在问题，请扮演高级架构师，剔除掉那些吹毛求疵（Nitpicks）或是存在误报的条目，仅保留会引起运行时崩溃的致命问题。”
3. 最后，将精华数据通过 GitHub API `POST /repos/{owner}/{repo}/pulls/{pull_number}/comments` 写入具体的行。

## 三、改进收益评估
- **实现成本**：高。它涉及到极其复杂的 Prompt 工程（防误报）和 GitHub API 的深度集成交互，需要至少一周以上的研发和数据微调。
- **直接收益**：
  1. **碾压传统静态扫描工具**：彻底告别 SonarQube 等工具死板的警告，给出带有极强语境理解的高分逻辑报错，成为市面上无可挑剔的智能审查霸主。
  2. **建立绝对的信任感**：通过过滤掉无用的低信噪比发言（Nitpicks），让开发者一看到 Qwen Code 的评论，就知道“这里真的出了大问题必须修”，极大地建立品牌威信。