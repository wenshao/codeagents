# 7. /review 命令实现深度对比

> 基于四个工具的 review 命令完整源码逐行分析。面向 Code Agent 开发者的技术对比。

## 源码来源

| 工具 | 源码文件 | 行数 | 获取方式 |
|------|---------|------|---------|
| **Claude Code** | `plugins/code-review/commands/code-review.md` | 109 | GitHub API |
| **Copilot CLI** | `definitions/code-review.agent.yaml` | 94 | 本地 npm 包提取 |
| **Qwen Code** | `packages/core/src/skills/bundled/review/SKILL.md` | 123 | GitHub API |
| **Codex CLI** | `codex review --help` + 二进制分析 | 37 | 本地 --help |

---

## 一、架构设计对比

### Claude Code：编排者模式（Orchestrator）

```
用户 → /code-review [--comment]
  │
  ├── Step 1: Haiku 前置检查代理
  │     └── 检查: 已关闭? 草稿? trivial? 已审查?
  │
  ├── Step 2: Haiku 规范收集代理
  │     └── 搜集仓库中所有 CLAUDE.md 文件路径
  │
  ├── Step 3: Sonnet 摘要代理
  │     └── 生成 PR 变更结构化摘要
  │
  ├── Step 4: 4 并行审查代理 ──┬── Sonnet: CLAUDE.md 合规 #1
  │                            ├── Sonnet: CLAUDE.md 合规 #2（冗余）
  │                            ├── Opus: Bug 扫描（仅 diff）
  │                            └── Opus: 安全/逻辑分析（新增代码）
  │
  ├── Step 5: N 并行验证代理（每个问题一个）
  │     ├── Opus 验证 Bug（读取完整上下文确认）
  │     └── Sonnet 验证 CLAUDE.md 违规（确认规则范围）
  │
  ├── Step 6: 过滤未通过验证的问题
  │
  ├── Step 7: 终端输出
  │
  ├── Step 8: 内部自检（列出计划评论，不发布）
  │
  └── Step 9: 发布 PR 内联评论（如 --comment）
        └── mcp__github_inline_comment__create_inline_comment
```

**设计理念：高信号、低噪音。** 通过验证步骤（Step 5）和过滤步骤（Step 6）确保只有真正的问题被报告。宁可漏报也不误报。

**模型分层策略：**
- **Haiku**（最便宜）：前置检查、文件列表等低复杂度任务
- **Sonnet**（平衡）：摘要、合规审计、CLAUDE.md 验证
- **Opus**（最强）：Bug 检测、安全分析、Bug 验证（需要最深推理）

**代理数量：** 最少 7 个代理（2 Haiku + 1 Sonnet + 4 审查），若发现 N 个问题则再增加 N 个验证代理。

---

### Copilot CLI：单代理深度模式（Single-Agent Deep）

```
用户 → /review
  │
  └── code-review 代理 (claude-sonnet-4.5, tools: *)
        │
        ├── 1. git status → staged/unstaged/branch diff
        ├── 2. 读取周围代码理解上下文
        ├── 3. 尝试编译/测试验证
        └── 4. 仅报告高置信度问题
```

**设计理念："$20 bill in jeans"** — 每条反馈都应该是惊喜，不是噪音。

**与 Claude Code 的根本区别：** 没有独立的验证**代理**，但有**实际运行验证**。Claude Code 用独立 LLM 代理重新审查每个问题；Copilot CLI 用 `bash` 工具实际编译代码和运行测试来验证。这是两种不同的验证哲学：**LLM 推理验证 vs 代码执行验证。**

**验证能力（源码原文，tools: `"*"`）：**
```
3. **Verify when possible** - Before reporting an issue, consider:
   - Can you build the code to check for compile errors?
   - Are there tests you can run to validate your concern?
   - Is the "bug" actually handled elsewhere in the code?
   - Do you have high confidence this is a real problem?
```

```
Use `bash` to run git commands, build, run tests, execute code
```

