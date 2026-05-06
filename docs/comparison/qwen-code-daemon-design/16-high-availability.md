# 16 — HA 高可用与故障恢复

> [← 上一篇：持久层与外部存储](./15-persistence-and-storage.md) · [回到 README](./README.md)

> 多租户 daemon 在 Stage 6 SaaS 模式下的 HA 设计：状态可恢复性分类、5 层架构、failover 时序、SSE reconnect 协议、LLM streaming 中断 7 种场景、Chaos 测试矩阵、SLO 设计。

## 一、TL;DR

| 维度 | 设计 |
|---|---|
| HA 拓扑 | **k8s StatefulSet N≥3 + Ingress sticky + Postgres Patroni + Redis Sentinel + S3 多 AZ** |
| 路由策略 | **sticky by `sessionId`**（不是 `tenantId`，更细粒度）+ cookie hash fallback |
| 状态恢复 | **transcript-first fork resume（PR#3739）+ Redis 共享 subscribers/quota/permission cache** |
| Pod failover | **graceful shutdown 90s drain → client SSE 自动重连 → 新 pod 重建 session** |
| LLM streaming 中断 | **不自动续接**（避免重复计费），client UI 显示 "session interrupted, retry?" |
| Postgres failover | **Patroni 自动选主 30-60s**，daemon 进 degraded mode 缓冲 audit log |
| SLO | **99.9% (43m/月) for Stage 6 起步 / 99.99% (4.3m/月) 企业 SLA** |
| 跨 region | **DNS failover + S3 cross-region rep + Postgres logical rep**（可选）|

## 二、HA vs DR 概念

| 维度 | HA（高可用）| DR（灾难恢复）|
|---|---|---|
| 目标 | 单组件失败时服务不中断 | 整个 region 失败后恢复 |
| RTO | 秒级 | 分钟到小时 |
| RPO | 0-几秒 | 几分钟 |
| 部署 | 同 region 多 AZ | 跨 region |
| 触发 | pod / Postgres 节点失败 | 自然灾害 / 大规模故障 |
| 本章重点 | ✓ 主线 | §五.4 简述 |

## 三、Daemon 状态可恢复性矩阵

[§14 实体模型](./14-entity-model.md) 列出 6 层实体；HA 视角下按 **状态恢复成本** 重新分类：

| 状态 | 存储位置 | 持久化？ | 跨 pod 重建成本 | HA 策略 |
|---|---|---|---|---|
| Tenant config / token | Postgres | ✓ | 0（直接读）| L3 Postgres HA |
| Workspace meta | Postgres | ✓ | 0 | L3 Postgres HA |
| Session meta | Postgres | ✓ | 0 | L3 Postgres HA |
| Transcript | S3 + 本地缓存 | ✓ | 中（下载耗时）| L4 S3 多 AZ |
| Permission decisions | Postgres + Redis cache | ✓ | 0 | L3 + Redis |
| Audit log | Postgres | ✓ | 0 | L3，degraded 时本地缓冲 |
| Background task meta | Postgres | ✓ | 0 | L3 |
| Quota counter | Redis | 部分 | 0 | Redis Sentinel |
| **SSE / WebSocket 长连接** | pod TCP | ✗ | **极高** | sticky + client reconnect |
| **active LLM streaming** | pod 内存 + Provider | ✗ | **极高** | 不续接，UI 提示 |
| **MCP / LSP server 子进程** | pod 本地 spawn | ✗ | **极高** | 新 pod 重新 spawn（accept 1-3s 启动延迟）|
| **FileReadCache** | pod 内存 | ✗ | 中 | 重建（下次 read 时 miss → fill）|
| **AsyncLocalStorage Instance ctx** | pod 内存 | ✗ | 低 | tool call 边界自然重建 |
| **Background task 子进程**（shell PTY / sandbox）| pod 本地 | ✗ | **极高** | 失败标记 task 状态 `interrupted`|
| **subscribers Set** | pod 内存 + Redis | 部分 | 低 | Redis pub/sub 转发事件 |

**关键洞察**：
- **持久化数据**（前 7 行）跨 pod 0 成本恢复
- **进程类状态**（后 7 行）不可序列化，必须 sticky 或失败重建
- **HA 设计目标**：让 client 感知最小（自动重连 + transcript 续接）

## 四、5 层 HA 架构详解

