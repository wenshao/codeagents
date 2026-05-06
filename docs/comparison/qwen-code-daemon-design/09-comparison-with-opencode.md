# 09 — 与 OpenCode 详细对比

> [← 上一篇：3 阶段路线图](./08-roadmap.md) · [回到 README](./README.md)

> 本设计与 OpenCode daemon 在大方向上一致（共进程 + AsyncLocalStorage + SQLite），但在关键路径上做了 4 个有意识的差异化选择。

## 一、设计哲学对比

| 维度 | OpenCode | Qwen Daemon（本设计）| 差异理由 |
|---|---|---|---|
| 进程模型 | 单 daemon 多 session 共进程 | **同款** | 已验证最优 |
| `process.cwd()` | 永不改变 | **同款** | OpenCode 已验证 |
| 上下文传播 | Effect-TS `LocalContext` | **AsyncLocalStorage 直接** | Qwen 不引入 Effect 重依赖 |
| HTTP 框架 | Hono | **Hono（同款）** | Bun-friendly + OpenCode 已验证 |
| 协议 schema | OpenAPI codegen（13525 行）| **复用 ACP NDJSON zod schema** | Qwen 已有 838 行 ACP agent，0 设计成本 |
| 多 channel 支持 | 仅 SDK / TUI / Web | **+ IM / IDE 全走 SessionRouter** | Qwen 已有 Channels 包 |
| 鉴权 | 单密码 `OPENCODE_SERVER_PASSWORD` | **bearer token + PR#3723 应用层权限流** | Qwen 已有 PR#3723 |
| Session 共享 | 否（per-SDK call）| **可配（thread/single/user）** | Qwen Channels 已有 scope 概念 |
| 数据持久化 | SQLite（drizzle-orm）| **JSONL session（PR#3739）+ SQLite for permission decisions** | 复用 Qwen 现有持久层 |
| 默认安全 | 无 token 警告，仍启动 | **无 token + 0.0.0.0 拒绝启动** | 比 OpenCode 严格 |

## 二、HTTP 路由对比（详细）

### OpenCode 路由结构

```
/global          → 全局元信息
/control         → 多 workspace 调度面
/                → workspace router
  ├─ /session/*       (session lifecycle)
  ├─ /file/*          (file 读写)
  ├─ /pty/*           (terminal, WebSocket)
  ├─ /tui/*           (TUI client 接入点)
  ├─ /provider/*      (provider 管理)
  ├─ /mcp/*           (MCP 管理)
  ├─ /permission/*    (审批)
  └─ /event/*         (SSE/WS)
/ui              → 内嵌 web UI
```

### Qwen Daemon 路由结构（本设计）

```
/                                       服务端元信息（含 acp 协议版本）
/health                                  健康检查（无认证）
/authenticate                            bearer token 取换 long-lived token

/session                                 session lifecycle (复用 ACP 协议)
  ├─ POST /session                       NewSessionRequest
  ├─ GET  /session                       ListSessionsRequest
  ├─ POST /session/:id/load              LoadSessionRequest
  ├─ POST /session/:id/prompt            PromptRequest
  ├─ POST /session/:id/cancel            CancelNotification
  ├─ POST /session/:id/model             SetSessionModelRequest
  └─ GET  /session/:id/events            SSE / WebSocket

/permission/:requestId                   审批响应（异步流模式）

/workspace                               多 workspace 路由
  ├─ POST /workspace                     register workspace
  ├─ GET  /workspace/:id/skills          已加载 skill
  ├─ GET  /workspace/:id/mcp             MCP server 状态
  ├─ GET  /workspace/:id/lsp             LSP 状态
  ├─ GET  /workspace/:id/tasks           background tasks (4 kinds)
  ├─ GET  /workspace/:id/file            read file
  ├─ POST /workspace/:id/file            write file (PR#3774 prior-read 守卫)
  ├─ POST /workspace/:id/file/edit       edit file (同上)
  └─ POST /workspace/:id/pty             open PTY (Upgrade: websocket)
```

**关键差异**：

