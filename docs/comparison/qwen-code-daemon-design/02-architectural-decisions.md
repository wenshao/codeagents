# 02 — Architecture Decisions

> [← 上一篇：Overview](./01-overview.md) · [下一篇：HTTP API & Protocol →](./03-http-api.md)

## TL;DR

7 个核心架构决策（决策 §1-§7）。最关键的是 §2 状态进程模型：**1 daemon = 1 workspace × N session multiplexed**（与 `qwen --acp` stdio 1:1 心智完全对齐 + OS 进程级隔离 + cgroup quota / K8s 云原生契合 + blast radius 最小）。**终态决策矩阵见 [§九](#九决策矩阵汇总)**。

---

## 〇、术语表

> 详 [§01 §一 术语表](./01-overview.md#一术语表)。简表：

| 术语 | 定义 |
|---|---|
| **Daemon process** | `qwen serve` 进程，绑定启动时 cwd = 单 workspace |
| **Session** | daemon 内嵌 `qwen --acp` child 的 `QwenAgent.sessions: Map` 内一条 |

> 代码中可能看到的废弃符号：`byWorkspaceChannel` / `ChannelInfo` / `Workspace Bridge`（PR#3889 multi-workspace 路由层，已由 [PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) 移除）。

---

## 1. session 是否跨 client 共享 — 两种拓扑

### 两种正交拓扑（LaZzyMan PR#3889 review 提出）

| 拓扑 | 形态 | 典型场景 | 主要压力 |
|---|---|---|---|
| **P1 — 1:N**（multi-end sync）| 1 session × N clients 订阅同一 conversation 事件流 | 桌面 TUI + 手机 mirror / Web UI attach / pair programming | EventBus fan-out |
| **P2 — N:1**（resource sharing）| N session × 1 user 同 workspace 切换 / 并行 | **IDE multi-window**（不同分支 / 子目录）/ mobile app N conversations | 同 daemon 内 N session 共享 `qwen --acp` child process；当前 cache/MCP 仍 per-session |

**关键观察**：IDE multi-window **是 P2 不是 P1**——多窗口为并行不同的事，不是同 session 多视图（Cursor / Continue / Claude Code / OpenCode / Gemini CLI 均原生支持 P2 single-process N-session）。

### 决策

**默认 `sessionScope: 'single'`**——同 daemon 多 client 自动 attach 到现有 session（语义 "first POST creates, subsequent POST attaches"）→ live collaboration（P1）。

**Stage 1.5 must-have #1** 落地后支持 per-request `sessionScope: 'thread'` override —— P2 同 daemon 内显式新建 isolated session，多 session 多路复用同 `qwen --acp` child。注意：当前源码里每个 ACP session 仍会创建自己的 `Config` / `ToolRegistry` / `McpClientManager` / `FileReadCache`；跨 session 共享 MCP/cache 是后续 pool/proxy 或 cache split 优化，不是 Stage 1 已有能力。

### 共享语义

| 操作 | 行为 |
|---|---|
| Client A 发 prompt | Client B 通过 SSE 看到完整事件流 |
| Client B 同时发 prompt | 同 session 串行——B 挂起等 A 完成（决策 §6）|
| A 等待 permission | 任何 client 都能 POST 应答（first-responder）|
| A 关闭 | daemon 进程不影响；其他 client 继续观察 |
| 所有 client 断开 + 空闲 | daemon 进入 idle，可被 orchestrator 回收 |

### 安全 / 隔离边界

`single` 默认下：
- ✓ **跨 workspace = 跨 daemon process = OS 进程级隔离**（多 daemon 部署天然隔离）
- ✓ 跨 daemon process 进程级隔离（外部 orchestrator 多 daemon 部署时）
- ⚠️ **同 daemon 同 workspace 多 client 能互相看见** —— 有意设计
- ⚠️ **同 daemon N session 共 OS 权限**（同 `qwen --acp` child / 同 UID / 同 workspace fs 视图）—— 多 tenant 必须 1 daemon 1 tenant

**多租户约束**：orchestrator 在 daemon process 层做 1:1 tenant 绑定（1 daemon = 1 tenant × 1 workspace）。详 [§06 §5.2](./06-roadmap.md#52-multi-tenancy--oidc--quota--audit)。

---

## 2. 状态进程模型（核心决策）

### 决策

**1 Daemon Process = 1 Workspace × N Sessions Multiplexed**。

`qwen serve` 启动时绑定 cwd = 单 workspace，daemon 内嵌单 `qwen --acp` child；`QwenAgent.sessions: Map<sessionId, Session>` 提供 N session multi-plexing。多 workspace 部署 = 多 daemon process（systemd / docker / k8s 各 1 process）。

```
qwen serve (绑定 cwd = /work/repo-a)
├─ Express HTTP front + bearer auth + Host allowlist
├─ EventBus（per-session fan-out + ring replay + Last-Event-ID 重连）
└─ qwen --acp child (workspace = /work/repo-a)
   └─ QwenAgent.sessions: Map → {sess-1, sess-2, sess-3}
```

**关键 invariants**：
- **N session 共享**：同一个 `qwen --acp` child process 与 workspace bound context。
- **N session 当前不共享**：`Config` / `ToolRegistry` / `McpClientManager` / `FileReadCache` 仍随 ACP session 创建。
- **跨 workspace = 多 daemon process**：OS 进程级隔离 + systemd `MemoryMax=` / cgroup / docker `--memory` 直接 = per-workspace quota
- **daemon crash 半径**：整个 daemon 退出 = 该 workspace 全部 session 收 `session_died`；其他 daemon（其他 workspace）不受影响
- **Blast radius 最小**：1 daemon = 1 workspace，daemon crash 只影响 1 workspace
- **K8s 云原生天然契合**：1 pod = 1 daemon = 1 workspace
- **与 `qwen --acp` stdio 1:1 心智对齐**：daemon 把 ACP stdio 包装成 HTTP，不引入中间抽象

### 多 workspace 部署 = 多 daemon process

```
qwen serve --port 8001 --workspace /work/repo-a
qwen serve --port 8002 --workspace /work/repo-b
qwen serve --port 8003 --workspace /work/repo-c
```

Client / orchestrator 侧做多 endpoint 路由（daemon discovery）。**External Reference Architecture** 提供 orchestrator 层（详 [§06 §五](./06-roadmap.md)）。

### 演进时间线

| Commit / PR | 内容 |
|---|---|
| Stage 1 初版 | 1 daemon = 1 session = 1 `qwen --acp` child（spawn-per-session）|
| `6a170ef8`（2026-05-12）| Review 反馈（LaZzyMan / tanzhenxin / 维护者）发现 `QwenAgent.sessions: Map` 原生支持单 child 多 session；重构为 bridge-per-workspace + N session multiplexed |
| **PR#4113**（✅ MERGED 2026-05-15）| `refactor(serve): 1 daemon = 1 workspace` — 移除 multi-workspace 路由抽象（`byWorkspaceChannel: Map` / `getOrCreateChannel` / `ChannelInfo`），回归 ACP stdio 1:1 心智；详 [PR#4113 description](https://github.com/QwenLM/qwen-code/pull/4113) |

### 与 IM Channels / ACP 协议 multi-cwd 能力的关系

tanzhenxin reviewer 反馈："ACP channels 是支持 working dir 的"——澄清三层现状：

| 层 | multi-cwd 能力 | 实际用法 |
|---|---|---|
| **ACP 协议** `newSession({cwd})` | ✅ 协议支持 per-call cwd | 设计意图允许 1 ACP child 服多 cwd |
| **`packages/channels/base/`** | ✅ API 保留 per-session cwd | ❌ 实际只用 `config.cwd` 单值（`ChannelBase.ts:270`）|
| **`acpAgent.ts:600`** 实现 | ❌ `this.settings = loadSettings(cwd)` 是 instance-wide，新 cwd 覆盖旧值 | 阻止跨 cwd 多 session（污染 settings / userHooks）|

**结论**：channels 实际用法 = "1 AcpBridge child = 1 cwd × N session"——与本系列 1 daemon = 1 workspace 100% 同构。ACP 协议的 per-session cwd 能力在 qwen-code 实现层不可用，是 Stage 2e native in-process 前置任务（需重构 `acpAgent.ts` 把 settings/hooks 从 instance-wide 改为 per-session）。

### 与 OpenCode 的设计差异

OpenCode default 是 1 daemon 多 workspace（`Map<workspace, Instance>` ALS in-process），主场景是 IDE + Web SDK + 个人开发者多项目。Qwen Code 主场景含 IM Channels + 多 tenant SaaS + K8s 部署——**强隔离 / quota / blast radius 要求高**，1 daemon = 1 workspace 更契合主场景。

### 性能对比

| 维度 | OpenCode（多 workspace ALS）| **Qwen (1 daemon = 1 workspace)** |
|---|---|---|
| 启动时间 | ~2-3s | ~2-3s |
| 首 session 创建（新 workspace）| <100ms（同 daemon 内）| ~2-3s（启新 daemon）|
| 同 workspace 第 N session | <50ms | **<200ms** |
| 跨 workspace 第 1 session | <50ms | ~2-3s |
| 100 同 workspace session 内存 | ~100-150MB | 类似 |
| 100 跨 workspace session 内存 | ~200MB（共 daemon）| ~10-15GB（100 daemon × baseline）|
| 隔离强度 | 应用层 ALS | **OS 进程级**（最强）|
| Blast radius | 整 daemon | **1 workspace** |
| Quota 颗粒度 | 需应用层抽象 | **cgroup / systemd 直接套用** |

跨 workspace 高密度场景 OpenCode 内存更省，但 Qwen 换得 OS 进程级真隔离 + cgroup quota + K8s 天然契合 + blast radius 最小——主场景下值得。详 [§06 §六 vs OpenCode](./06-roadmap.md#六vs-opencode最相似的竞品)。

### 工程约束

| 约束 | 验证 |
|---|---|
| daemon 主线程**永不**调用 `process.chdir()` | CI grep audit |
| 顶层 `process.on('uncaughtException')` log + graceful exit | top-level handler |
| 启动时绑定 cwd 不变 | daemon 启动后 workspace 固化 |
| `qwen --acp` child 退出 = daemon 进入终态 | 该 daemon 全部 session 收 `session_died` event；daemon 自身退出 |

---

## 3. MCP server 生命周期

**当前状态**：**per-session MCP state**。每个 ACP `newSession()` 创建新的 `Config`，`ToolRegistry` 拥有自己的 `McpClientManager`，因此同 daemon N session 不共享 MCP children。

- daemon 内的 `qwen --acp` child 是共享的，但 session config / MCP manager 是 session-local。
- 同 daemon N session 可能重复 spawn 同一组 MCP server children。
- 跨 daemon（= 跨 workspace）不同 child 各自独立 MCP children（OS 进程级隔离）。
- 未来如果要共享，需要 process-level MCP pool/proxy，并处理 stdio MCP 的 request/session 隔离问题。

### 依据

1. **当前源码绑定点是 `Config`**：`Config.createToolRegistry()` 创建 `ToolRegistry`，`ToolRegistry` 创建 `McpClientManager`。
2. **ACP `newSession()` 每次构造新 `Config`**：因此 MCP children 自然随 session 生命周期走。
3. **MCP 协议本身没有 qwen session 概念**：共享 stdio MCP child 需要额外 proxy/pool 设计，不能只把生命周期标签从 per-session 改成 per-daemon。

### 已有优化仍然有效

| 优化 | 价值 |
|---|---|
| **PR#3818 in-flight rediscovery coalesce** | 单个 manager 内并发 rediscovery 合并为单一 in-flight restart |
| **30s 健康检查 + 自动重连** | OpenCode 没有；掉线后用户主动 connect |

### 重复 spawn 代价

同 user 同 workspace N session 当前会有 N 套 MCP children。多 workspace 同 user = M daemon × N session × MCP sets。单 MCP ~50-200MB，若未来 TUI / channels / IDE 大量并发 session，MCP pool/proxy 会变成 Stage 2/2e 的资源优化项。

---

## 4. FileReadCache 共享语义

**决策**：**Session 内严格私有**。同 daemon N session 各自持独立 FileReadCache（`SessionService` per-session 字段）；不向其他 session 泄漏。

### 依据

1. **PR#3717 已是 session-scoped** —— `FileReadCache` instance 由 `SessionService` 持有，daemon 化天然兼容
2. **PR#3774 prior-read enforcement 依赖 session 私有**：cache miss = "**当前 session** 没看过该文件" → 拒绝 Edit/WriteFile。共享 cache 后此语义失效
3. **PR#3810 invalidation 5 路径** 表明跨 session 共享会把 fragility 半径扩到全 daemon
4. **跨 session 重复 read 代价小** —— OS page cache 兜底；FileReadCache 节省的是 LLM token 不是 disk I/O

### PR#3810 / PR#3774 与 cache 语义耦合

| PR | 行为 | 依赖 session-scoped |
|---|---|---|
| **PR#3810** | `microcompactHistory` / `setHistory` / `truncateHistory` / `resetChat` / `stripOrphanedUserEntriesFromHistory` 5 路径触发 cache invalidation | 操作 per-session，invalidation 半径不扩至 daemon 级 |
| **PR#3774** | `EDIT_REQUIRES_PRIOR_READ` / `FILE_CHANGED_SINCE_READ` 错误码 | "miss" 等同 "当前 session 未读过"；共享 cache 后此语义失效 |

### Stage 2e 候选优化

理论上可拆 2 层 — "content cache（`path+mtime→content bytes`）跨 session 共享" + "per-session read set（`Set<fileId>` 保留 PR#3774 enforcement）"。但 OS page cache 已兜底 disk I/O 增益边际；实现复杂度（拆 unified FileReadCache + 拆 PR#3810 invalidation 路径）较高。**仅在 500+ session/机实测瓶颈时再考虑**。

### daemon 内资源共享汇总

| 资源 | 共享范围 | 隔离机制 |
|---|---|---|
| Provider registry | daemon 全局 | 不可变 |
| Skill registry | daemon 全局 + path-conditional | 不可变 + per-tool-call 激活 |
| Auth credentials | per-daemon | 跨 daemon OS 进程级隔离 |
| **LSP server** | per-session / implementation-dependent | 当前随 session config 初始化；跨 daemon 进程级隔离 |
| **MCP server** | per-session | 同 daemon N session 不共享；future pool/proxy 可优化 |
| Background shell / agent / monitor / dream | per-task / 调度面 per-daemon | task ID + sessionId 关联 |
| **Session state** | per-session（N session 各自 SessionService）| SessionService 持久化 + transcript JSONL |
| **FileReadCache** | per-session（不向其他 session 泄漏）| PR#3717 session-scoped |
| Permission flow | per-tool-call | PR#3723；workspace/global scope decisions 文件 per-daemon 共享（详 [§05](./05-permission-auth.md)）|
| FastModel config | per-model | PR#3815 |

---

## 5. Permission Flow（链接 §05）

**决策**：**复用 PR#3723 共享 L3→L4 permission flow + daemon 第 4 种 execution mode + permission_request 走 SSE + first-responder 应答**。

```
ExecutionMode = 'interactive' | 'non-interactive' | 'acp' | 'daemon-http'
```

`daemon-http` mode 下 `ask` 决策不阻塞 HTTP，改 SSE 推 `permission_request` event；HTTP request 挂起等任意 client `POST /session/:id/permission/:requestId` 响应（first-responder）。

详 [§05 Security & Permission](./05-permission-auth.md)。

---

## 6. 多 Client 并发请求

**决策**：**同 session 串行 prompt（FIFO 队列）+ 多 client 同时观察事件流（fan-out SSE/WS）+ 跨 session 并行**。

> **术语**：**fan-out** = 1 事件源 → N 订阅者的广播模式（pub-sub / multicast 同义概念，反义词 fan-in）。在 daemon 上下文中：1 session 产生 `SessionNotification` 事件流（agent 思考 / tool call / text chunk），daemon 把每个事件**遍历推给该 session 的所有订阅 client**（CLI / WebUI / mobile / IM bot 同时观察）。实现：`Map<sessionId, Set<ClientSubscription>>` —— 见 `packages/cli/src/serve/eventBus.ts`。Per-session 路由：A session 事件只 fan-out 到 A session 的订阅者，不泄漏到 B session（隔离边界，详 [§05 first-responder](./05-permission-auth.md)）。

PR#3889 commit `ca996ecb5` 实现 per-session FIFO + no-poison（一个 prompt 失败不阻塞队列）。

### 多 client 事件分发

```
Client A → POST /session/:id/prompt
Client B / C → GET /session/:id/events （SSE 已订阅）

daemon Session.handlePrompt 启动
  └─ SessionNotification stream
      ├─ A 走 POST 的 SSE response
      ├─ B 走 GET /events SSE         ← fan-out
      └─ C 走 GET /events SSE         ← fan-out
```

每个 Session 维护 `Set<ClientSubscription>`，notification broadcast 到所有订阅者。

### 操作矩阵

| 操作 | 谁能做 | 冲突处理 |
|---|---|---|
| 发 prompt | 任何 client | 同 session 串行 FIFO，第二个挂起等 |
| 审批 permission_request | **任何 client（first responder wins）** | A 触发 → B 抢先应答 → A/C 收"已被 B 应答" |
| 取消 | 任何 client | `POST /session/:id/cancel` |
| 设置 model / mode | 任何 client | 立即生效，所有 client 收到通知 |

### 依据

ACP 协议本身就是"client → agent → 同步 response"语义，不允许同 session 并发 prompt。daemon 跟随这个约束 + 加上事件 fan-out 实现"多 client 协作观察"。同 session 并发 prompt 几乎无实际收益且实现复杂度极高（LLM 调用 / 工具调用并行化 / FileReadCache 同步）。

---

## 7. 部署模式 — Mode B mainline / Mode A parking lot

### 决策

**2026-05-15 后，roadmap 先只推进 Mode B。** Mode A 仍作为设计记录保留，但不再是 Stage 1.5 主线。

| 模式 | 启动命令 | TUI | 适用场景 |
|---|---|---|---|
| **Mode B: Headless + HttpServer** | `qwen serve [--port N]` | ❌ | 当前主线：服务器 / 容器 / 远端机器 / K8s pod / 所有 client 的统一 runtime |
| **Mode A: CLI + HttpServer** | `qwen --serve [--port N]` | ✅ 本地 | 暂停推进；待 Mode B contract 稳定后再评估 |

当前 client 直接边界是 HTTP server：TUI / channels / web / IDE 通过 `DaemonSessionClient` 调用 `POST /session/:id/*`，通过 `GET /session/:id/events` 消费 SSE。EventBus 是 daemon 内部 fan-out primitive；`EventBus lift` 指抽出 typed event contract / reducer / server-side primitive，不是让外部 client 直接 subscribe 内存对象。

### 依据

1. **PR#3889 已实现 Mode B**（Stage 1 ✅ MERGED 2026-05-13）。
2. **PR#4113 已把 Mode B 边界收紧到 1 daemon = 1 workspace**（✅ MERGED 2026-05-15）。
3. **TUI / channels / web / IDE 是 primary clients**，应先统一到 daemon HTTP/SSE + typed event contract。
4. **remote-control 后置**，等 primary clients 收敛后再作为 daemon facade 复用同一 contract。
5. **Mode A 暂停**，避免在 event/control/client contract 稳定前引入第二条 in-process 暴露路径。

### TUI 在多 session daemon 下的语义

详 [§04](./04-deployment-and-client.md)。简：

- **Mode B TUI adapter** 应作为 HTTP/SSE client，不再拥有 runtime。
- **channels / web / IDE** 同样通过 `DaemonSessionClient` 接入。
- **daemon-side control-plane parity** 落地后，remote clients 才能覆盖 memory / MCP / skills / tools / agents / auth / provider / context 等状态。
- **Mode A** 保留为 parking lot，不进入当前 stage 主线。

---

## 九、决策矩阵汇总

| # | 决策 | 选择 | 关键依据 |
|---|---|---|---|
| 1 | session 跨 client 共享 | **默认 `sessionScope: 'single'` 同 daemon 多 client 共享 session**；per-request scope override 是 Stage 1.5 must-have #1 | PR#3739 transcript-first fork resume + Stage 1.5 must-have #1 |
| 2 | 状态进程模型 | **1 daemon = 1 workspace × N session multiplexed**（与 `qwen --acp` stdio 1:1 心智 + OS 进程级隔离 + cgroup quota + K8s 云原生契合 + blast radius 最小）| [PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) 移除 PR#3889 multi-workspace 路由 |
| 3 | MCP server 生命周期 | **当前 per-session**（随 `Config` / `ToolRegistry` / `McpClientManager` 创建）；跨 session MCP 共享需要未来 pool/proxy | 当前源码状态 + Stage 1.5c state CRUD |
| 4 | FileReadCache 共享 | **per-session 严格私有**（同 daemon N session 各自实例不共享；跨 daemon 自然独立）+ PR#3774 prior-read 守卫 + PR#3810 5 路径 invalidation | PR#3717 / PR#3774 / PR#3810 |
| 5 | Permission flow | 复用 PR#3723 + daemon 第 4 mode + SSE permission_request | PR#3723 evaluatePermissionFlow() |
| 6 | 多 client 并发 | **同 session prompt 串行（FIFO）+ 事件 fan-out + 任何 client 可应答 permission** | PR#3889 commit `ca996ecb5`（FIFO + no-poison）+ ACP 协议语义 + EventBus subscriber set |
| 7 | 部署模式 | **Mode B mainline；Mode A parking lot** | 2026-05-15 决策：优先 TUI / channels / web / IDE 接入 Mode B；remote-control 后置 |

---

下一篇：[03 — HTTP API & Protocol →](./03-http-api.md)
