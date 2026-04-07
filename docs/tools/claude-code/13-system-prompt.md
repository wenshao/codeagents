# 13. 系统提示构建——开发者参考

> Claude Code 的系统提示不是一段静态文本——它是由 20+ 个动态段落、Feature Flag 条件分支、Prompt Cache 分区标记组成的**运行时拼装系统**。理解这套机制对优化 Qwen Code 的 prompt 效率至关重要。
>
> **Qwen Code 对标**：Qwen Code 的系统提示相对简单（`prompts.ts` ~1000 行 vs Claude Code ~56,000 行）。Claude Code 的 Prompt Cache 分区、动态段落缓存、`<system-reminder>` 注入模式是主要参考。

## 一、为什么系统提示构建这么复杂

### 问题定义

系统提示占 Code Agent 每次 API 调用 token 的 **20-40%**。一个典型的系统提示包含：

| 组成部分 | 大小 | 变化频率 |
|---------|------|---------|
| 行为指令（角色/规则/语气） | ~3K token | 从不变 |
| 工具 Schema（42 个工具） | ~10K token | 工具动态加载时变 |
| CLAUDE.md 项目指令 | ~2K token | 项目切换时变 |
| Git 上下文（分支/状态/提交） | ~500 token | 每轮变 |
| 记忆（MEMORY.md） | ~1K token | 会话间变 |
| 环境信息（平台/shell/日期） | ~200 token | 每轮变 |

**核心矛盾**：系统提示的大部分内容**不变**（行为指令、工具 Schema），但 Anthropic API 的 Prompt Cache 只有当前缀完全匹配时才命中。一旦 Git 状态变了（前缀不同），**整个系统提示的缓存都失效**。

### Claude Code 的解决方案：静态/动态分区

```
┌─────────────────────────────────────────────┐
│  静态前缀（Cache Scope: global）            │
│  行为指令 + 工具描述 + 通用规则              │
│  ────── 跨组织共享，所有用户命中同一缓存 ──── │
├─ SYSTEM_PROMPT_DYNAMIC_BOUNDARY ────────────┤
│  动态后缀（Cache Scope: org 或无缓存）       │
│  Git 状态 + CLAUDE.md + 记忆 + 环境 + 语言   │
│  ────── 每轮可能变化，不影响静态前缀缓存 ──── │
└─────────────────────────────────────────────┘
```

**效果**：静态前缀（~13K token）的缓存**永远不被动态内容打破**。API 成本降低 50-80%（缓存 token 价格为正常价格的 1/10）。

## 二、构建流程

### 2.1 主入口

源码: `constants/prompts.ts`，核心函数 `getSystemPrompt()`

```
getSystemPrompt(tools, model, additionalDirs, mcpClients)
  │
  ├─ 静态段落（缓存到 /clear 或 /compact）
  │   ├─ 角色定义（"You are Claude Code..."）
  │   ├─ 行为规则（任务执行、安全、代码风格）
  │   ├─ 工具使用指南
  │   ├─ 语气风格
  │   └─ 输出效率
  │
  ├─ ── SYSTEM_PROMPT_DYNAMIC_BOUNDARY ──
  │
  ├─ 动态段落（每轮可能变化）
  │   ├─ 会话特定指导
  │   ├─ 记忆提示（MEMORY.md）
  │   ├─ 环境信息（平台/shell/日期）
  │   ├─ 语言设置
  │   ├─ 输出风格
  │   ├─ MCP 指令
  │   ├─ Scratchpad
  │   ├─ Function result clearing
  │   └─ Token 预算
  │
  └─ 返回 string[]
```

### 2.2 段落缓存机制

源码: `constants/systemPromptSections.ts`

两种段落类型：

| 类型 | 缓存 | 使用场景 |
|------|------|---------|
| `systemPromptSection(name, compute)` | 缓存直到 `/clear` 或 `/compact` | 大部分段落 |
| `DANGEROUS_uncachedSystemPromptSection(name, compute, reason)` | **每轮重算**，可能破坏缓存 | Git 状态等极易变化的内容 |

**开发者启示**：Qwen Code 当前没有段落级缓存。每轮 API 调用都重新构建完整系统提示。引入段落缓存（`useMemo` 语义）可以减少 prompt 构建的 CPU 和 GC 开销。

### 2.3 CLAUDE.md 注入方式

**关键设计**：CLAUDE.md 内容**不在系统提示中**，而是作为**第一条用户消息**注入，包裹在 `<system-reminder>` 标签中：

```typescript
// api.ts: prependUserContext()
createUserMessage({
  content: `<system-reminder>
As you answer the user's questions, you can use the following context:
# claudeMd
${claudeMdContent}
# currentDate
Today's date is ${date}.

IMPORTANT: this context may or may not be relevant...
</system-reminder>`,
  isMeta: true,  // UI 不显示
})
```

