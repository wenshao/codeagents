# Qwen Code 改进建议 — MCP 并行连接与动态插槽调度 (MCP Parallel Connection)

> 核心洞察：随着大模型代理接入的企业级系统越来越多，挂载超过 10 个 MCP (Model Context Protocol) 服务器将成为常态（如内部数据库、Jira、CI/CD 系统、外部检索源）。在启动 Agent 时，如果简单粗暴地串行加载或无节制地全量 `Promise.all` 发起连接，会导致极其严重的进程卡顿（“Fork Bomb” 效应）甚至阻塞整个任务流水线。Claude Code 构建了精细的本地与远程双层并发组，并结合 `p-limit` 动态插槽实现了极速且防阻塞的发现机制；而 Qwen Code 目前的处理方式极为初级。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、MCP 服务器挂载的性能瓶颈

### 1. Qwen Code 现状：缺乏调度的并发洪水
在当前的 `McpClientManager.initializeAllClients()` 逻辑中，当系统配置了 15 个 MCP 服务器时，它会使用一个简单的 `Promise.all(discoveryPromises)`。
- **痛点一（资源耗尽）**：如果是本地 `stdio` 类型的 MCP 服务器，这意味着它会瞬间 fork 出 15 个 Node.js/Python 子进程，可能瞬间抽干 CPU 资源。
- **痛点二（短板效应）**：如果使用固定的批处理或者不做任何隔离，在这 15 个服务器中，只要有一个远端（HTTP/SSE）服务器由于网络原因卡死或者握手极慢，整个主进程就必须等待它超时。开发者直观的感受就是“一旦配了外网 MCP，Agent 启动就要干等 10 秒”。

### 2. Claude Code 解决方案：动态插槽与双层编排
在 Claude Code 的 `services/mcp/client.ts` 中，设计了一套极尽巧思的连接拓扑结构：

#### 第一层：本地与远程分类隔离
它将服务器配置严格分为两类，施加截然不同的并发上限：
- **Local Servers (`stdio` / 本地脚本)**：并发度被严格限制为 **3**。因为子进程 Spawn 会极大地消耗 OS 句柄和计算资源。
- **Remote Servers (`sse` / `http` / `ws`)**：并发度被放宽至 **20**。因为它们属于 I/O 密集型操作，大部分时间都在等待网络握手。

这两种类型的初始化池通过 `Promise.all([localPool, remotePool])` 完全并列运行。

#### 第二层：动态插槽调度 (Dynamic Slot Scheduling via pMap)
Claude Code 并没有使用僵硬的静态批次（例如每组等 3 个全做完再开启下一组 3 个），而是引入了类似线程池的流转逻辑（`processBatched()`）。
一旦某个远程 MCP（如内网的 GitLab 接口）极速秒连，它腾出的并发插槽（Slot）会被立刻分配给排队的下一个服务器。
**哪怕有 2 个服务器不幸彻底卡死，只要没有占满插槽总数，其余 13 个服务器依然能够畅通无阻地完成注册并进入可用状态**。

#### 第三层：资源请求并发化
在建立单个连接后，协议通常要求立刻拉取该服务器宣告的 `tools`（工具）, `commands`（命令） 和 `resources`（资源）。
Claude 也是果断采用了 `Promise.all([fetchTools, fetchCommands, fetchResources])` 的并发提取，并配以 20 条记录上限的 `MCP_FETCH_CACHE_SIZE` LRU 缓存，杜绝重复的网络开销。

## 二、Qwen Code 的改进路径 (P2 优先级)

为了将 Qwen Code 打造成企业 MCP 网关中心，网络拓扑调度必须被重构。

### 阶段 1：引入并发控制器 (p-limit)
1. 在依赖库中引入或手写一个并发队列工具（如 `p-limit` 或 `pMap`）。
2. 在 `mcp-client-manager.ts` 中废弃直接的 `Promise.all` 裸奔逻辑。

### 阶段 2：重写 `initializeAllClients` 方法
1. 遍历配置，按传输协议的 `type`（`stdio` 归本地，`sse`/`websocket` 归远端）对列表进行分流。
2. 设定参数：`LOCAL_CONCURRENCY = 3`，`REMOTE_CONCURRENCY = 20`。
3. 利用插槽控制器进行安全的并行发现注册。

### 阶段 3：缓存与超时隔离
1. 为每个单一 MCP 挂载增加严格的时延锁（Timeout，如 3000ms），一旦超时仅抛出单独的警告（Warning），不阻塞主线程的运转，允许 Agent 带着“部分就绪”的工具子集先跑起来。
2. 对于 `Client.listTools()` 级别的请求加入防抖缓存（Debounced Cache）。

## 三、改进收益评估
- **实现成本**：中等。核心在引入并发流转控制，代码重构量在 150 - 200 行。
- **直接收益**：
  1. **无感知的秒级冷启**：即使用户配置了海量的扩展服务器，终端启动也能保持在毫秒级，且彻底避免了卡死无响应。
  2. **容灾降级体验**：单点 MCP 服务不可用不会再拖垮整个 AI Agent 生态。