> **重要发现：** Copilot CLI 拥有 `tools: ["*"]`（全部工具），prompt 明确指示它**编译代码、运行测试**来验证发现的问题。这意味着它的验证不是靠"第二个 LLM 思考"，而是靠**实际执行代码**。在某些场景下（如编译错误检测），这比 Claude Code 的 LLM 验证更可靠。

**关键约束（源码原文）：**
```
CRITICAL: You Must NEVER Modify Code.
You have access to all tools for investigation purposes only:
- Use `bash` to run git commands, build, run tests, execute code
- Use `view` to read files and understand context
- Use `grep` and `glob` to find related code
- Do NOT use `edit` or `create` to change files
```

这是唯一**同时禁止修改代码但允许运行代码**的实现——可以编译和测试，但不能修改。

---

### Qwen Code：并行维度模式（Parallel Dimensions）

```
用户 → /review [PR号 | 文件路径]
  │
  ├── Step 1: 确定审查范围
  │     ├── 无参数 → git diff + git diff --staged
  │     ├── PR 号 → git stash → gh pr checkout → gh pr view → 保存到 /tmp
  │     └── 文件路径 → git diff HEAD -- <file>
  │
  ├── Step 2: 4 并行审查代理 ──┬── Agent 1: Correctness & Security
  │                            ├── Agent 2: Code Quality
  │                            ├── Agent 3: Performance & Efficiency
  │                            └── Agent 4: Undirected Audit（无预设）
  │
  └── Step 3: 环境恢复 + 汇总输出
        ├── checkout 原始分支
        ├── git stash pop
        ├── 删除临时文件
        └── 合并四个代理结果 → Summary + Findings + Verdict
```

**设计理念：全维度覆盖 + 自由探索。** 前三个代理覆盖已知维度，第四个代理（Undirected Audit）用全新视角捕获其他代理遗漏的问题。

**与 Claude Code 的关键差异：**
1. **无验证步骤** — 信任每个代理的判断
2. **无 CLAUDE.md 合规检查** — 只看代码本身
3. **有环境恢复** — 审查 PR 后自动恢复（Claude Code 没有）
4. **diff 不复制** — 源码明确要求"Do NOT paste the full diff into each agent's prompt"，而是让代理自己获取
5. **有 Verdict** — 输出包含 Approve/Request changes/Comment 决定（Claude Code 不做决定）

---

### Codex CLI：CLI-first 模式（非交互式）

```
codex review [--uncommitted] [--base BRANCH] [--commit SHA] [--title TITLE] [PROMPT]
  │
  └── 单代理审查（GPT-5 系列模型）
        ├── 确定审查目标（uncommitted/base/commit）
        └── 生成审查报告
```

**设计理念：CI/CD 优先。** 作为 CLI 子命令（非交互式斜杠命令），可直接嵌入 GitHub Actions、GitLab CI 等。

**与其他工具的根本区别：**
- 不在交互式会话中运行
- 支持从 stdin 读取指令（`echo "check errors" | codex review -`）
- 支持 `@codex review` PR 评论触发
- 可指定审查范围（`--uncommitted` / `--base` / `--commit`）

---

## 二、审查维度深度对比

### 维度定义（源码逐字提取）

| 维度 | Claude Code | Copilot CLI | Qwen Code |
|------|------------|-------------|-----------|
| **编译/解析错误** | "code will fail to compile or parse (syntax errors, type errors, missing imports, unresolved references)" | — | — |
| **逻辑错误** | "code will definitely produce wrong results regardless of inputs (clear logic errors)" | "Bugs and logic errors" | "Logic errors and edge cases" |
| **安全漏洞** | "security issues, incorrect logic" (Agent 4) | "Security vulnerabilities" | "Security vulnerabilities (injection, XSS, SSRF, path traversal, etc.)" |
| **竞态条件** | — | "Race conditions or concurrency issues" | "Race conditions and concurrency issues" |
| **内存泄漏** | — | "Memory leaks or resource management problems" | "Memory leaks or excessive memory usage" |
| **错误处理** | — | "Missing error handling that could cause crashes" | "Error handling gaps" |
| **数据假设** | — | "Incorrect assumptions about data or state" | "Null/undefined handling" + "Type safety issues" |
| **API 破坏** | — | "Breaking changes to public APIs" | — |
| **性能问题** | — | "Performance issues with measurable impact" | 整个 Agent 3: "N+1 queries, memory leaks, unnecessary re-renders, inefficient algorithms, missing caching, bundle size" |
| **代码质量** | — | — | 整个 Agent 2: "style consistency, naming, duplication, over-engineering, comments, dead code" |
| **CLAUDE.md 合规** | 整个 Agents 1+2: "CLAUDE.md compliance" | — | — |
| **自由审计** | — | — | 整个 Agent 4: "business logic, boundary interactions, implicit assumptions, unexpected side effects" |

