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

> 💡 **Implementation tracker — [Issue #4175](https://github.com/QwenLM/qwen-code/issues/4175)**（doudouOUC，2026-05-15 11:41 起 + 2026-05-17 重排）：Mode B v0.16 production-ready **31-PR rollout plan**，分 7 Wave（含新增 Wave 2.5）。本节 Stage 1.5a/c/-prereq/client adapters 等 sub-stage 都映射到 Wave 1-5；Wave 6 为 release hardening + v0.16 production-ready。详 §三·一 Wave breakdown。

### 三·一 Issue #4175 — 31-PR Wave breakdown (production-ready tracker)

按 7 Wave 拆分；critical dependency chain：

```
capability registry → DaemonSessionClient → typed events
  → daemon-stamped clientId → session-scoped permission
  → heartbeat/replay/lifecycle closure (Wave 2.5)
  → mutation-gating helper → control-plane mutation routes
  → bridge extraction → real MCP pool + full PermissionMediator
```

| Wave | 范围 | PRs | 对应 codeagents Stage |
|:---:|---|---|---|
| **1** Protocol foundation（无依赖）| baseline harness + capability registry + DaemonSessionClient skeleton + typed event schema | PR 1-4 — ✅ **4/4 MERGED**：PR 1 [#4205](https://github.com/QwenLM/qwen-code/pull/4205) + PR 2 [#4191](https://github.com/QwenLM/qwen-code/pull/4191) + PR 3 [#4201](https://github.com/QwenLM/qwen-code/pull/4201) 2026-05-16 / PR 4 [#4217](https://github.com/QwenLM/qwen-code/pull/4217) 2026-05-17 04:31 | 1.5a #9 + 1.5-prereq |
| **2** Session lifecycle + min multi-client safety | per-request sessionScope + loadSession HTTP + minimal client identity + session-scoped permission | PR 5-8 — ✅ **4/4 MERGED**：PR 5 [#4209](https://github.com/QwenLM/qwen-code/pull/4209) 2026-05-16 + PR 6 [#4222](https://github.com/QwenLM/qwen-code/pull/4222) + PR 7 [#4231](https://github.com/QwenLM/qwen-code/pull/4231) + PR 8 [#4232](https://github.com/QwenLM/qwen-code/pull/4232) 2026-05-17 | 1.5a #1/#2/#3 (minimal)/#5 |
| **2.5** Reliability + session lifecycle closure | client heartbeat + SSE replay sizing + slow-client warnings + session metadata/close-delete lifecycle | PR 9-11 — ✅ **3/3 MERGED**：PR 9 [#4235](https://github.com/QwenLM/qwen-code/pull/4235) + PR 10 [#4237](https://github.com/QwenLM/qwen-code/pull/4237) + PR 11 [#4240](https://github.com/QwenLM/qwen-code/pull/4240) 2026-05-17 | 1.5a #4 reliability + #2 lifecycle closure |
| **3** Read-only control plane + diagnostics | read-only status routes + preflight/env diagnostics + MCP guardrails (measurement, not full pool) | PR 12-14 — ✅ **3/3 MERGED**：PR 12 [#4241](https://github.com/QwenLM/qwen-code/pull/4241) + PR 13 [#4251](https://github.com/QwenLM/qwen-code/pull/4251) 2026-05-17 + PR 14 [#4247](https://github.com/QwenLM/qwen-code/pull/4247) 2026-05-18；🔧 follow-up **PR 14b** [#4271](https://github.com/QwenLM/qwen-code/pull/4271) MCP guardrail push events + hysteresis OPEN | 1.5c read-only + chiga0 diagnostics |
| **4** Auth-gated mutation/control routes | **mutation gating helper** + memory/agents CRUD + approval/tools/init/MCP-restart + FileSystemService 边界 + safe file read + file write/edit + auth device-flow | PR 15-21 — ✅ PR 15/16/18/19 MERGED + 🔧 PR 17 [#4282](https://github.com/QwenLM/qwen-code/pull/4282) + PR 20 [#4280](https://github.com/QwenLM/qwen-code/pull/4280) + PR 21 [#4255](https://github.com/QwenLM/qwen-code/pull/4255) OPEN (doudouOUC 同时 3 PR 在飞) | 1.5c CRUD + 文件 routes |
| **5** Architecture extraction + output sinks + full multi-client security | bridge primitives extraction + real MCP shared pool (config-hash keyed) + pairing revocation + full PermissionMediator + 独立 output sinks + flag-gated client adapters | PR 22-26 | 1.5-prereq full + 1.5a #3 full + adapter migration |
| **6** Release hardening + v0.16 | alpha release docs + npm alpha publish + **production token defaults** (`~/.qwen/serve/instances/<host>-<port>-<workspaceHash>/token`) + deployment refs + v0.16 release | PR 27-31 | Stage 2 + release |

### Wave 1 — Protocol foundation（无依赖，可立即开始）

| PR | 内容 | 状态 |
|---|---|:---:|
| **PR 1** `test/perf: daemon baseline harness` | RSS curve + same-workspace attach latency + prompt p50/p99 + MCP child count + SSE replay/backpressure basics — **measure before optimize** | ✅ **MERGED 2026-05-16 16:41** [PR#4205](https://github.com/QwenLM/qwen-code/pull/4205) (doudouOUC, +1343 LOC 全在 `integration-tests/`，0 production code；4 Critical 修后 wenshao 本地 70.7s 跑过 20 iteration；首份 `baseline-stage-1.json` macOS arm64：RSS 223.5 MB / `growthPerSessionMB ≈ 0` / attach 1-3 ms / MCP 4 children constant under default single-scope) |
| **PR 2** `feat(serve): capability registry + protocol versions` | 替换 hard-coded `STAGE1_FEATURES` 为 additive registry（新 `capabilities.ts` +52 LOC，每 feature `{ since: 'v1' }` descriptor，留 `deprecated` / `requires` 扩展位）+ `/capabilities.protocolVersions: { current, supported }`；`STAGE1_FEATURES` 保留为 `@deprecated` alias；SDK 加 `DaemonProtocolVersions` type；测试验证 backward compat（accepts old v1 envelopes without `protocolVersions`）；关闭 chiga0 finding 5 FIXME | ✅ **MERGED 2026-05-16 10:07** [PR#4191](https://github.com/QwenLM/qwen-code/pull/4191) (doudouOUC, `[codex]` 前缀, +170/-39, 84+43 tests passing) |
| **PR 3** `feat(sdk): DaemonSessionClient skeleton` | SDK helper over `DaemonClient`：create/attach/prompt/events/cancel/model；tracks `Last-Event-ID` replay state；给 TUI/channels/web/IDE adapters 共用（依赖 PR 2）| ✅ **MERGED 2026-05-16 17:01** [PR#4201](https://github.com/QwenLM/qwen-code/pull/4201) (chiga0；前身 [PR#4195](https://github.com/QwenLM/qwen-code/pull/4195) CLOSED；v2 经 review 补 AbortSignal 转发 / event-without-id guard / error path 三轴 45 cases；wenshao 本地 verify 53 tests + typecheck + build clean)；✅ follow-up [PR#4225](https://github.com/QwenLM/qwen-code/pull/4225) **MERGED 2026-05-17 07:05** (chiga0, 3h11m open→merge, +323/-18 测试 141→205；**多模型 /review pipeline**：DeepSeek-v4-pro + claude-opus-4-7 + wenshao 4 轮 review；初稿提的 eager guard 设计被 wenshao 否决—abandoned generator 永久占 slot 风险——**chiga0 让步改回 lazy**+ 加 `cursor monotonicity via Math.max`（同 PR#4217 reducer hardening pattern 跨 PR 复用）+ abort-signal propagation + SSE `event.id` validation + test 钉 lazy-guard 行为防 regression) |
| **PR 4** `feat(protocol): typed daemon event schema v1` | SDK-layer discriminated union + reducer skeleton；保留 raw `DaemonEvent { data: unknown }` 兼容（依赖 PR 2, 3）| ✅ **MERGED 2026-05-17 04:31** [PR#4217](https://github.com/QwenLM/qwen-code/pull/4217) (chiga0, squashed `ab88f6f1`；**5 轮 review / 2 轮自我修复**：① 4 Critical 修—bracket notation 22 处 / `client_evicted` reducer 不设 `alive: false` / `client_evicted`+`session_update` 零测试 / `isPermissionRequestData` 不检查 required `toolCall`；② 5 项 reducer hardening invariants—`lastEventId` 单调推进抗回退 / `pendingPermissions` cap 64/session + dropped 诊断计数 / `permission_resolved` 未匹配 requestId 诊断计数 + cancelled outcome / `toolCall` 校验收紧 + finite number / reducer 存储时复制 data 抗引用共享；wenshao 本地 20/20 SDK schema + DaemonSessionClient tests passing)；⚠️ 同 PR 平行的 [PR#4226](https://github.com/QwenLM/qwen-code/pull/4226) (doudouOUC, 2026-05-17 03:58, +1398/-18, 1.8x 测试比；开 4 分钟后 PR#4217 即 MERGED) 重复，**待 close 或拆 SessionState reducer 部分作 Wave 5 PR 25 提前** |

#### Bonus: 提前到 Wave 1 阶段的 client adapter spikes

> chiga0 把原 Wave 5 client adapter 工作的 design draft 升级为 **implementation spike**（design + code 同 PR，避免脱节）。这些 spike 可以与 Wave 1 PRs 并行 review，但默认 off，等 Wave 2/3 blockers 落地后才能切换默认。

| PR | 内容 | 状态 |
|---|---|:---:|
| [PR#4202](https://github.com/QwenLM/qwen-code/pull/4202) `feat(tui): add daemon adapter spike` | `DaemonTuiAdapter` reduce daemon SSE → TUI updates；forward prompt/cancel/model/permission；default-off layer before touching Ink runtime（最终 +1970）| ✅ **MERGED 2026-05-18 03:22** (chiga0) |
| [PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) `feat(channel): add daemon bridge spike` | `DaemonChannelBridge` in `@qwen-code/channel-base`：bind daemon session + consume SSE + route permission/cancel/model；server-side BFF only（最终 +2012）| ✅ **MERGED 2026-05-18 02:21** (chiga0) |
| [PR#4199](https://github.com/QwenLM/qwen-code/pull/4199) `feat(ide): add daemon connection spike` | IDE daemon transport behind flag（最终 +1676）| ✅ **MERGED 2026-05-18 02:38** (chiga0) |

#### Stage 1 / 2 adapter wire-up + experimental flag-gated (chiga0, 2026-05-18)

> chiga0 把 adapter migration 工作进一步拆 **3 adapter × 3 stage = 9 PR**。Stage 0 spike 是 protocol primitive（已 ✅ 3/3），Stage 1 是 developer harness（reviewer 手验 + 不替换 production path），Stage 2 是 experimental flag-gated（真接入 production 渲染链，behind `--experimental-daemon-tui` / `qwen-code.experimentalDaemonIde` flag）。

| Stage | PR | 内容 | 状态 |
|---|---|---|---|
| **Stage 1 TUI** | [PR#4260](https://github.com/QwenLM/qwen-code/pull/4260) | 新 CLI subcommand `qwen daemon-tui --daemon-url` + harness 测 prompt/cancel/model/permission（+248）| ❌ **CLOSED 2026-05-18 06:59**（chiga0 主动；wenshao 抓 240-line command-layer 测试缺口后，Stage 2 PR#4266 真接入 Ink TUI 已覆盖更彻底）|
| **Stage 1 channel** | [PR#4261](https://github.com/QwenLM/qwen-code/pull/4261) | `qwen channel start --daemon-url` flag + env vars；channel 改 depend on 结构 `ChannelBridge` interface，可注入 `AcpBridge`（默认）或 `DaemonChannelBridge`（opt-in）（+159/-43）| 🔧 OPEN draft + CHANGES_REQUESTED（channel 无 Stage 2 PR，**仅剩此 Stage 1 在飞**）|
| **Stage 1 IDE** | [PR#4263](https://github.com/QwenLM/qwen-code/pull/4263) | VS Code 新命令 `Qwen Code: Daemon Smoke Test`：stream daemon session 文本到 output channel + permission quickpick（+165）| ❌ **CLOSED 2026-05-18 06:59**（chiga0 主动；wenshao 抓 `outputChannel` JSDoc dep 不一致后，Stage 2 PR#4267 真注入 webview 覆盖）|
| **Stage 2 TUI** | [PR#4266](https://github.com/QwenLM/qwen-code/pull/4266) | CLI flag `--experimental-daemon-tui` —— **真接入 production Ink TUI**：history/pending-item components render daemon SSE（+664/-16）| 🔧 OPEN draft |
| **Stage 2 IDE** | [PR#4267](https://github.com/QwenLM/qwen-code/pull/4267) | VS Code config `qwen-code.experimentalDaemonIde` —— **真注入 daemon-backed ACP-compatible connection 到 webview**，可替代 child-process ACP spawn（+230/-5）| 🔧 OPEN draft + CHANGES_REQUESTED |
| **Stage 2 channel** | ⏳ 待开 | (channel stage 2 尚未开 PR) | ⏳ |

chiga0 设计哲学（每 PR 反复出现）：**existing default path remains unchanged + opt-in only + draft for validation, not final replacement**。Wave 5 PR 26 提前覆盖 8/9 阶段。

详 [§04 §一 Channel / Web BFF 适配安全边界](./04-deployment-and-client.md#channel--web-bff-适配安全边界pr4203-摘要)。

### Wave 2 — Session lifecycle + minimum multi-client safety

| PR | 内容 | 状态 |
|---|---|:---:|
| **PR 5** per-request `sessionScope` | `POST /session` 接受 `{ sessionScope: 'single' \| 'thread' }`；默认 `single`；无效值 `400 invalid_session_scope`；新 capability tag `session_scope_override` 暴露在 `/capabilities.features`；review 发现并修 mixed-scope leak（thread-first 后省略-scope 调用 attach 到隔离 session 的 bug）；同时解锁 PR 1 baseline harness 在 thread mode 下诚实测量 per-session cost（依赖 PR 2）| ✅ **MERGED 2026-05-16 15:54** [PR#4209](https://github.com/QwenLM/qwen-code/pull/4209) (doudouOUC, +512/-20, 4h26m open→merge, 9 tests + DeepSeek-v4-pro /review APPROVED)；✅ follow-up [PR#4214](https://github.com/QwenLM/qwen-code/pull/4214) **MERGED 17:51** (doudouOUC, +14/-11, 1h23m open→merge) 校准 integration-test `caps.features` 9→10 + user-doc 删除过时 blocker；建立 capability registry **三套来源 lockstep** 模式：生产 `SERVE_CAPABILITY_REGISTRY` ↔ unit `EXPECTED_STAGE1_FEATURES` ↔ integration `caps.features` toEqual —— 未来加 capability 必须三处同步 |
| **PR 6** HTTP load/resume session | `POST /session/:id/load` + `/resume`；SDK methods；保留 ACP direct 行为；**replay buffer race solve**（replay frame 先 buffer 进 SSE ring 再 register session，避免重连缺数据）；3 类 race guard（missing session / conflicting load+resume / unrelated concurrent restore fail）；conservative concurrency（load racing behind in-flight resume → reject with retry guidance）；**symmetric coalesce guard**（原 in-flight 只 guard load-on-resume，因 `resume()` seeds `lastEventId: 0` 与 load 语义截然不同必须双向，修法 `if (action !== inFlight.action)`）；新 capability tag `session_load_resume`（依赖 PR 3, 5）| ✅ **MERGED 2026-05-17 04:58** [PR#4222](https://github.com/QwenLM/qwen-code/pull/4222) (doudouOUC `[codex]`, 3h17m open→merge, **5 轮 review**；体量 review 期间几乎翻倍 +1091/-35 13 文件 → **+2078/-51 16 文件**；wenshao 03:33 第一次 APPROVE 后 11 分钟二次 /review 发现 asymmetric coalesce guard + 另 1 Critical 翻回 CHANGES_REQUESTED；commit `db55b1c8b` 修后 04:55 最终 APPROVE) |
| **PR 7** **minimal** daemon-stamped client identity | daemon assigns/stamps `clientId`；emitted events 使用 trusted `originatorClientId`；无 revocation；**header-based echo (`X-Qwen-Client-Id`) only**（防 client 自报伪造）；state-changing routes 拒绝 unknown clientId；live-session scoped（daemon 重启 / session 死 = id 丢失）；新 capability tag `client_identity`；adapter 不切换（只 ship primitive）（依赖 PR 3, 4）| ✅ **MERGED 2026-05-17 08:19** [PR#4231](https://github.com/QwenLM/qwen-code/pull/4231) (chiga0, 1h23m open→merge, 最终 +910/-79；wenshao **9 parallel review agents** 覆盖 correctness/security/code quality/performance/test coverage + 3 audit personas；commit `52295980f4` 修 1 Critical（`InvalidClientIdError` 走 `sendBridgeError` 翻 400 而非 500，避免 client 输入错误冒到 500 internal error）+ 6/7 其他 concern；clientId 用 `randomUUID()` + `client_` 前缀 122 bits entropy unguessable；未来 follow-up：`clientIds` shrink path + `DaemonSessionClient` reconnect-identity gap) |
| **PR 8** session-scoped permission route | `POST /session/:id/permission/:requestId`；保留 legacy `POST /permission/:requestId`；加 `permission_already_resolved` event；**bounded in-memory record of recent resolutions**（同 PR#4217 "pendingPermissions cap 64/session" 跨 PR pattern 复用）；新 capability tag `session_permission_vote`；SDK 新方法 `respondToSessionPermission()` 与 legacy `respondToPermission()` 共存（依赖 PR 7）| ✅ **MERGED 2026-05-17 09:48** [PR#4232](https://github.com/QwenLM/qwen-code/pull/4232) (chiga0, 2h44m open→merge, 最终 +801/-30；rebase 到 main 后 single-commit `4eae97a33b`；wenshao 4 轮 review 抓 3 项：① barrel re-export 新 type `DaemonPermissionAlreadyResolvedEvent` + `Data` ② 抽 `parsePermissionOutcome(req, res)` 共享 helper 去掉 scoped+legacy 两 route 的 `safeBody`+`isValidOutcome`+catch block 重复 ③ input validation 测试补全；5 test scenarios：accepted / already-resolved / malformed option / wrong-session / unknown-session) |

### Wave 2.5 — Reliability + session lifecycle closure

> 来自 Issue #4175 的 P0 contract gap：在 broad mutation/control-plane 工作之前必须先 close session 重连可信度 + 慢 client 信号 + 显式 close/delete semantics。

| PR | 内容 | 状态 |
|---|---|:---:|
| **PR 9** client heartbeat | `POST /session/:id/heartbeat` empty body → `200 { sessionId, clientId?, lastSeenAt }`（Date.now epoch ms）/ `404` unknown session / `400 invalid_client_id`；optional `X-Qwen-Client-Id` header；Bridge 新增 `recordHeartbeat()` + `getHeartbeatState()` snapshot accessor（**HTTP state route 推迟到 Wave 3 PR 12**）；`SessionEntry` 加 `sessionLastSeenAt?: number` + `clientLastSeenAt: Map<string, number>`；**4 安全不变式**：① pre-validation BEFORE bump 防 random-id 时间戳 spam ② `unregisterClient` drop per-client entry 防 long-lived daemon 累积 stale id（即 Wave 5 PR 24 要 plug 的 leak）③ snapshot Map ReadonlyMap + copy-on-read ④ anonymous heartbeat 只 bump per-session 水位；新 capability tag `client_heartbeat`；feeds Wave 3 PR 12 diagnostics + Wave 5 PR 24 revocation policy（依赖 PR 7）| ✅ **MERGED 2026-05-17 10:57** [PR#4235](https://github.com/QwenLM/qwen-code/pull/4235) (doudouOUC, 2h00m open→merge, **首轮一把过 0 CHANGES_REQUESTED**——daemon 项目首例；+581/-2 14 文件, **测试 / 生产 ≈ 1.7x**, 14 test cases；wenshao quote："all **3471 serve/SDK tests pass** ... security model is sound: clientId validation runs before any timestamp update, bearer-auth gates all routes, error shapes follow existing `sendBridgeError`"；把 chiga0 5 轮 review 学到的 cap pattern + pre-validation + lockstep 全 internalize 进首版) |
| **PR 10** SSE replay sizing + `slow_client_warning` backpressure | `DEFAULT_RING_SIZE` 4000 → **8000**（对齐 #3803 §02 chatty session target）；`--event-ring-size <n>` CLI flag fail-CLOSED 校验；**`slow_client_warning` SSE frame** at queue 75% full（hysteresis re-arm 37.5% 防 flap）+ 携带 `{queueSize, maxQueued, lastEventId}`；`?maxQueued=N` query 范围 `[16, 2048]` 默认 256，越界 `400 invalid_max_queued` **before opening SSE**（避 EventSource auto-reconnect）；新 capability tag `slow_client_warning`；SDK 加 typed `DaemonSlowClientWarningEvent` + `slowClientWarningCount` 计数（**non-terminal**，`alive` 保持）（依赖 PR 1, 4）| ✅ **MERGED 2026-05-17 11:30** [PR#4237](https://github.com/QwenLM/qwen-code/pull/4237) (doudouOUC, 2h19m open→merge, **3 轮 review** (0 Critical, 3+5 Suggestion)；最终 +893/-81 18 文件；wenshao 高赞 **`BoundedAsyncQueue.liveCount` refactor** 是 thoughtful pre-emptive fix——原 `forcedInBuf` counter 在 `slow_client_warning` mid-stream force-push 下会挂，doudouOUC 自己实现时意识到 invariant 破裂提前重构（不是 reviewer 抓出来的）；review 期间修：5 处 docs "default 4000" → "8000" 文案 / `eventRingSize` forwarding in `createServeApp` / `BoundedAsyncQueue.forcedInBuf` invariant；⚠️ 内存翻倍：default ring 4000 → 8000 在 64 subs × 8000 frames × 500 B ≈ ~256 MB worst-case；operators 紧 budget 可 pin `--event-ring-size 4000`) |
| **PR 11** session metadata + close/delete lifecycle | `DELETE /session/:id` force-close（即使其他 client 还 attached，cancel active prompt + resolve pending permissions as cancelled + emit `session_closed` event）+ `PATCH /session/:id/metadata` 更新 `displayName` (max 256 chars) + `GET /workspace/:id/sessions` 加 `createdAt`/`displayName`/`clientCount`/`hasActivePrompt`；新 `session_closed` (terminal) + `session_metadata_updated` events；新 capability tags `session_close` + `session_metadata`；双 close 幂等（SDK 把 404 翻译为 idempotent success）（依赖 PR 6, 7）| ✅ **MERGED 2026-05-17 12:42** [PR#4240](https://github.com/QwenLM/qwen-code/pull/4240) (doudouOUC, 2h16m, 4 轮 review；最终 +1175/-35；headRef `worktree-delightful-cooking-goose`——Claude Code worktree 生成 fingerprint；**1 Critical typecheck 修**（`BridgeSessionSummary` 新字段 `createdAt`/`clientCount`/`hasActivePrompt` mock 同步）+ **ordering 修**（`events.close()` 必须 BEFORE `connection.cancel()` in `closeSession`——否则 SSE subscriber 收 `session_closed` 之前流就断）；wenshao 高赞 "terminal-event upgrade + pending-permission cancellation test coverage exactly the contract I'd worry about most") |

### Wave 3 — Read-only control plane + diagnostics

| PR | 内容 | 状态 |
|---|---|:---:|
| **PR 12** read-only status routes | `GET /workspace/mcp` + `/skills` + `/providers` + `/session/:id/context` + `/session/:id/supported-commands`；payload 必须 protocol-versioned + SDK 内 typed；**关键不变式**：workspace routes **不 spawn ACP** 即使 polled（idle workspace 返 `initialized: false`），避免 monitoring 保活 daemon；session routes 要求 live session（依赖 PR 2, 4）| ✅ **MERGED 2026-05-17 13:37** [PR#4241](https://github.com/QwenLM/qwen-code/pull/4241) (doudouOUC, 3h02m，最终 +2363/-64 review +251 LOC；wenshao **review pipeline 升级**：gpt-5.5 /review + **mimo-v2-5-pro 9 parallel agents**（新加 **attacker simulation + 3AM oncall** personas）+ 增量审 + force-push hardening commit `6244c894`；cli vitest 368 → **396 tests passing**（+28）+ sdk vitest 91/91；最终修复：read-only session routes 也 forward `clientId` for **audit symmetry**——把 PR#4231 invariant 扩到 read 路径；Session.ts unused AbortController 删；⚠️ integration test mirror 漏校准 5 features（+ PR#4237 漏 `slow_client_warning`）—— release CI 跑挂，由 follow-up [PR#4245](https://github.com/QwenLM/qwen-code/pull/4245) 修，**该 mirror pattern 第三次 drift**) |
| **PR 13** preflight + env diagnostics routes | `GET /workspace/preflight` + `GET /workspace/env`（**不是** 一个 generic diagnostics blob）；包含 daemon-locality notes + actionable `errorKind`：`missing_binary` / `blocked_egress` / `auth_env_error` / `init_timeout` / `protocol_error` / `missing_file` / `parse_error`。**Constraint**：所有 diagnostic payload across PR 12 + 13 + 14 共享同一 cell shape `{ kind, status, error?, errorKind?, hint? }`，SDK reducer 一套渲染所有 3 routes（否则 3 schemas 会 drift）（依赖 PR 12；详 [§04 §五 Runtime locality](./04-deployment-and-client.md#五runtime-locality--environment-contract)）| ✅ **MERGED 2026-05-17 23:29** [PR#4251](https://github.com/QwenLM/qwen-code/pull/4251) (doudouOUC, 7h40m, 7 轮 review；最终 +2577/-127 (review 期间 +684/-98)；**第六次 drift 被 wenshao [Critical] 在 PR review 中抓**——doudouOUC "故意 batch fix" 策略破产，必须 in-PR 修；wenshao 自己实测 `.toEqual()` 严格比对会 fail，不再依赖 release CI；4 轮 fix 内容：① **`execSync` → `execFile` migration** 安全防 shell injection（也修 Windows CI 挂）② `safeCheck` errorKind ③ proxy redaction `safeProxyValue` **3-stage parse** (URL → `http://`-prepend → regex scrub → `<unparseable>` final fallback + 4 unit tests: scheme-less/authority-only/unparseable/lowercase variants) ④ `validateAuthMethod` mutation P1 ⑤ integration test mirror 加 `workspace_env` + `workspace_preflight` ⑥ **live ACP + ACP failure fallback tests**（之前只测 idle path）⑦ **174-line delta** of 3 structural fix from low-confidence items (ACP_PREFLIGHT_KINDS docstring drift 等)；2 route + 第一个 land **closed `errorKind` 7-value taxonomy**（PR 14 复用）+ 5 strict invariants 含 build-time grep + 6 commit 拆分；639/639 tests passed) |
| **PR 14** MCP resource guardrails | measurement-backed：MCP child/session budget + warnings 或 controlled refusal（**不是** full shared pool；依赖 PR 1, 12）| ✅ **MERGED 2026-05-18 04:07** [PR#4247](https://github.com/QwenLM/qwen-code/pull/4247) (doudouOUC, **13h09m daemon 项目史上最艰难一合**；9+ 轮 review **11 [Critical]**——超越所有先前 PR 的 review 强度；最终 +2867/-31（review 翻 2.4x，初版 +1188/-13）；**4 个不同 LLM model 跑 review 形成 audit pipeline**：mimo-v2.5-pro / DeepSeek-v4-pro / glm-5.1 / 9 parallel agents + 3 reverse-audit rounds；R2 短暂 APPROVED 但 R3 翻 CHANGES_REQUESTED 触发后续 8 轮；wenshao 中文 R10 quote: "前次 16:18 APPROVED 落后 5 个 commit；我陆续追了 11 条 [Critical]"；**核心架构修复**：3 个 spawn path（bulk `discoverAllMcpTools` / per-server `discoverMcpToolsForServerInternal` / lazy `readResource`）现在 **`weReserved`-driven 清理完全对称**——每个 catch 块都是 `if (weReservedSlot) { try { await client.disconnect() } catch {} reservedSlots.delete(serverName) }`；3 path budget gating 全补 (C1)；zombie slot leak 全修 (C2/C3)；transport leak `discoverAllMcpTools` catch (R7-R8)；`runWithDiscoveryTimeout` timeout handler 加 `reservedSlots.delete`；stale global `discoveryState()` 改 instance-bound；197/197 tests passing；体量/review 轮次/Critical 数全 daemon 项目最高纪录；引 claude-code `filterMcpServersByPolicy` + `--mcp-*` flag 命名 + opencode `heap.ts` hysteresis primitive + claude-code telemetry 4 prior art；v2 **PR 14b** [#4271](https://github.com/QwenLM/qwen-code/pull/4271) deferred typed SSE push events `mcp_budget_warning` + `mcp_child_refused_batch` —— **🔧 OPEN 2026-05-18 07:16** (+1824/-16 13 文件)：snapshot 上叠 real-time push channel，2 typed event + hysteresis state machine **at manager level** mirrors PR 10 `slow_client_warning` per-subscriber backlog；coalesced refused batch + length-1 lazy spawn fallback；`evaluateBudgetState()` + `emitRefusedBatchIfAny()` + `pendingRefusalNames` queue distinct from snapshot `lastRefusedServerNames` 保 **PR 14 contract preserved** v1→v2 干净 layer；`setOnBudgetEvent(cb)` 在 `loadCliConfig` 后 + discovery start 前注册；新 ACP transport `qwen/notify/session/mcp-budget-event`；**✅ 主动包 integration test +61**——doudouOUC 真正落实 PR-internal lockstep) |

### Wave 4 — Auth-gated mutation/control routes

> ⚠️ 所有 mutation routes 必须用 **PR 15 中心化 mutation gate**，不能 per-route open-code auth check。

| PR | 内容 | 状态 |
|---|---|:---:|
| **PR 15** **mutation gating helper** + `--require-auth` | 中心化 `createMutationGate({ tokenConfigured, requireAuth })` helper for state-changing routes；4-cell behavior matrix（`requireAuth: true` 或 token 配 → passthrough；no-token loopback dev + `strict: false` → passthrough；`strict: true` → `401 token_required`）；`--require-auth` CLI flag boot-loud refuse-no-token + 关闭 `/health` 豁免；**conditional `require_auth` capability tag**（仅 operator opt-in 才 emit）+ 新 `CONDITIONAL_SERVE_FEATURES` registry primitive 为未来 per-deployment toggle 建 shape；Wave 1-2 mutation routes opt-in non-strict 作 centralization marker `grep gateMutation`（依赖 PR 7）| ✅ **MERGED 2026-05-17 12:10** [PR#4236](https://github.com/QwenLM/qwen-code/pull/4236) (doudouOUC, 3h06m, 2-3 轮 review **无 Critical** 全 nit suggestion；最终 +620/-24, 271/271 serve tests passing across 5 files；wenshao **真起 `qwen serve` 端到端 verify 4-cell behavior matrix 各 1 次**（review quality 新基线）；解锁 Wave 4 PR 16-21 全 6 个) |
| **PR 16** memory + agents CRUD | `GET/POST /workspace/memory` + `/agents` + agent-type scoped `GET/POST/DELETE /workspace/agents/:agentType`；mutation paths gated + audited（依赖 PR 15, 12）| ✅ **MERGED 2026-05-18 06:27** [PR#4249](https://github.com/QwenLM/qwen-code/pull/4249) (doudouOUC, **15h20m 创新 daemon 项目最长 lifetime** 破 PR#4250 13h55m；**11 rounds review + 6 个 LLM model**：Copilot / gpt-5.5 / DeepSeek-v4-pro / glm-5.1 / qwen-latest / github-advanced-security + wenshao R1-R7；最终 +5318/-8 23 文件（review 翻 +2364 LOC，初版 +2954/-3）；wenshao R11 quote: "**fold-in cascade 2a → 2j has addressed every critical and high-impact finding**"——10 sub-fix iteration 是 daemon 项目最系统化修复 trail；7 routes + 2 cap tag (`workspace_memory`/`workspace_agents`) + 2 typed event (`memory_changed`/`agent_changed`) workspace-level fan-out via `bridge.publishWorkspaceEvent`；3 scope decision: 静态 `QWEN.md` only (auto-memory deferred PR 16.5) / agents POST split create+update 409 `agent_already_exists` / persistent audit log deferred PR 24；工程亮点：① CRUD-scoped `Config` Proxy stub fail-loud ② whitespace-only-append suppression 防 no-op POST 污染 ③ workspace-level fan-out + `knownClientIds()` snapshot) — 此前 PR open 时 OPEN 状态保留如下供参照 (doudouOUC, 2026-05-17 15:06, **+2954/-3 17 文件 项目第二大 PR**；7 routes + 2 capability tag `workspace_memory` + `workspace_agents` + 2 typed event `memory_changed`/`agent_changed` workspace-level fan-out via `bridge.publishWorkspaceEvent` + `knownClientIds()`；3 scope decision: **静态 `QWEN.md` only**（auto-memory 4-type taxonomy + MEMORY.md + extract/dream deferred PR 16.5）/ agents POST split create-only on `/workspace/agents` + update on `:agentType`（409 `agent_already_exists`，match `SubagentManager.createSubagent` vs `updateSubagent`）/ audit stamp `originatorClientId` on emitted events only（persistent audit ring deferred PR 24）；**工程亮点**：① CRUD-scoped `Config` Proxy stub 只暴露 `getSdkMode`/`getProjectRoot`/`getActiveExtensions`，其他方法 throw 立即 crash —— fail-loud 防 future refactor 在 CRUD path 加方法 daemon silently incorrect ② **whitespace-only-append suppression** in `writeContextFile.ts` 防 no-op POST bump mtime / fan out 误导 `memory_changed`（返 `{ changed: boolean }` flag）③ `bridge.publishWorkspaceEvent` per-entry catch + `writeServeDebugLine`；**PR open 前自跑 2 specialist agents** (code-review + silent-failure-hunter) **5 项 high-impact pre-fix**——review pipeline 推前到 PR open 前；693 tests green (348/348 serve + 10/10 writeContextFile + 335/335 SDK)，30+ new `it` blocks 覆盖 success/strict-deny/4xx/event-stamp/fan-out/SDK round-trip；⚠️ **第五次 drift 风险**：未含 `integration-tests/cli/qwen-serve-routes.test.ts`，doudouOUC 故意 batch fix 等多 cap 合后一次 follow-up 校准) |
| **PR 17** approval + tools + init + MCP restart controls | `POST /session/:id/approval-mode` + `/workspace/tools/:name/enable` + `/workspace/init` + `/workspace/mcp/:server/restart`（依赖 PR 15, 12, 14）| 🔧 **OPEN [PR#4282](https://github.com/QwenLM/qwen-code/pull/4282)** (doudouOUC, 2026-05-18 10:06, +2746/-10 26 文件；4 strict-gated mutation route：`POST /session/:id/approval-mode` 切 (`plan`/`default`/`auto-edit`/`yolo`) + optional `persist: true` 同时写 workspace settings / `POST /workspace/tools/:name/enable` toggle `tools.disabled` (skip-register distinct from `permissions.deny`) / `POST /workspace/init` **故意纯机械** scaffold 空 `QWEN.md` 不调 model 保 transparency 让 client 显式发 prompt / `POST /workspace/mcp/:server/restart` + PR 14 v1 budget pre-check；全 strict-gated by PR 15 + `X-Qwen-Client-Id` audit (PR 7) + `originatorClientId`-stamped SSE event；新 core `TrustGateError` typed exception **cross-bundle handling**——route→bridge→ACP child 三层 bundle typed narrow 一致；wenshao 10:32 评 "structure / layering / capability advertising / `TrustGateError` cross-bundle handling 全 well thought out" 但 **1 CI blocker + 3 correctness issues**→10:46 CHANGES_REQUESTED) |
| **PR 18** `refactor(serve): add FileSystemService boundary` | 引入 per-request file-system service 抽象；统一 workspace canonicalization / symlink policy / ignore/trust behavior / size/binary limits / audit hooks —— 必须在 file routes 暴露之前 land（依赖 PR 12, 15）| ✅ **MERGED 2026-05-18 05:14** [PR#4250](https://github.com/QwenLM/qwen-code/pull/4250) (doudouOUC, **13h55m 创新 daemon 项目最长 lifetime** 破 PR#4247 13h09m；**10 rounds 70 review threads 全 resolved**；最终 +4753/-68（review +1483 LOC）；wenshao R10 quote: "**Ten rounds of review iteration in, all 70 threads resolved, no Critical or Suggestion left dangling**"；review 抓出 13+ Critical + ~50+ Suggestion：① `import type` value mismatches 引 ReferenceError CI fail ② **TOCTOU symlink substitution** in `readText` ③ **`writeText` 完全无 TOCTOU 保护** ④ `edit()` read-modify-write race window ⑤ **`safeUtf8Truncate` off-by-one** 读 `buf[end-1]` 而非 `buf[end]` corrupt UTF-8 ⑥ OOM gate gap in `readBytes` 不依赖 caller maxBytes ⑦ dangling+multi-hop symlink bypass ⑧ glob cwd bypass + error classification ⑨ `edit()` bypasses encoding/BOM ⑩ `hasSuspiciousPathPattern` regex gaps + FP ⑪ `enforceReadBytesSize` hard-cap clamp ⑫ `stat` ENOENT tolerance ⑬ audit `message` privacy gating；**`assertInodeStableAfterRead` invariant 贯穿 readText/readBytes/edit**——typical chokepoint refactor 范本；**解锁 Wave 4 PR 19 safe file read + PR 20 file write/edit**) — 此前 PR open 时 OPEN 状态保留如下供参照 (doudouOUC, 2026-05-17 15:19, **+3270/-68 16 文件 daemon 项目史上最大 PR**（除 Stage 1）；**pure refactor** 无 new route 无 capability tag；新模块 `packages/cli/src/serve/fs/` 含 `paths.ts`(+353)/`errors.ts`(+141)/`policy.ts`(+214)/`audit.ts`(+218)/`workspaceFileSystem.ts`(+596)+10-case contract test；**8 security/correctness 防线**：① suspicious path pattern reject (NTFS ADS / UNC / DOS device names / 三连续 dots) ② ENOTDIR explicit reject → `parse_error` ③ chain-aware realpath + ENOENT-tolerant ancestor walk ④ errno auto-categorize（EACCES → `permission_denied` / ELOOP → `symlink_escape` / ENOTDIR/EISDIR → `parse_error`）⑤ `recordAndWrap` always emit audit + always wrap（防 raw errnos escape）⑥ `readText` stats first 拒 > MAX_READ_BYTES 256 KiB BEFORE 走 slurping core 防 OOM ⑦ `glob` realpath-checks each hit + filtered escapes 报 single aggregated `fs.denied` (with dropped count) ⑧ `Intent` exhaustive `never` guard 未来 intent 新加 → 编译错误 at trust gate；**audit 隐私**：SHA-256-hashed paths 默认 + `QWEN_AUDIT_RAW_PATHS=1` opt-in passthrough + discriminator `kind`；**`trusted: false` 默认 factory** 防 forget-inject `fsFactory` silently allow writes；**3 specialist agent pre-run 5 P0 + 1 P1 pre-fix**——review pipeline 推前升到 3 agent；引 **claude-code `permissions/filesystem.ts`** (chain-aware symlink walk + Windows attack patterns) + **opencode `File.Service` shape** 2 prior art；**测试 / 生产 ≈ 98%** (~1613/1652 LOC, 101 unit + 10-case contract, 411/411 serve passing)；7 项 P2 deferred (workspace deleted post-boot / `FsKind` 复用 / `RequestContext` compose / `FsError` status mapping / Windows cross-drive / contract corpus expansion / `unsafeAsResolved()` helper)；**不触发 mirror drift** (pure refactor 无新 cap)) |
| **PR 19** safe workspace file **read** routes | read/list/stat only；经 `FileSystemService` 路由；canonicalize paths + workspace boundary + size/binary limits + symlink policy + actionable errors（依赖 PR 18）| ✅ **MERGED 2026-05-18 08:17** [PR#4269](https://github.com/QwenLM/qwen-code/pull/4269) (doudouOUC, **1h54m 极短 lifetime**——PR 18 chokepoint 红利显化；最终 +1454/-8 10 文件；wenshao 中文 APPROVED quote: "本地实测通过(525/525 tests + **安全边界全部正确拒绝** + **审计串联确认**)"；PR-internal lockstep 已 internalize) — 此前 PR open 时 OPEN 状态保留如下供参照 (doudouOUC, 2026-05-18 06:23 **PR#4249 merge 前 4 分钟开零空窗接力**；+1177/-3 10 文件；4 routes 通过 PR 18 `WorkspaceFileSystem` boundary：`GET /file?path=...` UTF-8 text + meta(encoding/BOM/lineEnding) + `?maxBytes` soft-truncate + `?line`+`?limit` window / `GET /list?path=...` `{name, kind, ignored}` 2000-entry cap + `?includeIgnored=1` opt-in / `GET /glob?pattern=...` workspace-relative + `?cwd` + `?maxResults` / `GET /stat?path=...`；单 capability tag `workspace_file_read` 覆盖 4 read route；wire `runQwenServe` 构 + inject `fsFactory`——**PR 18 立的 `trusted: false` default invariant 在 PR 19 验证**(第一个真 consumer)；关闭 PR 18 follow-up #2 + #4：`fsFactory` injection contract test + glob audit hashes `boundWorkspace` 但 emit 文字 `pattern` field on 成功 + parse-rejection 两 path；trust snapshot 默认 `true`(operator-chosen workspace)) |
| **PR 20** file write/edit routes behind auth | 独立 PR：mutation gate + audit log + trust/qwenignore + 显式 symlink policy（依赖 PR 8, 15, 19）| 🔧 **OPEN [PR#4280](https://github.com/QwenLM/qwen-code/pull/4280)** (doudouOUC `[codex]`, 2026-05-18 09:50, +2108/-75 20 文件 382 tests passing；4 块新功能：① bounded raw byte reads (补 PR#4269 漏的 binary) ② hash-bearing text reads (给 write 用做 precondition) ③ strict-auth text write+edit routes 经 PR 15 mutation gate ④ content-hash concurrency checks 防 stale write；**4 关键设计点**：① **serve-local atomic temp+rename helper**——写不直接 truncate，先 temp file 后 rename 防中断破坏文件 ② **expected-hash precondition** 防 stale write (write 必须带匹配的 hash，否则报错) ③ **edit single-match policy**——`oldText` 在文件中必须 **exactly 1 处** match（零 match 错，多 match 错）④ `X-Qwen-Client-Id` 强制 stamp audit on write/edit；wenshao 10:32 第一次 APPROVED 评 "Atomic write flow: temp file → write → hash precondition → rename → fsync" 但 10:39 翻 CHANGES_REQUESTED——同 PR#4222/4250 second-pass agent 抓 pattern；follow-up PR#4279 Windows hotfix 已修 PR#4269 的 `path.sep` 漏 `/` normalize) |
| **PR 21** auth device-flow route | `POST /workspace/auth/device-flow` 或 Capability RPC for remote auth；必须 honor runtime locality（依赖 PR 15, 12）| 🔧 **OPEN [PR#4255](https://github.com/QwenLM/qwen-code/pull/4255)** (doudouOUC, 2026-05-17 17:26, **+3527/-8 17 文件 daemon 项目史上最大 PR** 破 PR#4250 纪录；OAuth 2.0 Device Authorization Grant (RFC 8628) brokered through daemon——tokens 落 daemon 不落 client；**4 route 在 `/workspace/auth/`**：POST device-flow strict + idempotent take-over (重复 POST 返 `attached: true`) / GET (5-min terminal grace) / DELETE idempotent / GET status；**5 workspace-scoped typed events** `_started`/`_throttled`/`_authorized`/`_failed`/`_cancelled`；新 cap tag `auth_device_flow`；**Runtime locality 严格**：daemon **NEVER spawn browser** 即使本地——**build-time static-source grep test** 11 forbidden patterns (`open`/`xdg-open`/`child_process`/`shell.openExternal`/dynamic-import 变体) fail build 防 future regression；**8 设计精彩点**：① per-providerId singleton + concurrent-call coalesce in-flight Promise map ② **`BrandedSecret<T>` 大重写**——specialist 发现原 `new String()` 在 `+`/template literal 经 `Symbol.toPrimitive` leak primitive → 改 frozen plain object + WeakMap + 4-way redaction (`toString`/`toJSON`/`Symbol.toPrimitive`/numeric → `'[redacted]'`/`NaN`) + unique symbol brand + 6 leak-path tests ③ `persist()` disk write FIRST 防 zombie in-memory token ④ `poll()` accepts signal + lost-success branch audit (`status: 'lost_success'` for incident-response correlation) ⑤ `transitionTerminal` returns boolean 防 sweeper × poll-tick double-fire ⑥ `bridge.broadcastWorkspaceEvent` 故意 distinct PR 16 避 conflict 后 fold-in ⑦ `BridgeClient.dispose()` wired into `runQwenServe.close()` shutdown drain ⑧ side fix `oauth_creds.json` 0o600 mode；**3 specialist agent pre-run 12 P0/P1 fold-in**——加 `type-design-analyzer` agent 总 3 agent；2 coordination items 待 wenshao input（`/workspace/auth/status` vs PR 12 `/workspace/providers` boundary）；5 fold-in 1 deferred post-merge；204+28 tests passing；⚠️ 未含 `integration-tests/cli/qwen-serve-routes.test.ts` **第七次 drift 风险**) |

### Wave 5 — Architecture extraction + output sinks + full multi-client security

> 必须等 Protocol skeleton（Wave 1）+ Permission route（Wave 2）+ Lifecycle closure（Wave 2.5）稳定后才能开始。

| PR | 内容 | 状态 |
|---|---|:---:|
| **PR 22** `refactor(serve): extract acp bridge primitives` | `httpAcpBridge.ts` 拆为 shared `AcpChannel` + `Transport` + `EventBus` + bridge primitives；CLI route contract 保持（依赖 PR 4, 8, 11）| ⏳ 等 PR 11（PR 4 + 8 ✅ 已解锁）|
| **PR 23** `feat(mcp): shared MCP transport/process pool` | 真共享 pool，keyed by canonical workspace + server **config hash** + auth/env/runtime inputs；lifecycle/refcount tests（依赖 PR 22, 14）| ⏳ |
| **PR 24** `feat(security): client pairing revocation + PermissionMediator` | pair tokens + revocation API + audit log + 4 policy strategies（first-responder / designated / consensus / local-only）（依赖 PR 8, 22）| ⏳ |
| **PR 25** `refactor(output): daemon-compatible output sinks` | JSONL / stream-json / dual-output behavior 移到 protocol/output sink 边界后；让 CLI + daemon client 共享 event semantics 而不是 duplicate terminal-specific logic（依赖 PR 4, 22）—— PR#4226 doudouOUC 平行 reducer 实现可拆这里提前 | ⏳ |
| **PR 26** `feat(adapters): flag-gated daemon client adapters` | 开始 TUI / channels / web-debug / IDE adapter migration behind flag，用 `DaemonSessionClient`；如 ownership/review size 需要可按 adapter 拆分；3 bonus spike [PR#4202](https://github.com/QwenLM/qwen-code/pull/4202) / [PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) / [PR#4199](https://github.com/QwenLM/qwen-code/pull/4199) 已铺路（依赖 PR 3, 4, 25）| ⏳ |

### Wave 6 — Release hardening + v0.16

| PR | 内容 | 状态 |
|---|---|:---:|
| **PR 27** alpha release docs | README known limits + loopback noauth warning + daemon runtime locality + durability semantics + deployment notes | ⏳ |
| **PR 28** npm alpha publish | 发布 Mode B alpha 到 npm + post-publish smoke test（依赖 selected Wave 1/2/2.5/3 baseline）| ⏳ |
| **PR 29** production token defaults | auto-generate daemon token + SDK env/file fallback + `~/.qwen/serve/instances/<host>-<port>-<workspaceHash>/token` + stale cleanup（依赖 PR 24）| ⏳ |
| **PR 30** production deployment references | systemd / docker / k8s examples + supervisor/restart docs + security model（依赖 PR 29）| ⏳ |
| **PR 31** v0.16 production-ready release | Final release after security defaults + docs + client identity/permission lifecycle complete（依赖 PR 24, 29, 30）| ⏳ |

### 并行 / 关键依赖

可并行的工作：
- **PR 1 baseline** 可与 PR 2/3 并行
- **PR 5 sessionScope** 在 PR 2 之后即可（不需要 typed events）
- **PR 9 heartbeat** 在 PR 7 之后可起，与 **PR 10 replay/backpressure**（依赖 PR 1, 4）并行
- **PR 12 read-only routes** 在 PR 2/4 之后可开（PR 7/8 review 中也能进行）
- **PR 15 mutation-gate helper** 在 PR 7 之后即可起，**与 Wave 2.5 并行**（仅 formal dep 是 clientId）；Wave 4 PR 16-21 仅 gate 在 PR 15 自身，不在 Wave 2.5 closure 上
- **PR 19 read-only file routes** 可在 write/edit (PR 20) 之前 land，但必须在 PR 18 `FileSystemService` boundary 后
- **Release docs** (PR 27) 可等到 npm publish 计划好

### Open questions（[Issue #4175 §Open questions](https://github.com/QwenLM/qwen-code/issues/4175)）

| 问题 | 当前推荐 |
|---|---|
| 何时 npm alpha publish？ | Wave 1 + 足够的 Wave 2 后 + release docs ready；不阻塞所有 control-plane routes |
| Loopback 默认 token？ | v0.15 alpha 保持现状 + 加 `--require-auth`（PR 15）；v0.16 改 token-by-default + SDK auto-discovery + explicit opt-out |
| Token instance path？ | `~/.qwen/serve/instances/<host>-<port>-<workspaceHash>/token`（多 daemon 共存）+ PID metadata（替代 port-only 路径）|
| 如何 align PR#3929-3931 remote-control？ | 等 primary clients 稳定后改为 daemon facade / control overlay；同时承认 **local daemon + remote-control relay** 和 **remote daemon + gateway** 两种形态，避免 parallel runtime/protocol fork |
| Worktree 交互？ | `boundWorkspace` 仍是 boot-time daemon workspace；file routes 默认 bound-workspace safety；worktree-specific 行为必须显式，不是隐式 `process.chdir()` |

---

### 三·二 Deployment + package contract (chiga0 #3803 comment 2026-05-18)

来源：chiga0 [Issue #3803 comment 4476174099](https://github.com/QwenLM/qwen-code/issues/3803#issuecomment-4476174099) + [comment 4476318030](https://github.com/QwenLM/qwen-code/issues/3803#issuecomment-4476318030) (GPT-5 Codex 协助生成)，**在 Wave 4 收尾、Wave 5 adapter migration 真要默认切换前，提议钉死 deployment / package / renderer / remote-control 契约**：

#### 1. Deployment forms 3 类（详 [§01 §三·一](./01-overview.md#三一-deployment-forms来自-chiga0-3803-comment-4476174099-2026-05-18)）

local-local（主装）/ remote-remote daemon 与 workspace colocate（cloud 推荐）/ **❌ local workspace + remote daemon**（不推荐——daemon 看不到 local fs/tools/MCP/skills）。

#### 1.5 Deployment shape matrix（详 [§04 §四](./04-deployment-and-client.md#deployment-shape-matrixclientruntime-lens2026-05-18)）

3-form 表只回答 daemon/workspace locality；client migration 还需要按 UI/adapter 形态拆分验证：

| Shape | Runtime locality | 当前 roadmap 含义 |
|---|---|---|
| Local - Local | 本机 daemon/runtime/workspace | `qwen` 默认迁移目标；必须有 auto-daemon UX + control-plane parity |
| Web chat / web terminal - Remote | remote daemon/runtime/workspace | web terminal 目标是 **daemon-native renderer**（typed events + reducer），PTY proxy 仅 fallback |
| Local IDE - Local daemon | 本机 daemon/runtime/workspace | IDE dogfood 优先形态；path identity 共享，workspace mismatch 要 fail loud |
| Local TUI - Remote | remote daemon/runtime/workspace | TUI 必须明示 remote label/path/auth；local cwd 不可当 runtime cwd |
| Channel + daemon | daemon 可 local 或 remote | channel adapter 需要 session routing / identity mapping / permission cards；local daemon 可服务个人 workstation remote-control |
| Remote-control overlay | local daemon + relay 或 remote daemon + gateway | P2 后置，但不是新 runtime protocol；复用 `DaemonSessionClient` + HTTP/SSE |

**Review rule**：每个 client PR 必须说明它验证哪种 shape、daemon/workspace/client locality 假设、是否 behind flag/default off，以及对 path mapping、runtime diagnostics、client capability reverse RPC 的依赖。

#### 2. Server / client / adapter 3 层 package boundary

即使**不物理拆分**，dependency direction 也必须 enforce：

```text
@qwen-code/daemon-server
  qwen serve / HTTP routes / auth / EventBus / ACP bridge / FS boundary / sandbox hooks

@qwen-code/daemon-client
  DaemonClient / DaemonSessionClient / typed event schema / reducer
  reconnect / heartbeat / capability negotiation

@qwen-code/daemon-adapters-*
  tui adapter / channel adapter / ide-web adapter / jsonl + stream-json + dual-output sinks
```

**3 条依赖方向规则**：
- ❌ server code 不可依赖 TUI / IDE / channel adapter
- ✅ adapter 只可依赖 SDK / protocol / reducer surface
- ✅ shared event reducer + typed protocol helper **必须住 client/protocol 层**，不能在 `packages/cli/src/serve/`

否则"每个 client integration 长出略不同的 bridge → Mode B convergence goal 侵蚀"。

#### 3. Local auto-daemon UX（**新设计草图**）

local TUI 默认走 daemon **不能**变成"先 manually 启 server 再 manually attach TUI"。目标 UX：

```text
qwen
  → discover daemon for this workspace
  → if absent, auto-start local `qwen serve` on loopback
  → attach TUI to a session
  → apply lifecycle policy on TUI exit: keep daemon / idle timeout / explicit shutdown
```

**收益**：TUI crash 不杀 daemon/session；IDE/web/channel attach 同一 session；重连 SSE `Last-Event-ID` + heartbeat + load/resume；event fan-out + permission flow 跨 client 统一。

**代价/风险**：extra local process/port/token/discovery file-lock/health check/logs；TUI 渲染必须 coalesce daemon chunks 到 Ink UI 而非 raw event spam；每个 mutate runtime state 的 TUI dialog 必须有 daemon control-plane route；daemon crash 影响 workspace 所有 session（1 daemon = 1 workspace blast radius 仍 acceptable）。

—— **属于 client migration plan 一部分，不是 afterthought**。Wave 6 release hardening 前补。

#### 4. Sandbox runner model（未来分层）

当前 Stage 1：

```text
qwen serve → spawn qwen --acp child
  → Config / ToolRegistry / McpClientManager / SkillManager
  → tools / shell / skills / MCP 全在 daemon host env 跑
```

期望未来：

```text
client → daemon API / control plane
  → runtime worker / sandbox runner
    → shell / skills / MCP / LSP / file tools
```

daemon 保 **control plane / session-event coordinator**，sandbox/runtime worker 独立 fail+restart。sandbox 挂 ≠ daemon 挂，daemon emit typed diagnostic event 重建 runner。

对 MCP / skills 的严格要求：
- MCP stdio children **在 runtime worker 跑**，不在 visual client
- HTTP/SSE MCP egress **从 runtime host/pod 出**，不是 client laptop
- skills 必须 exist 在 runtime env 或 sync/mount 进
- skill scripts/resources 在 runtime env 求值
- **`client capability reverse RPC` 严格 scoped 到 editor/clipboard/browser/notification/file_picker**，**不能 silently 成为 MCP/skill 执行 fallback**

#### 5. Client default migration gate（3-condition checklist）

TUI / channel / IDE default 切换到 daemon-backed 必须等：

1. **control-plane parity** —— TUI 所有 mutating dialog 在 daemon API 都有对应 route（[§04 §二 9 项 dialog](./04-deployment-and-client.md) 全 wire 化）
2. **reducer / adapter quality** —— typed event 消费器稳定 + 无 raw event spam
3. **auto-daemon lifecycle** —— 上面第 3 点的 discovery / loopback auth / lifecycle policy / port collision / workspace binding 都齐
4. **shape-specific readiness** —— local-local / remote TUI / IDE / channel / web terminal 各自 locality、path mapping、auth/gateway、diagnostics 要有明确验证记录

**当前 PR#4266 / PR#4267 draft 不冲突这条 gate** —— 是合规 behind-flag experiment。

#### 6. 文档更新建议（chiga0 list）

| 章节 | 加 / 强化 |
|---|---|
| Deployment forms | 3 forms + 哪些推荐 |
| Deployment shape matrix | local-local / web chat-terminal remote / local IDE-local daemon / local TUI-remote / channel+daemon / remote-control overlay |
| Package / dependency boundary | server / client SDK / adapter 三层 |
| Local auto-daemon UX | discovery / loopback auth / lifecycle / port collision / workspace binding |
| Runtime locality | daemon/runtime host owns fs/network/process/env/credentials/MCP/skills |
| Sandbox runner model | 当前 same-process trust vs 未来 isolated runtime worker |
| Client migration gate | default 切换条件 + per-shape readiness |

—— "Mode B 是对的，但 deployment + packaging 契约必须先显式化，否则同一套 code path 要同时服务 local CLI / remote devbox / enterprise cloud 三个场景，边界会糊。"

#### 当前 codebase 对照

| 建议项 | 已有 | 缺失 |
|---|---|---|
| 1 Deployment forms | §01 §三 双部署模式 | ✅ 已加 §三·一 3-form 表 |
| 1.5 Deployment shape matrix | §04 §四 | ✅ 已加 6-shape 表 + web terminal / remote-control clarify |
| 2 Package boundary | SDK 在 `@qwen-code/sdk`；channel-base 已拆 | ⚠️ daemon-server / daemon-client / daemon-adapters 未官方命名；3 条 dependency rule 未 lint enforce |
| 3 Auto-daemon UX | ❌ 完全未做 | **Wave 6 release hardening 前补**（PR 28 npm alpha 之前）|
| 4 Runtime locality | §04 §五 ✅；PR#4255 OAuth build-time grep test 已 ship | ⚠️ 未升级到 deployment model 章节 → 已加 callout 互链 |
| 5 Sandbox runner model | Stage 1 same-process trust 已显式；NoSandbox 默认 | Wave 5 PR 24 PermissionMediator 后或 Stage 2 独立设计 |
| 6 Client migration gate | Wave 5 PR 26 "flag-gated" 已写 | ⚠️ 3-condition checklist 未明文化 → 已加 §三·二 #5 |

---

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
| **web/debug** | [PR#4132](https://github.com/QwenLM/qwen-code/pull/4132) `/demo` ✅ **MERGED 2026-05-18 08:31** (jifeng, 4 天 24 reviews) | 作为最薄 POST+SSE client 验证面，已 ship；XSS 修把威胁模型扩到 daemon-emitted poisoned events | 已 ship |
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
| `GET /workspace/preflight`（**新增**）| daemon 启动 + 配置 readiness 整体检查：providers / MCP / skills / required binaries / egress 检测 | TUI / IDE / web |
| `GET /workspace/env`（**新增**）| daemon host 关键环境信息：可用 binaries / env vars（masked secrets）/ filesystem mount points / 网络可达性摘要 | TUI / IDE / web（运维）|

这一步的原则：**daemon 是 runtime owner，client 只做 view + command surface**。

**关键 status route 必须返回 actionable failure detail**（chiga0 [comment 4458840712](https://github.com/QwenLM/qwen-code/issues/3803#issuecomment-4458840712) 强调）：

| Route | 必须返回 |
|---|---|
| `GET /workspace/:id/mcp` | 每个 MCP server：`status` + `error` + `errorKind`（missing binary / blocked egress / auth/env error / init timeout / protocol error）—— 不能只返回布尔状态 |
| `GET /workspace/:id/skills` | 每个 skill：`loaded` + `error`（missing file / parse error / required binary not found）|

否则远端 client 会 "silently lose tools"——用户看到工具不可用但不知道是 daemon host 缺 `docker` 还是 pod 网络拦了 egress。详 [§04 §五 Runtime locality / environment contract](./04-deployment-and-client.md#五runtime-locality--environment-contract)。

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

2026-05-18 补充：remote-control 是 **control overlay**，不等于 daemon 必须远端。后续设计应同时覆盖两类部署：

| 形态 | 架构 | 关键要求 |
|---|---|---|
| Local workspace + local daemon + remote-control relay | remote UI/channel → relay → local bridge → loopback daemon → local workspace/runtime | outbound-only bridge；pairing/revoke；remote device identity → daemon client identity audit；local daemon 不裸露公网 |
| Remote workspace + remote daemon + remote-control UI | remote UI/channel → gateway → remote daemon → remote workspace/runtime | orchestrator/gateway；tenant isolation；quota/audit；runtime diagnostics |

两者都复用同一 daemon HTTP/SSE typed event contract；差别是部署/routing，不是 runtime protocol。

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
