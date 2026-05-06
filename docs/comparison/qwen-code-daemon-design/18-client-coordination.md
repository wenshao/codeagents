# 18 — 多端协调策略：subscriber 协议 / liveness / takeover

> [← 上一篇：远端 CLI 模式](./17-remote-cli-mode.md) · [回到 README](./README.md)

> 决策 §1 + §6 让一个 session 可被多 client 同时订阅；本章定义这些 client 如何协调（liveness / active typer / takeover / exclusive 模式 / IM bot 多用户分摊），保住 collaboration 红利的同时解决 stale connection 等运维痛点。

## 一、TL;DR

| 维度 | 默认 | 可选（企业）|
|---|---|---|
| Subscriber 数量 | 不限（max_subscribers=20 防滥用）| 限制可配 |
| 同类型多个（CLI×N / WebUI×N）| ✓ 允许 | exclusive_per_type 模式拒绝 |
| Liveness 协议 | 30s heartbeat / 90s 超时 / TCP RST 即时剔除 | 同 |
| Active Typer 协调 | "X is typing..." 提示 + 5s 让出 | 同 |
| Takeover | 显式 `--takeover` flag | 同 |
| Exclusive 模式 | ✗ | tenant config 启用 |
| IM bot 多用户 | im_bot kind 单独配额 5 | 可调 |
| 总指导原则 | **协调 > 排斥**（live collaboration first）| —— |

## 二、设计目标

### 2.1 保住的收益

- **Pair programming**：Alice + Bob 同 session
- **多 terminal 工作流**：tmux 多 pane 各看一面
- **跨机器接力**：办公室笔记本 → 家里 desktop 无缝
- **Web UI 多 tab**：浏览器多 tab 同时翻历史 / 看实时
- **IM 多人**：同事们在微信/钉钉里观察同一 session
- **决策 §6 first responder**：任意 client 应答 permission

### 2.2 要解决的痛点

- **Stale connection**：CLI kill -9 没干净断，残留订阅占资源
- **谁在打字困惑**：多端同时输入 prompt，UX 混乱
- **资源滥用**：恶意 / bug 创建过多 subscriber
- **企业合规**：某些场景要审计 "同时连接的人是谁"

### 2.3 拒绝的反模式

- ❌ 全局 hard limit "1 CLI per session"（[§17 §一](./17-remote-cli-mode.md) 列出 7 个被破坏场景）
- ❌ 第一连接独占（违反 §1 'single' scope 哲学）
- ❌ kick everyone on new connection（默认就是吵架）

## 三、Subscriber 模型

### 3.1 数据结构

```ts
// packages/server/src/session/Subscriber.ts
interface Subscriber {
  id: ClientId                              // 'cli-laptop-alice-uuid'
  kind: ClientKind                           // 'cli' | 'webui' | 'ide' | 'im_bot' | 'sdk' | 'mobile'
  userId: string | null                      // 'alice@example.com'（如有 SSO）
  hostname: string | null                    // 'laptop' / 'desktop'（client 上报）
  ip: string                                 // SSE 连接 IP
  userAgent: string                          // browser UA / CLI version
  joinedAt: number                           // 加入时间戳
  lastHeartbeatAt: number                    // 最近 heartbeat
  lastEventSentAt: number                    // 最近 daemon 推 event
  capabilities: ClientCapabilities           // 见 §17 §3.5
  state: 'active' | 'idle' | 'typing' | 'stale'
  ssePosition: string | null                 // last delivered event id
}

class Session {
  subscribers = new Map<ClientId, Subscriber>()
  
  async addSubscriber(sub: Subscriber, mode: SessionPolicyMode = 'shared') {
    if (mode === 'exclusive_per_type') {
      await this.enforceExclusive(sub.kind)  // 见 §六.4
    }
    if (this.subscribers.size >= this.maxSubscribers) {
      throw new TooManySubscribersError()
    }
    this.subscribers.set(sub.id, sub)
    this.broadcast({ type: 'subscriber_joined', subscriber: redact(sub) })
  }
  
  removeSubscriber(id: ClientId, reason: string) {
    const sub = this.subscribers.get(id)
    if (!sub) return
    this.subscribers.delete(id)
    if (this.activeTyper === id) this.activeTyper = null
    this.broadcast({ type: 'subscriber_left', id, reason })
  }
}
```

