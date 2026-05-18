# 01 — Overview

> [← 返回 README](./README.md) · [下一篇：Design Decisions →](./02-architectural-decisions.md)

## TL;DR

**qwen serve** 是 Qwen Code 的 HTTP daemon 模式——把 ACP NDJSON 协议通过 HTTP+SSE 暴露成可被任何 client / orchestrator 消费的服务。

**核心架构**：

```
1 daemon process = 1 workspace × N sessions multiplexed
```

与 `qwen --acp` stdio **1:1 心智对齐**——daemon 把 ACP stdio 包装成 HTTP。多 workspace 部署 = 多 daemon process（systemd / docker / k8s 各 1 process 自然管理）。

**关键设计依据**：
- **OS 进程级隔离**：跨 workspace = 跨 daemon process = 跨 OS process（最强）
- **资源 quota 直接对应**：systemd `MemoryMax=` / cgroup / docker `--memory` 直接 = per-workspace quota
- **K8s 云原生天然契合**：1 pod = 1 daemon = 1 workspace
- **Blast radius 最小**：daemon crash 只影响 1 workspace
- **Observability 直接**：`htop` / `ps` 列表 1 OS process = 1 workspace
- **心智简单**：daemon ↔ session 两层（无中间抽象）

**两条长期链路**：
- **Native local TUI** `qwen` — 继续走现有直连 / streamJson / Ink 路径；这是本地终端体验的长期主线，不是临时 fallback。原因：本机 TUI 直连比“本机 TUI → localhost HTTP server → runtime”少一层 httpServer，性能更直接、维护面更小、故障概率更低。
- **Mode B** `qwen serve` — headless HTTP front，当前优先服务 **remote web chat + web terminal** 等浏览器 / BFF / remote runtime 场景。remote web chat + web terminal technical POC 可与 P0 must-haves / state CRUD 并行启动，先验证 daemon HTTP/SSE typed event contract 的可行性；production-ready 仍等 P0/P1 收口。其他 channel、IDE 插件继续使用现有 `--acp` 模式，daemon 迁移后置。
- **Mode A** `qwen --serve` — 2026-05-15 后暂停推进；作为 parking lot 保留。

**主线 scope**：daemon building block + 协议表面锁定（Stage 2 后）。多 tenant / 跨 daemon process 路由 / SaaS 部署属 **External Reference Architecture**（外部商业平台实施）。

---

## 一、术语表

