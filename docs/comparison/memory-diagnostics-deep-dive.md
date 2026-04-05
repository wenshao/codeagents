# Qwen Code 改进建议 — 内存诊断与泄漏预警 (Memory Diagnostics & Leak Prevention)

> 核心洞察：随着大模型上下文的无限扩张和 AI Agent 支持的本地工具越来越多（如海量文件解析、LSP 并发进程、Ast 解析等），CLI Agent 进程在长时间的深度会话中非常容易出现内存泄漏（Memory Leak）。如果没有任何监控，Node.js 进程会在达到 V8 堆上限（默认 1.4GB 左右）时直接 OOM (Out Of Memory) 暴毙。这会导致开发者辛辛苦苦跑了半天的多轮对话数据和代码审查进度瞬间灰飞烟灭，没有任何挽救机会。Claude Code 内置了企业级的 `heapDumpService.ts`，能做到 OOM 前预警并自动采集完整的 `smaps_rollup` 现场；而 Qwen Code 目前在此领域的治理处于“裸奔”状态。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么我们需要内建的内存诊断？

### 1. Qwen Code 现状：黑盒崩溃
在目前 Qwen Code 的长会话（例如超过 100 轮交互，或者加载了一个带有几百张图片的知识库文档）中：
- **痛点一（突发性 OOM）**：当内存泄漏（如未释放的 `EventEmitter` 订阅、冗余的日志数组缓存）积压到临界点时，Node 进程会不带任何预警地直接退出，抛出 `FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed`。
- **痛点二（无法排查）**：当用户在 GitHub 提 Issue 抱怨“跑到一半崩溃了”时，开发者无法重现，也拿不到任何 Heap Snapshot 现场，Bug 永远是一个谜。

### 2. Claude Code 的极客级护航：主动防线
在 `utils/heapDumpService.ts` 和 `/heapdump` 命令的加持下，Claude Code 构建了一套防微杜渐的内存防火墙。

#### 机制一：内存高水位巡检 (High-watermark Polling)
系统在后台启动了一个极低开销的轮询器，定期通过 `process.memoryUsage()` 检查 `rss` 和 `heapUsed`。
当检测到堆内存逼近警戒线（如 1.5GB 阈值）时，它不再等待进程自然死亡，而是**主动拦截并抛出红色告警**，建议用户立刻 `/compact` 压缩上下文或者保存当前状态退出。

#### 机制二：自动化故障现场留存 (Heap Snapshot)
如果开发者执行了底层的 `/heapdump` 命令，或者在即将 OOM 前的最后时刻，系统会调用 V8 原生接口：
```typescript
import * as v8 from 'v8';
v8.writeHeapSnapshot('/tmp/claude-heap-dump-xxxx.heapsnapshot');
```
这不仅将崩溃前一秒的 V8 堆栈拍了照片，还会在 Linux 环境下尝试读取 `/proc/self/smaps_rollup`，获取更底层 C++ 附加库（比如 Rust 绑定的 NAPI 插件）分配的常驻内存片段，打包生成一份极度详尽的诊断报告，甚至还包含初步的 leak 建议分析。

## 二、Qwen Code 的改进路径 (P3 优先级)

对于生产级工具，不崩溃是底线；崩溃了能提供完美案发现场，是优秀开源项目的素养。

### 阶段 1：开发内存看门狗 (Memory Watchdog)
1. 在 `packages/core/src/utils/` 下新增 `memoryMonitor.ts`。
2. 设定软阈值（如 `1024 MB`）和硬阈值（如 `1400 MB`）。
3. 每隔 30 秒或在每个推理循环 (`runReasoningLoop`) 结束时检测一次。
4. 如果越过软阈值，向 `debugLogger` 或控制台打出警告：“内存占用已达警戒线，建议通过 /compact 命令清理对话上下文”。

### 阶段 2：支持 `/doctor memory` 探针
扩充 Qwen Code 的 `/doctor` (或者新增专有的 `/heapdump`) 命令：
1. 捕获 V8 的 `heapUsed` / `external` / `arrayBuffers` 分布。
2. 提供 `v8.writeHeapSnapshot()` 能力，方便用户遇到卡顿时，手动帮开源社区打出一个诊断包上传到 GitHub Issue。

### 阶段 3：自动脱水自救机制 (Auto-eviction)
当看门狗探测到内存即将 OOM，自动触发一次类似 `Micro Compact` 的操作，遍历并丢弃所有的历史 `ToolResult` 的超长字符串，仅保留 `[Content Evicted for Memory Safety]` 占位符。这通常能瞬间夺回几百兆的存活空间。

## 三、改进收益评估
- **实现成本**：小到中等。Node.js 已经原生提供了 V8 监控能力，只需编写调度层代码，百行以内可实现基础预警。
- **直接收益**：
  1. **排障神兵利器**：让所有的 OOM 问题变得可被追溯和分析，大幅降低开源社区 Issue 排查的沟通成本。
  2. **免于崩溃的优雅体验**：用预警和自动压缩替代直接宕机，守住大模型长会话最后的尊严。