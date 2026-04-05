# Qwen Code 改进建议 — GitHub Code Review 多 Agent 并行审查 (Multi-Agent Code Review)

> 核心洞察：代码审查（Code Review）是代码合并前最耗时、最关键的环节。当开发者提交一个涉及 20 个文件的复杂 PR 时，让人工审查或单线程的大模型去逐个文件阅读，效率极低且容易遗漏重点。Claude Code（在其官方文档与托管方案中体现）利用了多 Agent 并行架构：每个子 Agent 只负责一部分文件，或者只专注于一种审查维度（例如逻辑、安全、性能），最终聚合生成一条高质量的、去重的 Inline Comment 审查报告；而 Qwen Code 目前仅能顺序执行简单的审查。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、当前 Code Review 模式的痛点

### 1. Qwen Code 现状：串行与上下文溢出
Qwen Code 目前具备基础的 `/review` 命令，但其实现逻辑较为基础：
- 它会将 `git diff` 或者当前变动的文件一次性读取，并把整个差异（Diff）全量投喂给主大模型。
- **痛点一**：如果 PR 过大，这种方式极易触发 Token 上限或 `prompt_too_long`。
- **痛点二**：大模型在一次性处理大量文件时容易产生注意力分散（Lost in the middle），只能给出一些诸如“代码风格统一”、“补充了注释”等毫无营养的表面结论。
- **痛点三**：执行过程是单线程阻塞的，大 PR 可能需要跑几分钟甚至十几分钟。

### 2. 理想的多 Agent 并行 Review (以 Claude 为参考)
在现代 AI 审查实践中，最佳模式是分发与聚合（Map-Reduce）：
- **分发 (Map)**：主进程解析 PR 的文件列表，按照文件数量或逻辑模块，生成多个独立的子 Agent。甚至可以生成职能各异的 Agent（例如：Agent A 专门看是否有安全注入风险；Agent B 专门看是否符合项目里配置的 `QWEN.md` 规范）。
- **并行执行 (Parallel Execution)**：这多个 Agent 被同时唤起执行，时间消耗等同于最慢的那一个文件审查时间。
- **聚合与去重 (Reduce & Deduplication)**：由于大模型经常给出误报，主节点在收到各个子 Agent 返回的潜在缺陷后，进行一次汇总过滤（例如：过滤掉“遗留问题 / Pre-existing”，专注于新增的逻辑错误），并自动按照严重程度（🔴 Important / 🟡 Nit）分类。
- **Inline Comment**：最后利用 GitHub API 在对应的代码行直接发起精确的行内评论（Inline Comment），而非笼统地评论在 PR 首页。

## 二、Qwen Code 的改进路径 (P1 优先级)

让 Qwen Code 成为 GitHub 仓库里那个“响应最快、审查最细”的无情审查机器。

### 阶段 1：基础的 PR Review 插件化
1. 开发一个专有的指令 `/code-review [PR_URL]`。
2. 内部拉起一个解析器，利用 `gh api` 或 `octokit` 获取 PR 的具体文件 Diff 列表及改动行信息。

### 阶段 2：构建多 Agent 分发模型
1. 依赖之前我们探讨过的 `InProcess 同进程多 Agent 隔离` 和 `AsyncLocalStorage` 机制，安全地在进程内启动多个 Subagent。
2. 按文件大小或者目录拆分，每个子 Agent 被赋予独立的 Prompt：
   > “你负责审查 `src/backend/` 下的这 3 个文件变动。重点寻找空指针、SQL 注入、未处理异常等高风险问题。”
3. 使用 `Promise.all` 等待所有审查 Agent 完成。

### 阶段 3：审查验证与结构化输出 (Inline Annotations)
1. 设立一个最终的“验证 Agent”或者简单的规则引擎，对返回的问题数组进行去重。
2. 使用统一的 Schema 输出（配合 `--json-schema` 参数）：
   ```json
   {
      "reviews": [
         { "path": "src/auth.ts", "line": 42, "severity": "important", "comment": "Potential SQL injection here." }
      ]
   }
   ```
3. 通过 CI 脚本调用 GitHub Review API 将这些数据精准挂载到代码变动行上。

## 三、改进收益评估
- **实现成本**：高。需要结合并行隔离机制、多模型协同策略，并深入理解 GitHub 的 Review API。
- **直接收益**：
  1. **10倍速的审查效率**：原本需要十几分钟的长文分析缩短到 1-2 分钟。
  2. **企业级信赖**：大幅降低虚假警报（False Positives），提供真正深度、多维度的安全和逻辑双重审查，成为企业愿意掏钱部署的核心功能。