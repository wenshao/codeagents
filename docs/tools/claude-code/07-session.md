# 7. 会话、记忆与上下文管理——开发者参考

> Claude Code 最核心的工程优势之一：5 层递增压缩、CLAUDE.md 分层记忆、Auto Dream 自动整理、Team Memory 团队同步、崩溃恢复。这是 Qwen Code 与 Claude Code 差距最大的领域。
>
> **Qwen Code 对标**：上下文压缩（仅单一 70% 手动压缩 vs 5 层自动）、记忆系统（简单笔记 vs CLAUDE.md + Auto Dream）、崩溃恢复（无 vs 3 种检测 + 合成续行）
>
> **计数规则**：源码行数基于 TypeScript 文件的 `wc -l` 统计。7.1.1 表格「目录总规模」列为子系统所有文件合计；括号内为核心文件精确 LOC。全文 ~73,000 行为所有 session/memory 相关目录（含 Token 管理、对话恢复、并发管理等辅助模块）的总计。

## 7.1 架构总览

### 7.1.1 子系统全景

| 子系统 | 目录总规模 | 核心文件（单文件 LOC） | 职责 |
|--------|-----------|----------------------|------|
| **会话存储** | ~9,938 LOC | `utils/sessionStorage.ts` (5,105) | JSONL 持久化、会话恢复、并发管理 |
| **上下文压缩** | ~3,960 LOC | `services/compact/compact.ts` (1,706) | 5 层递增压缩策略 |
| **Token 管理** | ~3,327 LOC | `utils/analyzeContext.ts` (1,382) | 预算分配、用量估算、阈值告警 |
| **CLAUDE.md 记忆** | ~1,876 LOC | `utils/claudemd.ts` (1,480) | 6 层发现、`@include` 指令、条件加载 |
| **Memdir 系统** | ~1,736 LOC | `memdir/memdir.ts` (507) | 记忆目录管理、路径解析 |
| **自动记忆提取** | ~769 LOC | `services/extractMemories/extractMemories.ts` (616) | 对话结束后后台提取记忆 |
| **SessionMemory** | ~1,026 LOC | `services/SessionMemory/sessionMemory.ts` (495) + `prompts.ts` (324) + `utils.ts` (207) | 轻量级会话内记忆缓存 |
| **autoDream** | ~550 LOC | `services/autoDream/autoDream.ts` (325) | 后台记忆整合（24h + 5 会话门控） |
| **团队记忆同步** | ~2,167 LOC | `services/teamMemorySync/index.ts` (1,257) | 本地↔云端双向同步 |
| **Worktree** | ~2,888 LOC | `utils/worktree.ts` (1,519) | Git worktree 隔离会话 |
| **文件检查点** | ~1,116 LOC | `utils/fileHistory.ts` (1,116) | 文件级快照/回退 |

> **计数说明**：「目录总规模」是该子系统所有文件的 LOC 合计（含辅助文件、类型定义、UI 组件等）。「核心文件」是其中最大的单一文件，括号内为其精确 LOC。

### 7.1.2 会话生命周期

```
┌─────────────┐     ┌─────────────────────────────┐     ┌─────────────┐
│  创建         │     │  活跃                         │     │  恢复/归档   │
│             │     │                             │     │             │
│ 懒创建 JSONL  │────▶│ 追加消息                      │────▶│ --resume    │
│ 注册 PID      │     │ PID 状态更新                  │     │ --continue  │
│ 初始化记忆    │     │ 工具结果持久化                 │     │ --fork      │
│             │     │  ┌──────────────────┐        │     │ 对话链回放   │
│             │     │  │ 上下文压缩（异步） │        │     │             │
│             │     │  │ 5层递增 / Token预算│        │     │             │
│             │     │  └──────────────────┘        │     │             │
└─────────────┘     └─────────────────────────────┘     └─────────────┘
```

**关键设计**：
- 会话文件**懒创建**：第一条 user/assistant 消息时才创建 JSONL，之前元数据缓存在内存 `pendingEntries` 中
- **Append-only JSONL**：消息只追加、不原地更新。删除使用尾部拼接（tail-splice）提高效率
- **PID 文件并发管理**：`~/.claude/sessions/{pid}.json` 跟踪运行中会话，`claude ps` 可查看
- **上下文压缩**是活跃阶段的**异步子任务**，不是独立的线性阶段——在 token 用量超过阈值时自动触发，也可通过 `/compact` 手动触发

## 7.2 会话存储

### 7.2.1 存储格式

源码：`utils/sessionStorage.ts`

**会话文件路径**：`~/.claude/projects/{sanitized_project_path}/{sessionId}.jsonl`

每行一个 JSON 条目，核心字段：

```json
{
  "type": "user|assistant|attachment|system|last-prompt|custom-title|tag|...",
  "uuid": "...",
  "parentUuid": "...",
  "timestamp": "...",
  "sessionId": "..."
}
```

**元数据条目类型**（通过 `reAppendSessionMetadata()` 持久化）：

| 条目类型 | 用途 |
|---------|------|
| `last-prompt` | 最后用户提示文本 |
| `custom-title` | 用户/AI 设置的会话标题 |
| `tag` | 会话标签 |
| `agent-name` / `agent-color` / `agent-setting` | Agent 上下文 |
| `mode` | `coordinator` vs `normal` 模式 |
| `worktree-state` | Worktree 会话状态（三态：undefined/null/object） |
| `pr-link` | 关联的 PR 元数据 |
| `file-history-snapshot` | 文件检查点快照 |
| `content-replacement` | 缓存优化替换记录 |

