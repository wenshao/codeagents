# 10. /simplify 命令深度分析

> `/simplify` 是 Claude Code 独有的代码简化和质量审查命令，通过三个并行代理从不同维度审查已修改代码。

## 功能覆盖

| 工具 | 有 /simplify | 类似功能 |
|------|-------------|---------|
| **Claude Code** | ✓ `/simplify` | 三代理并行审查（复用/质量/效率） |
| **Copilot CLI** | ✗ | 无（需手动提示） |
| **Codex CLI** | ✗ | 无 |
| **Aider** | ✗ | `/architect` 可用于重构规划 |
| **Gemini CLI** | ✗ | 无 |
| **Qwen Code** | ✗ | `/review` Agent 2 (Code Quality) 部分覆盖 |
| **Kimi CLI** | ✗ | 无 |
| **Goose** | ✗ | 无 |

> **只有 Claude Code 有专用的代码简化命令。** Qwen Code 的 `/review` Agent 2 (Code Quality) 覆盖部分维度，但不自动修复。

---

## 源码定义（v2.1.81 二进制反编译提取）

```javascript
d4({
  name: "simplify",
  description: "Review changed code for reuse, quality, and efficiency,
    then fix any issues found.",
  userInvocable: true,
  async getPromptForCommand(H) {
    let $ = q7_;  // 完整提示词
    if (H) $ += `\n## Additional Focus\n${H}`;
    return [{type: "text", text: $}];
  }
})
```

### 关键特性
- 类型：**prompt Skill**（发送提示给 LLM，LLM 使用工具执行）
- 可附加自定义焦点：`/simplify 重点关注性能问题`
- 不仅审查——**自动修复发现的问题**（与 /review 只报告不修改不同）

---

## 三阶段工作流（源码完整提示词提取）

### Phase 1：识别变更

```bash
git diff        # 查看未暂存更改
git diff HEAD   # 包含已暂存更改
```

如果没有 git 变更，审查最近修改过的文件或对话中提到的文件。

### Phase 2：三个并行审查代理

> 源码指令："Use the Agent tool to launch all three agents concurrently in a single message. Pass each agent the full diff so it has the complete context."

#### Agent 1：代码复用审查

**职责：** 搜索已有的工具函数和 helper，避免重复造轮子。

| 检查项 | 说明 | 示例 |
|--------|------|------|
| **搜索已有 utility** | 在 utility 目录、共享模块、相邻文件中搜索可替代新代码的已有函数 | 手写字符串处理 → 已有 `formatString()` |
| **标记重复函数** | 新函数与已有函数功能重复 | 新建 `calculateTax()` vs 已有 `computeTax()` |
| **标记可替代的内联逻辑** | 手写逻辑可用已有工具替代 | 手动路径拼接 → `path.join()`，自定义环境检查 → `config.get()` |

源码原文（逐字提取）：
> "Search for existing utilities and helpers that could replace newly written code. Look for similar patterns elsewhere in the codebase — common locations are utility directories, shared modules, and files adjacent to the changed ones."

#### Agent 2：代码质量审查

**职责：** 检查 hacky 模式，7 个具体检查项。

| # | 检查项 | 源码描述（逐字） |
|---|--------|----------------|
| 1 | **冗余状态** | "state that duplicates existing state, cached values that could be derived, observers/effects that could be direct calls" |
| 2 | **参数膨胀** | "adding new parameters to a function instead of generalizing or restructuring existing ones" |
| 3 | **复制粘贴变体** | "near-duplicate code blocks that should be unified with a shared abstraction" |
| 4 | **抽象泄漏** | "exposing internal details that should be encapsulated, or breaking existing abstraction boundaries" |
| 5 | **字符串类型化** | "using raw strings where constants, enums (string unions), or branded types already exist in the codebase" |
| 6 | **不必要的 JSX 嵌套** | "wrapper Boxes/elements that add no layout value — check if inner component props (flexShrink, alignItems, etc.) already provide the needed behavior" |
| 7 | **不必要的注释** | "comments explaining WHAT the code does (well-named identifiers already do that), narrating the change, or referencing the task/caller — delete; keep only non-obvious WHY (hidden constraints, subtle invariants, workarounds)" |

> **注意第 7 项的判断标准：**
> - 删除：解释"做了什么"的注释（好的命名已说明）
> - 删除：叙述性注释（"此处我们修改了..."）
> - 删除：引用调用者的注释
> - **保留：解释"为什么"的注释**（隐藏约束、微妙不变量、临时解决方案）

#### Agent 3：效率审查

**职责：** 检查性能问题，7 个具体检查项。

| # | 检查项 | 源码描述（逐字） |
|---|--------|----------------|
| 1 | **不必要的工作** | "redundant computations, repeated file reads, duplicate network/API calls, N+1 patterns" |
| 2 | **错过的并发** | "independent operations run sequentially when they could run in parallel" |
| 3 | **热路径膨胀** | "new blocking work added to startup or per-request/per-render hot paths" |
| 4 | **循环中的无操作更新** | "state/store updates inside polling loops, intervals, or event handlers that fire unconditionally — add a change-detection guard so downstream consumers aren't notified when nothing changed. Also: if a wrapper function takes an updater/reducer callback, verify it honors same-reference returns" |
| 5 | **不必要的存在检查** | "pre-checking file/resource existence before operating (TOCTOU anti-pattern) — operate directly and handle the error" |
| 6 | **内存问题** | "unbounded data structures, missing cleanup, event listener leaks" |
| 7 | **过于宽泛的操作** | "reading entire files when only a portion is needed, loading all items when filtering for one" |

> **第 4 项极其精确：** 不仅检查"循环中的无条件更新"，还要求检查"wrapper 函数是否尊重 same-reference 返回值"——这是 React/状态管理中的常见性能陷阱。

> **第 5 项引用了安全概念：** TOCTOU (Time-of-Check to Time-of-Use) 反模式——先检查存在再操作不如直接操作并处理错误。

### Phase 3：修复问题

三个代理返回发现后，**自动修复所有问题**。这是与 `/review`（只报告不修改）的根本区别。

---

## /simplify vs /review 对比

| 维度 | `/simplify` | `/review` |
|------|------------|-----------|
| **目的** | 简化和优化已有代码 | 审查代码变更的正确性 |
| **代理数** | 3（复用/质量/效率） | 4-6（合规/Bug/安全/验证） |
| **审查对象** | 已修改的文件 | PR diff 或未提交更改 |
| **维度** | 复用 + 质量(7项) + 效率(7项) = **17 项** | 编译错误 + 逻辑 + 安全 + 合规 = **4 维度** |
| **修复** | **✓ 自动修复** | ✗ 只报告 |
| **PR 评论** | ✗ | ✓（`--comment`） |
| **假阳性控制** | 无（直接修复） | 验证步骤 + 80/100 阈值 |
| **触发方式** | `/simplify [焦点]` | `/code-review [--comment]` |

---

## 使用场景

### 开发完成后的质量清理
```bash
# 修改了一堆代码后，自动清理
/simplify

