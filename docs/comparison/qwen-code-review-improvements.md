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

## 二、与业界领先实现的差距

### 竞品架构深度剖析

1. **Copilot Code Review**:
   - **Agentic 工作流**: 运行在 GitHub Actions 上，拥有 Repository-wide search、文件读取和符号跳转的能力。
   - **CodeQL 深度集成**: 这是它最大的杀手锏。将 **大模型概率推理** 与 **CodeQL 确定性语义/安全分析** 融合。CodeQL 提供安全漏洞和复杂数据流的 Ground Truth（基础事实），LLM 负责解释并过滤噪音，这极大地降低了幻觉（Hallucination）。
   - **Autofix 与配置化**: 提供 Autofix 自动修复建议，并且能够严格遵守通过 `.github/copilot-instructions.md` 注入的团队审查规范。
2. **Gemini CLI (`async-pr-review` Skill)**:
   - **Agentic Asynchronous Pattern（智能体异步模式）**: 通过 `is_background: true` 在后台分离执行任务。它甚至通过 `gemini -p`（无头模式）实现纯后台的 LLM 推理。
   - **Ephemeral Worktrees（临时工作树）**: 为了不污染用户的主工作区，它会在 `.gemini/tmp/async-reviews/pr-<number>` 自动创建临时 `git worktree`。
   - **闭环验证**: 后台自动运行构建、测试，并在最后将测试执行日志与大模型 Review 结果合成 `final-assessment.md`。
3. **Claude Code (`commands/review.ts`)**:
   - 采用较为基础的 Prompt 包装模式 (`LOCAL_REVIEW_PROMPT`)，使用 `gh pr diff` 获取差异并直接给出一个全面的单次 Prompt 审查要求（包括正确性、风格、性能、安全等）。
   - 但也包含了调用远程 `Ultrareview` API 进行深度云端审查的能力。

### 对比矩阵

| 能力 | Qwen Code | Copilot Code Review | Claude Code | Gemini CLI |
|------|-----------|-------------------|-------------|-----------|
| 并行审查 Agent | ✓ 4 个并行 | ✓ Agentic（单 agent 多工具）| ✓ 1 个 Prompt 包装 | ✓ 5 个异步任务 + Headless |
| 独立验证 | ✓ 每个 finding 独立验证 | ✓ CodeQL 兜底验证 | — | — |
| 确定性分析（linter/typecheck） | — | ✓ CodeQL + ESLint/PMD | — | ✓ 自动前置检查脚本 |
| 构建/测试执行 | — | ✓（Actions CI 集成） | — | ✓ 临时工作树中跑测试 |
| 跨文件影响分析 | — | ✓ 追踪 import 链与调用流 | — | ✓ `codebase_investigator` |
| 重复代码检测 | — | — | — | ✓ `review-duplication` skill |
| 异步/后台审查 | — | ✓ GitHub Actions 后台 | — | ✓ Native Background Shells |
| 项目规则自定义 | — | ✓ `copilot-instructions.md` | — | ✓ `.gemini/skills` 体系 |
| 评论聚合 | — | ✓ 同模式合并 | — | — |
| 自动修复 (Autofix) | — | ✓ 基于分析结果一键修复 | — | — |

### 关键差距

结合矩阵分析，当前 Qwen Code 主要在以下 8 个方面存在差距：

1. **只靠 LLM，无确定性分析**——linter/typecheck 能轻易捕捉的问题（如类型错误、未使用变量），依赖 LLM 审查不仅慢，而且极易产生幻觉和漏报。
2. **不运行构建和测试**——无法验证代码是否能够通过编译或破坏了现有测试。
3. **不分析跨文件影响**——Agent 的视野局限于 Diff 变更本身，缺乏追踪被修改函数调用方（下游依赖）的能力。
4. **无项目自定义规则**——缺乏像 `.github/copilot-instructions.md` 这样的项目级规范注入机制。
5. **同步阻塞**——审查由于串行等待大模型响应，时间长达数分钟，期间完全阻塞 CLI。
6. **缺少自动修复 (Autofix) 闭环**——仅提供文本建议，未利用工具能力直接生成或应用修复补丁。
7. **评论缺乏聚合与置信度区分**——同一类问题会被重复报告多次，且所有问题均被视为"确定问题"，缺乏"疑似待确认"的灰度状态。
8. **缺乏记忆与持久化**——再次运行 `/review` 会重复消耗 Token 审查未变更的代码，且终端关闭后审查结论即告丢失。

## 三、改进建议（按优先级）

### P0：集成确定性分析工具

