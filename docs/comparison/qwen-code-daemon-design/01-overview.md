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

**两种部署**：
- **Mode B** `qwen serve` — 当前主线：headless HTTP front，所有 client 通过 HTTP/SSE 接入同一 daemon runtime。
- **Mode A** `qwen --serve` — 2026-05-15 后暂停推进；作为 parking lot 保留，待 Mode B event/control/client contract 稳定后再评估。

**主线 scope**：daemon building block + 协议表面锁定（Stage 2 后）。多 tenant / 跨 daemon process 路由 / SaaS 部署属 **External Reference Architecture**（外部商业平台实施）。

---

## 一、术语表

| 术语 | 定义 | 源码 anchor |
|---|---|---|
| **Daemon process** | `qwen serve` HTTP front 进程；启动时绑定 cwd = 单 workspace；持 Express 5 server + EventBus + 1 个内嵌 `qwen --acp` child | `packages/cli/src/serve/server.ts` |
| **Session** | ACP `Session` 实例（`QwenAgent.sessions: Map<sessionId, Session>` 内一条）；持 transcript / FileReadCache / PermissionManager | `packages/cli/src/acp-integration/session/Session.ts` |

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

External Reference Architecture 提供 orchestrator 层（详 [§06 §五 External Reference Architecture](./06-roadmap.md)）。

---

## 三、双部署模式

| 模式 | 启动命令 | TUI | 适用场景 |
|---|---|---|---|
| **Mode B: Headless + HttpServer** | `qwen serve [--port N]` | ❌ | 当前主线：服务器 / 容器 / 远端机器 / K8s pod / 所有 client 的统一 runtime |
| **Mode A: CLI + HttpServer** | `qwen --serve [--port N]` | ✅ 本地 | 暂停推进；作为 parking lot 保留 |

**当前 client 边界**：TUI / channels / web / IDE 直接对接 `qwen serve` HTTP server；`GET /session/:id/events` 是 daemon 内部 EventBus 的 SSE projection。外部 client 不直接 import / subscribe 内存 EventBus。

**Mode B 远端 client 是 "thin shell"**（Stage 1）——只能渲染 wire 流，daemon-side state dialogs（`/memory` / `/mcp` / `/agents` 等）不可用。Stage 1.5c daemon-side state CRUD 补齐后，TUI / channels / web / IDE 才能成为完整 client。详 [§04](./04-deployment-and-client.md)。

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
| **Stage 1.5-client adapters** **(P1 behind flag)** | TUI / channels / web/debug / IDE 接入 Mode B daemon；默认切换必须等 P0/P1 | ~2-3 周 |
| **Stage 1.5b** Mode A **(P2 推迟)** | Mode A `qwen --serve` flag — [Issue #4156](https://github.com/QwenLM/qwen-code/issues/4156)；A1 [PR#4160](https://github.com/QwenLM/qwen-code/pull/4160) ✅ MERGED；**推迟到 1.5c 后**（Mode A 价值依赖 1.5c）| ~5-6d |
| **Stage 1.5-remote-control** **(P2 后置)** | [PR#3929](https://github.com/QwenLM/qwen-code/pull/3929) / [#3930](https://github.com/QwenLM/qwen-code/pull/3930) / [#3931](https://github.com/QwenLM/qwen-code/pull/3931) 后续作为 daemon facade | 待 primary clients 收敛 |
| **Stage 2** | 协议补齐（WebSocket / mDNS / OpenAPI / Prometheus / `/ext` + Reverse RPC 5 类 Client Capability）| ~3-4 周（拆 2a-2d）|
| **Stage 2e** | 可选 native in-process（去 `qwen --acp` child）| ~1-2 周 |

> **优先级决策（2026-05-15）**：Mode B 优先 — must-haves + 1.5c 摆脱 thin shell → 1.5-prereq 架构清洁 → Mode A（1.5b）推迟。详 [§06 §三 推进顺序](./06-roadmap.md)。

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