**子代理转录路径**：`{projectDir}/{sessionId}/subagents/agent-{agentId}.jsonl`

**文件权限**：`0o600`（仅所有者可读写），目录 `0o700`

### 7.2.2 关键常量

源码：`utils/sessionStorage.ts`

| 常量 | 值 | 用途 |
|------|---|------|
| `MAX_TRANSCRIPT_READ_BYTES` | 50 MB | 防止 OOM |
| `MAX_TOMBSTONE_REWRITE_BYTES` | 50 MB | 尾部拼接安全限制 |
| `FLUSH_INTERVAL_MS` | 100 ms | 写队列排空间隔 |
| `MAX_CHUNK_BYTES` | 100 MB | 单次写入最大块 |

### 7.2.3 Project 单例与写队列

源码：`utils/sessionStorage.ts` — `Project` 类

`Project` 是管理所有写入的单例，采用**写队列模式**：
- 条目缓存在 `writeQueues`（按文件的 Map）
- 每 100ms 通过 `scheduleDrain()` / `drainWriteQueue()` 排空
- 支持等待排空的 `flushSessionStorage()`

缓存的元数据字段：
```
currentSessionTag, currentSessionTitle, currentSessionAgentName,
currentSessionAgentColor, currentSessionLastPrompt,
currentSessionAgentSetting, currentSessionMode ('coordinator' | 'normal'),
currentSessionWorktree (三态), currentSessionPrNumber, ...
```

### 7.2.4 消息链构建

源码：`utils/sessionStorage.ts` — `buildConversationChain(byUuid, tip)`

从叶子节点沿 `parentUuid` 链回溯到根节点，构建完整的对话树。`progress` 条目被排除在链外——它们是 UI 临时状态，包含会导致恢复时产生链分叉（bugs #14373, #23537）。

### 7.2.5 轻量元数据读取

源码：`utils/sessionStoragePortable.ts`

`readLiteMetadata()` 只读取 JSONL 文件最后 ~64KB 的尾部窗口提取元数据，无需扫描全文件。会话退出时，`reAppendSessionMetadata()` 将元数据重写到 EOF，确保尾部窗口可找到最新元数据。

> **设计理由**：对于长会话（数万条消息），全文件扫描可能需要数秒。尾部窗口方案将元数据读取降至毫秒级。

## 7.3 会话恢复

### 7.3.1 恢复入口

```bash
# 恢复最近会话
claude --resume

# 恢复指定会话
claude --resume <session-id>

# 继续上次对话
claude -c

# 恢复并创建新会话 ID（不覆盖原会话）
claude --resume <session-id> --fork-session

# 关联 PR 恢复
claude --from-pr 123
```

### 7.3.2 恢复流程

源码：`utils/conversationRecovery.ts` → `utils/sessionRestore.ts`

```
loadConversationForResume(source)
  ├── 1. 定位 JSONL 文件（最新 / session-id / 预加载）
  ├── 2. 反序列化 + 过滤
  │     ├── migrateLegacyAttachmentTypes()    # new_file→file, new_directory→directory
  │     ├── filterUnresolvedToolUses()        # 移除未配对的 tool_use/tool_result
  │     ├── filterOrphanedThinkingOnlyMessages()
  │     └── filterWhitespaceOnlyAssistantMessages()
  ├── 3. 回合中断检测 (detectTurnInterruption)
  │     ├── 'none': 最后一轮已完成
  │     ├── 'interrupted_prompt': 用户已发送但模型未响应
  │     └── 'interrupted_turn': 模型执行中中断 → 注入 "Continue from where you left off."
  ├── 4. 恢复 Skill 状态
  └── 5. 触发 SessionStart hooks (resume type)

processResumedConversation(result)
  ├── 1. 匹配 coordinator/normal 模式
  ├── 2. 设置 session ID（或 fork 新 ID）
  ├── 3. 恢复会话元数据（标题、标签、Agent、Worktree、PR）
  ├── 4. 恢复 Worktree 目录（chdir）
  ├── 5. 恢复 Agent 定义和模型覆盖
  └── 6. 更新 PID 文件
```

### 7.3.3 回合中断检测

源码：`utils/conversationRecovery.ts` — `detectTurnInterruption()`

| 中断类型 | 判定条件 | 恢复行为 |
|---------|---------|---------|
| `none` | 最后一条是 assistant/system/meta | 直接恢复 |
| `interrupted_prompt` | 最后一条是普通用户消息 | 注入 "Continue from where you left off." |
| `interrupted_turn` | 最后一条是 `tool_result` 或 `attachment` | 转为 `interrupted_prompt` 并注入续行消息 |

**特殊处理**：
- **Brief 模式**：`SendUserMessage` 的 tool_result 是终端状态（回合已完成），不会误判为中断
- **API 错误消息**：在查找最后一条回合相关消息时被跳过

### 7.3.4 跨项目恢复

源码：`utils/crossProjectResume.ts`

当 `--resume` 指定的会话属于不同项目目录时，系统检测跨项目情况并区分处理：
- **同 repo worktree**：直接恢复，无需切换目录
- **不同项目**：返回 `cd '/path' && claude --resume <sessionId>` 命令，由调用方决定是否执行

> **注**：Worktree 检测当前仅对 `USER_TYPE === 'ant'` 用户启用（分阶段推送）。非 ant 用户始终走命令提示路径。

## 7.4 上下文压缩（5 层递增策略）

上下文压缩是 Claude Code 最复杂的子系统之一，按成本递增分为 5 层，每一层在上一层无法释放足够空间时触发。

### 7.4.1 压缩层次总览

