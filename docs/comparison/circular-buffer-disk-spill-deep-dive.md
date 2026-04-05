# Qwen Code 改进建议 — 环形缓冲区与磁盘溢出 (CircularBuffer & Disk Spill)

> 核心洞察：CLI Agent 的常驻后台能力越来越强。在执行复杂的多步骤任务（例如：拉取全库代码，跑一次全量测试，然后收集控制台输出给大模型分析）时，如果子进程在本地产生了上百万行的标准输出（Stdout），将其全部塞进普通的数组结构中会瞬间引发 Node.js 的 OOM（内存溢出）。Claude Code 在处理这种无边界流式数据时，引入了极其经典的底层数据结构 `CircularBuffer`（环形缓冲区）来限制内存占用，并配以安全的磁盘溢写（Disk Spilling）策略；而 Qwen Code 的内存收集机制目前缺乏强制上限，存在极大的稳定性隐患。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、无底洞般的流式数据陷阱

### 1. Qwen Code 的现状：不受控的内存数组
在处理后台进程的输出、MCP 消息队列或者终端历史日志收集时，如果不加限制，最常见的写法是 `array.push(line)`。
- **痛点（静默的内存泄露）**：当你在终端跑一个挂载了 `verbose` 参数的构建工具时，它可能一秒钟喷出几万行无用的日志。如果 Qwen Code 使用无界的数组或者 `string += chunk` 的方式收集上下文，短短一分钟内，Node 进程的常驻内存（RSS）就会飙升到 1GB 以上，引发疯狂的垃圾回收（GC），使得终端 TUI 卡成幻灯片，最终直接暴毙退出，导致之前的交互历史全盘丢失。

### 2. Claude Code 解决方案：强制截断与双路收集
在 Claude Code 的 `utils/CircularBuffer.ts` 及任务输出组件 `utils/task/TaskOutput.ts` 中，构建了一道坚不可摧的内存防浪堤。

#### 机制一：定容环形队列 (`CircularBuffer`)
这是一种教科书级的数据结构。Claude Code 为每一个子任务或者长连接终端分配了一个固定容量（例如 `1000` 行）的 `CircularBuffer`：
```typescript
class CircularBuffer<T> {
  // 永远只用固定大小的 Array
  private buffer: T[] = new Array(capacity);
  private head = 0;

  add(item: T) {
    this.buffer[this.head] = item;
    // 覆盖最老的数据，永不扩容！
    this.head = (this.head + 1) % this.capacity; 
  }
}
```
通过这种极其高效的 O(1) 尾部覆盖操作，无论你外面的构建脚本跑了多少天、喷了几个 G 的日志，这段程序在 V8 引擎里的堆内存永远只有区区几百 KB！
当需要在界面（TUI）上为人类或者大模型展示进度时，它随时可以提取这最新的 1000 行日志，提供了完美的“最近现场”。

#### 机制二：全量数据磁盘溢写 (Disk Spill)
大模型有时候确实需要看全量日志，那怎么办？
系统会拉起双路管道（Dual Pipeline）：
- 热数据进 `CircularBuffer`，服务于内存和实时 UI。
- 冷数据直接通过流（Stream）或之前提到的 `File Descriptor (FD)` [绕过 JS 直接刷入硬盘临时文件](./shell-output-fd-bypass-deep-dive.md)。如果文件体积到达极高的阈值（如 8MB），直接在系统层强行截断（Truncate）或只保留首尾 2000 行。

## 二、Qwen Code 的改进路径 (P2 优先级)

拒绝内存泄漏，将防 OOM 提升到架构底座级别。

### 阶段 1：引入 `CircularBuffer` 数据结构
1. 在 `packages/core/src/utils/` 下编写并单元测试 `CircularBuffer.ts`。
2. 梳理全局所有的 `data` 监听器（如处理 `shell` 工具的标准输出、WebSocket 流接收缓冲等）。将原本的 `string` 拼接或 `array.push` 全部替换为此数据结构。

### 阶段 2：重构历史上下文截断
在组装向大模型发送的历史（Transcript）或者工具执行结果（Tool Result）时：
强制对超长输出取 `buffer.toArray()`。并在截断处自动拼接一行系统旁白：
`[... 上文日志已省略以保护内存，仅展示最后 1000 行 ...]`
这既保护了 Node.js 内存，也保护了下一次发往 API 时的 Token 预算不被无聊的重复日志烧光。

### 阶段 3：结合 `BoundedUUIDSet`
除了日志，对于大量产生的小型对象（比如前端向后台发出的海量通知、文件搜索路径缓存等），同样引入带容量限制的 Set 或 Map，强制淘汰（Evict）最早的元素，保证整个 Agent 进程的内存占用曲线在长达 24 小时的待机后依然是一条完美的平直线。

## 三、改进收益评估
- **实现成本**：极低。只需引入几十行的底层工具类，并替换几个关键工具的收集逻辑。
- **直接收益**：
  1. **极强的抗压体质**：让 Qwen Code 能够扛住极端异常环境下的“日志洪水攻击（Log Flood）”，成为最皮实的企业级工具。
  2. **消除内存泄漏隐患**：让开发者在长周期的编程会话中不用担心工具变卡，保证了极其顺滑的开发体验。