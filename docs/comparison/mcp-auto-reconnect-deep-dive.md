# Qwen Code 改进建议 — MCP Auto-Reconnect 自动重连防抖 (MCP Auto-Reconnect)

> 核心洞察：模型上下文协议 (Model Context Protocol, MCP) 极大地拓宽了 CLI Agent 的能力边界，使得它们能连接本地的数据库、浏览器的调试器，甚至是远程的知识服务。然而，基于 `stdio` 或 `SSE (Server-Sent Events)` 的长连接在现实中极其脆弱。如果使用 Docker 容器跑批或者遭遇网络波动，远程的 MCP Server 可能会发生短时掉线。在普通的 Agent 架构中，一旦底层连接抛出 Socket 错误，该 Agent 拥有的那一套 MCP 工具会彻底报废，用户必须尴尬地使用 `Ctrl+C` 强退重启。Claude Code 构建了一套极其坚韧的 **“连续 3 次容错与自动重建”** 机制，确保了流媒体通道的自愈力；而 Qwen Code 目前在处理 MCP 掉线上基本属于“一断就死”。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、玻璃一样的底层通道

### 1. Qwen Code 现状：极其脆弱的工具链
当我们在 Qwen Code 中挂载了一个拉取远程 Jira 任务的 MCP HTTP 服务器：
- **痛点一（断线即永久报废）**：如果在夜间开发时，公司内网的网关重启了一下（大概 5 秒断网），底层的 EventSource 会立刻触发 `onerror`。由于没有自愈的 Retry 逻辑，整个 Client 端进入死锁。用户再次让大模型去查 Jira 时，大模型只会迷茫地返回 `Error: Transport is closed`，只能杀进程重开，前文积累的几十条极其珍贵的历史 Context 瞬间归零。
- **痛点二（极差的错误反馈）**：当 MCP 挂掉时，控制台通常只会抛出一堆毫无意义的深层 `ECONNREFUSED` 或 `Socket hang up` 堆栈，用户完全不知道刚才发生了一次网络抖动。

### 2. Claude Code 解决方案：坚若磐石的自愈网络
在 Claude Code 的 `services/mcp/client.ts` 源码中，针对不稳定的连接痛点，工程师引入了“自动重连心跳（Auto-Reconnect）”防抖系统。

#### 机制一：三振出局策略 (Consecutive Errors Threshold)
他们不迷信一次报错就宣告死亡，而是维护了一个 `consecutiveConnectionErrors` 计数器。
当检测到底层的流式通道（无论是 SDK 还是 SSE 层）发生连接错误时：
如果 `errors < 3`，系统会静默拦截这个错误。并在后台快速发起一个短暂退避（Backoff，比如延迟 500ms）的重新建链请求。
只有当同一个端点连续 3 次以上（或者长达几分钟）死活连不上，才会把真正的错误抛到上层中断流。

#### 机制二：透明的挂起与恢复 (Transparent Suspension)
在等待重连的那一两秒内，如果有高层业务（大模型刚好想用这个工具）打过来了。
客户端内部的网络层会将其**挂起 (Suspend) 进队列**，而不是立刻报错返回失败。等下面修好了路，自动把堆积的请求重发过去。大模型在云端根本感受不到地面发生的这一切，它只觉得这次拿工具结果稍微慢了那么零点几秒。

#### 机制三：失效探针 (Session 404 嗅探)
对于基于 HTTP 的连接，如果服务端重启了，之前的 Session ID 全部作废（返回 404）。系统只要探测到这个特殊的 404，不仅会重新建连，还会主动去**重刷一遍 Tools 和 Resources** 的注册表，以防服务端重启后功能发生了变化。

## 二、Qwen Code 的改进路径 (P2 优先级)

想要接管企业复杂的内网开发任务，网络容错性是及格线。

### 阶段 1：构建带重连状态机的 Client 装饰器
1. 在 `packages/core/src/mcp/` 下。
2. 包装原始的 `@modelcontextprotocol/sdk`。为每一个 MCP 服务器连接建立生命周期映射：`CONNECTED | RECONNECTING | DEAD`。
3. 设定常量 `MAX_ERRORS_BEFORE_RECONNECT = 3`。

### 阶段 2：挂钩错误处理器
劫持底层 Transport 的 `onerror` 和 `onclose` 事件。
```typescript
transport.onclose = () => {
    if (this.state === 'RECONNECTING') return;
    this.consecutiveConnectionErrors++;
    
    if (this.consecutiveConnectionErrors <= MAX_ERRORS_BEFORE_RECONNECT) {
        logDebug("MCP connection lost. Attempting silent reconnect...");
        this.attemptReconnect(); 
    } else {
        this.markAsDead();
        notifyUser("MCP Server [Jira] permanently disconnected.");
    }
};
```

### 阶段 3：UI 的静默与提示
如果在重连期间耗时超过了 2 秒，在底部的状态栏使用黄字警告 `[Reconnecting to MCP: Database...]`，重连成功后瞬间转为绿色 `[Restored]`。赋予开发者极大的掌控感。

## 三、改进收益评估
- **实现成本**：小。主要是网络连接层的容错包装和错误重试定时器逻辑，代码量大约 100-150 行。
- **直接收益**：
  1. **拯救长线工作的崩溃**：在一个需要通宵跑批或者长时间挂载的会话里，它挽救了无数因为一次短暂的网线松动而被迫从头再来的灾难。
  2. **企业级的高可用背书**：自动重连（Auto-Reconnect）是所有成熟中间件（如 Redis、Kafka Client）的标配。它的加入宣告着 Qwen Code 对待 MCP 插件的严肃态度。