# 关注特定方面
/simplify 重点关注性能问题
/simplify focus on removing duplicate code
/simplify 检查是否有可复用的已有工具函数
```

### 与 /review 配合使用
```bash
# 1. 先 simplify 自动修复质量问题
/simplify

# 2. 再 review 检查正确性和安全性
/review

# 3. 最后 commit
/commit
```

### 典型工作流
```
写代码 → /simplify（自动修复 17 个维度）→ /review（检查 4 个维度）→ /commit → /commit-push-pr
```

---

## 面向 Code Agent 开发者的洞察

### 1. "审查+修复"一体化 vs "审查+报告"分离

Claude Code 选择将 `/simplify`（审查+修复）和 `/review`（审查+报告）分为两个命令，而非合并为一个。这个设计背后的逻辑：

- **`/simplify` 可以大胆修改**——因为它处理的是代码质量问题（风格、冗余、效率），修复通常是安全的
- **`/review` 不能修改**——因为它处理的是 Bug 和安全问题，修复需要人工判断

### 2. 三代理 vs 单代理

`/simplify` 使用三个并行代理而非单代理，原因是三个维度需要不同的搜索策略：
- Agent 1（复用）需要**搜索整个代码库**寻找已有函数
- Agent 2（质量）需要**理解设计模式和抽象边界**
- Agent 3（效率）需要**理解运行时行为和热路径**

这三种能力很难在单次 prompt 中同时最大化。

### 3. 为什么其他工具没有 /simplify？

实现 `/simplify` 需要：
1. **子代理系统**——并行启动 3 个代理（大部分工具有）
2. **代码搜索能力**——Agent 1 需要搜索整个代码库（需要 Glob/Grep 工具）
3. **自动修复能力**——需要 Edit/Write 工具权限（/review 故意不给）
4. **精确的审查维度定义**——21 个检查项（需要仔细设计 prompt）

Qwen Code 的 `/review` Agent 2 (Code Quality) 覆盖了部分维度，但它只报告不修复。如果将 Agent 2 扩展为自动修复，就接近 `/simplify` 了。

---

## 证据来源

| 数据 | 来源 |
|------|------|
| `/simplify` 注册定义 | 二进制 `d4({name:"simplify",...})` |
| 完整提示词（`q7_` 变量） | 二进制 strings 提取 `# Simplify: Code Review and Cleanup` |
| Agent 1-3 完整检查项 | 二进制 strings 提取，逐字记录 |
| Phase 1-3 工作流 | 二进制提示词结构分析 |
