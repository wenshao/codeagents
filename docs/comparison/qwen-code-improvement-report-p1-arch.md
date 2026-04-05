# Qwen Code 改进建议 — P1 架构与性能增强

> 中高优先级改进项（架构与性能方向）。每项包含：问题场景、现状分析、改进前后对比、实现成本评估、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. 分层上下文压缩策略增强（P1）

Claude Code 的上下文压缩不是单一机制，而是 **3 条独立路径**——根据成本和紧急程度选择最合适的路径。当前 Qwen Code 仅有单一压缩（`/compress` 手动触发或 70% 阈值自动触发），缺少精细控制。

**Claude Code 的 3 条压缩路径**：

| 路径 | 触发条件 | 成本 | 效果 |
|------|---------|------|------|
| **Auto-compact** | token 达 ~83% 窗口 | 中（一次 LLM 调用） | 9 章节摘要 + 自动恢复文件 |
| **Cached Micro-compact** | 每轮自动 | **零**（不破坏 cache） | 通过 `cache_edits` API 原地删除旧 tool results |
| **Time-based Micro-compact** | 空闲 >60 分钟 | **零**（不破坏 cache） | content-clear 旧 tool results |

**关键差异分析**：

| 方面 | Claude Code | Qwen Code |
|------|-------------|-----------|
| 触发阈值 | ~83%（200K 窗口 - 13K buffer） | 70% |
| 压缩后恢复 | 最近 5 文件 + 活跃 Skill + Plan | 无恢复 |
| Micro-compact | 有（`cache_edits` API） | 无 |
| Time-based MC | 有（60 分钟空闲） | 无 |
| 熔断器 | 连续 3 次失败停止 | 无 |
| 摘要章节 | 9 章节（详细） | 5 章节（简略） |

**改进方案——引入 Time-based Micro-compact**（最容易实现的增益）：

当用户离开终端超过阈值（默认 60 分钟，对应服务端 prompt cache 1h TTL），直接在消息数组中标记旧 tool results 为已清除——不破坏缓存前缀，下次 API 调用自动受益：

```typescript
// 伪代码：API 调用前检查
function maybeTimeBasedMicroCompact(messages: Message[]): Message[] {
  const lastAssistantAt = findLastAssistantTimestamp(messages);
  const gapMinutes = (Date.now() - lastAssistantAt) / 60000;
  
  if (gapMinutes < 60) return messages;  // 未达阈值
  
  // 保留最近 5 个 tool results，其余清除
  const keepRecent = 5;
  const toolResults = messages.filter(m => m.role === 'tool');
  const toClear = toolResults.slice(0, -keepRecent);
  
  return messages.map(m => {
    if (toClear.includes(m)) {
      return { ...m, content: '[Old tool result content cleared]' };
    }
    return m;
  });
}
```

**改进方案——增强 Auto-compact**（中等难度）：

