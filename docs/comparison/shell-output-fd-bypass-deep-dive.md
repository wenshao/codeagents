# Qwen Code 改进建议 — Shell 输出文件直写 (Shell Output FD Bypass)

> 核心洞察：当代码 Agent 获得了一个 Bash 环境，大模型难免会尝试运行诸如 `npm run build`、`mvn clean install` 甚至解压某个巨型 `tar.gz` 等重度流水线命令。这些命令会在 `stdout` 和 `stderr` 中疯狂倾泻几万甚至几十万行的日志流。如果直接使用 Node.js 的事件侦听器 `child_process.on('data')` 去捕获并拼接这些字符串，只需短短十几秒，Node.js 进程就会遭遇 V8 内存超限（OOM）而直接暴毙。Claude Code 通过底层的文件描述符（File Descriptor）重定向技术，彻底绕过了 JavaScript 堆内存的捕获陷阱；而 Qwen Code 目前在执行长命令时存在极大的稳定性隐患。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、海量标准输出带来的 OOM 陷阱

### 1. Qwen Code 的现状：全量字符串拼接
Qwen Code（或大多数初级 Agent）在实现 `Shell/Bash` 工具时，通常是这样的：
```typescript
let output = '';
child.stdout.on('data', (chunk) => {
    output += chunk.toString(); // 致命操作：无限膨胀的字符串拼接
    // 通知 UI 渲染...
});
```
- **痛点一（V8 内存溢出）**：大模型的输出可能会产生 50MB 甚至 100MB 的日志。在 Node.js 中拼接如此巨大的字符串会引发疯狂的 GC（垃圾回收），并很快触及 1.4GB 的 V8 堆内存上限导致进程崩溃。
- **痛点二（事件循环堵死）**：当子进程源源不断以极高频率抛出 `data` 事件时，Node.js 主线程光是处理流编码和跨进程回调就已经应接不暇了，终端 UI 也会随之彻底卡死。

### 2. Claude Code 解决方案：底层的 FD 管道直连
对于那些潜在高吞吐的子进程，Claude Code 的底层进程管理器极其聪明：**它拒绝让 Node.js 经手海量数据。**

#### 机制一：StdIO -> 文件描述符 (FD) 直通
在 Spawn 子进程时，它会先在硬盘上开启一个临时文件：
```typescript
const fd = fs.openSync('/tmp/claude-bash-output.log', 'w');
// Spawn 时，直接把子进程的标准输出挂载到这个硬盘文件的描述符上！
const child = spawn('bash', ['-c', 'npm install'], {
    stdio: ['ignore', fd, fd] 
});
```
此时，子进程产生的数十兆日志会由操作系统的底层 I/O 直接刷入硬盘，**完全不经过 Node.js 的内存空间**！

#### 机制二：UI 层的轻量级尾部轮询 (Tail Polling)
虽然数据被卸载到了硬盘，但用户仍然需要在终端看到“命令正在运行，而且输出了什么”。
Claude 放弃了全量监听，而是启动了一个类似 `tail -f` 的极低频定时器（例如 1000 毫秒一次）。它每秒钟去临时文件里**只读取最后几百个字节**用于驱动 UI 屏幕的 Spinner 和状态栏显示。

#### 机制三：安全截断交付
当命令执行完毕后，系统通过 `fs.stat` 查看这个日志文件有多大。如果查过了一定配额（比如 8MB），它会只截取文件的前 2000 行和最后 2000 行拼凑成一个结果反馈给大模型，避免大模型的 Context 被撑爆。

## 二、Qwen Code 的改进路径 (P2 优先级)

为了让 Qwen Code 能够安全无虞地托管任何疯狂的用户级自动化脚本，这层降级保护是必需的。

### 阶段 1：重构 `Shell` 工具的执行底层
1. 修改 `packages/core/src/tools/shell.ts` 或是对应的进程管理器。
2. 创建一个基于当前时间戳和随机 UUID 的临时文件 `.qwen/tmp/bash-[uuid].out`。
3. 利用 `fs.open` 拿到可写的文件句柄（fd），并将传递给 PTY（伪终端）或 `spawn` 选项的 `stdout`/`stderr` 数组指向这个 fd。

### 阶段 2：开发轻量级的 Tail Watcher
由于直接使用了 fd 挂载，原有的 `.on('data')` 将失效。
1. 使用 `setInterval` (如 `500ms` 间隔) 去探测这个 `.out` 文件的末尾。
2. 提取最后 `256` 字节的内容用于触发 `AgentEventType.TOOL_OUTPUT_UPDATE` 以驱动 UI 动画。

### 阶段 3：执行完的智能收尾
1. 当检测到子进程 `exit`。
2. 关闭文件描述符。使用流式接口（Stream）或者部分读取（如使用 `fs.read` 指定 offset）来获取文件首尾部分。
3. 组合并返回给工具最终结果，并删除临时文件（如果体积不大）或将体积过大的文件就地转为上文提到的 `持久化 ToolResult`。

## 三、改进收益评估
- **实现成本**：中等。涉及对 PTY 或者 Node.js Spawn 机制的重新接管，需要处理一些文件权限问题。
- **直接收益**：
  1. **绝对的稳定性**：从此 Qwen Code 告别了因为 `npm install --verbose` 而导致的系统假死和 OOM，真正成为抗造的系统级 Agent。
  2. **消除无用 CPU 消耗**：免去了海量的 JS 端字符串缓冲转换操作，极大节省了资源。