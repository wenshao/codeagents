# 05 — Security & Permission

> [← 上一篇：Deployment & Client](./04-deployment-and-client.md) · [下一篇：Roadmap & Ecosystem →](./06-roadmap.md)

## TL;DR

**双层权限模型**：传输层 Bearer token（PR#3889 ✅ MERGED 2026-05-13）+ 应用层复用 PR#3723 `evaluatePermissionFlow()`（daemon 作为第 4 种 execution mode）。**默认安全策略**：0.0.0.0 binding + 无 token = 拒绝启动。**Permission 分发**：first-responder vote（任意 client 抢答），per-session 隔离（cross-session permission_request 不泄漏）。

**Stage 1.5+ 候选**：per-request `sessionScope` override / Stage 1.5 must-have #3 pair tokens + revocation API / chiga0 finding 3 `PermissionMediator` 抽象（4 policy strategies）。

---

## 一、双层权限模型

```
┌────────────────────────────────────────────────────┐
│ Layer 1：传输层 Bearer Token（PR#3889 已实现）         │
│ ├─ daemon 启动: QWEN_SERVER_TOKEN env / --token flag │
│ ├─ AuthMiddleware: SHA-256 + crypto.timingSafeEqual  │
│ └─ 401 uniform across missing / bad-scheme / wrong   │
└────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────┐
│ Layer 2：应用层 Permission Flow（PR#3723 已合并）      │
│ ├─ L3: Tool 内置默认权限                              │
│ ├─ L4: PermissionManager 规则覆盖（allowlist/deny）   │
│ ├─ L5: 调用方覆盖（YOLO / AUTO_EDIT / PLAN / daemon-http）│
│ └─ finalPermission: allow / deny / ask                │
└────────────────────────────────────────────────────┘
                       ↓
                tool 执行 / 拒绝 / 弹审批
```

### Mode B 认证默认值

2026-05-15 后 roadmap 先只推进 Mode B（`qwen serve`）。Mode A（`qwen --serve`）保留为 parking lot，不再作为近期 Stage 1.5 主线。

| 维度 | Mode B（`qwen serve`）|
|---|---|
| 默认 auth | loopback 可无 token；非 loopback 必须 bearer token |
| 默认 listen | `127.0.0.1`（需显式 `--hostname 0.0.0.0` 才暴露远端）|
| CORS / Origin | 默认拒绝 browser Origin；Stage 2/后续 named `--allow-origin` |
| 关键场景 | 服务器 / 容器 / 远端机器 / TUI、channels、web、IDE client 统一 runtime |

本章下面的机制均按 Mode B 描述；未来若 Mode A 重新评估，应复用相同 permission / auth contract，而不是引入第二套权限语义。

---

## 二、Layer 1：传输层 Bearer Token（Stage 1 ✅ 实现）

### 启动配置

```bash
# 方式 A：环境变量（推荐 production / scripting）
QWEN_SERVER_TOKEN=$(openssl rand -hex 32) qwen serve

# 方式 B：CLI flag（推荐手动 / 测试）
qwen serve --token=$(openssl rand -hex 32)
```

Mode B 默认：未设 token 时 daemon 启动时随机生成一次性 token + 写入 `~/.qwen/serve/token`（0600 权限）；SDK / CLI 默认从该路径读取。

### 关键安全特性（PR#3889 commit `ad0e6ec06`）

| 特性 | 实现 |
|---|---|
| **timing-safe compare** | SHA-256 hash + `crypto.timingSafeEqual`——防 side-channel timing attack |
| **401 uniform** | "missing header" / "bad scheme" / "wrong token" 三种情况返回**完全一致**——防 side-channel 探测 |
| **0.0.0.0 + 无 token = 拒绝启动** | `--hostname 0.0.0.0` 必须配 `--token` 或 `QWEN_SERVER_TOKEN`，否则 boot refuses |
| **Host allowlist** | loopback 绑定时 Host 白名单（防 DNS rebinding）：`localhost:port` / `127.0.0.1:port` / `[::1]:port` / `host.docker.internal:port` |
| **IPv6 loopback** | `LOOPBACK_BINDS` 含 `::1` / `[::1]` |
| **CORS** | 默认拒绝所有 browser Origin |