### 3.2 ClientId 生成

```
ClientId = <kind>-<host>-<unguessable-random-base32>
        = cli-laptop-alice-b7m2k9...
        = webui-firefox-h3p8j2...
        = im_bot-wechat-x9k4n1...
```

unguessable 防猜测（[§12 §3.1.A4](./12-horizontal-privilege-defense.md) 同款）。

### 3.3 Subscriber 列表 API

任何 subscriber 都可以查看当前订阅列表（透明协作）：

```http
GET /v1/session/<sid>/subscribers HTTP/1.1
Authorization: Bearer ...

Response:
[
  {
    "id": "cli-laptop-...",
    "kind": "cli",
    "userId": "alice@example.com",
    "hostname": "laptop",
    "joinedAt": 1714983600000,
    "state": "typing",
    "userAgent": "qwen-cli/1.0.0 linux"
  },
  {
    "id": "webui-firefox-...",
    "kind": "webui",
    "userId": "alice@example.com",
    "joinedAt": 1714983710000,
    "state": "idle",
    "userAgent": "Mozilla/5.0 ..."
  },
  {
    "id": "im_bot-wechat-...",
    "kind": "im_bot",
    "userId": null,
    "joinedAt": 1714983800000,
    "state": "active",
    "userAgent": "qwen-bot/1.0 wechat-channel"
  }
]
```

返回字段经过 redact——`ip` 不暴露给其他 subscriber（仅 audit log 内部用）。

## 四、6 类 Client Kind 定义

### 4.1 完整表

| Kind | 描述 | 默认上限 | Capabilities | 典型行为 |
|---|---|---|---|---|
| `cli` | TUI 终端命令行 | 5 | editor / clipboard / browser / file_picker | 主输入 + 实时输出 |
| `webui` | 浏览器 Web UI | 5 | clipboard / browser / file_picker / notification | 副渲染 + 历史回放 |
| `ide` | IDE 插件（VSCode / IntelliJ）| 3 | editor / clipboard / browser / file_picker / notification | 内嵌 chat panel |
| `im_bot` | IM bot（微信/钉钉/Telegram）| 10 | (none, 仅文本) | 多人观察 + 单 user 输入 |
| `sdk` | SDK 应用（自动化 / 测试 / 评测）| 3 | (按需声明) | 编程式访问 |
| `mobile` | 移动端 App | 3 | clipboard / browser / notification | 移动端 thin client |

**总上限默认 20**（所有 kind 加起来）。

### 4.2 Kind 声明

CLI 启动时 POST：

```http
POST /v1/session/<sid>/subscribe HTTP/1.1
Authorization: Bearer ...
Content-Type: application/json

{
  "client_kind": "cli",
  "client_id": "cli-laptop-alice-b7m2k9...",
  "client_info": {
    "name": "qwen-cli",
    "version": "1.0.0",
    "platform": "linux",
    "hostname": "laptop"
  },
  "client_capabilities": {
    "open_editor": true,
    "clipboard": true,
    "open_browser": true,
    "file_picker": true,
    "notification": false
  }
}
```

daemon 校验 + 加入 subscribers + 返回 SSE 流的 endpoint。

### 4.3 Kind 不可伪造

每个 kind 的 token scope 限制（决策 §11 多租户）：
- `webui` token 不能声明 `cli` kind（防止绕过 cli 上限）
- `im_bot` token 不能声明 `cli` kind（防止 IM bot 当成 CLI 抢 active typer）
- daemon 端校验 `token.allowedKinds.includes(declared_kind)`

```jsonc
// token 定义
{
  "id": "tok-alice-im",
  "scope": ["im_bot:*"],
  "allowedKinds": ["im_bot"]   // 仅允许声明 im_bot
}
```

## 五、Liveness 协议

### 5.1 Heartbeat 频率

| 间隔 | 用于 |
|---|---|
| **30s 标准** | 默认 client heartbeat 间隔 |
| **10s 加密** | mTLS / 高敏感场景，更快检测 stale |
| **60s 弱网** | 移动网络 / IM bot，省流量 |