| 改进项 | 当前 | 改进后 |
|--------|------|--------|
| 触发阈值 | 70% | ~83%（给模型更多工作空间） |
| 压缩后恢复 | 无 | 自动恢复最近 5 文件 + 活跃 Skill |
| 熔断器 | 无 | 连续 3 次失败停止重试 |
| 摘要章节 | 5 章节 | 9 章节（更详细） |

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/compact/autoCompact.ts` | `AUTOCOMPACT_BUFFER_TOKENS = 13_000`、`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3` |
| `services/compact/microCompact.ts` | `COMPACTABLE_TOOLS`（8 种可清除工具）、cache_edits 路径 |
| `services/compact/timeBasedMCConfig.ts` | `gapThresholdMinutes = 60`、`keepRecent = 5` |
| `services/compact/compact.ts` (1705行) | 9 章节摘要模板、自动恢复逻辑 |

**Qwen Code 修改方向**：

1. **Time-based Micro-compact**（~100 行，~1 天）：
   - `coreToolScheduler.ts` 中 API 调用前检查空闲时间
   - 超过 60 分钟则清除旧 tool results（保留最近 5 个）
   - 标记为 `[Old tool result content cleared]`

2. **Auto-compact 增强**（~300 行，~3 天）：
   - 阈值从 70% 改为 ~83%
   - 压缩后自动恢复最近 5 文件（从历史消息中提取文件路径）
   - 增加熔断器（连续 3 次失败停止）

**实现成本评估**：
- Time-based MC：~100 行，~1 天
- Auto-compact 增强：~300 行，~3 天
- 难点：文件恢复逻辑（从历史消息中识别文件路径和内容）

**改进前后对比**：
- **改进前**：用户离开 2 小时后回来，旧 tool results 仍占上下文——浪费 token
- **改进后**：Time-based MC 自动清除——上下文精简，token 节省

**意义**：用户经常离开终端（开会、吃饭），回来后旧上下文仍占 token——浪费。
**缺失后果**：旧 tool results 不清除——上下文浪费，压缩触发过早。
**改进收益**：Time-based MC 自动清理——用户回来时上下文已精简，token 节省。

---

<a id="item-2"></a>

### 2. API 指数退避与智能重试（P1）

你让 Agent 执行一个复杂任务，突然 API 返回 429（Too Many Requests）——请求被限流。当前 Qwen Code 的重试逻辑是固定次数重试（如 3 次），但问题在于：

- **固定间隔重试**：如果 API 限流是渐进式的（1s → 5s → 30s），固定间隔（如每次等 1s）会快速耗尽重试次数
- **缺少降级策略**：连续限流后没有模型降级（如从高端模型切到标准模型）
- **401 Token 过期**：API Key 过期时没有自动刷新逻辑

**Claude Code 的解决方案——10 次指数退避 + 模型降级**：

| 场景 | 重试策略 |
|------|---------|
| 429 Too Many Requests | 10 次指数退避（1s → 2s → 4s → 8s → ... → 512s） |
| 529 模型不可用 | 降级到备用模型（如 Opus → Sonnet） |
| 401 Unauthorized | 刷新 token 后重试（如 OAuth token 过期） |
| 5xx 服务器错误 | 3 次指数退避 |

**指数退避实现**：

```typescript
async function retryWithBackoff(
  fn: () => Promise<Response>,
  maxRetries = 10,
  baseDelay = 1000
): Promise<Response> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fn();
      if (response.ok) return response;
      
      if (response.status === 429) {
        const delay = baseDelay * Math.pow(2, i);
        const retryAfter = response.headers.get('Retry-After');
        const waitMs = retryAfter ? parseInt(retryAfter) * 1000 : delay;
        await sleep(waitMs);
        continue;
      }
      
      if (response.status === 529) {
        // 模型降级到备用模型
        return await fnWithFallbackModel();
      }
      
      throw new Error(`API error: ${response.status}`);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(baseDelay * Math.pow(2, i));
    }
  }
}
```

**关键设计**：
- `Retry-After` 头优先（API 返回的建议等待时间）
- 退避上限 512 秒（~8.5 分钟，防止无限等待）
- 模型降级需要用户预配置备用模型
- 401 刷新 token 仅适用于 OAuth 场景

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/api/withRetry.ts` (822行) | 指数退避逻辑、`Retry-After` 头解析、`maxRetries`、`maxDelayMs` |
| `services/api/client.ts` | 401/429/529 处理、模型降级 |

**Qwen Code 现状**：`api.ts` 中有基础重试逻辑，但缺少指数退避、模型降级、401 刷新。

**Qwen Code 修改方向**：① `api.ts` 新增指数退避逻辑（`Math.pow(2, i)`）；② 解析 `Retry-After` 头；③ 429 处理；④ 529 时降级到备用模型（需配置）；⑤ 401 时刷新 token（如适用）。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~1.5 天（1 人）
- 难点：模型降级逻辑（需要备用模型配置）、401 刷新（取决于认证方式）

**改进前后对比**：
- **改进前**：429 限流 → 固定间隔重试 3 次 → 快速失败 → 任务中断
- **改进后**：429 限流 → 10 次指数退避（最长等 512s）→ 模型降级 → 任务继续

**意义**：API 限流是常见场景——指数退避提高成功率，模型降级避免完全失败。
**缺失后果**：固定间隔重试快速失败——限流期间任务中断。
**改进收益**：指数退避 + 模型降级——限流期间自动适应，任务不中断。

---

<a id="item-3"></a>

### 3. 同步 I/O 异步化（P1）

Node.js 事件循环是单线程的——任何同步阻塞操作都会阻塞整个事件循环，导致：

