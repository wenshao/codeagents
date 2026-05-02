# SDK / ACP / Daemon 架构 Deep-Dive — 4 大 Code Agent 程序化接口对比

> 对比 OpenCode、Qwen Code、Codex、Claude Code 在 SDK、ACP（Agent Client Protocol）、HTTP daemon 三个维度的设计差异。基于 2026-05-01 各项目本地源码分析。
>
> **配套文章**：
> - [Agent SDK Python Deep-Dive](./agent-sdk-python-deep-dive.md) —— Python SDK 跨语言桥接设计
> - [SDK 双向控制协议 Deep-Dive](./sdk-bidirectional-control-deep-dive.md) —— Claude Code NDJSON 控制语义
> - [Remote Control Bridge Deep-Dive](./remote-control-bridge-deep-dive.md) —— Qwen Code Channels 远程驱动
> - [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么这个话题重要

CLI Agent 不只是给人在终端敲命令用的工具——当它要被嵌入 IDE 插件、被 Python 数据流水线调度、被 web UI 展示、被 CI 脚本批量驱动时，**程序化访问接口的设计直接决定了集成成本**。

四款主流 Code Agent 在这个问题上做出了**根本不同的选择**：

| 产品 | 程序化访问主入口 |
|---|---|
| **Claude Code** | 自家 NDJSON 双向控制 SDK（TS + Python） |
| **Qwen Code** | 三语言 SDK（TS + Python + Java）+ ACP 双向（agent + client） |
| **Codex** | 自家 JSON-RPC `app-server-protocol`（TS + Python SDK） |
| **OpenCode** | **HTTP daemon + OpenAPI codegen 客户端** + ACP agent |

差别不在表面包装，而在**进程模型与状态共享语义**——本文剖开来讲。

## 二、4 种通信架构

### Subprocess 模型（Claude / Qwen / Codex）

```
┌──────────┐  spawn   ┌─────────────────────────────┐
│ SDK 客户端 │─────────▶│ CLI 子进程（per-query/per-Client）│
└──────────┘  stdio   │ ├─ stdin/stdout NDJSON      │
                      │ │  或 JSON-RPC              │
                      │ └─ core (in-process 库调用) │
                      └─────────────────────────────┘
每个 query() / Client 实例 = 1 个 CLI 子进程；query 内多轮工具调用复用同一进程
```

**特征**：粒度是 **per-query 或 per-Client**——同一个 `query()` 流式返回中的多轮工具调用复用同一子进程；但不同 `query()` 调用各自 spawn 新进程。状态隔离强、每次新会话付启动开销。

### Daemon 模型（OpenCode 独家）

```
┌──────────┐  HTTP/WS ┌─────────────────────────────┐
│ SDK 客户端 │◀────────▶│ daemon 进程（长生命）         │
└──────────┘          │ ├─ Hono / Bun.serve         │
                      │ ├─ Instance / Session Map   │
                      │ └─ core (in-process 库调用) │
                      └─────────────────────────────┘
1 次 spawn daemon → N 个 client 永久 HTTP 复用
```

**特征**：daemon 启动一次后，所有客户端 HTTP/WebSocket 调用都在同一进程内 in-process 函数调用 core。状态共享强、启动开销摊销。

### ACP 模型（Qwen / OpenCode 支持）

```
┌──────┐  spawn   ┌─────────────────────────────┐
│ IDE  │─────────▶│ Agent 进程 = CLI 进程         │
└──────┘  stdio   │ ├─ NDJSON (Zed ACP 协议)     │
                  │ └─ core (in-process 库调用) │
                  └─────────────────────────────┘
IDE 启动时 spawn 一次，长连接驱动 agent
```

**特征**：是 subprocess 模型的"长连接版"——IDE 拉起 agent 一次，通过 stdio NDJSON 持续通信直到 IDE 关闭。

## 三、SDK 矩阵详细对比

### 3.1 语言覆盖

| 维度 | Claude Code | Qwen Code | Codex | OpenCode |
|---|---|---|---|---|
| **TypeScript SDK 包** | `@anthropic-ai/claude-agent-sdk` | `@qwen-code/sdk` v0.1.7 | `@openai/codex-sdk` v0.0.0-dev | `@opencode-ai/sdk` |
| **Python SDK 包** | `claude-agent-sdk` | `qwen-code-sdk` v0.1.0a | `openai-codex-app-server-sdk` v0.116.0a1 + `openai-codex-cli-bin` runtime | ❌ 无 |
| **Java SDK 包** | ❌ 无 | `com.alibaba:qwencode-sdk` v0.0.3-α + `com.alibaba:acp-sdk` v0.0.1-α | ❌ 无 | ❌ 无 |
| **生成方式** | 手写 + 完整双向控制 schema | 手写 + Transport 抽象 | Pydantic（Python）/ 手写（TS）+ Rust 协议层 codegen | **OpenAPI 13525 行 codegen** |
| **底层传输** | subprocess + NDJSON `stdin/stdout` | subprocess（`ProcessTransport`）+ NDJSON | subprocess JSON-RPC | HTTP REST（自动从 OpenAPI 生成） |

### 3.2 各 SDK 的内部"形状"

**Claude Code**——双向控制最完整：

```ts
// 核心: entrypoints/sdk/controlSchemas.ts 定义 20+ 控制结构
const q = query({
  prompt,
  canUseTool: async (req) => userApprovesIt(req),  // 工具审批回调
})
q.setModel('haiku')        // 运行中切模型
q.seedReadState([...])     // 把 IDE 已打开文件灌入 fileReadCache
q.interrupt()              // 注入软中断
```

**Qwen Code**——架构对齐 Claude，控制语义在追赶：

```ts
// 源码: packages/sdk-typescript/src/index.ts
import { query, tool, createSdkMcpServer } from '@qwen-code/sdk'

// 已暴露类型: CLIControlRequest / CLIControlResponse / ControlCancelRequest
// Transport 接口预留 HttpTransport / WebSocketTransport（packages/sdk-typescript/src/transport/Transport.ts:5-7）
```

**Codex**——最厚的协议层，最薄的语言层：

```python
# 源码: sdk/python/src/codex_app_server/client.py
from codex_app_server import Client
# 协议在 Rust 端 17414 行（v1: 245 行 + v2: 10885 行）
# Python/TS SDK 都是 protocol/v2.rs 的 codegen
client = Client.connect()  # subprocess 拉起 openai-codex-cli-bin
```

**OpenCode**——SDK 只是 OpenAPI HTTP 壳子：

```ts
// 源码: packages/sdk/openapi.json 13525 行
import { createOpencodeServer } from '@opencode-ai/sdk'
// 1. 自动 spawn `opencode serve` daemon
// 2. SDK 实例就是 OpenAPI 客户端，所有方法都是 HTTP 调用
const server = await createOpencodeServer()
const client = new OpencodeClient({ baseUrl: server.url })
```

### 3.3 Qwen Java SDK 的特殊地位

Qwen Code 的 `sdk-java/` 拆为两个独立 Maven 包：

| Maven 坐标 | 用途 |
|---|---|
| `com.alibaba:acp-sdk` v0.0.1-α | **独立的 Java ACP 协议实现库**（不限于 Qwen Code）|
| `com.alibaba:qwencode-sdk` v0.0.3-α | Qwen Code 的 Java 客户端，依赖 acp-sdk |

意义：**4 款产品中唯一为 ACP 协议提供 Java 生态实现**——这意味着任何 ACP 兼容的 agent（含 OpenCode）都可以被 Java 应用集成，而不只是为 Qwen 服务。

## 四、ACP（Agent Client Protocol）支持

ACP 是 Zed 团队推动的 IDE↔Agent 标准协议，依赖 npm 包 `@agentclientprotocol/sdk`。

### 4.1 各家立场

| 角色 | Claude Code | Qwen Code | Codex | OpenCode |
|---|---|---|---|---|
| **作为 ACP Agent**（被 IDE 拉起）| ❌ | ✅ `packages/cli/src/acp-integration/acpAgent.ts`（838 行 · `@agentclientprotocol/sdk@^0.14.1`）| ❌ | ✅ `packages/opencode/src/acp/agent.ts` |
| **作为 ACP Client**（驱动其他 Agent）| ❌ | ✅ `packages/vscode-ide-companion/src/services/acpConnection.ts` | ❌ | ❌ |
| **Java ACP 实现** | ❌ | ✅ `acp-sdk` 独立可复用库 | ❌ | ❌ |
| **Zed 编辑器扩展** | ❌（用自家 IDE 扩展）| ✅ `packages/zed-extension/` | ❌ | ❌ |
| **VSCode 集成方式** | 私有协议 | `vscode-ide-companion` 走 ACP | ❌（仅 CLI） | `/sdks/vscode/` 单独包 |

### 4.2 三个观察

1. **Qwen Code 是 4 者中 ACP 投入最重的**——同时做 ACP agent + ACP client + Zed 扩展 + Java ACP 库。这是基于"开放协议生态优于自研"的判断。

2. **Claude Code 与 Codex 都选了"自家协议"**——Anthropic 用 NDJSON 双向控制，OpenAI 用 JSON-RPC `app-server-protocol`（17K 行 schema）。头部厂商不愿被外部协议 schema 约束 control plane 设计。

3. **Codex 用 MCP 替代 ACP**——Codex 自身可作为 MCP server 暴露能力（`codex-mcp` / `mcp-server` crates）。MCP 是"工具调用协议"（窄），ACP 是"会话协议"（全）。Codex 选 MCP 反映它把自己定位为"被其他 LLM agent 调用的工具"，而非"被 IDE 嵌入的会话"。

### 4.3 控制语义对比

| 能力 | Claude Code | Qwen Code | Codex | OpenCode |
|---|---|---|---|---|
| 工具审批回调 | ✅ NDJSON `control_request` | ✅（ACP `permission_request`）| ✅（JSON-RPC `request_user_input`）| ✅（ACP `permission_request`）|
| 运行中切模型 | ✅ `set_model` | 🟡 部分（`SetSessionModelRequest`）| ✅ | 🟡 |
| 注入预读缓存 | ✅ `seed_read_state` | ❌ | ❌ | ❌ |
| 软中断 | ✅ `interrupt` | ✅ ACP `cancel` | ✅ JSON-RPC `cancel` | ✅ |
| 多 session 管理 | ✅ | ✅（`LoadSessionRequest`/`ForkSessionRequest`）| ✅（thread_state）| ✅ |
| Fork session | ✅ | ✅ ACP | ✅ | ✅ ACP |

**Claude Code 独家的 `seed_read_state`**：SDK 宿主可以把"用户在 IDE 已打开的文件"直接灌入引擎的 `fileReadCache`，避免重复读取。这是**最贴 IDE 工作流**的设计——Qwen Code 在 PR#3717 加了 FileReadCache 基础设施，理论上可以补齐这个 API。

## 五、OpenCode HTTP daemon 模式深度剖析

### 5.1 启动方式

```bash
opencode serve  # 启动 headless HTTP server
```

源码 `packages/opencode/src/cli/cmd/serve.ts`：

```ts
const opts = await resolveNetworkOptions(args)
const server = await Server.listen(opts)
console.log(`opencode server listening on http://${server.hostname}:${server.port}`)
await new Promise(() => {})  // 永久阻塞作为 daemon
```

仅 ~20 行代码。`serve` 子命令是 `opencode` 同一二进制的一种运行模式——daemon 不是独立 binary。

### 5.2 技术栈

| 组件 | 实现 |
|---|---|
| HTTP 框架 | **Hono**（`packages/opencode/src/server/server.ts`）+ `hono-openapi` 自动生成 spec |
| 运行时 | **Bun 优先**（`adapter.bun.ts:Bun.serve`），Node 回退（`adapter.node.ts`）|
| 默认端口 | 4096（占用则随机分配）|
| 服务发现 | **mDNS Bonjour**（`mdns.ts`）—— 局域网内自动广播 `opencode-{port}._http._tcp.local` |
| 鉴权 | `OPENCODE_SERVER_PASSWORD` env；不设则警告 unsecured |
| WebSocket | `Bun.serve` 内建 + `createBunWebSocket` —— 长连接事件流推送 |
| OpenAPI | `generateSpecs(app)` 运行时生成 spec，SDK 直接 codegen |

### 5.3 路由层级

```
/global          → 全局元信息（providers / installation / version）
/control         → 控制面（多 workspace 调度）
/                → workspace router → instance routes（核心 API）
  ├─ /session/*       (创建/列表/fork/resume/rewind/...)
  ├─ /file/*          (读写)
  ├─ /pty/*           (终端，WebSocket 升级)
  ├─ /tui/*           (TUI 客户端连接点)
  ├─ /provider/*      (LLM provider 管理)
  ├─ /mcp/*           (MCP server 管理)
  ├─ /permission/*    (审批流)
  ├─ /event/*         (事件订阅 SSE/WS)
  └─ ...
/ui              → 内嵌 web UI
+ /experimental/workspace
+ Flag.OPENCODE_EXPERIMENTAL_HTTPAPI 切到独立 HttpApi 实现
```

中间件链：`ErrorMiddleware → AuthMiddleware → LoggerMiddleware → CompressionMiddleware → CorsMiddleware → FenceMiddleware`

### 5.4 SDK 与 daemon 的连接方式

`@opencode-ai/sdk` 的 `createOpencodeServer()`（`packages/sdk/js/src/server.ts`）：

```ts
const args = [`serve`, `--hostname=${options.hostname}`, `--port=${options.port}`]
const proc = launch(`opencode`, args, { env: {...} })
```

链路：

```
SDK 客户端
  │
  │  cross-spawn `opencode serve` 一次（启动 daemon）
  ▼
opencode serve 进程（daemon）
  │
  │  HTTP/WebSocket（之后所有调用走此通道）
  ▼
SDK OpenAPI codegen 客户端调用 daemon REST API
```

### 5.5 daemon 内部不再 spawn CLI

源码证据（`packages/opencode/src/server/routes/instance/index.ts`）：

```ts
import { Instance } from "@/project/instance"
import { Agent } from "@/agent/agent"
import { Skill } from "@/skill"
import { Global } from "@opencode-ai/core/global"
// ... 全部是 import，不是 spawn

.post("/instance/dispose", ..., async (c) => {
  await Instance.dispose()  // ← 直接函数调用 core
  return c.json(true)
})
```

整个 `server/routes/` 目录搜不到任何 spawn CLI 子进程的代码——core 是通过 import 加载到 daemon 进程内的库。

## 六、多 session 进程模型

### 6.1 OpenCode：所有 session 共进程

源码 `packages/opencode/src/project/instance.ts`：

```ts
const cache = new Map<string, Promise<InstanceContext>>()  // ← 内存级 instance 缓存

export const Instance = {
  async provide<R>(input: { directory: string; ... }): Promise<R> {
    const directory = AppFileSystem.resolve(input.directory)
    let existing = cache.get(directory)  // 同 directory 复用，不 spawn
    ...
  }
}
```

**N 个 session × M 个 workspace = 永远是 1 个 daemon 进程**。

### 6.2 进程模型层级

```
opencode serve daemon 进程（承载 N 个 session 的主进程）
│
├─ Hono HTTP server
├─ 全局状态：providers / config / GlobalBus / Database (SQLite)
│
├─ Instance Map（按 project directory 缓存）
│   ├─ Instance A（项目 /work/repo-a）
│   │   ├─ Session a1（LLM 上下文 + transcript）  ── in-memory
│   │   ├─ Session a2 ── in-memory
│   │   ├─ LSP server（spawn 一次）              ← 子进程，跨 session 共享
│   │   ├─ MCP server（spawn 一次）              ← 子进程，跨 session 共享
│   │   └─ Shell PTY（按需 spawn）               ← 子进程，工具调用粒度
│   │
│   └─ Instance B（项目 /work/repo-b）
│       └─ ...
│
└─ 上述所有 session 共享：Provider / Auth / Bus / Database / Hono runtime
```

### 6.3 颗粒度：何时 spawn 子进程

| 颗粒度 | 是否 spawn 子进程 | 说明 |
|---|---|---|
| 新加 session | ❌ 永不 | 纯数据结构 + Effect Context |
| 新加 workspace（instance）| ❌ 永不 | 加到 `cache` Map 里 |
| LLM 调用 | ❌ 永不 | HTTP fetch from daemon |
| LSP 服务器 | ✅ 每 instance 一次 | 同 workspace 内 session 共享 |
| MCP 服务器 | ✅ 每 MCP 配置一次 | 跨 session 共享 |
| Shell / Bash 工具调用 | ✅ 每次工具调用 | PTY 子进程，工具结束就回收 |
| `opencode tui` 客户端 | ✅ 是 daemon 的 client | 不是 daemon 内部进程 |

### 6.4 设计取舍

| 维度 | OpenCode daemon | Qwen/Claude/Codex SDK subprocess |
|---|---|---|
| Session 是否独立进程 | ❌ N 个 session 共享 daemon | ✅ 每个 query/Client 独立进程 |
| 跨 session 状态共享 | ✅ 简单（直接 Map）| ❌ 需要文件 IPC |
| 一个 session 崩了影响其他 | ✅ 会（同进程）| ❌ 不会（隔离进程）|
| 启动开销摊销 | ✅ 一次（daemon 拉起后）| ❌ 每个 query 都付 |
| MCP server 复用 | ✅ daemon 寿命内（多 query 共享）| ❌ Client 内多轮共享，跨 Client 重启 |
| 用户感受冷启动 | 仅第一次 | 每个新 Client/query |
| OOM/内存隔离 | 弱（应用层 Effect Context）| 强（OS 进程隔离）|
| 资源效率 | 高（共享 model registry / db）| 低（每个新进程重新加载）|

OpenCode 用 **Effect-TS 的 `LocalContext` / `Context.Service`** 强制依赖注入，避免 module-level 全局可变状态——这是它敢做共进程多 session 的工程基础。`Instance.dispose()` 提供显式资源回收的逃生口。所有关键状态持久化到 SQLite（`session.sql.ts:SessionTable` / `SessionEntryTable`），进程崩溃后重启可恢复。

## 七、Qwen Code 引入 daemon 的工作量评估

### 7.1 可直接复用的现成资产

| 资产 | 位置 | 价值 |
|---|---|---|
| **Express HTTP server 模板** | `packages/vscode-ide-companion/src/ide-server.ts` | 已用 express + cors + auth token 起 HTTP 服务（给 IDE 用），代码可参考 |
| **Channels 多路由基础设施** | `packages/channels/base/` | `SessionRouter` / `PairingStore` / `SenderGate` / `GroupGate` / `BlockStreamer` / `AcpBridge` —— 原本服务于 Telegram/微信/钉钉 channels 的多用户多 session 设施 |
| **ACP agent（838 行）** | `packages/cli/src/acp-integration/acpAgent.ts` | NDJSON 协议、session 生命周期、permission 流、authentication、cancel 全齐 —— **协议层 ~100% 可复用**，只需把 stdio 替成 HTTP/WS |
| **SessionService** | `packages/core/src/...` | JSONL session 持久化、resume、fork、rewind、rebuild from transcript（PR#3739 刚加）|
| **WebUI 包** | `packages/webui/` | Vite + React + Tailwind，已有 web 客户端 |
| **SDK Transport 抽象** | `packages/sdk-typescript/src/transport/Transport.ts:5-7` | **代码注释明确写了 `HttpTransport: Remote CLI via HTTP (future)` + `WebSocketTransport`**——是规划内事项 |
| **Background shell pool** | PR#3642 已合并 | 多任务调度抽象，daemon 模式可直接扩展为多 client 任务队列 |

### 7.2 主要缺口与新增成本

| 缺口 | 工作量 | 说明 |
|---|---|---|
| `qwen serve` CLI 命令 | 0.5 天 | 加个 cmd 入口（参考 OpenCode `serve.ts` 仅 ~20 行） |
| HTTP server 选型 + 路由 | 2-3 天 | 推荐 Hono（与 OpenCode 一致 + Bun 友好），或继续 express |
| ACP agent → 多 client 改造 | 3-5 天 | 当前 ACP 是单 stdio session 模型，改成 per-request session ID 路由 |
| HTTP API schema（zod / OpenAPI）| 2-3 天 | 复用 ACP 的 zod schema |
| SSE 或 WebSocket 流式事件 | 2-3 天 | core 已有 event emitters，只需桥接 |
| 鉴权（bearer token + env）| 1 天 | 完全照搬 OpenCode 思路 |
| HttpTransport（SDK 端）| 2-3 天 | 已留好接口，按 ProcessTransport 镜像写 |
| daemon 生命周期 + pid file | 1-2 天 | graceful shutdown / SIGTERM / health check |
| **MVP 合计** | **~2-3 周（1 人）** | |
| 多 workspace 路由 | 5-7 天 | 当前是 single-workspace，需要加 workspace ID 中间件 |
| mDNS 服务发现 | 1 天 | 直接 `bonjour-service`（OpenCode 同款） |
| OpenAPI codegen | 3-5 天 | 跟 OpenCode 一样 `generateSpecs(app)` |
| WebUI 接入 daemon | 5-7 天 | 改 webui 数据源从 ipc 改 HTTP |
| 文档 + 测试 + 例子 | 5-7 天 | |
| **对标 OpenCode 合计** | **~1.5-2 个月（1-2 人）** | |

### 7.3 真正的难点（架构决策）

| 决策点 | 选项 A | 选项 B | 影响 |
|---|---|---|---|
| **Session 共享语义** | 多 client 严格隔离 | Session 可跨 client 共享（手机→桌面续行）| 影响 SessionService 锁/可见性 |
| **状态进程模型** | 1 daemon 承载所有 session | daemon 路由到子进程 | 后者对 OOM 隔离友好但启动慢 |
| **MCP server 生命周期** | per-session 启动 | daemon 内 pool 跨 session 复用 | 后者高效但有状态泄漏风险 |
| **FileReadCache 共享** | 每 session 独立 | 整个 daemon 共享 | `(dev,ino)` key 设计天然支持共享，但语义需要确认 |
| **Permission flow** | 信任 daemon 内决策 | 每 client 单独审批 UI | PR#3723 刚把三模式合一，daemon 是第 4 种 |
| **多 client 并发请求** | 串行 | 并行 | 后者是 daemon 真正价值但需共享资源加锁 |

### 7.4 推荐渐进路径

```
Stage 1（~1 周）：实验性 --http-bridge flag
  ├─ 在现有 ACP agent 外加 HTTP→stdio 桥接（最小改动）
  ├─ 1 个 daemon 进程 = 1 个 ACP session（多 client 排队）
  └─ 让用户先用起来探索需求

Stage 2（~2-3 周）：原生 qwen serve 多 session
  ├─ 重写 ACP agent 为多 session router
  ├─ 加 SDK HttpTransport 实现
  ├─ Web UI 接入
  └─ MVP 可用

Stage 3（~1-2 月）：对标 OpenCode 完整设计
  ├─ Workspace routing
  ├─ mDNS + OpenAPI
  ├─ WebSocket 流式
  ├─ 集群部署文档
  └─ 企业鉴权
```

### 7.5 旁证：近期 PR 是否在为 daemon 做准备？

最近一周连续合并的几个 PR 在**消除 session 共享/恢复/权限的障碍**：

- **PR#3739**（2026-05-01 +4087/-165）`Add background agent resume and continuation` —— `BackgroundAgentResumeService` + transcript-first fork resume
- **PR#3717**（2026-04-30）`feat(core): add FileReadCache and short-circuit unchanged Reads` —— session-scoped 缓存基础设施
- **PR#3723**（2026-04-30）`feat(core): add shared permission flow for tool execution unification` —— Interactive / Non-Interactive / ACP 三模式权限决策合一
- **PR#3642**（2026-04-28）`feat(core): managed background shell pool with /tasks command` —— 跨 session 任务调度

这些恰好是 daemon 模式必须解决的前置问题。**仅依据近期 PR 主题推测**，Qwen 团队心里大概率有 daemon 路线图。

## 八、典型场景的最佳选择

| 场景 | 最佳选 | 原因 |
|---|---|---|
| Python 数据科学 / ML 流水线集成 | **Claude / Qwen / Codex** | 三者都有 Python SDK；Codex 的 `pydantic` 模型对类型严格的工程师更友好 |
| Java 后端服务集成 | **Qwen Code 唯一选项** | 唯一提供 Java SDK + Java ACP 实现 |
| Zed 编辑器内嵌 Agent | **Qwen / OpenCode** | 两者都做 ACP agent；Qwen 还自带 zed-extension |
| VSCode 插件双向集成（自定义审批 UI）| **Claude / Qwen / OpenCode** | Claude NDJSON / Qwen ACP / OpenCode ACP 都可承担 |
| 把 Agent 当 MCP 工具被另一个 LLM 调用 | **Codex** | 唯一原生暴露 `codex-mcp` server 接口 |
| Browser/Web 调度多 Agent 实例 | **OpenCode** | REST API 设计天然适合 HTTP 调度 |
| 强双向控制（中途换模型 / 注入缓存）| **Claude Code** | `set_model` / `seed_read_state` 是独家 |
| HTTP/JSON-RPC 直连无需 SDK | **Codex / OpenCode** | Codex `app-server` JSON-RPC / OpenCode REST |
| 长跑 daemon 节省启动开销 | **OpenCode 唯一原生支持** | 其他三家每个新 query/Client 要 spawn 一次 |
| CI 脚本一次性批量任务 | **任一** | subprocess 模型反而更简单（一次性进程更干净）|

## 九、四种架构哲学的总结

| 产品 | 设计哲学 | 体现 |
|---|---|---|
| **Claude Code** | **深度 + 私有协议** | 20+ NDJSON 控制原语让宿主像调试器一样精细操控引擎，不入 Zed/外部 ACP 生态 |
| **Qwen Code** | **广度 + 兼容** | 三语言 SDK + 双向 ACP + Java ACP 库，集成口最多，深控制语义在追赶 |
| **Codex** | **协议 first，SDK 是壳** | 17K 行 Rust JSON-RPC 协议 + MCP 双暴露，自定位"被调用的工具/服务" |
| **OpenCode** | **REST/daemon first** | OpenAPI codegen + 长跑 daemon 进程，多 client 共享 core 状态 |

## 十、关键洞察清单

1. **没有任何 SDK/ACP 实现是直接 link core 库到客户端进程**——core 永远在另一个进程里，差别只在那个进程是 daemon 还是 short-lived subprocess。

2. **OpenCode daemon 内部不再 spawn CLI**——daemon 就是 CLI 二进制以 `serve` 模式运行，core 通过 import 加载到 daemon 进程内。

3. **Qwen Code 是 4 者中 ACP 投入最重的**——同时做 ACP agent + ACP client + Zed 扩展 + Java ACP 库。

4. **Claude Code 与 Codex 都选了"自家协议"**——头部厂商不愿被外部协议 schema 约束 control plane 设计。

5. **Codex 用 MCP 替代 ACP 的角色**——把自己定位为"被调用的工具"，而非"被嵌入的会话"。

6. **OpenCode 多 session 共享 1 个 daemon 进程**，`Map<directory, InstanceContext>` 缓存 + Effect-TS Context 做应用层隔离 + SQLite 做持久化。子进程仅限 LSP / MCP / PTY 等"外部进程依赖"。

7. **Qwen Code 加 daemon 的工作量约 2-3 周（MVP）/ 1.5-2 月（对标 OpenCode）**——因为 ACP agent + Channels + WebUI + SDK Transport 抽象都已就绪。

8. **真正的难点是几个架构决策**——session 共享语义、状态进程模型、MCP server 生命周期、并发语义——而不是代码量。

## 十一、源码证据索引

| 主题 | 文件路径 |
|---|---|
| OpenCode `serve` 命令 | `packages/opencode/src/cli/cmd/serve.ts` |
| OpenCode HTTP server 主入口 | `packages/opencode/src/server/server.ts` |
| OpenCode Bun adapter | `packages/opencode/src/server/adapter.bun.ts` |
| OpenCode mDNS | `packages/opencode/src/server/mdns.ts` |
| OpenCode Instance Map（多 session 共进程证据） | `packages/opencode/src/project/instance.ts` |
| OpenCode Instance routes | `packages/opencode/src/server/routes/instance/index.ts` |
| OpenCode SDK server 启动器 | `packages/sdk/js/src/server.ts` |
| OpenCode ACP agent | `packages/opencode/src/acp/agent.ts` |
| OpenCode session SQLite schema | `packages/opencode/src/session/session.sql.ts` |
| Qwen Code ACP agent（838 行）| `packages/cli/src/acp-integration/acpAgent.ts` |
| Qwen Code SDK Transport 接口（注释预告 HTTP/WS） | `packages/sdk-typescript/src/transport/Transport.ts:5-7` |
| Qwen Code SDK ProcessTransport | `packages/sdk-typescript/src/transport/ProcessTransport.ts` |
| Qwen Code Channels 路由设施 | `packages/channels/base/src/SessionRouter.ts` 等 |
| Qwen Code Java acp-sdk pom | `packages/sdk-java/client/pom.xml` |
| Qwen Code IDE companion HTTP server（参考模板）| `packages/vscode-ide-companion/src/ide-server.ts` |
| Codex Python SDK client | `sdk/python/src/codex_app_server/client.py` |
| Codex Rust 协议层 | `codex-rs/app-server-protocol/src/protocol/v2.rs`（10885 行）|
| Codex MCP server crate | `codex-rs/codex-mcp` / `codex-rs/mcp-server` |

> **免责声明**：以上数据基于 2026-05-01 各项目本地源码分析，可能已过时。版本号仅反映当时仓库状态。各产品演进迅速，建议使用前以仓库最新状态为准。
