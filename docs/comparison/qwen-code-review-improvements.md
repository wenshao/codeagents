# Qwen Code /review 功能改进建议

> 基于 Qwen Code 本地源码、Copilot CLI 二进制分析、Claude Code / Gemini CLI 对比，以及 GitHub 官方文档，对 Qwen Code `/review` 的现状、差距与改进方向进行梳理。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md) | [/review 命令对比](./review-command.md)

## 一、结论摘要

Qwen Code 的 `/review` 已经不是“缺失能力”，而是一个**可用但仍偏 prompt 驱动**的本地审查方案：

- 已支持 **本地未提交变更、PR、单文件** 三种目标
- 已支持 **4 个并行审查 Agent + 去重 + 独立验证 Agent**
- 已支持 `--comment` 将结果发布为 **PR inline comments + overall review verdict**
- 但其核心仍主要由 `SKILL.md` 编排，缺少更强的**确定性执行链路、状态持久化、增量缓存、后台任务化 orchestration**

Copilot Code Review 之所以在 GitHub PR 页面上体感更好，核心不只是模型能力，而是：

1. **PR review 是强约束任务**：输入是 diff、base branch、PR 元数据，输出是行级评论
2. **GitHub 平台拥有原生工作流优势**：PR title/body、评论、review、checks、code scanning、merge gate 在同一个产品面中协同
3. **高 precision 优先**：少报但尽量报准，降低 review 噪音
4. **AI review 与确定性扫描/修复链路耦合更深**：例如 code scanning alert、Copilot Autofix、GitHub Actions 驱动的 cloud agent

因此，Qwen Code 的改进方向不应仅停留在“补 prompt”，而应分为两层：

- **Prompt 层增强**：确定性分析、构建/测试、跨文件追踪、规则注入、评论聚合
- **产品层增强**：后台审查、结果持久化、增量缓存、autofix pipeline、托管式 GitHub review 流程

## 二、当前 Qwen Code `/review` 的真实能力边界

## 2.1 当前入口与目标类型

Qwen Code 的 `/review` 是一个 bundled skill，而不是内置 TypeScript slash command。

支持三类审查目标：

- **无参数**：审查当前工作区未提交变更（`git diff` + `git diff --staged`）
- **PR 号或 URL**：检出目标 PR，再进行审查
- **文件路径**：仅审查指定文件相对 `HEAD` 的变更

并支持：

- `/review <pr-number> --comment`

用于将审查结果发布到 GitHub PR。

**源码与文档：**
- `源码: ../qwen-code/packages/core/src/skills/bundled/review/SKILL.md`
- `源码: ../qwen-code/packages/cli/src/services/BundledSkillLoader.ts`
- `源码: docs/tools/qwen-code/02-commands.md`

## 2.2 当前执行流程

根据当前 `SKILL.md`，Qwen Code `/review` 的流程更接近下图：

```text
/review [PR号|文件路径] [--comment]
  │
  ├─ Step 1: 确定审查范围
  │   ├─ 无参数 → git diff + git diff --staged
  │   ├─ PR 号 → gh pr checkout + gh pr view
  │   └─ 文件路径 → git diff HEAD -- <file>
  │
  ├─ Step 2: 4 个并行审查 Agent
  │   ├─ Agent 1: Correctness & Security
  │   ├─ Agent 2: Code Quality
  │   ├─ Agent 3: Performance & Efficiency
  │   └─ Agent 4: Undirected Audit
  │
  ├─ Step 2.5: 去重 + 独立验证
  │   ├─ 合并重复 finding
  │   └─ 每个唯一 finding 由独立验证 Agent 确认/驳回
  │
  ├─ Step 3: 输出 Summary + Findings + Verdict
  │
  ├─ Step 4: 可选发布 PR inline comments + review verdict
  │
  └─ Step 5: 恢复工作区环境
```

**优势：**
- 并行覆盖多个维度
- 已有独立验证步骤，可降低误报
- 支持 PR inline 评论和最终 verdict

