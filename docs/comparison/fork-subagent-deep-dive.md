# Fork 子代理 Deep-Dive

> 当 Agent 需要将任务委派给子代理时，如何共享完整的对话上下文并最大化 prompt cache 命中率？本文基于 Claude Code（v2.1.89 源码分析）和 Qwen Code（v0.15.0 开源）的源码分析，深度介绍 Claude Code 的隐式 Fork Subagent 机制及其与 Qwen Code Agent 工具的架构差异。

---

## 1. 问题定义

AI Agent 需要将复杂任务拆分给多个子代理并行处理。核心挑战：

| 挑战 | 普通子代理 | Fork 子代理 |
|------|-----------|-----------|
| 上下文传递 | ❌ 子代理从头开始，需重新描述上下文 | ✅ 继承父代理完整对话历史 |
| Prompt Cache | ❌ 每个子代理独立请求前缀，无法共享 | ✅ 字节一致前缀，N 个子代理共享一份缓存 |
| 成本 | 线性增长（N × 完整 prompt 费用） | 近常数（1 × 缓存费用 + N × 增量费用） |
| 用户体验 | 需指定 `subagent_type` | 省略即自动 fork |

---

## 2. Claude Code：隐式 Fork 机制

### 2.1 触发条件

```typescript
// 源码: tools/AgentTool/forkSubagent.ts#L32-L39
function isForkSubagentEnabled(): boolean {
  if (feature('FORK_SUBAGENT')) {         // 编译时 feature flag
    if (isCoordinatorMode()) return false   // 与 Coordinator 模式互斥
    if (getIsNonInteractiveSession()) return false  // SDK/API 模式禁用
    return true
  }
  return false
}
```

### 2.2 决策树

```
Agent(prompt, subagent_type?)
  │
  ├─ subagent_type 已指定 → 使用指定类型（常规路径，不 fork）
  │
  └─ subagent_type 未指定
      ├─ isForkSubagentEnabled() = true
      │     ├─ 已在 fork 子代理内？ → 报错（递归防护）
      │     └─ 否 → FORK 路径
      │
      └─ isForkSubagentEnabled() = false → 默认 general-purpose Agent
```

> 源码: `tools/AgentTool/AgentTool.tsx#L318-L356`

### 2.3 FORK_AGENT 定义

```typescript
// 源码: forkSubagent.ts#L60-L71
const FORK_AGENT = {
  agentType: 'fork',
  tools: ['*'],              // 继承父代理完整工具集
  maxTurns: 200,
  model: 'inherit',          // 继承父代理模型（上下文长度一致）
  permissionMode: 'bubble',  // 权限提示冒泡到父终端
  getSystemPrompt: () => '', // 空——直接传父代理已渲染的系统提示字节
}
```

**为何 `getSystemPrompt` 为空？** Fork 不重新计算系统提示，而是通过 `override.systemPrompt` 直接传递父代理的 `renderedSystemPrompt` 字节。这避免 GrowthBook feature flag 在子进程中产生不同值导致缓存失效。

---

## 3. 消息构建：Prompt Cache 共享的核心

### 3.1 构建流程

```typescript
// 源码: forkSubagent.ts#L107-L169
function buildForkedMessages(directive, assistantMessage): Message[] {
  // 1. 克隆完整 assistant 消息（thinking + text + 所有 tool_use）
  // 2. 为每个 tool_use 创建 tool_result，文本完全相同
  // 3. 追加 fork 指令
}
```

### 3.2 消息结构

```
父代理 API 请求:
  system: [父代理已渲染的系统提示字节]
  tools:  [tool_a, tool_b, tool_c]
  messages: [
    user(上下文...),
    assistant(tool_use₁, tool_use₂, text),
    user(result₁, result₂),
    ...更多轮对话...
  ]

Fork 子代理 API 请求:
  system: [相同字节]                    ← override.systemPrompt 传入
  tools:  [tool_a, tool_b, tool_c]     ← useExactTools=true，父代理原始数组
  messages: [
    user(上下文...),                    ← 相同
    assistant(tool_use₁, tool_use₂),   ← 相同
    user(                               ← 新 user 消息
      tool_result("Fork started — processing in background"),  ← 统一占位文本
      tool_result("Fork started — processing in background"),  ← 所有 fork 相同
      text(<fork-boilerplate>你的指令...</fork-boilerplate>)   ← 唯一不同的部分
    )
  ]
```

### 3.3 为何占位文本必须相同

```
Cache Key = hash(system_bytes + tool_serialization + messages_prefix + thinking_config)

Fork A: messages = [...共享前缀..., user(result_A, directive_A)]
Fork B: messages = [...共享前缀..., user(result_B, directive_B)]
                                          ↑
                             如果 result_A ≠ result_B → cache key 不同 → cache miss

解决方案: result_A = result_B = "Fork started — processing in background"
→ messages_prefix 完全一致 → cache key 相同 → cache hit ✓
→ 只有 directive 部分产生新 token 费用
```

