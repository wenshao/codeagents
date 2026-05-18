# Qwen Code Daemon 架构设计（系列文档）

> Qwen Code 引入 HTTP daemon 模式的完整设计方案。基于 [SDK / ACP / Daemon 架构 Deep-Dive](../sdk-acp-daemon-architecture-deep-dive.md) 第七章"Qwen Code 引入 daemon 的工作量评估"展开为可执行的工程蓝图。

## 一、TL;DR

> **2026-05-15 决策更新**：先忽略 Mode A（`qwen --serve`）。后续 roadmap 以 **Mode B：`qwen serve` headless daemon 作为底层 runtime** 为主线；Mode A 暂停在 [Issue #4156](https://github.com/QwenLM/qwen-code/issues/4156) 里作为 parking lot，已合并的 [PR#4160](https://github.com/QwenLM/qwen-code/pull/4160) 仅作为可复用 in-memory channel primitive 记录。

```
ACP NDJSON 协议 → HTTP+SSE daemon
1 daemon process = 1 workspace × N sessions multiplexed
```

`qwen serve` 启动时绑定 cwd = 单 workspace，daemon 内嵌单个 `qwen --acp` child；N session 通过 `QwenAgent.sessions: Map` 多路复用同一 child。多 workspace 部署 = 多 daemon process（systemd / docker / k8s 各 1 process）。

**关键设计依据**：
- 与 `qwen --acp` stdio **1:1 心智对齐**
- 跨 workspace = 跨 daemon process = **OS 进程级真隔离**（最强）
- systemd / cgroup / docker 直接 = per-workspace quota
- K8s 云原生天然契合（1 pod = 1 daemon = 1 workspace）
- Blast radius 最小（daemon crash 只影响 1 workspace）

**两种部署模式**：

| 模式 | 命令 | TUI | 适用场景 |
|---|---|:---:|---|
| **Mode B** | `qwen serve [--port N]` | ❌ | **当前主线**：服务器 / 容器 / 远端机器 / K8s pod / 所有 client 的统一 runtime |
| **Mode A** | `qwen --serve [--port N]` | ✅ 本地渲染 | **暂停推进**：待 Mode B HTTP/SSE event contract / control-plane / client identity 稳定后再评估 |

**当前状态**：
- ✅ [PR#3889](https://github.com/QwenLM/qwen-code/pull/3889) Stage 1 MERGED 2026-05-13（`qwen serve` headless daemon）
- ✅ [PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) MERGED 2026-05-15（1 daemon = 1 workspace 收紧 + `--workspace` flag + `400 workspace_mismatch`）
- ✅ [PR#4160](https://github.com/QwenLM/qwen-code/pull/4160) MERGED 2026-05-15（`createInMemoryChannel` helper；从 Mode A stack 中产出，但现在只作为通用 primitive）
- 🔧 **Mode B 优先**（2026-05-15 决策）：Stage 1.5a must-haves（9 项）+ Stage 1.5c daemon-side state CRUD 优先；Mode A（[Issue #4156](https://github.com/QwenLM/qwen-code/issues/4156)）推迟到 1.5c 后
- 📋 **Implementation tracker**：[Issue #4175](https://github.com/QwenLM/qwen-code/issues/4175) doudouOUC Mode B v0.16 production-ready **31-PR rollout plan**（7 Wave：Protocol foundation → Session lifecycle → Wave 2.5 reliability → Read-only control plane → Auth-gated mutation → Architecture extraction → Release hardening）—— 详 [§06 §三·一](./06-roadmap.md#三一-issue-4175--31-pr-wave-breakdown-production-ready-tracker)
- 🎉 **Wave 1+2+2.5+3 完整 + Wave 4 4/7 + 3 在飞**（2026-05-16~18 共 **27 MERGED + 7 OPEN/draft + 2 CLOSED**：18 Wave PRs + 5 follow-up + 3 bonus Stage 0 + 1 外部；Wave 4 PR 17/20/21 + PR 14b + 3 adapter wire-up；Wave plan 进度 **18/31 = 58%**；**无 block 点**）：
  - ✅ [PR#4191](https://github.com/QwenLM/qwen-code/pull/4191) Wave 1 PR 2 capability registry **MERGED 2026-05-16 10:07** (doudouOUC)
  - ✅ [PR#4209](https://github.com/QwenLM/qwen-code/pull/4209) Wave 2 PR 5 per-request `sessionScope` override **MERGED 2026-05-16 15:54** (doudouOUC)
  - ✅ [PR#4205](https://github.com/QwenLM/qwen-code/pull/4205) Wave 1 PR 1 baseline harness **MERGED 2026-05-16 16:41** (doudouOUC)
  - ✅ [PR#4201](https://github.com/QwenLM/qwen-code/pull/4201) Wave 1 PR 3 DaemonSessionClient skeleton **MERGED 2026-05-16 17:01** (chiga0)
  - ✅ Wave 2 follow-up [PR#4214](https://github.com/QwenLM/qwen-code/pull/4214) **MERGED 2026-05-16 17:51** (doudouOUC) — capability registry 三套来源 lockstep 修
  - ✅ [PR#4217](https://github.com/QwenLM/qwen-code/pull/4217) Wave 1 PR 4 typed event schema **MERGED 2026-05-17 04:31** (chiga0, 5 轮 review / 2 轮自我修复；reducer hardening invariants：单调 lastEventId / 64-cap pendingPermissions / 诊断计数 / immutable storage)
  - ✅ [PR#4222](https://github.com/QwenLM/qwen-code/pull/4222) Wave 2 PR 6 HTTP load/resume session **MERGED 2026-05-17 04:58** (doudouOUC, 5 轮 review, 体量翻倍至 +2078/-51 16 文件；核心修：asymmetric coalesce guard bidirectional 收紧)
  - ✅ [PR#4231](https://github.com/QwenLM/qwen-code/pull/4231) Wave 2 PR 7 daemon-stamped client identity **MERGED 2026-05-17 08:19** (chiga0, 1h23m, wenshao 9 parallel review agents; randomUUID `client_` 前缀 122 bits entropy)
  - ✅ [PR#4232](https://github.com/QwenLM/qwen-code/pull/4232) Wave 2 PR 8 session-scoped permission route **MERGED 2026-05-17 09:48** (chiga0, 2h44m, rebase 到 main; permission_already_resolved event + bounded record + parsePermissionOutcome 共享 helper)
  - ✅ [PR#4235](https://github.com/QwenLM/qwen-code/pull/4235) Wave 2.5 PR 9 client heartbeat **MERGED 2026-05-17 10:57** (doudouOUC, 2h00m, **首轮一把过**；3471 serve/SDK tests pass + 4 安全不变式 + lockstep 维持)
  - ✅ [PR#4237](https://github.com/QwenLM/qwen-code/pull/4237) Wave 2.5 PR 10 SSE replay sizing + slow_client_warning backpressure **MERGED 2026-05-17 11:30** (doudouOUC, 2h19m, 3 轮 review; BoundedAsyncQueue.liveCount pre-emptive refactor + 8000 ring + 75%/37.5% hysteresis)
  - ✅ [PR#4236](https://github.com/QwenLM/qwen-code/pull/4236) Wave 4 PR 15 mutation gating helper + --require-auth **MERGED 2026-05-17 12:10** (doudouOUC, 3h06m, wenshao 端到端 verify 4-cell matrix, 解锁 Wave 4 PR 16-21)
  - ✅ [PR#4240](https://github.com/QwenLM/qwen-code/pull/4240) Wave 2.5 PR 11 session metadata + close/delete lifecycle **MERGED 2026-05-17 12:42** (doudouOUC, 2h16m, 4 轮 review, 1 Critical typecheck + events.close() ordering 修)
  - ✅ [PR#4241](https://github.com/QwenLM/qwen-code/pull/4241) Wave 3 PR 12 read-only status routes **MERGED 2026-05-17 13:37** (doudouOUC, 3h02m, wenshao 9 parallel agents + mimo-v2-5-pro + gpt-5.5 multi-model review, clientId forward for audit symmetry)
  - ✅ Follow-up [PR#4245](https://github.com/QwenLM/qwen-code/pull/4245) integration test mirror align **MERGED 2026-05-17 14:53** (doudouOUC, 40m 一把过；第三次 drift —— mirror pattern 工程债待解)
  - ✅ [PR#4251](https://github.com/QwenLM/qwen-code/pull/4251) Wave 3 PR 13 preflight + env diagnostics **MERGED 2026-05-17 23:29** (doudouOUC, 7h40m, 7 轮 review; **第六次 drift 被 wenshao 在 PR review 抓**; execSync→execFile migration + safeProxyValue 3-stage parse + 5 strict invariants 含 build-time grep + 第一个 land closed errorKind 7-value taxonomy)
  - ✅ [PR#4247](https://github.com/QwenLM/qwen-code/pull/4247) Wave 3 PR 14 MCP client guardrails **MERGED 2026-05-18 04:07** (doudouOUC, 13h09m daemon 项目史上最艰难一合; 9+ 轮 review / 11 [Critical] / 4 LLM model 多轮 audit; weReserved-driven 对称清理 across 3 spawn paths)
  - ✅ [PR#4249](https://github.com/QwenLM/qwen-code/pull/4249) Wave 4 PR 16 workspace memory + agents CRUD **MERGED 2026-05-18 06:27** (doudouOUC, **15h20m 新 lifetime 纪录**; 11 rounds + 6 LLM model; fold-in cascade 2a→2j; 最终 +5318/-8 23 文件)
  - ✅ [PR#4269](https://github.com/QwenLM/qwen-code/pull/4269) Wave 4 PR 19 safe workspace file read routes **MERGED 2026-05-18 08:17** (doudouOUC, **1h54m 极短** — PR 18 chokepoint 红利; 525/525 tests + 安全边界全过)
  - ✅ Follow-up [PR#4279](https://github.com/QwenLM/qwen-code/pull/4279) Windows 路径 normalize **MERGED 2026-05-18 09:53** (doudouOUC, **26m 极短 — daemon 项目最快 hotfix** 破 PR#4245 40m; `workspaceRelative` 漏 `path.sep` → `/` normalize)
  - 🔧 [PR#4280](https://github.com/QwenLM/qwen-code/pull/4280) Wave 4 PR 20 file write/edit OPEN (doudouOUC, 2026-05-18 09:50, +2108/-75 20 文件; atomic temp+rename + content-hash precondition 防 stale + edit single-match policy + 382 tests)
  - 🔧 [PR#4282](https://github.com/QwenLM/qwen-code/pull/4282) Wave 4 PR 17 approval/tools/init/MCP-restart OPEN (doudouOUC, 2026-05-18 10:06, +2746/-10 26 文件; 4 strict-gated mutation route + 新 TrustGateError cross-bundle exception)
  - 🔧 [PR#4271](https://github.com/QwenLM/qwen-code/pull/4271) Wave 3 PR 14b MCP guardrail push events + hysteresis OPEN+CONFLICTING (doudouOUC, 2026-05-18 07:16, +1824/-16, PR 14 deferred follow-up; mcp_budget_warning 75/37.5% hysteresis + mcp_child_refused_batch coalesced; PR-internal lockstep ✅)
  - ✅ [PR#4250](https://github.com/QwenLM/qwen-code/pull/4250) Wave 4 PR 18 FileSystemService boundary **MERGED 2026-05-18 05:14** (doudouOUC, 13h55m daemon 项目最长 lifetime; 10 rounds 70 review threads 全 resolved; TOCTOU + UTF-8 off-by-one + writeText guard + 13+ Critical 全修)
  - 🔧 [PR#4255](https://github.com/QwenLM/qwen-code/pull/4255) Wave 4 PR 21 OAuth device-flow route OPEN (doudouOUC, 2026-05-17 17:26, +3527/-8 项目史上最大 PR；OAuth 2.0 RFC 8628 brokered through daemon；4 route + 5 typed event + build-time grep 防 browser-spawn regression + BrandedSecret 4-way redaction + 3 pre-PR agent / 12 P0+P1 fold-in)
  - ✅ PR 3 follow-up [PR#4225](https://github.com/QwenLM/qwen-code/pull/4225) DaemonSessionClient hardening **MERGED 2026-05-17 07:05** (chiga0, 多模型 /review 4 轮；chiga0 让步把 eager guard 改回 lazy + cursor monotonicity + abort propagation + event.id validation)
  - ⚠️ [PR#4226](https://github.com/QwenLM/qwen-code/pull/4226) typed event schema 竞品 OPEN (doudouOUC) — 与 PR#4217 重叠，待 close 或拆 reducer 作 Wave 5 PR 25 提前
  - ✅ Bonus Stage 0 spike 全 MERGED 2026-05-18: [PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) channel (02:21) + [PR#4199](https://github.com/QwenLM/qwen-code/pull/4199) IDE (02:38) + [PR#4202](https://github.com/QwenLM/qwen-code/pull/4202) TUI (03:22) (chiga0; Wave 5 PR 26 提前)
  - ⚠️ Bonus Stage 1 wire-up 调整: [PR#4260](https://github.com/QwenLM/qwen-code/pull/4260) TUI + [PR#4263](https://github.com/QwenLM/qwen-code/pull/4263) IDE **CLOSED 06:59** (Stage 2 直接覆盖); [PR#4261](https://github.com/QwenLM/qwen-code/pull/4261) channel `--daemon-url` 仍 draft (channel 无 Stage 2)
  - 🔧 Bonus Stage 2 experimental flag-gated 2 PR draft: [PR#4266](https://github.com/QwenLM/qwen-code/pull/4266) `--experimental-daemon-tui` / [PR#4267](https://github.com/QwenLM/qwen-code/pull/4267) `qwen-code.experimentalDaemonIde` (chiga0, 2026-05-18 05:06 起; channel stage 2 待开)
- ✅ [PR#4132](https://github.com/QwenLM/qwen-code/pull/4132) `/demo` debug page (jifeng) **MERGED 2026-05-18 08:31** —— 4 天 24 reviews 终于合，daemon 项目 OPEN 最长 PR；XSS 修 (daemon-emitted poisoned events 威胁模型) + rebase 过 #4247/4250/4251 冲突
- 🧭 [PR#3929](https://github.com/QwenLM/qwen-code/pull/3929) / [#3930](https://github.com/QwenLM/qwen-code/pull/3930) / [#3931](https://github.com/QwenLM/qwen-code/pull/3931) remote-control stack 仍 OPEN draft / changes requested；**优先级后置**，等 TUI / channels / web / IDE 先完成 Mode B client 适配后，再重定向为 daemon HTTP/SSE facade
- ⏳ Stage 1.5 剩余主线：P0 production must-haves + daemon-side state CRUD，P1 typed event contract / bridge primitives + client adapters behind flag，P2 remote-control / Mode A revisit（详 [§06 Roadmap](./06-roadmap.md)）

## 二、6 章总览

| # | 文档 | 核心内容 |
|---|---|---|
| **01** | [Overview](./01-overview.md) | TL;DR + 2 层术语 + 架构图 + Mode B 主线 + 资源经济性 + Stage 进展 + 阅读指南 |
| **02** | [Architectural Decisions](./02-architectural-decisions.md) | 8 决策：session 共享 P1/P2 / 1 daemon = 1 workspace × N session / MCP 生命周期 / FileReadCache / Permission flow / 多 client 并发 / Mode B mainline / server-client-runtime boundary |
| **03** | [HTTP API & Protocol](./03-http-api.md) | Route table（`/workspace/*` 单 workspace 路由）+ ACP wire 4 层兼容性矩阵 + SSE + Last-Event-ID + 双向 RPC 异步化 + Capability negotiation |
| **04** | [Deployment & Client](./04-deployment-and-client.md) | Mode B client convergence + deployment shape matrix + TUI / channels / web / IDE 适配边界 + daemon-native renderer + remote-control overlay |
| **05** | [Security & Permission](./05-permission-auth.md) | Bearer + Host allowlist + 0.0.0.0 拒绝 / PR#3723 4-mode evaluatePermissionFlow / first-responder vote + per-session 隔离 / Multi-tenant = 1 daemon 1 tenant OS 进程级隔离 |
| **06** | [Roadmap & Ecosystem](./06-roadmap.md) | Timeline + Stage 1 audit + Stage 1.5 + chiga0 10 must-haves + 6 architecture findings + Stage 2 + External Reference Architecture + vs OpenCode + vs Anthropic |

## 三、阅读路径

| 路径 | 时间 | 顺序 | 适合 |
|---|---|---|---|
| 🚀 **快速理解** | ~20 min | §01 → §02 → §06 §〇/§一/§六 | 评估方案是否值得做 |
| 🔧 **MVP 实施** | ~1 h | §01 → §02 → §03 → §04 → §05 → §06 | 准备开 PR 写代码 |
| 📖 **完整设计** | ~2 h | §01 → §06 顺序 6 章读完 | 全面理解 |
| 🔒 **安全 / 多租户** | ~40 min | §05 → §06 §五 | 企业部署评估 |
| 🌐 **远端 / 多 client** | ~30 min | §04 §三/§四 + §06 §四 | 客户端体验设计 |

## 四、核心架构

### 2 层术语模型

| 层 | 数量 | 边界 | 资源 |
|---|---|---|---|
| **Daemon process** | 1（per workspace）| OS 进程 = 启动时 cwd 绑定 = 1 workspace | Express server / Bearer auth / EventBus / 内嵌单个 `qwen --acp` child |
| **Session** | N（per daemon）| `QwenAgent.sessions: Map<sessionId, Session>` 多路复用 | per-session transcript / pending tool calls / cancellation token / FileReadCache（session-private）|

详 [§02 §〇 术语](./02-architectural-decisions.md)。

### 8 个关键设计决策

| 决策 | 选择 |
|---|---|
| Session 共享语义 | 默认 P1（多 client 同 session live collaboration）+ P2（N 独立 session per daemon） |
| **状态进程模型** | **1 daemon = 1 workspace × N session multiplexed** |
| MCP 生命周期 | **当前 per-session**（`Config` / `ToolRegistry` / `McpClientManager` 随 ACP session 创建；跨 session MCP 共享需未来 pool/proxy）|
| FileReadCache | session-private（PR#3717 已实现）|
| Permission flow | 复用 PR#3723 + daemon 作为第 4 种 mode |
| 多 client 并发 | FIFO prompt 串行 + fan-out 事件 + first-responder permission vote |
| Mode A vs Mode B | **Mode B 主线**；Mode A hold，待 Mode B event/control/client contract 稳定后再评估 |
| Server/client/runtime boundary | server control plane / daemon client-protocol / adapters / runtime worker 分层；daemon-native renderer 为目标；remote-control 是 control overlay |

详 [§02](./02-architectural-decisions.md)。

### Stage 进展（at 2026-05-15）

**合入原则**：Stage 拆分必须逐步迁移。每个 PR 都要可单独合入、向后兼容、默认不破坏现有 TUI / channels / IDE / CLI 行为；新 daemon 能力通过 capability tag 暴露，client adapter 先 behind flag / 双栈测试，再单独 PR 切默认。

| Stage | 状态 | 范围 |
|---|:---:|---|
| **Stage 1 — Mode B base** | ✅ MERGED | [PR#3889](https://github.com/QwenLM/qwen-code/pull/3889)（2026-05-13）：HTTP + SSE + EventBus + prompt/cancel/model/permission 基础链路 |
| **Stage 1.5a §02** | ✅ MERGED | [PR#4113](https://github.com/QwenLM/qwen-code/pull/4113)（2026-05-15）1 daemon = 1 workspace |
| **Stage 1.5a must-haves** | ⏳ **P0** | chiga0 10 must-haves 剩 9 项 — Mode B 生产 blocker（~2 周，9 PRs 可并行）|
| **Stage 1.5c** | ⏳ **P0** | daemon-side state CRUD 8 routes — Mode B 远端 client 摆脱 thin shell（~3-5d）|
| Stage 1.5-prereq | ⏳ **P1** | chiga0 6 architecture findings — `AcpChannel` / `EventBus` / `PermissionMediator` lift（~1-2 周）|
| Stage 1.5-client adapters | 🔧 **P1 behind flag** | TUI / channels / web/debug / IDE 作为 daemon HTTP/SSE clients 试点；默认切换必须等 P0/P1 |
| **Stage 1.5b** Mode A | ⏳ **P2 推迟** | Mode A `qwen --serve` flag — [Issue #4156](https://github.com/QwenLM/qwen-code/issues/4156)；A1 [PR#4160](https://github.com/QwenLM/qwen-code/pull/4160) ✅；剩余推迟到 1.5c 后 |
| Stage 1.5-remote-control | ⏳ **P2 后置** | [#3929](https://github.com/QwenLM/qwen-code/pull/3929)/[#3930](https://github.com/QwenLM/qwen-code/pull/3930)/[#3931](https://github.com/QwenLM/qwen-code/pull/3931) 后续作为 daemon facade |
| Stage 2a-2d | ⏳ 待开 | 协议补齐（WebSocket / mDNS / OpenAPI / Prometheus / `/ext` + Reverse RPC）|
| Stage 2e | 可选 | native in-process（去 `qwen --acp` child）|

详 [§06](./06-roadmap.md)。

## 五、依赖的已合并 PR

| PR | 内容 | 对 daemon 的意义 |
|---|---|---|
| **PR#3717** ✅ | FileReadCache（session-scoped + `(dev,ino)` key）| daemon 模式下天然兼容 |
| **PR#3723** ✅ | 共享 L3→L4 permission flow | daemon 是第 4 种 ExecutionMode |
| **PR#3739** ✅ | Background agent resume + transcript-first fork resume | daemon 重启 / failover 后 session 可恢复（缺 HTTP 暴露：Stage 1.5 must-have #2）|
| **PR#3810** ✅ | FileReadCache invalidation 5 路径修复 | 长 session 正确性保障 |
| **PR#3889** ✅ | qwen serve daemon Stage 1 | 本系列设计基础 |
| **PR#4113** ✅ | 1 daemon = 1 workspace 收紧 | 移除 multi-workspace 路由，回归 ACP stdio 心智 |
| **[PR#4160](https://github.com/QwenLM/qwen-code/pull/4160)** ✅ | extract `createInMemoryChannel` helper（原 [Issue #4156](https://github.com/QwenLM/qwen-code/issues/4156) A1）| Mode A hold 后仍可作为 future in-process/native bridge primitive |

## 五-A、相关在途 PR / Issue（Mode B 视角）

| PR / Issue | 当前状态（2026-05-15）| Mode B roadmap 处理 |
|---|---|---|
| [Issue #3803](https://github.com/QwenLM/qwen-code/issues/3803) | OPEN | daemon proposal / Stage 1.5 tracker；最新 comment 将 P0/P1/P2 重排为 Mode B must-haves + state CRUD 优先，Mode A 后置 |
| [Issue #4156](https://github.com/QwenLM/qwen-code/issues/4156) | OPEN | Mode A 设计 issue，但最新结论是 **Mode A hold，核心推进 Mode B** |
| [PR#4132](https://github.com/QwenLM/qwen-code/pull/4132) | OPEN / changes requested | `/demo` debug page 可继续作为 Mode B POST+SSE client 验证面 |
| [PR#3929](https://github.com/QwenLM/qwen-code/pull/3929) | OPEN draft | remote-control foundation 后置；应等 TUI / channels / web / IDE 适配完成后改为 daemon HTTP/SSE client facade |
| [PR#3930](https://github.com/QwenLM/qwen-code/pull/3930) | OPEN draft / changes requested | worker/WebSocket 层若保留，应成为 daemon transport facade，而不是替代 HTTP/SSE + EventBus-backed event contract |
| [PR#3931](https://github.com/QwenLM/qwen-code/pull/3931) | OPEN draft / changes requested | remote-control TUI attach 后置；TUI 自身的 Mode B client adapter 更优先 |

## 六、决策与文档对应

| 上游决策点（[SDK/ACP/Daemon Deep-Dive §七](../sdk-acp-daemon-architecture-deep-dive.md#七qwen-code-引入-daemon-的工作量评估)）| 本系列章节 |
|---|---|
| Session 共享语义 | §02 §1 |
| 状态进程模型 | §02 §2 |
| MCP server 生命周期 | §02 §3 |
| FileReadCache 共享 | §02 §4 |
| Permission flow | §02 §5 + §05 |
| 多 client 并发请求 | §02 §6 + §04 §三 |
| 持久化（External Reference）| §06 §五 |
| 远端 CLI / 协作 | §04 §三/§四 |

---

> **免责声明**：本系列是 codeagents 项目的设计提案，不代表 Qwen Code 团队官方路线图。所有"工作量估算"是基于源码可见复用度的推测，实际开发可能因团队优先级、API 稳定性要求等变化。
