# Remote Control Bridge Deep-Dive

> 离开电脑后 Agent 需要人类审批权限——当前无法远程操作。本文基于 Claude Code 源码分析（bridge/ 目录 ~12600 行）和 Qwen Code（channels/ + ACP 架构）的源码对比，深度介绍 Claude Code 的 Remote Control Bridge 机制及其与 Qwen Code 的架构差异。

---

## 1. 问题定义

AI Agent 执行长任务时经常需要人类审批（文件写入、shell 命令、网络访问）。如果用户离开电脑，Agent 就卡在权限对话框上——无法继续工作。

| 场景 | 无远程控制 | 有远程控制 |
|------|-----------|-----------|
| 用户外出 | Agent 暂停等待审批 | 手机/浏览器远程审批 |
| 跨设备 | 必须回到同一终端 | Web/手机/iPad 均可操作 |
| 长任务监控 | 无法查看进度 | 实时查看输出和工具调用 |
| 崩溃恢复 | session 丢失 | Bridge Pointer 自动恢复 |

---

## 2. Claude Code：Remote Control Bridge 架构

### 2.1 整体架构

```
┌─────────────┐     WebSocket/SSE      ┌─────────────┐     HTTPS      ┌─────────────┐
│  Terminal    │ ◄──────────────────── │  Cloud API   │ ◄──────────── │  Web/Mobile  │
│  (本地 CLI)  │ ──────────────────── │  (中继服务)   │ ──────────── │  (浏览器/App) │
│             │     HTTP POST          │             │     OAuth      │             │
│  Outbound   │                        │  Session     │                │  用户审批    │
│  Only Mode  │                        │  Ingress     │                │  上下文补充   │
└─────────────┘                        └─────────────┘                └─────────────┘
```

**关键设计决策**：Terminal 端是 **Outbound-only** 模式——主动向云端推送事件，不接受入站连接。这避免了 NAT 穿透、防火墙配置、端口暴露等问题。

### 2.2 三层传输协议

Claude Code 实现了 3 种传输协议，按优先级降级：

```typescript
// 源码: cli/transports/ 目录

// V1: WebSocket 读 + HTTP POST 写（HybridTransport）
// 读: wss://.../{version}/session_ingress/ws/{sessionId}
// 写: POST /v1/sessions/{id}/events （批量，100ms 合并窗口）

// V2: SSE 读 + HTTP POST 写（SSETransport + CCRClient）
// 读: GET /worker/events/stream（Last-Event-ID 续传）
// 写: POST /worker/events （SerialBatchEventUploader）

// 降级链: WebSocket → SSE → HTTP 轮询
```

**保活机制**：

| 层级 | 间隔 | 超时 |
|------|------|------|
| WebSocket ping/pong | 10s | — |
| Keep-alive 数据帧 | 5min | — |
| SSE comment 帧 | 15s（服务端） | 45s（客户端判定死亡） |
| Session 心跳 | 120s（2min） | — |

**重连策略**：

```typescript
// 源码: bridge/bridgeMain.ts#L72-75
const DEFAULT_BACKOFF = {
  connInitialMs: 2_000,       // 初始 2 秒
  connCapMs: 120_000,         // 上限 2 分钟
  connGiveUpMs: 600_000,      // 放弃 10 分钟
}
```

- 指数退避 + 抖动（`delay × 2 + jitter`）
- 睡眠检测：连续两次尝试间隔 > cap × 2，判定系统休眠，重置退避
- 永久关闭码（1002/4001/4003）不重连

### 2.3 会话生命周期

#### 注册与创建

```
Terminal                         Cloud API
   │                               │
   ├─ POST /v1/environments/bridge ─→  注册环境（OAuth）
   │                               │
   │← environmentId + secret ──────┤
   │                               │
   ├─ POST /v1/sessions ──────────→  创建会话
   │                               │
   │← sessionId ──────────────────┤
   │                               │
   ├─ GET /work/poll ─────────────→  等待 Web 端发起工作
   │                               │  （30-60s 长轮询）
   │← work_secret（base64url JSON）┤
   │                               │
   ├─ POST /work/{id}/ack ────────→  确认接收
   │                               │
   ├─ ws://session_ingress/ws/{id} → 建立 WebSocket
   │                               │
   │← 实时事件流 ─────────────────┤
```

**work_secret 解码**（源码: `bridge/workSecret.ts`）：