```ts
// CLI 端
setInterval(async () => {
  try {
    await fetch(`${daemonUrl}/v1/session/${sid}/heartbeat`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        clientId,
        state: currentState,           // 'active' | 'idle' | 'typing'
        ssePosition: lastEventId
      })
    })
  } catch {
    // 网络不通，下次重试
  }
}, 30_000)
```

### 5.2 超时与剔除

```ts
// daemon 端 cleanup loop（每 30s）
class SessionCleaner {
  cleanup() {
    for (const session of allSessions) {
      const now = Date.now()
      for (const sub of session.subscribers.values()) {
        const idle = now - sub.lastHeartbeatAt
        if (idle > 90_000) {
          session.removeSubscriber(sub.id, 'liveness_timeout')
        } else if (idle > 60_000) {
          // 灰度：标记 stale，UI 显示警告
          if (sub.state !== 'stale') {
            sub.state = 'stale'
            session.broadcast({ type: 'subscriber_stale', id: sub.id })
          }
        }
      }
    }
  }
}
```

### 5.3 即时剔除（TCP RST 检测）

SSE 连接 TCP-level RST 即时通知 daemon——比心跳超时快得多：

```ts
// daemon 端
sseStream.on('close', () => {
  session.removeSubscriber(subId, 'sse_disconnected')
})
```

**实测剔除时间**：
- 客户端 graceful close → < 1s
- 网络断开 + TCP RST → 1-30s（取决于 OS keepalive 配置）
- TCP 状态丢失（NAT 表过期）→ 60-90s（依赖 heartbeat 超时兜底）

### 5.4 子连接超时差异化

| 场景 | 超时 | 理由 |
|---|---|---|
| `cli` 没断但 90s 无心跳 | 剔除 | 标准 |
| `webui` 浏览器 tab 切到后台 | **延长 5min** | 浏览器后台节流，不应过早剔除 |
| `mobile` App 切后台 | **延长 10min** | iOS / Android 后台限制更狠 |
| `im_bot` 网络抖 | **延长 5min** | IM 平台有自己的 webhook 重试 |
| `sdk` evaluating | **延长 30min** | benchmark / 大规模评测可能长跑 |

通过 `client_kind` 决定超时阈值。

## 六、Active Typer 协调

### 6.1 状态机

```
   ┌──────────────────────────────┐
   │  No active typer (idle)       │
   └──────────────┬───────────────┘
                  ↓ takeTypingFocus
   ┌──────────────────────────────┐
   │  Active typer = client X      │
   │  (UI shows "X is typing")     │
   └──────────────┬───────────────┘
                  │
       5s no input ↓ ↑ keystroke
                  │
   ┌──────────────────────────────┐
   │  Soft idle                    │
   │  (any client can take focus)  │
   └──────────────────────────────┘
```

### 6.2 抢焦点协议

```ts
// CLI 端按下首键时
async function onFirstKeystroke() {
  const got = await daemonClient.takeTypingFocus(clientId)
  if (!got) {
    // 别人正在 typing
    showHint('Bob is typing... your input will be queued')
  } else {
    showStatusLine('You are typing')
  }
}
```

```ts
// daemon 端
takeTypingFocus(reqClientId: ClientId): boolean {
  const SOFT_IDLE_MS = 5000
  const now = Date.now()
  
  if (!this.activeTyper) {
    this.activeTyper = reqClientId
    this.activeTyperSince = now
    this.broadcastTypingFocus()
    return true
  }
  
  if (this.activeTyper === reqClientId) {
    this.activeTyperSince = now    // refresh
    return true
  }
  
  // 别人在 typing
  const idle = now - this.activeTyperSince
  if (idle > SOFT_IDLE_MS) {
    // 接管
    this.activeTyper = reqClientId
    this.activeTyperSince = now
    this.broadcastTypingFocus()
    return true
  }
  
  return false   // 拒绝
}
```

### 6.3 Submit 时的处理

Active typer 不影响 prompt 提交——决策 §6 prompt FIFO 已串行化：