### 0.0.0.0 + 无 token 拒绝启动设计依据

OpenCode 无 token 也启动（仅警告 "unsecured"）；Qwen 选择**直接拒绝启动**——理由：
- Qwen 默认服务对象包含 IM 用户（不只是开发者本地用），暴露公网风险更高
- 强制安全 default 是对用户负责（避免"开发时不开 token 直接走勿勿上线"）

---

## 三、Layer 2：应用层 Permission Flow（复用 PR#3723）

### 决策

**复用 PR#3723 共享 L3→L4 permission flow + daemon 加为第 4 种 execution mode**。

```typescript
type ExecutionMode = 'interactive' | 'non-interactive' | 'acp' | 'daemon-http'
```

PR#3723（已合并 +461/-95）把 Interactive / Non-Interactive / ACP 三模式的 L3→L4 决策合一为 `evaluatePermissionFlow()`。daemon 是第 4 种 mode，复用同一份决策逻辑——bug 修一处全 mode 受益。

### `daemon-http` mode 关键差异

ACP mode 是 stdio 单 client 同步等待；`daemon-http` mode 是多 client + HTTP 异步：

| 维度 | ACP mode | daemon-http mode |
|---|---|---|
| client 数 | 1 | N（同 session 多 subscriber）|
| `ask` 决策传递 | 直接 stdio 双向 RPC | SSE 推 `permission_request` + HTTP `POST /permission/:requestId` 应答 |
| 应答 | client 阻塞等待 → response | 任意 client first-responder wins |
| 超时 | client 端处理 | 60s 默认 deny |

---

## 四、Permission Cache 与 Multi-Session

### Stage 1 (commit `6a170ef8`) 现状

- **Permission decisions cache 是 per-`qwen --acp` child（= per-workspace）**
- 同 workspace N session 各自维护 PermissionManager（每个 ACP `Session` 实例内）
- `workspace` / `global` scope decisions 文件 **per-workspace 共享**——同 daemon N session 并发写时需 in-memory mutex（per-file lock）
- first-responder vote 路由按 sessionId 隔离——A session 的 `permission_request` 走 daemon 内部 EventBus，并通过 SSE 只 fan-out 到订阅 A session 的 client，不会泄漏到 B session 的订阅者

### Stage 2e native in-process（可选演进）

跨 workspace 共享时需 key 加 workspace 维度（`(workspace, sessionId, toolName, resource) → decision`）；同 daemon 内多 workspace 隔离仍由应用层保证。

### Persistence scope（per-tool decisions）

| Scope | 存储 | 生命周期 |
|---|---|---|
| `session` | 内存（per-Session）| daemon 退出即失效 |
| `workspace` | `~/.qwen/workspaces/<wsId>/permissions.json` | 启动时加载，per-daemon 共享 |
| `global` | `~/.qwen/permissions.json` | 启动时加载，daemon process 全局 |

---

## 五、Permission Vote 流（PR#3889 commit `6ee655f0a` 已实现）

### 完整流程

```
1. agent 内代码: PermissionManager.evaluate('Bash', {cmd: 'npm test'})
2. flow 走到 L4 = 'ask' → 推送 permission_request event 到 daemon 内部 EventBus
3. daemon broadcasts 'permission_request' SSE event 到 session 所有 subscriber
4. HTTP request 挂起（pending in `pendingPermissions` Map）
5. 任意 client `POST /permission/:requestId` 应答（first-responder）
6. PermissionManager 解锁 HTTP request → 继续 tool 执行
7. SSE 推 `permission_resolved` 让其他 client 知道结果
8. cancelSession / shutdown 解锁 outstanding requests as `cancelled`（per ACP spec）
```

### 6 种 Permission Policy（Stage 2a permission_request schema 预留）

