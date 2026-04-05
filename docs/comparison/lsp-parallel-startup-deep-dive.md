# Qwen Code 改进建议 — LSP 服务器并行启动与探测 (LSP Parallel Startup)

> 核心洞察：大模型对代码库的精确理解越来越依赖 LSP (Language Server Protocol) 提供的方法跳转、类型推断和诊断报错。当一个大型的全栈项目（比如前端 TypeScript + 后端 Go + 脚本 Python）同时激活三个 LSP Server 时，顺序拉起这些笨重的语言服务会使得 Agent 的冷启动时间延长数秒。Claude Code 利用了 `Promise.all` 并发启动和极致优化的 `Promise.race` 端口/状态探活策略，在后台瞬间满载拉起所有服务器而不阻塞主路；而 Qwen Code 在这块并发启动和超时降级上尚有优化空间。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、LSP 服务的重型开销

### 1. Qwen Code 现状：缺乏并发弹性的慢启动
语言服务器（如 `tsserver`, `gopls`, `pyright`）在启动时需要消耗大量的 CPU 解析全量工程树。
- **痛点一（串行阻塞）**：如果在启动阶段用一个普通的 `for` 循环依次 `await startLspServer()`，3 个服务器各自耗时 2 秒，整个应用的 LSP 挂载阶段就会被拉长到 6 秒以上。
- **痛点二（超时挂起）**：如果某个语言服务（比如本地 Python 环境损坏导致 `pyright` 卡在启动死锁中），没有极度严格的外围超时切断机制，会导致整个 Agent 因为等待一个不重要的特性而假死。

### 2. Claude Code 解决方案：Promise.race 与并发池
在 Claude Code 的 `services/lsp/LSPServerInstance.ts` 等底层文件里，处理这种“又重又不可靠的子进程”手段非常老辣：

#### 机制一：全量并行与背景探测
不再做串行 `await`，所有的配置好要启动的 LSP 均同时 Spawn。
使用 `Promise.race` 挂载一个防死锁计时器（例如 10 秒）：
```typescript
// 伪代码思路
return Promise.race([
  startAndHandshakeLSP(serverConfig),
  timeoutPromise(10000).then(() => { throw new Error("LSP Timeout"); })
]).finally(() => {
  // 清理探测器的句柄防止内存泄露
});
```

#### 机制二：崩溃隔离与重启退避
如果 `tsserver` 在中途 OOM 崩溃，系统并不会让 Agent 报错。它在 `onCrash` 回调里做了极好的隔离：最多尝试重启 3 次（带有指数退避），如果 3 次都不行，就把这台 LSP 标记为 `DEAD`。
Agent 的大模型如果此时想用工具去查类型推断，工具会友好地返回 `"The TypeScript Language Server is currently unavailable."`，而不是让整个终端抛出 Stack Trace。

## 二、Qwen Code 的改进路径 (P2 优先级)

将 LSP 作为“锦上添花”的可选组件，而非“阻塞主干”的累赘。

### 阶段 1：重构 LSP 启动流为 `Promise.allSettled`
1. 修改 `packages/core/src/lsp/LspClientManager.ts` 等初始化文件。
2. 收集所有需要的 LSP 实例，用 `Promise.allSettled` 包裹它们的初始化过程，实现 100% 并行启动。

### 阶段 2：引入 `Promise.race` 超时护航
1. 在启动和发送握手请求（Initialize Request）时，严格包裹 `Promise.race` 定时炸弹（建议 5-8 秒）。
2. 一旦超时，在 Debug 日志中记录，并将该 LSP 实例状态置为脱机。绝不让 Agent 的启动等待超时。

### 阶段 3：错误冒泡与大模型感知
当大模型调用如 `GoToDefinition` 工具时，如果对应的 LSP 未就绪或已崩溃：
返回优雅的 `ToolResult`：`{ success: false, message: "LSP server is indexing or offline. Try using grep or ripgrep instead." }`。
这让大模型能智能降级，自己去找替代方案（例如用全文搜索去找函数定义）。

## 三、改进收益评估
- **实现成本**：小到中等。核心是修改并发控制和错误处理包裹，逻辑非常明确。
- **直接收益**：
  1. **巨型工程的秒开体验**：即便项目大得离谱、配了四五个语言服务器，Agent 依然能顺滑启动，不拖泥带水。
  2. **容错与自愈能力极强**：屏蔽了环境损坏导致卡死的风险，使得底层基础架构显得极其专业和皮实。