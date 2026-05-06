# 08 — 3 阶段路线图

> [← 上一篇：权限 / 认证](./07-permission-auth.md) · [下一篇：与 OpenCode 详细对比 →](./09-comparison-with-opencode.md)

> 渐进式落地，每阶段都可独立交付价值。Stage 1 ~1 周可用、Stage 2 ~3 周完整 daemon、Stage 3 ~2 月对标 OpenCode。

## 总览

```
Stage 1 (~1 周): http-bridge 实验性 flag
  └─ 在现有 ACP agent 外加 HTTP→stdio 桥接
  └─ 让用户先用起来 + 收集需求

Stage 2 (~3 周): 原生 qwen serve 多 session
  └─ 重写 ACP agent 为多 session HTTP server
  └─ 加 SDK HttpTransport
  └─ Web UI 接入

Stage 3 (~2 月): 对标 OpenCode 完整设计
  └─ Workspace routing + mDNS + OpenAPI
  └─ WebSocket 双向 + 权限流深化
  └─ 多 token / 集群部署文档 / 企业鉴权
```

---

## Stage 1：实验性 `--http-bridge` flag（~1 周）

### 目标

**最小改动让用户先用上 daemon 模式**——通过把现有 ACP agent 包装成 HTTP→stdio 桥接，零业务逻辑变更，验证多 client 场景的需求与痛点。

### 实现

```
[现有] qwen --acp                 → stdio NDJSON ACP agent
[新增] qwen serve --http-bridge   → 启 Hono HTTP server
                                  → 内部启 ACP agent 子进程（pipe stdio）
                                  → HTTP body ↔ stdio NDJSON 桥接
```

**特点**：
- ACP agent 本身不改一行代码
- daemon 进程 **依然 spawn ACP agent 子进程**（不是真正的 daemon 内 in-process core）
- 单 ACP session = 单 stdio 子进程 = 多 client 排队访问

### 工作清单

| 任务 | 工作量 | 文件 |
|---|---|---|
| 新建 `packages/server/` 包 | 0.5d | `packages/server/package.json` |
| `qwen serve` CLI cmd | 0.5d | `packages/cli/src/cli/cmd/serve.ts`（仿 OpenCode）|
| Hono HTTP server scaffold | 1d | `packages/server/src/index.ts` |
| HTTP→stdio bridge | 2d | `packages/server/src/bridge/HttpAcpBridge.ts` |
| Auth middleware | 0.5d | bearer token 校验 |
| `/session/*` 路由 | 1d | 复用 ACP request schema |
| SSE event stream | 1d | NDJSON → SSE 适配 |
| 文档 + 示例 + e2e 测试 | 1d | |
| **合计** | **~7-8 天 / 1 人** | ~700-1000 行新增代码 |

### Stage 1 局限

- **同 session 多 client = 排队**（stdio 子进程一次只能处理一个 prompt）
- **每个新 session = 新 stdio 子进程**（启动开销没省）
- **跨 session 资源不共享**（LSP / MCP 各打一套）

### 价值

- 用户立刻能用 SDK over HTTP / Web UI / VSCode 直连 daemon
- 暴露多 client 真实场景（哪些 API 用得多 / pain points）
- 为 Stage 2 设计提供数据

---

## Stage 2：原生 `qwen serve` 多 session（~3 周）

### 目标

**真正的 daemon——多 session 共进程，core 直接 import**。Stage 1 的 stdio 桥接退役，进入"OpenCode 同模式但用 ACP schema"。

### 工作清单

| 任务 | 工作量 | 关键文件 / PR 关联 |
|---|---|---|
| 重写 ACP agent 为 in-process 多 session router | 3d | 新建 `packages/server/src/AcpAgent.ts` 替代 stdio 模式 |
| `Instance` AsyncLocalStorage 工具 | 1d | `packages/core/src/util/instance-context.ts` |
| Workspace 注册 / 路由 middleware | 2d | 复用 SessionRouter 思路 |
| HttpTransport（SDK 端）| 2-3d | `packages/sdk-typescript/src/transport/HttpTransport.ts` —— 镜像 ProcessTransport |
| Web UI 接入（HttpAcpAdapter）| 2d | `packages/webui/src/adapters/HttpAcpAdapter.ts` |
| Permission flow `daemon-http` mode | 2d | 扩展 PR#3723 `evaluatePermissionFlow()` + SSE permission_request |
| WebSocket 升级 + bidi 通信 | 2d | `Bun.serve` + `createBunWebSocket` |
| MCP server pool 跨 session 复用 | 2d | 扩展 `mcp-client-manager.ts` + fingerprint 路由 |
| `/permission/:id` 路由 + persist | 1d | SQLite `permission_decisions` 表 |
| daemon 生命周期（pid file / graceful shutdown / SIGTERM）| 1d | |
| 集成测试 + 文档 | 2-3d | |
| **合计** | **~3 周 / 1 人**（或 1.5 周 / 2 人）| ~2000-3000 行 |

### Stage 2 验收

- ✓ 多 session 共进程（Map<workspaceId, Workspace>）
- ✓ AsyncLocalStorage cwd 隔离
- ✓ HTTP/WebSocket 流式事件
- ✓ Bearer token 鉴权
- ✓ Permission flow 复用 PR#3723
- ✓ SDK HttpTransport 可用
- ✓ Web UI / VSCode 可接入
- ❌ mDNS 发现（推到 Stage 3）
- ❌ OpenAPI 自动生成（推到 Stage 3）