| 层级 | 机制 | 触发时机 | 信息损失 | 源码 |
|------|------|---------|---------|------|
| **L1: 缓存编辑微压缩** | `cache_edits` API 删除旧工具结果 | 每次 API 调用前（仅 Ant） | 工具输出文本 | `services/compact/microCompact.ts` |
| **L2: 时间微压缩** | 就地清除过期工具结果 | 服务器缓存已过期时 | 工具输出文本 | `services/compact/microCompact.ts` |
| **L3: SessionMemory 压缩** | 基于 SessionMemory 裁剪旧消息 | 自动压缩触发后**优先尝试**（与 L4 共享阈值 ~83.5%） | 旧对话轮次 | `services/compact/sessionMemoryCompact.ts` |
| **L4: 完整压缩（摘要）** | Fork 子代理生成摘要替代历史 | L3 失败后、手动 `/compact` | 大部分对话细节 | `services/compact/compact.ts` |
| **L5: 反应式压缩** | API 413 应急压缩 | API 返回 prompt_too_long | 可能严重 | `query.ts` |

### 7.4.2 Token 预算计算

源码：`services/compact/autoCompact.ts`, `utils/tokens.ts`

```
原始上下文窗口:     200,000 tokens（默认模型）
                    1,000,000 tokens（Sonnet 4 / Opus 4-6）

摘要预留:           min(modelMaxOutput, 20,000) tokens
                    (基于 p99.99 = 17,387 tokens)

有效上下文窗口:     rawWindow - summaryReserved
                    = 200,000 - 20,000 = 180,000

自动压缩阈值:       effectiveWindow - 13,000
                    = 180,000 - 13,000 = 167,000 (~83.5%)

警告阈值:           autoCompactThreshold - 20,000
错误阈值:           autoCompactThreshold - 20,000
阻塞限制:           effectiveWindow - 3,000
```

**Token 估算函数** `tokenCountWithEstimation()`（`utils/tokens.ts`）：
- 取最后一次 API 响应的 `usage`（input + output + cache tokens）
- 加上自此之后追加消息的粗略估算
- 按 4/3 比例填充（保守估计）
- 处理并行工具调用：回溯到相同 `message.id` 的第一个兄弟消息

### 7.4.3 L1/L2: 微压缩

源码：`services/compact/microCompact.ts` (531 LOC)

**可压缩工具集合** (`COMPACTABLE_TOOLS`)：FileRead, Shell, Grep, Glob, WebSearch, WebFetch, FileEdit, FileWrite

**L1: 缓存编辑微压缩**（仅 Ant，Feature gate: `CACHED_MICROCOMPACT`）：
- 使用 Anthropic `cache_edits` API，直接在缓存前缀中删除工具结果
- **不使缓存失效**——无需重发内容
- 仅修改缓存删除指令，本地内容不变

**L2: 时间微压缩**：
- 检测距最后一次 assistant 消息的时间差是否超过阈值（服务器缓存已过期）
- 将旧工具结果内容替换为 `[Old tool result content cleared]`
- 由于缓存已过期，清除内容"免费"（不会增加重写成本）

> **设计理由**：微压缩只在主线程（`isMainThreadSource`）执行。源码注释说明："Forked agents (session_memory, prompt_suggestion, etc.) would cause the main thread to try deleting tools that don't exist in its own conversation."

### 7.4.4 L3: SessionMemory 压缩

源码：`services/compact/sessionMemoryCompact.ts` (631 LOC)

实验性结构感知压缩，在完整压缩前优先尝试。

**配置** (`DEFAULT_SM_COMPACT_CONFIG`)：

| 参数 | 默认值 | 用途 |
|------|--------|------|
| `minTokens` | 10,000 | 最少保留 token 数 |
| `minTextBlockMessages` | 5 | 最少保留含文本块消息数 |
| `maxTokens` | 40,000 | 保留 token 硬上限 |

**流程**：
1. 检查 SessionMemory 是否可用且非空
2. 找到上一次压缩的 `lastSummarizedMessageId`
3. 计算裁剪点：向后扩展以满足最低 token/消息约束
4. `adjustIndexToPreserveAPIInvariants()` 确保不拆分 `tool_use`/`tool_result` 对或 thinking 块
5. 创建压缩边界消息并构建后压缩消息

> **设计理由**：`adjustIndexToPreserveAPIInvariants()` 处理一个微妙的流式工件——"streaming yields separate messages per content block (thinking, tool_use, etc.) with the same message.id but different uuids"。如果拆分这些组，会导致 "API error: orphan tool_result references non-existent tool_use"。

### 7.4.5 L4: 完整压缩

源码：`services/compact/compact.ts` (1,706 LOC)

**核心函数**：`compactConversation()`

**完整压缩流程**：

```
1. 执行 PreCompact hooks（合并 hook 指令与用户指令）
2. 构建压缩提示词（prompt.ts）
3. 尝试 forked-agent 路径（复用主线程的 prompt cache）
   ├── 成功 → 使用结果
   └── 失败 → 回退到流式路径（常规 API 调用）
4. 如果响应为 prompt_too_long：
   └── truncateHeadForPTLRetry() 丢弃最旧 API-round 组，重试（最多 3 次）
5. 后压缩清理：
   ├── 清除文件读取缓存
   ├── 重新生成附件（文件、计划、Skill、延迟工具、MCP 指令、Agent 列表）
   └── 执行 SessionStart hooks + PostCompact hooks
6. 重置 cache-break 检测基线（notifyCompaction）
7. 记录遥测（tengu_compact 事件）
```

**关键常量**：