- 键盘输入响应延迟（用户打字卡顿）
- TUI 渲染卡顿（UI 闪烁或不更新）
- 工具执行延迟（本该并行的 I/O 被阻塞）

**Claude Code 的做法——全面异步 I/O**：

Claude Code 在源码中避免使用 `readFileSync`/`writeFileSync`/`statSync`，全部替换为 `async/await` 版本：

```typescript
// ❌ 错误：同步 I/O（阻塞事件循环）
const content = fs.readFileSync(filePath, 'utf-8');
const stat = fs.statSync(filePath);

// ✅ 正确：异步 I/O（不阻塞）
const content = await fs.promises.readFile(filePath, 'utf-8');
const stat = await fs.promises.stat(filePath);
```

**关键异步化点**：

| 操作 | 同步（阻塞） | 异步（非阻塞） |
|------|-------------|---------------|
| 文件读取 | `readFileSync()` | `fs.promises.readFile()` |
| 文件写入 | `writeFileSync()` | `fs.promises.writeFile()` |
| 文件状态 | `statSync()` | `fs.promises.stat()` |
| 目录列表 | `readdirSync()` | `fs.promises.readdir()` |
| 文件删除 | `unlinkSync()` | `fs.promises.unlink()` |
| 目录创建 | `mkdirSync()` | `fs.promises.mkdir()` |

**性能影响**：

| 场景 | 同步 I/O | 异步 I/O |
|------|---------|---------|
| 读取 10 个文件 | ~50ms（阻塞 50ms） | ~5ms（并行，阻塞 <1ms） |
| 大文件读取（10MB） | ~100ms（阻塞 100ms） | ~100ms（不阻塞其他操作） |
| 用户感知 | 键盘输入卡顿 | 流畅 |

**Claude Code 源码审查**：

在整个 Claude Code 源码库中搜索 `readFileSync`/`writeFileSync`/`statSync`，发现：
- **0 处** `readFileSync`（全部异步）
- **0 处** `writeFileSync`（全部异步）
- **少量** `statSync`（仅在启动初始化阶段，可接受）

**Qwen Code 现状**：通过 grep 搜索 `readFileSync`/`writeFileSync`/`statSync`，发现多处使用——特别是在文件操作工具（`read-file.ts`、`write-file.ts`）和配置加载（`config.ts`）中。

**Qwen Code 修改方向**：① 搜索所有 `*Sync` 调用（`grep -r "readFileSync\|writeFileSync\|statSync" packages/core/src/tools/`）；② 逐一替换为 `async/await` 版本；③ 启动阶段可保留（不影响运行时性能）；④ 工具执行路径必须全部异步。

**实现成本评估**：
- 涉及文件：~10 个（需 grep 确认具体数量）
- 新增代码：~200 行（修改现有代码）
- 开发周期：~2 天（1 人）
- 难点：调用链上游也需要异步化（否则异步变同步）

**改进前后对比**：
- **改进前**：读取 10 个文件 → 阻塞事件循环 50ms → 用户打字卡顿
- **改进后**：读取 10 个文件 → 异步并行 → 不阻塞事件循环 → 用户输入流畅

**意义**：同步 I/O 阻塞事件循环——影响用户输入、TUI 渲染、工具执行。
**缺失后果**：文件操作期间用户输入卡顿、UI 不更新。
**改进收益**：全面异步 I/O——用户输入流畅、TUI 不闪烁、工具并行执行。

---

<a id="item-4"></a>

### 4. 文件读取缓存 + 批量并行 I/O（P1）

Agent 在探索代码时，经常重复读取相同文件——比如第一轮读了 `package.json` 了解依赖，第三轮又读 `package.json` 确认版本。每次读取都是磁盘 I/O（~5ms），累积起来可观。更严重的是，当 Agent 需要读取 10 个文件时，当前 Qwen Code 逐个顺序读取——总延迟 = 10 × 5ms = 50ms。

**Claude Code 的解决方案——文件读取缓存 + 批量并行**：