```typescript
// Base64url JSON 包含（源码: bridge/workSecret.ts 解码验证字段）：
{
  version: number,                // 协议版本
  session_ingress_token: string,  // JWT 访问令牌
  api_base_url: string,           // API 端点
  // 额外字段（由 WorkSecret 类型定义，解码器不做强校验）：
  sources?: unknown,              // 数据源配置
  mcp_config?: unknown            // MCP 服务器配置
}
```

#### 崩溃恢复

```typescript
// 源码: bridge/bridgePointer.ts
// 会话创建后立即写入指针文件
// 路径: ~/.claude/projects/{sanitized_dir}/bridge-pointer.json
{
  sessionId: string,
  environmentId: string,
  source: 'standalone' | 'repl'
}
// TTL: 4 小时（基于 mtime，非嵌入时间戳）
```

恢复流程：
1. 启动时读取 bridge pointer（mtime < 4h）
2. `POST /v1/environments/bridge` 携带 `reuseEnvironmentId`
3. 如果环境仍存活，`reconnectSession()` 恢复
4. Poll 循环从中断处继续

**Worktree 感知恢复**（源码: `bridgePointer.ts#L129-184`）：

```typescript
// 在 git worktree 兄弟目录中扇出查找最新 pointer
// 最多并行 stat() 50 个 worktree（MAX_WORKTREE_FANOUT）
readBridgePointerAcrossWorktrees()
// 选择 ageMs 最小的 pointer
```

### 2.4 消息协议

#### 出站（Terminal → Cloud）

| 消息类型 | 内容 | 触发时机 |
|----------|------|----------|
| `SDKAssistantMessage` | 模型文本输出 | 每个 content block |
| `SDKPartialAssistantMessage` | 流式增量 | 每个 text_delta |
| `SDKToolProgressMessage` | 工具执行进度 | 工具运行中 |
| `SDKResultMessage` | 轮次完成 | end_turn |
| `SDKControlResponse` | 权限审批响应 | 用户审批后 |

#### 入站（Cloud → Terminal）

| 消息类型 | 内容 | 来源 |
|----------|------|------|
| `SDKUserMessage` | 用户输入 | Web/Mobile 输入框 |
| `SDKControlRequest` | 控制请求 | 模型切换/中断/权限 |
| `SDKControlResponse` | 权限决策 | Web 审批对话框 |

#### 消息去重

```typescript
// 源码: bridge/bridgeMessaging.ts#L429-461
// BoundedUUIDSet: 环形缓冲区 + Set，O(1) 查重
// 容量 2000，FIFO 淘汰

// 两层去重：
recentPostedUUIDs  // 我发出的消息——忽略回声
recentInboundUUIDs // 已处理的入站——忽略历史重放
```

### 2.5 远程权限处理

这是 Remote Control Bridge 最核心的价值——用户在 Web/Mobile 上审批权限请求：

```
Terminal                    Cloud                    Web/Mobile
   │                         │                          │
   │  模型请求 Bash("rm -rf") │                          │
   │                         │                          │
   ├─ control_request ──────→│                          │
   │  {                      │                          │
   │    subtype: 'can_use_tool',                        │
   │    tool_name: 'Bash',   │─── 转发权限请求 ─────────→│
   │    input: {command: 'rm -rf build/'},               │
   │    tool_use_id: 'xxx'   │                   用户看到│
   │  }                      │                 权限对话框│
   │                         │                          │
   │                         │←── 用户点击 Allow ────────┤
   │                         │    {behavior: 'allow'}   │
   │← control_response ─────┤                          │
   │  {                      │                          │
   │    subtype: 'success',  │                          │
   │    response: {          │                          │
   │      behavior: 'allow', │                          │
   │      updatedInput: ..., │                          │
   │      updatedPermissions: [...] │                   │
   │    }                    │                          │
   │  }                      │                          │
   │                         │                          │
   │  执行 rm -rf build/     │                          │
```

**权限建议**（Permission Suggestions）：

```typescript
// 源码: bridge/bridgePermissionCallbacks.ts
// 发送请求时附带建议规则
{
  permissionSuggestions: [
    { tool: 'Bash', rule: 'rm -rf build/', scope: 'session' }
  ]
}
// Web 端可一键接受建议——后续相同命令自动批准
```

### 2.6 安全模型

| 层级 | 机制 | 实现 |
|------|------|------|
| **API 认证** | OAuth Bearer Token | `getBridgeAccessToken()` 从 Keychain |
| **会话认证** | Session Ingress JWT | work_secret 解码获取 |
| **设备信任** | Trusted Device Token | 90 天滚动过期，Keychain 存储 |
| **ID 验证** | 正则白名单 `[a-zA-Z0-9_-]+` | 防路径遍历和注入 |
| **消息净化** | `hooks/useReplBridge.tsx` 引用 `webhookSanitizer.js`（运行时生成） | 防 XSS 和注入 |