**问题**：4 个 LLM Agent 审查"变量未使用"比 ESLint 慢 100 倍且不可靠。

**改进**：在 Step 2 之前增加 Step 1.5——运行项目已有的 linter/typecheck，将结果注入后续流程。

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

**与排除标准的协同**：SKILL.md 排除标准已声明"Issues that a linter or type checker would catch automatically"不应由 LLM 报告。集成 linter 后两者形成闭环——linter 负责确定性问题，LLM 专注于 linter 无法捕获的逻辑/设计/安全问题，彼此互补。

**实现成本**：SKILL.md 增加 ~30 行指令，无代码改动。

### P1：运行构建和测试

**问题**：代码看起来正确但编译不通过、测试失败——这是最重要的反馈，但当前完全缺失。

**改进**：在 Step 2 的 4 个 Agent 中增加第 5 个——Build & Test Agent。结合 Gemini CLI 的经验，在临时 Worktree 中执行构建测试，或者确保它不会破坏主环境的状态。

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

**改进**：在审查 Agent 的指令中强调跨文件追踪，或借鉴 Copilot 的 Agentic 探索能力。

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

**改进**：支持 `.qwen/review-rules.md` 项目级审查规则（参考 Copilot 的 `copilot-instructions.md`）。

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

### P2：自动修复闭环 (Autofix)

**问题**：发现问题后仅提供纯文本建议，用户仍需手动回到编辑器中修改，割裂了工作流。

**改进**：利用 Agent 的写入能力，生成可以直接应用的修复。

```markdown
## Step 5: 生成并应用 Autofix

对于审查得出的 Critical 和 Suggestion 级别问题，若修复方案明确：
1. 生成补丁文件（如 `.qwen/tmp/autofix.patch`）或提供 `git apply` 就绪的差异内容。
2. 询问用户："Review complete. Found 2 issues. Apply suggested auto-fixes? (y/n)"
3. 如果用户同意，通过 `run_shell_command` 执行代码修正。
```

**实现成本**：SKILL.md 在最终输出阶段增加 ~15 行处理指令。

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

**问题**：审查 15 个文件的 PR 需要数分钟，期间用户无法使用 CLI。

**改进**：支持后台审查模式，借鉴 Gemini CLI 的 `async-pr-review` 模式。

```markdown
## 异步审查模式

当 PR 较大（>500 行 diff）时，提示用户：
"This is a large PR. Run in background? (y/n)"

如果选择后台：
1. 创建临时 worktree：`git worktree add .qwen/tmp/review-<pr> HEAD`
2. 在 worktree 中以 Headless 模式或脱机 Shell 后台执行审查任务。
3. 完成后将状态写入汇总文件并通知用户
4. 清理 worktree

优势：不阻塞主工作区，避免修改状态冲突。
```

**实现成本**：SKILL.md +20 行 worktree 指令 + `BundledSkillLoader` 支持后台执行（需一定代码改动）。

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

## 四、实现优先级总结

| 优先级 | 改进 | 改动量 | 效果 |
|--------|------|--------|------|
| **P0** | 集成 linter/typecheck | SKILL.md +30 行 | 消除确定性问题的 LLM 浪费，提供可靠 Ground Truth |
| **P1** | 构建 & 测试执行 | SKILL.md +20 行 | 发现编译与测试失败问题 |
| **P1** | 跨文件影响分析 | SKILL.md +15 行 | 发现 API 修改带来的 Breaking Change |
| **P1** | 项目自定义审查规则 | SKILL.md +10 行 | 适应不同项目的特有代码规范 |
| **P2** | 自动修复闭环 (Autofix) | SKILL.md +15 行 | 补齐审查-修复的最后一步，体验大增 |
| **P2** | 评论聚合 | SKILL.md +15 行 | 减少冗余同质化评论 |
| **P2** | 异步后台审查 | SKILL.md +20 行 + 代码改动 | 不阻塞用户终端心流 |
| **P2** | Severity 置信度 | SKILL.md +10 行 | 区分确定性 Bug 与疑似风险 |
| **P3** | 增量审查 | SKILL.md +15 行 | 避免重复审查，节省 Token |
| **P3** | 报告持久化 | SKILL.md +10 行 | 审查结果可追溯、可分享 |

> **关键洞察**：除“异步后台审查”需改动底层调度逻辑外，**所有 P0-P2 核心功能改进均只需要修改 `SKILL.md` 的 prompt 指令，几乎不需要改动 TypeScript 源码**。这充分体现了 Qwen Code 基于 Agent 工具链架构的强大扩展性与灵活性。