| 常量 | 值 | 用途 |
|------|---|------|
| `POST_COMPACT_MAX_FILES_TO_RESTORE` | 5 | 压缩后重新注入的最大文件数 |
| `POST_COMPACT_TOKEN_BUDGET` | 50,000 | 重新注入文件的总 token 预算 |
| `POST_COMPACT_MAX_TOKENS_PER_FILE` | 5,000 | 每个文件最大 token |
| `POST_COMPACT_SKILLS_TOKEN_BUDGET` | 25,000 | Skill 总预算（~5 个 Skill） |
| `POST_COMPACT_MAX_TOKENS_PER_SKILL` | 5,000 | 每个 Skill 最大 token |
| `MAX_PTL_RETRIES` | 3 | prompt-too-long 重试次数 |

**部分压缩** (`partialCompactConversation`)：
- `'from'` 方向：总结 pivotIndex **之后**的消息（保留 prompt cache 前缀）
- `'up_to'` 方向：总结 pivotIndex **之前**的消息（会失效 cache）

**`CompactionResult` 接口**：
```typescript
interface CompactionResult {
  boundaryMarker: string           // 压缩边界标记
  summaryMessages: Message[]       // 生成的摘要消息（替代被压缩的对话）
  attachments: Attachment[]        // 附件（保留）
  hookResults: HookResult[]        // Hook 执行结果
  messagesToKeep?: Message[]       // 未被压缩的保留消息
  preCompactTokenCount?: number    // 压缩前 token 数
  postCompactTokenCount?: number   // 压缩后 token 数
}
```

### 7.4.6 压缩提示词

源码：`services/compact/prompt.ts` (374 LOC)

**提示词结构**（3 段式）：

```
┌─────────────────────────────────┐
│ NO_TOOLS_PREAMBLE               │ ← "Respond with TEXT ONLY"（置于最前）
│   防止 Sonnet 4.6+ 自适应思考    │   Sonnet 4.6 失败率 2.79% vs 4.5 的 0.01%
├─────────────────────────────────┤
│ <analysis> 暂存块               │ ← 模型组织思路的草稿区
├─────────────────────────────────┤
│ 9 段摘要模板                    │
│  1. Primary Request and Intent  │
│  2. Key Technical Concepts      │
│  3. Files and Code Sections     │
│  4. Errors and Fixes            │
│  5. Problem Solving             │
│  6. All User Messages           │
│  7. Pending Tasks               │
│  8. Current Work                │
│  9. Optional Next Step          │
├─────────────────────────────────┤
│ NO_TOOLS_TRAILER                │ ← 强化"不要调用工具"
└─────────────────────────────────┘
```

`formatCompactSummary()` 处理输出：去除 `<analysis>` 草稿块，将 `<summary>` XML 标签替换为纯文本标题。

### 7.4.7 自动压缩触发

源码：`services/compact/autoCompact.ts` (351 LOC)

**触发门控链**：

```
1. 查询源检查 → 跳过 session_memory/compact 查询（避免死锁）
2. Feature flag → REACTIVE_COMPACT 抑制主动压缩
                  CONTEXT_COLLAPSE 抑制（会与 collapse 竞争）
3. 阈值检查 → tokenCount >= effectiveWindow - 13,000
4. 优先尝试 SessionMemory 压缩
   └── 失败 → 回退到完整压缩
```

**熔断器**：`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`，连续 3 次失败后停止重试。

> **设计理由**：源码注释说明熔断器的起因——"was causing ~250K wasted API calls/day"。在不可恢复的超大会话中，1,279 个会话产生 50+ 次失败。

**环境变量覆盖**：

| 变量 | 用途 |
|------|------|
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | 覆盖有效上下文窗口 |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 按百分比触发 |
| `DISABLE_COMPACT` | 禁用所有压缩 |
| `DISABLE_AUTO_COMPACT` | 禁用自动但保留手动 `/compact` |

### 7.4.8 工具结果持久化

源码：`utils/toolResultStorage.ts`

在压缩之外，大型工具结果通过独立机制管理：

**三层大小管理**：

| 层级 | 机制 | 阈值 |
|------|------|------|
| 单结果持久化 | 超过阈值的结果保存到磁盘，模型收到路径 + 2KB 预览 | `min(tool.maxResultSizeChars, 50,000)` 字符 |
| 聚合消息预算 | 单用户消息内的并行工具结果总预算 | 200,000 字符（`MAX_TOOL_RESULTS_PER_MESSAGE_CHARS`） |
| 微压缩清除 | 就地替换旧工具结果为 `[Old tool result content cleared]` | 时间/缓存过期触发 |

**缓存稳定性**：一旦工具结果被"看过"，它就被"冻结"（要么已替换，要么保持原样）。每次回合重新应用相同决策，以保持 prompt cache 前缀。

### 7.4.9 消息分组

源码：`services/compact/grouping.ts` (63 LOC)

消息按 **API-round 边界**（新的 `assistant.message.id`）分组，确保压缩时不会拆分 `tool_use`/`tool_result` 对。

## 7.5 CLAUDE.md 记忆系统

### 7.5.1 六层发现层级

源码：`utils/claudemd.ts` (1,479 LOC)

| 层级 | 名称 | 路径 | 作用域 | 可排除 |
|------|------|------|--------|--------|
| 1 | Managed | `/etc/claude-code/CLAUDE.md` | 系统管理员策略（所有用户） | ❌ |
| 2 | User | `~/.claude/CLAUDE.md` + `~/.claude/rules/*.md` | 私人全局指令 | ✅ |
| 3 | Project | `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md` | 团队共享（提交到 Git） | ✅ |
| 4 | Local | `CLAUDE.local.md`（项目根目录） | 私人项目级（gitignored） | ✅ |
| 5 | AutoMem | `~/.claude/projects/<slug>/memory/MEMORY.md` | 自动生成 | ❌ |
| 6 | TeamMem | `<autoMemPath>/team/MEMORY.md` | 团队共享（Feature flag） | ❌ |

