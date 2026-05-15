# 06 — Roadmap & Ecosystem

> [← 上一篇：Security & Permission](./05-permission-auth.md) · [回到 README](./README.md)

## TL;DR

**2026-05-15 roadmap reset**：先忽略 Mode A（`qwen --serve`），以 **Mode B：`qwen serve` headless daemon** 作为唯一主线。Stage 1 ✅ MERGED 2026-05-13（PR#3889）→ Stage 1.5a ✅ MERGED 2026-05-15（PR#4113，1 daemon = 1 workspace）→ Stage 1.5 继续做 Mode B event/control/client convergence。执行优先级对齐 upstream 最新 roadmap：**P0 = 9 个 production must-haves + daemon-side state CRUD**；client adapters 先 behind flag，默认切换必须等 P0/P1 基础完成；remote-control / Mode A 后置。Stage 2 做协议和生态补齐。**Stage 2 后协议表面锁定**——后续不扩展 wire 协议；平台层（orchestrator / 多租户 / sandbox / SaaS）由 External Reference Architecture 实施。

**与竞品定位**：qwen-code daemon = building block + Unix-style 可组合；OpenCode 走端到端 SaaS；Anthropic Managed Agents 是托管服务。详 §五 / §六。

---

## 一、主线时间线

```
                Week 1-2      Week 3-6        Week 7-10        Week 11-12
qwen-code 主线
   Stage 1       ████ ✅ MERGED 2026-05-13（PR#3889 merge commit 870bdf2a）
   Stage 1.5a            ██ ✅ MERGED 2026-05-15（PR#4113 workspace hardening）
   1.5a must-haves/P0   ███ identity + lifecycle + reliability must-haves（~1-2w）
   Stage 1.5c/P0        ███ daemon-side control-plane parity / state CRUD（~1-2w）
   1.5-prereq/P1        ███ typed event contract + shared DaemonSessionClient（~1w）
   client adapters/P1   █████ primary clients behind flag: TUI / channels / web / IDE（~2-3w）
   remote-control/P2    ▒▒▒ remote-control revisit（后置，复用 daemon facade）
   Stage 1.5b/P2        ▒▒▒ Mode A revisit（后置）
   Stage 2                            ████████ 2a-2d（~3-4w）
   Stage 2e（可选）                                ██████ native in-process（~1-2w）
```

**核心判断**：qwen-code 是 building block，不是 SaaS 平台。Stage 2 完成后 daemon 协议表面 100% 稳定，外部集成方（商业平台 / k8s operator / 云厂商）基于此自由实现 orchestrator + 多租户 + SaaS。这与 OpenCode（端到端 SaaS）的设计哲学相反——保持 Unix 风格的可组合性。

**前置 PR 全部已合并**（2026-05-06 之前）：PR#3717 FileReadCache + PR#3810 5 路径 invalidation + PR#3723 共享 permission flow + PR#3739 transcript-first fork + PR#3642 `/tasks` + PR#3818 MCP rediscovery coalesce + PR#3836 Kind framework。

---

## 二、Stage 1：Mode B headless `qwen serve`（✅ MERGED 2026-05-13）

