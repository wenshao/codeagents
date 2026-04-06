# Qwen Code /review 功能改进建议

> 基于 Qwen Code、Gemini CLI、Claude Code、Copilot Code Review 四方源码/架构对比，提出 Qwen Code `/review` 功能的改进方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md) | [/review 命令对比](./review-command.md)

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

## 二、为什么 GitHub PR 里的 Copilot Code Review 体感更好

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

### 4. 高 precision 优先

Copilot CLI 的 `code-review` agent prompt 反复强调：只报真正重要的问题、不确定就不说、风格/格式/命名不提。PR review 场景里，**少量高价值评论**比大量泛化建议更有用。Qwen Code 的 SKILL.md 排除标准也有类似设计（"lean toward rejecting"），方向一致。

## 三、与业界实现的差距

### 竞品架构深度剖析

1. **Copilot Code Review**：
   - **Agentic 工作流**：运行在 GitHub Actions 上，拥有 Repository-wide search、文件读取和符号跳转能力。
   - **CodeQL 深度集成**：将 LLM 概率推理与 CodeQL 确定性语义/安全分析融合。CodeQL 提供安全漏洞和数据流的 Ground Truth，LLM 负责解释并过滤噪音，极大降低幻觉。
   - **Autofix**：提供一键修复建议，并通过 `copilot-instructions.md` 注入团队审查规范。
2. **Gemini CLI（`async-pr-review` Skill）**：
   - **异步模式**：通过 `is_background: true` 在后台分离执行，用 `gemini -p`（headless 模式）实现纯后台 LLM 推理。
   - **Ephemeral Worktree**：在 `.gemini/tmp/async-reviews/pr-<number>` 创建临时工作树，不污染主工作区。
   - **闭环验证**：后台自动运行构建、测试，将测试日志与 LLM Review 结果合成 `final-assessment.md`。
3. **Claude Code（`commands/review.ts`）**：
   - 采用 Prompt 包装模式（`LOCAL_REVIEW_PROMPT`），用 `gh pr diff` 获取差异，给出单次全面审查（正确性/风格/性能/安全）。拥有 tools: *（所有工具），模型可自主探索代码。
   - 另有 `/ultrareview` 调用远程云端进行深度审查。

### 对比矩阵

| 能力 | Qwen Code | Copilot Code Review | Claude Code | Gemini CLI |
|------|-----------|-------------------|-------------|-----------|
| 并行审查 Agent | ✓ 4 个并行 | ✓ Agentic（单 agent 多工具）| ✓ 1 个（tools: *） | ✓ 5 个异步任务 + Headless |
| 独立验证 | ✓ 每个 finding 独立验证 | — | — | — |
| 确定性分析（linter/typecheck） | — | ✓ CodeQL + ESLint | — | ✓ 自动前置检查脚本 |
| 构建/测试执行 | — | ✓（Actions CI 集成） | — | ✓ 临时工作树中跑测试 |
| 跨文件影响分析 | — | ✓ 追踪 import 链与调用流 | — | ✓ `codebase_investigator` |
| 重复代码检测 | — | — | — | ✓ `review-duplication` skill |
| 异步/后台审查 | — | ✓ GitHub Actions 后台 | — | ✓ Native Background Shells |
| 项目规则自定义 | — | ✓ `copilot-instructions.md` | — | ✓ `.gemini/skills` 体系 |
| 评论聚合 | — | ✓ 同模式合并 | — | — |
| 自动修复（Autofix） | — | ✓ 基于分析结果一键修复 | — | — |
| 增量审查 | — | ✓ 新 commit 触发 | — | — |
| 跨 PR 记忆 | — | ✓ | — | — |

### 关键差距

1. **只靠 LLM，无确定性分析**——linter/typecheck 能轻易捕捉的问题（类型错误、未使用变量），依赖 LLM 审查不仅慢，而且易产生幻觉和漏报
2. **不运行构建和测试**——无法验证代码是否编译通过或破坏了现有测试
3. **不分析跨文件影响**——Agent 的视野局限于 diff 变更本身，缺乏追踪被修改函数调用方的能力
4. **无项目自定义规则**——缺乏像 `copilot-instructions.md` 这样的项目级规范注入机制
5. **同步阻塞**——审查串行等待 LLM 响应，时间长达数分钟，期间完全阻塞 CLI
6. **缺少自动修复（Autofix）闭环**——仅提供文本建议，未利用工具能力直接生成或应用修复补丁
7. **评论缺乏聚合与置信度区分**——同一类问题被重复报告，且所有问题均被视为"确定问题"，缺乏"疑似待确认"的灰度状态
8. **缺乏记忆与持久化**——再次运行 `/review` 会重复消耗 token 审查未变更的代码，终端关闭后审查结论丢失