**加载优先级**：**后加载的优先级更高**——模型对后面出现的内容关注度更高。在 Project/Local 层内，越靠近 CWD 的文件越后加载（优先级越高）。目录遍历从根向 CWD 进行。

> **设计理由**：源码注释说明："Files loaded LATER have HIGHER priority because the model pays more attention to later content." 这与直觉相反（通常先加载的更重要），但符合 LLM 注意力机制的特性。

> **层 3 vs 层 4 说明**：Project 和 Local 虽在同一目录遍历中加载，但它们是独立的层级——使用不同的 `MemoryType` 标记（`'Project'` vs `'Local'`），受不同的 `isSettingSourceEnabled` 门控（`projectSettings` vs `localSettings`），且 Local 不受 worktree 去重影响。

### 7.5.2 `@include` 指令系统

源码：`utils/claudemd.ts`

**语法**：`@path`, `@./relative/path`, `~/home/path`, `@/absolute/path`

**约束**：
- 只在叶子文本节点中工作（不在代码块内）
- 支持递归，最大深度 `MAX_INCLUDE_DEPTH = 5`
- 通过 `processedPaths` 集合防止循环引用
- 支持 70+ 文本文件扩展名（白名单 `TEXT_FILE_EXTENSIONS`）
- HTML 注释被剥离；frontmatter 解析用于基于 glob 的条件规则

**设置源门控**：每个层级受设置源控制——`userSettings`、`projectSettings`、`localSettings` 分别控制各层启用。`claudeMdExcludes` 模式可跳过特定 User/Project/Local 文件（Managed/AutoMem/TeamMem 永不排除）。

### 7.5.3 `getMemoryFiles()` 函数

源码：`utils/claudemd.ts:790`（memoized）

处理顺序：
1. Managed → User → Project/Local（root→CWD 遍历）→ `--add-dir` 目录 → AutoMem → TeamMem
2. 每步调用 `processMemoryFile()` 处理 `@include` 递归
3. `getClaudeMds()` 格式化为统一提示词字符串

**头部声明**：`"Codebase and user instructions are shown below. These instructions OVERRIDE any default behavior."`

每个文件附带描述标签（如 "project instructions, checked into the codebase"）。

### 7.5.4 AutoMem 路径解析

源码：`memdir/paths.ts` (278 LOC)

`getAutoMemPath()` 优先级链：
1. `CLAUDE_COWORK_MEMORY_PATH_OVERRIDE` 环境变量（SDK/Cowork 全路径覆盖）
2. `settings.json` 中的 `autoMemoryDirectory`（仅限信任源：policy/flag/local/user，**排除 projectSettings** 防止注入）
3. 默认：`<memoryBase>/projects/<sanitized-git-root>/memory/`

**路径安全**（`validateMemoryPath()`）：拒绝相对路径、根路径（长度 < 3）、Windows 驱动器根、UNC 路径、空字节、裸 `~` 展开。

### 7.5.5 记忆内容类型

源码：`memdir/memoryTypes.ts` (271 LOC)

| 类型 | 范围 | 内容 |
|------|------|------|
| `user` | 始终私人 | 用户角色、目标、偏好、知识水平 |
| `feedback` | 默认私人；团队级可共享 | 纠正和确认的方法 |
| `project` | 偏向团队 | 进行中的工作、目标、截止日期 |
| `reference` | 通常团队 | 外部系统指针（Linear 项目、Grafana 仪表板） |

**内容排除规则** (`WHAT_NOT_TO_SAVE_SECTION`)：
- 不保存代码模式/架构/文件路径（可从项目状态推导）
- 不保存 git 历史（使用 `git log`/`git blame`）
- 不保存调试解决方案（修复已在代码中）
- 不保存已在 CLAUDE.md 中的内容
- 不保存临时任务细节
- 即使显式保存，这些排除规则仍然适用

**截断限制**：MEMORY.md 上限 200 行 **且** 25KB。

## 7.6 自动记忆提取

### 7.6.1 ExtractMemories（回合结束后台代理）

源码：`services/extractMemories/extractMemories.ts` (616 LOC)

在每个完整查询循环结束时运行（模型产生最终响应且无工具调用时），通过 `handleStopHooks` 触发。

**特性**：
- Feature gate：`tengu_passport_quail`（提取模式）+ `tengu_slate_thimble`（非交互式会话）
- 使用 `runForkedAgent()`——完美复制主对话，共享 prompt cache
- **与主代理互斥**：如果主代理在当轮已写入记忆（`hasMemoryWritesSince()` 检测），后台代理跳过该范围
- 允许工具：FileEdit, FileWrite, FileRead, Glob, Grep, Bash（只读）, REPL
- `createAutoMemCanUseTool()` 工厂约束工具只能操作自动记忆目录

### 7.6.2 SessionMemory（会话内记忆缓存）

源码：`services/SessionMemory/` (3 文件共 1,026 LOC：`sessionMemory.ts` 495 + `prompts.ts` 324 + `sessionMemoryUtils.ts` 207)

轻量级会话内记忆，通过 forked subagent 定期提取。