> chiga0 [PR#3889 audit](https://github.com/QwenLM/qwen-code/pull/3889) 指出 first-responder 缺 authorization model 风险：daemon 升级为 1:N 广播后没有 client identity 区分，**bot client 可在 human 看到前自动 approve**。即使 Stage 1 只实现 first-responder，schema 应预留 policy 字段。

```jsonc
// SSE event: permission_request
{
  "type": "permission_request",
  "requestId": "r1",
  "tool": "Bash",
  "args": { "cmd": "npm test" },
  "policy": "first-responder",     // Stage 2a schema 预留
  "designatedClientIds": null,      // policy='designated' 时填
  "quorumRequired": null            // policy='quorum' 时填
}
```

### Stage 1.5b/P1 finding 3 — `PermissionMediator` interface lift

> chiga0 [comment 4427773706](https://github.com/QwenLM/qwen-code/pull/3889#issuecomment-4427773706) finding 3：当前 daemon 的 first-responder + `nonInteractive/ControlDispatcher` + `channels/BridgeClient` 是同一概念的 3 个独立实现。Stage 1.5b/P1 抽 `PermissionMediator` interface + 4 种 strategy policy，让 daemon HTTP/SSE、channels、stream-json 等路径共享同一 mediator：

```ts
interface PermissionMediator {
  request(req: PermissionRequest, policy?: PermissionPolicy): Promise<PermissionOutcome>;
}
type PermissionPolicy =
  | { kind: 'first-responder' }              // Stage 1 默认
  | { kind: 'designated'; clientId: string } // 多用户场景：指定 client 才能批
  | { kind: 'consensus'; minVotes: number }  // quorum 模式
  | { kind: 'local-only' };                  // 当前 TUI behavior（local-jsx，不出 wire）
```

详 [§06 §三 1.5-prereq](./06-roadmap.md#15-prereq--mode-b-event-contract--bridge-primitives) 与 cross-module refactor findings。

---

## 六、Multi-Tenant 关键约束

> ✅ **1 daemon = 1 workspace 模式下天然 OS 进程级隔离**：跨 tenant = 跨 daemon process，无需应用层 tenant 抽象。

### 隔离形态

[§02 §2](./02-architectural-decisions.md#2-状态进程模型核心决策) 1 daemon = 1 workspace × N session 模式下：

- **跨 tenant 部署 = 多 daemon process**：1 daemon = 1 tenant × 1 workspace，OS 进程级真隔离
- **systemd `MemoryMax=` / cgroup / docker `--memory` 直接 = per-tenant quota**——不需要 daemon 内部抽象
- **同 daemon N session 共 OS 权限**（同 `qwen --acp` child，共 user UID + fs 视图；MCP children 当前随 session config 创建但仍在同 UID/workspace 信任域内）——天然 1 tenant 内 N session 共信任域

### 同 daemon N session 边界（注意）

⚠️ 同 daemon N session 共享 OS 权限——即同 tenant 内 N session 共信任域。**不可让多 tenant 共一个 daemon**：

- 1 daemon 启动时绑定 1 tenant 的 1 workspace（启动 cwd + 启动用户）
- 多 tenant 必须各自独立 daemon process（orchestrator 在创建 daemon 时绑 daemon → tenant）

详 [§06 §5.2 Multi-tenancy](./06-roadmap.md#52-multi-tenancy--oidc--quota--audit)。

### 并发写 race condition

- **Stage 1**：同 workspace N session 并发写 `workspace` / `global` scope decisions / settings 时需 in-memory mutex（per-file lock）防 lost update。`session` scope 仍 per-session 私有不冲突
- **多 daemon 并发写**：由 orchestrator 层处理（SQLite `permission_decisions` 表 + WAL）；跨 daemon process 不共享 in-memory state，需 orchestrator 协调

---

## 七、PR#3726 Monitor permission namespace（已合并）

PR#3726（已合并）为 `Monitor` 工具加了独立 permission namespace：

```
Monitor(*)         # 所有 monitor 调用允许
Monitor(npm test)  # 仅 npm test 允许
```

daemon 模式下完全兼容——`evaluatePermissionFlow()` 已识别此 namespace；用户在远端 client 应答 permission_request 时填写规则会保存到 daemon 进程 settings。

---

下一篇：[06 — Roadmap & Ecosystem →](./06-roadmap.md)
