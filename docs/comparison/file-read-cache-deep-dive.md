# Qwen Code 改进建议 — 文件读取缓存与批量并行 I/O (File Read Cache & Parallel I/O)

> 核心洞察：代码 Agent 最频繁的底层操作就是文件 I/O。当 Agent 需要综合上下文分析 10 个文件，或者在一个回合中修改某个文件后立即重读该文件以验证时，缓慢的磁盘读取会极大拖慢响应速度。Claude Code 通过内存 LRU 缓存、mtime 自动失效机制以及 `Promise.all` 批量并发，将这部分耗时压缩到了极致；而 Qwen Code 目前使用的是无缓存的顺序（串行）读取。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

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