**特性**：
- Feature gate：`tengu_session_memory` GrowthBook flag
- **初始化阈值**：token 数超过可配置阈值时触发
- **更新阈值**：需要最低 token 增长 + 最低工具调用次数（自上次提取以来）
- 使用 `runForkedAgent()` 共享 prompt cache
- 写入会话作用域记忆文件（`getSessionMemoryPath()`）
- 可自定义：`~/.claude/session-memory/config/template.md` 和 `prompt.md` 覆盖默认提示词

### 7.6.3 autoDream（后台记忆整合）

源码：`services/autoDream/autoDream.ts` (325 LOC)

当时间门控和会话数门控同时通过时，以 forked subagent 运行 `/dream` 提示词。

**双触发门控 + 执行锁**（从最便宜的开始）：

| 阶段 | 类型 | 条件 | 默认值 |
|------|------|------|--------|
| **时间门控** | 触发条件 | 距上次整合 >= minHours | 24h（GrowthBook `tengu_onyx_plover`） |
| **会话门控** | 触发条件 | mtime > lastConsolidatedAt 的会话数 >= minSessions | 5 |
| **锁门控** | 执行保护 | 无其他进程正在整合 | 文件锁 `tryAcquireConsolidationLock()` |

**额外约束**：
- 扫描节流：会话目录扫描间隔最少 10 分钟（`SESSION_SCAN_INTERVAL_MS`）
- 排除当前会话
- KAIROS 模式（长期助手会话）：追加时间戳条目到日期日志文件，夜间 `/dream` 整合
- 成功时记录 `tengu_auto_dream_completed` 遥测（含 cache hit/creation 指标）
- 失败时回滚锁 mtime 使时间门控再次通过

## 7.7 团队记忆同步

### 7.7.1 架构

源码：`services/teamMemorySync/index.ts` (1,257 LOC)

团队记忆在本地文件系统与 Anthropic 服务器 API 之间同步，按仓库（通过 git remote hash 标识）划分作用域，组织内所有认证成员共享。

### 7.7.2 API 契约

| 操作 | 方法 | 说明 |
|------|------|------|
| 拉取 | `GET /api/claude_code/team_memory?repo={owner/repo}` | 支持 ETag/304 |
| 校验和 | `GET ...&view=hashes` | 仅获取 SHA-256，用于冲突检测 |
| 推送 | `PUT /api/claude_code/team_memory?repo={owner/repo}` | Upsert 语义 |

### 7.7.3 同步语义

| 操作 | 行为 |
|------|------|
| **Pull** | 服务器优先（本地文件被覆盖） |
| **Push** | 增量上传——仅推送 SHA-256 内容哈希不同的条目 |
| **删除不传播** | 删除本地文件不会从服务器删除；下次 pull 会恢复 |

> ⚠️ **推断**：删除不传播的设计可能是为了防止一个成员的误操作影响整个团队，但会增加协调成本。

### 7.7.4 安全措施

源码：`services/teamMemorySync/secretScanner.ts` (324 LOC)

| 措施 | 实现 |
|------|------|
| **密钥扫描** | Push 前运行 `scanForSecrets()` 防止凭据泄露 |
| **路径验证** | `validateTeamMemKey()` 防止路径遍历 |
| **设置源信任** | 仅 policy/flag/local/user 可配置团队记忆路径（**排除 projectSettings**） |
| **认证** | 需要第一方 OAuth（`CLAUDE_AI_INFERENCE_SCOPE` + `CLAUDE_AI_PROFILE_SCOPE`） |

**关键常量**：

| 常量 | 值 |
|------|---|
| `MAX_FILE_SIZE_BYTES` | 250,000 / 条目 |
| `MAX_PUT_BODY_BYTES` | 200,000（网关限制；大批量拆分为顺序 PUT） |
| `TEAM_MEMORY_SYNC_TIMEOUT_MS` | 30,000 |
| `MAX_RETRIES` | 3 |
| `MAX_CONFLICT_RETRIES` | 2 |

## 7.8 Worktree 隔离

### 7.8.1 概述

源码：`utils/worktree.ts` (1,519 LOC) + `tools/EnterWorktreeTool/` (177 LOC) + `tools/ExitWorktreeTool/` (386 LOC)

Git worktree 允许多个 Claude Code 实例在不同分支上并行工作，互不干扰。

### 7.8.2 Worktree 创建

```bash
# CLI 方式
claude --worktree [name]
claude --worktree --tmux    # 在 tmux 会话中运行

# 工具方式（会话内动态切换）
EnterWorktree: { name?: string }
ExitWorktree:  { action: 'keep' | 'remove', discard_changes?: boolean }
```

**创建流程**（`getOrCreateWorktree`）：

1. **快速恢复路径**：直接读取 `.git` 指针文件（无需 subprocess，节省 ~15ms）
2. **新 worktree 路径**：
   - 获取基础分支（如果 `origin/<branch>` 已本地存在则跳过 fetch，节省 6-8s）
   - `git worktree add -B`
   - 支持 `--no-checkout` + `sparse-checkout set --cone` 用于大仓库
3. **后创建设置**（`performPostCreationSetup`）：
   - 复制 `settings.local.json`
   - 配置 `core.hooksPath`（husky 兼容）
   - 软链接配置目录（如 `node_modules`，避免磁盘膨胀）
   - 复制 `.worktreeinclude` 文件
   - 安装 commit attribution hook（`installPrepareCommitMsgHook`，Feature flag `COMMIT_ATTRIBUTION`）

**Worktree 存储位置**：`.claude/worktrees/<flattened-slug>`

**Slug 验证**（`validateWorktreeSlug`）：
- 拒绝路径遍历（`..`、绝对路径）
- 每段验证：`/^[a-zA-Z0-9._-]+$/`
- 最大 64 字符
- `flattenSlug()` 将 `/` 替换为 `+`，避免 git ref D/F 冲突