**限制：**
- 主要是 **skill prompt 驱动**，不是专门的 review runtime
- 去重、验证、评论发布虽已定义，但缺少更强的**状态管理、失败恢复、持久化与观测性**

**源码：**
- `源码: ../qwen-code/packages/core/src/skills/bundled/review/SKILL.md`

## 2.3 架构性质：更像“prompt 编排”，而不是专用 review engine

这一点很关键。

Qwen Code 当前的 skill 机制，本质是将 `SKILL.md` 内容作为 prompt 注入模型；`/review` 并没有一个独立的 TypeScript review orchestrator。

这意味着：

- 调整审查步骤、输出格式、提示词约束，很多情况下**只改 `SKILL.md` 即可**
- 但若目标是后台任务、增量缓存、结果持久化、autofix pipeline，则**不能只靠 prompt 完成**

`SkillConfig.allowedTools` 在当前 skill v1 中主要是说明性元数据，而不是强制权限边界。

**源码：**
- `源码: ../qwen-code/packages/core/src/tools/skill.ts`
- `源码: ../qwen-code/packages/core/src/skills/types.ts`
- `源码: ../qwen-code/packages/core/src/skills/skill-manager.ts`
- `源码: ../qwen-code/packages/cli/src/services/BundledSkillLoader.ts`

> **结论**：
> “P0-P1 只改 `SKILL.md` 不改代码”只对 prompt 级改进成立；一旦涉及后台化、持久化、缓存、autofix、幂等发布等产品能力，就需要代码改动。

## 三、为什么 GitHub PR 里的 Copilot Code Review 体感更好

这一部分需要和 Copilot CLI 本地证据、GitHub 平台官方文档严格区分。

## 3.1 PR review 是强约束任务，比 chat 更容易做准

PR review 场景天然比通用聊天更适合高质量输出，因为它的输入输出都被强约束：

- 输入不是“整个仓库”，而是**这次 diff**
- 额外上下文往往是 **base branch、PR title、PR body、相关评论**
- 输出不是长篇解释，而是**具体文件/具体行的 review comment**
- 目标不是开放式问答，而是**发现高风险问题**

GitHub 官方文档明确提到，Copilot Code Review 在生成反馈时会结合**代码变更和额外上下文**，包括 PR title 与 body。

**官方文档：**
- `https://docs.github.com/en/copilot/responsible-use/code-review`
- `https://docs.github.com/en/copilot/using-github-copilot/code-review/using-copilot-code-review`

## 3.2 GitHub 平台拥有本地 CLI 不具备的平台级上下文

GitHub PR 页面上的 AI review 不只是“看 diff”，而是运行在更完整的平台工作流之上：

- Pull Request 的 title / body / timeline discussion
- Reviewers、reviews、comments、checks、merge gate
- Code scanning alerts 与 annotations
- Pull request conversation 中的历史讨论
- 与 repository / issues / 历史 PR 的平台级关联

GitHub Docs 明确说明：

- Copilot Code Review 可以作为 **PR review** 出现在 GitHub 网站中
- code scanning alerts 会进入 PR 的 **checks / annotations / conversation / review** 流程
- cloud agent 运行在 **GitHub Actions 驱动的 ephemeral environment** 中，并可利用 issues、历史 PR 等上下文

**官方文档：**
- `https://docs.github.com/en/copilot/using-github-copilot/code-review/using-copilot-code-review`
- `https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/triaging-code-scanning-alerts-in-pull-requests`
- `https://docs.github.com/en/copilot/concepts/about-copilot-coding-agent`

## 3.3 Copilot CLI 本地证据能证明什么，不能证明什么

从本地二进制分析看，Copilot CLI **可以可靠证明**以下几点：

- 存在内置 `code-review` agent，与 `/review` 命令对应
- 该 agent 以**极高信噪比**为目标，只输出真正重要的问题
- 允许读取 git diff、周边代码，并在必要时**build / run tests** 做验证
- 具备多个 GitHub PR 读取工具：PR、comments、reviews、files、status 等
- 支持 `.github/copilot-instructions.md` 这类项目级指令文件