**Trusted Device Token**（源码: `bridge/trustedDevice.ts`）：

```typescript
// 注册: POST /api/auth/trusted_devices（登录后 <10 分钟内）
// 存储: macOS Keychain
// 有效期: 90 天滚动
// Header: X-Trusted-Device-Token
// 门控: tengu_sessions_elevated_auth_enforcement（GrowthBook）
```

### 2.7 多会话模式

```typescript
// 源码: bridge/bridgeMain.ts
// 三种模式：
'single-session'  // claude remote-control（会话结束即退出）
'worktree'        // 持久服务，每个会话独立 git worktree
'same-dir'        // 持久服务，共享工作目录（可能冲突）
```

**容量管理**（源码: `bridge/pollConfigDefaults.ts`）：

```typescript
{
  poll_interval_ms_not_at_capacity: 2_000,     // 空闲时 2s 轮询
  poll_interval_ms_at_capacity: 600_000,       // 满载时 10min 轮询
  multisession_poll_interval_ms_partial_capacity: 2_000, // 部分满载 2s
  reclaim_older_than_ms: 5_000,                // 5s 无活动可回收
  session_keepalive_interval_v2_ms: 120_000    // 2min 心跳
}
```

**Capacity Wake**（源码: `bridge/capacityWake.ts`）：会话结束时发送唤醒信号，中断 at-capacity 睡眠，立即轮询新工作。

### 2.8 文件附件

Web 端用户可上传文件（截图、文档）：

```typescript
// 源码: bridge/inboundAttachments.ts
// 1. Web 上传: POST /api/{org}/upload（Cookie 认证）
// 2. Bridge 下载: GET /api/oauth/files/{uuid}/content
// 3. 存储: ~/.claude/uploads/{sessionId}/{uuid-prefix}-{filename}
// 4. 注入: 在入站消息末尾追加 @"path" 引用
```

---

## 3. Qwen Code：Channels + ACP 架构

### 3.1 Channels 系统

Qwen Code 通过 Channels 架构实现多平台接入：

```
┌─────────────┐                    ┌─────────────┐
│  DingTalk    │──── AcpBridge ────│             │
├─────────────┤    (stdio ndjson)  │  Qwen Code  │
│  Telegram   │──── AcpBridge ────│  CLI 子进程  │
├─────────────┤                    │             │
│  WeChat     │──── AcpBridge ────│  (--acp)    │
├─────────────┤                    │             │
│  VSCode     │──── HTTP MCP ─────│             │
└─────────────┘                    └─────────────┘
```

**AcpBridge**（源码: `packages/channels/base/src/AcpBridge.ts`）：
- spawn CLI 子进程 + `--acp` flag
- stdio ndjson 双向 IPC
- Agent Client Protocol (ACP) SDK 集成
- 崩溃后指数退避重启

**会话路由**（SessionRouter）：
- Key 格式按作用域不同：`user` → `<channel>:<senderId>:<chatId>`、`thread` → `<channel>:<threadId|chatId>`、`single` → `<channel>:__single__`
- 作用域: `user`（每用户独立）/ `thread`（每线程）/ `single`（全局单一）
- 消息调度（ChannelBase 层）: `collect`（收集）/ `steer`（转向，默认）/ `followup`（追加）

### 3.2 与 Claude Code Bridge 的关键差异

| 维度 | Claude Code Bridge | Qwen Code Channels |
|------|-------------------|-------------------|
| **方向** | Terminal → Cloud（Outbound-only） | Platform → CLI（Inbound-only） |
| **场景** | 用户远程驱动自己的终端 | 外部平台用户向 Agent 提问 |
| **认证** | OAuth + JWT + Trusted Device | Platform-specific（Bot Token） |
| **权限审批** | 远程转发到 Web，用户审批 | 本地 CLI 权限规则自动决策 |
| **会话持有者** | 终端用户（同一人远程操作） | 平台用户（不同人向 Agent 提问） |
| **崩溃恢复** | Bridge Pointer 自动恢复 | AcpBridge 进程重启 |
| **文件附件** | Web 上传 → Bridge 下载 → @引用 | Platform 消息附件 → CLI |
| **连接模型** | 长连接 WebSocket/SSE | 子进程 stdio |

**核心区别**：