### 7.8.3 Worktree 清理

| 操作 | 行为 |
|------|------|
| `keep` | 保留 worktree + 分支在磁盘上 |
| `remove` | `git worktree remove --force` + `git branch -D`（100ms 等待锁释放） |

**过期清理**（`cleanupStaleAgentWorktrees`）：
- 仅清理匹配 6 种临时模式（`EPHEMERAL_WORKTREE_PATTERNS`）的 slug
- **Fail-closed**：`git status` 失败或有 tracked changes 时跳过；未从 remote 可达的 commit 也跳过
- `hasWorktreeChanges()` 检查脏工作树 + 新 commit

### 7.8.4 ExitWorktree 安全验证

源码：`tools/ExitWorktreeTool/ExitWorktreeTool.ts`

`validateInput()` 中的安全门：
1. 拒绝无活跃会话的情况
2. `action: 'remove'` 且未设 `discard_changes: true` 时：
   - 如果 `countWorktreeChanges` 返回 null（无法验证状态）→ 失败
   - 如果有未提交文件或新 commit → 失败（列出精确数量）

这是防止数据丢失的唯一安全门。

## 7.9 文件检查点与回退

### 7.9.1 概述

源码：`utils/fileHistory.ts` (1,116 LOC)

Claude Code 在每次工具调用前自动创建文件快照，支持精确到文件级别的回退。

### 7.9.2 存储格式

**备份路径**：`~/.claude/file-history/<sessionId>/<hash>@v<N>`

- `hash`：`sha256(filePath)` 前 16 个十六进制字符
- 版本号：每文件单调递增
- `null` backupFileName = 文件在当时的版本不存在
- 路径存储为相对于 `originalCwd`（节省空间）

### 7.9.3 核心数据结构

```typescript
type FileHistoryBackup = {
  backupFileName: string | null  // null = 文件不存在
  version: number
  backupTime: Date
}

type FileHistorySnapshot = {
  messageId: UUID
  trackedFileBackups: Record<string, FileHistoryBackup>
  timestamp: Date
}

type FileHistoryState = {
  snapshots: FileHistorySnapshot[]
  trackedFiles: Set<string>
  snapshotSequence: number  // 单调计数器，永不重置
}
```

**快照上限**：`MAX_SNAPSHOTS = 100`

### 7.9.4 三阶段模式

所有操作采用**同步捕获 → 异步 I/O → 同步提交**三阶段：

**`fileHistoryTrackEdit`**（文件写入前调用）：
1. 阶段 1（sync）：检查文件是否已在最新快照中被跟踪
2. 阶段 2（async）：`createBackup()` 创建备份
3. 阶段 3（sync）：提交到状态（重新检查竞争条件）

**`fileHistoryMakeSnapshot`**（每回合调用一次）：
1. 阶段 1（sync）：通过 no-op updater 捕获状态
2. 阶段 2（async）：对每个跟踪文件 stat + 与最新备份比较（mtime 优化跳过未修改文件）
3. 阶段 3（sync）：追加快照，淘汰到 MAX_SNAPSHOTS

### 7.9.5 回退机制

**`fileHistoryRewind(state, messageId)`**：恢复所有跟踪文件到指定 `messageId` 对应快照时的状态。

`applySnapshot()` 行为：
- 删除目标版本中不存在的文件
- 通过 `restoreBackup()` 恢复文件（复制 + 恢复权限）
- 仅写入与当前状态不同的文件

**辅助函数**：
- `fileHistoryGetDiffStats()`：干运行回退，返回 `{ filesChanged, insertions, deletions }`
- `fileHistoryHasAnyChanges()`：轻量布尔检查，第一个变化文件即返回

### 7.9.6 恢复支持

源码：`copyFileHistoryForResume(log)` — 通过硬链接（`fs.link`，回退到复制）将备份从旧会话迁移到新会话。仅记录所有备份迁移成功的快照。

### 7.9.7 启用条件

```typescript
fileHistoryEnabled():
  // 交互模式：默认启用
  //   禁用条件：fileCheckpointingEnabled === false 或 CLAUDE_CODE_DISABLE_FILE_CHECKPOINTING

fileHistoryEnabledSdk():
  // SDK/非交互模式：默认禁用
  //   需显式启用：CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING=true
  //   且未被 CLAUDE_CODE_DISABLE_FILE_CHECKPOINTING 覆盖
```

> **设计理由**：SDK 模式默认禁用是因为自动化脚本通常在无用户交互的环境运行，文件快照的磁盘开销和 I/O 延迟可能不可接受。

## 7.10 并发会话管理

### 7.10.1 PID 文件系统

源码：`utils/concurrentSessions.ts` (204 LOC)

**PID 目录**：`~/.claude/sessions/`
**PID 文件**：`{process.pid}.json`

```json
{
  "pid": "<process.pid>",
  "sessionId": "<UUID>",
  "cwd": "<original working dir>",
  "startedAt": "<timestamp>",
  "kind": "<interactive|bg|daemon|daemon-worker>",
  "status": "<busy|idle|waiting>",
  "name": "<session name>",
  "bridgeSessionId": "<remote session ID or null>"
}
```

**会话类型** (`SessionKind`)：

| 类型 | 说明 |
|------|------|
| `interactive` | 交互式 CLI 会话 |
| `bg` | 后台 tmux 会话（`claude --bg`） |
| `daemon` | 守护进程会话 |
| `daemon-worker` | 守护进程工作线程 |

**会话状态** (`SessionStatus`)：