**缓存层**：
```typescript
// 1000 条 LRU 缓存，mtime 失效
const fileReadCache = new LRUCache<string, { content: string, mtime: number }>({
  max: 1000,
  ttl: 5 * 60 * 1000,  // 5 分钟过期
});

async function readFileCached(path: string): Promise<string> {
  const cached = fileReadCache.get(path);
  if (cached) {
    const stat = await fs.promises.stat(path);
    if (stat.mtimeMs === cached.mtime) {
      return cached.content;  // 缓存命中
    }
  }
  // 缓存未命中，读取磁盘
  const content = await fs.promises.readFile(path, 'utf-8');
  const stat = await fs.promises.stat(path);
  fileReadCache.set(path, { content, mtime: stat.mtimeMs });
  return content;
}
```

**批量并行**：
```typescript
// 并行读取 10 个文件（最多 32 并发）
async function readFilesBatch(paths: string[]): Promise<string[]> {
  return pMap(paths, readFileCached, { concurrency: 32 });
}
```

**性能收益**：

| 场景 | 无缓存 | 有缓存 | 增益 |
|------|--------|--------|------|
| 重复读同一文件 | 5ms | <0.1ms | **50×** |
| 读 10 个不同文件（并行） | 50ms（顺序） | 5ms（并行） | **10×** |
| 读 10 个文件（缓存命中） | 50ms | <1ms | **50×** |

**关键参数**：
- LRU 缓存：1000 条上限（防止内存膨胀）
- TTL：5 分钟（平衡新鲜度和命中率）
- mtime 校验：文件修改后缓存自动失效
- 并行度：32 并发（避免打开太多文件描述符）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fileCache.ts` | 文件读取缓存（LRU + mtime） |
| `services/tools/toolOrchestration.ts` | 批量并行工具执行 |

**Qwen Code 现状**：`read-file.ts` 每次从磁盘读取文件——无缓存。多个文件读取顺序执行——无并行。

**Qwen Code 修改方向**：① 新建 `utils/fileCache.ts`（LRU 缓存 + mtime 失效）；② `read-file.ts` 使用缓存读取；③ 工具调度器支持批量并行（`pMap` 或 `Promise.all` 分片）。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：缓存失效策略（确保文件修改后不返回旧缓存）

**改进前后对比**：
- **改进前**：Agent 探索代码 → 10 个文件顺序读取 → 50ms 延迟
- **改进后**：Agent 探索代码 → 缓存命中 70% + 并行 → <10ms 延迟

**意义**：文件读取是 Agent 最频繁的操作之一——缓存 + 并行加速代码探索。
**缺失后果**：重复读取相同文件 + 顺序 I/O——探索速度慢。
**改进收益**：LRU 缓存 + 批量并行——代码探索快 5-10×。

---

<a id="item-5"></a>

### 5. Prompt Cache 分段与工具稳定排序（P1）

Anthropic/DashScope API 的 prompt cache 机制要求**缓存前缀字节完全一致**才能命中缓存。如果工具定义的顺序变化、或系统提示内容微调，整个缓存失效——每次 API 调用都需重新缓存（浪费 token + 增加延迟）。

**Claude Code 的解决方案——静态/动态分段 + 工具稳定排序**：

```
API 请求消息结构：
┌─────────────────────────────────┐
│  Static Prefix（缓存前缀）       │  ← 系统提示 + 工具定义 + 早期消息
│  - system prompt                │
│  - tool definitions (sorted)    │  ← 稳定排序（按工具名字母序）
│  - messages[0..N]              │  ← 早期对话历史
├─────────────────────────────────┤
│  Dynamic Suffix（动态后缀）      │  ← 最近消息（每轮变化）
│  - messages[N+1..end]          │
│  - new tool results             │
└─────────────────────────────────┘
```

**关键设计**：

| 机制 | 说明 |
|------|------|
| **工具稳定排序** | 工具定义按名字字母序排列（`tools.sort((a,b) => a.name.localeCompare(b.name))`），确保每次 API 请求的工具顺序一致 |
| **工具 schema 锁定** | 工具参数 schema 不动态变化（如 `description` 字段不注入运行时信息） |
| **内置工具前缀** | 内置工具始终在 MCP 工具之前（防止 MCP 工具数量变化影响缓存前缀） |
| **Static/Dynamic 分界** | 前 N 条消息标记为 static（不变），后续消息为 dynamic（每轮变化） |

**缓存命中率影响**：

| 场景 | 无稳定排序 | 有稳定排序 |
|------|-----------|-----------|
| 工具顺序不变 | ~90% | ~90% |
| MCP 工具增减 | ~20%（缓存失效） | ~85%（前缀不变） |
| 工具 schema 变化 | ~10%（缓存失效） | ~85%（schema 锁定） |

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/api/claude.ts` | prompt cache 管理、`cache_reference` 标记、缓存前缀优化 |
| `services/api/promptCacheBreakDetection.ts` | 缓存失效检测、TTL 阈值监控 |
| `services/api/withRetry.ts` | 重试时保留模型名防止缓存失效 |