```
┌─────────────────────────────────────────────────────────────┐
│ L1: Edge / DNS                                               │
│   - Cloud DNS 60s TTL                                        │
│   - GeoDNS 路由（跨 region 时）                               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│ L2: Ingress / Load Balancer (stateless N≥2)                  │
│   - HAProxy / nginx-ingress                                  │
│   - Sticky session: cookie hash by qwen-aff cookie           │
│   - cookie content: HMAC(sessionId, server-secret)           │
│   - SSE long-lived idle timeout: 600s                        │
│   - Health check: GET /healthz 5s 间隔, fail-2 摘除          │
└────────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┼────────────┐
            ↓            ↓            ↓
        ┌───────┐    ┌───────┐    ┌───────┐
        │ d-1   │    │ d-2   │    │ d-3   │   L3a: Daemon pods (StatefulSet)
        │ pod   │    │ pod   │    │ pod   │   N+1 容量规划
        │       │    │       │    │       │   PDB minAvailable: 2
        └───┬───┘    └───┬───┘    └───┬───┘
            │            │            │
            └────┬───────┴───────┬────┘
                 ↓               ↓
        ┌──────────────┐  ┌──────────────────┐
        │ Redis        │  │ Postgres Cluster │   L3b: 共享状态
        │ Sentinel     │  │ Patroni HA       │
        │ master+2     │  │ 1 primary +      │
        │  slaves      │  │ 2 sync standbys  │
        └──────┬───────┘  └─────────┬────────┘
               ↓                     ↓
                                                L4: 大 blob
        ┌────────────────────────────────────┐
        │ S3 / OSS (multi-AZ default)         │
        │ transcripts/<tenant_id>/<sess>.jsonl │
        └─────────────────────────────────────┘
```

### 4.1 L1 — DNS / Edge

- **Cloud DNS**：60s TTL（HA failover 时快速切）
- **Anycast / GeoDNS**（可选）：用户路由到最近 region
- **DDoS 防护**：CDN 层挡（Cloudflare / Akamai）—— qwen daemon 本身不抗 DDoS

### 4.2 L2 — Ingress

**Sticky 策略选择**：

| 策略 | 优点 | 缺点 | 推荐 |
|---|---|---|---|
| Cookie by `tenant_id` | 简单 | 同 tenant 多 session 全打到 1 pod，单 pod 过载 | ⚠ 小 tenant OK，大 tenant 风险 |
| **Cookie by `session_id`** | 粒度细，负载均匀 | client 必须保留 cookie | ✓ **推荐** |
| Source IP hash | 无 cookie 依赖 | NAT / VPN 场景失效 | ✗ 不推荐 |
| Consistent hashing by user-id | 跨 channel 同 user 路由一致 | user-id 不一定可见 | ⚠ 'user' scope 时考虑 |

**Cookie 安全**：

```
Cookie name: qwen-aff
Cookie value: HMAC-SHA256(sessionId || nonce, server-secret)
Cookie attrs: HttpOnly; Secure; SameSite=Strict; Max-Age=86400
```

防 cookie 篡改 → 不能伪造路由到任意 pod（防 DoS 单 pod）。

**Ingress 配置示例**：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: qwen-daemon
  annotations:
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/session-cookie-name: "qwen-aff"
    nginx.ingress.kubernetes.io/session-cookie-hash: "sha256"
    nginx.ingress.kubernetes.io/session-cookie-max-age: "86400"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"  # SSE long idle
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/upstream-fail-timeout: "10"
    nginx.ingress.kubernetes.io/upstream-max-fails: "2"
spec:
  rules:
  - host: daemon.qwen.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: qwen-daemon
            port: {name: http}
```

### 4.3 L3a — Daemon Pod

**StatefulSet 关键字段**：

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qwen-daemon
spec:
  replicas: 3
  serviceName: qwen-daemon
  podManagementPolicy: Parallel              # 并行启动 / 重启
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 0
      maxUnavailable: 1                       # 同时只允许 1 pod 不可用
  template:
    spec:
      terminationGracePeriodSeconds: 90       # graceful drain 时间
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels: {app: qwen-daemon}
            topologyKey: kubernetes.io/hostname    # 同 host 不放 2 pod
      containers:
      - name: daemon
        image: qwen-daemon:v1.0
        readinessProbe:
          httpGet: {path: /healthz, port: 8080}
          periodSeconds: 5
          failureThreshold: 2                  # 10s 内 2 次失败摘除
          successThreshold: 1
        livenessProbe:
          httpGet: {path: /livez, port: 8080}
          periodSeconds: 30
          failureThreshold: 3                  # 90s 失败重启
        startupProbe:
          httpGet: {path: /healthz, port: 8080}
          periodSeconds: 5
          failureThreshold: 30                 # 150s 启动窗口
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "qwen-daemon drain --timeout 80"]
        resources:
          requests: {cpu: "1", memory: "2Gi"}
          limits: {cpu: "4", memory: "8Gi"}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: qwen-daemon
spec:
  minAvailable: 2
  selector:
    matchLabels: {app: qwen-daemon}
```

