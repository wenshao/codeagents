# Qwen Code 改进建议 — 优雅关闭序列与信号处理 (Graceful Shutdown & Signal Handling)

> 核心洞察：CLI Agent 的运行环境（终端）极其脆弱，且常常伴随着大量异步的磁盘写入（持久化日志、存储）与网络连接（Telemetry 上报）。如果用户在 Agent 执行任务期间不耐烦地按下了 `Ctrl+C` (SIGINT) 或意外关掉了终端窗口 (SIGHUP)，处理不当会导致：终端鼠标光标丢失、键盘回显失效、写入一半的文件彻底损坏、甚至产生游离的僵尸后台进程。Claude Code 构建了一套极其完备的“同步恢复 + 异步清理 + 兜底强制杀死”的优雅关闭机制（Graceful Shutdown），而 Qwen Code 目前在核心执行流上缺乏统一的系统级信号安全收尾控制。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、异常退出导致的灾难性体验

### 1. Qwen Code 现状：简单粗暴或缺乏统一防线
目前在 Qwen Code 中，虽然个别子模块（如 Telemetry `sdk.ts`）监听了 `SIGINT` 并试图进行 flush 操作，但在整个应用主干层面，缺乏一个全局统筹的 `gracefulShutdown` 机制。

**痛点表现**：
- **终端状态未复原**：如果在全屏渲染（Alt-screen）或使用 Ink 库接管了鼠标追踪（Mouse Tracking）期间按 `Ctrl+C` 退出，返回 Shell 后，用户会发现滚动滚轮不再是翻页、甚至键盘输入的字符也不再显示（Cooked mode 被破坏），只能被迫输入 `reset` 命令恢复终端。
- **孤儿进程泄漏（Orphan Process）**：如果在 Mac/Linux 平台下直接点击红叉关闭终端，终端模拟器发出的 `SIGHUP` 信号可能无法正确回收仍在后台拼命 `Spawn` 执行的 Agent 进程，导致 CPU 和内存暗中飙升。
- **Telemetry 或缓存丢失**：因为 `process.exit()` 极其迅速，还没来得及异步 Flush 的请求（如 1P 事件打点或用户偏好）被无情丢弃。

### 2. Claude Code 解决方案：5 阶段防御关机序列
在 Claude Code `utils/gracefulShutdown.ts` 中，设计了一套教科书级别的守护退出逻辑，包含严格的同步与异步执行顺序。

当它捕获到 `SIGINT`、`SIGTERM` 或 `SIGHUP` 时，它会按如下 5 个阶段执行：

#### 阶段一：同步强制重置终端模式 (Synchronous Cleanup)
由于异步的 `React Unmount` 无法保证在终端崩溃前执行完毕，Claude Code 第一步先用底层的 `fs.writeSync(1, ...)` 直接向 stdout 暴力写入一长串终端控制转义码：
```typescript
writeSync(1, DISABLE_MOUSE_TRACKING)
writeSync(1, EXIT_ALT_SCREEN)
writeSync(1, SHOW_CURSOR)
writeSync(1, DISABLE_MODIFY_OTHER_KEYS)
```
这确保了即使后续 Node.js 进程立刻挂掉，用户回到的 Bash 环境也一定是健康的。

#### 阶段二：展示恢复提示 (Resume Hint)
立刻同步打印一条高亮信息：`"Resume this session with: claude --resume <session-id>"`，缓解用户的中断焦虑。

#### 阶段三：异步注册清理表与 Hooks (Async Registry)
调用统一的全局清理方法（`runCleanupFunctions`），同时触发 `SessionEnd` 的生命周期 Hooks（给插件系统通知收尾），每个步骤严格限定最多 2 秒的超时（Timeout），绝不无限期卡死。

#### 阶段四：网络与遥测下线 (Flush Telemetry)
调用 Datadog 和 1P 事件收集器的 Shutdown 方法，确保最后一条奔溃原因的日志成功上报。

#### 阶段五：兜底强制杀死 (5s Failsafe Timer)
为了防止某个网络请求卡住导致进程拒绝退出，在 `gracefulShutdown` 的开头，它会挂载一个 5 秒的定时炸弹（Failsafe Timer）：
```typescript
failsafeTimer = setTimeout(() => {
   process.kill(process.pid, 'SIGKILL'); // 不管三七二十一，用系统最高权限直接抹杀自身
}, 5000);
```

## 二、Qwen Code 的改进路径 (P1 优先级)

一个专业的开发者 CLI 工具，必须能够从容应对任何恶意的进程中断。

### 阶段 1：集中化系统信号监听
1. 在项目启动主入口（如 `entrypoints/cli.ts`）统一部署 `setupGracefulShutdown()` 拦截器。
2. 将现存散落于各处的 `process.on('SIGINT')` 统一收编至一个中心化的事件分发器，避免多个监听者产生冲突。
3. 引入对 macOS 典型的静默终端关闭检测：利用定时器检测 `process.stdout.writable`，在发现自己变成“聋哑进程”时主动触发退出。

### 阶段 2：实施“先同步、后异步”收尾动作
1. 提取一套类似 `termio/dec.ts` 的 ANSI Escape Code 静态字符串。
2. 无论发生任何中断，先用 `process.stdout.write` 或底层的 `writeSync` 强行释放全屏模式、重置光标显示。
3. 接着 `await` 异步持久化核心会话状态并释放所有文件系统锁。

### 阶段 3：Failsafe Timer 兜底机制
1. 所有涉及到 `Promise` 的收尾工作必须包裹一层 `Promise.race([Task, timeout(2000)])`。
2. 如果超过 5 秒仍然无法正常进入 `process.exit(0)`，直接利用 `process.kill(process.pid, 'SIGKILL')` 清除自身，杜绝产生耗费 CPU 资源的活死人后台进程。

## 三、改进收益评估
- **实现成本**：低到中等。实现核心退出拦截只需要约 200 行纯粹的 Node.js 进程控制代码。
- **直接收益**：
  1. **开发者体验零损坏**：彻底告别 `Ctrl+C` 之后终端被彻底搞乱，只能 `kill -9` 的窘境。
  2. **安全退出不丢档**：在关闭的千钧一发之际拯救正在写入的暂存文件，避免会话彻底损坏。
  3. **增强遥测可靠性**：显著降低进程中途被杀导致的错误日志黑洞，提高分析后台的数据保真度。