**为什么不放在系统提示中？**
1. 系统提示的静态前缀需要跨用户共享缓存——CLAUDE.md 是项目特定的，会打破缓存
2. 用户消息的缓存粒度更细（org-level），不影响全局缓存
3. `isMeta: true` 确保这条消息不在对话 UI 中显示

### 2.4 Git 上下文注入

源码: `context.ts`，函数 `getGitStatus()`

```typescript
// 并行执行 5 个 git 命令：
const [branch, mainBranch, status, log, userName] = await Promise.all([
  getBranch(),
  getDefaultBranch(),
  execFileNoThrow('git', ['--no-optional-locks', 'status', '--short']),
  execFileNoThrow('git', ['--no-optional-locks', 'log', '--oneline', '-n', '5']),
  execFileNoThrow('git', ['config', 'user.name']),
])
```

**注入位置**：系统提示的末尾（动态区域），通过 `appendSystemContext()` 追加。

**`--no-optional-locks` 的原因**：避免 `git status` 获取仓库锁（防止阻塞其他 git 操作）。

### 2.5 Feature Flag 条件段落

```typescript
// prompts.ts - 编译时条件（build-time DCE）
...(feature('PROACTIVE') || feature('KAIROS')
  ? [getProactiveSection()]
  : [])

// 运行时条件
...(process.env.USER_TYPE === 'ant'
  ? [getAntModelOverrideSection()]
  : [])
```

22 个 Feature Flag 控制系统提示的不同段落——外部构建中，Kairos/Proactive 相关的提示段落被完全移除。

## 三、Prompt Cache 优化详解

### 3.1 三种缓存模式

源码: `utils/api.ts`，函数 `splitSysPromptPrefix()`

| 模式 | 使用条件 | 静态前缀缓存 | 动态内容缓存 |
|------|---------|------------|------------|
| Global Cache | 1P（Anthropic API 直连） | `scope: 'global'`（跨组织共享） | `scope: null`（不缓存） |
| Org Cache | 有 MCP 工具时 | `scope: 'org'`（组织级） | `scope: 'org'` |
| Default Org | 3P Provider | `scope: 'org'` | `scope: 'org'` |

### 3.2 工具 Schema 的缓存策略

工具 Schema 通过 `toolToAPISchema()` 构建，支持 `cache_control` 标记：

- 核心工具的 Schema 带 `cache_control`（缓存命中率高）
- 动态加载的工具（ToolSearch 激活的）不带 `cache_control`（避免污染缓存）
- MCP 工具的 Schema 在 `defer_loading` 模式下不发送

### 3.3 缓存命中率的实际影响

```
每次 API 调用的 token 成本构成：
┌──────────────────────────┬─────────┬──────────┐
│ 组件                      │ Token   │ 缓存状态  │
├──────────────────────────┼─────────┼──────────┤
│ 系统提示（静态前缀）       │ ~13,000 │ ✓ 全局缓存 │
│ 系统提示（动态后缀）       │ ~2,000  │ × 不缓存   │
│ 工具 Schema              │ ~8,000  │ ✓ 组织缓存 │
│ CLAUDE.md（用户消息）     │ ~2,000  │ ✓ 组织缓存 │
│ 对话历史                  │ 变化    │ 部分缓存   │
├──────────────────────────┼─────────┼──────────┤
│ 缓存命中的 token           │ ~23,000 │ 1/10 价格  │
│ 未缓存的 token             │ ~2,000  │ 全价       │
└──────────────────────────┴─────────┴──────────┘
```

## 四、竞品系统提示对比

| Agent | 系统提示构建 | Prompt Cache | CLAUDE.md 等价物 |
|-------|-------------|-------------|-----------------|
| **Claude Code** | 动态拼装（~56K 行代码） | 静态/动态分区 + global/org 缓存 | CLAUDE.md（用户消息注入） |
| **Gemini CLI** | `PromptProvider.getCoreSystemPrompt()` | 无显式 Prompt Cache 管理 | GEMINI.md |
| **Qwen Code** | `prompts.ts`（~1K 行） | 基础缓存 | QWEN.md |
| **Copilot CLI** | agent YAML 定义 | 依赖 API 端缓存 | copilot-instructions.md |

## 五、Qwen Code 改进建议

### P0：系统提示静态/动态分区

将不变的行为指令和工具 Schema 放在前缀，Git 状态等易变内容放在后缀。确保前缀内容的字节序列稳定→缓存命中率最大化。

### P1：段落级缓存

对不频繁变化的段落（工具 Schema、行为规则）使用 `useMemo` 语义缓存，避免每轮重新序列化。

### P1：CLAUDE.md → QWEN.md 用户消息注入

将 QWEN.md 内容从系统提示移到第一条用户消息（`<system-reminder>` 标签），避免项目特定内容打破系统提示缓存。

### P2：Git 上下文并行获取

参考 Claude Code 的 `Promise.all()` 并行执行 5 个 git 命令模式，减少上下文收集延迟。
