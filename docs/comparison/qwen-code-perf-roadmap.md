# Qwen Code 性能优化 Roadmap

> 基于 codeagents 全部性能相关 item 的统一 roadmap —— 按 ROI 排序的可执行优化清单。
>
> **数据来源**：[改进报告 P0/P1 引擎优化](./qwen-code-improvement-report-p0-p1-engine.md) + [P2 性能优化](./qwen-code-improvement-report-p2-perf.md) + 实际源码审计 + 已合并 PR 度量数据

---

## ⚠️ 多轮源码审计修正记录（v1 → v2，2026-04-28）

v1 版本部分声明经源码审计后需修正。本版（v2）修正以下问题：

| v1 错误 | 实际情况 | 影响 |
|---|---|---|
| 声称 **MCP 服务器串行启动** | `tools/mcp-client-manager.ts:137,459,514` 已用 `Promise.all(discoveryPromises)` 并行 | 项 ④ 改为：MCP 已并行，**仅"扩展加载默认路径"和 LSP 还有串行问题** |
| 代码示例用 `lru-cache` / `p-map` | 这两个包**都不在 `packages/core/dependencies` 里**；`p-limit@7.3.0` 在 `packages/cli` 里 | 改用 Map 实现 LRU 或加 dep；并行用 `p-limit` |
| 声称工具是"同步加载" | 工具**已经 lazy-loaded**（`config.ts:2580-2628` 全部 `await import('../tools/...')`）| 项 ⑤ 改为：**`toolRegistry.warmAll()` 反而 eager 加载所有 lazy 工具**——真正的 gap 是避免 warmAll，让 first-use 触发 import |
| 漏看 readManyFiles **同步 I/O** | `readManyFiles.ts:107` 仍有 `existsSync + statSync`（PR#3581 没改到这处）| 项 ③ 增加：把 sync I/O 改 async + 同时 32 批并行 |
| 声称 **PR#3013 已合并**（"SlicingMaxSizedBox + useStableHeight"）| 实际 **PR#3013 CLOSED**（2026-04-24 未合并）。flicker 由 **PR#3591 (MERGED 2026-04-25)** 处理。`MaxSizedBox` 基础设施来自上游 Gemini CLI（PR#1217 等）非 PR#3013 | 已完成基线表移除 PR#3013，改为标注 MaxSizedBox 来自 upstream + PR#3591 是真正的 flicker foundation |
| 声称 **`<available_skills>` 注入到 system prompt** | 实际是注入到 **SkillTool description 字段**（`tools/skill.ts:182`），随 tool schema 在每次 API 请求中发送 | 项 ① 集成点改为 `tools/skill.ts` 而非 `prompts.ts` |
| 没区分 PR#3636 vs ⑦ | PR#3636 是 "concurrency cap"（上限），项 ⑦ 是 "request dedupe"（合并），是不同概念 | 项 ⑦ 加注：与 PR#3636 共存，不冲突 |

剩余声明（① sentSkillNames / ② FileReadCache / ⑥ Git execSync / ⑦ in-flight coalesce）经审计**确认正确**。

---

---

## 速查表 · 一页读懂

```
✅ 已完成（基线）
   PR#3581 · sync I/O hot path 110→10 (-91%)
   PR#3591 · TUI flicker foundation
   MaxSizedBox · 渲染前裁剪基础设施（来自 upstream，非 PR#3013）
   PR#3013 · CLOSED（2026-04-24，未合并；flicker 由 PR#3591 解决）
   PR#3604 · Skill 并行加载 + conditional 激活（item-28 子项 1+2+6）

🥇 P0 本周（建议）
   ① sentSkillNames 去重                    50 行   每轮省 1K token
   ② FileReadCache 内容层（Map LRU 无 dep）  150 行  Read-Edit 循环零 I/O
   ③ readManyFiles 32 批并行 + 同步 I/O 异步  80 行   多文件 I/O 1/32 + 消除 PR#3581 漏改的 sync I/O

🥈 P1 下周
   ④ Extension 默认目录加载并行 + LSP 并行  50 行  启动 -1-3s
     （注：MCP discovery 已 Promise.all 并行，无需改）
   ⑤ 避免 warmAll() + lazy import      80 行  冷启动 -300ms
     （注：工具已 lazy，warmAll 反而 eager 触发所有 import）
   ⑥ Git 直读避免 spawn (execSync)    100 行  状态栏 -30ms
   ⑦ in-flight 请求合并 (request dedup) 80 行  并行 subagent 节省 API

🥉 P2-P3 按需
   ⑧ React.memo 高频组件 / ⑨ WeakRef 长 session 内存 / ⑩ 正则编译缓存 /
   ⑪ Shell AST 解析缓存 / ⑫ 终端行宽缓存 / ⑬ Bun 原生 API 等
```

