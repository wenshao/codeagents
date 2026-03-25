# /review 命令全工具对比

> 代码审查是 AI 编程助手的核心能力之一。本文对比各工具的 /review 实现深度。

## 总览

| 工具 | 有 /review | 实现方式 | 多代理 | 审查维度 | 自动 PR 评论 |
|------|-----------|---------|--------|---------|-------------|
| **Claude Code** | ✓ | Skill + code-review 插件（9 步流水线） | **4-6 代理**（Haiku/Sonnet/Opus） | 4 维度 + 验证 | ✓（`--comment`） |
| **Copilot CLI** | ✓ | 内置命令 + code-review 代理（YAML） | **1 代理**（claude-sonnet-4.5） | 8 维度 | ✓（`gh pr`） |
| **Codex CLI** | ✓ | CLI 子命令 `codex review` + TUI `/review` | **1 代理** | 通用 | ✓（`@codex review`） |
| **Qwen Code** | ✓ | Skill（`skills/bundled/review/SKILL.md`） | **4 代理**（并行） | 4 维度 | ✗ |
| **Gemini CLI** | ✓ | 官方扩展（`/code-review`） | **1 代理** | 通用 | ✓（via MCP） |
| **Aider** | ✗ | 无（`/ask` 替代） | — | — | — |
| **Kimi CLI** | ✗ | 无（explore 子代理替代） | — | — | — |
| **Goose** | ✗ | 无（MCP + 提示词替代） | — | — | — |
| **OpenCode** | ✗ | 无 | — | — | — |

---

## Claude Code `/review`（最强实现）