1. **ACP RPC 直接映射**：Qwen 的 `/session/:id/*` body 直接是 ACP request schema（`PromptRequest` / `LoadSessionRequest` / `SetSessionModelRequest` 等）；OpenCode 是自创的 OpenAPI schema。
2. **`/workspace/:id/tasks` 列出 4 kinds**：Qwen 把 PR#3471/3488/3642/3791/3836 的 agent/shell/monitor/dream 4 种 kind 任务统一展示；OpenCode 没有 monitor + dream 概念。
3. **`/permission/:requestId` 异步响应**：Qwen 走 SSE 推 + POST 回的异步流模式；OpenCode 走 dialog 同步模式（与 daemon 模型相对差，因为 daemon 通常 headless）。

## 三、技术栈对比

| 组件 | OpenCode | Qwen Daemon |
|---|---|---|
| HTTP 框架 | Hono | Hono |
| Runtime | Bun 优先 / Node fallback | Bun 优先 / Node fallback |
| WebSocket | `Bun.serve` + `createBunWebSocket` | 同款 + SSE 兜底 |
| OpenAPI 生成 | `hono-openapi` | `hono-openapi`（Stage 3）|
| Schema 验证 | Effect Schema | **zod**（与现有 ACP 一致）|
| 上下文传播 | Effect `Context.Service` | **`AsyncLocalStorage` 直接** |
| 服务发现 | mDNS Bonjour（默认开启）| Stage 3 可选（默认关）|
| 持久化 | SQLite via drizzle-orm | JSONL（session）+ SQLite（permission）|
| 鉴权 | `OPENCODE_SERVER_PASSWORD` env | bearer token + PR#3723 |

## 四、API 命名对比

| 概念 | OpenCode | Qwen Daemon |
|---|---|---|
| 创建 session | `POST /session` | `POST /session`（body 是 ACP `NewSessionRequest`）|
| 发送消息 | `POST /session/:id/message` | `POST /session/:id/prompt`（ACP 术语）|
| 取消 | `POST /session/:id/abort` | `POST /session/:id/cancel`（ACP 术语）|
| 流式事件 | `GET /event` 全局 | `GET /session/:id/events`（per-session 流）|
| 切换 workspace | URL `/?directory=...` query | URL `/workspace/:id/...` path |
| MCP 列表 | `/mcp` 全局 | `/workspace/:id/mcp`（per-workspace 隔离）|

**Qwen 选择更显式的 path-based workspace** —— 与 OpenCode 的"directory query"相比，URL 一眼能看出请求作用范围。

## 五、与 OpenCode 不同的 4 个核心选择

### 5.1 ACP zod schema 而非自创 OpenAPI

**收益**：
- 协议层 0 设计成本（ACP 已有 838 行 agent 验证过）
- daemon route handler 与 ACP `Session.handleXxx()` 共享同一组业务函数
- 客户端可直接复用 ACP 类型（`@agentclientprotocol/sdk`）

**代价**：
- ACP schema 设计为 stdio NDJSON，HTTP body 用起来不是最 idiomatic（如 path id 与 body id 重复）
- 协议演进绑定 ACP 版本（当前 0.14）

**判断**：复用 ACP 收益远大于代价——0 设计成本 + 与 IDE/Zed 生态天然兼容（IDE 通过 ACP 连 daemon 时不需要 schema 适配）。

### 5.2 多 channel 路由（IM / VSCode / Web 全走 SessionRouter）

**OpenCode**：daemon 是给 SDK / TUI / Web UI 用的——单一类客户端。
**Qwen**：Channels 包已有的 IM 路由（Telegram / 微信 / 钉钉）也走 daemon——多类异构客户端共存。

**优势**：
- 一个用户可以从手机微信发命令，回到电脑 SDK 继续看（`scope='user'`）
- IM 客户端 + 桌面 IDE + Web UI 同时观察一个 session

**复杂性**：
- 多 channel scope 矩阵（thread / single / user）增加测试面积
- IM 客户端的认证模式与 HTTP bearer token 不同（IM 用 OAuth 配对）—— 需额外适配层

### 5.3 PR#3723 应用层权限流

**OpenCode**：单 password 控制访问，工具级 permission 走 OpenCode permission system。
**Qwen**：bearer token + 复用 PR#3723 evaluatePermissionFlow()——daemon 只是第 4 种 mode。