```
T=0   Alice 在 cli-laptop 提交 prompt P1 → FIFO[P1]
T=5   Bob 在 cli-desktop 提交 prompt P2 → FIFO[P1, P2]（排队）
T=8   Alice 收到 P1 完整响应
T=10  P2 开始处理（FIFO 自动）
```

UI 显示队列：
```
[CLI Alice] ✓ P1 done
[CLI Bob]   ⏳ P2 queued (will run next)
```

### 6.4 Active typer vs Permission first responder

两者独立机制：

| 机制 | 决策 | 谁有权 |
|---|---|---|
| Active typer | 谁在打字（UI 协调）| 任何 client |
| Permission first responder | 谁应答 tool 权限 | 任何 client（含 IM bot 群里同事抢答）|

可能出现：Alice 在 typing prompt，但 Bob（IM bot 里的）抢答了 Bash 权限请求。这是合理的——分工。

## 七、Takeover 显式接管

### 7.1 何时需要

- 笔记本被偷 / 同事远程接管 incident response
- Stale exclusive 模式 + 老 client 死锁
- 调试时强制清场

### 7.2 协议

```http
POST /v1/session/<sid>/takeover HTTP/1.1
Authorization: Bearer ...
Content-Type: application/json

{
  "reason": "incident_response",
  "kick_kinds": ["cli", "webui"],   // 或 "all" / 具体 kinds
  "exempt_self": true                // 不踢自己
}

Response:
{
  "kicked": [
    { "id": "cli-laptop-...", "kind": "cli" },
    { "id": "webui-firefox-...", "kind": "webui" }
  ],
  "remaining": [
    { "id": "cli-incident-resp-...", "kind": "cli" }
  ]
}
```

### 7.3 CLI flag

```bash
$ qwen attach sess-abc --takeover
[!] About to kick: cli-laptop-alice (Alice@laptop, 30min ago)
                   webui-firefox-... (Alice@firefox, 5min ago)
Continue? [y/N] y
✓ Took over session sess-abc
```

被踢的 client 收到 SSE event：
```
event: forced_disconnect
data: {
  "reason": "takeover",
  "by_client_id": "cli-incident-resp-...",
  "by_user": "alice@example.com",
  "message": "Your session was taken over."
}
```

### 7.4 审计

每次 takeover 写入 [§11 audit log](./11-multi-tenancy-and-sandbox.md)：

```sql
INSERT INTO audit_log (tenant_id, timestamp, method, path, details)
VALUES ('t-alice', NOW(),
  'POST', '/v1/session/sess-abc/takeover',
  '{"kicked": [...], "by_user": "alice@example.com"}'
)
```

企业 tenant 可订阅 audit webhook 实时告警 takeover 事件。

## 八、Exclusive 模式（可选 / tenant config）

### 8.1 启用

```jsonc
// /etc/qwen/tenants/finance-co.json
{
  "sessionPolicy": {
    "subscribers": {
      "mode": "exclusive_per_type",
      "limits": { "cli": 1, "webui": 1, "ide": 1, "im_bot": 5 },
      "newConnectionBehavior": "kick_oldest",  // 或 reject_new
      "kickGracePeriodMs": 30000               // kick 前 30s 通知老 client
    }
  }
}
```

### 8.2 行为决策树

```
新连接来了，kind=K
  ↓
当前同 kind subscribers 数 < limits[K]?
  ↓ Yes
  添加成功
  
  ↓ No
新连接行为 = ?
  ↓ kick_oldest
  通知最老的同 kind subscriber: { type: 'kick_pending', graceMs: 30000 }
  等 30s
  剔除老 + 添加新

  ↓ reject_new
  返回 409 Conflict { error: 'kind_limit_reached' }
  CLI 端提示：另一 CLI 正在使用，请联系 Alice@laptop
```

### 8.3 kick_oldest 流程图

```
T=0     新 CLI 接入请求 → kind=cli, 当前已有 1 个 (cli-old @laptop)
T=0     daemon broadcasts to cli-old:
        { type: 'kick_pending',
          graceMs: 30000,
          reason: 'new_connection_with_exclusive_policy' }
T=0     新 CLI 收到: { type: 'subscribe_pending', graceMs: 30000 }
T=0-30  cli-old UI 显示: "Another CLI is connecting (Alice@desktop)
                          You will be disconnected in 30s
                          [Cancel takeover]"
T=30    cli-old 自动 disconnect（如果用户没点 Cancel）
T=30    新 CLI 添加成功，返回 200
```

