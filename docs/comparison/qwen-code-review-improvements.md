# Qwen Code /review 功能改进建议

> 基于 Qwen Code、Gemini CLI、Claude Code、Copilot Code Review 四方源码/架构对比，提出 Qwen Code `/review` 功能的改进方向。
>
> 最后更新：2026-04-06
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md) | [/review 命令对比](./review-command.md)

## 零、Copilot Code Review 为什么效果最好——完整证据链

> 本节补充全行业最关键的量化数据和源码证据，为改进方向提供锚点。

### 0.1 生产规模数据：6000 万次审查的飞轮效应

GitHub 截至 2026 年 3 月的官方数据（来源：[60 Million Copilot Code Reviews](https://github.blog/ai-and-ml/github-copilot/60-million-copilot-code-reviews-and-counting/)）：

| 指标 | 数值 | 含义 |
|------|------|------|
| 累计审查量 | **6000 万+** | 占 GitHub 平台全部代码审查量的 **20% 以上** |
| 采用组织数 | **12,000+** | 已在仓库级默认自动启用 CCR |
| 无评论比例 | **29%** | Agent 选择保持沉默，零评论返回 |
| 有行动反馈比例 | **71%**（= 100% - 29%） | 产生可操作的审查意见 |
| 平均每次审查评论数 | **~5.1 条** | 评论量少但质量高 |
| 用户反馈增长 | 自 CCR 正式发布以来使用量增长 **10 倍** | 采用率持续攀升 |
| WEX 客户交付提升 | 代码交付量提升约 **30%** | 企业侧实际效果数据 |

**核心洞察**：6000 万次审查 + 每次审查都有 👍/👎 反馈机制（👎 需提供原因）形成了持续改进的数据飞轮。这是任何 CLI 工具都无法复制的**生产规模反馈闭环**。

### 0.2 Agentic 架构升级效果：+8.1% 正面反馈

2026 年 3 月 5 日，GitHub 将 Copilot Code Review 从基于 prompt 的架构重构为 **agentic tool-calling 架构**（来源：[GitHub Changelog](https://github.blog/changelog/2026-03-05-copilot-code-review-now-runs-on-an-agentic-architecture/)）。升级后：

- 正面反馈增加 **8.1%**
- 采用更高级推理模型后，正面反馈率再提升 **6%**（审查延迟同步增加 16%）

**Agentic 架构的五个核心改进**：

| 改进 | 旧架构 | 新架构 |
|------|--------|--------|
| 上下文收集 | 被动接收 diff | Agent **主动**搜索代码、读取目录结构、追踪引用 |
| 问题捕获 | 读完 diff 再总结 | **边读边捕获**，实时记录问题，避免早期发现被遗忘 |
| 跨 PR 记忆 | 无 | 识别出的代码模式**存储并在后续审查中复用** |
| 规划策略 | 无 | 针对超长/复杂 PR 提前生成**审查路径图**，防止上下文丢失 |
| 关联分析 | 仅看 diff | 自动读取关联 Issue 与 PR，发现偏离目标的隐蔽缺口 |

### 0.3 Copilot CLI code-review agent 完整 prompt 源码

从 Copilot CLI npm 包 v0.0.403 反编译提取（源码：`definitions/code-review.agent.yaml`，完整 94 行 YAML，[EVIDENCE.md](../tools/copilot-cli/EVIDENCE.md)）：

**8 个审查维度（白名单）：**
1. Bugs and logic errors
2. Security vulnerabilities
3. Race conditions or concurrency issues
4. Memory leaks or resource management problems
5. Missing error handling that could cause crashes
6. Incorrect assumptions about data or state
7. Breaking changes to public APIs
8. Performance issues with measurable impact

**8 个排除维度（黑名单）：**
1. Style, formatting, or naming conventions
2. Grammar or spelling in comments/strings
3. "Consider doing X" suggestions that aren't bugs
4. Minor refactoring opportunities
5. Code organization preferences
6. Missing documentation or comments
7. "Best practices" that don't prevent actual problems
8. Anything you're not confident is a real issue

**关键 prompt 原文（逐字引用）：**

```
Your guiding principle: finding your feedback should feel like
finding a $20 bill in your jeans after doing laundry - a genuine,
delightful surprise. Not noise to wade through.
```

```
If you're unsure whether something is a problem, DO NOT MENTION IT.
```

```
CRITICAL: You Must NEVER Modify Code.
You have access to all tools for investigation purposes only:
- Use `bash` to run git commands, build, run tests, execute code
- Use `view` to read files and understand context
- Use `grep` and `glob` to find related code
- Do NOT use `edit` or `create` to change files
```

```
Silence is better than noise. Every comment you make should be
worth the reader's time.
```

**设计哲学**："**$20 bill in jeans**"——每条反馈都应该是惊喜，不是噪音。这是已知 CLI Agent 中**少见的同时禁止修改代码但允许运行代码**的实现：可以编译和测试，但不能修改。

### 0.4 学术界：LLM 代码审查的可靠性边界

| 研究 | 关键发现 |
|------|---------|
| [Evaluating LLMs for Code Review](https://arxiv.org/abs/2505.20206)（2025） | 正确性判定准确率：GPT-4o **68.5%**，Gemini 2.0 Flash **63.9%**。代码修复成功率：GPT-4o 67.8%，Gemini 54.3%。结论："LLMs would be **unreliable in a fully automated code review environment**."建议采用 Human-in-the-loop 流程 |
| [Rethinking Code Review with LLM](https://arxiv.org/html/2505.16339v1)（WirelessCar，2025） | 开发者反馈："If they're not good enough, you stop reading them...you miss the real issues because you start ignoring the feedback."——**低质量 AI 反馈反而降低整体审查质量**（狼来了效应） |
| [CORE: Resolving Code Quality Issues](https://dl.acm.org/doi/10.1145/3643762)（ACM） | 二阶段 proposer+ranker 模式减少 **25.8%** 假阳性——与 Claude Code 的多 Agent 验证异曲同工 |

**行业共识**：LLM 审查应定位为**辅助咨询**而非**自动化质量关卡**。真正的质量关卡应该是测试套件和 linter。

### 0.5 五层信任架构（来源：[Latent Space](https://www.latent.space/p/reviews-dead)）

| 层 | 机制 | 说明 |
|---|------|------|
| 1 | 竞争 Agent | 多个 Agent 解决同一问题，按测试通过率和 diff 大小排名 |
| 2 | 确定性护栏 | 自定义 linter、类型检查、契约验证——客观通过/失败 |
| 3 | BDD 验收标准 | 人类定义的行为规格 |
| 4 | 权限系统 | 按文件/任务限制 Agent 范围 |
| 5 | 对抗验证 | 编码 Agent + 验证 Agent + 红队/模糊测试 Agent |

**核心转变**：将人类监督从**下游代码阅读**移到**上游规格编写**。

---

## 一、当前 Qwen Code /review 的架构

```
/review [PR号|文件路径] [--comment]
  │
  ├─ Step 1: 确定审查范围
  │   ├─ 无参数 → git diff (未提交变更)
  │   ├─ PR 号 → gh pr checkout + gh pr view
  │   └─ 文件路径 → git diff HEAD -- <file>
  │
  ├─ Step 2: 4 个并行审查 Agent
  │   ├─ Agent 1: 正确性 & 安全
  │   ├─ Agent 2: 代码质量
  │   ├─ Agent 3: 性能 & 效率
  │   └─ Agent 4: 无方向审计
  │
  ├─ Step 2.5: 去重 + 独立验证
  │   ├─ 合并重复发现
  │   └─ 每个发现由独立 Agent 确认/驳回
  │
  ├─ Step 3: 输出结果（Critical/Suggestion/Nice to have）
  │
  └─ Step 4 (可选): --comment 时发布 PR inline 评论
```

**优势**：4 Agent 并行 + 独立验证 = 覆盖面广 + 低误报率。

**可用工具**：`agent`、`run_shell_command`、`grep_search`、`read_file`、`write_file`、`glob`。

源码：`packages/core/src/skills/bundled/review/SKILL.md`（261 行）

## 二、Copilot Code Review 为什么效果好——量化证据

### 0. 生产规模数据

GitHub 截至 2026-03 的官方数据（来源：[60 Million Copilot Code Reviews](https://github.blog/ai-and-ml/github-copilot/60-million-copilot-code-reviews-and-counting/)）：

| 指标 | 数值 |
|------|------|
| 累计审查量 | 6000 万+（占 GitHub 全部 code review 的 20%+） |
| 采用组织数 | 12,000+ |
| 无评论比例 | 29%（Agent 选择保持沉默） |
| 有行动反馈比例 | 71% |
| 平均评论数 | ~5.1 条/次 |
| Agentic 架构升级效果 | 正面反馈 +8.1%（2026-03-05） |

### 0.1 Copilot CLI code-review prompt 设计哲学

从 Copilot CLI 二进制反编译提取的 `code-review.agent.yaml`（94 行，见 `docs/tools/copilot-cli/EVIDENCE.md`）中的关键设计原则：

> *"Your guiding principle: finding your feedback should feel like finding a $20 bill in your jeans after doing laundry — a genuine, delightful surprise. Not noise to wade through."*

> *"Silence is better than noise. Every comment you make should be worth the reader's time."*

> *"If you're unsure whether something is a problem, DO NOT MENTION IT."*

**8 个审查维度（白名单）**：Bugs、Security、Race conditions、Memory leaks、Missing error handling、Incorrect assumptions、Breaking API changes、Performance issues

**8 个排除维度（黑名单）**：Style/formatting、Grammar、"Consider doing X"、Minor refactoring、Code organization、Missing docs、"Best practices" without real problems、Anything uncertain

**独特设计**：允许 `bash` 运行 build/test 验证，允许 `view`/`grep`/`glob` 读取代码，但 **禁止 `edit`/`create` 修改代码**——只读验证，不碰源码。

### 0.2 Claude Code /ultrareview 云端多 Agent 架构

Claude Code 除本地 `/review`（30 行 prompt）外，还有 `/ultrareview`——远程 CCR 云端审查：

- **Fleet 规模**：默认 **5 个并行 Agent**（可配置 5-20，源码: `BUGHUNTER_FLEET_SIZE`）
- **时长控制**：总墙钟 10-25 分钟（`BUGHUNTER_MAX_DURATION`）
- **三阶段流水线**：finding → verifying → synthesizing
- **付费门控**：免费层有次数限制，Enterprise 无限制

源码: `commands/review/reviewRemote.ts`（316 行）

### 0.3 为什么 GitHub PR 里的 Copilot 体感更好

Copilot Code Review 效果好，核心不只是模型能力，而是**任务约束 + 平台优势 + 确定性工具 + 高 precision 策略**四者叠加。

### 1. PR review 是强约束任务

PR review 天然比通用聊天更适合高质量输出，因为输入输出都被强约束：

- 输入不是"整个仓库"，而是**这次 diff + base branch + PR 元数据**
- 输出不是长篇解释，而是**具体文件/具体行的 review comment**
- 目标不是开放式问答，而是**发现高风险问题**

这意味着 Qwen Code 的 `/review` 天然也具备做好的条件——diff 是明确的，PR 元数据可以通过 `gh pr view` 获取。

### 2. GitHub 平台拥有 CLI 不具备的原生上下文

GitHub PR 页面上的 AI review 运行在更完整的平台工作流之上：PR title/body、评论历史、checks、code scanning alerts、merge gate 在同一个产品面中协同。CLI 虽然可以通过 `gh` 命令获取大部分信息，但缺少事件驱动（新 commit 自动触发）和持久化状态管理。

### 3. CLI 能力 vs 平台能力需要区分

从 Copilot CLI 二进制分析（见 `docs/tools/copilot-cli/EVIDENCE.md`）可确认 CLI 端存在 `code-review` agent，具备读取 diff、周边代码、build/test 验证的能力。但以下能力属于**平台级**，不在 CLI 中：

- 自动在 PR 页面发起 inline review comments
- 增量复审（新 commit 自动触发）
- 跨 PR 持久记忆
- CodeQL 深度集成的全部实现细节

Qwen Code 的改进方向应分为两层：
- **Prompt 层增强**（改 SKILL.md）：确定性分析、构建/测试、跨文件追踪、规则注入、评论聚合
- **产品层增强**（改代码）：后台审查、结果持久化、增量缓存、Autofix pipeline

### 4. 高 precision 优先："沉默优于噪声"

Copilot CLI 的 `code-review` agent prompt 反复强调：只报真正重要的问题、不确定就不说、风格/格式/命名不提。PR review 场景里，**少量高价值评论**比大量泛化建议更有用。Qwen Code 的 SKILL.md 排除标准也有类似设计（"lean toward rejecting"），方向一致。

**生产数据验证**：29% 的 Copilot 审查返回零评论——这是设计使然。**"Silence is better than noise"** 是 GitHub 的核心设计理念，宁可不评论，也不产生噪声。这避免了学术界发现的"狼来了效应"：低质量反馈导致开发者停止阅读所有 AI 评论，从而错过真正的问题。

### 5. 用户反馈闭环：👍/👎 驱动的数据飞轮

Copilot Code Review 的每个评论都有 👍/👎 反馈机制，点击 👎 时需提供原因（可附评语）。这些反馈直接用于：
1. 迭代建议质量与排序
2. 验证 Agent 标记的缺陷是否在代码合并前被开发者实际修复
3. 模型训练的奖励信号

6000 万次审查 × 平均 5.1 条评论 × 每次都有反馈 = 持续改进的数据飞轮。这是任何 CLI 工具都无法复制的**生产规模反馈闭环**。

## 三、与业界实现的差距

### 竞品架构深度剖析

1. **Copilot Code Review（平台级）**：
   - **Agentic 工作流**：从 prompt 架构重构为 agentic tool-calling 架构（2026-03-05），Agent 主动收集仓库上下文（代码、目录结构、引用）来理解变更如何融入整体架构。升级后正面反馈 +8.1%。
   - **边读边捕获**：阅读代码时实时记录问题，避免传统"读完再总结"导致的早期发现遗忘。
   - **跨 PR 记忆**：识别出的代码模式可存储并在后续审查中复用，打破单次审查孤立性。
   - **显式规划策略**：针对超长/复杂 PR 提前生成审查路径图，防止上下文丢失。
   - **CodeQL 深度集成**：将 LLM 概率推理与 CodeQL 确定性语义/安全分析融合。CodeQL 提供安全漏洞和数据流的 Ground Truth，LLM 负责解释并过滤噪音，极大降低幻觉。
   - **Autofix**：提供一键修复建议，并通过 `copilot-instructions.md` 注入团队审查规范。
   - **用户反馈闭环**：每个评论 👍/👎，👎 需提供原因，直接用于模型迭代。

2. **Claude Code（`/review` + `/ultrareview` 双层架构）**：
   - **`/review`（本地）**：采用 Prompt 包装模式（`LOCAL_REVIEW_PROMPT`），用 `gh pr diff` 获取差异，给出单次全面审查。拥有 tools: *（所有工具），模型可自主探索代码。
   - **`/ultrareview`（云端多 Agent 编排）**：
     - **Fleet 规模**：默认 **5 个并行 Agent**（可配置 5-20），每个 Agent 独立寻找 Bug。
     - **三阶段流水线**：`finding`（发现）→ `verifying`（验证）→ `synthesizing`（去重合成）。
     - **验证过滤**：每个发现的 Bug 由独立验证 Agent 确认，置信度 < 8 的被过滤。17+ 类误报排除规则。
     - **Live 进度**：每 ~10 秒推送 `<remote-review-progress>` 标签，包含 bugs_found / bugs_verified / bugs_refuted 计数。
     - **时长控制**：总墙钟时间上限 22-27 分钟，单 Agent 超时 10-30 分钟。
     - **计费门控**：免费层有次数限制，Enterprise 用户无限制，用完后需确认 Extra Usage 计费（最低 $10 余额）。
     - 源码：`commands/review.ts`、`commands/review/reviewRemote.ts`、`commands/review/ultrareviewCommand.tsx`（Claude Code 本地源码 `/root/git/claude-code-leaked/`）

3. **Gemini CLI（`async-pr-review` Skill）**：
   - **异步模式**：通过 `is_background: true` 在后台分离执行，用 `gemini -p`（headless 模式）实现纯后台 LLM 推理。
   - **5 并行后台任务**（源码：`.gemini/skills/async-pr-review/scripts/async-review.sh`）：
     | 任务 | 内容 |
     |------|------|
     | `[1/5] pr-diff` | `gh pr diff` 捕获差异 |
     | `[2/5] build-and-lint` | `npm ci && npm run build && npm run lint:ci && npm run typecheck` |
     | `[3/5] review` | `gemini --policy policy.toml -p "/review-frontend <pr_number>"`（headless） |
     | `[4/5] npm-test` | 等待 build-and-lint 完成后，`gh pr checks` + 选择性本地测试 |
     | `[5/5] test-execution` | headless Gemini 手动操作变更代码，验证交互行为 |
   - **Ephemeral Worktree**：在 `.gemini/tmp/async-reviews/pr-<number>/worktree` 创建临时工作树，不污染主工作区。
   - **codebase_investigator 子 Agent**：专用的只读深度调查 Agent（Flash 模型，3 分钟限时），构建完整的代码调用链心智模型，输出结构化 JSON 报告。
   - **review-duplication Skill**：专门的重复代码检测技能，使用 `codebase_investigator` 深度搜索项目中是否已存在相同逻辑。
   - **闭环验证**：所有任务完成后，headless Gemini 合成 `final-assessment.md`，整合测试日志、lint 结果、LLM Review。
   - 源码：`.gemini/skills/async-pr-review/`（Gemini CLI 本地源码 `/root/git/gemini-cli/`）

4. **Qwen Code（`/review` Skill）**：
   - **4 Agent 并行维度**：正确性&安全、代码质量、性能&效率、无方向审计。
   - **独立验证**：每个 finding 由独立 Agent 确认/驳回（竞品中少见）。
   - **排除标准**：明确声明 linter/typecheck 能捕获的问题不应由 LLM 报告（与 P0 改进形成闭环）。
   - 源码：`packages/core/src/skills/bundled/review/SKILL.md`（261 行，Qwen Code 本地源码 `/root/git/qwen-code/`）

### 对比矩阵

| 能力 | Qwen Code | Copilot Code Review | Claude Code | Gemini CLI |
|------|-----------|-------------------|-------------|-----------|
| 并行审查 Agent | ✓ 4 个并行 | ✓ Agentic（单 agent 多工具）| ✓ 本地 1 个 + 云端 5 个（/ultrareview） | ✓ 5 个异步任务 + Headless |
| 独立验证 | ✓ 每个 finding 独立验证 | — | ✓ 验证 Agent（/ultrareview） | — |
| 确定性分析（linter/typecheck） | — | ✓ CodeQL + ESLint | — | ✓ 自动前置检查脚本 |
| 构建/测试执行 | — | ✓（Actions CI 集成） | — | ✓ 临时工作树中跑测试 |
| 跨文件影响分析 | — | ✓ 追踪 import 链与调用流 | ✓ tools: * 自主探索 | ✓ `codebase_investigator` |
| 重复代码检测 | — | — | — | ✓ `review-duplication` skill |
| 异步/后台审查 | — | ✓ GitHub Actions 后台 | ✓ /ultrareview 云端后台 | ✓ Native Background Shells |
| 项目规则自定义 | — | ✓ `copilot-instructions.md` | ✓ CLAUDE.md（全局指令，非 review 专用） | ✓ `.gemini/skills` 体系 |
| 评论聚合 | — | ✓ 同模式合并 | ✓ 去重合成（/ultrareview） | — |
| 自动修复（Autofix） | — | ✓ 基于分析结果一键修复 | — | — |
| 增量审查 | — | ✓ 新 commit 触发 | — | — |
| 跨 PR 记忆 | — | ✓ | — | — |
| Live 进度反馈 | — | — | ✓ 10 秒轮询进度 | ✓ .exit 文件状态跟踪 |
| 置信度过滤 | — | — | ✓ 置信度 < 8 过滤 | — |
| 用户反馈闭环 | — | ✓ 👍/👎 + 原因 | — | — |

### 关键差距

1. **只靠 LLM，无确定性分析**——linter/typecheck 能轻易捕捉的问题（类型错误、未使用变量），依赖 LLM 审查不仅显著更慢，而且学术界证实 LLM 正确性判定准确率仅 68.5%（GPT-4o），63.9%（Gemini 2.0 Flash），易产生幻觉和漏报
2. **不运行构建和测试**——无法验证代码是否编译通过或破坏了现有测试
3. **不分析跨文件影响**——Agent 的视野局限于 diff 变更本身，缺乏追踪被修改函数调用方的能力
4. **无项目自定义规则**——缺乏像 `copilot-instructions.md` 这样的项目级规范注入机制
5. **同步阻塞**——审查串行等待 LLM 响应，时间长达数分钟，期间完全阻塞 CLI
6. **缺少自动修复（Autofix）闭环**——仅提供文本建议，未利用工具能力直接生成或应用修复补丁
7. **评论缺乏聚合与验证结果的细粒度区分**——同一类问题被重复报告；验证 Agent 的结果仅有 confirmed/rejected 二元状态，缺少"疑似待确认"的灰度地带（human review needed）
8. **缺乏记忆与持久化**——再次运行 `/review` 会重复消耗 token 审查未变更的代码，终端关闭后审查结论丢失

## 四、Qwen Code 已有的可复用基础设施

改进并非从零开始，以下现有能力可直接复用：

| 现有能力 | 源码 | 可支撑的改进 |
|---------|------|------------|
| `agent` 工具 + 并行 Subagent | `packages/core/src/tools/agent.ts` | 多 Agent 审查（已用）、验证 Agent |
| `run_shell_command` + 后台 shell | `packages/core/src/tools/shell.ts` | linter/build/test 执行 |
| `grep_search` + `read_file` | `packages/core/src/tools/grep.ts` | 跨文件调用方搜索 |
| `write_file` | `packages/core/src/tools/write-file.ts` | Autofix 补丁、报告持久化 |
| `gh` CLI 集成 | SKILL.md Step 4 已使用 | PR inline 评论、review verdict |
| `/setup-github` workflow 分发 | `packages/cli/src/ui/commands/setupGithubCommand.ts` | 未来 GitHub Actions 集成入口 |

## 五、改进建议（按优先级）

### P0：集成确定性分析工具

**问题**：4 个 LLM Agent 审查"变量未使用"比 ESLint 显著更慢且不可靠（学术界证实 LLM 正确性判定准确率仅 68.5%）。

**改进**：在 Step 2 之前增加 Step 1.5——运行项目已有的 linter/typecheck，将结果注入 Agent 的上下文。

```markdown
## Step 1.5: 运行确定性分析

在 4 个 Agent 启动前，先运行项目的 linter 和 type checker。
将输出作为**已确认的问题**直接加入 findings，不需要 LLM 验证。

检测方式（按优先级尝试）：
1. 如果 package.json 有 `lint` script → `npm run lint -- --format json 2>&1 | head -200`
2. 如果有 `tsconfig.json` → `npx tsc --noEmit 2>&1 | head -100`
3. 如果有 `.eslintrc*` → `npx eslint --format json <changed-files>`
4. 如果有 `pyproject.toml` 或 `ruff.toml` → `ruff check <changed-files>`

仅对 diff 中涉及的文件运行（不全量 lint）。
```

**与排除标准的协同**：SKILL.md 排除标准已声明"Issues that a linter or type checker would catch automatically"不应由 LLM 报告。集成 linter 后两者形成闭环——linter 负责确定性问题，LLM 专注于 linter 无法捕获的逻辑/设计/安全问题，彼此不重复。

**实现成本**：SKILL.md 增加 ~30 行指令，无代码改动。

### P1：运行构建和测试

**问题**：代码看起来正确但编译不通过、测试失败——这是最重要的反馈，但当前完全缺失。

**改进**：在 Step 2 的 4 个 Agent 中增加第 5 个——Build & Test Agent。

```markdown
## Agent 5: 构建 & 测试验证

1. 运行构建命令（检测 package.json / Makefile / Cargo.toml）：
   - `npm run build 2>&1 | tail -50`
   - `make build 2>&1 | tail -50`  
   - `cargo build 2>&1 | tail -50`
2. 运行测试命令：
   - `npm test 2>&1 | tail -100`
   - `pytest 2>&1 | tail -100`
3. 如果构建/测试失败，分析错误原因并关联到 diff 中的具体变更。
4. 输出格式同其他 Agent（File/Issue/Impact/Suggested fix/Severity）。
   构建失败和测试失败一律标为 **Critical**。
```

**注意**：构建/测试失败是确定性事实，其 findings 应跳过 Step 2.5 的 LLM 验证，直接标为 confirmed Critical。

**实现成本**：SKILL.md 增加 ~20 行指令。

### P1：跨文件影响分析

**问题**：修改了 `auth.ts` 的接口签名，但 10 个调用方没更新——当前 Agent 只看 diff 不会发现。

**改进**：在审查 Agent 的指令中强调跨文件追踪。

```markdown
## 对每个被修改的函数/类/接口：

1. 用 `grep_search` 搜索所有调用方（搜索函数名/类名）
2. 检查调用方是否与修改后的签名兼容
3. 如果修改了导出的 API，检查是否有 breaking change
4. 重点关注：
   - 参数数量/类型变更
   - 返回类型变更
   - 异常行为变更（新增 throw、null 返回）
   - 删除的公开方法/属性
```

**注意**：grep_search 是语义搜索，更适合"找到相关代码片段"场景。如果需精确查找函数/变量的所有引用，建议同时用 `grep` 工具执行正则搜索（如 `grep -rn "functionName(" src/`），两者互补确保不漏。

**实现成本**：SKILL.md 在 Step 2 的 Agent 指令中增加 ~15 行。

### P1：项目自定义审查规则

**问题**：React 项目需要检查 hooks 规则，Go 项目需要检查 error 处理，但当前用统一 prompt。

**改进**：支持 `.qwen/review-rules.md` 项目级审查规则。

```markdown
## Step 0: 加载项目审查规则

如果项目根目录存在以下文件，读取并作为审查指导：
1. `.qwen/review-rules.md`（Qwen Code 原生）
2. `copilot-instructions.md`（兼容 Copilot）
3. `AGENTS.md` 中的 `## Code Review` 章节
4. `QWEN.md` 中的 `## Code Review` 章节

将规则内容注入每个审查 Agent 的提示中：
"除了通用审查标准，还需要遵守以下项目特定规则：
[规则内容]"
```

**实现成本**：SKILL.md 增加 ~10 行文件检测 + 注入指令。

### P2：自动修复闭环（Autofix）

**问题**：发现问题后仅提供纯文本建议，用户仍需手动回到编辑器中修改，割裂了审查-修复工作流。

**改进**：利用 Agent 的 `write_file` / `run_shell_command` 能力，生成可直接应用的修复。

```markdown
## Step 3.5: 生成并应用 Autofix

对于 Critical 和 Suggestion 级别问题，若修复方案明确：
1. 生成补丁文件 `.qwen/tmp/autofix.patch` 或直接通过 edit 工具修改文件
2. 询问用户："Review complete. Found N fixable issues. Apply auto-fixes? (y/n)"
3. 如果用户同意，逐一应用修复并展示 diff
4. 如果用户拒绝，仅保留文本建议
```

**实现成本**：SKILL.md 在 Step 3 后增加 ~15 行 Autofix 指令。

### P2：评论聚合（同模式合并）

**问题**：同一模式错误出现 10 次（如"缺少错误处理"），生成 10 条独立评论——信息冗余。

**改进**：在 Step 2.5 的去重阶段增加模式聚合。

```markdown
## Step 2.5 增强：模式聚合

在去重后，如果多个 finding 描述了**相同类型的问题**：
1. 合并为一条 finding，列出所有受影响的位置
2. 格式：
   - **File:** [多个位置列表]
   - **Pattern:** <问题模式的统一描述>
   - **Occurrences:** N 处
   - **Example:** <最典型的一个实例>
   - **Suggested fix:** <通用修复方案>
3. 如果同模式超过 5 处，在 PR 评论中只列出前 3 处 + "and N more"
```

**实现成本**：SKILL.md 在 Step 2.5 增加 ~15 行聚合指令。

### P2：异步审查（后台执行）

**问题**：审查 15 个文件的 PR 需要 2-3 分钟，期间用户无法使用 CLI。

**改进**：支持后台审查模式。

```markdown
## 异步审查模式

当 PR 较大（>500 行 diff）时，提示用户：
"This is a large PR. Run in background? (y/n)"

如果选择后台：
1. 检出 PR 的 feature branch：
   - GitHub：`git fetch origin pull/<PR>/head:pr-<PR>`
   - GitHub CLI：`gh pr checkout <PR> --detach`（推荐，兼容 Enterprise Server）
2. 创建临时 worktree：`git worktree add .qwen/tmp/review-<pr> pr-<PR>`
3. 在 worktree 中执行审查
4. 完成后通知用户
5. 清理 worktree：`git worktree remove .qwen/tmp/review-<pr>`

优势：不阻塞主工作区，不影响用户当前工作。
```

**实现成本**：SKILL.md +20 行 worktree 指令 + `BundledSkillLoader` 支持后台执行（需代码改动）。

### P2：Severity 置信度标注

**问题**：验证 Agent 只返回 confirmed/rejected 二元结果。但有些 finding 是"可能有问题但不确定"——当前要么报告要么丢弃，缺少中间态。

**改进**：增加置信度评分。

```markdown
## 验证 Agent 返回增强

验证 Agent 返回三级结果：
- `confirmed (high confidence)` — 确定是问题
- `confirmed (low confidence)` — 可能是问题，建议人工复查
- `rejected` — 不是问题

输出时区分：
- High confidence findings → 直接列在 Findings 中
- Low confidence findings → 单独列在 "Needs Human Review" 区域
```

**实现成本**：SKILL.md 修改验证 Agent 的返回格式约 ~10 行。

### P3：增量审查

**问题**：PR 更新后重新 `/review`，已确认无问题的文件被重新审查——浪费时间和 token。

**改进**：记录已审查的 commit SHA，下次只审查新增的 diff。

```markdown
## 增量审查

如果 `.qwen/review-cache/<pr-number>.json` 存在：
1. 读取上次审查的 commit SHA
2. 只获取 `git diff <base-branch>...<feature-branch>` 的增量变更（三点 diff 语法，仅对比共同祖先之后的变更）
3. 对增量变更运行完整审查流程
4. 合并增量 findings 和之前的 findings（去除已修复的）
5. 更新 cache 文件
```

**实现成本**：SKILL.md +15 行 cache 读写指令。需要确保 `.qwen/review-cache/` 在 `.gitignore` 中，防止 cache 文件被提交。

### P3：审查报告持久化

**问题**：审查结果只显示在终端，关掉就没了。

**改进**：将审查结果保存为 Markdown 文件。

```markdown
## 审查报告保存

审查完成后自动保存到 `.qwen/reviews/<date>-<target>.md`：
- 本地变更：`.qwen/reviews/<date>-local.md`
- PR 审查：`.qwen/reviews/<date>-pr-<number>.md`

报告内容：
- 审查时间、目标、diff 统计
- 所有 findings（含已验证状态）
- Verdict
- 确定性分析结果（linter/typecheck 输出）
```

**实现成本**：SKILL.md +10 行文件保存指令。

## 六、实现优先级总结

| 优先级 | 改进 | 改动量 | 仅改 SKILL.md？ | 效果 | 对标 |
|--------|------|--------|:---:|------|------|
| **P0** | 集成 linter/typecheck | +30 行 | 是 | 消除确定性问题的 LLM 浪费 | Copilot CodeQL + Gemini 前置脚本 |
| **P1** | 构建 & 测试执行 | +20 行 | 是 | 发现编译/测试失败 | Copilot CI + Gemini worktree 测试 |
| **P1** | 跨文件影响分析 | +15 行 | 是 | 发现 breaking change | Gemini codebase_investigator |
| **P1** | 项目自定义审查规则 | +10 行 | 是 | 适应不同项目规范 | Copilot copilot-instructions.md |
| **P2** | 自动修复闭环（Autofix） | +15 行 | 是（阶段 A）| 补齐审查-修复最后一步 | Copilot Autofix |
| **P2** | 评论聚合 | +15 行 | 是 | 减少冗余评论 | Claude /ultrareview 去重合成 |
| **P2** | 异步后台审查 | +20 行 + 代码 | 否 | 不阻塞用户 | Gemini async-pr-review |
| **P2** | Severity 置信度 | +10 行 | 是 | 区分确定/不确定 | Claude /ultrareview 验证 |
| **P3** | 增量审查 | +15 行 | 是（但需 .gitignore）| 避免重复审查 | Copilot 新 commit 触发 |
| **P3** | 报告持久化 | +10 行 | 是 | 审查结果可追溯 | Gemini final-assessment.md |

> **关键洞察**：P0-P1 改进都只需修改 `SKILL.md` 的 prompt 指令——不需要改 TypeScript 代码。P2 中仅"异步后台审查"需要代码改动（`BundledSkillLoader` 后台执行支持），其余均为 prompt 层增强。这是 Qwen Code skill 架构的优势——审查逻辑全部在 prompt 中，可以快速迭代。
>
> **设计哲学锚点**：所有改进都应遵循 Copilot 的 "Silence is better than noise" 原则——宁可少报，不误报。学术研究表明 LLM 正确性判定准确率仅 68.5%（GPT-4o），低质量反馈会导致"狼来了效应"，开发者停止阅读后反而错过真正的问题。