但仅凭 CLI 二进制/本地文档，**不能直接证明**以下平台级结论：

- 自动在 GitHub PR 页面发起/发布 inline review comments
- 增量复审、新 commit 自动触发
- 跨 PR 持久记忆
- Copilot Code Review 主链路与 CodeQL “深度集成”的全部实现细节
- 通用意义上的 Autofix 一键修复

因此，文档中应避免把“Copilot CLI 能力”和“GitHub Copilot Code Review 平台能力”混为一谈。

**本地证据：**
- `源码: docs/tools/copilot-cli/EVIDENCE.md`
- `源码: docs/tools/copilot-cli/02-commands.md`
- `源码: docs/tools/copilot-cli/03-architecture.md`

## 3.4 高 precision 优先，是 Copilot review 体验好的关键

Copilot CLI 的 `code-review` agent prompt 反复强调：

- 只报真正重要的问题
- 不确定就不要说
- 风格、格式、命名、轻度重构机会都不要提
- 能验证时尽量验证

这与很多本地 Agent 的“尽量多提建议”不同。PR review 场景里，**少量高价值评论**往往比大量泛化建议更有用。

这也是 GitHub 文档中“Copilot 只提交 Comment，不 Approve/Request changes”的产品定位基础：AI review 作为高价值补充，而不是代替人工 gatekeeper。

**本地证据与官方文档：**
- `源码: docs/tools/copilot-cli/EVIDENCE.md`
- `https://docs.github.com/en/copilot/using-github-copilot/code-review/using-copilot-code-review`

## 四、Qwen Code 与现有仓库文档之间的差异

当前仓库内若干文档对 Qwen `/review` 的描述已经部分过时，完善本文档时需要顺带修正判断边界。

## 4.1 `review-command.md` 中“无验证步骤”的说法已过时

当前 Qwen Code `SKILL.md` 已包含：

- Step 2.5：去重
- 对每个唯一 finding 启动**独立验证 Agent**
- 验证失败或不确定时倾向 reject

因此，Qwen Code 当前并非“4 个 Agent 直接汇总，无验证步骤”，而是已经引入了**LLM-based independent verification**。

**证据：**
- `源码: ../qwen-code/packages/core/src/skills/bundled/review/SKILL.md`
- `源码: docs/comparison/review-command.md`

## 4.2 “GitHub Code Review 缺失”的说法需要细化

如果把“GitHub Code Review”理解为：

- 本地 CLI 审查 PR
- 发布 inline comments
- 发布整体 review verdict

那么 Qwen Code 已经部分具备。

如果把它理解为：

- 平台原生、事件驱动、持续运行、带状态管理的托管式 PR review 服务

那么 Qwen Code 仍明显不足。

因此，后续文档建议使用更细分表述：

- **已具备**：本地 PR 审查、inline 评论、overall review verdict
- **仍缺失**：后台任务化、增量复审、持久化状态、强幂等评论发布、平台级托管工作流

**证据：**
- `源码: ../qwen-code/packages/core/src/skills/bundled/review/SKILL.md`
- `源码: docs/comparison/qwen-code-improvement-report.md`

## 五、与 Copilot / Claude / Gemini 的关键差距

## 5.1 验证机制：Qwen 已有 LLM 验证，但执行验证仍偏弱

当前几类产品的验证哲学可以概括为：

| 工具 | 主要验证方式 | 特点 |
|------|-------------|------|
| Qwen Code | 独立 verification agent | 降低误报，但仍主要依赖 LLM 推理 |
| Claude Code | 多阶段 agent orchestration + verification | 更强调多层编排与再确认 |
| Copilot CLI | build/test/execution-based verification | 对编译错误、测试失败更确定 |
| Gemini CLI | 后台工作树 + build/test 闭环 | 审查与验证更接近异步 CI |

