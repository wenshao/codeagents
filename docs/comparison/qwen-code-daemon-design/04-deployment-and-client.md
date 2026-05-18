# 04 — Deployment & Client Experience

> [← 上一篇：HTTP API & Protocol](./03-http-api.md) · [下一篇：Security & Permission →](./05-permission-auth.md)

## TL;DR

**2026-05-15 更新**：先忽略 Mode A（`qwen --serve`），以 **Mode B `qwen serve`** 作为唯一主线。TUI / channels / web / IDE 都应作为 daemon HTTP/SSE client 接入；EventBus 是 daemon 内部 fan-out primitive，client 共享的是 typed event contract + reducer + `DaemonSessionClient`，不是直接订阅内存 EventBus。

**多 client 协调**（P1 拓扑）：subscriber 协议 + liveness（15s SSE heartbeat + TCP RST 即时剔除）+ active typer 提示 + takeover + first-responder permission。

**Deployment shapes（Mode B）**：runtime 维度仍是 Local-Local / Local-Remote（**不推荐**）/ Remote-Remote（**推荐**，workspace 与 daemon 同机）；client 维度进一步拆成 local-local、web chat/terminal-remote、local IDE-local daemon、local TUI-remote、channel+daemon、remote-control overlay。Web terminal 的目标是 **daemon-native renderer**（typed event + reducer），PTY proxy 只作为兼容 / demo / debug fallback。Client Capability 反向 RPC（5 类：editor / clipboard / browser / notification / file_picker）让 daemon 调起 client 本地资源——属 External Reference Architecture 范畴。

---

## 一、部署模式

| 模式 | 启动命令 | TUI | 适用场景 |
|---|---|---|---|
| **Mode B: Headless + HttpServer** | `qwen serve [--port N]` | ❌ | 当前主线：服务器 / 容器 / 远端机器 / 所有 client 的统一 runtime |
| **Mode A: CLI + HttpServer** | `qwen --serve [--port N]` | ✅ 本地 | 暂停推进；parking lot |