## 四、Qwen Code 已有的可复用基础设施

改进并非从零开始，以下现有能力可直接复用：

| 现有能力 | 源码 | 可支撑的改进 |
|---------|------|------------|
| `agent` 工具 + 并行 Subagent | `core/src/tools/agent.ts` | 多 Agent 审查（已用）、验证 Agent |
| `run_shell_command` + 后台 shell | `core/src/tools/shell.ts` | linter/build/test 执行 |
| `grep_search` + `read_file` | `core/src/tools/grep.ts` | 跨文件调用方搜索 |
| `write_file` | `core/src/tools/write-file.ts` | Autofix 补丁、报告持久化 |
| `gh` CLI 集成 | SKILL.md Step 4 已使用 | PR inline 评论、review verdict |
| `/setup-github` workflow 分发 | `cli/src/ui/commands/setupGithubCommand.ts` | 未来 GitHub Actions 集成入口 |

## 五、改进建议（按优先级）

### P0：集成确定性分析工具

**问题**：4 个 LLM Agent 审查"变量未使用"比 ESLint 慢 100 倍且不可靠。

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

**实现成本**：SKILL.md 在 Step 2 的 Agent 指令中增加 ~15 行。

### P1：项目自定义审查规则

**问题**：React 项目需要检查 hooks 规则，Go 项目需要检查 error 处理，但当前用统一 prompt。

**改进**：支持 `.qwen/review-rules.md` 项目级审查规则。

```markdown
## Step 0: 加载项目审查规则

如果项目根目录存在以下文件，读取并作为审查指导：
1. `.qwen/review-rules.md`（Qwen Code 原生）
2. `copilot-instructions.md`（兼容 Copilot）
3. `QWEN.md` 中的 `## Code Review` 章节

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
1. 创建临时 worktree：`git worktree add .qwen/tmp/review-<pr> HEAD`
2. 在 worktree 中执行审查
3. 完成后通知用户
4. 清理 worktree

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
2. 只获取 `git diff <last-reviewed-sha>..HEAD` 的增量变更
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
- 本地变更：`.qwen/reviews/2026-04-06-local.md`
- PR 审查：`.qwen/reviews/2026-04-06-pr-2923.md`

报告内容：
- 审查时间、目标、diff 统计
- 所有 findings（含已验证状态）
- Verdict
- 确定性分析结果（linter/typecheck 输出）
```

**实现成本**：SKILL.md +10 行文件保存指令。

## 六、实现优先级总结

| 优先级 | 改进 | 改动量 | 仅改 SKILL.md？ | 效果 |
|--------|------|--------|:---:|------|
| **P0** | 集成 linter/typecheck | +30 行 | 是 | 消除确定性问题的 LLM 浪费 |
| **P1** | 构建 & 测试执行 | +20 行 | 是 | 发现编译/测试失败 |
| **P1** | 跨文件影响分析 | +15 行 | 是 | 发现 breaking change |
| **P1** | 项目自定义审查规则 | +10 行 | 是 | 适应不同项目规范 |
| **P2** | 自动修复闭环（Autofix） | +15 行 | 是（阶段 A）| 补齐审查-修复最后一步 |
| **P2** | 评论聚合 | +15 行 | 是 | 减少冗余评论 |
| **P2** | 异步后台审查 | +20 行 + 代码 | 否 | 不阻塞用户 |
| **P2** | Severity 置信度 | +10 行 | 是 | 区分确定/不确定 |
| **P3** | 增量审查 | +15 行 | 是（但需 .gitignore）| 避免重复审查 |
| **P3** | 报告持久化 | +10 行 | 是 | 审查结果可追溯 |

> **关键洞察**：P0-P1 改进都只需修改 `SKILL.md` 的 prompt 指令——不需要改 TypeScript 代码。P2 中仅"异步后台审查"需要代码改动（`BundledSkillLoader` 后台执行支持），其余均为 prompt 层增强。这是 Qwen Code skill 架构的优势——审查逻辑全部在 prompt 中，可以快速迭代。
