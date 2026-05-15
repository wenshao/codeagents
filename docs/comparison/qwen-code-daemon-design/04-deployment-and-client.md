# 04 — Deployment & Client Experience

> [← 上一篇：HTTP API & Protocol](./03-http-api.md) · [下一篇：Security & Permission →](./05-permission-auth.md)

## TL;DR

**2026-05-15 更新**：先忽略 Mode A（`qwen --serve`），以 **Mode B `qwen serve`** 作为唯一主线。TUI / channels / web / IDE 都应作为 daemon HTTP/SSE client 接入；EventBus 是 daemon 内部 fan-out primitive，client 共享的是 typed event contract + reducer + `DaemonSessionClient`，不是直接订阅内存 EventBus。

**多 client 协调**（P1 拓扑）：subscriber 协议 + liveness（15s SSE heartbeat + TCP RST 即时剔除）+ active typer 提示 + takeover + first-responder permission。

**远端 CLI（Mode B）**：3 类拓扑 — Local-Local（本机）/ Local-Remote（混合，**不推荐**）/ Remote-Remote（**推荐**，workspace 与 daemon 同机）。Client Capability 反向 RPC（5 类：editor / clipboard / browser / notification / file_picker）让 daemon 调起 client 本地资源——属 External Reference Architecture 范畴。

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
| 第一波 | TUI | attach-to-daemon render target；HTTP/SSE + shared reducer |
| 第一波 | channels | 新 daemon transport，保留 channel routing |
| 第一波 | web/debug | [PR#4132](https://github.com/QwenLM/qwen-code/pull/4132) `/demo` 作为最薄验证面 |
| 第二波 | IDE | daemon transport behind flag，先覆盖 session/prompt/events/cancel/model |
| 并行 | JSONL / stream-json / dual-output | daemon event sinks |
| P2 deferred | remote-control | 后置；primary clients 收敛后作为 daemon facade |

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
| `/agents` 管理 | ❌ 完全可以 | `GET/POST /workspace/agents` — 参考实现详 [Claude Code `/agents` Deep-Dive](../claude-code-agents-view-deep-dive.md)（~3042 LOC 完整范本）| ~0.5d | Stage 1.5c |
| `/tools` 启停 | ❌ 完全可以 | `POST /workspace/tools/:name/enable` | ~0.5d | Stage 1.5c |
| `/approval-mode` 切换 | ❌ 完全可以 | `POST /session/:id/approval-mode` | ~0.5d | Stage 1.5c |
| `/init` 项目初始化 | ❌ 完全可以 | `POST /workspace/init` | ~0.5d | Stage 1.5c |
| `/resume <id>` 切换 session | ❌ Stage 1.5 must-have #2 已规划 | `POST /session/:id/load` | Stage 1.5a must-haves | ✅ 计划 |
| `/auth` OAuth 登录 | ⚠️ 部分难点 | device-flow 或 Capability RPC | ~2-3d | Stage 1.5c |
| `/ide` IDE 集成 | ⚠️ 语义模糊 | "IDE 在哪台机器？" | TBD | TBD |
| `ModelDialog` 选 model | ✅ 已 wire 化 | `POST /session/:id/model` + `model_switched` event | — | Stage 1 ✓ |
| `SessionPicker` 列 session | ✅ 已 wire 化 | `GET /workspace/:id/sessions` | — | Stage 1 ✓ |

**结论**：6/9 项 ~0.5d；2/9 项有 IPC 难点但 Capability RPC 可解；1/9 项语义模糊。它们归入 [§06 Stage 1.5c state CRUD](./06-roadmap.md#15c--daemon-side-state-crud--control-plane-parity)。

> 💡 **`/agents` 参考实现**：Claude Code `/agents` slash command 已 ship 完整 ~3042 LOC 的 7-mode 状态机 + 11-step wizard + AI 生成 agent + 6 source 分层——是 daemon-side state CRUD 的最佳设计 anchor。详 [**Claude Code `/agents` UI Deep-Dive**](../claude-code-agents-view-deep-dive.md)（含 P0/P1 借鉴项：`omitClaudeMd` 省 ~5-15 Gtok/周 / `criticalSystemReminder_EXPERIMENTAL` 每 turn 重注入 / `isolation: worktree` agent 隔离 / AI 生成 agent 等）。

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

| 拓扑 | workspace 位置 | daemon 位置 | 适用 |
|---|---|---|---|
| **A. Local-Local** | 本机 | 本机 | 单人开发（最常见），Stage 1/1.5/2 默认 |
| **B. Local-Remote** | 本机 | 远端 | ❌ **不推荐** — daemon 看不到本地 fs，必须 mount fs to remote 或 sync，运维复杂 |
| **C. Remote-Remote**（**推荐**）| 远端 | 远端 | 类比 GitHub Codespaces / Coder；workspace 与 daemon 同机 = 不跨网络 fs |

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

## 五、Client Capability 反向 RPC（External Reference Architecture）

> daemon 不直接拥有 client 本地资源（editor / clipboard / browser / notification / file_picker），但 agent 有时需要"调起 client 本地能力"。设计 5 类 Client Capability 反向 RPC 协议，让 daemon 通过 SSE event 反向调用 client，client 通过 HTTP callback 回复。

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

## 六、与 PR#3929-3931 (remote-control stack) 的关系

2026-05-15 决策后，remote-control 优先级后置。它仍然可以作为 mobile/browser facade 存在，但不应继续拥有 parallel runtime / event log / worker server。正确方向是等 TUI / channels / web / IDE 先收敛到 Mode B daemon contract 后，remote-control 再复用同一 `DaemonSessionClient` + HTTP/SSE typed event contract。

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