Qwen Code 当前最明显的短板不是“完全没有验证”，而是：

- 缺少系统性 **execution-based verification**
- 构建/测试/lint 尚未成为 `/review` 主流程中的一等公民

**证据：**
- `源码: ../qwen-code/packages/core/src/skills/bundled/review/SKILL.md`
- `源码: docs/tools/copilot-cli/EVIDENCE.md`
- `源码: docs/comparison/review-command.md`

## 5.2 跨文件影响分析仍不够制度化

Qwen 当前 review 虽可借助搜索工具自行扩展上下文，但还没有把“symbol / import / call-site 追踪”固化为审查主流程的一部分。

对于这类变更，容易遗漏：

- 导出 API 签名变化
- 返回值/异常语义变化
- 参数数量/类型变化
- 上游/下游调用方兼容性

相比之下，GitHub 平台上的 PR review 场景更容易围绕变更做上下文扩展；Copilot CLI 也明确鼓励读取周边代码和验证 concern 是否已在别处处理。

## 5.3 项目规则注入与团队审查规范不足

Copilot 体系中，`.github/copilot-instructions.md` 是明确存在的项目级指令入口；Qwen Code 当前虽有 `QWEN.md` 与 skill 体系，但 `/review` 尚未把项目自定义 review 规则系统化纳入主流程。

这会影响不同项目的审查适配度，例如：

- React hooks 规则
- Go error handling 规范
- monorepo 目录所有权约定
- API stability policy

## 5.4 同步阻塞、缺乏后台 job 化能力

Qwen Code 已具备：

- agent 并行能力
- background shell 能力

但这些底层能力尚未上升为 `/review` 的正式产品能力。当前缺少：

- review job id
- queued/running/completed 状态
- 异步结果回传
- 中断后恢复
- `status/history/resume/cancel` 等查询接口

**源码：**
- `源码: ../qwen-code/packages/core/src/tools/agent.ts`
- `源码: ../qwen-code/packages/core/src/tools/shell.ts`
- `源码: ../qwen-code/packages/core/src/services/shellExecutionService.ts`

## 5.5 持久化、增量缓存、评论幂等不足

目前 `/review` 的结果主要停留在当前会话中，难以复用为：

- 跨会话的 review 历史
- 针对 PR 的增量复审缓存
- 已发布评论的去重与幂等控制

而 GitHub PR 平台天然具备 conversation、reviews、checks、comments 的历史载体；Copilot Code Review 也具备手动/自动 review 的平台入口。

## 六、Qwen Code 已有的可复用基础设施

这些改进并非完全从零开始，Qwen Code 已有多项底座能力可复用。

## 6.1 子代理与并行执行基础已存在

Qwen Code 已提供：

- `agent` 工具
- builtin `Explore` 只读子代理
- headless subagent 执行路径
- 单消息内并行启动多个 agent 的能力

这为 review 的多代理拆分、验证代理、只读探索代理提供了现成基础。

**源码：**
- `源码: ../qwen-code/packages/core/src/tools/agent.ts`
- `源码: ../qwen-code/packages/core/src/subagents/builtin-agents.ts`
- `源码: ../qwen-code/packages/core/src/subagents/subagent-manager.ts`
- `源码: ../qwen-code/packages/core/src/agents/runtime/agent-headless.ts`

## 6.2 Shell 执行能力足以支撑 build/test/lint 链路

Qwen Code 已有成熟的 shell 执行能力，支持：

- 前台/后台命令
- 持久 shell session
- 进程组管理

这意味着 execution-based verification 在技术上并非空白，而是**尚未被 `/review` 主流程制度化**。

**源码：**
- `源码: ../qwen-code/packages/core/src/tools/shell.ts`
- `源码: ../qwen-code/packages/core/src/services/shellExecutionService.ts`

## 6.3 已存在 GitHub Actions 集成入口

Qwen Code 的 `/setup-github` 已包含 `pr-review/qwen-review.yml` 相关 workflow 分发逻辑。