**统计：**
- Claude Code: 3 个明确维度 + CLAUDE.md 合规（独有）
- Copilot CLI: **8 个明确维度**（最多）
- Qwen Code: 4 个代理维度，每个含 5-7 个子项 ≈ **24 个检查项**（最细）

---

## 三、假阳性控制对比

### Claude Code 的三层过滤（业界最严格）

**第一层：Prompt 指令排除（源码原文）**
```
Do NOT flag:
- Code style or quality concerns
- Potential issues that depend on specific inputs or state
- Subjective suggestions or improvements
```

**第二层：显式假阳性清单（6 类）**
```
- Pre-existing issues（已有代码中的问题，非 PR 引入）
- Something that appears to be a bug but is actually correct
- Pedantic nitpicks that a senior engineer would not flag
- Issues that a linter will catch (do not run the linter to verify)
- General code quality concerns unless explicitly required in CLAUDE.md
- Issues mentioned in CLAUDE.md but explicitly silenced in the code (via lint ignore comment)
```

**第三层：独立验证代理（唯一拥有此机制的工具）**
每个被标记的问题由独立的验证代理重新审查，未通过验证的问题被移除。这相当于"二次确认"——发现者和验证者是不同的代理实例。

### Copilot CLI 的三层过滤（含代码执行验证）

**第一层：Prompt 核心原则**
```
If you're unsure whether something is a problem, DO NOT MENTION IT.
```

**第二层：显式排除清单（8 类，源码原文）**
```
CRITICAL: What You Must NEVER Comment On:
- Style, formatting, or naming conventions
- Grammar or spelling in comments/strings
- "Consider doing X" suggestions that aren't bugs
- Minor refactoring opportunities
- Code organization preferences
- Missing documentation or comments
- "Best practices" that don't prevent actual problems
- Anything you're not confident is a real issue
```

**第三层：代码执行验证（独有）**

prompt 明确指示在报告问题前尝试**编译和运行测试**：
```
Verify when possible:
- Can you build the code to check for compile errors?
- Are there tests you can run to validate your concern?
```

> **这与 Claude Code 的验证步骤形成互补：** Claude Code 用独立 LLM 代理做"第二意见"验证；Copilot CLI 用 `bash` 实际运行代码验证。**编译错误和测试失败是 100% 确定的**——不存在 LLM 幻觉问题。

### Qwen Code 的一层过滤

**仅有 Guidelines 指导：**
```
- Be specific and actionable. Avoid vague feedback.
- Reference the existing codebase conventions.
- Focus on the diff, not pre-existing issues.
- Keep the review concise.
- Flag any exposed secrets, credentials, API keys, or tokens as Critical.
```

**无显式排除清单，无验证步骤。** 依赖四个代理的专注维度来自然过滤。

### Codex CLI

**无公开的假阳性控制机制。** 审查行为由模型内部判断决定。

---

## 四、输入/输出协议对比

### 输入方式

| 输入类型 | Claude Code | Copilot CLI | Qwen Code | Codex CLI |
|---------|------------|-------------|-----------|-----------|
| 未提交更改 | ✓ | ✓（自动检测） | ✓（`git diff`） | ✓（`--uncommitted`） |
| 分支 diff | ✓（自动） | ✓（`git diff main...HEAD`） | ✓（PR checkout） | ✓（`--base BRANCH`） |
| 特定 PR | ✓（PR 号） | ✗（需手动 checkout） | ✓（PR 号/URL） | ✗ |
| 特定 commit | ✗ | ✗ | ✗ | ✓（`--commit SHA`） |
| 特定文件 | ✗ | ✗ | ✓（文件路径） | ✗ |
| 自定义指令 | ✗ | ✗ | ✗ | ✓（`[PROMPT]` 或 stdin） |