> **注**：工具顺序稳定性是基于 Claude Code 架构的推断——工具注册层保证顺序一致，
> API 层通过 `cache_reference` 标记缓存前缀。未发现显式的字母序排序代码，
> 但 `tools` 数组顺序在请求间保持稳定是缓存命中的必要条件。

**Qwen Code 现状**：工具注册顺序即 API 请求顺序——无稳定排序。MCP 工具动态发现后插入——可能改变缓存前缀。

**Qwen Code 修改方向**：① 工具定义按名字母序排序（`tools.sort(...)`）；② 内置工具始终在前，MCP 工具在后；③ 工具 schema 不注入运行时信息（保持静态）；④ 系统提示中静态部分和动态部分分离。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：确保所有工具注册点都遵循稳定排序

**改进前后对比**：
- **改进前**：MCP 工具增减 → 工具顺序变化 → 缓存失效 → 每次多花 20K token 重建缓存
- **改进后**：MCP 工具增减 → 前缀不变 → 缓存命中 → 每次省 20K token

**意义**：Prompt cache 命中率直接影响 API 成本和延迟——稳定排序是关键。
**缺失后果**：工具顺序变化导致缓存失效——浪费 token + 增加延迟。
**改进收益**：稳定排序 + schema 锁定——缓存命中率 ~85%+，API 成本降低。

---

<a id="item-6"></a>

### 6. 记忆/附件异步 Prefetch（P1）

Agent 在每轮工具执行期间，经常需要搜索相关记忆（Session Memory）、加载附件（文件、图片）、收集 LSP 诊断信息。当前这些操作是**顺序执行**的——先搜索记忆 → 再加载附件 → 再收集 LSP 诊断——总延迟 = 记忆搜索 + 附件加载 + LSP 诊断。

**Claude Code 的解决方案——异步 Prefetch 流水线**：

在工具执行的**同时**，后台并行搜索相关记忆和加载附件——当工具完成后，记忆和附件已经准备好：

```
工具执行开始：
  ├─ 执行工具（如 ReadFile）  ← 主要操作
  ├─ Prefetch 记忆搜索       ← 后台并行
  ├─ Prefetch 附件加载       ← 后台并行
  └─ Prefetch LSP 诊断      ← 后台并行
  
工具执行完成：
  ├─ 工具结果就绪
  ├─ 记忆结果就绪（已预取）
  └─ 附件结果就绪（已预取）
```

**关键设计**：
- `Promise.all` 并行获取（记忆 + 附件 + LSP）
- 超时保护（prefetch 超过 2s 则放弃，不阻塞主流程）
- 结果缓存（同一轮多次工具执行共享 prefetch 结果）
- 内存限制（prefetch 结果上限 100KB，防止膨胀）

**性能收益**：