**Cancel takeover** 优雅 UX —— 老 client 用户可阻止被踢（这种情况新 CLI 等待结束后收到 reject）。

### 8.4 死锁防御

```
场景: cli-old kill -9 没断（TCP 还没 RST）
新 CLI 来了 → 30s grace period 等待老的回应（但老的已死）
30s 后老的没回应 → 强行 kick

兜底: liveness 60s 已标 stale；exclusive 模式下 stale 视为可强制 kick
```

## 九、Subscriber 数量上限

### 9.1 默认上限

```jsonc
{
  "subscribers": {
    "maxTotal": 20,                          // 单 session 最多 20 subscriber
    "maxPerKind": {
      "cli": 5,
      "webui": 5,
      "ide": 3,
      "im_bot": 10,
      "sdk": 3,
      "mobile": 3
    }
  }
}
```

### 9.2 超限行为

| 触发 | 行为 |
|---|---|
| 总数 ≥ maxTotal | 409 拒绝新连接 |
| 单 kind ≥ maxPerKind | 409 拒绝（即使总数没满）|
| 大 tenant 想提高 | tenant config 覆写 |

### 9.3 事件 fan-out 性能

```
20 subscribers × 平均 100 events/min/session × 1KB/event
= 2MB/min/session SSE 流量
= 33KB/s

10000 active sessions × 33KB/s = 330MB/s 出栈带宽
```

中型 SaaS（10k session）已经是十 Gbps 数据中心级别。所以 `maxTotal=20` 是个合理保护。**实际 Stage 6 SaaS 可调高到 100**，看运维容量。

## 十、UI 协调 mockup

### 10.1 CLI status line

```
┌─ qwen sess-abc · alice@example.com ──────────────────────────┐
│                                                                │
│  > 用户输入 prompt 区...                                       │
│                                                                │
└─ Active subscribers (3): cli@laptop[YOU,typing] webui@firefox idle  im_bot@wechat ─┘
```

### 10.2 Web UI 侧栏

```
Active subscribers
─────────────────
🖥️  Alice@laptop      cli       typing
🌐  Alice@firefox     webui     idle  ← YOU
💬  wechat-bot        im_bot    active
                                
[Takeover session]
```

### 10.3 Active typer 提示

```
[Active typer: Bob@desktop is typing...]
[Your input will be queued. ESC to cancel.]
```

### 10.4 Stale 警告

```
[⚠ cli@laptop appears stale (no heartbeat for 60s)]
[Will be removed in 30s unless reconnected]
```

### 10.5 Takeover 通知

```
[!] You were disconnected by takeover
    By: alice@example.com (cli@new-laptop)
    Reason: incident_response
    Time: just now
    
[Reconnect] [View transcript] [Quit]
```

## 十一、IM Bot 多用户特殊处理

### 11.1 问题

一个微信 / 钉钉群里有 10 个同事，他们都想观察同一 session（看 Alice 在做什么）。每条 LLM 输出群里都广播。

### 11.2 设计：im_bot 单 client + N 用户

```
[微信群 dev-team]
  ├─ Alice (主用户)
  ├─ Bob   ┐
  ├─ Carol ├─ 观察者（看消息）
  └─ Dave  ┘

  ↓ 都连同一 wechat bot

[wechat-bot subscriber: 1 个]
  ├─ session = sess-abc
  ├─ 收 LLM 输出 → 转发到群
  ├─ 群里任何人发消息 → bot 判断:
  │    - Alice 发 → 转给 daemon 作为 user prompt
  │    - 其他人 @bot 发 → 转给 daemon
  │    - 其他人不 @ → 群内闲聊，bot 忽略
  └─ permission 请求 → bot 把请求广播到群,
       任何人回 "allow" / "deny" 即应答（first responder）
```

### 11.3 IM bot 的特殊路由协议