- **Claude Code Bridge** = **同一用户**从 Web/Mobile 远程控制**自己的终端** Agent
- **Qwen Code Channels** = **不同用户**从 DingTalk/Telegram 向**服务端** Agent 提问

Channels 不是 Remote Control Bridge 的替代——它们解决完全不同的问题。

---

## 4. 差距分析

### Qwen Code 缺失的能力

| 能力 | 说明 | 优先级 |
|------|------|--------|
| **远程权限审批** | 手机/浏览器审批终端 Agent 的权限请求 | P1 |
| **远程会话查看** | Web 端实时查看终端输出和工具调用 | P1 |
| **远程上下文补充** | Web 端向运行中的 Agent 发送补充信息 | P1 |
| **崩溃恢复指针** | 进程死亡后通过 pointer 文件自动恢复 | P2 |
| **多会话服务模式** | 单机运行多个独立会话 | P2 |
| **Worktree 感知恢复** | 跨 git worktree 查找最近会话 | P2 |
| **文件附件远程上传** | Web 端上传截图供 Agent 使用 | P2 |

### 建议实现路径

```
阶段 1: 基础 Remote Control（对接已有基础设施）
├── 对接阿里云 WebSocket 服务（或自建 relay）
├── 实现 Outbound-only 连接模式
├── 权限请求远程转发
└── Bridge Pointer 崩溃恢复

阶段 2: Web 端 UI
├── 权限审批对话框
├── 实时输出查看
└── 消息发送/文件上传

阶段 3: 多会话 + 高级功能
├── Worktree 隔离的多会话
├── Capacity Wake 智能轮询
└── Trusted Device 安全增强
```

---

## 5. 源码文件索引

### Claude Code Bridge 核心文件

| 文件 | 行数 | 职责 |
|------|:----:|------|
| `bridge/bridgeMain.ts` | 2999 | Poll-dispatch 主循环、多会话编排 |
| `bridge/replBridge.ts` | 2406 | REPL 桥接核心、Session Ingress |
| `bridge/bridgeMessaging.ts` | 461 | 消息路由、BoundedUUIDSet 去重 |
| `bridge/bridgeApi.ts` | 539 | HTTP API 封装（环境/会话端点） |
| `bridge/bridgePointer.ts` | 210 | 崩溃恢复指针管理 |
| `bridge/codeSessionApi.ts` | 168 | CCR v2 会话 API |
| `bridge/bridgePermissionCallbacks.ts` | 43 | 权限回调协议 |
| `bridge/workSecret.ts` | 127 | Work Secret 解码 |
| `bridge/trustedDevice.ts` | 210 | Trusted Device 注册与管理 |
| `bridge/flushGate.ts` | 71 | 初始消息刷新门控 |
| `bridge/inboundAttachments.ts` | 175 | Web 文件附件下载 |
| `bridge/sessionRunner.ts` | 550 | 子 CLI 进程管理 |
| `cli/transports/HybridTransport.ts` | 282 | WS 读 + HTTP 写 |
| `cli/transports/SSETransport.ts` | 711 | SSE 传输 |
| `cli/transports/WebSocketTransport.ts` | 800 | WebSocket 传输 |

### Qwen Code Channels 文件

| 文件 | 职责 |
|------|------|
| `packages/channels/base/src/AcpBridge.ts` | ACP 子进程 IPC |
| `packages/channels/base/src/ChannelBase.ts` | Channel 基类 |
| `packages/channels/base/src/SessionRouter.ts` | 会话路由 |
| `packages/channels/dingtalk/src/` | 钉钉适配器 |
| `packages/channels/telegram/src/` | Telegram 适配器 |
| `packages/channels/weixin/src/` | 微信适配器 |

---

## 6. 总结

Claude Code 的 Remote Control Bridge 解决了一个实际痛点：**用户离开电脑后 Agent 无法继续工作**。通过 Outbound-only WebSocket/SSE 连接到云端中继服务，实现了：

1. **远程权限审批**——手机上看到 Agent 请求执行 `npm install`，一键批准
2. **实时进度查看**——浏览器中看到 Agent 正在编辑哪些文件
3. **上下文补充**——远程发送截图或补充信息
4. **崩溃恢复**——Bridge Pointer + 4h TTL 自动恢复

Qwen Code 的 Channels 架构解决的是**不同的问题**（多平台接入），但可以复用 AcpBridge 的 ndjson IPC 机制作为 Remote Control 的传输层基础。

> **免责声明**: 以上分析基于 2026 年 Q1 源码快照，可能已过时。
