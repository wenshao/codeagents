# Qwen Code 改进建议 — /security-review 专项安全审查 (Security Audit Review)

> 核心洞察：随着大模型被越来越多地用于辅助代码审查 (Code Review)，人们发现：如果在 Prompt 中仅仅让它“审查这段代码”，大模型的关注点往往会严重分散到诸如“变量命名不规范”、“缺少注释”、“可以换个更快的写法”等无足轻重的格式问题上，而漏掉致命的“SQL 注入”或“越权访问”漏洞。Claude Code 通过专有的 `/security-review` 命令，结合纯净的 `git diff` 上下文收集和极其聚焦的 Prompt 模板，将大模型瞬间转化为了冷酷的安全专家；而 Qwen Code 目前只能依靠开发者自己撰写复杂的命令。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、通用审查在安全领域的软肋

### 1. Qwen Code 现状：泛泛而谈的 Review
目前如果在 Qwen Code 里使用默认的分析能力去审查一个 Pull Request：
- **痛点**：Agent 会试图面面俱到，把大量的精力花在理解业务逻辑上。如果你传入了一个包含 10 个文件、2000 行变更的巨大提交，模型极度容易在汪洋大海中产生“丢失注意力（Lost in the middle）”。对于深藏在第 1800 行的一个没有验证用户输入的 `req.body.userId`，通用模型基本抓不住。

### 2. Claude Code 解决方案：高定版的渗透专家
在 Claude Code 的 `commands/security-review.ts` 源码中，作者巧妙地封装了一个“开箱即用”的高级 Slash 命令。

#### 机制一：极其聚焦的系统提示词 (Focused Prompting)
它内置了一段极其专业的 Markdown 模板：
```markdown
You are a senior security engineer conducting a focused security review of the changes on this branch.
...
OBJECTIVE:
Analyze ONLY for potential security vulnerabilities. Ignore style, performance, and formatting.
Focus on OWASP Top 10 categories including:
- SQL/Command Injection
- Cross-Site Scripting (XSS)
- Authentication & Authorization bypass
- Server-Side Request Forgery (SSRF)
- ...
If the code is secure, return "No significant security issues found."
```
这段强硬的指令彻底关掉了大模型对业务逻辑和样式的兴趣，强行迫使其把所有计算资源用来扫描漏洞模式。

#### 机制二：基于 Git Diff 的靶向注入
与泛读整个工作区不同，这个命令内部自动组合了一系列特定的 Bash 工具：
```bash
git status
git diff --name-only origin/HEAD...
git log --no-decorate origin/HEAD...
git diff origin/HEAD...
```
它利用这些宏指令精确提取了当前分支的增量变化（Delta），拼装在刚才的 Prompt 中，让大模型的安全审查变得有的放矢，效率极高。

## 二、Qwen Code 的改进路径 (P3 优先级)

让大模型在最能体现其价值的“代码找茬”领域发挥出极限威力。

### 阶段 1：开发安全专项 Skill
不需要写复杂的 TypeScript 逻辑！我们可以完全借助系统的插件/命令支持：
1. 新建 `packages/core/src/skills/bundled/security-review/SKILL.md`。
2. 参照上述的机制，在文件中固化好关于 OWASP 漏洞模式的系统级提示词。

### 阶段 2：注入上下文变量
在这个 Skill 文件中，使用预处理变量或直接集成工具宏（Macros）：
```markdown
# Git Changes
<git_diff>
${EXEC: git diff main...HEAD}
</git_diff>
```
确保每次运行 `/security-review` 时，大模型拿到的永远是最精准的当前开发分支变动流。

### 阶段 3：引导强类型输出
结合我们之前探讨过的 `--json-schema` 特性，可以进一步将 `/security-review` 的输出强制固化为一份标准的漏洞扫描报告（包含行号、危险等级、修复建议），从而无缝对接给内部的 SonarQube 或者 GitHub Security Advisory 面板。

## 三、改进收益评估
- **实现成本**：极低。本质上是提供了一个官方预制的、高质量的最佳实践 Prompt 组合。开发仅需 2 小时。
- **直接收益**：
  1. **极强的专业感**：这能向企业客户传达一个强烈信号：Qwen Code 不仅是写代码的助理，更是企业研发流程中可靠的“安全左移（Shift-Left Security）”拦截网。
  2. **避免人工繁琐拼接**：一键执行就能完成原本需要打几十个字和复制粘贴代码的审查流程。