```http
POST /v1/session/<sid>/prompt HTTP/1.1
Authorization: Bearer ${IM_BOT_TOKEN}
Content-Type: application/json

{
  "prompt": "重构 auth 模块",
  "im_metadata": {
    "channel": "wechat:dev-team",
    "im_user_id": "alice-wxid",
    "im_user_display_name": "Alice"
  }
}
```

daemon 把 IM 用户元信息存到 transcript（不影响 LLM 上下文，但 audit 可查谁说了什么）。

### 11.4 多 IM 渠道并存

同 session 可绑多个 IM 渠道：

```
sess-abc subscribers:
  ├─ cli@laptop (Alice)
  ├─ im_bot@wechat-dev-team
  ├─ im_bot@dingtalk-eng-channel
  └─ im_bot@telegram-prod-incidents
```

LLM 输出 fan-out 到 4 个 subscriber → 3 个 IM 群同时看到。

### 11.5 跨 IM 消息消重

防止用户在多 IM 群里 @ 同一 session 时重复 prompt：

```ts
// 简单的去重
const recentPrompts = new LRUCache(50)
function dedupePrompt(prompt: string, sessionId: string): boolean {
  const key = `${sessionId}:${hash(prompt)}`
  if (recentPrompts.has(key)) {
    if (Date.now() - recentPrompts.get(key) < 5000) return true
  }
  recentPrompts.set(key, Date.now())
  return false
}
```

## 十二、错误恢复场景

### 12.1 客户端 crash 恢复

```
T=0    cli@laptop crashes (kernel panic)
T=0-1  daemon 检测 TCP RST → 立即 removeSubscriber
T=10   用户重启电脑
T=15   cli@laptop reconnect → 重新 subscribe
T=15   daemon 添加新 subscriber（不是恢复老的，新 ClientId）
T=15   transcript 重放 events from Last-Event-ID

如果 active typer 是老的 cli@laptop:
T=0-1  removeSubscriber 时 activeTyper = null
T=15   新连接需重新 takeTypingFocus
```

### 12.2 网络抖动

```
T=0    cli@laptop 网络断（NAT 状态丢失，TCP 没 RST）
T=0-30 SSE 没新事件，client 不知道断了
T=30   client 应该发 heartbeat → 失败
T=30-60 client 退避重连
T=60   重连成功 → 新 SSE 流（同 ClientId 复用）
T=60   daemon 端：老 SSE 正在 timeout 中，新连接来了
       → 端老的（同 ClientId 视为重连），用新连接
       → activeTyper 保持（同 client 复用）
T=60+  events from Last-Event-ID 续接
```

### 12.3 跨 daemon pod failover ([§16](./16-high-availability.md))

```
T=0    daemon-1 crash
T=10   sticky cookie 过期 → ingress 路由到 daemon-2
T=15   client subscribe → daemon-2 loadSession
T=15   daemon-2 重建 subscribers 列表（从 Postgres / Redis）
T=15+  其他 client 也重连 → 全部聚到 daemon-2
T=20   coordination 状态全部恢复
```

注意：activeTyper 是**纯 in-memory 状态**，failover 后需要重新协商。第一个发 takeTypingFocus 的拿到。

### 12.4 Stale + 用户回来

```
T=0    Alice 接入 cli@laptop，开始打字
T=10   Alice 突然走开（meeting 30min）
T=70   liveness 60s → 标 stale
T=100  liveness 90s → 剔除
T=120  Alice 回来，按键继续打字
T=120  CLI heartbeat 失败（已被剔除）
T=120  CLI auto-resubscribe → 新 ClientId 重新加入
T=120  之前正在编辑的 prompt 内容 lost? → 不一定
       - 如果 client 端 buffer prompt 在内存 → 还在
       - 如果 daemon 端 partial state → 已丢
       
建议: prompt 编辑完全在 client 端，submit 才发 daemon → robust against subscriber 重连
```

## 十三、与决策的协同

| 决策 | 与本章交互 |
|---|---|
| §1 'single' scope | 本章是 §1 落地的协调机制 |
| §6 prompt FIFO + first responder | 本章 active typer 是 §6 的 UX 补充（不替代 FIFO）|
| §13 多 TUI 共 session | TUI 内部要实现本章的 typing focus / subscriber 列表 UI |
| §16 HA failover | activeTyper 状态需 in-memory，failover 后重协商 |
| §17 远端 CLI 模式 + capability | 本章 subscriber 元信息是 capability 路由依据 |

