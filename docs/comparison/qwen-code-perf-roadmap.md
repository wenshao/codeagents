# Qwen Code 性能优化 Roadmap

> 基于 codeagents 全部性能相关 item 的统一 roadmap —— 按 ROI 排序的可执行优化清单。
>
> **数据来源**：[改进报告 P0/P1 引擎优化](./qwen-code-improvement-report-p0-p1-engine.md) + [P2 性能优化](./qwen-code-improvement-report-p2-perf.md) + 实际源码审计 + 已合并 PR 度量数据

---

## 速查表 · 一页读懂

```
✅ 已完成（基线）
   PR#3581 · sync I/O hot path 110→10 (-91%)
   PR#3591 · TUI flicker foundation
   PR#3013 · SlicingMaxSizedBox
   PR#3604 · Skill 并行加载 + conditional 激活（item-28 子项 1+2+6）

🥇 P0 本周（建议）
   ① sentSkillNames 去重         50 行   每轮省 1K token
   ② FileReadCache 内容层        150 行  Read-Edit 循环零 I/O
   ③ readManyFiles 32 批并行      30 行   多文件 I/O 1/32

🥈 P1 下周
   ④ MCP/LSP 并行启动             50 行   启动 -2-5s
   ⑤ 延迟初始化 lazyImport       80 行   冷启动 -300ms
   ⑥ Git 直读避免 spawn          100 行  状态栏 -30ms
   ⑦ in-flight 请求合并 (dedupe)  80 行   并行 subagent 节省

🥉 P2-P3 按需
   ⑧ React.memo 高频组件 / ⑨ WeakRef 长 session 内存 / ⑩ 正则编译缓存 /
   ⑪ Shell AST 解析缓存 / ⑫ 终端行宽缓存 / ⑬ Bun 原生 API 等
```

**总投入**：P0+P1 约 **8 天 × 1 人 / 540 行代码**，预期收益：每轮节省 1K+ tokens、冷启动 -300ms、文件 I/O 1/32、启动 -2-5s。

---

## 一、已完成基线（不重复推进）

> 这些 PR 已合并 / 进行中，不要再重复实现。

### ✅ MERGED（2026-04 期间）