**容量规划 N+1**：
- 峰值并发 session = X
- 单 pod 容量 = Y
- replicas ≥ ceil(X/Y) + 1（多一个备容失败）

### 4.4 L3b — 共享状态层

详见 [§15 持久层](./15-persistence-and-storage.md)；HA 视角下补充：

**Postgres Patroni**：

```
       ┌────────────┐
       │  Patroni   │  自动选主 (30-60s)
       │  + etcd    │
       └─────┬──────┘
             │
   ┌─────────┼─────────┐
   ↓         ↓         ↓
┌─────┐   ┌─────┐   ┌─────┐
│ pri │←──│ sync│←──│ sync│   synchronous_commit=on
│     │   │stby1│   │stby2│   2 sync standby = 写延迟翻倍
└─────┘   └─────┘   └─────┘   primary 失败 → standby 接管
                                RPO = 0 (sync rep)
```

**Redis Sentinel**：

```
   ┌──────────┐      ┌──────────┐      ┌──────────┐
   │ Sentinel │      │ Sentinel │      │ Sentinel │   3 个仲裁节点
   └─────┬────┘      └─────┬────┘      └─────┬────┘   majority quorum
         │                  │                  │
         └────────┬─────────┴────────┬─────────┘
                  ↓                  ↓
              ┌───────┐          ┌───────┐
              │ Redis │ ─repl→  │ Redis │
              │ master│          │ slave │
              └───────┘          └───────┘
```

Sentinel 检测 master 失败（30s）→ 选主切换 → daemon 通过 sentinel 协议自动重连。

### 4.5 L4 — Object Storage

S3 / 阿里云 OSS / minio：
- 跨 AZ 多副本默认（云厂商 SLA 99.99%）
- 跨 region replication（DR 用）
- Lifecycle policy：30 天后转 IA / Glacier 降本

**Transcript 双写策略**：

```ts
async function appendToTranscript(sessionId: string, message: TranscriptMessage) {
  const localPath = `/var/cache/qwen/transcripts/${sessionId}.jsonl`
  
  // 1. 本地 append (fast，每 message 都做)
  await fs.appendFile(localPath, JSON.stringify(message) + '\n')
  
  // 2. 标记 dirty（异步 flush 到 S3）
  dirtyTranscripts.add(sessionId)
}

// 后台 flush（每 5s 一次）
setInterval(async () => {
  for (const sid of dirtyTranscripts) {
    const local = await fs.readFile(`/var/cache/qwen/transcripts/${sid}.jsonl`)
    const s3Key = `tenants/${tenantOf(sid)}/transcripts/${sid}.jsonl`
    await s3.putObject({ Key: s3Key, Body: local })
    dirtyTranscripts.delete(sid)
  }
}, 5000)
```

**Pod 失败时丢失风险**：最多丢失最近 5s 的 transcript（未 flush 的）—— 业务上是 LLM 几个 token / 几句话，可接受。如严格要求 → 改同步写 S3（性能下降 20-50%）。

## 五、SSE Reconnect 协议

SSE 长连接断开后客户端如何无缝恢复，是 daemon HA 的核心 UX 体验。

### 5.1 协议设计