> 源码: `forkSubagent.ts#L93`（占位常量）

### 3.4 缓存一致性的四个保证

| 保证 | 机制 | 源码 |
|------|------|------|
| **系统提示** | 直接传父代理已渲染字节 | `AgentTool.tsx#L495-L512`: `override.systemPrompt` |
| **工具列表** | 传父代理原始数组，跳过过滤 | `AgentTool.tsx#L603`: `useExactTools: true` |
| **消息历史** | 所有 fork 用相同占位文本 | `forkSubagent.ts#L93` |
| **Thinking 配置** | 从父代理继承 | `runAgent.ts#L668-L695`: `toolUseContext.options.thinkingConfig` |

---

## 4. Fork 子代理的 10 条铁律

通过 `<fork-boilerplate>` XML 标签注入子代理（源码: `forkSubagent.ts#L171-L198`）：

| # | 规则 | 目的 |
|:-:|------|------|
| 1 | 系统提示说"默认 fork"——忽略它，你已经是 fork。**不要生成子代理** | 防止递归 |
| 2 | 不要对话，不要提问 | 专注执行 |
| 3 | 不要发表评论或元叙述 | 减少无用输出 |
| 4 | 直接使用工具（Bash/Read/Write 等），保持沉默 | 行动优先 |
| 5 | 修改文件后先 commit，报告中包含 commit hash | 可追溯性 |
| 6 | 工具调用之间不要输出文本 | 减少 token |
| 7 | 严格在指令范围内工作 | 防止范围蔓延 |
| 8 | 报告 < 500 词 | 简洁 |
| 9 | 响应必须以 "Scope:" 开头 | 结构化输出 |
| 10 | 报告结构化事实后停止 | 明确终止 |

**强制输出格式**：

```
Scope: <一句话描述任务范围>
Result: <发现/结果>
Key files: <相关文件路径>
Files changed: <修改的文件 + commit hash>
Issues: <发现的问题>
```

---

## 5. 递归防护（双层）

```typescript
// 层 1: querySource 检查（主路径，不受 autocompact 影响）
// 源码: AgentTool.tsx#L332-L334
if (querySource === 'agent:builtin:fork') {
  throw new Error('Fork is not available inside a forked worker')
}

// 层 2: 消息扫描（备份，捕获 querySource 被清理的边界 case）
// 源码: forkSubagent.ts#L78-L89
function isInForkChild(messages): boolean {
  return messages.some(m => m.message.content.some(
    block => block.type === 'text' && block.text.includes('<fork-boilerplate>')
  ))
}
```

**为何需要两层？** Fork 子代理保留 Agent 工具（用于缓存一致），因此理论上可递归调用。`querySource` 是快速路径；消息扫描是安全网。

---

## 6. Worktree 隔离

当 `isolation: 'worktree'` 时，fork 子代理在独立 Git worktree 中运行：

```typescript
// 源码: AgentTool.tsx#L568-L602
if (effectiveIsolation === 'worktree') {
  const slug = `agent-${earlyAgentId.slice(0, 8)}`
  worktreeInfo = await createAgentWorktree(slug)
}
// Fork + worktree: 注入路径翻译提示
if (isForkPath && worktreeInfo) {
  promptMessages.push(createUserMessage({
    content: buildWorktreeNotice(getCwd(), worktreeInfo.worktreePath)
  }))
}
```

**Worktree Notice 告诉子代理**：
- 继承上下文中的路径指向父目录
- 需翻译到 worktree 路径
- 修改文件前先重新 Read（父代理可能已修改）
- 变更隔离在 worktree 内，不影响父代理

**生命周期**：
- 子代理完成后检查 worktree 是否有变更
- 有变更 → 保留 worktree 供检查
- 无变更 → 自动删除 worktree 和分支

---

## 7. 异步执行与任务通知

```typescript
// 源码: AgentTool.tsx#L555-L567
// Fork 启用时，所有 Agent 生成强制异步
const forceAsync = isForkSubagentEnabled()
const shouldRunAsync = run_in_background || forceAsync || ...
```

**结果交付**：子代理通过 `<task-notification>` XML 向父代理报告：

```xml
<task-notification>
  <task-id>{agentId}</task-id>
  <status>completed</status>
  <summary>5-10 词摘要</summary>
  <result>完整结果（遵循 Scope/Result/Key files 格式）</result>
  <worktree>/path/to/worktree</worktree>
</task-notification>
```

---

## 8. 执行引擎集成

```typescript
// 源码: tools/AgentTool/runAgent.ts#L368-L378
// Fork 特有: 过滤不完整工具调用，克隆文件状态缓存
const contextMessages = forkContextMessages
  ? filterIncompleteToolCalls(forkContextMessages)  // 防止 API 错误
  : []
const initialMessages = [...contextMessages, ...promptMessages]
const agentReadFileState = forkContextMessages !== undefined
  ? cloneFileStateCache(toolUseContext.readFileState)  // 继承父缓存
  : createFileStateCacheWithSizeLimit(READ_FILE_STATE_CACHE_SIZE)
```