| PR | 内容 | 度量 |
|---|---|---|
| **[PR#3581](https://github.com/QwenLM/qwen-code/pull/3581)** | sync I/O hot path | 110→10 syscall/prompt（**-91%**）|
| **[PR#3591](https://github.com/QwenLM/qwen-code/pull/3591)** | TUI flicker foundation | throttle + pre-slice + soft-wrap 抑制 + 同步终端 allowlist |
| **[PR#3013](https://github.com/QwenLM/qwen-code/pull/3013)** | SlicingMaxSizedBox + useStableHeight | 渲染前裁剪到 maxLines |
| **[PR#3604](https://github.com/QwenLM/qwen-code/pull/3604)** | Skill 并行加载 + path-conditional 激活 | item-28 子项 #1+#2+#6 |

### 🟡 部分完成 / 持续推进

| Item | 已完成 | 仍缺 |
|---|---|---|
| [item-2 文件读取缓存](./qwen-code-improvement-report-p0-p1-engine.md#item-2) | 查询层 LRU（PR#3581）| 内容层 FileReadCache + 32 批并行 |
| [item-28 Skill 装载性能](./qwen-code-improvement-report-p0-p1-engine.md#item-28) | 子项 #1/#2/#6（PR#3604）| 子项 #3/#4/#5/#7/#8/#9 |

---

## 二、🥇 Tier 1 · P0 高 ROI 必做（本周）

### ① sentSkillNames per-agent 去重（50 行 · 每轮省 1K+ tokens）

**问题**：每个 turn 把全部 skill 列表注入 system prompt。100 skill = 600-1500 tokens × N turn。

**解决方案**（对标 Claude `utils/attachments.ts:2607`）：

```typescript
// packages/core/src/skills/sentSkillNames.ts (新建)
const sentSkillNames = new Map<string, Set<string>>()  // agentId → already-sent

export function getSkillListingDelta(
  agentId: string,
  allSkills: string[]
): string[] {
  const sent = sentSkillNames.get(agentId) ?? new Set()
  if (!sentSkillNames.has(agentId)) sentSkillNames.set(agentId, sent)

  const newOnes = allSkills.filter(name => !sent.has(name))
  newOnes.forEach(name => sent.add(name))
  return newOnes  // 只返回未发送过的
}

export function resetSentSkillNames(): void { sentSkillNames.clear() }
```

**集成点**：
- `packages/core/src/core/prompts.ts` 组装系统提示时调用 `getSkillListingDelta(agentId, ...)` 而不是注入全集
- skill watcher 触发 reload 时调用 `resetSentSkillNames()`
- subagent spawn 时为新 agentId 创建独立 Set
- `/clear` 路径 reset

**度量**：
```bash
# 注入 token 数（before/after）
QWEN_DEBUG_PROMPT_SIZE=1 qwen ...
```

**预期收益**：100 skill 用户每轮省 ~1K token × 10 turn = **每会话省 ~10K token**。

---

### ② FileReadCache 内容层（150 行 · Read-Edit 循环零 I/O）

**问题**：Agent 频繁 Read+Edit 同一文件 —— Read 后 Edit，Edit 后再 Read 验证 —— 每次都从磁盘读，浪费大量 I/O。

**解决方案**（对标 Claude `utils/fileReadCache.ts`）：

```typescript
// packages/core/src/utils/fileReadCache.ts (新建)
import { LRUCache } from 'lru-cache'

interface CachedRead {
  content: string
  mtime: number
  size: number
}

const cache = new LRUCache<string, CachedRead>({ max: 1000 })

export async function readWithCache(filePath: string): Promise<string> {
  const stat = await fs.promises.stat(filePath)
  const cached = cache.get(filePath)

  if (cached && cached.mtime === stat.mtimeMs && cached.size === stat.size) {
    return cached.content  // 命中
  }

  const content = await fs.promises.readFile(filePath, 'utf-8')
  cache.set(filePath, { content, mtime: stat.mtimeMs, size: stat.size })
  return content
}

export function invalidateAfterWrite(filePath: string): void {
  cache.delete(filePath)
}
```

**集成点**：
- `tools/read.ts` `readFile()` 改用 `readWithCache()`
- `tools/edit.ts` / `tools/write.ts` 写入后调 `invalidateAfterWrite()`
- `tools/multiedit.ts` 同上

**度量**：
```bash
# tracer 追 readFile 调用次数
NODE_OPTIONS='--require trace-readfile.cjs' qwen -p "..."
```

**预期收益**：Edit-then-Read（Agent 常见验证模式）从 2 次 I/O → 1 次。10K 行长 session **节省 50%+ 文件 read I/O**。

---

### ③ readManyFiles 32 批并行（30 行 · 多文件场景 1/32 延迟）

**问题**：`utils/readManyFiles.ts` 用 `for...of` 串行读文件 —— 50 个文件 = 50× 累加延迟。

**解决方案**：

```typescript
// 当前（packages/core/src/utils/readManyFiles.ts）
for (const path of paths) {
  const content = await fs.promises.readFile(path)
  // ...
}

// 改为：
const BATCH_SIZE = 32
for (let i = 0; i < paths.length; i += BATCH_SIZE) {
  const batch = paths.slice(i, i + BATCH_SIZE)
  const results = await Promise.all(
    batch.map(path => readWithCache(path))  // 配合 ① 用 cache
  )
  // ...
}
```

**度量**：
```bash
time qwen -p "Read all .ts files in src/ and summarize"
```

**预期收益**：50 文件场景从 ~250ms → ~25ms（**10× 加速**），配合 FileReadCache 后续访问 0ms。

---

## 三、🥈 Tier 2 · P1 下周建议

### ④ MCP / LSP 并行启动（50 行 · 启动 -2-5s）

**问题**：`extensionManager.ts` 串行启动 N 个 MCP server。每个 ~500ms = 累计阻塞主线程。

**解决方案**（对标 [p2-perf item-1](./qwen-code-improvement-report-p2-perf.md#item-1)）：

```typescript
import pMap from 'p-map'

// 当前：for (const server of mcpServers) await connectMCP(server)
// 改为：
await pMap(mcpServers, connectMCP, {
  concurrency: 5,
  stopOnError: false,  // 单个失败不阻塞其他
})
```

LSP 服务器同理。

**预期收益**：5 MCP × 500ms 串行 → 1× 500ms 并行（**-2s 启动延迟**）。

---

### ⑤ 延迟初始化 / lazyImport（80 行 · 冷启动 -300ms）

**问题**：`bootstrap` 阶段同步加载所有大模块（mcp / lsp / channels / arena），实际首轮 80% 用不到。

**解决方案**（对标 [p2-perf item-9](./qwen-code-improvement-report-p2-perf.md#item-9) + [Gemini PR#25758 backport item-58](./qwen-code-gemini-upstream-report-details.md#item-58)）：

```typescript
// 改造目标：
// 1. dynamic import: const mcp = await import('./mcp/...')
// 2. fire-and-forget Promise: experiments + quota fetch 不阻塞 bootstrap
// 3. lazy schema: zod schema 第一次校验时才构建

// 例：
const mcpManagerLazy = lazy(() => import('./mcp/manager'))
async function getMcpManager() {
  return (await mcpManagerLazy()).MCPManager
}
```

**度量**：
```bash
NODE_OPTIONS='--require trace-startup.cjs' qwen --version
# 看 main.ts → first interactive 的 ms
```

**预期收益**：冷启动 -300ms（用户感知明显，从"卡顿 1s+"→"瞬启"）。

---

### ⑥ Git 直读避免进程 Spawn（100 行 · 状态栏 -30ms）

**问题**：状态栏 / commit attribution / git context 注入都用 `spawn('git status')` —— 进程开销 ~30ms × N。

**解决方案**（对标 [p2-perf item-11](./qwen-code-improvement-report-p2-perf.md#item-11)）：

```typescript
// utils/gitDirect.ts (新建)
export async function readHEAD(repoPath: string): Promise<string> {
  // 直读 .git/HEAD 文件（"ref: refs/heads/main\n"）
  const head = await fs.promises.readFile(`${repoPath}/.git/HEAD`, 'utf-8')
  if (head.startsWith('ref: ')) {
    const refPath = head.slice(5).trim()
    return await fs.promises.readFile(`${repoPath}/.git/${refPath}`, 'utf-8')
  }
  return head.trim()  // detached HEAD
}

export async function readBranch(repoPath: string): Promise<string> {
  const head = await fs.promises.readFile(`${repoPath}/.git/HEAD`, 'utf-8')
  if (head.startsWith('ref: refs/heads/')) {
    return head.slice('ref: refs/heads/'.length).trim()
  }
  return 'HEAD'  // detached
}

// 配合 LRU 缓存：
const branchCache = new LRUCache({ max: 100, ttl: 5000 })  // 5s TTL
```

**集成点**：状态栏 `getBranch()` / commit attribution / `<git-context>` 注入。

**预期收益**：每个状态栏更新从 ~30ms → ~1ms。在 1Hz 状态栏更新场景下 **30× 加速**。

---

### ⑦ In-flight 请求合并（80 行 · 并行 subagent 场景去重）

**问题**：并行 subagent 场景下，多个 agent 可能同时请求同一 model + 相同 prompt（如多个并行的 explore agent 都要列项目结构）。

**解决方案**（对标 Claude `coalescing + BoundedUUIDSet`）：

```typescript
// core/inFlightCoalesce.ts (新建)
const inFlight = new Map<string, Promise<Response>>()

export async function coalesce<T>(
  key: string,  // 通常是 hash(model + prompt + tools)
  fetch: () => Promise<T>
): Promise<T> {
  const existing = inFlight.get(key)
  if (existing) return existing as Promise<T>

  const promise = fetch().finally(() => inFlight.delete(key))
  inFlight.set(key, promise)
  return promise
}
```

**集成点**：`openaiContentGenerator/pipeline.ts` / `anthropicContentGenerator.ts` 的入口。

**预期收益**：并行 subagent + 重复请求场景**节省一次 API call 成本**（~$0.01-0.10/次）。

---

## 四、🥉 Tier 3 · P2 按需推进

### TUI 流畅度

| 项 | 文件 | 收益 |
|---|---|---|
| **React.memo 高频组件**（[p2-perf item-25](./qwen-code-improvement-report-p2-perf.md#item-25)）| `HistoryItemDisplay` / `AppHeader` / `ToolGroupMessage` | 高频 re-render 减少 30-50% |
| **WeakRef/WeakMap 防止 GC 保留**（[p2-perf item-18](./qwen-code-improvement-report-p2-perf.md#item-18)）| Map<sessionId, ...> 类强引用 | 长 session 内存增长解决 |
| **正则编译缓存**（[p2-perf item-23](./qwen-code-improvement-report-p2-perf.md#item-23)）| Hook 系统 + LSP hot path | hot path 微秒级加速 |
| **Diff 渲染 useMemo + Regex 预编译**（[p2-perf item-34](./qwen-code-improvement-report-p2-perf.md#item-34)）| `DiffRenderer.tsx` 62 行 regex | diff 切换不卡顿 |

### Shell / Git

| 项 | 收益 |
|---|---|
| **Shell AST 解析缓存**（[p2-perf item-32](./qwen-code-improvement-report-p2-perf.md#item-32)）| 同命令重复执行省 1-2ms |
| **Shell 环境快照 session 级缓存**（[p2-perf item-29](./qwen-code-improvement-report-p2-perf.md#item-29)）| process.env 收集启动期一次性 |
| **Memoization cold start 去重**（[p2-perf item-22](./qwen-code-improvement-report-p2-perf.md#item-22)）| 启动期同一 expensive 计算只跑一次 |

### Tier 4 · P3 边角

| 项 | 适用场景 |
|---|---|
| Bun 原生 API（[item-26](./qwen-code-improvement-report-p2-perf.md#item-26)）| Bun runtime 用户 |
| 编译时 feature gating + DCE（[item-28](./qwen-code-improvement-report-p2-perf.md#item-28)）| bundle 大小 |
| 输出缓冲与防阻塞渲染（[item-6](./qwen-code-improvement-report-p2-perf.md#item-6)）| 大量流式输出 |
| 终端行宽缓存 + Blit screen diff（[item-27](./qwen-code-improvement-report-p2-perf.md#item-27)）| 终端 resize |
| 图片压缩多策略流水线（[item-17](./qwen-code-improvement-report-p2-perf.md#item-17)）| paste 大图 |

---

## 五、度量驱动方法（参考 PR#3581 范式）

每个 perf PR 应带 baseline vs after 数字。tracer 模板：

### A. Sync I/O tracer（PR#3581 已有）

```bash
# /tmp/qwen-trace/trace-sync-io.cjs（PR body 含完整脚本）
NODE_OPTIONS='--require /tmp/qwen-trace/trace-sync-io.cjs' \
QWEN_TRACE_WARMUP_MS=4000 \
qwen -p "<test prompt>"

cat /tmp/qwen-trace/summary.${PID}.txt
# 看 unique_sites + total_calls
```

### B. 启动延迟 tracer

```bash
# /tmp/qwen-trace/trace-startup.cjs（建议新建）
const startTime = process.hrtime.bigint()
const phases = []

require('module').prototype.require = new Proxy(...)  // 拦截每个 require
// 记录每个模块加载时间

process.on('exit', () => {
  console.log(`Total: ${Number(process.hrtime.bigint() - startTime) / 1e6}ms`)
  console.log('Top 10 slow modules:', phases.sort((a,b) => b.dur - a.dur).slice(0, 10))
})
```

### C. Token 注入开销

```bash
QWEN_DEBUG_PROMPT_SIZE=1 qwen -p "..."
# 输出每轮 system prompt 大小（chars + estimated tokens）
```

### D. 内存泄漏

```bash
NODE_OPTIONS='--inspect --max-old-space-size=512' qwen --resume <long-session>
# 用 chrome devtools 看 heap snapshot
```

### E. 文件 I/O tracer

```js
// trace-readfile.cjs
const fs = require('fs')
const orig = fs.promises.readFile
fs.promises.readFile = function(path, ...args) {
  console.error(`[readFile] ${path}`)
  return orig.call(this, path, ...args)
}
```

---

## 六、PR 工作流建议（学 PR#3581 + PR#3604 范式）

### PR description 模板

```markdown
## Summary
<一句话说明改动 + 度量结果>

## Reproducing the measurement
1. Tracer 脚本（贴完整源码或路径）
2. 测试 prompt（让 reviewer 能复现）
3. Before/After 数字对比

### Before (commit <baseline-sha>)
<tracer 输出>

### After (this PR)
<tracer 输出>

## Test plan
- [x] vitest run packages/core
- [x] vitest run packages/cli
- [x] Manual: <场景描述>
```

### 拆分原则

不要把多个独立优化塞进一个 PR。PR#3581 拆 3 commit（async write / LRU cache / regression test）就是好范式：每个 commit 自洽 + 可独立 review。

### 风险控制

- 缓存类改动 **必须有失效路径**（如 `invalidateAfterWrite`）
- 并行类改动 **必须保留串行 fallback**（如 `--no-parallel` flag）
- 异步化改动 **必须 graceful shutdown**（`Config.shutdown()` await flush）

---

## 七、不推荐方向（已不再有意义）

| 不推荐 | 原因 |
|---|---|
| 编写自己的 ink fork | 已有 `@jrichman/ink@6.6.7`（Claude Code 用） |
| 单独优化 OSC 8 / 11 | 内部专精团队（chiga0/Edenman）已覆盖 |
| 大改 `query.ts` 主循环 | 内部决策权 + 影响面太大，不会被 review |
| 自实现 LSP 协议 | 已有 vscode-languageclient |

---

## 八、相关文档

- [改进报告主矩阵](./qwen-code-improvement-report.md) —— 全部 275 项 + PR 追踪
- [P0/P1 引擎优化（28 项）](./qwen-code-improvement-report-p0-p1-engine.md)
- [P2 性能优化（35 项）](./qwen-code-improvement-report-p2-perf.md)
- [启动优化 Deep-Dive](./startup-optimization-deep-dive.md)
- [Prompt Cache 优化 Deep-Dive](./prompt-cache-optimization-deep-dive.md)
- [Bun 原生 API 优化 Deep-Dive](./bun-native-api-optimization-deep-dive.md)
- [文件读取缓存 Deep-Dive](./file-read-cache-deep-dive.md)
- [同步 I/O 异步化 Deep-Dive](./sync-io-async-deep-dive.md)

---

**最后更新**：2026-04-28
**状态**：active roadmap，每两周更新一次
**反馈**：在 codeagents 仓库提 issue / 在 qwen-code 仓库提 PR