[**PR#3889**](https://github.com/QwenLM/qwen-code/pull/3889) `feat(cli,sdk): qwen serve daemon (Stage 1)` —— **✅ MERGED 2026-05-13 06:47 UTC**（merge commit `870bdf2a`）**+12993/-194 / 84 commits**。

### 落地的 9 个 STAGE1_FEATURES

```
['health', 'capabilities', 'session_create', 'session_list',
 'session_prompt', 'session_cancel', 'session_events',
 'session_set_model', 'permission_vote']
```

### 关键 commits（按时序）

| Commit | 改动 |
|---|---|
| `61f2f59a1` | scaffold `qwen serve` Express + auth + Host allowlist + /health + /capabilities |
| `8d7c03a5f` | HttpAcpBridge spawn `qwen --acp` per workspace + ACP 10s init + sessionScope:single |
| `ca996ecb5` | POST /prompt FIFO + /cancel + SessionNotFoundError |
| `41aa95094` | EventBus + SSE Last-Event-ID + 15s heartbeat + ring replay + client_evicted overflow |
| `6ee655f0a` | POST /permission first-responder vote + cancelSession resolves outstanding |
| `8206a64b5` | SDK DaemonClient + DaemonHttpError + parseSseStream |
| `a8ce5e08d` | /workspace/:id/sessions + /session/:id/model + errorMessage helper |
| `ad0e6ec06` | audit round 1: timing-safe bearer + IPv6 loopback ergonomics + failOnError |
| `27a164c` | Stage 1 文档补全（用户 quickstart + HTTP 协议 reference + SDK ts 示例 591 行）|
| **`6a170ef8`** 🌟 | **架构重构（第一轮）**：bridge-per-workspace + N session multiplexed via `QwenAgent.sessions: Map`；N=5 内存 300-500MB → 60-100MB（注：[PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) 第二轮简化为 1 daemon = 1 workspace × N session，去掉 multi-workspace 路由）|
| `f29353a2` | N:1 framing 修正 docs |
| `bbc7b8b6` + `b1767903` | chiga0 第 3 轮 review：Stage 1 scope honesty + 10 must-haves for Stage 1.5+ + Durability model |
| `734d833b` / `e18b8fa6` / `b37cc01c` | 多轮 ~30 review threads close（atomic write / read-size cap / 6 critical bugs + 6 follow-ups）|

### 体量与经验

| 维度 | 预估 | 实际 | 倍数 |
|---|---|---|---|
| LOC | ~700-1000 行 | **+12993 / -194** | **7-12x** |
| 工作量 | ~7-8 天 / 1 人 | 多周（84 commits 跨 5 轮 multi-model audit + chiga0 三轮 + LaZzyMan + tanzhenxin reviews + 维护者 N:1 framing 反馈 + 架构重构）| 几周 vs 1 周 |
| Review threads close | — | ~60+ | — |

**超出原因**：EventBus 完整实现（提前到 Stage 1）+ Timing-safe bearer + IPv6 loopback ergonomics + 多 reviewer 多轮 audit + 架构重构（`6a170ef8`）+ Stage 1 docs 补全。**最 expensive 的 follow-up 是 `6a170ef8` multi-workspace 重构**（reviewer 反馈触发的架构反思）；[PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) 第二轮进一步简化为 1 daemon = 1 workspace，与 `qwen --acp` stdio 1:1 心智完全对齐。

### Stage 1 已实现的 HA / 稳定性机制

| 机制 | 实现 |
|---|---|
| Daemon crash 自动重启 | 外部进程管理器（systemd / k8s）|
| Transcript-first fork resume | PR#3739（但 Stage 1 不在 HTTP 暴露 `loadSession` —— Stage 1.5 must-have #2）|
| SSE Last-Event-ID 重连 | commit `41aa95094` |
| Crash isolation 半径 | 单 daemon 全部 N session；跨 workspace 部署 = 跨 daemon process OS 进程级隔离 |
| `killSession` 简化 | [PR#4113](https://github.com/QwenLM/qwen-code/pull/4113)：单 daemon 单 child，无引用计数；最后一个 session 退出 = daemon 进入 idle，可选 graceful exit |
| timing-safe bearer auth + 401 uniform | commit `ad0e6ec06` |
| Durability model | 显式 documented as ephemeral（chiga0 must-have #10）|

主线**不需要**：multi-pod sticky session / Postgres Patroni / Redis Sentinel / per-tenant heap budget / Worker thread tenant isolation / 30 天 Soak/Chaos 测试矩阵——这些都是 External SaaS 运营层关切。

---

## 三、Stage 1.5：Mode B 优先 + client convergence（~3-4 周）

> **优先级重排（2026-05-15 决策）**：Mode B 已 ship Stage 1 + PR#4113 §02，需先做完 Mode B 生产化（must-haves + daemon-side state CRUD）让远端 client 完整可用；Mode A 价值依赖 1.5c daemon-side state CRUD（否则 Mode A 也只能服务 thin shell 远端 client），故 1.5b 后置。

### 拆分（按优先级排序）

| 优先级 | Sub-stage | 内容 | 状态 / 工作量 |
|:---:|---|---|---|
| ✅ | **1.5a §02** | [PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) 1 daemon = 1 workspace 收紧 | ✅ MERGED 2026-05-15 |
| **P0** | **1.5a must-haves** | chiga0 10 must-haves 剩 9 项（生产 blocker）| ~2 周（9 PRs 可并行）|
| **P0** | **1.5c** | daemon-side state CRUD 8 routes（Mode B 远端 client 摆脱 thin shell）| ~3-5d |
| **P1** | **1.5-prereq** | chiga0 6 architecture refactor findings（lift `AcpChannel` / `EventBus` / `PermissionMediator` 到 `@qwen-code/acp-bridge`）| ~1-2 周 |
| **P1** | **client adapters** | TUI / channels / web/debug / IDE 通过 `DaemonSessionClient` behind flag 接入 Mode B；默认切换必须等 P0/P1 | ~2-3 周，可与 P0/P1 试点并行 |
| **P2** | **remote-control revisit** | [#3929](https://github.com/QwenLM/qwen-code/pull/3929) / [#3930](https://github.com/QwenLM/qwen-code/pull/3930) / [#3931](https://github.com/QwenLM/qwen-code/pull/3931) 后续作为 daemon facade | 后置 |
| **P2** | **1.5b Mode A** | Mode A `qwen --serve` flag — [Issue #4156](https://github.com/QwenLM/qwen-code/issues/4156) doudouOUC 3-phase plan；A1 [PR#4160](https://github.com/QwenLM/qwen-code/pull/4160) ✅ MERGED；剩余 ~5-6d **推迟到 P0 完成后** | ~5-6d |
| **合计**（按 P0 → P1 → P2 顺序）| | | **~4 周 + Mode A 1 周** |

### 推进顺序（4 周窗口）

```text
Week 0 (now, 2026-05-15)
└─ 9 个 1.5a must-have PRs 并行启动（multi-contributor 友好）
   + 优先开 #2 loadSession HTTP（3-4d，最大用户痛点）
   + #1 sessionScope override + #3 pair tokens（生产 blocker）
   + #4-7 reliability + #8-9 ergonomics（小 PR，1-2d each）

Week 1
├─ must-haves PRs review + merge
└─ 1.5c daemon-side state CRUD 开 PR（独立开发 ~3-5d）

Week 2
├─ must-haves 剩余 merge
├─ 1.5c merge → Mode B 远端 client 摆脱 thin shell
└─ 1.5-prereq AcpChannel lift 启动（refactor 全部 stacks）

Week 3
├─ 1.5-prereq merge → Stage 2 协议层准备就绪
├─ TUI / channels / web/debug / IDE behind-flag adapters 试点
└─ 1.5b Mode A 启动（Issue #4156 A0/A2/A3 + Phase B/C）

Week 4
└─ 1.5b Mode A merge + 部署生态（Dockerfile / systemd / k8s manifest）
```

### Mode B client convergence 补充

client 统一接入不是让外部 client 直接 import daemon 内存里的 `EventBus`，而是稳定 HTTP/SSE 边界上的 typed event contract、shared reducer 和 `DaemonSessionClient`：

```text
qwen serve
  -> HTTP/SSE API
  -> internal EventBus fan-out
  -> typed event contract + DaemonSessionClient
  -> TUI / channels / web / IDE adapters
  -> JSONL / stream-json / dual-output sinks
  -> remote-control later as daemon facade
```

### 合入原则（每个 PR 必须满足）

Stage 1.5 不是一次性 rewrite，而是 **逐步测试、逐步迁移**。每个 PR 都必须能单独合入，并且默认不破坏现有功能：

| 原则 | 要求 |
|---|---|
| 单 PR 可合入 | 每个 PR 自带完整测试，合入后 main 仍可发布 |
| 向后兼容 | 不移除现有 route / event 字段 / CLI 行为；新增字段必须 additive + optional |
| 默认不切换 | TUI / channels / IDE 先 behind flag 或 adapter 双栈；默认仍走现有路径，直到验证完成 |
| serve 不破坏 | `qwen serve` Stage 1 routes 和 SDK 行为保持可用；新能力通过 capabilities feature tag 暴露 |
| 渐进迁移 | P0 must-haves / state CRUD / typed contract 可并行；client 先 behind flag 试点，再扩大默认面 |
| 可回滚 | 每个 client adapter 都能独立关闭，不影响其他 client 和 daemon |
| 测试先行 | 新 contract 有 unit tests；client adapter 有 smoke/e2e；老路径有 regression tests |

### Why Mode A 推迟到 1.5c 之后

Mode A 价值是 "本地 TUI super-client + 远端 client 同时接入同 daemon"——但**远端 client 在 1.5c 之前是 thin shell**（只能渲染 wire 流，看不到 daemon-side `/memory` / `/mcp` / `/agents` 状态）。先 ship 1.5c 让远端 client 完整功能 → 再 ship 1.5b 让本地 TUI 加进来，**远端 client 体验从 Day 1 就完整**，避免"Mode A 上线后远端 client 还是残缺"的 UX 断层。

### 1.5a — Workspace hardening（✅ shipped）

[**PR#4113**](https://github.com/QwenLM/qwen-code/pull/4113) `refactor(serve): 1 daemon = 1 workspace (#3803 §02)`（MERGED 2026-05-15，`790f2d04`，+2051/-434）已实施 §02 核心决策。

关键结果：

- bridge state 折叠为单 workspace slot。
- `BridgeOptions.boundWorkspace` required。
- `POST /session` 可省略 `cwd`，默认使用 daemon boot workspace。
- mismatched `cwd` 返回 `400 workspace_mismatch`。
- `/capabilities.workspaceCwd` 暴露 bound workspace。
- 新增 `--workspace <path>` flag。

这一步把 Mode B 的边界钉死：**一个 daemon 只服务一个 workspace，多个 session 复用一个 `qwen --acp` child**。多 workspace 由多个 daemon process / orchestrator 解决。

### 1.5-prereq — Mode B event contract / bridge primitives

当前 `EventBus` 已经在 Stage 1 实现，但仍是 `packages/cli/src/serve/eventBus.ts` 的 serve 私有实现，事件 envelope 也还是：

```ts
{
  v: 1,
  type: string,
  data: unknown,
  id?: number,
  originatorClientId?: string,
}
```

要让 TUI / channels / web / IDE 真正统一接入，不是让它们直接 import daemon 里的 `EventBus` 对象，而是把它背后的 **event contract** 稳定下来。Mode B 下外部 client 的直接边界仍然是 HTTP server：

```text
client
  -> DaemonSessionClient
  -> POST /session/:id/prompt
  -> GET /session/:id/events  # SSE projection of internal EventBus
  -> daemon internal EventBus
```

因此 `EventBus lift` 的含义是：抽出 typed event schema、reducer、server-side fan-out primitive 和 transport adapter，而不是要求外部 client 直接 subscribe 一个内存对象。

| 工作项 | 目标 |
|---|---|
| typed `SessionEvent` / `ControlEvent` | 把 `data: unknown` 收敛为 discriminated union |
| shared `DaemonSessionClient` | SDK / TUI / channels / IDE 共用 HTTP/SSE client |
| `AcpChannel` / transport primitive | 把 child stdio、in-memory channel、daemon HTTP transport 的 bridge 边界拆清 |
| `PermissionMediator` | 统一 daemon first-responder、channels、stream-json / non-interactive 的 permission 策略 |
| Event reducer | 从 daemon events 构建 client view-model，避免每个 client 自己拼状态 |
| output sinks | JSONL / stream-json / dual-output 变成同一 event stream 的 sink |
| capability negotiation | `/capabilities` 增加 `protocol_versions` / feature registry，client 可按能力降级 |

这一步是所有 client 默认切换的前置；可以与 P0 must-haves / state CRUD 并行启动，不需要等 Mode A。

**兼容性要求**：

- 旧 `DaemonEvent` envelope 继续可解析；typed union 是 SDK/helper 层增强。
- `data: unknown` 不立即删除；新增 typed helpers 与旧 consumer 并存。
- 新 capability 字段必须 optional，旧 daemon / 新 client、旧 client / 新 daemon 都能工作。
- Event reducer 必须只消费已有事件，不能要求 daemon 立即新增全量 state event。

### Client adapters — Primary clients（优先 TUI / channels / web / IDE）

目标是让现有 client 不再各自拥有一条 parallel runtime，而是接到同一个 Mode B daemon：

| Client | 当前状态 | Mode B 适配方向 | 接入顺序 |
|---|---|---|---|
| **TUI** | 走内部 Ink / `useGeminiStream` 路径 | 新增 attach-to-daemon render target；用 shared reducer 渲染 daemon `SessionEvent`；本地 TUI 不再拥有 runtime | 第一波 behind flag |
| **channels** | `packages/channels/base/AcpBridge.ts` 自己 spawn `qwen --acp` | 新增 daemon transport；保留 channel routing，但 prompt/event/cancel/model 走 `DaemonSessionClient` | 第一波 behind flag |
| **web/debug** | [PR#4132](https://github.com/QwenLM/qwen-code/pull/4132) `/demo` OPEN / changes requested | 作为最薄 POST+SSE client 验证面，优先暴露 event schema / reconnect / permission UI 问题 | 第一波 behind flag |
| **IDE** | VSCode companion 直接 spawn `qwen --acp` | 新增 daemon transport behind flag；先覆盖 session create/prompt/events/cancel/model，再补 file/context/control routes | 第二波 behind flag |
| JSONL / stream-json / dual-output | CLI 内部 adapter | 变成 daemon event sinks；不再驱动 runtime，只消费 typed events | 与 contract 并行 |
| remote-control | [#3929](https://github.com/QwenLM/qwen-code/pull/3929) / [#3930](https://github.com/QwenLM/qwen-code/pull/3930) / [#3931](https://github.com/QwenLM/qwen-code/pull/3931) draft stack | **后置**；等上述 clients 收敛后作为 daemon facade 复用同一 contract | P2 deferred |

适配可以先 behind flag 开始；默认切换需要等 P0 的 1.5a must-haves / 1.5c state CRUD，以及 P1 的 1.5-prereq contract / bridge primitive 完成。

**每个 client 的合入策略**：

| Client | 第一个可合入 PR | 默认切换条件 |
|---|---|---|
| TUI | `qwen tui --daemon-url` / env flag attach 原型；只读渲染 + prompt/cancel/model | control-plane parity 覆盖常用 dialogs；TUI regression 通过 |
| channels | 新 `DaemonChannelTransport` behind config flag；保留 `AcpBridge` 默认 | IM routing、permission、reconnect、sessionScope 验证通过 |
| web/debug | `/demo` 或独立 web client 只依赖 HTTP/SSE；不扩大 daemon CORS 默认面 | allow-origin / auth / reconnect 策略明确 |
| IDE | daemon transport behind flag；默认仍 direct ACP child | file/context/control routes 补齐；workspace mismatch 和 resume 测试通过 |
| output sinks | JSONL / stream-json adapter 从 typed events 生成旧格式 | 快照和现有 CLI output tests 通过 |

### 1.5c — daemon-side state CRUD / control-plane parity

Stage 1 的主链路已经可用：prompt / events / cancel / model / permission vote。但 TUI、channels、web、IDE 要做完整 client，还需要 daemon 暴露 runtime state 和 mutation API。

| 新 wire route / capability | 对应能力 | 主要 client |
|---|---|---|
| `GET/POST /workspace/:id/memory` | memory 查看 / 更新 | TUI / IDE / web |
| `GET /workspace/:id/mcp` + `POST .../mcp/:server/restart` | MCP 状态 / 重启 | TUI / IDE / web |
| `GET/POST /workspace/:id/agents` | agents 管理 | TUI / IDE |
| `POST /workspace/:id/tools/:name/enable` | tools allowlist | TUI / IDE |
| `POST /session/:id/approval-mode` | approval mode | TUI / IDE / channels |
| `GET /session/:id/context` | context usage | TUI / IDE / web |
| `GET /session/:id/supported-commands` | command palette / UI affordance | TUI / IDE / web |
| `GET /workspace/:id/providers` + `POST /session/:id/model` | provider/model 状态 | TUI / IDE / web |
| `POST /workspace/:id/auth/device-flow` 或 Capability RPC | auth | TUI / IDE / web |
| `POST /workspace/:id/init` | project init / trust | TUI / IDE |

这一步的原则：**daemon 是 runtime owner，client 只做 view + command surface**。

**兼容性要求**：

- 所有新 route 都必须有 capability tag；client 发现不存在时 fallback 到旧行为或隐藏 UI。
- 新 route 不改变 daemon 启动默认配置；不自动 mutate settings。
- 对已有 `/session/:id/model`、`/session/:id/prompt` 等 route 不做 breaking schema 改动。
- state CRUD 首先支持 read-only / status，再加入 mutation，降低风险。

### 1.5a must-haves — identity + lifecycle + reliability

来源仍是 chiga0 PR#3889 downstream-consumer review：Stage 1 适合原型和本地小团队，但 TUI/channel/web/IDE 正式默认接入前，需要补多 client 的硬约束。

| 类别 | 必需项 |
|---|---|
| Client identity | pair tokens + per-client revocation；daemon-stamped `originatorClientId`，不能由 client 自报 |
| Permission | `POST /session/:id/permission/:requestId`；session-scoped pending map；`permission_already_resolved` event；`PermissionMediator` 收敛 ACP direct / daemon / stream-json |
| Session lifecycle | `loadSession` / `unstable_resumeSession` HTTP；close/delete session；per-request `sessionScope` override；`POST /session/:id/_meta` |
| Reliability | client heartbeat；larger/per-session replay ring；`slow_client_warning` before `client_evicted`；stream gap semantics |
| Browser/network | named `--allow-origin` / same-origin web strategy；phantom SSE cleanup；可选 WebSocket transport |

**兼容性要求**：

- 共享 bearer token 继续可用；pair token / per-client token 是增强，不是立即替换。
- `originatorClientId` 由 daemon-stamped 新字段承载；旧 self-declared 字段进入兼容期。
- `POST /permission/:requestId` 保留兼容；新增 `POST /session/:id/permission/:requestId` 后逐步迁移。
- `loadSession` / `resume` 是 additive route；daemon restart 语义不在同一 PR 内改变。

### 1.5f — remote-control later

remote-control 仍然有价值，但优先级后置。原因：

- 当前 [#3929](https://github.com/QwenLM/qwen-code/pull/3929) / [#3930](https://github.com/QwenLM/qwen-code/pull/3930) / [#3931](https://github.com/QwenLM/qwen-code/pull/3931) 是 draft / changes requested，且包含 parallel worker/WebSocket/runtime 路线。
- 今天的 Mode B 决策要求所有 client 先收敛到 daemon HTTP/SSE API，并消费同一套 EventBus-backed typed event contract。
- TUI / channels / web / IDE 是基础 client 面，先完成它们能反过来定义 remote-control 应复用的 contract。

后续 remote-control 应该降级为：

```text
remote-control UI / pairing / optional WS facade
  -> DaemonSessionClient
  -> qwen serve HTTP/SSE
  -> daemon internal EventBus
```

而不是重新拥有 session runtime、event log 或 worker server。

### Mode A parking lot

[**Issue #4156**](https://github.com/QwenLM/qwen-code/issues/4156) 仍保持 open 作为 Mode A 设计记录，但最新结论是“Mode A 暂时 hold，核心推进 Mode B”。

[**PR#4160**](https://github.com/QwenLM/qwen-code/pull/4160) `refactor(serve): extract createInMemoryChannel helper (#4156 A1)` 已 MERGED 2026-05-15。它来自 Mode A stack，但在当前 roadmap 中只记录为可复用 primitive：未来 native in-process / test harness / paired ACP channel 仍可使用，不代表 Mode A 继续推进。

### Cross-module refactor findings（仍然有效）

> 来源：chiga0 第 2 轮 review [comment 4427773706](https://github.com/QwenLM/qwen-code/pull/3889#issuecomment-4427773706) "cross-module unification"。Mode A hold 后，这些 finding 反而更应该服务 Mode B client convergence。

| # | Finding | Mode B 改造方向 |
|---|---|---|
| 1 | `HttpAcpBridge` 混淆 transport + bridging | 抽 `AcpChannel` interface + `Transport` interface，供 serve / channels / IDE 复用 |
| 2 | `EventBus` 私有于 HTTP/SSE | 抽出 typed event contract / reducer / server-side fan-out primitive；外部 client 仍通过 HTTP/SSE 接入 |
| 3 | Permission flow 自实现（vs `ControlDispatcher`）| Lift `PermissionMediator` + first-responder / designated / consensus / local-only policy |
| 4 | `BridgeClient` fs 是 fork | Inject `FileSystemService` ctor dep，避免 daemon fs 语义和 core 分叉 |
| 5 | Capability registry hard-coded | Plug-in registry + feature negotiation + future `POST /ext/:method` |
| 6 | `dualOutput` / `remoteInput` convergence | 把输出和输入 sidecar 变成 daemon event sink / command source |

---

## 四、Stage 2：daemon 协议补齐（拆分 2a-2d，~3-4 周）

> **拆分动机**（chiga0 Recommendation 5）：原 Stage 2 6 项打包到 "1-2w"——protocol completion / observability / perf evaluation / ecosystem 是 4 个不同 workstream，混在一起 review/merge 阻塞。

| Sub-stage | 内容 | 工作量 |
|---|---|---|
| **2a Protocol** | WebSocket bidi + `/health?deep=1` + `POST /ext/:method` + permission policy schema | ~5-7d |
| **2b Ecosystem** | OpenAPI codegen + `HttpTransport` SDK 适配器 | ~5-8d |
| **2c Observability** | Prometheus metrics + mDNS + `--max-sessions` guard rail | ~3-5d |
| **2d Perf eval + docs** | TTI / streaming / memory baseline + cookbook | ~4-5d |
| **合计**（可并行 2a/2c · 后接 2b · 收尾 2d）| | **~3-4 周** |

### 可选 Stage 2e — Native in-process

去掉 `qwen --acp` child 桥接，daemon 直接 import `QwenAgent`——省 ~50MB child 开销 + IPC 延迟。工作量 ~1-2 周。**仅在大规模 SaaS（500+ session / 机）必需时推进**。

---

## 五、External Reference Architecture（参考实现，非项目路线图）

> qwen-code 主线只交付 daemon building block。下面是给外部集成方（商业平台 / k8s operator / 云厂商）的设计参考蓝图，**不在 qwen-code 项目路线图**。

### 5.1 Cross-Daemon Orchestrator（跨 daemon process / 跨机器）

| 组件 | 工作量参考 |
|---|---|
| `qwen-coordinator` HTTP front | ~3-5d |
| Daemon process pool / spawn-per-tenant | ~2-3d |
| Cross-daemon sessionId → daemonUrl 注册表 | ~2d |
| Cross-daemon aggregate API | ~2d |
| Sticky cookie / failover routing | ~2-3d |
| **合计** | **~1.5-2 周** |

> **何时需要**：单机 daemon 容量到顶（N=50+ workspaces 或 cross-tenant 隔离要求）需要多 daemon process 时；k8s 多 pod 部署时。单机单 daemon 完全不需要本节。

### 5.2 Multi-tenancy + OIDC + Quota + Audit

> 🚨 **Multi-Tenant 关键约束**（1 daemon = 1 workspace 模式下天然 OS 进程级隔离）：daemon 同 workspace 内 N session **共享同 `qwen --acp` child 的 OS 权限**。**不可让多 tenant 共一个 daemon**——orchestrator 必须在 daemon process 层做 1:1 tenant 绑定（1 daemon = 1 tenant × 1 workspace）：
> - **Workspace 层（推荐）**：1 tenant ↔ 1 workspace
> - **Daemon process 层（高安全）**：1 tenant ↔ 独立 daemon process

| 组件 | 工作量参考 |
|---|---|
| Tenant 抽象 + Workspace ACL | ~3-5d |
| AuthN 4 模式（Bearer / OIDC / mTLS / cookie）| ~5-7d |
| Quota engine（Redis sliding-window + reservation）| ~5-7d |
| Audit log 4 通道（jsonl / syslog / OpenTelemetry / Kafka）| ~3-5d |
| **合计** | **~3-4 周 / 1-2 人** |

### 5.3 Shell Sandbox

主线 daemon 默认 **NoSandbox**——agent 跑 daemon 进程权限（PR#3889 现状）。同 workspace N session 共享同 `qwen --acp` child 的 OS 权限，多 tenant / 跨用户必须由 orchestrator 做 daemon-per-tenant 隔离。

| 方向 | 方案 | 工作量参考 |
|---|---|---|
| 本地 sandbox | OS user 切换 / Linux namespace / Container（Docker/Podman）| ~2-3w |
| 远程 sandbox | SSH / gRPC / k8s Job / containerd over TCP | ~2-3w |
| **合计** | | **~4-6 周 / 1 人** |

### 5.4 SaaS deployment

| 组件 | 工作量参考 |
|---|---|
| k8s native（StatefulSet + PVC + Service mesh）| ~1-2w |
| Postgres state + Redis cache + S3 transcript | ~1-2w |
| Multi-region / cross-geo scheduling | ~1-2w |
| **合计** | **~3-6 周 / 2-3 人** |

---

## 六、vs OpenCode（最相似的竞品）

### 设计哲学

| 维度 | OpenCode | Qwen Daemon |
|---|---|---|
| 进程模型 | 单 daemon 多 workspace（in-process `Map<workspace, Instance>` ALS）| **1 daemon = 1 workspace × N session**；多 workspace = 多 daemon process（OS 进程级隔离）|
| HTTP 框架 | Hono | Express 5（复用 vscode-ide-companion）|
| 协议 schema | OpenAPI codegen（13525 行 `openapi.json`）| **复用 ACP NDJSON zod schema** |
| Session 共享 | 否（per-SDK call）| **默认 `sessionScope: 'single'` + live collaboration** |
| 数据持久化 | SQLite（drizzle-orm）| JSONL（PR#3739）+ SQLite for permission decisions |
| 默认安全 | 无 token 警告，仍启动 | **无 token + 0.0.0.0 拒绝启动** |
| 上下文传播 | Effect-TS `LocalContext` | wire 自带 sessionId 路由 |

### 关键差异点

1. **复用 ACP zod schema**——0 设计成本 + 与 IDE/Zed 生态天然兼容
2. **IM Channels 多渠道路由**（`packages/channels/`：钉钉 / Telegram / 微信 / Slack）—— OpenCode 无等价
3. **PR#3723 应用层权限流**（4 mode 共享 evaluatePermissionFlow）
4. **默认 0.0.0.0 + 无 token = 拒绝启动**（比 OpenCode 严格）
5. **1 daemon = 1 workspace** —— 主场景（IM Channels / 多 tenant SaaS / K8s）对强隔离 / quota / blast radius 要求高，与 OpenCode 哲学差异显著

### 性能对比

| 维度 | OpenCode（多 workspace ALS）| Qwen (1 daemon = 1 workspace) |
|---|---|---|
| 启动时间 | ~2-3s | ~2-3s |
| 同 workspace 第 N session | <50ms | <200ms（attach existing child）|
| 跨 workspace 第 1 session | <50ms（同 daemon 内）| ~2-3s（启新 daemon）|
| 100 跨 workspace session 内存 | ~200MB | ~10-15GB（100 daemon × baseline）|
| Blast radius | 全部 workspace | **1 workspace** |
| 隔离强度 | 应用层 ALS | **OS 进程级**（最强）|
| Quota 颗粒度 | 需应用层抽象 | cgroup / systemd 直接套 |

跨 workspace 高密度场景 OpenCode 内存更省，但 Qwen 换得 OS 进程级隔离 + cgroup quota + K8s 天然契合 + blast radius 最小。

---

## 七、vs Anthropic Managed Agents

> **本节是 External Reference Architecture 范畴**——qwen-code 主线只交付 daemon building block，不直接对标 Anthropic Managed Agents（云 SaaS 平台）。本节对比的是**基于 qwen-code daemon + 完整 External Reference Architecture 包装出来的 "Managed Qwen Agents" 产品** vs Anthropic Managed Agents。
>
> **免责声明**：基于 Anthropic 公开文档（截至 2026 Q1）；Managed Agents 是闭源服务，具体细节、定价、内置工具可能已变更。本系列与 Anthropic / Qwen 团队均无关联。

### 架构哲学相似性

Anthropic Managed Agents 的内部模型很可能是 per-session container/process（云原生隔离的最自然形态）；**Qwen daemon 1 daemon = 1 workspace × N session 在 daemon 内偏离纯 per-session 隔离**（共 OS 权限 + 共 MCP），跨 daemon（= 跨 workspace）仍保持进程级隔离。Anthropic 内部具体实现未公开，可能也走类似 hybrid 模型节省 container baseline。

| 维度 | Anthropic Managed Agents | Qwen daemon |
|---|---|---|
| 本质 | 云托管 SaaS agent runtime | 自托管 agent daemon |
| 代码 | 闭源 | Apache-2.0 开源 |
| 模型 | Claude only | 任意 provider（DashScope / Claude / OpenAI / 自训练）|
| 进程模型 | 推测 per-session container/process 或 hybrid | 1 daemon = 1 workspace × N session multiplexed |
| Session 共享 | per call 独立 / 持久化跨 call | sessionScope:single 多 client 共享 |
| 多租户 | Anthropic 管理 | 由 External orchestrator 做 1 tenant 1 workspace / daemon process |

### 关键差异

- **自托管 vs 云托管**：Qwen 走 building block 路线；Anthropic 提供托管服务
- **IM 多渠道生态**：Qwen 通过 `packages/channels/` + IM 路由原生支持 Telegram / 微信 / 钉钉 / Slack；Anthropic 只暴露 API
- **Java SDK 直连**：Qwen 唯一有 Java acp-sdk，daemon 后跨语言更顺
- **Background tasks 4 kinds 跨 client 可见**：Qwen kind framework（PR#3836）能在 daemon 模式下让所有 client 看到所有后台任务（agent/shell/monitor/dream）

---

## 八、风险与缓解

| 风险 | 缓解 |
|---|---|
| 单 daemon process OOM / race condition | 外部 orchestrator（systemd / k8s）自动重启；transcript JSONL 持久化保证 PR#3739 fork-resume；Stage 1.5 must-have #2 `loadSession` HTTP 后 client 跨 daemon restart 重建 |
| MCP server 跨 session 状态泄漏 | per-server `requiresPerSession` flag fallback；同 workspace N session 共享需审计；跨 workspace 进程级隔离不受影响 |
| FileReadCache 与 history rewrite 同步 | PR#3810 已修 5 路径 |
| Bearer token 泄漏 | 默认 0.0.0.0 binding 拒绝启动 + timing-safe compare + 401 uniform |
| `process.chdir()` 误调 | 落地后 grep audit + CI 守卫 |
| 与现有 ACP agent 行为不一致 | Stage 1 stdio 桥接持续保留作 reference impl |
| 用户期望"开箱即用 SaaS"失望 | README 顶部明确 scope：daemon building block，平台层外部实现 |

---

## 九、不复用 / 待弃用资产

| 资产 | 处理 | 理由 |
|---|---|---|
| `ProcessTransport.ts` 的 `spawn` 逻辑 | 不复用 | 假设对端是 CLI 子进程；daemon 模式下对端是 HTTP server，HttpTransport 从零写 |
| `vscode-ide-companion/src/ide-server.ts` | Stage 2 后逐步弃用 | VSCode 直接连 daemon 即可；保留 deprecation 期 |

---

下一篇：[← 回到 README](./README.md)