这说明项目已经具备从“本地 review”走向“GitHub workflow 集成”的方向性基础，只是 `/review` 本身尚未成为完整托管式审查服务。

**源码：**
- `源码: ../qwen-code/packages/cli/src/ui/commands/setupGithubCommand.ts`

## 七、改进建议（按优先级分层）

## 7.1 P0：先校正文档与能力边界

**目标**：先把“当前已实现什么、未实现什么”说清楚，避免后续路线图建立在错误前提上。

建议：

1. 将 `/review` 从“缺失能力”改为“已具备基础能力，但成熟度不足”
2. 将 `review-command.md` 中“Qwen 无验证步骤”的描述更新为“已有独立验证 Agent”
3. 在相关文档中明确区分：
   - **Copilot CLI 本地能力**
   - **GitHub Copilot Code Review 平台能力**

**理由**：文档边界不清，会直接影响产品路线判断。

## 7.2 P1：把确定性分析与 execution-based verification 纳入 `/review` 主流程

**问题**：当前 Qwen review 仍过度依赖 LLM 推理来发现部分本可确定性发现的问题。

**建议**：在 Step 2 前加入 Step 1.5：

- 检测并运行项目已有的 lint / typecheck / build / test
- 仅针对 diff 相关文件或最小必要范围运行
- 将确定性输出作为“已确认问题”直接注入 findings
- 对失败日志做简洁摘要，避免大段原样灌入 prompt

**优先顺序建议：**
1. linter / typecheck
2. build
3. tests
4. 必要时运行特定 smoke checks

**预期收益**：
- 降低 LLM 浪费
- 减少“其实编不过/测不过”的低级漏报
- 向 Copilot CLI 的 execution-based verification 靠拢

## 7.3 P1：将跨文件影响分析升级为明确流程

建议在每个审查 Agent 的指令中显式要求：

- 对被修改的导出函数/类/接口做调用方搜索
- 检查返回值与异常语义变化
- 检查 breaking API changes
- 检查 import/调用链上的兼容性问题

进一步的中期方向可以考虑：

- AST-aware symbol lookup
- import / call graph 扩展
- 与历史类似变更的检索

## 7.4 P1：支持项目级审查规则注入

建议 `/review` 在主流程开始前按优先级尝试加载：

1. `.qwen/review-rules.md`
2. `.github/copilot-instructions.md` 或 `copilot-instructions.md`
3. `QWEN.md` 中的 `## Code Review` 章节

这样既兼容 Qwen 自身配置，也兼容已有 Copilot 项目规范，降低迁移成本。

## 7.5 P2：结果聚合、置信度分层与“Needs Human Review”区域

建议将当前二元验证结果扩展为：

- `confirmed (high confidence)`
- `confirmed (low confidence)`
- `rejected`

并在输出中区分：

- **Confirmed Findings**
- **Needs Human Review**

这有助于保持高 precision，同时不给模型“非黑即白”的过强压力。

## 7.6 P2：后台审查、持久化与增量缓存

这部分已超出单纯改 `SKILL.md` 的范围，需要代码改动。

建议新增 review-specific 基础设施：

- review job schema：`queued/running/completed/failed/cancelled`
- job id + `status/history/resume/cancel`
- findings/result store
- 按 PR/commit/diff 的 cache key
- 已发布评论的去重与幂等逻辑

**关键点**：
- 后台 shell 能力是已有底座，但“后台化 review 产品能力”仍需专门 orchestrator
- 持久化可以借鉴 todo/session/log 现有模式，但 review 数据结构需单独设计

## 7.7 P2：Autofix 要区分“建议修复”与“产品级自动修复”

建议分两个阶段：

### 阶段 A：Suggested fix
- 对部分 confirmed findings 输出结构化修复建议
- 不直接修改文件

### 阶段 B：Autofix pipeline
- 用户确认后应用 patch
- 自动执行 lint/test/format
- 失败时可回滚
- 生成 fix commit 或 fixup commit