### 输出格式

**Claude Code：** 问题列表 + 可选 PR 内联评论
```markdown
## Code review
Found 3 issues:
1. Missing error handling for OAuth callback (CLAUDE.md says "Always handle OAuth errors")
   https://github.com/owner/repo/blob/abc123/src/auth.ts#L67-L72
```
- 链接格式要求：完整 SHA + `#L` 标记 + 至少 1 行上下文
- 可提交建议：小修复包含 committable suggestion block，大修复只描述

**Copilot CLI：** 结构化问题报告
```markdown
## Issue: [Brief title]
**File:** path/to/file.ts:123
**Severity:** Critical | High | Medium
**Problem:** Clear explanation
**Evidence:** How you verified this
**Suggested fix:** Brief description (but do not implement it)
```
- 无问题时："No significant issues found in the reviewed changes."
- 无填充："Do not pad your response with filler. Do not summarize what you looked at. Do not give compliments."

**Qwen Code：** 三段式报告 + Verdict
```markdown
### Summary
1-2 句概述

### Findings
- **Critical** — Must fix before merging.
- **Suggestion** — Recommended improvement.
- **Nice to have** — Optional optimization.

### Verdict
Approve | Request changes | Comment
```
- 每个 finding 包含：文件:行号 + 问题 + 影响 + 建议修复
- **唯一输出 Verdict（审查决定）的工具**

**Codex CLI：** 无公开的输出格式规范（由模型自由生成）

---

## 五、工具权限对比

| 工具 | 允许的工具 | 禁止的工具 | 约束方式 |
|------|-----------|-----------|---------|
| **Claude Code** | `Bash(gh:*)`, `mcp__github_inline_comment__*` | 所有其他工具 | **Frontmatter `allowed-tools` 白名单**（最严格） |
| **Copilot CLI** | `*`（全部） | edit, create | **Prompt 文本禁止**（"You Must NEVER Modify Code"） |
| **Qwen Code** | task, run_shell_command, grep_search, read_file, glob | 其他 | **Frontmatter `allowedTools` 白名单** |
| **Codex CLI** | 全部（CLI 子命令，非 Skill） | — | 由审批模式控制 |

**关键设计差异：**
- Claude Code 只允许 `gh` CLI 和一个 MCP 工具——**连文件读取都不在白名单中**（代理必须通过 `gh pr diff` 获取代码）
- Copilot CLI 给了全部工具但用 prompt 约束——**可以运行测试、编译代码来验证问题**
- Qwen Code 允许读取和搜索但不允许 GitHub 交互——**无法自动发布 PR 评论**

---

## 六、PR 评论集成

| 维度 | Claude Code | Copilot CLI | Codex CLI | Qwen Code |
|------|------------|-------------|-----------|-----------|
| **触发方式** | `/code-review --comment` | `/review` 后手动 | `@codex review` PR 评论 | 无 |
| **评论位置** | **内联评论**（代码行级别） | 终端输出（需手动复制） | **PR 评论** | 终端输出 |
| **评论工具** | MCP `create_inline_comment` | — | GitHub API | — |
| **可提交建议** | ✓（小修复包含 suggestion block） | ✗ | ✗ | ✗ |
| **去重** | ✓（"Only post ONE comment per unique issue"） | — | — | — |
| **无问题评论** | ✓（"No issues found"模板） | ✓（"No significant issues"） | — | — |
| **链接格式** | 完整 SHA + `#Lstart-Lend` | `file:line` | — | `file:line` |

---

## 七、性能与成本考量