| 状态 | 说明 |
|------|------|
| `busy` | 正在处理 |
| `idle` | 等待输入 |
| `waiting` | 阻塞等待特定条件 |

**过期清理**：`countConcurrentSessions()` 时自动删除进程不存在的 PID 文件（WSL 上跳过，因为 WSL 无法通过 `/proc` 探测 Windows 宿主机的 PID，防止误删正在运行的宿主进程）。严格的文件名验证 `/^\d+\.json$/` 防止误删。

## 7.11 MCP 集成

### 7.11.1 传输协议

| 协议 | 说明 | 适用场景 |
|------|------|----------|
| **stdio** | 标准输入/输出 | 本地进程，最常用 |
| **sse** | Server-Sent Events | 远程服务器 |
| **streamable-http** | 可流式 HTTP | 云端部署 |

### 7.11.2 配置

**CLI 方式**：`--mcp-config <configs...>` 加载 MCP 服务器配置（JSON 文件或字符串）

**项目级**（`.claude/settings.json`）：

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    },
    "remote-server": {
      "type": "sse",
      "url": "https://mcp.example.com/sse"
    }
  }
}
```

### 7.11.3 工具命名与限制

MCP 工具以 `mcp__serverName__toolName` 格式注册（双下划线分隔）。

**关键常量**：

| 常量 | 值 | 用途 |
|------|---|------|
| `MAX_MCP_OUTPUT_TOKENS` | 25,000 | MCP 输出 token 限制（可通过环境变量覆盖） |
| MCP 截断乘数 | 0.5 | 输出超过限制时截断到 50% |

**MCP 相关工具**（详见 04-tools.md 4.8 节）：
- `McpAuthTool`：未认证 MCP 服务器的 OAuth 流程
- `ReadMcpResourceTool`：读取 MCP 资源
- `ListMcpResourcesTool`：列出 MCP 资源

**SDK 控制消息**（MCP 管理用）：
- `mcp_status`：查询 MCP 服务器状态
- `mcp_message`：发送 MCP 消息
- `mcp_set_servers`：动态设置 MCP 服务器
- `mcp_reconnect`：重新连接 MCP 服务器
- `mcp_toggle`：启用/禁用 MCP 服务器

## 7.12 实现者 Checklist

对于设计会话和记忆系统的 Code Agent 开发者：

### 会话持久化
- [ ] 采用 append-only JSONL 格式（避免原地更新的并发问题）
- [ ] 元数据尾部重写（快速元数据读取无需全文件扫描）
- [ ] PID 文件跟踪运行中会话（支持 `ps` 命令和并发限制）
- [ ] 消息链使用 `parentUuid` 树结构（支持分叉和恢复）
- [ ] 懒创建会话文件（避免空会话产生垃圾文件）
- [ ] SIGINT/SIGTERM 信号处理：优雅退出时强制排空 `pendingEntries` 队列，保证 JSONL 完整性

### 上下文压缩
- [ ] 实现多层递增压缩策略（从低成本到高成本逐层尝试）
- [ ] 微压缩优先清除已过期的缓存内容（零额外成本）
- [ ] SessionMemory 压缩在完整压缩前尝试（保留更多信息）
- [ ] 完整压缩使用 forked-agent 复用 prompt cache（降低成本）
- [ ] 熔断器防止连续压缩失败浪费 API 调用
- [ ] prompt-too-long 时丢弃最旧 API-round 组重试

### 记忆系统
- [ ] 多层发现（全局/项目/目录级）覆盖不同使用场景
- [ ] 加载顺序与优先级一致（后加载 = 高优先级）
- [ ] `@include` 支持递归引用，设置循环引用检测和深度限制
- [ ] 记忆内容排除规则防止保存可推导信息
- [ ] 后台提取与主代理互斥（避免同一范围重复写入）
- [ ] 团队记忆密钥扫描防止凭据泄露

### Worktree 隔离
- [ ] VCS-agnostic hook 接口（不绑定特定 VCS）
- [ ] Fail-closed 清理策略（有未提交变更时拒绝删除）
- [ ] 软链接大目录（node_modules）避免磁盘膨胀
- [ ] 过期清理仅匹配临时模式（防止误删用户 worktree）

### 文件检查点
- [ ] 三阶段操作模式防止 React 重渲染风暴
- [ ] 硬链接迁移备份（跨会话恢复时节省磁盘）
- [ ] mtime 快速路径跳过未修改文件
- [ ] 版本号去重（相同内容文件共享 `{hash}@v1` 备份名）

## 7.13 设计哲学与架构权衡

| 决策 | 选择 | 替代方案 | 权衡 |
|------|------|----------|------|
| 会话存储格式 | Append-only JSONL | SQLite / LevelDB | 写入并发零冲突、崩溃恢复简单；查询需全扫描 |
| 5 层递增压缩 | L1→L2→L3→L4→L5 逐层升级 | 单层智能压缩 | 渐进降级保证可用性；实现复杂度高 |
| CLAUDE.md 优先级 | 后加载 = 高优先级 | 先加载 = 高优先级 | 符合 LLM 注意力机制（模型更关注 prompt 尾部） |
| 团队记忆删除 | 删除不传播 | 双向同步删除 | 防止误操作影响全团队；本地删除仅影响本地 |
| 文件检查点模式 | sync→async→sync | 纯异步 | 防止 React 重渲染风暴；微小延迟开销 |
| autoDream 触发 | 双门控 + 文件锁 | 定时任务 | 资源高效（仅达标时运行）；整合可能延迟 |
| 文件备份命名 | `hash@vN` | 时间戳 | 去重（相同内容共享备份）+ 确定性可验证 |