当前主线只有 Mode B。详 [§02 §7](./02-architectural-decisions.md#7-部署模式--mode-b-mainline--mode-a-parking-lot)。

### Mode B 拓扑核心特征

- 无 in-process TUI client；所有 client 全走 HTTP/SSE。
- 进程没有终端；通过 systemd / pm2 / Docker 后台运行。
- 重启策略由进程管理器决定；session 通过 PR#3739 transcript-first fork resume 重建，HTTP `loadSession` / `resume` 仍待 Stage 1.5a must-haves 暴露。
- `GET /session/:id/events` 是 daemon 内部 EventBus 的 SSE projection；client 不直接 import EventBus。

### Client 接入顺序

> 这里的顺序不是 upstream Stage 1.5 的 P0/P1/P2 foundation 优先级。P0 foundation 仍是 must-haves + daemon-side state CRUD；下表只描述各 client behind-flag 试点的先后。

| 顺序 | Client | 适配方向 |
|---|---|---|
| 第一波 | TUI | attach-to-daemon render target；HTTP/SSE + shared reducer — 实施 spike 详 [PR#4202](https://github.com/QwenLM/qwen-code/pull/4202) `feat(tui): add daemon adapter spike` (+864 LOC) |
| 第一波 | channels | 新 daemon transport，保留 channel routing — 实施 spike 详 [PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) `feat(channel): add daemon bridge spike` (+813 LOC) |
| 第一波 | web/debug | [PR#4132](https://github.com/QwenLM/qwen-code/pull/4132) `/demo` 作为最薄验证面 + [PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) channel/web BFF 共用安全边界 |
| 第二波 | IDE | daemon transport behind flag — 实施 spike 详 [PR#4199](https://github.com/QwenLM/qwen-code/pull/4199) `feat(ide): add daemon connection spike` |
| 并行 | JSONL / stream-json / dual-output | daemon event sinks |
| P2 deferred | remote-control | 后置；作为 daemon facade / control overlay，不意味着 daemon 必须远端 |

> 📌 **chiga0 把 docs drafts 升级为 implementation spikes**（2026-05-16 ~08:00）：原 docs-only PR#4196 (TUI) / #4197 (channel) / #4198 (IDE) 已 CLOSED，改为 [PR#4202](https://github.com/QwenLM/qwen-code/pull/4202) (TUI +864 LOC) / [PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) (channel +813 LOC) / [PR#4199](https://github.com/QwenLM/qwen-code/pull/4199) (IDE) **implementation spikes**——把设计文档与代码 spike 放同 PR，避免文档与实现脱节。

### Channel / Web BFF 适配安全边界（[PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) 摘要）

> chiga0 [PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) `feat(channel): add daemon bridge spike` 在 `@qwen-code/channel-base` 内引入 `DaemonChannelBridge`，让 channel bot + web chat backend 接入 Mode B 的 server-side-only 适配。**关键安全边界**：

```
✅ ALLOWED:
   Channel bot backend  → qwen serve                (server-side direct)
   Browser → Web BFF → qwen serve                   (server-side BFF only)

❌ DENIED:
   Browser → qwen serve direct                      (daemon rejects browser Origin)
```

**核心 invariant**：browser **永远不直接** call daemon；daemon bearer token **永远不进入 browser/frontend code**。这是 daemon Origin 拒绝策略的合理推论。

**Proposed entry points**：

```bash
# Channel
QWEN_CHANNEL_DAEMON_URL=http://127.0.0.1:4170 qwen channel start telegram

# Web backend (BFF)
QWEN_WEB_DAEMON_URL=http://127.0.0.1:4170 qwen web-chat-backend

# Shared
QWEN_DAEMON_TOKEN=...
QWEN_DAEMON_WORKSPACE=/repo
```

### Session isolation constraint（重要安全 guidance）

> ✅ **2026-05-16 update**：per-request `sessionScope` 已 ship — Wave 2 PR 5 [PR#4209](https://github.com/QwenLM/qwen-code/pull/4209) MERGED。channel/web BFF 现在可在 `POST /session` body 携带 `sessionScope: 'thread'` 主动声明 strict isolation；无效值 `400 invalid_session_scope`；新 capability tag `session_scope_override` 暴露在 `/capabilities.features`，client 可 preflight 后再发字段。Review 还修了一个 mixed-scope leak（thread-first 后省略-scope 调用 attach 到隔离 session 的 bug），强烈推荐升级。

历史 Stage 1 daemon 只有 daemon-wide `sessionScope: 'single'`，无 override 路径。**Pre-PR#4209 时代多 user channel / web 部署需三选一**（保留作部署历史参考；现在用 per-request override 即可）：

| 选项 | 含义 |
|---|---|
| 1 daemon per channel thread / web room | 每个会话独立 daemon 进程 |
| 1 daemon per user workspace | 1 user 共享同 daemon 内多 session（合理 trust 域）|
| single-user demo only | 仅原型 / 验证 |

⚠️ **Do NOT silently multiplex unrelated channel threads into one daemon session** —— 避免不同用户 conversation context 污染 / 隐私越界。

### Event mapping contract（[PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) 7 events → channel/web actions）

| Daemon SSE event | Channel/web backend 处理 |
|---|---|
| `session_update` / `agent_message_chunk` | Append assistant 文本 |
| `session_update` / `agent_thought_chunk` | Optional hidden/debug stream |
| `session_update` / `tool_call` | Emit tool status card / message |
| `permission_request` | Platform-specific approval interaction |
| `permission_resolved` | Close / update approval |
| `model_switched` | Update backend session metadata |
| `session_died` | Notify user + stop stream |
| **Unknown events** | **Ignore or forward as debug, NOT fatal** |

### 5 Blockers before channel/web default migration

[PR#4203](https://github.com/QwenLM/qwen-code/pull/4203) 明确：channel / web client 默认切换 daemon 前必须先 ship 以下 5 项（全部来自 [Issue #4175](https://github.com/QwenLM/qwen-code/issues/4175) Wave 2-3）：

| # | Blocker | 对应 PR | 状态（2026-05-18）|
|---|---|---|---|
| 1 | Per-request `sessionScope` | Wave 2 PR 5 | ✅ MERGED [PR#4209](https://github.com/QwenLM/qwen-code/pull/4209) |
| 2 | Session metadata + close/delete lifecycle | Wave 2.5 PR 11 | ✅ MERGED [PR#4240](https://github.com/QwenLM/qwen-code/pull/4240) |
| 3 | Daemon-stamped client identity | Wave 2 PR 7 | ✅ MERGED [PR#4231](https://github.com/QwenLM/qwen-code/pull/4231) |
| 4 | Session-scoped permission route | Wave 2 PR 8 | ✅ MERGED [PR#4232](https://github.com/QwenLM/qwen-code/pull/4232) |
| 5 | Read-only diagnostics for MCP / skills / providers / environment | Wave 3 PR 12 / 13 / 14 | ✅ MERGED [PR#4241](https://github.com/QwenLM/qwen-code/pull/4241) / [#4251](https://github.com/QwenLM/qwen-code/pull/4251) / [#4247](https://github.com/QwenLM/qwen-code/pull/4247) |

详 [§06 §三·一 Wave 2-3](./06-roadmap.md#wave-2--session-lifecycle--minimum-multi-client-safety)。

### Channel/Web Explicit non-goals（PR#4203 列出）

- ❌ Browser direct-to-daemon fetch / EventSource
- ❌ CORS relaxation in adapter PR
- ❌ Default migration of Telegram / Weixin / Dingtalk / plugin channels
- ❌ File CRUD / memory CRUD / MCP restart / provider mutation（Wave 4 范围）
- ❌ Client-side `sessionScope` emulation（daemon 端 Wave 2 PR 5 已 ship — [PR#4209](https://github.com/QwenLM/qwen-code/pull/4209)，client 直接在 `POST /session` body 携带 `sessionScope` 字段即可）

---

## 二、TUI / client 边界

Stage 1 的 Mode B client 只能覆盖 conversation 主链路。要让 TUI / channels / web / IDE 成为完整 client，需要先补 P0 的 production must-haves 与 daemon-side control-plane parity，再补 P1 typed event contract / bridge primitives；client adapters 只能先 behind flag。

### TUI 形态 4 种

| TUI 形态 | 数据源 | 完整 dialog 支持 |
|---|---|---|
| 传统单进程（`qwen`）| in-process direct call | ✅ super-client（~15 Ink dialogs + local-jsx）|
| **Mode B + TUI adapter** | HTTP/SSE via `DaemonSessionClient` | ⚠️ Stage 1: 仅 conversation；Stage 1.5c 后补齐 daemon state |
| **Mode B + 远端非-TUI client**（Web UI / mobile / IM bot）| HTTP/SSE | N/A — 非 Ink 渲染 |
| **Mode A 本地 TUI**（`qwen --serve`）| in-process | ⏸ HOLD |

### TUI 与 wire 的边界 — 9 项 dialogs 真实成本

| Dialog | 真的不能 wire 化？ | Wire 化方案 | 工作量 | 当前 |
|---|---|---|---|---|
| `/memory` 编辑 | ❌ 完全可以 | `GET/POST /workspace/memory` 读写 `~/.qwen/memory.json` | ~0.5d | Stage 1.5c |
| `/mcp` 启停 / 配置 | ❌ 完全可以 | `GET /workspace/mcp` + `POST /workspace/mcp/:server/restart` | ~1d | Stage 1.5c |
| `/agents` 管理 | ❌ 完全可以 | `GET/POST /workspace/agents` — 参考实现详 [Claude Code `/agents` Deep-Dive](../claude-code-agents-command-deep-dive.md)（~3042 LOC 完整范本）| ~0.5d | Stage 1.5c |
| `/tools` 启停 | ❌ 完全可以 | `POST /workspace/tools/:name/enable` | ~0.5d | Stage 1.5c |
| `/approval-mode` 切换 | ❌ 完全可以 | `POST /session/:id/approval-mode` | ~0.5d | Stage 1.5c |
| `/init` 项目初始化 | ❌ 完全可以 | `POST /workspace/init` | ~0.5d | Stage 1.5c |
| `/resume <id>` 切换 session | ❌ Stage 1.5 must-have #2 已规划 | `POST /session/:id/load` | Stage 1.5a must-haves | ✅ 计划 |
| `/auth` OAuth 登录 | ⚠️ 部分难点 | device-flow 或 Capability RPC | ~2-3d | Stage 1.5c |
| `/ide` IDE 集成 | ⚠️ 语义模糊 | "IDE 在哪台机器？" | TBD | TBD |
| `ModelDialog` 选 model | ✅ 已 wire 化 | `POST /session/:id/model` + `model_switched` event | — | Stage 1 ✓ |
| `SessionPicker` 列 session | ✅ 已 wire 化 | `GET /workspace/:id/sessions` | — | Stage 1 ✓ |

**结论**：6/9 项 ~0.5d；2/9 项有 IPC 难点但 Capability RPC 可解；1/9 项语义模糊。它们归入 [§06 Stage 1.5c state CRUD](./06-roadmap.md#15c--daemon-side-state-crud--control-plane-parity)。

> 💡 **`/agents` 参考实现**：Claude Code `/agents` slash command 已 ship 完整 ~3042 LOC 的 7-mode 状态机 + 11-step wizard + AI 生成 agent + 6 source 分层——是 daemon-side state CRUD 的最佳设计 anchor。详 [**Claude Code `/agents` UI Deep-Dive**](../claude-code-agents-command-deep-dive.md)（含 P0/P1 借鉴项：`omitClaudeMd` 省 ~5-15 Gtok/周 / `criticalSystemReminder_EXPERIMENTAL` 每 turn 重注入 / `isolation: worktree` agent 隔离 / AI 生成 agent 等）。

### 同行竞品对标

| 工具 | 远端 UI 完整访问 daemon-side state |
|---|---|
| Cursor | ✅ |
| Continue.dev | ✅ |
| Claude Code | ✅ |
| OpenCode | ✅ |
| Gemini CLI daemon | ✅ |
| **Qwen Code Stage 1**（current）| ❌ 离群点（thin shell only）|
| **Qwen Code Stage 1.5c 后** | ✅ 对齐（除 `/auth` `/ide` 部分场景）|

### 远端 client Attach / Reconnect 状态恢复

| # | 要点 | 详情 |
|---|---|---|
| 1 | **Attach / reconnect 必须 re-fetch state** | 用 `Last-Event-ID: 0` 重放 `model_switched` 等终态 event 拿当前 model；`/capabilities` 拿终态 |
| 2 | **不假设 TUI mutations 通过 event 推送** | `/approval-mode` / `/memory` / `/mcp` / `/agents` / `/tools` 等应视为 **opaque server state** |
| 3 | **每次 reconnect 后视为 cold state** | 除 conversation 主流，其他状态应当作 unknown |

### Mode A parking lot

Mode A `qwen --serve` 设计暂时 hold。本节保留原问题作为 future evaluation checklist：如果未来重新推进 Mode A，必须先回答 TUI 绑定哪个 daemon session、TUI local mutations 如何进入 typed event contract、TUI 退出是否带走 daemon 等问题。

| 问题 | 当前处理 |
|---|---|
| TUI 是否同进程 co-host daemon | HOLD |
| TUI 是否绑定一个 session 还是 attach 任意 session | HOLD |
| TUI local dialogs 是否 wire 化 | 先通过 Mode B control-plane parity 解决 |
| TUI 是否可作为纯 daemon client | **优先 behind flag 试点**：Stage 1.5c TUI adapter；默认切换等 P0/P1 |

---

## 三、多 Client 协调（P1 拓扑）

> 决策 §1 + §6 让一个 session 可被多 client 同时订阅；本节定义这些 client 如何协调。本节聚焦 **P1 拓扑（multi-end sync）**；P2 拓扑（IDE multi-window）由 daemon HTTP layer 在 session 边界隔离，不涉及本节协议。

### 设计目标

| 维度 | 默认 | 可选（企业）|
|---|---|---|
| Subscriber 数量 | default maxTotal=20 防滥用 | tenant config 调整 |
| 同类型多个（CLI×N / WebUI×N）| ✓ 允许 | exclusive_per_type 模式拒绝 |
| Liveness（Stage 1）| server-push 15s SSE keepalive + TCP RST 即时剔除 | 同 |
| Liveness（Stage 2+）| + 90s heartbeat 超时兜底 + 子连接超时差异化 | 弱网调 30/60s |
| Active Typer 协调 | "X is typing..." 提示 + 5s 让出 | 同 |
| Takeover | 显式 `--takeover` flag | 同 |
| Exclusive 模式 | ✗ | tenant config 启用 |
| IM bot 多用户 | im_bot kind 单独配额 5 | 可调 |

**总指导原则**：**协调 > 排斥**（live collaboration first）。

### Subscriber 协议

```typescript
// daemon 维护
sessionSubscribers: Map<sessionId, Set<SubscriberInfo>>

interface SubscriberInfo {
  clientId: string;
  kind: 'cli' | 'web' | 'ide' | 'im_bot' | 'mobile' | 'tui';
  joinedAt: number;
  lastHeartbeat: number;
  isActive: boolean;     // 5s 内有 input
}
```

### Liveness 协议（Stage 1 子集已实现，commit `41aa95094`）

| 机制 | Stage 1 | Stage 2+ |
|---|---|---|
| server-push 15s SSE keepalive | ✅ | ✅ |
| AbortController on `req.close` 即时剔除 | ✅ | ✅ |
| bounded subscriber queues + `client_evicted` overflow | ✅ | ✅ |
| client-POST heartbeat | ❌（Stage 1.5 must-have #4）| ✅ |
| 90s 超时兜底 + SessionCleaner | ❌ | ✅ |
| 子连接超时差异化（mobile 5min / web 1h / cli infinite）| ❌ | ✅ |

### Active typer 协调（Stage 2+）

```
T=1   Alice 开始打字 (cli-laptop)
T=2   Bob 在 web 上看到 "Alice is typing..."
T=3   Alice 提交 prompt P1 → FIFO[P1]，执行中
T=5   Bob 在 cli-desktop 提交 prompt P2 → FIFO[P1, P2]（排队）
T=7   Alice 看到 "Bob queued"
T=10  P1 完成 → P2 开始
```

### Takeover 流程（Stage 2+）

```
T=1   Alice 在远程 cli 跑长任务，连接掉线（笔记本关盖）
T=10  daemon 检测 Alice subscriber timeout，标 stale
T=15  Bob 在 web 接入同 session，看到 "Alice is offline. Take over?"
T=20  Bob 点 takeover → daemon 把 active typer 转给 Bob
T=25  Alice 笔记本醒来重连 → daemon 通知 "Bob 接管了"
```

### 多 client 同 session 同 prompt 队列

任何 client（含 TUI）都能：
- 发 prompt → 同 session 串行 FIFO，第二个挂起等
- 应答 permission_request → first-responder wins
- 取消 → `POST /session/:id/cancel`
- 设置 model / mode → 立即生效，所有 client 收到通知

详 [§02 §6 多 client 并发](./02-architectural-decisions.md#6-多-client-并发请求)。

---

## 四、远端 CLI 模式（Mode B 拓扑）

> 远端 client 直连 daemon URL + Bearer token + SSE 重连是 PR#3889 Stage 1 已实现的基础链路。下面其余设计（Client Capability 反向 RPC / mTLS / NAT 穿透 / Local echo / 离线降级）属 **External Reference Architecture** 范畴——Stage 1 不实现，仅作外部集成方蓝图。

### 3 类拓扑

> 这是 **workspace/runtime locality lens**。更细的 client UI / adapter 部署形态见下一节 deployment shape matrix。

| 拓扑 | workspace 位置 | daemon 位置 | 适用 |
|---|---|---|---|
| **A. Local-Local** | 本机 | 本机 | 单人开发（最常见），Stage 1/1.5/2 默认 |
| **B. Local-Remote** | 本机 | 远端 | ❌ **不推荐** — daemon 看不到本地 fs，必须 mount fs to remote 或 sync，运维复杂 |
| **C. Remote-Remote**（**推荐**）| 远端 | 远端 | 类比 GitHub Codespaces / Coder；workspace 与 daemon 同机 = 不跨网络 fs |

### Deployment shape matrix（client/runtime lens，2026-05-18）

> 来源：chiga0 [Issue #3803 comment 4476318030](https://github.com/QwenLM/qwen-code/issues/3803#issuecomment-4476318030)。关键不变式：**runtime capabilities follow the daemon/runtime host, not the visual client**。对 remote-control 来说，"remote" 指 control entrypoint 可远端，不表示 daemon/runtime 必须远端。

| Shape | Client / adapter | Daemon + runtime | Workspace | 主要要求 | 推荐阶段 |
|---|---|---|---|---|---|
| **1. Local - Local** | local TUI / IDE / local web / channel adapter | 本机 loopback `qwen serve` | 本机 | auto-daemon discovery / loopback auth / lifecycle / port+token+logs；control-plane parity；TUI 渲染不能 raw event spam | 现有用户默认迁移目标 |
| **2. Web chat / web terminal - Remote** | browser UI | remote devbox / pod | remote volume | gateway/auth/CORS；SSE reconnect；runtime diagnostics；web terminal 走 daemon-native renderer，PTY proxy 仅 fallback | cloud/devbox P1 |
| **3. Local IDE - Local daemon** | IDE extension | 本机 loopback daemon | IDE 当前 workspace | IDE 启动/发现 daemon；workspace mismatch preflight；editor context 显式传入；path identity 共享 | P1 early dogfood |
| **4. Local TUI - Remote** | 本地 terminal renderer | remote daemon/runtime | remote workspace | TUI 明示 remote label/path/auth；local cwd 非 runtime cwd；path mapping / client capability reverse RPC；latency coalescing | P1 after TUI adapter quality |
| **5. Channel + daemon** | IM/channel backend adapter | local 或 remote daemon | daemon-bound workspace | user/group/thread → session routing；identity mapping；permission cards；dedupe；长任务通知 | P1 behind flag |
| **6. Remote-control overlay** | web/mobile/channel control surface | local daemon + bridge 或 remote daemon + gateway | local workstation 或 remote devbox | pairing/revoke；outbound bridge；audit；不 fork runtime/protocol | P2 after client contract stabilizes |

#### Web terminal：daemon-native renderer，不是 PTY proxy 主线

Web chat 和 web terminal 都应消费 daemon typed events / reducer。差异只在 UI 呈现：chat UI 用 DOM chat renderer，web terminal 用 terminal-like renderer。TUI adapter 已经是在做 Ink/terminal 版的 **daemon-native renderer**；web terminal 应复用同一 contract。

PTY proxy 仍可作为兼容 / demo / debug fallback，但不能成为目标架构：它代理 terminal bytes，会重新耦合进程生命周期，并绕开 typed event / reducer convergence。

#### Channel + local daemon 是合法 remote-control 形态

用户可以在个人 workstation 上跑 `qwen serve`，再通过 DingTalk / WeChat / Telegram 从手机控制本机 workspace。此时 channel input 是 remote，daemon/runtime/workspace 仍是 local。这与"local workspace + remote daemon"不同，后者不推荐，因为远端 daemon 看不到本地文件、MCP、skills 和环境。

#### Remote-control overlay 两种形态

```text
6A local workspace + local daemon + remote-control relay
remote UI → relay / IM / websocket broker
  → local bridge on user's workstation
  → local qwen serve on loopback
  → local workspace/runtime

6B remote workspace + remote daemon + remote-control UI
remote UI → gateway / web backend
  → remote qwen serve
  → remote workspace/runtime
```

两者都应复用 `DaemonSessionClient` + HTTP/SSE typed event contract。区别是部署和 routing，不是新 runtime protocol。

#### Client PR review guidance

每个 client adapter / wire-up PR 应在 PR 描述里声明：

- 验证的 deployment shape（例如 local-local、local TUI-remote、channel+local daemon）。
- daemon/workspace/client locality 假设。
- 是否 behind flag / default off。
- 对 control-plane parity、path mapping、runtime diagnostics、client-local capability 的依赖。
- 本地手动验证方式，以及是否会影响现有非 daemon 主链路。

### 拓扑 C — Remote-Remote（推荐）

```
Laptop                           Remote workstation
├─ qwen CLI (--remote-url xxx)   ├─ Workspace /work/repo
└─ Editor (Ink TUI render)       ├─ qwen daemon (qwen serve --hostname 0.0.0.0)
                                  └─ MCP / LSP / Bash 都在远端跑
        ─ HTTP/SSE (TLS+Bearer) ─→
```

**适用**：远程开发机（VPS / 云 dev box）+ 团队多人协作 / 容器化 SaaS。

### Stage 演进表

| 阶段 | 远端 TUI 体验 | 部署建议 |
|---|---|---|
| **Stage 1**（current）| thin shell（仅 conversation + model_switch）| 可做原型；默认体验仍受限 |
| **Stage 1.5c + 1.5-prereq 后** | typed event + daemon state/control-plane 补齐 | 多端协作 / 容器化 SaaS / 远端 dev box 都可用 |

### 完整 TUI 体验 + 远程访问选项

| 选项 | 部署 | TUI 体验（Stage 1）| TUI 体验（Stage 1.5c + 1.5-prereq 后）|
|---|---|---|---|
| **A. SSH + 单进程** | SSH 进远端机器跑 `qwen` | ✅ 完整本地 TUI | ✅ 完整 |
| **B. Mode B + 远端 TUI client** | 远端 `qwen serve` headless，本地用 TUI adapter attach | ⚠️ thin shell | ✅ **接近完整**（除 `/ide` 等场景）|
| **C. Mode A** | `qwen --serve` | ⏸ HOLD | 待重新评估 |

---

## 五、Runtime locality / environment contract

> 来源：chiga0 [Issue #3803 comment 4458840712](https://github.com/QwenLM/qwen-code/issues/3803#issuecomment-4458840712)（2026-05-15）+ [comment 4476174099](https://github.com/QwenLM/qwen-code/issues/3803#issuecomment-4476174099)（2026-05-18 强化）。Mode B 下 **daemon 是 runtime owner**——MCP / Skills / shell / LSP / tool execution / provider auth / file access 全部在 **daemon host / pod** 上 evaluate，不在 client 机器。这一约束**必须显式 documented**，避免远端 client 误以为自己的 local network / files / tools 仍然适用。
>
> **2026-05-18 升级**：此 invariant 已从 "runtime locality contract" 提升为 **deployment model 一部分**——详 [§01 §三·一 Deployment forms](./01-overview.md#三一-deployment-forms来自-chiga0-3803-comment-4476174099-2026-05-18) 3-form 表（**local-local 主装** / **cloud-remote daemon 与 workspace colocate** / **local workspace + remote daemon ❌ 不推荐**）+ [§06 §三·二 Package boundary contract](./06-roadmap.md#三二-deployment--package-contract-chiga0-3803-comment-2026-05-18)。

### Daemon 拥有的 runtime 资源

```
┌────────────────────────────────────────────────────────┐
│ daemon host / pod                                       │
│   ├─ filesystem (skills / CLAUDE.md / settings)        │
│   ├─ network (MCP HTTP/SSE / provider API)             │
│   ├─ process execution (shell / LSP / MCP children)    │
│   ├─ credentials (OAuth tokens / API keys)             │
│   ├─ env vars (cloud CLIs / docker / kubeconfig)       │
│   └─ Unix sockets / SSH agent / browser profile        │
└────────────────────────────────────────────────────────┘
              ↑ HTTP/SSE
              │
   ┌──────────┴───────────┐
   │  client (TUI / web / │  ← 不拥有 runtime；只渲染 + 发 prompt + 应答 permission
   │  IDE / channels)     │
   └──────────────────────┘
```

### 5 项具体含义

| # | 含义 | 例子 |
|---|---|---|
| 1 | **stdio MCP servers** 在 daemon host spawn | daemon host 必须有 `node` / `uv` / `python` / docker CLI / cloud CLIs + env vars / secrets / files |
| 2 | **HTTP/SSE MCP servers** 从 daemon host 访问 | daemon host/pod 需要 outbound egress 到 MCP endpoints 及其调用的 API/databases |
| 3 | **本地资源** (`localhost` / Unix sockets / mounted volumes / kubeconfig / SSH agent / browser profile) | 全是 **daemon host 本地**，不是 client |
| 4 | **Personal skills** (`~/.qwen/skills`) / **project skills** (`.qwen/skills`) / **extension skills** | 必须在 **daemon filesystem**；client local skills **不会**自动可见，除非未来通过 sync / mount / install / control-plane push |
| 5 | **锁定 VPC/pod 无 egress** | SaaS MCP discovery/init 或 tool calls 失败，除非网络策略允许 |

### 这不意味着 "daemon 必须开放公网"

- daemon 只需要 **configured providers / MCP servers / skills 实际所需的** network surface
- **生产推荐**：deny-by-default egress + explicit allowlist
- 但**必须明确**：client 端连得通不等于 daemon 端连得通——daemon-side runtime 必须能 reach configured services

### 部署 preflight / 诊断（Stage 1.5c 新增）

为了让远端 client 看到 actionable failures 而非"silent loss of tools"，Stage 1.5c daemon-side state CRUD 必须在 status routes 中返回详细错误信息：

| Route | 必须返回 |
|---|---|
| `GET /workspace/mcp` | 每个 MCP server：`status` + `error` + `errorKind`（missing binary / blocked egress / auth/env error / init timeout / protocol error）|
| `GET /workspace/skills` | 每个 skill：`loaded` + `error`（missing file / parse error / required binary not found）|
| `GET /workspace/preflight`（**新增 route**）| daemon 启动 + 配置 readiness 整体检查：providers / MCP / skills / required binaries / egress 检测 |
| `GET /workspace/env`（**新增 route**）| daemon host 关键环境信息：可用 binaries / env vars（masked secrets）/ filesystem mount points / 网络可达性摘要 |

### Reverse RPC scope（与 runtime locality 关系）

[§六 Client Capability 反向 RPC](#六client-capability-反向-rpc) 的 5 类 capability（`editor` / `clipboard` / `browser` / `notification` / `file_picker`）是**显式 delegated 给 client-local 资源**的特定能力——**不是** MCP / skill / shell execution 的 general fallback。

| 用例 | 走 reverse RPC？ |
|---|:---:|
| daemon 让 client 打开 editor 编辑文件 | ✅ `open_editor` |
| daemon 让 client 读 clipboard 内容 | ✅ `clipboard` |
| daemon 用 client 本地的 docker CLI 跑 MCP server | ❌ **不**——MCP 必须在 daemon 上 |
| daemon 用 client 本地的 `~/.qwen/skills` | ❌ **不**——skills 必须在 daemon filesystem |

未来若要允许 client-side MCP / skill 兜底，需要**独立设计**（不在当前 Client Capability scope 中）。

---

## 六、Client Capability 反向 RPC（External Reference Architecture）

> daemon 不直接拥有 client 本地资源（editor / clipboard / browser / notification / file_picker），但 agent 有时需要"调起 client 本地能力"。设计 5 类 Client Capability 反向 RPC 协议，让 daemon 通过 SSE event 反向调用 client，client 通过 HTTP callback 回复。
>
> **Scope 限定**（详 [§五 Runtime locality](#五runtime-locality--environment-contract)）：5 类 capability 是显式 delegated 给 client-local 资源的能力，**不是** MCP / skill / shell execution 的 general fallback。

### 协议结构

```
1. agent 内代码: client.openEditor({path: '/work/foo.py', line: 42})
2. daemon → SSE event: { type: 'capability_request', requestId: 'r1', capability: 'open_editor', params: {...} }
3. client (CLI) 收 SSE event → 本地 spawn editor (`code -g foo.py:42`)
4. client → daemon: POST /capability/r1 { status: 'ok' }
5. daemon → agent 内代码: 返回 { status: 'ok' }
```

### 5 类 Capability 设计

| Capability | 用途 | client 端实现 |
|---|---|---|
| `open_editor` | 在 client 本地打开文件 / 跳转行号 | spawn `code` / `vim` / `subl` 等 editor 子进程 |
| `clipboard` | 读 / 写 client 本地剪贴板 | xclip / pbcopy / clip.exe |
| `open_browser` | 在 client 本地浏览器打开 URL | `open` / `xdg-open` / start |
| `notification` | client 本地 system notification | osascript / notify-send / Windows toast |
| `file_picker` | client 本地文件选择 dialog | TUI Ink dialog / OS native dialog |

### Client 不支持时的兜底

```
1. client 启动时通过 capability registration 告诉 daemon 它支持哪几类
2. daemon 收 capability_request 时按 client 的支持列表选 fallback：
   - 多 client 同 session：优先发给"支持该 capability 的 client"
   - 没人支持：返回错误码给 agent，agent 用 LLM-based fallback（提示用户手动操作）
```

详细设计 / TLS / mTLS / Sticky cookie HMAC / NAT 穿透方案 / Local echo / 离线降级 属 **External Reference Architecture** 范畴。

---

## 七、与 PR#3929-3931 (remote-control stack) 的关系

2026-05-15 决策后，remote-control 优先级后置。它仍然可以作为 mobile/browser/channel control overlay 存在，但不应继续拥有 parallel runtime / event log / worker server。正确方向是等 TUI / channels / web / IDE 先收敛到 Mode B daemon contract 后，remote-control 再复用同一 `DaemonSessionClient` + HTTP/SSE typed event contract。

**重要澄清（2026-05-18）**：remote-control 不要求 daemon 必须在远端。它至少有两种有效部署形态：

| 形态 | Runtime / workspace | Control entrypoint | 说明 |
|---|---|---|---|
| **Local daemon + remote-control relay** | 用户 workstation 本机 | web/mobile/channel 远端入口 → relay → local bridge | Codex / Claude Code-like；保留本机 workspace、git state、MCP、skills、provider env；local daemon 可保持 loopback-only |
| **Remote daemon + remote-control UI** | remote devbox / pod | web/mobile/channel → gateway | SaaS / devbox；workspace 生命周期、tenant isolation、quota、audit 由平台负责 |

第一种不是"local workspace + remote daemon"反模式；workspace/runtime 没有离开本机，只有控制入口远端化。

PR#3929-3931 当前仍是 draft / changes requested。简表：

| 维度 | Mode B daemon mainline | PR#3929-3931 stack |
|---|---|---|
| 入口 | `qwen serve` + client adapters | `qwen remote-control` worker / `qwen --remote-control` attach |
| 传输 | HTTP + SSE（Stage 2 可选 WebSocket facade）| HTTP + WebSocket + stream-json + dual-output JSONL |
| 协议复用 | 100% 复用 ACP zod schema | 复用 dual-output + stream-json 包装 |
| session 模型 | 1 daemon = 1 workspace × N session multiplexed | Worker server spawn / attach 当前 TUI |
| 多 client 共 session | ✅ live collaboration + first-responder | ⚠️ mobile/browser attach 同 session 但首要场景单 mobile + 当前 TUI 双视图 |
| Mobile / browser UI | 先由 web/debug + IDE/TUI adapters 定 contract | ✅ 自带最小化 mobile/browser UI（PR#3930 +2564 行）|
| Pairing token + LAN URL | ❌ 仅 bearer token | ✅ 一次性 pairing token + LAN URL 报告 |
| Capability 反向 RPC（5 类）| ✅ editor / clipboard / browser / notification / file_picker | ❌ 无反向 RPC——permission approve/deny 通过 stream-json 直接路由 |
| 2026-05-15 处理 | 主线；优先 TUI / channels / web / IDE | 后置；未来应改为 daemon facade |

---

下一篇：[05 — Security & Permission →](./05-permission-auth.md)