**总投入**：P0+P1 约 **8-10 天 × 1 人 / ~590 行代码**，预期收益：每轮节省 1K+ tokens、冷启动 -300ms、文件 I/O 1/32 + 消除 sync I/O、Extension 启动 -1.6s、状态栏 -30ms、并行 subagent 节省 API 成本。

---

## 一、已完成基线（不重复推进）

> 这些 PR 已合并 / 进行中，不要再重复实现。

### ✅ MERGED（2026-04 期间）

| PR | 内容 | 度量 |
|---|---|---|
| **[PR#3581](https://github.com/QwenLM/qwen-code/pull/3581)** | sync I/O hot path | 110→10 syscall/prompt（**-91%**）|
| **[PR#3591](https://github.com/QwenLM/qwen-code/pull/3591)** | TUI flicker foundation | throttle + pre-slice + soft-wrap 抑制 + 同步终端 allowlist |
| **MaxSizedBox 基础**（自 Gemini upstream PR#1217 等多 PR）| 渲染前裁剪到 maxLines（基础设施层）| 已有 fork 期前的能力 |
| **[PR#3604](https://github.com/QwenLM/qwen-code/pull/3604)** | Skill 并行加载 + path-conditional 激活 | item-28 子项 #1+#2+#6 |

### 🟡 部分完成 / 持续推进

| Item | 已完成 | 仍缺 |
|---|---|---|
| [item-2 文件读取缓存](./qwen-code-improvement-report-p0-p1-engine.md#item-2) | 查询层 LRU（PR#3581）| 内容层 FileReadCache + 32 批并行 |
| [item-28 Skill 装载性能](./qwen-code-improvement-report-p0-p1-engine.md#item-28) | 子项 #1/#2/#6（PR#3604）| 子项 #3/#4/#5/#7/#8/#9 |

---

## 二、🥇 Tier 1 · P0 高 ROI 必做（本周）

### ① sentSkillNames per-agent 去重（50 行 · 每轮省 1K+ tokens）

**问题**：每个 API 调用把全部 skill 列表通过 **SkillTool description** 注入（`tools/skill.ts:182-184` `<available_skills>${skillDescriptions}</available_skills>`）。100 skill = 600-1500 tokens × N API call。

> **审计修正**：原 v1 描述说"注入 system prompt"，实际是注入到 **SkillTool 的 description 字段**，会随 tool schema 在每次 API 请求中发送。优化机制相同，但实现位置是 **`tools/skill.ts` 而不是 `prompts.ts`**。

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
- `packages/core/src/tools/skill.ts:182` `<available_skills>${skillDescriptions}</available_skills>` 改为按 agentId 过滤，只列入未发送过的 skill
- 同时通过 `<system-reminder>` 注入新 skill 通知（保留模型可见性）
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

> **依赖说明**：`packages/core` 当前**没有 `lru-cache` 依赖**，需要选一个：①加 dep；②自己实现简易 LRU（Map + insertion order）。下面给出无依赖版本：

```typescript
// packages/core/src/utils/fileReadCache.ts (新建)
import * as fs from 'node:fs/promises'

interface CachedRead {
  content: string
  mtime: number
  size: number
}

const MAX = 1000
const cache = new Map<string, CachedRead>()  // Map 保留 insertion order

export async function readWithCache(filePath: string): Promise<string> {
  const stat = await fs.stat(filePath)
  const cached = cache.get(filePath)

  if (cached && cached.mtime === stat.mtimeMs && cached.size === stat.size) {
    // LRU: 命中后移到末尾
    cache.delete(filePath)
    cache.set(filePath, cached)
    return cached.content
  }

  const content = await fs.readFile(filePath, 'utf-8')
  if (cache.size >= MAX) {
    // 删除最早的 entry（Map iteration order = insertion order）
    const oldestKey = cache.keys().next().value
    if (oldestKey) cache.delete(oldestKey)
  }
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

### ③ readManyFiles 32 批并行 + 同步 I/O 异步化（80 行 · 多文件场景 1/32 延迟）

**问题**：`packages/core/src/utils/readManyFiles.ts:104-127` 有**两个问题**：

1. `for (const rawPattern of inputPatterns)` 串行 —— 50 文件 = 50× 累加延迟
2. **`readManyFiles.ts:107` 仍有 sync I/O**：`fs.existsSync(fullPath) ? fs.statSync(fullPath) : null` —— PR#3581 没覆盖这处（PR#3581 改的是 `chatRecordingService` + `fileUtils` + `paths` + `workspaceContext` + `ripGrep`）

**解决方案**：

```typescript
// packages/core/src/utils/readManyFiles.ts:104（改造前）
for (const rawPattern of inputPatterns) {
  const fullPath = path.resolve(projectRoot, normalizedPattern)
  const stats = fs.existsSync(fullPath) ? fs.statSync(fullPath) : null  // ← sync I/O
  if (stats?.isDirectory()) { ... }
  if (stats?.isFile() && !seenFiles.has(fullPath)) {
    seenFiles.add(fullPath)
    const readResult = await readFileContent(config, fullPath)  // ← 串行
    // ...
  }
}

// 改造后：
const BATCH_SIZE = 32
const resolvedPatterns = inputPatterns.map(p => ({
  raw: p,
  full: path.resolve(projectRoot, p.replace(/\\/g, '/')),
}))

// 第一阶段：并行 stat（替代 sync existsSync + statSync）
const statResults = await Promise.all(
  resolvedPatterns.map(async ({ full }) => {
    try {
      return { full, stats: await fs.promises.stat(full) }
    } catch (err: any) {
      if (err.code === 'ENOENT') return { full, stats: null }
      throw err
    }
  })
)

// 第二阶段：分类 + 32 批并行读取
const fileItems = statResults.filter(r => r.stats?.isFile() && !seenFiles.has(r.full))
const dirItems = statResults.filter(r => r.stats?.isDirectory())

for (let i = 0; i < fileItems.length; i += BATCH_SIZE) {
  const batch = fileItems.slice(i, i + BATCH_SIZE)
  const results = await Promise.all(
    batch.map(({ full }) => {
      seenFiles.add(full)
      return readFileContent(config, full)  // 配合 ② 用 readWithCache
    })
  )
  // 合并 contentParts / files
}

// 目录递归保持顺序（避免内存爆炸）
for (const { full } of dirItems) {
  const { contentParts: dp, info } = await readDirectory(config, full)
  contentParts.push(...dp)
  files.push(info)
}
```

**度量**：
```bash
time qwen -p "Read all .ts files in src/ and summarize"
```

**预期收益**：50 文件场景从 ~250ms → ~25ms（**10× 加速**）+ sync I/O 消除。配合 FileReadCache 后续访问 0ms。

---

## 三、🥈 Tier 2 · P1 下周建议

### ④ Extension 默认目录加载 + LSP 并行启动（50 行 · 启动 -1-3s）

**审计修正**：

- **MCP discovery 已经并行**（`tools/mcp-client-manager.ts:137,459,514` 用 `Promise.all(discoveryPromises)`）。**不需要改 MCP**
- **真正的 gap 在两处**：

#### 4a. Extension 默认目录加载仍串行

`extension/extensionManager.ts:559` 默认路径加载是串行：

```typescript
// 改造前（串行）
extensions = []
for (const subdir of subdirs) {
  const extension = await this.loadExtension({ extensionDir, ... })  // ← 串行
  if (extension) extensions.push(extension)
}

// 改造后（并行，10 extensions × 200ms 串行 → 200ms 并行）
import pLimit from 'p-limit'  // packages/cli 已有 p-limit@7.3.0，但 core 需加 dep
const limit = pLimit(5)
extensions = (await Promise.all(
  subdirs.map(subdir => limit(() => this.loadExtension({
    extensionDir: path.join(userExtensionsDir, subdir),
    workspaceDir: this.workspaceDir,
  })))
)).filter((e): e is Extension => e !== null)
```

> 命名查找路径（`extensionManager.ts:545`）已经是 `Promise.all`，仅默认全量加载是串行。

#### 4b. LSP 服务器启动顺序待审计

```bash
# 验证命令
grep -n "for.*await\|Promise.all" packages/core/src/lsp/*.ts | grep -v test
```

如果 LSP 启动是串行（待审计），加 `pLimit(3)` 并行启动 TypeScript / Python / Go。

**预期收益**：10 个用户级 extension 串行 2s → 并行 ~400ms（**-1.6s 启动**）。

---

### ⑤ 避免 `toolRegistry.warmAll()` 全量预热 + 延迟初始化（80 行 · 冷启动 -300ms）

**审计修正**：Qwen Code 工具**已经 lazy-loaded**（`config/config.ts:2580-2628` 全部 `await import('../tools/...')`）。**真正的 gap 是 `warmAll()` 反而 eager 触发了所有 lazy import**：

```typescript
// 当前问题：3 处都在 init 路径调 warmAll()
// packages/core/src/core/client.ts:231              await toolRegistry.warmAll()
// packages/core/src/core/geminiChat.ts:948          await toolRegistry.warmAll()
// packages/core/src/agents/runtime/agent-core.ts:307 await toolRegistry.warmAll()
```

**`warmAll()` 同步触发所有 ~30 个工具的 `await import(...)`**，本来 lazy 的设计被破坏。

**解决方案**：

#### 5a. 把 `warmAll()` 改为 lazy first-use

```typescript
// tool-registry.ts
async warmAll(options?: { strict?: boolean }): Promise<void> {
  // 改为：仅 strict mode（如启动期 schema validation）才真正 warm，
  // 普通 init 路径返回立即（让 ensureTool() 在第一次调用时 lazy import）
  if (!options?.strict) return
  // 原来的 warmAll 逻辑保留供 strict 场景
}
```

调用者（client.ts / geminiChat.ts / agent-core.ts）**默认不再调 warmAll**，只在确实需要全量 schema 时才调。

#### 5b. 静态 import 改 lazy

```typescript
// config.ts:14 当前
import { ArenaAgentClient } from '../agents/arena/ArenaAgentClient.js'

// 改为：
let _ArenaAgentClient: typeof import('../agents/arena/ArenaAgentClient.js').ArenaAgentClient | undefined
async function getArenaAgentClient() {
  if (!_ArenaAgentClient) {
    _ArenaAgentClient = (await import('../agents/arena/ArenaAgentClient.js')).ArenaAgentClient
  }
  return _ArenaAgentClient
}
```

#### 5c. fire-and-forget experiments / quota fetch（如有）

对标 [Gemini PR#25758 backport item-58](./qwen-code-gemini-upstream-report-details.md#item-58)，把启动期的远程 fetch 改为不阻塞 bootstrap。

**度量**：
```bash
NODE_OPTIONS='--require trace-startup.cjs' qwen --version
# 看 main.ts → first interactive 的 ms
```

**预期收益**：冷启动 -300ms（删 warmAll 单项就能拿大头）。

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

### ⑦ In-flight 请求合并 / dedupe（80 行 · 并行 subagent 场景去重）

> **审计提示**：[PR#3636](https://github.com/QwenLM/qwen-code/pull/3636) OPEN 是 `cap concurrent in-flight requests per provider`，**与本项不同** —— PR#3636 做"并发上限"（rate limiting），本项做"相同请求合并"（dedupe）。两者可共存。


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