### Stage 2 后的架构状态

```
                  ┌─────────────────┐
SDK / Web UI ─────│ qwen serve daemon│
VSCode       ─────│  多 session HTTP │
                  │  SQLite 持久化   │
                  │  AsyncLocalStorage│
                  │  in-process core │
                  └─────────────────┘

跑起来与 OpenCode daemon 同形态，仅差 mDNS / OpenAPI / 企业认证。
```

---

## Stage 3：对标 OpenCode 完整设计（~2 月）

### 目标

**生产级 daemon**——支持团队部署、多租户、零摩擦发现。

### 工作清单

| 任务 | 工作量 | 说明 |
|---|---|---|
| Workspace routing 中间件 | 5-7d | URL `/workspace/:id/*` 与 host header 双路由 |
| mDNS 服务发现 | 1d | `bonjour-service`（OpenCode 同款）—— `_qwen._tcp.local` |
| OpenAPI codegen | 3-5d | `hono-openapi` 自动生成 spec + SDK 验证 |
| WebUI 直接跑在 daemon 上 | 5-7d | 静态资源 mount，`/ui/*` 直接 serve |
| 多 token + workspace allowlist | 5-7d | `tokens.json` + per-token user-id |
| 企业认证（OIDC / SSO）| 7-10d | OAuth 2.0 / OIDC discovery |
| 审计日志 | 3-5d | 每次工具调用 / 权限决策 / 文件操作 写 audit.log |
| 配额管理（每 user / 每 workspace）| 5-7d | LLM token 用量 + tool call 频率限流 |
| 跨 client 审批 UX | 3-5d | "primary client" 概念 / 多 majority 决策 |
| 集群多实例 / 负载均衡文档 | 5-7d | sticky session + Redis state（可选）|
| 健康检查端点 / Metrics（Prometheus）| 3-5d | `/metrics` 标准 OpenMetrics |
| Stage 3 升级 FileReadCache 跨 session 共享（可选）| 5-7d | 重审 PR#3774 prior-read 语义 |
| 文档 + 例子 + 性能基准 | 7-10d | |
| **合计** | **~6-8 周 / 2-3 人** | ~5000-8000 行 |

### Stage 3 验收

| 维度 | 要求 |
|---|---|
| 多用户 | 支持 10+ 并发 user，每 user 多 session |
| 性能 | 单 daemon 进程并发 100 sessions 无明显性能下降 |
| 可观测性 | OpenMetrics + audit log + traceId（PR#3847 OPEN 已铺路）|
| 部署 | Docker image + helm chart + 集群部署文档 |
| 兼容 | OpenAPI spec 稳定 + SDK 版本兼容矩阵 |
| 安全 | OIDC / SSO + 多 token + 速率限制 + CSP |

---

## 时间线甘特图

```
                  Week 1   Week 2   Week 3   Week 4   ...   Week 8   Week 12
Stage 1           ████
Stage 2                   ████████████████
Stage 3                                    ████████████████████████████████
                                           (同时多人并行)

里程碑:
   end Week 1: --http-bridge flag GA, 用户首批反馈
   end Week 4: qwen serve 原生 daemon GA
   end Week 12: 企业级 daemon 1.0
```

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| Stage 2 多 session 共进程引入 OOM/race condition | 严格 AsyncLocalStorage 测试覆盖 + Effect-style 隔离审计 |
| MCP server 跨 session 状态泄漏 | per-server `requiresPerSession` flag fallback |
| FileReadCache 与 history rewrite 同步问题 | PR#3810 已修 5 路径，新加 daemon 路径需类似 audit |
| Bearer token 泄漏 | 默认 0.0.0.0 binding 拒绝启动（无 token）|
| `process.chdir()` 误调 | 落地后 grep audit + CI 守卫 |
| 与现有 ACP agent 行为不一致 | Stage 1 stdio 桥接持续保留作 reference impl |

## Stage 0：前置 PR 完成度（确认已就绪）

进入 Stage 1 前确认以下 PR 已合并：

| PR | 状态 | 必要性 |
|---|---|---|
| PR#3717 FileReadCache | ✅ 已合并 | session-scoped cache 是 daemon 必备 |
| PR#3810 FileReadCache 5 路径 invalidation | ✅ 已合并 | 长 session 正确性 |
| PR#3723 共享 permission flow | ✅ 已合并 | daemon 加第 4 mode 的基础 |
| PR#3739 Background agent resume + transcript-first fork | ✅ 已合并 | daemon 重启 / 跨 client 续行 |
| PR#3642 `/tasks` + background shell pool | ✅ 已合并 | 跨 session 任务调度 |
| PR#3818 MCP rediscovery coalesce | ✅ 已合并 | MCP pool 共享 |
| PR#3836 Kind framework 4 消费者 | ✅ 已合并 | 跨 client 任务可见性 |

✓ **全部 PR 在 2026-05-06 之前已合并**——daemon 化的所有前置基础已就绪。

---

下一篇：[09-与 OpenCode 详细对比 →](./09-comparison-with-opencode.md)