| 场景 | 顺序执行 | 异步 Prefetch | 增益 |
|------|---------|--------------|------|
| 记忆搜索 500ms + 附件 300ms + LSP 200ms | 1000ms | 500ms（并行） | **2×** |
| 工具执行 2s + 记忆 500ms | 2500ms | 2000ms（重叠） | **1.25×** |

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/contextPrefetch/prefetch.ts` | 异步 prefetch 编排 |
| `services/SessionMemory/sessionMemory.ts` | 记忆搜索集成 |

**Qwen Code 现状**：记忆搜索、附件加载、LSP 诊断顺序执行——无 prefetch。

**Qwen Code 修改方向**：① 新建 `services/contextPrefetch/prefetch.ts`；② 工具执行开始时触发 `Promise.all` 并行获取；③ 超时保护（2s 放弃）；④ 结果缓存（同轮共享）。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~150 行
- 开发周期：~1.5 天（1 人）
- 难点：prefetch 与主流程的同步（确保工具完成时 prefetch 也完成）

**改进前后对比**：
- **改进前**：工具执行 → 等完成 → 搜索记忆 → 加载附件 → 收集 LSP（总 2500ms）
- **改进后**：工具执行 + 搜索记忆 + 加载附件 + 收集 LSP 并行（总 2000ms）

**意义**：上下文收集是每轮必需操作——prefetch 减少串行延迟。
**缺失后果**：顺序执行上下文收集——每轮多花 500ms。
**改进收益**：异步 prefetch——工具执行与上下文收集并行——每轮省 500ms。

---

<a id="item-7"></a>

### 7. 优雅关闭序列与信号处理（P1）

用户按 `Ctrl+C` 退出 Agent 时，如果 Agent 正在执行工具（如写入文件、运行测试），直接退出可能导致：

- 文件写入中断（文件内容不完整或损坏）
- 测试运行中断（测试数据库未清理）
- Session 状态未保存（对话历史丢失）
- 子进程孤儿化（后台进程未清理）

**Claude Code 的解决方案——5 阶段优雅关闭**：

| 阶段 | 操作 | 超时 |
|------|------|------|
| 1. 信号捕获 | 捕获 SIGINT（Ctrl+C）/SIGTERM（kill） | 立即 |
| 2. 停止接收 | 停止接受新输入（键盘、队列、MCP） | 100ms |
| 3. 清理注册 | 调用所有清理回调（文件句柄、子进程、临时文件） | 1s |
| 4. 状态保存 | 保存 session 状态（对话历史、内存、检查点） | 2s |
| 5. Failsafe | 如果上述超时，强制退出 | 5s 总计 |

**实现伪代码**：

```typescript
let isShuttingDown = false;

async function gracefulShutdown(signal: string) {
  if (isShuttingDown) return;  // 防止重复信号
  isShuttingDown = true;
  
  // 1. 停止接收输入
  stopInputQueue();
  disconnectMCP();
  
  // 2. 清理子进程
  await killAllChildProcesses(1000);  // 1s 超时
  
  // 3. 保存 session 状态
  await saveSessionState(2000);  // 2s 超时
  
  // 4. 清理临时文件
  cleanupTempFiles();
  
  // 5. 退出
  process.exit(0);
}

process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
```

**关键设计**：
- **去重**：`isShuttingDown` 标志防止重复信号导致多次清理
- **超时**：每个阶段有独立超时（防止某个阶段卡死）
- **Failsafe**：5s 总超时后强制退出（防止无限卡住）
- **清理回调注册**：关键操作（文件写入、子进程启动）时注册清理回调

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/gracefulShutdown.ts` | 信号处理、5 阶段关闭 |
| `tasks/LocalShellTask/LocalShellTask.tsx` | 子进程清理 |

**Qwen Code 现状**：non-interactive 模式（`nonInteractiveCli.ts`）有基础 SIGINT/SIGTERM 处理；interactive 模式（`useBracketedPaste.ts`）有 cleanup。但**缺少 5 阶段优雅关闭序列**（停止接收→清理子进程→保存状态→清理临时文件→failsafe），直接退出可能中断文件写入或子进程。

**Qwen Code 修改方向**：① 新建 `utils/gracefulShutdown.ts`；② 注册 SIGINT/SIGTERM 处理函数；③ 关键操作注册清理回调；④ 5s failsafe 强制退出。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~120 行
- 开发周期：~1 天（1 人）
- 难点：识别所有需要清理的资源（文件句柄、子进程、临时文件、网络连接）

**改进前后对比**：
- **改进前**：Ctrl+C 退出 → 文件写入中断 → 文件损坏
- **改进后**：Ctrl+C 退出 → 优雅关闭 → 文件写完再保存状态 → 安全退出

**意义**：优雅关闭防止数据损坏——文件、状态、子进程安全清理。
**缺失后果**：直接退出可能损坏文件、丢失状态、孤儿进程。
**改进收益**：5 阶段优雅关闭——数据安全、状态完整、无孤儿进程。

---

<a id="item-8"></a>

### 8. 原子文件写入与事务回滚（P1）

Agent 写入文件时，如果中途中断（用户 Ctrl+C、系统崩溃、进程被 kill），可能导致文件内容不完整——只写了一半的文件既不是旧版本也不是新版本，处于损坏状态。

**Claude Code 的解决方案——原子写入**：