| 术语 | 定义 | 源码 anchor |
|---|---|---|
| **Daemon process** | `qwen serve` HTTP front 进程；启动时绑定 cwd = 单 workspace；持 Express 5 server + EventBus + 1 个内嵌 `qwen --acp` child | `packages/cli/src/serve/server.ts` |
| **Session** | ACP `Session` 实例（`QwenAgent.sessions: Map<sessionId, Session>` 内一条）；持 transcript / FileReadCache / PermissionManager | `packages/cli/src/acp-integration/session/Session.ts` |
| **Daemon client / adapter** | web chat / web terminal 等 daemon-native client 通过 `DaemonClient` / `DaemonSessionClient` + typed event reducer 接入，不直接订阅内存 EventBus；TUI / channel / IDE 可共享 client/render 基础库，但不默认改传输链路 | 详 [§02 §8](./02-architectural-decisions.md#8-server--client--runtime-boundary2026-05-18) |
| **Runtime worker** | 真正执行 tool / shell / MCP / skills / LSP / file operations 的 runtime；当前是 `qwen --acp` child，未来可替换 sandbox runner | 详 [§02 §8](./02-architectural-decisions.md#runtime-worker--sandbox-runner-boundary) |

**核心约束**：
- 1 daemon process **严格 1 workspace**（启动 cwd 绑定）
- 1 daemon process **可持 N sessions**（`QwenAgent.sessions: Map` 多路复用）
- 同 workspace N session 共享同一个 `qwen --acp` child process；当前 `Config` / `FileReadCache` / `ToolRegistry` / `McpClientManager` 仍随 ACP session 创建，跨 session MCP 共享需要未来 pool/proxy。

> 代码中可能看到的废弃符号：`byWorkspaceChannel` / `ChannelInfo` / `Workspace Bridge`（PR#3889 multi-workspace 路由层，已由 [PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) 移除）。

---

## 二、架构图

```
qwen serve (1 Daemon process, 绑定 cwd = /work/repo-a)
├─ Express 5 HTTP server + bearer auth + Host allowlist
├─ EventBus（per-session fan-out + ring replay + Last-Event-ID 重连）
└─ qwen --acp child (workspace = /work/repo-a)
   ├─ QwenAgent.sessions: Map → {sess-1, sess-2, sess-3}
   └─ per-session Config / MCP manager / FileReadCache
```

**多 workspace 部署**（开发者本地多项目 / 多 user / 多 tenant）：

```
┌────────────────────────────────────────┐
│ 同机多 daemon 部署                       │
├────────────────────────────────────────┤
│ qwen serve (cwd=/work/repo-a) :8001    │  ← daemon-1
│ qwen serve (cwd=/work/repo-b) :8002    │  ← daemon-2
│ qwen serve (cwd=/work/repo-c) :8003    │  ← daemon-3
└────────────────────────────────────────┘
                ↓ systemd / docker-compose / k8s
        OS-level 进程隔离 + per-daemon cgroup quota
```

跨 workspace 协调（IM bot 多项目 / WebUI 多 workspace 概览 / IDE multi-root）由 **client 侧 / orchestrator 侧**做（多 daemon endpoint 发现 + 路由）——daemon 自身只管"当前 workspace"。

**2026-05-18 架构边界补充**：

```text
client/render adapters / output sinks
  → daemon client/protocol layer
  → qwen serve HTTP/SSE control plane
  → runtime worker / sandbox runner
```

web chat / web terminal 是 daemon 第一阶段 daemon-native consumers：消费 typed events + shared reducer，再投影到 DOM chat 或 terminal-like UI。Native local TUI 继续走直连链路，但应逐步把 source adapter 与 terminal renderer 分离，让 **direct streamJson** 和 **daemon ACP-over-HTTP events** 都能复用同一套 view model / Ink→ANSI 渲染核心。PTY proxy 只保留为兼容 / demo / debug fallback。remote-control 是 control overlay，不再拥有独立 runtime / event protocol。详 [§02 §8](./02-architectural-decisions.md#8-server--client--runtime-boundary2026-05-18)。

External Reference Architecture 提供 orchestrator 层（详 [§06 §五 External Reference Architecture](./06-roadmap.md)）。

---

## 三、双部署模式

| 模式 | 启动命令 | TUI | 适用场景 |
|---|---|---|---|
| **Native local TUI** | `qwen` | ✅ | 本地终端长期主线：直连 runtime，保留最佳性能和最低复杂度 |
| **Mode B: Headless + HttpServer** | `qwen serve [--port N]` | ❌ | daemon server 主线：服务器 / 容器 / 远端机器 / K8s pod / web chat + web terminal |
| **Mode A: CLI + HttpServer** | `qwen --serve [--port N]` | ✅ 本地 | 暂停推进；作为 parking lot 保留 |

**当前 client 边界**：web chat / web terminal 作为第一阶段 daemon consumers，直接或通过 BFF 对接 `qwen serve` HTTP/SSE；`GET /session/:id/events` 是 daemon 内部 EventBus 的 SSE projection。外部 client 不直接 import / subscribe 内存 EventBus。本地 TUI、channel、IDE 插件暂不默认改链路。

**Mode B 远端 client 是 "thin shell"**（Stage 1）——只能渲染 wire 流，daemon-side state dialogs（`/memory` / `/mcp` / `/agents` 等）不可用。Stage 1.5c daemon-side state CRUD 补齐后，web chat / web terminal 才能成为完整 browser client；channel / IDE 是否迁移另行评估。详 [§04](./04-deployment-and-client.md)。

### 三·一 Deployment forms（来自 chiga0 [#3803 comment 4476174099](https://github.com/QwenLM/qwen-code/issues/3803#issuecomment-4476174099)，2026-05-18）

Mode B 之下进一步区分**3 种 deployment form**，钉死 daemon host 与 workspace host 的同址要求：

| Form | Daemon host | Workspace host | Client host | 推荐度 |
|---|---|---|---|---|
| **Local single-machine** | local 机器 | local 机器 | local native TUI / local IDE / optional local web | ✅ 主装机体验；native TUI 直连长期保留；local daemon 仅服务 web/remote-control/实验 client |
| **Cloud/devbox remote-runtime** | remote host/pod | **同** remote host/volume | browser web chat / web terminal | ✅ 推荐 cloud+client 拆分；Codespaces/Coder 风格——workspace 与 runtime **必须 colocate** |
| **Local workspace + remote daemon** | remote host/pod | local 机器 | local client | ❌ **不推荐** —— daemon 看不到 local files / tools / MCP / skills，除非有显式 sync / mount / orchestrator |

**核心不变式 — daemon host = runtime host**：

> File access / shell tools / LSP / provider auth / MCP servers / skill discovery+resources+scripts / process execution **全部从 daemon environment 求值**，除非未来有显式的 [client-capability reverse RPC](./04-deployment-and-client.md#六client-capability-反向-rpc) 例外声明。

详 [§04 §四 Deployment shape matrix](./04-deployment-and-client.md#deployment-shape-matrixclientruntime-lens2026-05-18) + [§06 §三·二 Package boundary contract + auto-daemon UX](./06-roadmap.md#三二-deployment--package-contract-chiga0-3803-comment-2026-05-18)。

---

## 四、资源经济性

**同 workspace N session 经济性**（继承 ACP `QwenAgent.sessions: Map` 原生 multi-session）：

| N 同 workspace session | 内存 RSS | 说明 |
|---|---|---|
| 1 | ~60-100 MB | baseline |
| 5 | **~60-100 MB** | N session 共 1 `qwen --acp` child |
| 10 | **~80-150 MB** | 同上 |
| OAuth refresh | 1× per daemon | 共享 |
| FileReadCache | per session | 当前随 `Config` 创建；跨 session 共享未做 |
| CLAUDE.md parse | per session | 当前随 session config 初始化 |
| Cold start（同 daemon 第 N session）| **<200ms** | attach existing child |

**多 workspace 部署成本**：M workspace = M daemon process。每 daemon baseline ~30-50 MB Express server + bearer auth + EventBus + Host allowlist。例 5 workspace × 5 session 同机 ≈ ~450-750 MB（5 × baseline + 5 × child）。换得 OS 进程级隔离 + cgroup quota + blast radius 最小 + 心智简单。

---

## 五、Stage 演进

| Stage | 范围 | 状态 |
|---|---|---|
| **Stage 1** | Mode B headless `qwen serve` + N session multiplexed + EventBus + first-responder permission + 9 STAGE1_FEATURES | ✅ **MERGED 2026-05-13** ([PR#3889](https://github.com/QwenLM/qwen-code/pull/3889)) |
| **Stage 1.5a §02** | [PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) 1 daemon = 1 workspace 收紧 | ✅ **MERGED 2026-05-15** |
| **Stage 1.5a must-haves** **(P0)** | chiga0 10 must-haves 剩 9 项 — Mode B 生产 blocker（loadSession HTTP / pair tokens / sessionScope override）| ~2 周（9 PRs 可并行）|
| **Stage 1.5c** **(P0)** | daemon-side state CRUD 8 routes — Mode B 远端 client 摆脱 thin shell | ~3-5d |
| **Stage 1.5-prereq** **(P1)** | chiga0 6 architecture findings — lift `AcpChannel` / `EventBus` / `PermissionMediator` 到 `@qwen-code/acp-bridge` | ~1-2 周 |
| **Stage 1.5-client/render extraction** **(P1 / POC 并行)** | remote web chat / web terminal 先做 technical POC 接入 Mode B daemon；抽取 client 包与 terminal render core，供 native TUI 与 web terminal 共享渲染能力；channel / IDE 继续 `--acp`，迁移后置评估 | ~2-3 周，可与 P0 并行试点 |
| **Stage 1.5b** Mode A **(P2 推迟)** | Mode A `qwen --serve` flag — [Issue #4156](https://github.com/QwenLM/qwen-code/issues/4156)；A1 [PR#4160](https://github.com/QwenLM/qwen-code/pull/4160) ✅ MERGED；**推迟到 1.5c 后**（Mode A 价值依赖 1.5c）| ~5-6d |
| **Stage 1.5-remote-control** **(P2 后置)** | [PR#3929](https://github.com/QwenLM/qwen-code/pull/3929) / [#3930](https://github.com/QwenLM/qwen-code/pull/3930) / [#3931](https://github.com/QwenLM/qwen-code/pull/3931) 后续作为 daemon facade | 待 web chat / web terminal contract 稳定 |
| **Stage 2** | 协议补齐（WebSocket / mDNS / OpenAPI / Prometheus / `/ext` + Reverse RPC 5 类 Client Capability）| ~3-4 周（拆 2a-2d）|
| **Stage 2e** | 可选 native in-process（去 `qwen --acp` child）| ~1-2 周 |

> **优先级决策（2026-05-15）**：Mode B 优先 — must-haves + 1.5c 摆脱 thin shell → 1.5-prereq 架构清洁 → Mode A（1.5b）推迟。详 [§06 §三 推进顺序](./06-roadmap.md)。
>
> 💡 **Implementation tracker**：[Issue #4175](https://github.com/QwenLM/qwen-code/issues/4175) doudouOUC 的 Mode B v0.16 production-ready 31-PR rollout plan（7 Wave，含 Wave 2.5 reliability）—— 上表的 Stage 1.5a/c/-prereq 映射到 Wave 1-5；Wave 6 是 release hardening + v0.16。详 [§06 §三·一 Wave breakdown](./06-roadmap.md#三一-issue-4175--31-pr-wave-breakdown-production-ready-tracker)。
>
> 🎉 **Wave 1+2+2.5+3+4 + W5 PR 22a+22b/1+22b/2 + 多 follow-up 同夜冲合**（2026-05-16~19 共 **38 MERGED + 5 OPEN/draft + 3 CLOSED**：23 Wave PRs (含 W5 PR 22b/2 design) + 7 follow-up + 3 bonus Stage 0 + 1 外部 + 2 refactor follow-up + **3 凌晨新合 (#4302 telemetry polish + #4306 E2E unbreak + #4304 W5 PR 22b/2 design slice)** MERGED；1 PR 17 P2 follow-up + 1 #4291 7-thread follow-up + 3 adapter wire-up draft；Wave plan 进度 **22.75/31 ≈ 73%**；**仅剩 Wave 5 PR 22b/3 mechanical + 23/24/25/26 + Wave 6 共 ~9 PRs 待全开**）：
> - ✅ Wave 1 **PR 2** [PR#4191](https://github.com/QwenLM/qwen-code/pull/4191) capability registry + protocol versions — **MERGED 2026-05-16 10:07** (doudouOUC)
> - ✅ Wave 2 **PR 5** [PR#4209](https://github.com/QwenLM/qwen-code/pull/4209) per-request `sessionScope` override — **MERGED 2026-05-16 15:54** (doudouOUC, 4h26m open→merge)
> - ✅ Wave 1 **PR 1** [PR#4205](https://github.com/QwenLM/qwen-code/pull/4205) baseline harness — **MERGED 2026-05-16 16:41** (doudouOUC, 4 Critical 修后；首份 `baseline-stage-1.json` 存档 macOS arm64 / RSS 223.5 MB / attach 1-3 ms / MCP 4 children constant under single-scope)
> - ✅ Wave 1 **PR 3** [PR#4201](https://github.com/QwenLM/qwen-code/pull/4201) DaemonSessionClient skeleton — **MERGED 2026-05-16 17:01** (chiga0；前身 PR#4195 CLOSED；v2 补 AbortSignal/event-without-id/error-path 测试)
> - ✅ Wave 2 follow-up [PR#4214](https://github.com/QwenLM/qwen-code/pull/4214) — **MERGED 2026-05-16 17:51** (doudouOUC, 1h23m) — 校准 integration-test 9→10 + 建立 capability registry **三套来源 lockstep** 模式
> - ✅ Wave 1 **PR 4** [PR#4217](https://github.com/QwenLM/qwen-code/pull/4217) typed event schema — **MERGED 2026-05-17 04:31** (chiga0, squashed `ab88f6f1`，5 轮 review / 2 轮自我修复：① 4 Critical 修 ② 5 项 reducer hardening invariants：`lastEventId` 单调推进抗回退 / `pendingPermissions` cap 64/session + dropped 诊断计数 / `permission_resolved` 未匹配 requestId 诊断 + cancelled outcome / `toolCall` 校验收紧 + finite number / reducer 存储时复制抗引用共享)
> - ✅ Wave 2 **PR 6** [PR#4222](https://github.com/QwenLM/qwen-code/pull/4222) HTTP load/resume session — **MERGED 2026-05-17 04:58** (doudouOUC `[codex]`, 3h17m open→merge, 5 轮 review；体量 review 期间几乎翻倍 +1091/-35 → **+2078/-51 16 文件**；wenshao 03:33 第一次 APPROVE 后 11 分钟二次 /review 发现 **asymmetric coalesce guard** 等 2 Critical 翻回 CHANGES_REQUESTED——原只 guard load-on-resume，因 `resume()` seeds `lastEventId: 0` 与 load 语义不同必须双向；commit `db55b1c8b` 修后 04:55 最终 APPROVE)
> - ✅ Wave 2 **PR 7** [PR#4231](https://github.com/QwenLM/qwen-code/pull/4231) daemon-stamped client identity — **MERGED 2026-05-17 08:19** (chiga0, 1h23m open→merge, 最终 +910/-79；wenshao **9 parallel review agents** 覆盖 correctness/security/code quality/performance/test coverage + 3 audit personas；commit `52295980f4` 修 1 Critical（`InvalidClientIdError` 走 `sendBridgeError` 翻 400 而非 500）+ 6/7 其他 concern；`randomUUID()` + `client_` 前缀 122 bits entropy)
> - ✅ Wave 2 **PR 8** [PR#4232](https://github.com/QwenLM/qwen-code/pull/4232) session-scoped permission route — **MERGED 2026-05-17 09:48** (chiga0, 2h44m open→merge, 最终 +801/-30；rebase 到 main 后 single-commit `4eae97a33b`；review 抓 3 项：barrel re-export 新 type / **抽 `parsePermissionOutcome()` 共享 helper** 去掉 scoped+legacy 两 route 重复 / input validation 测试补全；`permission_already_resolved` event + bounded record 防 memory leak（同 PR#4217 cap pattern）+ 新 capability tag `session_permission_vote`)
> - ✅ Wave 2.5 **PR 9** [PR#4235](https://github.com/QwenLM/qwen-code/pull/4235) client heartbeat — **MERGED 2026-05-17 10:57** (doudouOUC, 2h00m open→merge，**首轮一把过 0 CHANGES_REQUESTED**；+581/-2 14 文件, 测试 / 生产 ≈ 1.7x, 14 test cases；wenshao quote："**all 3471 serve/SDK tests pass** ... security model is sound: clientId validation runs before any timestamp update"；**4 安全不变式** + lockstep 维持 + HTTP state route 推迟到 PR 12 + `client_heartbeat` capability tag —— 把 chiga0 5 轮 review 学到的全 internalize 进首版)
> - ✅ Wave 2.5 **PR 10** [PR#4237](https://github.com/QwenLM/qwen-code/pull/4237) SSE replay sizing + `slow_client_warning` backpressure — **MERGED 2026-05-17 11:30** (doudouOUC, 2h19m open→merge, 3 轮 review (0 Critical, 3+5 Suggestion)；最终 +893/-81；wenshao 高赞 **`BoundedAsyncQueue.liveCount` refactor** 是 thoughtful pre-emptive fix——原 `forcedInBuf` counter 在 `slow_client_warning` mid-stream force-push 下会挂，doudouOUC 自己实现时意识到 invariant 破裂提前重构；`DEFAULT_RING_SIZE` 4000→8000 + 5 处 docs 文案修 + `eventRingSize` forwarding + hysteresis 75%/37.5% 防 flap)
> - ✅ Wave 2.5 **PR 11** [PR#4240](https://github.com/QwenLM/qwen-code/pull/4240) session metadata + close/delete lifecycle — **MERGED 2026-05-17 12:42** (doudouOUC, 2h16m, 4 轮 review, 最终 +1175/-35；headRef `worktree-delightful-cooking-goose` Claude Code worktree fingerprint；1 Critical typecheck 修（`BridgeSessionSummary` 新字段 + mock 同步）+ ordering 修（`events.close()` 必须 BEFORE `connection.cancel()` in `closeSession`，否则 subscriber 收 `session_closed` 前流就断）；wenshao 高赞 "**terminal-event upgrade + pending-permission cancellation 的 test coverage exactly the contract I'd worry about most**")
> - ✅ Wave 3 **PR 12** [PR#4241](https://github.com/QwenLM/qwen-code/pull/4241) read-only status routes — **MERGED 2026-05-17 13:37** (doudouOUC, 3h02m，最终 +2363/-64 review +251 LOC；wenshao **review pipeline 又升级**：gpt-5.5 /review + **mimo-v2-5-pro 9 parallel agents**（新加 **attacker simulation + 3AM oncall** personas）+ 增量审 + force-push hardening commit `6244c894` 修；cli vitest 368 → **396 tests passing（+28）**；关键修复：read-only session routes 也 forward `clientId` for **audit symmetry**——把 PR#4231 invariant 扩到 read 路径；workspace routes 不 spawn ACP 即使 polled；5 routes + 5 capability tags + SDK 5 typed payload types)
> - ✅ Follow-up [PR#4245](https://github.com/QwenLM/qwen-code/pull/4245) integration test mirror align — **MERGED 2026-05-17 14:53** (doudouOUC, **40m open→merge 一把过**——daemon 项目最短；release CI run 25992130532 跑挂触发；features list 18→24 + SSE backpressure 3→4 frames 校准；wenshao 9-dimension review 全通过 + post-merge gpt-5.5 二次验证；**第三次 drift 警告**——doudouOUC 建议把 integration test 进 PR-CI lane 或 restructure assertion 去掉 inline expected list)
> - ✅ Wave 3 **PR 13** [PR#4251](https://github.com/QwenLM/qwen-code/pull/4251) preflight + env diagnostics routes — **MERGED 2026-05-17 23:29** (doudouOUC, 7h40m, 7 轮 review；最终 +2577/-127 (review +684/-98)；**第六次 drift 被 wenshao [Critical] 在 PR review 中抓**——doudouOUC "故意 batch fix" 策略破产，必须 in-PR 修；4 轮 fix: ① **execSync → execFile migration** 安全防 shell injection（也修 Windows CI 挂）② `safeCheck` errorKind ③ proxy redaction `safeProxyValue` 3-stage parse (URL → `http://`-prepend → regex scrub → `<unparseable>` final fallback + 4 unit tests) ④ `validateAuthMethod` mutation P1 ⑤ integration test mirror 加 `workspace_env` + `workspace_preflight` ⑥ live ACP + ACP failure fallback tests（之前只测 idle path）⑦ 3 structural fix from low-confidence items；2 route + 第一个 land **closed `errorKind` 7-value taxonomy**（PR 14 复用）+ 5 strict invariants（含 build-time grep）+ 6 commit 拆分；639/639 tests passed)
> - ✅ Wave 3 **PR 14** [PR#4247](https://github.com/QwenLM/qwen-code/pull/4247) MCP client guardrails — **MERGED 2026-05-18 04:07** (doudouOUC, **13h09m daemon 项目史上最艰难一合**, 9+ 轮 review **11 [Critical]**)；最终 +2867/-31（review 翻 2.4x +1679 LOC）；**4 个不同 LLM model 跑 review**: mimo-v2.5-pro / DeepSeek-v4-pro / glm-5.1 / 9 parallel agents + 3 reverse-audit rounds；R2 短暂 APPROVED 但 R3 翻回 CHANGES_REQUESTED；wenshao 中文最终 APPROVE quote: "前次 16:18 APPROVED 落后 5 个 commit；我陆续追了 11 条 [Critical]（R3-R8 各轮）。HEAD 全部对账通过——3 个 spawn path（bulk/per-server/lazy `readResource`）现在 **`weReserved`-driven 清理完全对称**"；核心修复 `if (weReservedSlot) { try { await client.disconnect() } catch {} reservedSlots.delete() }` 模式贯穿所有 catch 块；3 spawn path budget gating 全补 (C1) + zombie slot leak 全修 (C2/C3) + transport leak 修 (R7-R8) + stale global discoveryState 改 instance-bound + 197/197 tests passing；体量与 review 轮次创 daemon 项目 4 项最高纪录)
> - ✅ Wave 4 **PR 16** [PR#4249](https://github.com/QwenLM/qwen-code/pull/4249) workspace memory + agents CRUD — **MERGED 2026-05-18 06:27** (doudouOUC, **15h20m 创新 daemon 项目最长 lifetime** 破 PR#4250 13h55m；**11 rounds review + 6 LLM model**：Copilot / gpt-5.5 / DeepSeek-v4-pro / glm-5.1 / qwen-latest / github-advanced-security + wenshao R1-R7；最终 +5318/-8 23 文件（review 翻 +2364）；wenshao R11 quote: "**fold-in cascade 2a → 2j has addressed every critical and high-impact finding**"——10 sub-fix iteration；7 routes + 2 cap tag + 2 typed event workspace-level fan-out + 3 scope decision (auto-memory deferred PR 16.5 / agents create+update split / persistent audit log deferred PR 24)；工程亮点 CRUD-scoped `Config` Proxy stub fail-loud + whitespace-append suppression + bridge.publishWorkspaceEvent fan-out)
> - ✅ Wave 4 **PR 19** [PR#4269](https://github.com/QwenLM/qwen-code/pull/4269) safe workspace file read routes — **MERGED 2026-05-18 08:17** (doudouOUC, **1h54m 极短 lifetime**——PR 18 chokepoint 红利显化；最终 +1454/-8 10 文件；wenshao 中文 APPROVED quote: "本地实测通过(525/525 tests + **安全边界全部正确拒绝** + **审计串联确认**)"；4 routes `GET /file|/list|/glob|/stat` 通过 PR 18 `WorkspaceFileSystem` boundary；单 cap tag `workspace_file_read`；wire `runQwenServe` 构 + inject `fsFactory`——**PR 18 `trusted: false` default invariant 第一个真 consumer 验证**；关闭 PR 18 follow-up #2 + #4)
> - ✅ Follow-up [PR#4279](https://github.com/QwenLM/qwen-code/pull/4279) Windows 路径 hotfix — **MERGED 2026-05-18 09:53 (26m 极短，daemon 项目最快 hotfix 破 PR#4245 40m)** (doudouOUC, +7/-1 1 文件；`workspaceRelative` 漏 `path.sep`→`/` normalize，Windows CI 唯一 red 1h36m on main；4 routes `/file`/`/stat`/`/list`/`/glob` 全受影响；wenshao gpt-5.5 /review 一把过)
> - ✅ Wave 4 **PR 20** [PR#4280](https://github.com/QwenLM/qwen-code/pull/4280) file write/edit + bounded raw byte read — **MERGED 2026-05-18 14:37** (doudouOUC `[codex]`, **4h47m + 仅 13 reviews**——PR#4255 巅峰后回归常态；最终 +2557/-266 25 文件；4 块新功能：bounded raw byte reads (补 PR#4269 binary case) / hash-bearing text reads / strict-auth write+edit 经 PR 15 gate / content-hash concurrency check；**4 关键工程亮点**：① serve-local **atomic temp+rename helper** (temp write → fsync → hash precondition → rename → fsync dir) ② **expected-hash precondition** 防 stale write 丢失更新 ③ **edit single-match policy** `oldText` 必须 exactly 1 处 match (零/多 match 都报错，让 caller disambiguate) ④ `X-Qwen-Client-Id` 强制 stamp audit on write/edit；12:58 wenshao CHANGES_REQUESTED → 13:33 修 → 14:17 gpt-5.5 /review APPROVED → 14:37 MERGED)
> - ✅ Wave 4 **PR 17** [PR#4282](https://github.com/QwenLM/qwen-code/pull/4282) approval/tools/init/MCP-restart — **MERGED 2026-05-18 16:27** (doudouOUC, **6h21m + 34 reviews**——Wave 4 收尾常态；最终 +3685/-13 28 文件 (review +939)；**4 strict-gated mutation routes**：`POST /session/:id/approval-mode` (`plan`/`default`/`auto-edit`/`yolo` + optional `persist: true`) + `POST /workspace/tools/:name/enable` (`tools.disabled` skip-register **distinct from** `permissions.deny`) + `POST /workspace/init` **纯机械** scaffold `QWEN.md` 故意不调 model（保 mutation 同步语义 vs prompt 异步语义清晰；AI-fill 需 client 显式 follow-up `POST /session/:id/prompt`）+ `POST /workspace/mcp/:server/restart` 带 PR 14 v1 budget pre-check；全 strict-gated + `X-Qwen-Client-Id` audit + `originatorClientId`-stamped SSE event；**核心 hardening**：`TrustGateError` typed class in core → bridge map untrusted-folder rejection to `errorKind: 'auth_env_error'` (PR 13 taxonomy) **不再 regex-match messages**——跨 PR typed-error 模式复用；wenshao 14:59 CHANGES_REQUESTED → 15:51 doudouOUC inline 修 → 16:27 APPROVED + MERGED) — **Wave 4 完整 7/7 收尾 🎉**
> - ✅ Wave 5 **PR 22a** [PR#4295](https://github.com/QwenLM/qwen-code/pull/4295) acp-bridge skeleton + zero-coupling primitives lift — **MERGED 2026-05-18 17:23** (doudouOUC, **56 分钟极速合**——pure refactor 红利；最终 +1106/-688 17 文件，review 期间仅 -20/+44 极小调整；8 reviews；wenshao APPROVED quote: "**pure refactor, mechanically verified**: file moves preserve content via `git mv`, wrappers are two lines (docstring + `export *`) so **no opportunity for behavioral drift**, all **13 existing import sites resolve through the wrappers unchanged**, the new package builds and passes 28/28 of its own tests, and the daemon's SSE / ring replay / Last-Event-ID..."；3 zero-coupling primitive 移到新 `@qwen-code/acp-bridge` package；额外种 `PermissionMediator` interface contract 给 PR 24 4 strategies；chiga0 #3803 "Stage 1.5-prereq AcpChannel lift" 真正落地；**解锁 PR 22b / PR 23 / PR 24**；follow-up suggestion: `SubscriberLimitExceededError` (public DoS defense) 测试覆盖待补)
> - ✅ Follow-up [PR#4291](https://github.com/QwenLM/qwen-code/pull/4291) PR#4255 OAuth fold-in — **MERGED 2026-05-18 23:01** (doudouOUC, **7h35m**, 最终 +1406/-31 (初版 +418/-20，**review 期间 +988 ×3.4 涨**)；同时打 post-merge deepseek-v4-pro 5 项 (含 2 Critical: `poll()` raw err.message stderr / `runPollTick` 30s timeout) + PR#4255 PR body 列的 fold-in 1 deferred 5 项 (DeviceFlowEntry discriminated union / single-source status union / `awaitCompletion` memoize / ALL session bus fail stderr elevate / 404 `not_found_or_evicted` errorKind)；**OAuth 一条线总投入 ~+7578 LOC** (PR#4255 +6172 + PR#4291 +1406)，daemon 项目史上最贵功能)
> - ❌ Follow-up [PR#4293](https://github.com/QwenLM/qwen-code/pull/4293) E2E baseline lockstep — **CLOSED 2026-05-18 16:45 (Superseded by PR#4282)** (doudouOUC, 24 分钟内 close；**8th mirror drift** PR 20/21 merged 后 main E2E run 26040351119 跑挂 Linux sandbox:none/docker + macOS 全挂；doudouOUC 16:21 开 +3 一行 fix → 16:27 **PR#4282 W4 PR 17 MERGED 期间 review-time bundle 了 3 cap baseline 一并 sync**——wenshao 主动让 PR 17 顺手做 8th drift 善后 → 16:45 doudouOUC close PR#4293 提"main's E2E baseline is already in sync"；揭示 doudouOUC 真实 lockstep 模式是 **review-time batch consolidation** 而非 per-PR sync——main 短暂破损换每 feature PR 不加 lockstep 负担)
> - 🔧 Follow-up [PR#4297](https://github.com/QwenLM/qwen-code/pull/4297) PR#4282 post-merge P2 fixes — **OPEN + CONFLICTING + CHANGES_REQUESTED**（doudouOUC, 2026-05-18 16:39, **review 期间 +846 ×3.4 涨**到 +1191/-54 (初版 +345/-11)；**PR#4282 W4 PR 17 squash-merge 后 Codex /review 抓 4 P2 issue** 均现有测试套不可重现：① `POST /workspace/init` 用错文件名——daemon parent 不 `loadCliConfig`，修 `runQwenServe` snapshot value 转发 `BridgeOptions.contextFilename` ② `disabledTools` snapshot stale —— restart MCP 用 fresh snapshot ③④...；与 PR#4291 同款 ×3.4 体量膨胀 pattern；daemon 项目工作流升级：**"review at merge" → "review continuously"** 标准动作 post-merge AI /review)
> - ✅ Wave 5 **PR 22b/1** [PR#4298](https://github.com/QwenLM/qwen-code/pull/4298) acp-bridge: lift status / paths / errors / bridge types — **MERGED 2026-05-18 23:00** (doudouOUC, 4h55m, +1431/-1450 12 文件；**PR 22 拆 3 阶段 split**：PR 22a (zero-coupling primitives, MERGED 17:23) + **PR 22b/1 (pure-type + pure-utility surface lift, MERGED 23:00)** + ⏳ PR 22b/2 (implementation lift + `DaemonStatusProvider` injection seam)；mechanical + low-risk lift continuation；3-stage split 让每阶段保持机械低风险，复杂度集中在最后一阶段)
> - ✅ Follow-up [PR#4300](https://github.com/QwenLM/qwen-code/pull/4300) typed errors for channel-closed + missing-cli-entry — **MERGED 2026-05-18 23:14** (doudouOUC, closes #4299 tech-debt；+118/-29 3 files；`BridgeChannelClosedError` + `MissingCliEntryError` 替代 `mapDomainErrorToErrorKind` 的 regex on `.message`——**typed-error 模式跨 PR 第 N 次复用**（PR 13 closed `errorKind` taxonomy / PR 17 `TrustGateError` / PR 22-area BridgeTimeoutError / 现在两个），daemon 项目 typed-error 设计哲学固化)
> - ✅ Follow-up [PR#4302](https://github.com/QwenLM/qwen-code/pull/4302) telemetry Phase 1.5 polish — **MERGED 2026-05-19 01:21** (doudouOUC, 2h14m open→merge, 最终 +454/-65 7 files **review 期间 +199 LOC 涨** 255→454; merge commit `8d9cc6156b`；wenshao 1 轮 CHANGES_REQUESTED → DISMISSED → gpt-5.5 /review LGTM → qwen-latest /review APPROVED；4 fix items：① `session-tracing.ts` 新 `resolveParentContext()` mirrors `tracer.ts:getParentContext()`, ALS parent 缺时 re-parent 到 active OTel span 再 fallback 到 synthetic session root (3 call site 统一: `startLLMRequestSpan` / `startToolSpan` / `startToolExecutionSpan`) ② `coreToolScheduler.ts` exec span **abort-as-result snapshot**: tool resolves with normal `ToolResult` after observing `signal.aborted` → snapshot abort flag pass to `endToolExecutionSpan` 让 sub-span 与 cancelled parent tool span 一致 + 加 sanitized `error` reason ③ log/span consistency 4 项 polish；**follow-up to PR#4126 Phase 1，tracked in #4212**——独立 telemetry 工作流，**不在 daemon Wave plan**)
> - ✅ Wave 3 **PR 14b** [PR#4271](https://github.com/QwenLM/qwen-code/pull/4271) MCP guardrail push events + hysteresis — **MERGED 2026-05-18 17:06** (doudouOUC, 9h50m, 33 reviews；最终 **+3329/-266 review 期间 +1505 LOC 涨 +82%**；2 新 typed event：① `mcp_budget_warning` 75%/37.5% hysteresis at manager level (mirrors PR 10 跨抽象层 pattern) ② `mcp_child_refused_batch` coalesced；**PR 14 snapshot 字段保持不变 v1→v2 干净 layer** 验证；新 ACP transport `qwen/notify/session/mcp-budget-event` child→bridge notification；**临门同 PR#4255 widened literal type 问题再来** —— `slow_client_warning` fixture (line 664) widened literal type fail `asKnownDaemonEvent` typecheck，新 PR 14b fixtures (line 776/914) 用 `satisfies` 已修但触老 fixture；wenshao 17:05 APPROVED quote: "state machine + extNotification + bridge republish + SDK predicate/reducer chain holds end-to-end")
> - ✅ Wave 4 **PR 18** [PR#4250](https://github.com/QwenLM/qwen-code/pull/4250) FileSystemService boundary — **MERGED 2026-05-18 05:14** (doudouOUC, **13h55m 创新 daemon 项目最长 lifetime** 破 PR#4247 13h09m；**10 rounds 70 review threads 全 resolved**；最终 +4753/-68（review +1483 LOC）；wenshao R10 quote: "**Ten rounds of review iteration in, all 70 threads resolved, no Critical or Suggestion left dangling**"；review 抓出 13+ Critical + ~50+ Suggestion：`import type` value mismatches 引 ReferenceError CI fail / **TOCTOU symlink substitution** in readText / **writeText 无 TOCTOU 保护** / `edit()` read-modify-write race / **`safeUtf8Truncate` off-by-one** corrupt UTF-8 / OOM gate gap in `readBytes` 不依赖 caller maxBytes / dangling+multi-hop symlink bypass / glob cwd bypass + error classification / `edit()` bypasses encoding/BOM / `hasSuspiciousPathPattern` regex gaps + FP / `enforceReadBytesSize` hard-cap clamp / `stat` ENOENT tolerance / audit message privacy gating；**`assertInodeStableAfterRead` invariant 贯穿 readText/readBytes/edit**——typical chokepoint refactor 范本)
> - ✅ Wave 4 **PR 21** [PR#4255](https://github.com/QwenLM/qwen-code/pull/4255) OAuth device-flow route — **MERGED 2026-05-18 14:05** (doudouOUC, **20h39m daemon 项目史上最长 lifetime** 破 PR#4249 15h20m + **135 reviews 史上最多** + **最终 +6172/-51 daemon 项目史上最大 PR** 破 PR#4249 +5318；review 期间几乎翻倍 +2645/-43；OAuth 2.0 Device Authorization Grant (RFC 8628) brokered through daemon；4 route + 5 typed events + new cap tag `auth_device_flow`；**Runtime locality 严格**：build-time static-source grep 防 11 patterns；**8 设计精彩点**：BrandedSecret 4-way redaction + persist disk-first + poll signal lost-success + transitionTerminal boolean 防 double-fire + broadcastWorkspaceEvent distinct vs PR 16 + dispose wired into shutdown + `oauth_creds.json` 0o600；**临门一脚被 1 TS 类型 inference 卡 12:51 dismissed** (`daemonEvents.test.ts:664` synthetic `slow_client_warning` `type: string` 推导不匹配 `DaemonEvent`) → 13:01 doudouOUC 修 → 13:59 gpt-5.5 /review LGTM → 14:05 MERGED)
> - ✅ Wave 4 **PR 15** [PR#4236](https://github.com/QwenLM/qwen-code/pull/4236) mutation gating helper + `--require-auth` — **MERGED 2026-05-17 12:10** (doudouOUC, 3h06m, 2-3 轮 review 无 Critical 全 nit suggestion；最终 +620/-24；wenshao 真起 `qwen serve` **端到端 verify 4-cell behavior matrix 各 1 次**（review quality 新基线）；`createMutationGate` clean handoff for Wave 4 routes；`CONDITIONAL_SERVE_FEATURES` registry primitive；**解锁 Wave 4 PR 16-21 (6 个 PR)**)
> - ✅ PR 3 follow-up [PR#4225](https://github.com/QwenLM/qwen-code/pull/4225) DaemonSessionClient hardening — **MERGED 2026-05-17 07:05** (chiga0, 3h11m open→merge, +323/-18 测试 141→205 行；多模型 /review pipeline：DeepSeek-v4-pro + claude-opus-4-7 + wenshao 4 轮 review；**chiga0 最终让步把 eager guard 改回 lazy**+ 加 `cursor monotonicity via Math.max`（同 PR#4217 reducer hardening pattern）+ abort-signal propagation + SSE `event.id` validation + test 钉 lazy-guard 防 regression)
> - ⚠️ [PR#4226](https://github.com/QwenLM/qwen-code/pull/4226) typed event schema 竞品 OPEN (doudouOUC, 2026-05-17 03:58, +1398/-18, 测试/生产 1.8x)；与 PR#4217 重叠，开 4 分钟后 PR#4217 即 MERGED；**待 close 或拆 SessionState reducer 部分作 Wave 5 PR 25 提前**
> - ✅ **Bonus** client adapter Stage 0 全 MERGED 2026-05-18：[PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) channel bridge (chiga0, 02:21, +2012) + [PR#4199](https://github.com/QwenLM/qwen-code/pull/4199) IDE connection (chiga0, 02:38, +1676) + [PR#4202](https://github.com/QwenLM/qwen-code/pull/4202) TUI adapter (chiga0, 03:22, +1970)；2026-05-19 后定位调整为 **default-off spike / future migration 参考**，不代表 native TUI/channel/IDE 默认迁 daemon
> - ⚠️ **Bonus** Stage 1/2 wire-up 调整：[PR#4260](https://github.com/QwenLM/qwen-code/pull/4260) TUI harness + [PR#4263](https://github.com/QwenLM/qwen-code/pull/4263) IDE Smoke Test **CLOSED 2026-05-18 06:59**；[PR#4261](https://github.com/QwenLM/qwen-code/pull/4261) channel `--daemon-url`、[PR#4266](https://github.com/QwenLM/qwen-code/pull/4266) `--experimental-daemon-tui`、[PR#4267](https://github.com/QwenLM/qwen-code/pull/4267) `qwen-code.experimentalDaemonIde` 与最新主线不再一致，应收口为 draft/closed 或只吸收可复用代码到 render-core / web-terminal 方向
> - ✅ **外部** `/demo` debug page [PR#4132](https://github.com/QwenLM/qwen-code/pull/4132) — **MERGED 2026-05-18 08:31** (jifeng, **远古 4 天 24 reviews 终于合**, 最终 +858/-3)；单 HTML browser-based debug UI 是 **Mode B POST+SSE 最薄 client 验证面**；XSS in `logEvent` `tag` 修：识别 `update.sessionUpdate.kind` / `event.type` 从 daemon SSE 上行是 daemon-controlled (而非 user-controlled) → 威胁模型扩到 daemon-emitted poisoned events 后 escape；rebase 过 PR#4247/4250/4251 冲突
> - ✅ Wave 5 **PR 22b/2 design slice** [PR#4304](https://github.com/QwenLM/qwen-code/pull/4304) `BridgeOptions` lift + `DaemonStatusProvider` seam — **MERGED 2026-05-19 01:27** (doudouOUC, **1h57m** open→merge, merge commit `68e3ec988a`，+852/-371 11 files；wenshao 1 轮 CHANGES_REQUESTED → 4 轮 inline 修 → qwen-latest /review LGTM → MERGED；**3-stage 改 4-stage**：原 PR 22b/2 implementation lift 拆为 22b/2 design slice (冻 contract) + 22b/3 mechanical bulk lift (~3000 LOC, 1-2h IDE-driven `git mv`)；6 design decision baked in JSDoc：positional 参 / 全 envelope 返 / 无 abort/timeout / 单接口含 2 方法 / 可选 + idle fallback / acpChannelLive 由 bridge 传参；2 文件移：`BridgeOptions` interface (~150 LOC) → `acp-bridge/src/bridgeOptions.ts` + `buildDaemonPreflightCells` + `safeCheck` (~210 LOC byte-identical) → `cli/src/serve/daemonStatusProvider.ts`；新 factory `createDaemonStatusProvider()`；**Mode A in-process consumer 可省 `statusProvider?` 不崩** —— 对齐 PR 12/13 "idle status is queryable"；701/701 vitest pass；**Wave 5 PR 22 现 3/4 MERGED，仅剩 22b/3 mechanical bulk lift**)
> - 🔧 Follow-up [PR#4305](https://github.com/QwenLM/qwen-code/pull/4305) #4291 post-merge fix（7 threads）— **OPEN + CHANGES_REQUESTED** 2026-05-18 23:50 (doudouOUC, +454/-116 5 files；qwen-latest review on **MERGED #4291** 后 7 项 hardening：① late-poll observer 解构原始字段不再持 entry/BrandedSecret/cancelController（**memory + secret retention**）② 抽 `callerIsDeviceFlowInitiator(view, callerClientId)` 共享 helper 3 处 inline copy 换掉（**DRY+回归预防**）③ timer fire `DeviceFlowPollTimeoutError` 单实例复用 abort.reason+reject（polish）④ `err.name` 走 `sanitizeForStderr`（**log injection 姊妹堵**与 `oauthError`）⑤ timeout 路径 audit hint 用 `result.hint` 与 SSE 一致 ⑥ inline `QWEN_SERVE_DEBUG` → 现有 `isServeDebugMode()` helper + `?? ''` 死代码删（DRY+dead code）⑦ late-rejection observer `name + length` 模式对称 provider catch 不再 slice 原 message（**secret leak**）；新测试 hard-negative-assert secret 不入 stderr + hostile `Error.name` sanitization；OAuth 史诗续：**+8032 LOC line if PR 21+#4291+#4305 全合**)
> - ✅ Follow-up [PR#4306](https://github.com/QwenLM/qwen-code/pull/4306) unbreak E2E after #4271（capabilities + clientCount）— **MERGED 2026-05-19 01:16** (doudouOUC, **41m 极短** — qwen-latest /review 一把 APPROVED merge commit `7daf616e8b`；+48/-40 2 文件 integration test only；**2 regressions** from PR#4271 MCP guardrail events 落地后 main E2E 每跑必挂：① capabilities envelope test 漏 `mcp_guardrail_events` tag —— **第 9th drift** 同 #4268/#4284 class；integration test hand-maintained list 是 unit baseline + production registry 之外**第三处 hand-maintained 数据源** → "三套" 实际是 4 套 ② `clientCount === pgrep_observed` 不再成立——ACP child 跑 **2 个 `Config` 对象**（`runAcpAgent` bootstrap + per-session `newSessionConfig` 各一）每个独立 `McpClientManager`；fix 把 `MCP_SERVERS_CONFIGURED * 2` 编码为 literal tripwire；**架构发现**：**double MCP discovery in ACP child** 真浪费 spawn cost —— 值得 #4175 follow-up gate bootstrap MCP behind daemon-mode flag 或 refactor `newSessionConfig` 共享 bootstrap `McpClientManager`)

详 [§06 Roadmap & Ecosystem](./06-roadmap.md)。

---

## 六、阅读指引

| 角色 | 推荐路径 |
|---|---|
| **想知道这是什么** | §01（本章）|
| **想知道何时 ship 什么** | §06 Roadmap |
| **想知道为什么这么设计** | §02 Design Decisions |
| **想集成 client** | §03 HTTP API → §04 Client Experience |
| **关心安全** | §05 Security & Permission |
| **商业平台集成方** | §06 §四 External Reference Architecture |

---

下一篇：[02 — Design Decisions →](./02-architectural-decisions.md)