| 维度 | Claude Code | Copilot CLI | Qwen Code | Codex CLI |
|------|------------|-------------|-----------|-----------|
| **最少 API 调用** | 7+N（N=问题数） | 1 | 5（1 调度 + 4 代理） | 1 |
| **使用的模型** | Haiku+Sonnet+Opus（3 级） | claude-sonnet-4.5（1 级） | 继承主模型（1 级） | GPT-5 系列（1 级） |
| **估算 token** | 高（多代理冗余） | 中 | 中高（4 代理） | 低（单次） |
| **估算延迟** | 30-120 秒 | 10-30 秒 | 20-60 秒 | 5-15 秒 |
| **并行度** | 高（Step 4: 4 并行 + Step 5: N 并行） | 低（串行） | 中（Step 2: 4 并行） | 低（单次） |

---

## 八、面向 Code Agent 开发者的设计洞察

### 1. 两种验证哲学

| 工具 | 验证方式 | 原理 | 可靠性 |
|------|---------|------|--------|
| **Claude Code** | 独立 LLM 验证代理 | 另一个 LLM 重新审查每个问题 | 高（但 LLM 可能幻觉） |
| **Copilot CLI** | **编译+运行测试** | `bash` 实际执行代码验证 | **最高**（编译错误 = 100% 确定） |
| **Qwen Code** | 无 | 信任代理判断 | 中 |
| **Codex CLI** | 无 | 信任模型 | 中 |

Claude Code 的 LLM 验证适合**逻辑错误和设计问题**（需要推理判断）。Copilot CLI 的代码执行验证适合**编译错误、类型错误、测试失败**（客观可验证）。

**开发者决策：** 理想的 /review 实现应该**两者结合**——用代码执行验证客观问题，用 LLM 验证主观问题。目前没有工具做到这一点。

### 2. 多代理 vs 单代理

| 方案 | 优势 | 劣势 |
|------|------|------|
| **多代理**（Claude Code, Qwen Code） | 维度覆盖全、可并行、专注度高 | 成本高、需要编排逻辑、结果合并复杂 |
| **单代理**（Copilot CLI, Codex CLI） | 成本低、简单、上下文连贯 | 容易遗漏维度、无冗余 |

**Qwen Code 的 Agent 4 "Undirected Audit" 是一个优雅的设计：** 既利用了多代理的覆盖优势，又通过无预设维度避免了维度盲区。这是最值得其他工具借鉴的设计。

### 3. CLAUDE.md 合规检查的价值

Claude Code 独有的 CLAUDE.md 合规检查意味着团队可以将编码规范写入 CLAUDE.md，然后代码审查自动执行。这把"规范文档"变成了"可执行策略"——规范不再是建议，而是审查条件。

**对其他工具的启示：** 任何支持项目指令文件（AGENTS.md, GEMINI.md）的工具都可以做类似的合规检查，但目前只有 Claude Code 实现了。

### 4. diff 传递策略

Qwen Code 明确禁止将完整 diff 粘贴给每个代理（"Do NOT paste the full diff into each agent's prompt — this duplicates it 4x"），而是让代理自己执行 git 命令获取。这节省了大量 token 但增加了工具调用延迟。

Claude Code 走了不同路线——通过 `gh pr diff` 获取 diff，但代理工具白名单中没有 `Read`，说明它也不直接传递文件内容。

### 5. 环境恢复

只有 Qwen Code 在审查 PR 后自动恢复原始分支和 stash。这是一个容易被忽视但非常实用的功能——如果审查过程中 checkout 了 PR 分支，用户的本地工作状态会被打乱。

---

## 证据来源

| 工具 | 源码获取方式 | 完整性 |
|------|------------|--------|
| Claude Code | `gh api repos/anthropics/claude-code/contents/plugins/code-review/commands/code-review.md` | **完整 109 行 prompt** |
| Copilot CLI | `cat definitions/code-review.agent.yaml`（本地 npm 包） | **完整 94 行 YAML + prompt** |
| Qwen Code | `gh api repos/QwenLM/qwen-code/contents/packages/core/src/skills/bundled/review/SKILL.md` | **完整 123 行 SKILL.md** |
| Codex CLI | `codex review --help` + 二进制 strings | **CLI 接口完整，内部 prompt 不可见** |