## 十四、与 OpenCode / Claude Code / VSCode Live Share 对比

| 维度 | OpenCode | Claude Code | VSCode Live Share | qwen daemon |
|---|---|---|---|---|
| 多 client per session | ✗ 单 client | N/A（无 session 持久化）| ✓ host + N guest | ✓ N client |
| Liveness 协议 | N/A | N/A | 心跳 + presence | ✓ heartbeat + 90s |
| Active typer | N/A | N/A | 实时光标多色 | ✓ 简化的 "typing" 标识 |
| Takeover | N/A | N/A | host kick guest | ✓ explicit takeover API |
| Exclusive mode | N/A | N/A | host 控制 read-only / 编辑 | ✓ 可选 tenant config |
| Kind 区分 | N/A | N/A | role: host/guest | ✓ 6 类 kind |
| IM bot 一对多 | N/A | N/A | N/A（IDE only）| ✓ im_bot kind 设计 |

**VSCode Live Share** 是最接近的参照（host-guest 协作 IDE）。qwen daemon 在它基础上扩展：
- 支持 IDE 之外的 client（CLI / IM bot / SDK）
- 不要求 host 角色（任何 client 平等）
- IM bot 一对多用户的特殊处理

## 十五、测试矩阵

| # | 场景 | 期望行为 |
|---|---|---|
| T1 | 单 CLI 接入 | OK |
| T2 | 2 CLI 同时接入（默认 shared）| 都接入，subscribers list 显示 2 个 |
| T3 | 2 CLI 同时打字 | active typer 协调，UI 显示 typing |
| T4 | 21 个 subscribers（超 maxTotal）| 第 21 个被拒 |
| T5 | 6 个 cli kind（超 maxPerKind=5）| 第 6 个被拒 |
| T6 | CLI 断网 90s | 自动剔除，subscribers list 同步 |
| T7 | CLI kill -9 | TCP RST 即时剔除（< 1s）|
| T8 | Browser tab 切后台 5min | 不剔除（webui 5min 超时）|
| T9 | 2 CLI 模式 = exclusive_per_type | 第 2 个 kick_oldest 流程 |
| T10 | 用户 cancel takeover | 老 CLI 保留 |
| T11 | im_bot 多用户消息去重 | 5s 内重复 prompt 拒绝 |
| T12 | 跨 daemon pod failover | activeTyper 重协商 |
| T13 | takeover audit log | 写入 audit_log |
| T14 | client_kind 伪造（webui 声明 cli）| token allowedKinds 校验拒绝 |
| T15 | Subscribers list 隐私 | ip 字段不暴露 |

## 十六、Stage 1-6 各阶段实施

| Stage | 本章实施 |
|---|---|
| Stage 1 (HTTP-bridge) | minimal: 仅 add/remove subscriber + heartbeat |
| Stage 2 (原生 daemon) | + active typer + subscribers list UI |
| Stage 3 (完整 daemon) | + takeover + maxTotal/maxPerKind |
| Stage 4 (多租户) | + exclusive mode tenant config |
| Stage 5 (sandbox) | (no change) |
| Stage 6 (SaaS HA) | + Redis 同步 subscribers 跨 pod + audit log webhook |

## 十七、一句话总结

**Qwen daemon 多端协调 = 默认 shared 模式（不限制 client 数量，保住 §1+§6 collaboration 哲学）+ 6 类 client kind 分桶上限（cli/webui/ide/im_bot/sdk/mobile）+ 30s heartbeat + 90s 超时 + TCP RST 即时剔除 + active typer 协调（5s 让出，"X is typing"）+ 显式 takeover API（带 audit）+ 可选 exclusive_per_type 模式（企业 tenant config 启用，kick_oldest 行为带 30s grace + cancel takeover）+ IM bot kind 一对多用户特殊处理（多 IM 渠道并存 + 消息去重 + 任意人 first responder permission）。设计哲学：协调 > 排斥，默认让 collaboration 工作，企业有需要可加约束，不把 hard limit 作为全局默认。**

---

[← 返回 README](./README.md)