参考 [HTML5 EventSource](https://html.spec.whatwg.org/multipage/server-sent-events.html) `Last-Event-ID` header 标准。

**Event 格式**：

```
id: evt-12345
event: message_part
data: {"type":"text","content":"..."}

id: evt-12346
event: tool_call_request
data: {"tool":"Bash","args":{"cmd":"ls"}}
```

每个 event 携带单调递增 `id`（per-session）。

**Client 重连**：

```
GET /v1/session/sess-abc/events HTTP/1.1
Last-Event-ID: evt-12345
Authorization: Bearer ...
```

### 5.2 Daemon 端实现

```ts
// packages/server/src/routes/sse.ts (新)
app.get('/v1/session/:sid/events', async (c) => {
  const sessionId = c.req.param('sid')
  const lastEventId = c.req.header('Last-Event-ID')
  const session = await loadSession(sessionId)
  
  return c.body(new ReadableStream({
    async start(controller) {
      // 1. 发送 missed events（如果 client 提供 Last-Event-ID）
      if (lastEventId) {
        const missedEvents = await replayEventsAfter(sessionId, lastEventId)
        for (const evt of missedEvents) {
          controller.enqueue(formatSseEvent(evt))
        }
      }
      
      // 2. 订阅实时 events
      const unsubscribe = session.subscribe(controller)
      c.req.signal.addEventListener('abort', unsubscribe)
    },
  }), {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  })
})

async function replayEventsAfter(sessionId: string, lastEventId: string) {
  // 从 transcript 重读 lastEventId 之后的 events
  const transcript = await loadTranscript(sessionId)
  const startIdx = transcript.findIndex(e => e.id === lastEventId) + 1
  return transcript.slice(startIdx)
}
```

### 5.3 关键设计点

| 点 | 说明 |
|---|---|
| **event id = transcript 行号** | 直接复用 PR#3739 transcript 持久化，不需额外 event store |
| **新 pod 路由后续接** | 新 pod loadSession 重建 → replayEventsAfter 拉历史 → 客户端无缝 |
| **TTL 重放窗口** | 仅保留最近 24h replay 窗口（旧 session 不无限 replay）|
| **back-pressure** | client 慢消费 → daemon buffer 满 → 主动断连 + 让 client 重连 |

## 六、LLM Streaming 中断的 7 种场景

LLM streaming 是 daemon HA 最棘手的场景 —— 上游 Provider 已开始计费，下游用户已看到部分输出。

### 6.1 场景分类

| # | 场景 | 触发 | LLM Provider 端 | 客户端 UI |
|---|---|---|---|---|
| 1 | Pod crash mid-stream | OOM / kernel panic | call 仍在跑（计费）→ TCP 断 | "session interrupted, retry?" |
| 2 | Pod graceful drain | 滚动升级 | drain 时已收完 streaming | client 收完 ack 后 reconnect |
| 3 | Network partition daemon ↔ Provider | upstream 网络 | call 失败重试 | 显示重试中 |
| 4 | Network partition daemon ↔ client | client 侧网络 | streaming 继续 | client 重连续接 |
| 5 | Provider 端限流 / 429 | quota 耗尽 | 返回 429 | UI 提示 quota，等待重试 |
| 6 | Postgres 不可达（无法写 transcript）| L3 故障 | 收到 streaming 但无法持久化 | UI 显示 "degraded mode, reduced safety" |
| 7 | Client 端主动断 | 用户关 tab / kill -9 | call 继续到完成 | 无 |

### 6.2 各场景应对

**场景 1: Pod crash mid-stream**
```
旧 pod (崩溃)              新 pod (sticky 重路由)
  ↓                         ↓
LLM call 已收到一半         loadSession + replay
TCP 断                       transcript 显示 partial assistant message
                             （PR#3739 fork resume 重建上下文）
                             session 标记 status='interrupted'
                             SSE 事件: { type: 'session_interrupted',
                                          reason: 'pod_crash',
                                          last_offset: 12345 }
```

**关键决策**：**新 pod 不重新发起同 LLM call**——
- 避免重复计费
- 避免 prompt 不一致（temperature 抖动）
- 让用户在 UI 上 retry 决定

`POST /session/:id/retry-from-checkpoint` 让用户主动续。

**场景 2: Pod graceful drain**
```
SIGTERM
  ↓
preStop hook: qwen-daemon drain --timeout 80
  ↓
1. /healthz 返回 unhealthy → 新连接不进来
2. 已有 active streaming session 标记 draining=true
3. 等待所有 in-flight LLM streaming 完成（max 80s）
4. 完成 → fsync transcript + S3 flush
5. 通知 SSE subscribers: { type: 'pod_draining',
                            reconnect_after_ms: 1000 }
6. 关闭 MCP/LSP/sandbox 子进程
7. exit 0
```

**关键设计**：drain 时间 80s vs k8s grace 90s 留 10s buffer。

**场景 3: Network partition daemon ↔ Provider**
- daemon 内置 LLM call retry（exponential backoff，3 次）
- 失败后通过 SSE 通知 client `{type: 'tool_error', error: 'provider_unreachable'}`
- 不切 pod（pod 本身正常）

**场景 4: Network partition daemon ↔ client**
- daemon 端继续接收 streaming + 写 transcript
- client 重连后通过 Last-Event-ID 拉到完整结果
- 这是 SSE reconnect 协议设计的最常见 case

**场景 5: Provider 限流**
- daemon 主动 backoff（按 Retry-After header）
- SSE 通知 `{type: 'rate_limited', retry_after_ms: 30000}`
- session 状态保留，等待重试

**场景 6: Postgres 不可达 → degraded mode**
- daemon 进入 degraded：
  - 接受现有 session 操作（基于内存 + S3 transcript）
  - 拒绝新 session 创建（503）
  - audit log 缓冲到本地 SQLite
  - permission_decisions 使用 Redis cache（read-only）
- Postgres 恢复 → 自动 flush 缓冲

**场景 7: Client 主动断**
- daemon 端继续完成（避免 LLM call 浪费）
- 完成后等待 client 24h 内回连续接（PR#3739 transcript 已存）
- 24h 后 session 进入 archived，保留但需 explicit LoadSession

## 七、Failover 时序图

### 7.1 Pod Crash

```
T=0s    pod-2 OOM crash
        ├─ 内核杀进程
        └─ TCP 连接全部 RST
T=1s    Ingress 检测 pod-2 端口不通
        └─ /healthz 5s 周期内未响应（已 fail 1）
T=5s    /healthz fail-2 → Ingress 摘除 pod-2
T=5-10s Client 检测 SSE 断（TCP RST 立即知晓）
        └─ 自动重连（指数退避 1s, 2s, 4s）
T=10s   Client reconnect → Ingress sticky cookie 仍指 pod-2
        └─ pod-2 仍 unhealthy → fallback 到 pod-1 / pod-3
        └─ 新 cookie 设置 → 同 session 此后路由到新 pod
T=10-15s 新 pod loadSession(sess-abc)
        ├─ 读 Postgres sessions 表获取 transcript_path
        ├─ 从 S3 / 本地缓存读 transcript JSONL
        ├─ PR#3739 fork resume 重建上下文
        ├─ 初始化新 MCP/LSP server（启动 1-3s）
        └─ 标记 session.status='interrupted'
T=15s   Client 收到首个 SSE event:
        { type: 'session_resumed',
          status: 'interrupted',
          reason: 'pod_crash',
          last_completed_message_id: 'msg-42' }
        └─ UI 显示 "Connection restored. Last response was interrupted, [Retry?]"
T=20s   k8s 检测 pod-2 livez fail
        └─ 重启 pod-2

总停机时间: ~10-15s（client 视角）
```

### 7.2 Postgres Failover

```
T=0s    Postgres primary 节点失败
        └─ daemon 检测连接断（query timeout 5s）
T=5s    daemon 进入 degraded mode
        ├─ active session 继续（内存 + S3）
        ├─ 新 session 创建拒绝（503）
        ├─ audit log 缓冲本地 SQLite
        └─ permission_decisions 用 Redis read-only cache
T=5-30s Patroni 检测 primary down
        ├─ etcd quorum 投票
        └─ 选举 sync standby 1 为新 primary
T=30s   新 primary 接受写
        └─ daemon 重连成功
T=30-35s daemon 退出 degraded mode
        ├─ flush 本地 audit buffer 到 Postgres
        └─ 恢复正常
T=60s   旧 primary 作为 standby 重新加入

总服务影响: ~30s 新 session 创建被拒（503）
            active session 不受影响
```

### 7.3 Region Down (DR)

```
T=0s     us-west-2 region down (e.g. AZ 全部失败)
T=0-60s  Cloud DNS health check 检测 region 不可达
T=60s    DNS failover → us-east-1
T=60-180s us-east-1 cold standby daemon pod 启动
         ├─ 从 Postgres logical replica（已 promote）读
         └─ 从 S3 cross-region replica 读 transcript
T=180s   Client DNS 缓存过期 → 解析到 us-east-1 IP
T=180-240s Client 重连 + session 重建

总停机: ~3-4min（region 级灾难，业务上需告知用户）
RPO: < 5s（Postgres logical rep + S3 跨 region rep 默认）
```

## 八、Graceful Shutdown 详细步骤

```
SIGTERM 接收 (k8s 滚动升级 / scale down)
  │
  ├─ 0s: 信号 handler 触发
  │     ├─ daemon.state = 'draining'
  │     └─ /healthz 返回 503 (Ingress 5s 内摘除)
  │
  ├─ 5s: Ingress 已摘除新连接进来
  │     ├─ 现有 SSE 连接保留
  │     └─ 现有 active prompt 继续
  │
  ├─ 5-80s: 等待 in-flight 工作完成
  │     ├─ active LLM streaming 完成（多数 30s 内）
  │     ├─ active tool call 完成（Bash/Edit 通常秒级）
  │     ├─ background tasks: 状态保存到 Postgres
  │     │   ├─ shell task → 标记 status='paused'，pod 启动后可恢复
  │     │   ├─ agent task → 同上
  │     │   ├─ monitor task → 直接终止（重启时 spawn 命令重新执行）
  │     │   └─ dream task → 立即中断，重启不恢复
  │     ├─ MCP server 子进程 → 优雅关闭
  │     ├─ LSP server 子进程 → 优雅关闭
  │     └─ sandbox 子进程 → 优雅关闭（OS-user kill -TERM）
  │
  ├─ 80s: 强制 fsync
  │     ├─ transcript 本地文件 fsync
  │     ├─ 强制 flush S3 dirty queue
  │     └─ permission_decisions 任何 dirty entry → Postgres
  │
  ├─ 85s: 通知 SSE subscribers
  │     └─ broadcast { type: 'pod_draining',
  │                    reconnect_after_ms: 1000 }
  │
  ├─ 87s: 关闭 server.listen()
  │
  └─ 90s: process.exit(0)

如果 90s 还没退出 → k8s SIGKILL（数据可能丢失最近未 fsync 部分）
```

## 九、Sticky Session 路由策略详解

### 9.1 选择 sessionId 而非 tenantId

| 维度 | tenant 粘性 | session 粘性 |
|---|---|---|
| 负载均衡 | 大 tenant 单 pod 过载 | 各 session 均匀分布 |
| 故障半径 | 1 pod down → 1 tenant 全部受影响 | 1 pod down → 散布的 sessions 受影响 |
| 实现复杂度 | 简单 | client 需保留 cookie |
| 决策 §1 'single' scope | OK | **OK，更细粒度** |

**例外**：'user' scope（同 user-id 跨 channel 共享）应按 user-id 粘性。

### 9.2 cookie 内容

```
qwen-aff = base64( HMAC-SHA256(sessionId, server-secret) )
```

server-secret 通过 k8s Secret 注入，定期 rotate（Stage 6 SaaS 90 天）。

### 9.3 cookie 生命周期

```
首次创建 session → daemon 生成 cookie → Set-Cookie header
                                          ↓
client 后续所有请求带 cookie → Ingress 解析 cookie → 路由
                                          ↓
session 销毁 / 24h 未活跃 → cookie 过期
```

### 9.4 cookie 失效场景

| 场景 | 行为 |
|---|---|
| Cookie 过期 | Ingress 用默认 RR 路由 → 新 cookie |
| Cookie 篡改 | HMAC 验证失败 → 视为无 cookie，RR 路由 |
| Sticky pod 不可达 | Ingress 自动 fallback 到次优 pod，写新 cookie |
| Pod 重启后 cookie 仍指它 | OK，pod 重新 loadSession |

## 十、Chaos Engineering 测试矩阵

每周运行的 chaos 测试集（参考 Netflix Chaos Monkey + LitmusChaos）：

| # | 测试 | 注入方式 | 期望行为 | SLO 影响 |
|---|---|---|---|---|
| C1 | 单 pod kill -9 | `kubectl delete pod` | client SSE 重连 < 15s | < 0.01% |
| C2 | 单 pod OOM | 注入 mem leak | livez fail → restart | < 0.01% |
| C3 | 单 pod 网络隔离 | iptables drop | Ingress 摘除 | < 0.01% |
| C4 | Postgres primary 杀 | `pg_ctl stop` | Patroni failover < 30s | 30s 503 for 新 session |
| C5 | Postgres 网络抖动 | tc qdisc 注入 100ms 抖动 | daemon 优雅降级 | 性能下降 20% |
| C6 | Redis master 杀 | `redis-cli shutdown` | Sentinel failover < 30s | quota / cache miss |
| C7 | S3 间歇性 5xx | 代理注入 50% fail | dirty queue 重试，本地缓存兜底 | 0 |
| C8 | 磁盘满 | `dd if=/dev/zero` 灌满 | daemon 拒绝新 transcript 写，触发 alert | 503 |
| C9 | 单 pod CPU 100% | `stress --cpu` | livez 检测降级 → 摘除 | < 0.1% |
| C10 | 滚动升级 | `kubectl rollout restart` | maxUnavailable=1 平滑切 | 0 |
| C11 | Network partition daemon ↔ Postgres | 单向 drop | degraded mode | 见 §7.2 |
| C12 | LLM provider 大量 429 | mock provider | exponential backoff | UI 显示 rate-limit |
| C13 | 大量 client 同时重连 | 10000 concurrent reconnects | Ingress 节流，daemon 排队 | < 1s 延迟 |
| C14 | Subscribers 慢消费 | 故意慢 client | back-pressure → 主动断 | client 重连 |
| C15 | 跨 region failover drill | 主 region 全切 | DNS + cold standby ≤ 5min | DR 演练 |

## 十一、监控与告警

### 11.1 关键指标 (Golden Signals)

| 类别 | 指标 | 告警阈值 |
|---|---|---|
| **Latency** | p99 prompt latency | > 30s 持续 5min |
| | p99 SSE event latency | > 1s |
| | LLM streaming first-token p95 | > 5s |
| **Traffic** | RPS per pod | 突增 / 骤降 50% |
| | Concurrent sessions per pod | > 200 (容量上限) |
| | New session rate | > 10/s |
| **Errors** | HTTP 5xx rate | > 0.1% |
| | LLM provider error rate | > 5% |
| | Tool call error rate | > 10% |
| | Permission deny rate | > 20% (可能攻击) |
| **Saturation** | Pod CPU | > 80% 持续 5min |
| | Pod memory | > 85% |
| | Postgres connections | > 80% pool |
| | S3 throttle | > 0 |

### 11.2 健康检查端点

```ts
// /healthz - readiness (Ingress 用)
app.get('/healthz', async (c) => {
  const checks = {
    postgres: await pingPostgres(),
    redis: await pingRedis(),
    s3: await pingS3(),
    diskUsage: await checkDiskUsage(),
  }
  
  const ready = checks.postgres && checks.redis && checks.diskUsage < 90
  return c.json(checks, ready ? 200 : 503)
})

// /livez - liveness (k8s 重启用)
app.get('/livez', async (c) => {
  // 仅检查 daemon 自身是否响应（不检查依赖）
  const lastTickMs = Date.now() - eventLoopLastTick
  return c.json({ alive: lastTickMs < 5000 }, lastTickMs < 5000 ? 200 : 503)
})

// /metrics - Prometheus
app.get('/metrics', metricsHandler)
```

### 11.3 SLO 监控

```yaml
# Prometheus alerting rule
groups:
- name: qwen-daemon-slo
  rules:
  - alert: AvailabilityBelow999
    expr: |
      sum(rate(http_requests_total{status!~"5.."}[1h])) /
      sum(rate(http_requests_total[1h])) < 0.999
    for: 5m
  
  - alert: ErrorBudgetBurn
    expr: |
      (1 - (sum(rate(http_requests_total{status!~"5.."}[1h])) /
       sum(rate(http_requests_total[1h])))) > 14.4 * (1 - 0.999)
    for: 5m
    annotations:
      summary: "Burning 30 days of error budget in 1 hour"
```

## 十二、SLO 设计

### 12.1 分级 SLO

| 级别 | Availability | RTO | RPO | 月度允许停机 |
|---|---|---|---|---|
| 个人 / OSS | 99% (best effort) | N/A | N/A | 7.2h |
| **Stage 6 SaaS 起步** | **99.9%** | 5min | 5s | **43min** |
| 企业 SLA | 99.95% | 1min | 5s | 22min |
| 金融 / 医疗 | 99.99% | 30s | 1s | 4.3min |

### 12.2 错误预算策略

```
99.9% SLO = 0.1% 错误预算 = 43.2 分钟 / 月

预算消耗超 50% (21min) → freeze risky deploys
预算消耗超 80% (35min) → 仅允许 emergency hotfix
预算耗尽 → 全面 incident review，下个周期减半部署速度
```

### 12.3 SLI 定义

```
SLI 1: HTTP 成功率
  good = sum(http_requests{status<500})
  total = sum(http_requests)
  SLI = good / total

SLI 2: SSE 重连成功率
  good = sum(sse_reconnect{result='success'})
  total = sum(sse_reconnect)

SLI 3: Session resume 正确性
  good = sum(session_resume{transcript_intact='true'})
  total = sum(session_resume)
```

复合 SLO = SLI1 AND SLI2 AND SLI3。

## 十三、Degraded Mode 退化策略

各种依赖失败时 daemon 进入 degraded mode 而非全停。

| 依赖失败 | 退化策略 | 影响 |
|---|---|---|
| Postgres 不可达 | active session 走内存 + S3，新 session 拒绝 | 新创建 503 |
| Redis 不可达 | quota 用 Postgres（慢路径），subscribers 退化为单 pod 内 | 跨 pod 协调失败 |
| S3 不可达 | transcript 仅本地，等恢复后 flush | 重启数据丢失风险 |
| LLM Provider 全部失败 | session 保留，return tool error | 无法继续对话 |
| MCP 单 server 失败 | 该 MCP tool 不可用，其他工具继续 | 部分功能降级 |
| LSP 失败 | 静默降级到无 LSP（拼写检查不可用）| UX 降级 |
| Sandbox 失败 | 拒绝新 shell 类 tool call | 部分工具不可用 |

**核心原则**：宁愿部分功能降级，不要全停。

## 十四、与决策的协同

| 决策 | HA 影响 |
|---|---|
| §1 sessionScope='single' | 多 client 共 session → sticky 必须按 sessionId 而非 client |
| §2 单 daemon 进程承载全部 session | HA 通过多 pod，每 pod 内部仍单进程多 session |
| §3 MCP per-workspace | 新 pod 重启 MCP（1-3s 启动延迟）|
| §4 FileReadCache per-session | 新 pod 重建（首次 read 需重 stat → 命中率短期下降）|
| §5 Permission 第 4-5 mode | failover 后未决 permission 请求需重发 |
| §6 多 client fan-out + first responder | Redis pub/sub 跨 pod 同步 subscribers + first responder lock 用 Redis SETNX |
| §11 多租户 + sandbox | sandbox 子进程不可跨 pod 迁移，failover 后重建 |
| §12 越权防御 | HA 下加固：cookie HMAC 防伪造路由 |

## 十五、与 OpenCode / Claude Code HA 对比

| 维度 | OpenCode | Claude Code | qwen daemon Stage 6 |
|---|---|---|---|
| daemon HA 设计 | ❌ 单进程 | ❌ 无 daemon | ✓ 5 层架构 |
| Sticky session | N/A | N/A | ✓ sessionId cookie |
| Failover RTO | N/A | N/A | ✓ < 15s pod / < 30s Postgres |
| Graceful drain | minimal | N/A | ✓ 90s |
| Chaos testing | ❌ | ❌ | ✓ 15 项每周 |
| Multi-region DR | ❌ | ❌ | ✓ 可选 |
| SLO 公开 | ❌ | ❌ | ✓ 99.9% 起步 |

**OpenCode** 设计目标是单机 / 小团队，无内置 HA；要 HA 需自行配反向代理 + 数据库主从（社区有少量实践，无官方支持）。

**Claude Code** 是 CLI，无 daemon，HA 不在范畴。

**qwen daemon** Stage 6 SaaS 模式直接对标云原生 HA 实践。

## 十六、Stage 6 → Stage 7+ 演进

```
Stage 6  起步：3 pod / 1 region / 99.9% SLO
            ├─ 多 AZ 部署
            ├─ Postgres Patroni
            ├─ Redis Sentinel
            └─ 基础 Chaos testing

Stage 6.5 加 region：跨 AZ + DR region
            ├─ Cross-region S3 replication
            ├─ Postgres logical rep
            └─ DNS failover

Stage 7   多活：Active-Active 多 region
            ├─ Anycast / GeoDNS
            ├─ Postgres bidirectional rep (BDR)
            ├─ Conflict resolution (CRDT for permission_decisions)
            └─ 99.99% SLO

Stage 8   全球：edge daemon + 区域中心
            ├─ Edge cache (transcript / permission decisions)
            ├─ 主区域中心 Postgres + S3
            └─ 区域间 latency < 50ms
```

## 十七、一句话总结

**Qwen daemon HA = 5 层架构（Edge DNS → Ingress sticky-by-sessionId → StatefulSet pod N≥3 → Postgres Patroni + Redis Sentinel + S3 多 AZ）+ SSE Last-Event-ID 重连协议（复用 PR#3739 transcript 持久化作为 event store）+ LLM streaming 中断 7 类场景明确处理（核心：不自动续接避免重复计费）+ 90s graceful drain（80s 等待 in-flight + 10s buffer）+ degraded mode（依赖失败降级而非全停）+ 15 项 Chaos 测试每周 + 99.9% SLO 起步。关键设计哲学：daemon 高度有状态 → HA 不是任意切，而是 sticky + transcript-first 重建（PR#3739 是 HA 的隐藏基础设施）。**

---

[← 返回 README](./README.md)