**收益**：
- 工具级权限决策与 Interactive / Non-Interactive / ACP mode 共享同一份逻辑
- bug 修一处全 mode 受益（PR#3723 把"散落 3 处"重构为单一权威路径）
- `alwaysAllow` 持久化跨 mode 一致

**代价**：
- daemon 加 mode 后 PR#3723 的 4 mode 矩阵更复杂

### 5.4 默认 0.0.0.0 + 无 token = 拒绝启动

**OpenCode**：无 token 也启动（仅警告 "unsecured"）。
**Qwen**：无 token + `--hostname=0.0.0.0` **直接拒绝启动**。

**理由**：
- Qwen 默认服务对象包含 IM 用户（不只是开发者本地用），暴露到公网风险更高
- 强制安全 default 是对用户负责

## 六、性能对比预期

| 维度 | OpenCode（实测）| Qwen Daemon（预期）|
|---|---|---|
| 启动时间 | ~2-3s | 类似（同框架）|
| 单 session 创建 | <100ms | 类似 |
| 同 workspace 第二个 session | <50ms（LSP/MCP 已 ready）| 类似 |
| Prompt 端到端延迟（SSE 首字节）| 主要由 LLM 决定 | 类似 |
| 100 并发 session | 内存约 1-2GB（取决于 LLM 上下文）| 类似 |

**Qwen 可能略高的地方**：
- ACP zod schema 校验 vs OpenCode Effect Schema —— zod 在大 schema 上略慢但 Qwen 路由相对简单，影响可忽略
- Channels SessionRouter 的额外路由层 —— 仅 Map 查表，纳秒级

## 七、迁移路径（Qwen 用户从 stdio ACP 切到 daemon）

```bash
# Stage 0：现状 - 用户启动 stdio ACP agent
qwen --acp                                   # stdio NDJSON

# Stage 1（实验）：用 http-bridge 试一下
qwen serve --http-bridge --port 5096

# Stage 2 GA：原生 daemon
qwen serve --port 5096

# 客户端切换
# 旧：spawn qwen --acp + ndJsonStream(child.stdin/stdout)
# 新：HTTP fetch + EventSource
```

SDK 用户：

```ts
// 旧
const q = query({ transport: new ProcessTransport(...) })

// 新
const q = query({ transport: new HttpTransport({
  baseUrl: 'http://localhost:5096',
  bearerToken: process.env.QWEN_SERVER_TOKEN,
}) })
```

`Transport` 接口不变，业务代码一行不改。

## 八、长期可能的差异

5 个维度上 Qwen daemon **可能比 OpenCode 走得更远**（因为 Qwen 的 ecosystem 更广）：

1. **ChannelAdapter 生态**：Telegram / 微信 / 钉钉 / Slack 直接挂在 daemon 上 —— OpenCode 没这套
2. **VSCode IDE companion 直连 daemon**：替代当前 ide-server.ts 自起 express
3. **Java SDK 直连 daemon**：Qwen 唯一有 Java acp-sdk，daemon 后跨语言更顺
4. **Background tasks 4 kinds 跨 client 可见**：Qwen kind framework（PR#3836）能在 daemon 模式下让所有 client 看到所有后台任务（agent/shell/monitor/dream）
5. **MCP fingerprint pool**：Qwen 通过 PR#3818 / PR#3819 的 in-flight coalesce，跨 session 共享 MCP server pool 比 OpenCode 更精细

## 九、核心结论

| 共识 | Qwen 差异化 |
|---|---|
| daemon 单进程多 session | 1. 复用 ACP zod schema |
| AsyncLocalStorage 上下文 | 2. 多 channel 路由（IM/IDE/Web/SDK 同源）|
| Hono / Bun.serve 技术栈 | 3. 复用 PR#3723 应用层权限流 |
| SQLite + JSONL 持久化 | 4. 默认 0.0.0.0 + 无 token = 拒绝启动 |

**Qwen daemon 不是"OpenCode 的复刻"，而是"借鉴 OpenCode 验证过的进程模型 + 复用 Qwen 自家的 ACP / Channels / PR#3723 / Background tasks 等成熟资产"** —— 这正是 [02 现有资产盘点](./02-existing-assets.md) 表明的 ~75% 复用率的来源。

---

[← 回到 README](./README.md)