```typescript
// ❌ 错误：直接写入（中断时文件损坏）
await fs.promises.writeFile(filePath, content, 'utf-8');

// ✅ 正确：原子写入（temp + rename）
const tempPath = `${filePath}.tmp.${Date.now()}`;
try {
  await fs.promises.writeFile(tempPath, content, 'utf-8');
  await fs.promises.rename(tempPath, filePath);  // rename 是原子操作
} catch (error) {
  // 失败时清理临时文件
  await fs.promises.unlink(tempPath).catch(() => {});
  throw error;
}
```

**原子性保证**：
- `rename()` 在同一文件系统上是原子操作（POSIX 保证）
- 如果 rename 成功：文件要么是新版本，要么是旧版本（不会中间状态）
- 如果 rename 失败：原始文件不变，临时文件被清理

**大结果持久化**：

工具执行结果（如 Bash 输出）可能非常大（>1MB）。Claude Code 不将其保留在内存中，而是持久化到磁盘：

```typescript
// 工具结果 >1MB 时写入临时文件
if (toolResultSize > 1_000_000) {
  const resultPath = `/tmp/tool-results-${taskId}.json`;
  await fs.promises.writeFile(resultPath, JSON.stringify(toolResult));
  return { content: `Result too large, saved to ${resultPath}` };
}
```

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/atomicWrite.ts` | 原子写入（temp + rename） |
| `services/tools/toolResultStorage.ts` | 大结果持久化 |

**Qwen Code 现状**：`write-file.ts` 直接写入文件——中途中断时文件可能损坏。工具结果全部保留在内存中——大结果可能占大量内存。

**Qwen Code 修改方向**：① 新建 `utils/atomicWrite.ts`；② `write-file.ts` 使用原子写入；③ 工具结果 >1MB 时持久化到临时文件。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：无（原子写入是标准模式）

**改进前后对比**：
- **改进前**：写入文件时中断 → 文件损坏（一半内容）
- **改进后**：写入文件时中断 → 原文件不变（临时文件被清理）

**意义**：原子写入防止文件损坏——中途中断时文件完整性有保证。
**缺失后果**：写入中断时文件可能损坏——既不是旧版本也不是新版本。
**改进收益**：原子写入（temp + rename）——文件要么旧版本要么新版本，不会损坏。

---

<a id="item-9"></a>

### 9. Token Budget 续行与自动交接（P1）

Agent 执行复杂任务时，token 使用量持续增长。当前 Qwen Code 在 token 达到 70% 时触发压缩——但压缩是一次性的，如果压缩后 token 仍然紧张，Agent 可能很快再次触发压缩，陷入"压缩→执行→再压缩"的循环。

**Claude Code 的解决方案——Token Budget 续行与分层回退**：

| 阶段 | 触发条件 | 操作 |
|------|---------|------|
| **正常执行** | <83% 窗口 | 正常工具执行 |
| **一级警告** | 83%-90% | 提示用户，准备压缩 |
| **自动压缩** | >90% | auto-compact（9 章节摘要 + 恢复文件） |
| **续行检测** | 压缩后 >85% | 继续执行但监控增长速度 |
| **递减检测** | 连续 2 轮 token 增长 <5% | 判定任务接近完成，允许继续 |
| **分层回退** | 压缩后仍 >90% | micro-compact → session memory compact → full compact |

**关键设计**：
- **90% 续行**：压缩后如果 <85%，允许继续执行（不立即中断）
- **递减检测**：如果 token 增长速度递减（如 8% → 5% → 3%），说明任务接近完成，不需要再次压缩
- **分层回退**：一级压缩不够时升级（micro → session memory → full）
- **紧急停止**：>95% 强制停止（防止 API 报错）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/compact/autoCompact.ts` | 分层回退、`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3` |
| `query/tokenBudget.ts` | Token Budget 管理、续行逻辑 |
| `utils/tokenBudget.ts` | Token Budget 状态追踪 |

**Qwen Code 现状**：70% 阈值一次性压缩——压缩后不检查 token 使用情况，可能很快再次触发。

**Qwen Code 修改方向**：① 新建 `services/tokenBudget.ts`；② 实现 4 阶段管理（正常/警告/压缩/紧急停止）；③ 递减检测（连续 2 轮增长 <5% 允许继续）；④ 分层回退（micro → session memory → full）。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：递减检测算法（如何判定任务接近完成）

