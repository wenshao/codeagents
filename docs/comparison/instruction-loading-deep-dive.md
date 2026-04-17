# 指令文件加载 Deep-Dive

> CLAUDE.md vs QWEN.md——项目指令如何被发现、解析和注入到系统提示？本文基于 Claude Code（v2.1.89 源码分析）和 Qwen Code（v0.15.0 + 2026-04 最新 PR）的源码分析，对比两者在指令文件发现层级、`@include` 指令、Frontmatter 路径过滤和信任模型方面的设计差异。
>
> **最后更新**：2026-04-17（PR#3087 Auto-Memory/Auto-Dream + **PR#3339 `.qwen/rules/` 路径规则** 均已合并，Qwen Code 指令加载系统与 Claude Code 大部分对齐）

---

## 1. 架构总览

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **指令文件名** | `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/*.md` | `QWEN.md`, `AGENTS.md`（可配置），**`.qwen/rules/*.md`**（[PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓ 2026-04-17 合并） |
| **层级数** | 6 层（Managed/User/Project/Local/AutoMem/TeamMem） | **5 层**（Global/Home/Project + rules 目录（PR#3339 ✓）+ AutoMem（PR#3087 ✓）） |
| **@include 指令** | ✅ 5 层嵌套，循环检测，路径验证 | ✅ 5 层嵌套，循环检测，路径验证 |
| **Frontmatter 路径过滤** | ✅ `paths:` glob 模式，条件规则 | ✅ [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓ |
| **HTML 注释剥离** | ✅ | ✅ [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓（PR 范围内包含） |
| **条件规则（按文件路径）** | ✅ `.claude/rules/*.md` + `paths:` frontmatter | ✅ [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓（`.qwen/rules/*.md` + `paths:` frontmatter + **嵌套子目录，超过 Claude Code 的扁平结构**） |
| **信任模型** | `hasTrustDialogAccepted` + 外部 include 审批 | `folderTrust` 布尔值 |
| **Auto Memory** | ✅ `MEMORY.md`（200 行 / 25KB 截断） | ✅ [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓（2026-04-16 合并，`extract` 子系统） |
| **Auto Dream（自动整理）** | ✅ `services/autoDream/` | ✅ [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓（`dream` 子系统） |
| **Team Memory** | ✅（feature-gated） | ❌ |
| **Hook 事件** | ✅ `InstructionsLoaded`（含加载原因） | ❌ |

---

## 2. Claude Code：六层指令体系

### 2.1 发现层级（优先级从低到高）

```
1. Managed Memory    /etc/claude-code/CLAUDE.md（全局策略，管理员设置）
       ↓
2. User Memory       ~/.claude/CLAUDE.md（用户全局，所有项目）
       ↓
3. Project Memory    从 CWD 向上遍历到项目根：
                     ├── CLAUDE.md
                     ├── .claude/CLAUDE.md
                     └── .claude/rules/*.md（条件和非条件规则）
       ↓
4. Local Memory      CLAUDE.local.md（项目本地，不提交到 Git）
       ↓
5. Auto Memory       .claude/projects/<slug>/memory/MEMORY.md（自动学习）
       ↓
6. Team Memory       API 同步的团队记忆（feature-gated）
```

**目录遍历逻辑**（源码: `claudemd.ts#L790-L977`）：
- 从 CWD 向上遍历到文件系统根
- 在项目根处停止（git/hg/svn 边界）
- Git worktree 特殊处理：避免从主仓库重复加载
- 距 CWD 更近的文件优先级更高（后加载覆盖先加载）

> 源码: `utils/claudemd.ts`（1,479 行）

### 2.2 @include 指令

**语法**：

```markdown
参考 @./src/CODING_STANDARDS.md 中的编码规范
数据库模型定义见 @./docs/schema.md#models
用户指南: @~/shared-docs/guide.md
```

**路径解析规则**：

| 语法 | 解析方式 |
|------|----------|
| `@path` | 相对于包含文件所在目录 |
| `@./path` | 相对路径（同上） |
| `@~/path` | Home 目录 |
| `@/path` | 绝对路径 |
| `@path#fragment` | 自动剥离 `#` 后缀 |
| `@path\ with\ spaces` | 反斜杠转义空格 |

**安全约束**（源码: `claudemd.ts#L626-L667`）：
- 最大嵌套深度：**5 层**
- 循环引用检测：`Set<string>` 存储已处理文件的规范路径
- Symlink 解析后加入已处理集合
- 外部文件（项目目录外）需 `hasClaudeMdExternalIncludesApproved` 审批

**代码区域排除**（源码: `claudemd.ts#L451-L535`）：
- `@include` 不在以下区域内解析：
  - HTML 注释 `<!-- ... -->`
  - 围栏代码块 ` ```...``` `
  - 行内代码 `` `...` ``

### 2.3 Frontmatter 路径过滤

```yaml
---
paths:
  - src/**/*.ts
  - !src/generated/**
description: TypeScript 编码规范
---

# TypeScript Rules
这些规则仅在模型操作匹配 `src/**/*.ts` 的文件时生效。
```

**实现**（源码: `frontmatterParser.ts#L254-L279`）：
- `paths:` 字段支持 YAML 列表或逗号分隔字符串
- 使用 `ignore` 库（picomatch）进行 glob 匹配
- `**` 视为无约束（全局适用）
- 无 `paths:` 的规则始终适用

**条件规则加载策略**：
1. **急加载**：无 `paths:` frontmatter 的规则在会话启动时加载
2. **惰加载**：有 `paths:` 的规则仅在模型触及匹配文件时加载

### 2.4 HTML 注释剥离

```markdown
<!-- 这是给人看的注释，不会出现在系统提示中 -->
# 对模型的指令
这些内容会出现在系统提示中。
```

源码: `claudemd.ts#L292-L334`。使用 marked lexer 识别块级 HTML 注释，保留代码块内的注释。

### 2.5 Auto Memory（MEMORY.md）

```
路径: .claude/projects/<project-slug>/memory/MEMORY.md
截断: 200 行 / 25,000 字节（先行截断，再字节截断）
```

> 源码: `memdir/memdir.ts#L57-L103`

### 2.6 系统提示注入

```typescript
// 源码: context.ts#L155-L189
// 注入为 claudeMd 上下文键，前缀：
"Codebase and user instructions are shown below.
 Be sure to adhere to these instructions.
 IMPORTANT: These instructions OVERRIDE any default behavior
 and you MUST follow them exactly as written."
// 每个文件: "Contents of {path} ({description}):\n\n{content}"
```

### 2.7 InstructionsLoaded Hook

```typescript
// 源码: utils/hooks.ts#L4356-L4362
{
  file_path: string,
  memory_type: 'User' | 'Project' | 'Local' | 'Managed',
  load_reason: 'session_start' | 'include' | 'compact',
  globs?: string[],           // 条件规则的 glob 模式
  trigger_file_path?: string, // 触发惰加载的文件
  parent_file_path?: string,  // 包含此文件的父文件
}
```

---

## 3. Qwen Code：三层指令体系

### 3.1 发现层级

```
1. Global Memory     ~/.qwen/QWEN.md（用户全局）
       ↓
2. Home Memory       ~/QWEN.md（仅当 CWD 在 Home 时）
       ↓
3. Project Memory    从 CWD 向上遍历到 git 根：
                     ├── QWEN.md
                     └── AGENTS.md
```

**文件名可配置**（源码: `memoryTool.ts#L78-L113`）：

```typescript
setGeminiMdFilename('MY_CUSTOM.md')  // 替换默认文件名
getAllGeminiMdFilenames()              // → ['QWEN.md', 'AGENTS.md']
```

**发现逻辑**（源码: `memoryDiscovery.ts#L68-L217`）：
- 并发限制 10 防止 EMFILE 错误
- Set 去重避免重复加载
- 支持 `includeDirectoriesToReadGemini` 配置扩展搜索目录

### 3.2 @include 指令

Qwen Code **也支持** @include（源码: `memoryImportProcessor.ts`）：

**语法**：与 Claude Code 相同（`@./path`、`@/path`）

**两种导入格式**：

| 格式 | 标记 | 默认 |
|------|------|------|
| **Tree**（递归内联） | `<!-- Imported from: {path} -->` | ✅ |
| **Flat**（扁平列表） | `--- File: {path} ---` | — |

**安全约束**（源码: `memoryImportProcessor.ts#L402-L417`）：
- 最大嵌套深度：**5 层**（与 Claude Code 相同）
- 路径验证：必须在 `allowedDirectories`（项目根）内
- 拒绝 URL（`file://`、`http://`、`https://`）

**区别**：
- 不排除 HTML 注释内的 @include
- 支持两种导入格式（Claude Code 仅一种）

### 3.3 系统提示注入

```typescript
// 源码: qwen-code/packages/core/src/core/prompts.ts#L78-L118
// 结构:
// {customInstruction}
// ---
// {userMemory}         ← 指令文件内容
// ---
// {appendInstruction}
```

### 3.4 .qwenignore

Qwen Code 支持 `.qwenignore`（gitignore 语法）排除文件，Claude Code 使用 `claudeMdExcludes` 设置。

### 3.5 Auto-Memory + Auto-Dream（PR#3087 ✓ 已合并 2026-04-16）

**来源**：[PR#3087](https://github.com/QwenLM/qwen-code/pull/3087)（LaZzyMan，2026-04-16 合并）

**设计**：直接对齐 Claude Code 的 `services/autoDream/` + `services/SessionMemory/`：

- **`extract` 子系统**：从对话中自动提取记忆（用户偏好、项目事实、决策要点）——对应 Claude Code 的 Auto-Memory
- **`dream` 子系统**：后台整理/去重/合并旧记忆——对应 Claude Code 的 Auto Dream
- **`PermissionManager` wrapper**：限制 memory scope 写入权限
  - `write_file` / `edit` 只能改 auto-memory 目录（`isAutoMemPath()`）
  - shell 只允许 AST 验证的只读命令（`isShellCommandReadOnlyAST`）
- **Bug fix**：PR 同时修复了一个严重 bug —— `saveCacheSafeParams` 被 `skipNextSpeakerCheck` 的 early-return 路径跳过，导致 `extract` 从未实际触发

**对比 Hermes Agent**：Qwen Code 的 auto-memory 仍缺失 ① 冻结快照模式 ② 双计数器 Nudge ③ 保守 review prompt 三个关键要素——详见 [闭环学习系统深度对比](./closed-learning-loop-deep-dive.md)。

### 3.6 `.qwen/rules/` 路径规则（PR#3339 ✓ 2026-04-17 合并）

**来源**：[PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓（**2026-04-17 合并**，tanzhenxin）

**设计**：**直接镜像 Claude Code 的 `.claude/rules/` 参考实现**。PR 说明明确："This aligns closely with Claude Code's `.claude/rules/` reference implementation."

**目录结构**：

```
.qwen/rules/
├── 01-general.md              # 无 paths:，始终加载
├── frontend/
│   └── react.md               # paths: src/**/*.tsx，惰加载
└── backend/
    ├── api.md                 # paths: api/**/*.ts，惰加载
    └── database.md            # paths: migrations/**/*.sql，惰加载
```

**规则文件格式**：

```markdown
---
description: Frontend coding standards
paths:
  - "src/**/*.tsx"
  - "src/**/*.ts"
---
Use React functional components with hooks.
```

**加载行为**：

| 源 | 条件 |
|---|---|
| `~/.qwen/rules/**/*.md` | 始终扫描（全局规则） |
| `<project>/.qwen/rules/**/*.md` | 仅当 folder trusted 时 |

**设计特性**：
- **递归**目录扫描（匹配 Claude Code 行为）
- **按字母顺序排序**确保确定性
- **去重**当 project root == home directory 时
- `contextRuleExcludes` 配置项（glob-based）
- **HTML 注释剥离**（PR 范围内一并实现）
- **无 frontmatter / 无 `paths:`**：基线规则，始终加载
- **有 `paths:`**：懒加载，仅当模型访问匹配文件时才注入

**对比 Claude Code**：

| 特性 | Claude Code `.claude/rules/` | Qwen Code `.qwen/rules/` (PR#3339) |
|---|---|---|
| 目录结构 | 扁平（`.claude/rules/*.md`） | **嵌套子目录支持**（`.qwen/rules/frontend/react.md`） |
| `paths:` 语法 | YAML 列表或字符串，支持 `!pattern` 否定 | YAML 列表，glob 模式 |
| 急/惰加载分离 | ✅ | ✅（PR 设计一致） |
| HTML 注释剥离 | ✅ | ✅（PR 范围包含） |
| 递归扫描 | ✅ | ✅（PR 设计一致） |
| Trust 检查 | `hasTrustDialogAccepted` | `folderTrust` |
| Hook 事件 | `InstructionsLoaded` | ❌ |

---

## 4. 逐维度对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 层级数 | 6（含 AutoMem + TeamMem） | 5 + rules（PR#3339 ✓） + AutoMem（PR#3087 ✓） |
| 文件名 | 固定（CLAUDE.md / CLAUDE.local.md） | 可配置 |
| @include 深度 | 5 | 5 |
| @include 格式 | 单一（内联） | 两种（Tree / Flat） |
| HTML 注释剥离 | ✅ | ✅ PR#3339 ✓ |
| Frontmatter | ✅ paths + description + allowed-tools | ✅ PR#3339 ✓（paths + description） |
| 条件规则 | ✅（.claude/rules/*.md + paths: glob） | ✅ PR#3339 ✓（**含嵌套子目录，超过 Claude Code**） |
| 急/惰加载 | ✅（无 paths 急加载，有 paths 惰加载） | ✅ PR#3339 ✓ |
| 信任模型 | 多级（Dialog + External Include 审批） | 布尔值（`folderTrust`） |
| Auto Memory | ✅（MEMORY.md，200 行截断） | ✅ PR#3087 ✓（`extract` 子系统） |
| Auto Dream（自动整理） | ✅（services/autoDream/） | ✅ PR#3087 ✓（`dream` 子系统） |
| Team Memory | ✅（API 同步） | ❌ |
| Hook | ✅ InstructionsLoaded | ❌ |
| 排除机制 | claudeMdExcludes 设置 | .qwenignore 文件 + `contextRuleExcludes`（PR#3339 ✓） |
| Worktree 处理 | ✅ 去重 | ❌ |

**剩余差距**（14 维度中仅 5 项）：固定文件名、Team Memory、Hook 事件、多级信任模型、Worktree 去重。

---

## 5. 设计启示

1. **条件规则是高价值功能**：`paths:` frontmatter 让团队可以为 `src/`、`tests/`、`docs/` 设置不同的编码规范，而不是一份 CLAUDE.md 塞满所有规则
2. **HTML 注释剥离**允许在指令文件中留下人读注释（如解释为什么某条规则存在），而不污染 token 预算
3. **惰加载条件规则**是 token 效率与覆盖面的平衡——只在需要时加载相关规则，避免系统提示膨胀
4. **信任模型**的复杂度与安全需求成正比——Claude Code 的多级信任适合企业场景，Qwen Code 的布尔值适合个人开发者

---

## 6. 关键源码文件

### Claude Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `utils/claudemd.ts` | 1,479 | 指令发现/解析/@include/注释剥离 |
| `utils/frontmatterParser.ts` | ~279 | Frontmatter 解析（paths/description） |
| `context.ts` | L155-L189 | 系统提示注入 |
| `memdir/memdir.ts` | ~103 | MEMORY.md 加载与截断 |
| `utils/config.ts` | L697-L762 | Trust Dialog 逻辑 |

### Qwen Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `packages/core/src/utils/memoryDiscovery.ts` | 357 | 文件发现（3 层） |
| `packages/core/src/utils/memoryImportProcessor.ts` | ~417 | @include 处理（Tree/Flat 格式） |
| `packages/core/src/tools/memoryTool.ts` | 543 | 文件名配置与存储路径 |
| `packages/core/src/core/prompts.ts` | L78-L118 | 系统提示注入 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码（Claude Code v2.1.89、Qwen Code v0.15.0）+ 2026-04 社区 PR 追踪（PR#3087 已合并 / PR#3339 开发中）。后续版本可能已变更。

## 7. 社区 PR 追踪（均已合并）

| PR | 状态 | 合并日期 | 覆盖维度 |
|---|---|---|---|
| [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) | ✅ MERGED | 2026-04-16 | Auto-Memory（`extract`）+ Auto-Dream（`dream`）+ Permission scope |
| [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) | ✅ **MERGED** | **2026-04-17** | `.qwen/rules/` 条件规则 + `paths:` frontmatter + HTML 注释剥离 + 递归扫描 + **嵌套子目录** |

**追赶结果**：本 Deep-Dive 的"逐维度对比"从 13 个差距项**减少到 5 个**（仅剩：固定文件名、Team Memory、Hook 事件、Worktree 去重、多级信任模型）。

**关键意义**：Qwen Code 和 Claude Code 在"指令加载"维度上的追赶是 **2026 年 4 月最显著的功能对齐**之一，Qwen Code 借助 **两周内的 PR#3087 + PR#3339 组合拳**基本完成了对 Claude Code 指令系统核心能力的对标，**并在"嵌套子目录规则"这一点上超过了 Claude Code 的扁平结构**。
