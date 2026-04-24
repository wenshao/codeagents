# Qwen Code 改进建议 — 同步 I/O 异步化 (Sync I/O Asynchronization)

> 核心洞察：Node.js 是单线程事件驱动（Event Loop）的模型。当应用程序在主线程中调用 `readFileSync` 或 `statSync` 等同步 I/O 函数时，整个事件循环会被完全冻结。对于一个重度操作磁盘的 CLI Agent 而言，在热点路径（Hot Path）上的几毫秒同步阻塞，不仅会让流式输出动画（Spinner）卡顿，更会导致用户的盲打输入事件丢失。Claude Code 几近偏执地消灭了除初始化阶段外的所有 Sync I/O。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

> **🟡 进度追踪（2026-04-24）**：[**PR#3581**](https://github.com/QwenLM/qwen-code/pull/3581) OPEN —— `perf(core): cut runtime sync I/O on tool hot path by 91%` 直接对标本文方向。**度量：hot path 110 → 10 syscall/prompt（-91%）**。
>
> **3 个 commit 拆分**：
>
> | 阶段 | 调用数 | 核心改动 |
> |---|---|---|
> | 1. `appendRecord` 异步化 | 110 → 20 | `chatRecordingService` 每 event 4 syscall（existsSync + mkdirSync + existsSync + appendFileSync）→ fire-and-forget `writeChain` promise；`lastRecordUuid` 保持同步更新以维护 `parentUuid` 链；`Config.shutdown()` await 新增 `flush()` 确保无数据丢失；`jsonl.writeLine` 改用 `fs.promises.mkdir/appendFile` |
> | 2. hot-path fs 查询 LRU 缓存 | 20 → 10 | `workspaceContext.fullyResolvedPath` / `paths.validatePath`（positive only，ENOENT 不缓存）/ `ripGrep .qwenignore` 发现；`fileUtils` 删 `existsSync` pre-check 改 `fs.promises.stat` ENOENT→`FILE_NOT_FOUND` |
> | 3. 测试 + `_reset*ForTest` + 回归守卫 | — | ENOENT-not-cached / `flush()` 早 resolve / write 失败不阻塞 chain / 写 `parentUuid` 链的 race 说明 |
>
> **工程质量亮点**：PR body 含完整 tracer 脚本（`trace-sync-io.cjs` ~160 行）+ 可复现度量步骤；tracer 含 reentrancy guard（防 `appendFileSync` 内部递归调 `writeFileSync`）、PID-suffixed 输出（qwen 启动时派生的 sandbox-check / git-info 短命助手进程继承 `NODE_OPTIONS`，不能共用 summary 文件）、4s warmup 窗口（剔除模块初始化阶段 syscall）。
>
> **PR body 度量结果**：
>
> ```
> Baseline（HEAD 改动前，unique_sites=11, total_calls=110）：
>    22 mkdirSync          chatRecordingService.ts ensureChatsDir
>    22 existsSync         chatRecordingService.ts ensureConversationFile
>    22 existsSync         jsonl-utils.ts writeLineSync
>    22 appendFileSync     jsonl-utils.ts writeLineSync
>     8 realpathSync       workspaceContext.ts fullyResolvedPath
>     4 statSync           paths.ts validatePath
>     ...
>
> After PR#3581（unique_sites=5, total_calls=10）：
>     2 existsSync         todoWrite.ts
>     2 realpathSync       workspaceContext.ts（每个唯一输入 1 次）
>     2 statSync           paths.ts validatePath（每个唯一输入 1 次）
>     2 statSync           ripGrep.ts
>     2 existsSync         ripGrep.ts .qwenignore
> ```
>
> 每个剩余位点**每个唯一输入路径仅触发一次**——这是"不重写语义"前提下的理论下限。
>
> 合并后本项目可升级为 ✓ **已实现**（hot path 已饱和优化；启动阶段 sync I/O 保留是合理设计）。

## 一、主线程阻塞的蝴蝶效应

### 1. Qwen Code 现状：隐蔽的性能地雷
通过代码排查发现，Qwen Code 在运行时的多个核心路径上散落着同步 I/O。
- `config/settings.ts`: 实时加载配置时使用了 `readFileSync`。
- `utils/readManyFiles.ts`: 在遍历搜索文件时，使用了 `fs.statSync(fullPath)` 来判断是文件还是目录。
- `utils/workspaceContext.ts`: 注入 Git 状态或探测工作区时也是 `statSync`。

**痛点（微卡顿累加）**：
想象用户让 Agent 执行一次对 `src` 目录下 500 个文件的模糊搜索或信息注入。`statSync` 虽然单次极快（可能只有 0.1 毫秒），但连续循环 500 次，就会导致长达 50 毫秒的**绝对冻结**。
在这 50 毫秒内，大模型流式回传的网络数据包在排队，终端动画在卡顿，用户想通过 `Ctrl+C` 甚至都会感到不灵敏。这给最终用户带来的就是一股难以名状的“滞涩感”。

### 2. Claude Code 的极客纪律：异步化一切
Claude Code 的核心团队在源码中严格遵守了一条规则：“除进程最初的 100ms 启动外，禁止任何可能阻塞事件循环的 I/O”。

#### 机制一：全量向 `fs.promises` 迁移
除了极少数由 `fileReadCache.ts` 保护的带防抖机制的热点外，凡是涉及到目录探测、文件读取、设置刷新，全部使用了 `await fs.promises.stat` 和 `await fs.promises.readFile`。这保证了哪怕读取一个超大的 10MB 文本，底层的 C++ 线程池在搬运字节时，Node.js 主线程依然可以流畅地渲染 UI 的进度条。

#### 机制二：事件循环卡顿检测 (Event Loop Stall Detector)
为了防止团队中有人意外引入了同步阻塞库（比如某个解析巨大的 JSONL 文件的包），Claude Code 甚至内置了一个守护进程（`utils/eventLoopStallDetector.js`）：
```javascript
// 核心原理简述：它会不断注册 setTimeout(..., 50)
// 如果下一个 tick 唤醒的时间远远大于 50ms (比如间隔了 500ms)
// 说明主线程在刚刚的一段时间内被严重阻塞（冻结）了，系统会立刻打印性能告警日志！
```
这种极致的防御编程保证了 UI 的绝对丝滑。

## 二、Qwen Code 的改进路径 (P1 优先级)

千里之堤溃于蚁穴，消灭 Hot Path 上的同步操作是框架高可用的一环。

### 阶段 1：排查并清洗核心文件系统 API
全局搜查 `fs.readFileSync`, `fs.writeFileSync`, `fs.statSync`, `fs.existsSync`。
制定重构准则：
1. **启动初始化阶段 (Bootstrap)**：可以在应用第一帧渲染前使用同步，但尽量避免。
2. **命令执行期 (Runtime / Command Execution)**：绝对禁用。将涉及到多文件扫描（如 `readManyFiles.ts`）的逻辑改造为基于 `Promise.all` 或 `for await` 的全异步流。

### 阶段 2：安全升级依赖流
一些工具函数可能会因为异步化而被强行变为返回 `Promise`。这需要向上传导 `await`。这是一个体力活，但对于提升并发吞吐量意义重大。

### 阶段 3：引入事件循环监测器
1. 在 `debugLogger` 或遥测模块中，开启一个极低开销的内部定时器。
2. 记录每次 `setInterval` 触发的时间差（Delta），如果该差值大于阈值（例如 200 毫秒），则在开发者模式下向本地 Debug Log 抛出一条 `[Performance] Event loop blocked for XXX ms`，作为日后优化的锚点。

## 三、改进收益评估
- **实现成本**：中。涉及基础工具链的 API 签名改动和多处向上冒泡的 `await` 处理。
- **直接收益**：
  1. **显著的流畅度跃升**：彻底消灭 TUI 界面中的微卡顿和渲染闪烁，交互响应更加平滑。
  2. **避免 IO 竞争瓶颈**：随着文件并发处理（如多 Agent 协同）数量的增加，异步 I/O 可以将计算任务更早地交还给操作系统的线程池，榨干系统性能。