当前 Qwen 已有写文件/编辑文件能力，但缺少 review finding 到 patch application 的正式产品链路，因此这一项需要代码改动，不能只靠 prompt。

## 八、推荐的实现优先级

| 优先级 | 改进 | 是否可仅改 `SKILL.md` | 说明 |
|--------|------|----------------------|------|
| **P0** | 校正文档边界 | 是 | 先纠正现状认知 |
| **P1** | linter/typecheck 注入 | 是 | 最低成本提升确定性 |
| **P1** | build/test 纳入主流程 | 基本是 | 依赖项目命令探测与 prompt 编排 |
| **P1** | 跨文件影响分析流程化 | 是 | 先从 prompt 规范开始 |
| **P1** | 项目规则注入 | 是 | 与 Copilot 指令兼容性高 |
| **P2** | 评论聚合 + 置信度分层 | 大部分是 | 可先 prompt 化，后续再结构化 |
| **P2** | 后台审查 | 否 | 需要 job/state/orchestrator |
| **P2** | 结果持久化 | 否 | 需要 result store 与查询入口 |
| **P2** | 增量缓存 | 否 | 需要 cache schema 与失效策略 |
| **P2** | Autofix pipeline | 否 | 需要 patch/test/rollback 流程 |

## 九、对 Qwen Code 的实际准备建议

如果目标是“为改进 Qwen Code 做准备”，最现实的推进顺序是：

### 第一步：修正认知与文档
- 更新对 `/review` 当前能力的描述
- 明确本地 CLI 与 GitHub 平台能力边界

### 第二步：先做不改架构的大收益项
- linter/typecheck/build/test
- 跨文件影响分析
- 项目规则注入
- 评论聚合与置信度分层

### 第三步：再做产品化能力
- 后台 review jobs
- 持久化 history
- 增量复审缓存
- review-specific autofix

> **关键判断**：
> Qwen Code 当前并不缺 `/review`，缺的是把现有 skill-driven review 从“可用 prompt 工作流”升级为“更确定、更可追踪、更可持续复用的产品能力”。

## 参考来源

### Qwen Code 本地源码
- `源码: ../qwen-code/packages/core/src/skills/bundled/review/SKILL.md`
- `源码: ../qwen-code/packages/cli/src/services/BundledSkillLoader.ts`
- `源码: ../qwen-code/packages/core/src/tools/skill.ts`
- `源码: ../qwen-code/packages/core/src/skills/types.ts`
- `源码: ../qwen-code/packages/core/src/tools/agent.ts`
- `源码: ../qwen-code/packages/core/src/subagents/builtin-agents.ts`
- `源码: ../qwen-code/packages/core/src/subagents/subagent-manager.ts`
- `源码: ../qwen-code/packages/core/src/agents/runtime/agent-headless.ts`
- `源码: ../qwen-code/packages/core/src/tools/shell.ts`
- `源码: ../qwen-code/packages/core/src/services/shellExecutionService.ts`
- `源码: ../qwen-code/packages/cli/src/ui/commands/setupGithubCommand.ts`

### 当前仓库文档
- `源码: docs/tools/qwen-code/02-commands.md`
- `源码: docs/tools/copilot-cli/02-commands.md`
- `源码: docs/tools/copilot-cli/03-architecture.md`
- `源码: docs/tools/copilot-cli/EVIDENCE.md`
- `源码: docs/comparison/review-command.md`
- `源码: docs/comparison/qwen-code-improvement-report.md`

### GitHub 官方文档
- `https://docs.github.com/en/copilot/responsible-use/code-review`
- `https://docs.github.com/en/copilot/using-github-copilot/code-review/using-copilot-code-review`
- `https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/triaging-code-scanning-alerts-in-pull-requests`
- `https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/about-autofix-for-codeql-code-scanning`
- `https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning-with-codeql`
- `https://docs.github.com/en/copilot/concepts/about-copilot-coding-agent`