> 源码：[`plugins/code-review/commands/code-review.md`](https://github.com/anthropics/claude-code/tree/main/plugins/code-review)

### 9 步流水线

| 步骤 | 代理 | 模型 | 任务 |
|------|------|------|------|
| 1 | 前置检查 | Haiku | 跳过已关闭/草稿/trivial/已审查的 PR |
| 2 | 收集规范 | Haiku | 搜集仓库中所有 CLAUDE.md 文件 |
| 3 | 变更摘要 | Sonnet | 生成 PR 变更结构化摘要 |
| 4a | CLAUDE.md 合规 #1 | Sonnet | 检查代码是否违反 CLAUDE.md 规范 |
| 4b | CLAUDE.md 合规 #2 | Sonnet | 冗余审计（降低遗漏率） |
| 4c | Bug 扫描 | **Opus** | 只关注 diff 中新引入的缺陷 |
| 4d | 安全/逻辑分析 | **Opus** | 分析新增代码的安全隐患 |
| 5 | 并行验证 | Opus/Sonnet | 每个问题由独立验证代理确认 |
| 6-9 | 过滤+输出+评论 | — | 移除未验证问题，发布 PR 内联评论 |

### 审查维度
1. 编译/解析错误（语法、类型、缺失导入）
2. 逻辑错误（无论输入都产生错误结果）
3. 安全问题（注入、XSS 等）
4. CLAUDE.md 合规（引用具体被违反的规则）

### 显式排除
- 代码风格/格式
- Linter 能捕获的问题
- 主观建议
- 已有代码的问题（非 PR 引入）

### 过滤机制
- 验证代理二元判断（通过/不通过）
- README 描述的 80/100 置信度阈值
- 实际效果：审查命中率 16% → 54%，假阳性 <1%

---

## Copilot CLI `/review`

> 源码：[`definitions/code-review.agent.yaml`](EVIDENCE.md 中完整记录)

### 内置 code-review 代理

| 属性 | 值 |
|------|-----|
| 模型 | `claude-sonnet-4.5` |
| 工具 | 全部（`*`），但 prompt 禁止使用 edit/create |

### 审查维度（8 个，prompt 明确定义）
1. Bugs and logic errors
2. Security vulnerabilities
3. Race conditions or concurrency issues
4. Memory leaks or resource management
5. Missing error handling that could cause crashes
6. Incorrect assumptions about data or state
7. Breaking changes to public APIs
8. Performance issues with measurable impact

### 核心原则
> "Finding your feedback should feel like finding a $20 bill in your jeans after doing laundry"

### 显式排除（8 类）
- Style, formatting, naming
- Grammar/spelling in comments
- "Consider doing X" suggestions
- Minor refactoring
- Code organization preferences
- Missing documentation
- "Best practices" without actual problems
- Anything uncertain

### 审查流程
1. 理解变更范围（git status → staged/unstaged/branch diff）
2. 理解上下文（读取周围代码）
3. 验证（尝试编译、运行测试）
4. 仅报告高置信度问题

---

## Codex CLI `codex review`

> 源码：`codex review --help` 输出

### CLI 子命令

```bash
codex review [PROMPT]               # 自定义审查指令
codex review --uncommitted           # 审查未提交更改
codex review --base main             # 审查相对于 main 的更改
codex review --commit abc123         # 审查特定 commit
codex review --title "Auth Module"   # 附加标题
echo "check errors" | codex review - # 从 stdin 读取
```

### 特点
- 非交互式（CLI 子命令，可用于 CI/CD）
- 支持 `@codex review` PR 评论触发
- 可启用自动审查（每个新 PR）
- 推荐 GPT-5.2-Codex 模型

---

## Qwen Code `/review`

> 源码：[`skills/bundled/review/SKILL.md`](从 GitHub 完整提取)

### 四代理并行审查

| 代理 | 维度 | 检查项 |
|------|------|--------|
| **Agent 1** | Correctness & Security | 逻辑错误、空值、竞态条件、注入漏洞、类型安全、错误处理 |
| **Agent 2** | Code Quality | 代码风格一致性、命名规范、代码重复、过度工程、注释、死代码 |
| **Agent 3** | Performance & Efficiency | N+1 查询、内存泄漏、不必要重渲染、低效算法、缓存、包大小 |
| **Agent 4** | Undirected Audit | **无预设维度**——全新视角捕获其他代理遗漏的问题 |

### 输入方式
- 无参数：审查本地未提交更改（`git diff` + `git diff --staged`）
- PR 号/URL：checkout PR 分支，用 `gh pr view` 获取上下文
- 文件路径：审查指定文件的最近更改

### 输出格式
```
### Summary
1-2 句概述

### Findings
- **Critical** — 必须修复（Bug、安全、数据丢失）
- **Suggestion** — 建议改进
- **Nice to have** — 可选优化

### Verdict
Approve | Request changes | Comment
```

### 环境恢复
审查 PR 后自动恢复原始分支和 stash。

---

## Gemini CLI `/code-review`

> 来源：官方扩展 `gemini-cli-extensions/code-review`

- 需要安装：`gemini extensions install https://github.com/gemini-cli-extensions/code-review`
- 两个命令：`/code-review`（分支变更）和 `/pr-code-review`（PR 变更）
- 单代理审查
- 通过 MCP GitHub 工具发布 PR 评论

---

## 无 /review 的工具替代方案

| 工具 | 替代 | 说明 |
|------|------|------|
| **Aider** | `/ask` 模式 | 只读问答，手动要求审查 |
| **Kimi CLI** | `explore` 子代理 | 只读代码调查，非专用审查 |
| **Goose** | MCP + 提示词 | 通过 GitHub MCP 读取 diff，自由提示审查 |
| **OpenCode** | `review` 代理 | 内置代理之一，但无斜杠命令 |

---

## 横向对比

| 维度 | Claude Code | Copilot CLI | Codex CLI | Qwen Code | Gemini CLI |
|------|------------|-------------|-----------|-----------|-----------|
| **代理数** | 4-6 | 1 | 1 | 4 | 1 |
| **使用模型** | Haiku+Sonnet+Opus | claude-sonnet-4.5 | gpt-5.2-codex | 模型继承 | Gemini |
| **审查维度** | 4（含 CLAUDE.md 合规） | 8（最多） | 通用 | 4（含自由审计） | 通用 |
| **验证步骤** | ✓（独立验证代理） | ✗ | ✗ | ✗ | ✗ |
| **假阳性过滤** | 80/100 阈值 + 显式排除列表 | 显式排除列表 | ✗ | ✗ | ✗ |
| **PR 评论** | ✓（内联 + 摘要） | ✓ | ✓（@codex review） | ✗ | ✓ |
| **CI/CD 集成** | ✓（`--comment` flag） | ✓（`gh pr`） | ✓（`codex review` CLI） | ✗ | ✗ |
| **规范合规检查** | ✓（CLAUDE.md） | ✗ | ✗ | ✗ | ✗ |
| **自由审计维度** | ✗ | ✗ | ✗ | ✓（Agent 4 无预设） | ✗ |
| **环境恢复** | ✗ | ✗ | ✗ | ✓（自动 stash/checkout） | ✗ |

## 结论

- **最强整体**：Claude Code — 唯一有验证步骤和假阳性过滤的工具（审查命中率 54%，假阳性 <1%）
- **最多审查维度**：Copilot CLI — 8 个明确定义的审查维度
- **最创新**：Qwen Code — Agent 4 "Undirected Audit" 无预设维度设计 + 自动环境恢复
- **最适合 CI/CD**：Codex CLI — 非交互式 CLI 子命令，最易集成
- **最开放**：Gemini CLI — 扩展形式，可自定义审查逻辑
