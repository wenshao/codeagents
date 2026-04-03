# 指令文件加载 Deep-Dive

> CLAUDE.md vs QWEN.md——项目指令如何被发现、解析和注入到系统提示？本文基于 Claude Code（v2.1.89 源码分析）和 Qwen Code（v0.15.0 开源）的源码分析，对比两者在指令文件发现层级、`@include` 指令、Frontmatter 路径过滤和信任模型方面的设计差异。

---

## 1. 架构总览

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **指令文件名** | `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/*.md` | `QWEN.md`, `AGENTS.md`（可配置） |
| **层级数** | 6 层（Managed/User/Project/Local/AutoMem/TeamMem） | 3 层（Global/Home/Project） |
| **@include 指令** | ✅ 5 层嵌套，循环检测，路径验证 | ✅ 5 层嵌套，循环检测，路径验证 |
| **Frontmatter 路径过滤** | ✅ `paths:` glob 模式，条件规则 | ❌ |
| **HTML 注释剥离** | ✅ | ❌ |
| **条件规则（按文件路径）** | ✅ `.claude/rules/*.md` + `paths:` frontmatter | ❌ |
| **信任模型** | `hasTrustDialogAccepted` + 外部 include 审批 | `folderTrust` 布尔值 |
| **Auto Memory** | ✅ `MEMORY.md`（200 行 / 25KB 截断） | ❌ |
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

> 源码: `utils/claudemd.ts`（~2,300 行）

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

---

## 4. 逐维度对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 层级数 | 6（含 AutoMem + TeamMem） | 3 |
| 文件名 | 固定（CLAUDE.md / CLAUDE.local.md） | 可配置 |
| @include 深度 | 5 | 5 |
| @include 格式 | 单一（内联） | 两种（Tree / Flat） |
| HTML 注释剥离 | ✅ | ❌ |
| Frontmatter | ✅ paths + description + allowed-tools | ❌ |
| 条件规则 | ✅（.claude/rules/*.md + paths: glob） | ❌ |
| 急/惰加载 | ✅（无 paths 急加载，有 paths 惰加载） | 全部急加载 |
| 信任模型 | 多级（Dialog + External Include 审批） | 布尔值 |
| Auto Memory | ✅（MEMORY.md，200 行截断） | ❌ |
| Team Memory | ✅（API 同步） | ❌ |
| Hook | ✅ InstructionsLoaded | ❌ |
| 排除机制 | claudeMdExcludes 设置 | .qwenignore 文件 |
| Worktree 处理 | ✅ 去重 | ❌ |

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
| `utils/claudemd.ts` | ~2,300 | 指令发现/解析/@include/注释剥离 |
| `utils/frontmatterParser.ts` | ~279 | Frontmatter 解析（paths/description） |
| `context.ts` | L155-L189 | 系统提示注入 |
| `memdir/memdir.ts` | ~103 | MEMORY.md 加载与截断 |
| `utils/config.ts` | L697-L762 | Trust Dialog 逻辑 |

### Qwen Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `packages/core/src/utils/memoryDiscovery.ts` | ~217 | 文件发现（3 层） |
| `packages/core/src/utils/memoryImportProcessor.ts` | ~417 | @include 处理（Tree/Flat 格式） |
| `packages/core/src/tools/memoryTool.ts` | ~113 | 文件名配置与存储路径 |
| `packages/core/src/core/prompts.ts` | L78-L118 | 系统提示注入 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码（Claude Code v2.1.89、Qwen Code v0.15.0），后续版本可能已变更。
