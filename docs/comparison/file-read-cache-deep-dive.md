# Qwen Code 改进建议 — 文件读取缓存与批量并行 I/O (File Read Cache & Parallel I/O)

> 核心洞察：代码 Agent 最频繁的底层操作就是文件 I/O。当 Agent 需要综合上下文分析 10 个文件，或者在一个回合中修改某个文件后立即重读该文件以验证时，缓慢的磁盘读取会极大拖慢响应速度。Claude Code 通过内存 LRU 缓存、mtime 自动失效机制以及 `Promise.all` 批量并发，将这部分耗时压缩到了极致。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 🟢 进度追踪（2026-05-06 更新）

**当前状态**：🟡 **3 阶段中 2 阶段已完成**（FileReadCache ✓ + sync I/O 异步化 ✓，仅"32 批并行"仍待）。

| 阶段 | 描述 | PR | 状态 |
|---|---|---|---|
| **Stage 1** | FileReadCache 内存缓存层 | [PR#3717](https://github.com/QwenLM/qwen-code/pull/3717) | ✅ **2026-04-30 合并 +1212/-10** |
| **Stage 2** | 32 批并行 `readManyFiles` | — | ❌ 仍未实现 |
| **Stage 3** | 同步 I/O 异步化（hot path 91%）| [PR#3581](https://github.com/QwenLM/qwen-code/pull/3581) | ✅ **2026-04-24 合并** |
| **Bugfix** | FileReadCache invalidation 5 条遗漏路径 | [PR#3810](https://github.com/QwenLM/qwen-code/pull/3810) | ✅ **2026-05-04 合并 +579/-0**（修复 #3805 "read tool returns no content in long-running sessions"）|
| **Follow-up A** | 强制 prior-read（Edit/WriteFile）| [PR#3774](https://github.com/QwenLM/qwen-code/pull/3774) | ✅ **2026-05-06 合并 +1891/-118**（体量从 OPEN 时 +611/-2 增长 3x）|
| **Follow-up B** | file-changed-since-read 拒绝 | [PR#3840](https://github.com/QwenLM/qwen-code/pull/3840) | 🟡 OPEN |

**Stage 1 / Stage 3 详解见 [§四 已落地内容详解](#四-已落地内容详解2026-04-到-2026-05)**；prior-read 守卫的双轨设计见 [§五](#五-prior-read-enforcement-双轨设计-pr3774--pr3840)。

## 一、实现差异与性能分析

### 1. Qwen Code 的当前实现：串行、无缓存
在 `packages/core/src/utils/readManyFiles.ts` 中，Qwen Code 处理多文件读取的核心逻辑如下：

```typescript
// Qwen Code: 使用 for...of 串行等待每一个读取完成
for (const rawPattern of inputPatterns) {
    const fullPath = path.resolve(projectRoot, normalizedPattern);
    const stats = fs.existsSync(fullPath) ? fs.statSync(fullPath) : null;
    
    // ...
    if (stats?.isFile() && !seenFiles.has(fullPath)) {
        seenFiles.add(fullPath);
        // 阻塞式的串行 await
        const readResult = await readFileContent(config, fullPath);
        // ...
    }
}
```
**瓶颈**：
- **串行 I/O**：读取 30 个文件，总耗时为 `t1 + t2 + ... + t30`。如果遇到机械硬盘或远程挂载目录（如 WSL、NFS），延迟会被放大几十倍。
- **热点文件无缓存**：在多轮对话中，Agent 可能反复查阅同一个核心文件（如 `package.json` 或 `agent-core.ts`），Qwen Code 每次都会重新触发完整的磁盘读取。
- **主线程阻塞**：部分底层操作（如 `fs.statSync`）还在使用同步方法，会短暂阻塞 Node.js 事件循环。

### 2. Claude Code 的解决方案：三层优化
Claude Code 在 `utils/fileReadCache.ts` 以及文件搜索相关逻辑中，打出了一套性能组合拳：

#### 第一层：LRU 内存缓存与 Mtime 失效 (`FileReadCache`)
它在进程内维护了一个单例的 LRU Map（上限 1000 条），键为文件路径。
```typescript
// Claude Code: fileReadCache.ts
const stats = fs.statSync(filePath);
const cachedData = this.cache.get(cacheKey);

// 如果 mtime 没变，直接返回内存数据，磁盘开销降至 0
if (cachedData && cachedData.mtime === stats.mtimeMs) {
    return { content: cachedData.content, encoding: cachedData.encoding };
}
```
这保证了“一旦被修改（mtime变化），缓存立刻失效”，而“未修改的频繁读取，耗时为 0”。

#### 第二层：批量并发读取
在需要读取多文件时，它采用了分批（Batching）加 `Promise.all` 并发：
```typescript
// Claude Code
const READ_BATCH_SIZE = 32;
// 对每批 32 个文件同时发起异步读取，耗时等于最慢的那个文件，而不是总和
await Promise.all(batch.map(file => readFile(file)));
```

#### 第三层：并发获取元数据
不仅是读内容，对于大目录扫描（需要获取几百个文件的 stat），也是用并发：
```typescript
// 并发 stat 检查修改时间
await Promise.all(filePaths.map(lstat));
```

## 二、Qwen Code 的改进路径 (P1 优先级)

为了优化大中型代码库的探索速度和多轮交互的延迟，Qwen Code 需要重构底层文件系统交互层。

### 阶段 1：引入 FileReadCache (内存缓存层)
1. 在 `packages/core/src/utils/` 下新建 `fileReadCache.ts`。
2. 实现基于 `mtimeMs`（修改时间戳）的缓存校验逻辑，最大缓存数限制在 1000 左右防止 OOM。
3. 改造 `readFileContent` 优先走 `fileReadCache.readFile()`。

### 阶段 2：改造串行 I/O 为并发 (Concurrency)
1. 梳理 `readManyFiles.ts`。对于目录遍历可以保留顺序或队列，但对于明确指定的 `inputPatterns` 文件列表，应该先通过并发 `fs.promises.stat` 过滤出有效文件。
2. 随后使用 `Promise.all(files.map(f => readFileContent(f)))` 进行并发提取。
3. 建议设置合理的并发上限（如 `p-limit` 或固定批次 32），防止同时打开过多文件描述符抛出 `EMFILE` 错误。

### 阶段 3：解阻塞主线程
1. 盘点整个项目中的 `fs.statSync`、`fs.readFileSync`（特别是在 `getFolderStructure.ts` 和 `workspaceContext.ts` 这类高频热点中）。
2. 将非初始化阶段的 Sync 操作全部替换为异步 `promises` API，避免在文件 I/O 期间冻结终端 UI 的渲染或键盘事件接收。

## 三、改进收益评估
- **实现成本**：低到中等。涉及部分底层工具类改动，风险可控（只需做好并发控制和缓存一致性）。
- **直接收益**：
  1. **显著缩短等待**：阅读多文件或全目录时的速度理论上提升几倍至数十倍（取决于磁盘和并发数）。
  2. **消除无谓 IO**：在反复 Edit-Read 的开发循环中，极大地减轻了磁盘压力，让交互响应像读内存一样迅速。

---

## 四、已落地内容详解（2026-04 到 2026-05）

### 4.1 Stage 3 — Sync I/O 异步化（PR#3581 ✓ 2026-04-24 合并）

**度量**：单轮 prompt 主循环 sync fs 调用 **110 → 10（-91%）**。

PR 拆 3 个 commit：

| 阶段 | 调用数 | 改动 |
|---|---|---|
| 1. `appendRecord` 异步化 | 110 → 20 | `chatRecordingService` 每 event 4 syscall → fire-and-forget `writeChain` promise；`Config.shutdown()` await `flush()`；`jsonl.writeLine` 改用 `fs.promises.mkdir/appendFile` |
| 2. **热路径 fs 查询缓存** | 20 → 10 | bounded LRU：`workspaceContext.fullyResolvedPath` / `paths.validatePath`（positive only，ENOENT 不缓存）/ `ripGrep .qwenignore` 发现；`fileUtils` 删 `existsSync` pre-check（改用 `fs.promises.stat` ENOENT→`FILE_NOT_FOUND`） |
| 3. 测试 + `_reset*ForTest` + 回归守卫 | — | ENOENT-not-cached / `flush()` 早 resolve / write 失败不阻塞 chain |

**工程质量亮点**：PR body 含完整 tracer 脚本（`trace-sync-io.cjs` ~160 行）+ 可复现度量步骤 + reentrancy guard / PID-suffixed 输出 / warmup 窗口等细节。

### 4.2 Stage 1 — FileReadCache（PR#3717 ✓ 2026-04-30 合并 +1212/-10）

**与 Claude 设计的关键差异**：

| 维度 | Claude `fileReadCache.ts` | Qwen `FileReadCache`（PR#3717）|
|---|---|---|
| 缓存对象 | **完整文件内容**（1000 条 LRU + mtime 失效）| **占位符短路标记**（不缓存内容，只记"模型已看过整文件"）|
| Key | path string | **`(dev, ino)` 元组** —— 防符号链接/重命名假命中 |
| API 形态 | `get()` / `set()` | **三态 `check()` API**：`hit-fresh` / `hit-stale` / `miss` |
| 节省方式 | 内容回写省 token | 短占位符替代全文回写（让模型回看 prior tool result）|
| 度量 | — | `READ_FILE_CACHE_*` env 变量驱动可观测度量（不承诺数字，按 session 形态评估）|
| 拓展 | — | 三态 API 设计上**预留给后续 Edit/WriteFile 强制"必须先读"守卫**（参见 §五 PR#3774）|

**Qwen 选择的设计哲学**：不是直接 port Claude 的"缓存内容"路线，而是用占位符短路 + (dev,ino) key + 三态 API 实现**协议层去重**——比内容缓存更轻量（不占内存且天然支持 GC），且 API 预留给后续守卫机制。

**Range/非文本/截断兼容**：Range 读、非文本载荷、截断读、Write 后 Read 都走完整管道（保证任何实际内容变化都能反映到模型）。

### 4.3 Stage 1 关键 bugfix — invalidation 5 条遗漏路径（PR#3810 ✓ 2026-05-04 合并 +579/-0）

**修复 [#3805](https://github.com/QwenLM/qwen-code/issues/3805)** "read tool returns no content in long-running sessions"。

**问题本质**：FileReadCache 的占位符**依赖 prior tool result 仍在 history**；任何 history rewrite 都会让占位符指向已删除的 prior result，导致 Read 在 tool 层成功但 LLM 拿到空内容。

**PR#3717 wired invalidation 到 2 条路径**：

| 路径 | 触发场景 | 是否 clear cache（PR#3717 之后）|
|---|---|---|
| `tryCompressChat` | auto compaction | ✓ |
| `Config.startNewSession` | `/clear`、session resume | ✓ |

**PR#3810 multi-round audit 发现 5 条遗漏路径**：

| 路径 | 触发场景 | 修复前 |
|---|---|---|
| `microcompactHistory` | idle cleanup（≥60min）| ❌ → ✓ |
| `GeminiClient.setHistory` | `/restore` / `/load_history` | ❌ → ✓ |
| `GeminiClient.truncateHistory` | rewind | ❌ → ✓ |
| `GeminiClient.resetChat` | 公共 API | ❌ → ✓ |
| `stripOrphanedUserEntriesFromHistory` | retry path | ❌ → ✓ |

**集成测试方法**：用真实 `ReadFileTool` + on-disk 文件 + 真实 `microcompactHistory` 复现 bug——是工程上扎实的回归保障。

**架构教训**：FileReadCache 的占位符**与 history 状态强耦合**——任何修改 history 的代码都必须 clear cache。这种"散落 in/validation"风险在引入时未充分识别，audit 后才浮现。

---

## 五、prior-read enforcement 双轨设计（PR#3774 + PR#3840）

PR#3717 的 FileReadCache 三态 API（`hit-fresh` / `hit-stale` / `miss`）**预留**了 prior-read 守卫的实现。两个 PR 从不同方向使用此能力：

| PR | 方向 | 触发条件 | 错误码 | 状态 |
|---|---|---|---|---|
| **[PR#3774](https://github.com/QwenLM/qwen-code/pull/3774)** | 必须先读 | Edit/WriteFile 时 cache `miss` | `EDIT_REQUIRES_PRIOR_READ` | ✅ **2026-05-06 合并 +1891/-118** |
| **[PR#3840](https://github.com/QwenLM/qwen-code/pull/3840)** | 读后未变 | Edit/WriteFile 时 cache `hit-stale`（mtime 已变）| `FILE_CHANGED_SINCE_READ` | 🟡 OPEN |

**为什么需要双轨**：
- PR#3774 挡的是"模型凭想象 Edit"——`old_string` 恰好碰巧匹配文件中真实存在的串，但模型从未读过该文件
- PR#3840 挡的是"读后被外部修改"——模型读了文件、规划了 Edit，但中间用户/其他工具改了文件，再 Edit 会基于过时认知

**与 Claude 对比**：Claude Code 也有类似的"未读必读" + "modified outside" 双重检查，但实现散落在 EditTool / WriteFileTool 内部；Qwen 通过 FileReadCache 的三态 API 把这个能力**抽象到缓存层**——任何调用方都能直接判断状态，更可复用。

**合并后效果**：Stage 1 从"性能优化"升级为"模型可信度强制约束"——FileReadCache 不只是省 token，还是 Edit 正确性的工程基础。

---

## 六、剩余 gap：Stage 2 (32 批并行 readManyFiles)

仍未实现的部分：

```typescript
// 当前 packages/core/src/utils/readManyFiles.ts
for (const rawPattern of inputPatterns) {
    const fullPath = path.resolve(projectRoot, normalizedPattern);
    const stats = fs.existsSync(fullPath) ? fs.statSync(fullPath) : null;
    // ... 串行 await readFileContent ...
}
```

**Claude 风格目标**：

```typescript
const READ_BATCH_SIZE = 32;
for (const batch of chunkArray(filePaths, READ_BATCH_SIZE)) {
  await Promise.all(batch.map(file => readFileContent(file)));
}
```

**实现成本**：~100 行（含 batch 分块 + p-limit 控制 + EMFILE 错误处理）。

**收益**：30 个文件读取耗时从"30 × t"降到"max(t)"，在 NFS / WSL / 大型 monorepo 场景下提升数十倍。

**为什么没人做**：可能因为 PR#3717 的 FileReadCache 已经覆盖了"重复读同一文件"的最大热点（多轮对话场景），而批量并行优化"首次读多文件"的 cold path 收益相对较小。但仍是合理的 follow-up。

---

## 七、相关 item 在 Qwen Code Improvement Report 中的状态

参考 [item-2 文件读取缓存 + 批量并行 I/O](./qwen-code-improvement-report-p0-p1-engine.md#item-2)：

| 子项 | 状态 |
|---|---|
| 查询缓存（路径解析 / .qwenignore）| ✅ PR#3581 |
| FileReadCache（内容/占位符缓存）| ✅ PR#3717 |
| invalidation 5 条遗漏路径 | ✅ PR#3810 |
| sync I/O 异步化（hot path 91%）| ✅ PR#3581 |
| 32 批并行 readManyFiles | ❌ 仍未实现 |
| prior-read 守卫（必须先读）| ✅ PR#3774 已于 2026-05-06 合并（+1891/-118）|
| file-changed-since-read 拒绝 | 🟡 PR#3840 OPEN |

主体已实现（5/7 子项 ✓ + 2/7 OPEN），仅剩 32 批并行 cold path 优化。