```typescript
// 源码: runAgent.ts#L500-L502
// Fork 保留父工具数组（跳过过滤）
const resolvedTools = useExactTools
  ? availableTools          // 父代理原始数组 → 缓存一致
  : resolveAgentTools(...)  // 按代理定义重新过滤
```

---

## 9. Qwen Code 对比

| 维度 | Claude Code Fork | Qwen Code Agent |
|------|-----------------|-----------------|
| **`subagent_type`** | 可选（省略时隐式 fork） | **必填** |
| **上下文继承** | ✅ 完整对话历史 + 系统提示 + 工具集 + 文件缓存 | ❌ 每个子代理从头开始 |
| **Prompt Cache 共享** | ✅ 字节一致前缀 → N 个子代理共享缓存 | ❌ 每个子代理独立缓存 |
| **递归防护** | ✅ 双层（querySource + 消息扫描） | ❌ 不需要（不支持 fork） |
| **工具集传递** | `useExactTools: true`（跳过过滤） | 按代理定义重新过滤 |
| **Thinking 继承** | ✅ 继承父 `thinkingConfig` | 独立配置 |
| **执行模式** | 强制异步（`forceAsync = true`） | 异步 |
| **行为约束** | 10 条铁律 + 结构化输出格式 | 代理定义中的 `systemPrompt` |
| **Worktree 隔离** | ✅ 可选 | ✅（Arena 模式下） |

### Qwen Code Agent 工具入口

```typescript
// 源码: qwen-code/packages/core/src/tools/agent.ts
interface AgentParams {
  description: string
  prompt: string
  subagent_type: string  // 必填——无法隐式 fork
}
```

**SubagentManager 搜索优先级**（源码: `subagent-manager.ts#L186-L217`）：

```
Session 级 → Project 级 → User 级 → Extension 级 → Built-in
```

每个子代理通过 `createAgentHeadless()` 独立启动，不继承父代理上下文。

---

## 10. 成本模型对比

假设父代理有 100K token 的对话上下文，需要 fork 5 个子代理：

| 模型 | 输入 Token 总消耗 | 缓存行为 |
|------|:--:|------|
| **Claude Code Fork** | ~100K（1× 缓存创建）+ 5 × ~1K（增量指令） ≈ **105K** | 缓存命中率 ~95% |
| **Qwen Code Agent** | 5 × ~100K（各自独立上下文重建）≈ **500K** | 无缓存共享 |
| **无上下文传递** | 5 × ~5K（简短指令）≈ **25K** | — |

Fork 模型在保留完整上下文的同时，成本仅比无上下文传递高 ~4×，而非 20×。

---

## 11. 关键源码文件

### Claude Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `tools/AgentTool/forkSubagent.ts` | 211 | Fork 核心：gate/消息构建/铁律/递归防护/worktree notice |
| `tools/AgentTool/AgentTool.tsx` | 1,397 | Agent 入口：fork vs 常规决策树/系统提示分支/异步执行 |
| `tools/AgentTool/runAgent.ts` | 973 | 执行引擎：上下文组装/工具解析/Thinking 继承/查询循环 |
| `utils/forkedAgent.ts` | 690 | CacheSafeParams 存储/子代理上下文创建/forked query 循环 |
| `tools/AgentTool/loadAgentsDir.ts` | 755 | Agent 定义加载（FORK_AGENT 不在此列——运行时合成） |

### Qwen Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `packages/core/src/tools/agent.ts` | 676 | Agent 工具（`subagent_type` 必填，无 fork） |
| `packages/core/src/subagents/subagent-manager.ts` | 1,053 | 子代理管理器（5 级搜索） |
| `packages/core/src/subagents/builtin-agents.ts` | 159 | 内置代理（general-purpose, Explore） |

---

## 12. 设计启示

1. **Prompt Cache 是 fork 的核心经济学动力**：没有缓存共享，fork 的成本与独立子代理相同。四个一致性保证（系统提示/工具/消息/thinking）缺一不可
2. **隐式优于显式**：省略 `subagent_type` 即 fork——降低用户认知负担，让模型自然地委派任务
3. **10 条铁律是必要的约束**：fork 子代理继承完整工具集（包括 Agent 工具），没有铁律会导致递归 fork 和范围蔓延
4. **异步强制**使 fork 子代理不阻塞父代理——用户可继续与父代理交互，子代理在后台完成
5. **占位文本统一**是一个精巧的缓存优化——不同文本会破坏缓存前缀一致性

> **免责声明**: 以上分析基于 2026 年 Q1 源码（Claude Code v2.1.89、Qwen Code v0.15.0），后续版本可能已变更。
