# Qwen Code 改进建议 — 读写穿透缓存与 TTL 刷新 (Write-Through Cache & Stale-while-revalidate)

> 核心洞察：Agent 运行期间有大量诸如“MCP 工具列表获取”、“本地 Git 分支状态读取”、“配置解析”等短时间内不会剧烈变化，但又会被高频访问的操作。Qwen Code 在面对这些请求时大多缺乏通用的缓存防抖策略，每次对话轮次都全量重新读取，积累了可观的毫秒级阻塞延迟。Claude Code 则引入了经典的 Web 架构设计 `stale-while-revalidate` (过期返旧值并发起后台刷新)，在不牺牲实时性的前提下实现了极限加速。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、频繁轮询导致的积少成多型延迟

### 1. Qwen Code 现状：老实的重复劳动
在处理一次用户命令时，Qwen Code 的主推理循环常常需要准备前置上下文，例如：
- 重新遍历配置获取所有挂载的 MCP 服务器并调用它们的 `ListTools` (通过 IPC 开销很大)。
- 运行 `git status` 或 `git rev-parse HEAD` 来构建环境提示。
- 在大型项目中，解析复杂的配置文件或 Schema。

**痛点**：在一个 30 分钟、包含 50 个对话轮次的会话中，这些底层系统信息可能根本没有任何变化。但由于 Qwen Code 缺乏对状态读取的高效缓存与防抖机制，这些动作在每一次 `runReasoningLoop` 发生时都会同步阻塞地跑一遍，每轮凭空增加几百毫秒的延迟。

### 2. Claude Code 的解决方案：异步刷新机制
在 Claude Code 的 `utils/memoize.ts` 中，作者为了极致性能构建了两个极品的高阶函数：`memoizeWithLRU` (防 OOM 内存泄漏) 和 `memoizeWithTTL`。

#### stale-while-revalidate 的魔力
传统的 TTL 缓存（如 Redis）在过期后，下一个请求会遭到**同步阻塞 (Cache Miss Penalty)**，去查底层的慢数据。
而 Claude Code 的 `memoizeWithTTL(fn, 5min)` 实现的是**写穿透并发刷新**模式：
1. 首次读取，等待并返回结果，打上时间戳。
2. 5 分钟后缓存过期。下一次请求到来时：
   - 系统**不会阻塞等待**去获取最新值！
   - 系统立刻将内存里的**过期旧值 (Stale Value)** 返回给调用方，让主业务流零延迟继续。
   - 同时，后台静默触发原函数去真正的底层拿最新值，并带上防并发的 `refreshing` 锁（防止多个同时到来的请求触发多次刷新）。
   - 最新值拿到后，原地覆盖旧缓存。

由于类似 MCP 服务器列表、Git Branch 这样的信息，即使短暂滞后个几十秒也几乎不会导致任何业务灾难，这个策略巧妙地“骗过”了时间。

## 二、Qwen Code 的改进路径 (P2 优先级)

将这种微小却通用的高性能套件植入到底层框架中。

### 阶段 1：引入高级 Memoize 库
1. 新建 `packages/core/src/utils/memoize.ts`。
2. 编写 `memoizeWithTTLAsync` 高阶函数包装器。
3. 实现防重入锁：在 `refreshing = true` 时，所有并发访问都返回现存旧值，或者等待同一个挂起的 Promise (`inFlight Map`)。

### 阶段 2：梳理并改造系统级热点
在项目中全局搜索以下高频、低敏感的慢调用，并用该函数包裹：
1. **MCP Tools 查询**：将向远端 MCP 服务器发送 `tools/list` 的过程包裹在 `memoizeWithTTL(fn, 10分钟)` 中。当用户真的保存了 MCP 配置文件，可以通过一个强刷 `cache.clear()` 暴露点来主动过期。
2. **Git 环境查询**：对于获取当前仓库信息的 Shell 命令，配置 `memoizeWithTTL(fn, 1分钟)`。
3. **系统环境验证探测**：例如用于 `/doctor` 或启动检查的网络连通性测试。

### 阶段 3：配合 LRU 控制内存爆炸
对于那些输入参数千变万化的缓慢查询（比如基于全路径的文件 AST 解析），采用 `memoizeWithLRU(fn, max_size=100)` 保护。限制内存最高水位，以防止由于大范围遍历导致的 Node.js OOM。

## 三、改进收益评估
- **实现成本**：小。一个优秀的通用基础工具方法，可低侵入性地替换到各个子模块。
- **直接收益**：
  1. **消除无形时延**：在一个大型微服务仓库（带 10 个外网 MCP 和庞大 Git 树）的重度编程 Session 中，每轮问答交互的主观体感至少能加快 300 - 800 毫秒。
  2. **避免 IO 竞争**：防止多个并发 Agent（Swarm）同时去查询相同的基础状态而造成的进程内网络端口和磁盘 IO 踩踏。