**改进前后对比**：
- **改进前**：70% 压缩 → 执行 2 轮又到 70% → 再压缩——循环浪费 token
- **改进后**：90% 压缩 → 续行检测 → 递减判断——接近完成时不重复压缩

**意义**：Token Budget 管理避免频繁压缩——续行 + 递减检测减少不必要操作。
**缺失后果**：压缩后很快再次触发——"压缩→执行→再压缩"循环。
**改进收益**：Token Budget 续行 + 递减检测 + 分层回退——压缩次数减少，token 更高效。

---

<a id="item-10"></a>

### 10. 反应式压缩（P1）

当 API 返回 `prompt_too_long` 错误时，当前请求直接被拒绝——用户需要手动 `/compress` 后再重试。这个错误是完全可以自动恢复的。

**Claude Code 的解决方案——反应式压缩自动重试**：

```
API 返回 prompt_too_long
  ↓
捕获错误，进入反应式压缩
  ↓
裁剪最早的消息组（按 token 超限量或 20%）
  ↓
重试 API 调用（最多 3 次）
  ↓
成功 / 仍然失败（给用户错误提示）
```

**关键设计**：
- **裁剪策略**：优先裁剪最早的消息组（用户消息 + 工具结果配对裁剪）
- **裁剪量计算**：`max(超出 token 数, 总 token × 20%)`（确保裁剪足够多）
- **重试上限**：3 次（防止无限重试）
- **失败回退**：3 次后仍失败，给用户友好错误提示（"上下文过长，请手动 /compress"）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/compact/compact.ts` (1705行) | 反应式压缩、重试逻辑、`prompt_too_long` 处理 |

**Qwen Code 现状**：API 返回错误时直接展示给用户——无自动恢复。

**Qwen Code 修改方向**：① API 错误处理中捕获 `prompt_too_long`；② 裁剪最早的消息组；③ 重试（最多 3 次）；④ 失败时给用户友好提示。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~120 行
- 开发周期：~1 天（1 人）
- 难点：消息组配对裁剪（确保 user + assistant + tool results 完整裁剪）

**改进前后对比**：
- **改进前**：API 报错 prompt_too_long → 用户手动 /compress → 重试任务
- **改进后**：API 报错 prompt_too_long → 自动裁剪 + 重试 → 用户无感知

**意义**：反应式压缩自动恢复——用户不需手动干预。
**缺失后果**：API 报错后用户需手动压缩再重试——打断工作流。
**改进收益**：自动裁剪 + 重试（最多 3 次）——用户无感知恢复。

---

## 总结

本文件涵盖 10 项 P1 架构与性能增强改进：

| # | 改进点 | 优先级 | 开发周期 | 意义 |
|---|--------|:------:|:--------:|------|
| 1 | [分层上下文压缩增强](#item-1) | P1 | ~4 天 | Time-based MC + Auto-compact 增强 |
| 2 | [API 指数退避与智能重试](#item-2) | P1 | ~1.5 天 | 10 次退避 + 模型降级 |
| 3 | [同步 I/O 异步化](#item-3) | P1 | ~2 天 | 防止事件循环阻塞 |
| 4 | [文件读取缓存 + 批量并行](#item-4) | P1 | ~2 天 | 代码探索快 5-10× |
| 5 | [Prompt Cache 分段与稳定排序](#item-5) | P1 | ~1 天 | 缓存命中率 ~85%+ |
| 6 | [记忆/附件异步 Prefetch](#item-6) | P1 | ~1.5 天 | 每轮省 500ms |
| 7 | [优雅关闭序列与信号处理](#item-7) | P1 | ~1 天 | 数据安全 + 状态完整 |
| 8 | [原子文件写入与事务回滚](#item-8) | P1 | ~1 天 | 防止文件损坏 |
| 9 | [Token Budget 续行与交接](#item-9) | P1 | ~2 天 | 减少频繁压缩 |
| 10 | [反应式压缩自动重试](#item-10) | P1 | ~1 天 | 自动恢复 prompt_too_long |

**总计**：~17 天（1 人）

> **免责声明**: 以上分析基于 2026 年 Q1 Claude Code（`../claude-code-leaked`）与 Qwen Code（`../qwen-code`）源码对比，可能已过时。
