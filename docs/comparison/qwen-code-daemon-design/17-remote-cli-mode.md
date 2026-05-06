# 17 — 远端 CLI 模式与 Client Capability 协议

> [← 上一篇：HA 高可用与故障恢复](./16-high-availability.md) · [回到 README](./README.md)

> CLI 连接远端 daemon 的完整设计：3 类拓扑取舍、Client Capability 反向 RPC 协议（让 daemon 调起本地 editor/clipboard/browser）、TLS/mTLS auth 链、NAT 穿透方案、Local echo 性能优化、离线降级。

## 一、TL;DR

| 维度 | 设计 |
|---|---|
| 推荐拓扑 | **Remote-Remote**（workspace 与 daemon 同机）—— 类比 GitHub Codespaces / Coder |
| Auth 链 | TLS 1.3 + Bearer token + 可选 mTLS + sticky cookie HMAC |
| 反向 RPC | **Client Capability Request 协议**：daemon 通过 SSE event 反向调用 CLI（editor / clipboard / browser / notification / file_picker）|
| NAT 穿透 | Cloudflare Tunnel / Tailscale / SSH reverse tunnel |
| 性能优化 | TUI 端 local echo 抹平 keystroke RTT；LLM streaming 50ms RTT 几乎无感 |
| 重连 | SSE Last-Event-ID（[§16 §五](./16-high-availability.md) 协议）|
| 离线降级 | `--daemon-or-local` flag：daemon 不可达自动 fallback 到本地子进程模式 |

## 二、3 类拓扑详细对比

### 2.1 拓扑 A — Local-Local（同机）

```
Laptop / Workstation
├─ qwen CLI ──────HTTP──────→ qwen daemon (127.0.0.1:8080)
├─ Workspace /work/repo
└─ Editor / clipboard / browser
```

**适用**：
- 单人开发（最常见）
- Stage 1-3 默认部署
- 同 host 多 client（CLI 1 + CLI 2 + IDE 同 session，[§13](./13-tui-compatibility.md)）

**特点**：
- 无网络层 latency
- 所有本地依赖功能直接可用（editor / clipboard / xdg-open）
- 不需要 TLS（loopback 安全）

### 2.2 拓扑 B — Local-Remote（混合，**不推荐**）

```
Laptop                            Cloud / Workstation
├─ qwen CLI ──HTTPS+TLS─────────→ qwen daemon
├─ Workspace /work/repo           └─ ?? (no workspace here)
└─ Editor / clipboard
```

**问题**：
- daemon Edit/Read tool 看不到本地 `/work/repo` 文件
- daemon Bash spawn `npm test` 没有 repo 在远端
- LSP / MCP server 启动在远端，不能解析本地文件路径
- 沙箱在远端 spawn，访问的是远端 fs

**唯一可行的解法**（每种都有重大问题）：

| 方案 | 实现 | 问题 |
|---|---|---|
| sshfs / Mutagen 同步 workspace 到 daemon | mount 本地 dir 到远端 | 高 latency / 文件锁 / 大文件性能差 |
| daemon 主动 git clone | repo 必须在 git remote | dirty/uncommitted 修改丢失 |
| 双向同步（Mutagen continuous）| 持续同步 | 冲突 / 复杂运维 |

**结论**：拓扑 B **不主流支持**，文档明确标记为 unsupported（如真要用，走拓扑 C 的"假装本地"workflow，把开发整个搬到远端机器）。

### 2.3 拓扑 C — Remote-Remote（**推荐**）

```
Laptop (thin client)              Cloud / Workstation / Container
├─ qwen CLI ──HTTPS+TLS─────────→ qwen daemon
                                  ├─ Workspace /work/repo
                                  ├─ MCP / LSP / sandbox（all 在 daemon 同机）
└─ Editor / clipboard / browser   └─ Background tasks 子进程

Capability 反向 RPC:
                                  daemon emit { type: 'open_editor', content: '...' }
Editor / clipboard / browser ←─── via SSE event ─────
```

**适用**：
- Stage 6 SaaS（云端 dev container）
- GitHub Codespaces / Coder 风格 cloud workspace
- 工程师笔记本性能弱 / 跨机器开发
- 团队共享 dev environment（同一 daemon 多人接入不同 session）

**特点**：
- daemon 端有完整 workspace 视图
- 仅 5 类本地依赖功能需 capability 反向 RPC
- LLM 对话延迟基本无感（50ms RTT）
- TUI 端 local echo 抹平键击延迟

### 2.4 决策表

| 维度 | 拓扑 A | 拓扑 B | 拓扑 C |
|---|---|---|---|
| 开发体验 | 最佳 | 差 | 良好 |
| 文件 IO 复杂度 | 0 | 极高 | 0 |
| 沙箱 / 子进程 | 简单 | 极复杂 | 简单 |
| 网络要求 | 无 | 高 | 中 |
| 适用人群 | 单人 | 特殊 | SaaS / 团队 |
| 官方支持 | ✓ Stage 1+ | ✗ | ✓ Stage 3+ |

## 三、Client Capability Request 协议

### 3.1 设计动机

拓扑 C 下，daemon 在云端，无法直接调用本机 `xdg-open`、`vim`、`xclip` 等命令。**反向 RPC** 让 daemon 通过 SSE 事件请求 CLI 端代为执行。

类比 [LSP `window/showDocument`](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#window_showDocument) / [DAP `runInTerminal`](https://microsoft.github.io/debug-adapter-protocol/specification#Reverse_Requests_RunInTerminal) 的 reverse request 模式。

### 3.2 协议层

```
[CLI] ←──── SSE event ──── [daemon]      capability request
[CLI] ──── HTTP POST ────→ [daemon]      capability response
```

**为什么不用 WebSocket 全双工**：
- SSE + HTTP POST 简单，企业代理兼容性好
- WebSocket 在公司代理 / Cloudflare 之类有时需特殊配置
- HTTP/2 multiplexing 自然支持多 capability 并发

### 3.3 Request 格式

daemon 端 emit SSE event：

```
event: capability_request
id: cap-12345
data: {
  "id": "cap-12345",
  "type": "open_editor",
  "params": {
    "filename": "draft.md",
    "initialContent": "...",
    "syntax": "markdown",
    "expectsContent": true
  },
  "timeout_ms": 600000,
  "fallback": "return_inline"
}
```

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一 ID，用于 response 关联 |
| `type` | string | capability 类型（5 种，见 §四）|
| `params` | object | type 特定参数 |
| `timeout_ms` | number | client 必须在此时间内响应；超时 daemon 自动 fallback |
| `fallback` | string | client 不支持时 daemon 的退化策略（`error` / `return_inline` / `skip`）|

### 3.4 Response 格式

CLI 端 POST 回 daemon：

```http
POST /v1/session/<sid>/capability/cap-12345/response HTTP/1.1
Authorization: Bearer ...
Content-Type: application/json

{
  "id": "cap-12345",
  "status": "success",         // success / cancelled / error / unsupported
  "result": {
    "content": "edited content..."
  },
  "error": null                 // 当 status=error 时填
}
```

### 3.5 Client 不支持时的兜底

CLI 启动时声明能力：

```http
POST /v1/session HTTP/1.1
Authorization: Bearer ...
Content-Type: application/json

{
  "client_capabilities": {
    "open_editor": true,
    "clipboard": true,
    "open_browser": true,
    "notification": false,      // 终端环境无桌面通知
    "file_picker": false        // CLI 不支持 GUI file picker
  },
  "client_info": {
    "name": "qwen-cli",
    "version": "1.0.0",
    "platform": "linux",
    "tty": true
  }
}
```

daemon 在 emit capability_request 前检查 `client_capabilities`，不支持的 capability 走 `fallback` 策略。

## 四、5 类 Capability 详细设计

### 4.1 `open_editor`

**目的**：daemon 需要用户编辑长文本（commit message / 大段输入）。

**Request**：
```json
{
  "type": "open_editor",
  "params": {
    "filename": "COMMIT_EDITMSG",
    "initialContent": "feat: ...\n\n# Please enter the commit message...",
    "syntax": "git-commit",
    "expectsContent": true,
    "instructions": "Edit and save to confirm; close empty to abort."
  }
}
```

**CLI 端实现**：
```ts
// packages/cli/src/capability/editor.ts
async function handleOpenEditor(params: OpenEditorParams) {
  const editor = process.env.EDITOR || 'vim'
  const tmpFile = await mkstemp({ suffix: params.filename })
  await fs.writeFile(tmpFile, params.initialContent)
  
  await spawn(editor, [tmpFile], { stdio: 'inherit' })
  
  const finalContent = await fs.readFile(tmpFile, 'utf-8')
  await fs.unlink(tmpFile)
  
  return { status: 'success', result: { content: finalContent } }
}
```

**Fallback `return_inline`**：daemon 改用内置 multi-line input box（TUI 内部 vim-emulation，[Ink + ink-text-input]）。

**对比单进程模式**（同 host）：daemon 直接 spawn editor in pty —— 拓扑 A 的方式；远端模式必须走反向 RPC。

### 4.2 `clipboard`

**目的**：把内容复制到本地剪贴板 / 从剪贴板读取。

**Request (write)**：
```json
{
  "type": "clipboard",
  "params": {
    "operation": "write",
    "content": "https://github.com/...",
    "mime": "text/plain"
  }
}
```

**Request (read)**：
```json
{
  "type": "clipboard",
  "params": {
    "operation": "read",
    "mime": "text/plain"
  }
}
```

**CLI 端实现**：

```ts
async function handleClipboard(params: ClipboardParams) {
  if (params.operation === 'write') {
    // 优先 OSC 52 终端 escape (跨平台 / SSH 兼容)
    if (supportsOSC52()) {
      process.stdout.write(`\x1b]52;c;${base64(params.content)}\x07`)
    } else {
      // fallback: pbcopy / xclip / xsel / clip
      const cmd = pickClipboardCmd()
      await spawnWithStdin(cmd, params.content)
    }
    return { status: 'success' }
  } else {
    // read: 仅本机命令支持（OSC 52 read 安全风险大，多终端禁用）
    const cmd = pickClipboardCmd('read')
    const content = await spawnReadStdout(cmd)
    return { status: 'success', result: { content } }
  }
}
```

**OSC 52 优势**：
- 跨 SSH / tmux / VSCode Terminal 透明
- 不需要本地 X11 / Wayland 环境
- 不需要本机 `xclip` / `pbcopy` 安装

**OSC 52 限制**：
- 内容大小有限（多数终端 100KB-1MB）
- read 多数终端默认禁用（安全考虑）

### 4.3 `open_browser`

**目的**：OAuth flow / 文档链接 / preview server。

**Request**：
```json
{
  "type": "open_browser",
  "params": {
    "url": "https://login.qwen.com/oauth?...",
    "purpose": "oauth_flow",
    "expectsCallback": false
  }
}
```

**CLI 端实现**：

```ts
async function handleOpenBrowser(params: OpenBrowserParams) {
  // 1. 优先 OSC 8 hyperlink (终端可点)
  if (supportsOSC8()) {
    process.stdout.write(
      `\x1b]8;;${params.url}\x07[Click to open]\x1b]8;;\x07\n`
    )
  }
  
  // 2. 调系统命令
  const cmd = process.platform === 'darwin' ? 'open'
            : process.platform === 'win32' ? 'start'
            : 'xdg-open'
  
  try {
    await spawn(cmd, [params.url], { stdio: 'ignore', detached: true })
    return { status: 'success' }
  } catch {
    // 3. fallback: 显示 URL 让用户复制
    process.stdout.write(`Open in browser: ${params.url}\n`)
    return { status: 'success', result: { fallback: 'displayed_url' } }
  }
}
```

**OAuth callback 接管**（特殊场景）：

```
1. CLI 启动 ephemeral local HTTP server (e.g. localhost:23456/callback)
2. daemon 生成 OAuth URL，redirect_uri = http://localhost:23456/callback
3. CLI capability response 时附带 callback_port: 23456
4. daemon 把 redirect_uri 改为 client-provided
5. 浏览器 → callback → CLI HTTP server → POST 回 daemon
```

### 4.4 `notification`

**目的**：长任务完成通知用户。

**Request**：
```json
{
  "type": "notification",
  "params": {
    "title": "Background agent finished",
    "body": "PR draft ready for review",
    "urgency": "normal",         // low / normal / critical
    "icon": null
  }
}
```

**CLI 端实现**：

```ts
async function handleNotification(params: NotificationParams) {
  // 1. 终端 bell（最低公分母）
  if (params.urgency !== 'low') {
    process.stdout.write('\x07')  // BEL
  }
  
  // 2. OSC 9 / iTerm2 通知
  if (supportsOSC9()) {
    process.stdout.write(`\x1b]9;${params.title}: ${params.body}\x07`)
  }
  
  // 3. 桌面通知（仅本机环境）
  if (process.env.DISPLAY || process.platform === 'darwin') {
    const cmd = process.platform === 'darwin' ? 'osascript' : 'notify-send'
    // ...
  }
  
  return { status: 'success' }
}
```

### 4.5 `file_picker`

**目的**：用户选择本地文件（attach to prompt）。

**注意**：远端拓扑 C 下，"本地"指 CLI 端。这是 **唯一一个允许从 CLI 端读取文件并发送到 daemon 的 capability**。

**Request**：
```json
{
  "type": "file_picker",
  "params": {
    "multiple": false,
    "accept": ["image/*", ".pdf"],
    "purpose": "attach_to_prompt",
    "maxSize": 10485760
  }
}
```

**CLI 端实现**：

```ts
async function handleFilePicker(params: FilePickerParams) {
  // CLI 通常用 fzf / 内置 input
  const filename = await prompt('Enter file path: ')
  const fullPath = path.resolve(filename)
  
  const stats = await fs.stat(fullPath)
  if (stats.size > params.maxSize) {
    return { status: 'error', error: 'file_too_large' }
  }
  
  // 大文件分块上传到 daemon attachment endpoint
  const attachmentId = await uploadAttachment(daemonUrl, token, fullPath)
  
  return {
    status: 'success',
    result: {
      attachments: [
        { id: attachmentId, filename: path.basename(fullPath), size: stats.size }
      ]
    }
  }
}
```

### 4.6 Capability 协议总结表

| Capability | 用途 | OSC 终端兼容 fallback | 必需性 |
|---|---|---|---|
| `open_editor` | 编辑长文本 | 内置 ink-text-input multi-line | High（commit msg / 长 prompt）|
| `clipboard` | 读写剪贴板 | OSC 52 | Medium |
| `open_browser` | OAuth / 文档 | OSC 8 hyperlink + 显示 URL | High（OAuth 必需）|
| `notification` | 异步通知 | terminal bell + OSC 9 | Low |
| `file_picker` | 选本地文件 | 文件路径输入 | Medium |

## 五、TLS / Auth 完整链

### 5.1 5 层握手

```
[CLI 启动]
   ↓
1. DNS 解析 daemon.qwen.example.com
   ↓
2. TCP connect :443
   ↓
3. TLS 1.3 handshake
   ├─ Server cert 验证
   ├─ SNI: daemon.qwen.example.com
   └─ ALPN: h2 / http/1.1
   ↓
4. (可选) mTLS 客户端证书 challenge
   ↓
5. HTTP/2 stream
   ├─ Authorization: Bearer <token>
   └─ Initial: GET /v1/session/sess-abc/events
   ↓
6. daemon 验证：
   ├─ Token HMAC 比对（[§07](./07-permission-auth.md)）
   ├─ Tenant lookup
   ├─ Workspace allowlist check
   └─ Session 存在性 + 所属 tenant 匹配
   ↓
7. SSE 长连接建立 → 业务流量
```

### 5.2 Bearer Token 设计

参考 [§07 §1](./07-permission-auth.md)：

```
Token format: qwen_<env>_<tenant_id>_<random_64bytes_base32>

例:
  qwen_prod_t-alice_b7m2k9....    # 生产 tenant alice
  qwen_dev_t-bob_h3p8j2....       # 开发 tenant bob

Storage: bcrypt(token_secret, cost=12)
         daemon 仅存 hash，明文 token 仅返回一次
```

### 5.3 mTLS（可选，企业级）

```yaml
# /etc/qwen/daemon.json
{
  "tls": {
    "cert": "/etc/qwen/tls/server.crt",
    "key": "/etc/qwen/tls/server.key",
    "clientAuth": {
      "required": true,                    // 强制 mTLS
      "ca": "/etc/qwen/tls/client-ca.crt",  // 客户端证书 CA
      "verifyDepth": 2
    }
  }
}
```

**优势**：
- 第二因子（token + cert）
- token 泄漏 + 无客户端证书 → 仍无法连接
- 企业 PKI 集成

**不足**：
- 客户端证书发放 / 撤销复杂
- 笔记本丢失 → 撤销窗口期 cert revocation

### 5.4 Sticky Cookie HMAC

[§16 §九.2](./16-high-availability.md) 已述：

```
qwen-aff cookie = base64( HMAC-SHA256(sessionId, server-secret) )
HttpOnly + Secure + SameSite=Strict
```

防 cookie 篡改路由到任意 pod。

### 5.5 完整的认证三因子

| 因子 | 强度 | Stage |
|---|---|---|
| Bearer token | 默认 | Stage 1+ |
| + TLS server cert | 默认 | Stage 1+ |
| + mTLS client cert | 加固 | Stage 5+ 企业 |
| + IP allowlist | 加固 | Stage 5+ 企业 |
| + Time-based OTP（capability_request 二次确认）| 高敏感 | 可选 |

## 六、NAT 穿透方案

daemon 在内网 / 家里 / 防火墙后，CLI 在公网，3 种主流方案：

### 6.1 Cloudflare Tunnel（推荐）

```bash
# daemon 端
$ cloudflared tunnel login
$ cloudflared tunnel create qwen
$ cloudflared tunnel route dns qwen daemon.mydomain.com
$ cloudflared tunnel run --url http://localhost:8080 qwen

# CLI 端（任何地方）
$ qwen --daemon https://daemon.mydomain.com --token $QWEN_TOKEN
```

**优点**：零配置 NAT 穿透 / 自动 TLS / DDoS 防护
**缺点**：依赖 Cloudflare / 流量过它家

### 6.2 Tailscale（推荐内网）

```bash
# daemon 端 + CLI 端都装 Tailscale
$ tailscale up

# daemon 端获取 tailscale IP / hostname
$ tailscale ip -4   # 100.64.0.5

# CLI 端
$ qwen --daemon http://workstation:8080 --token $QWEN_TOKEN
       # workstation 是 Tailscale magic DNS hostname
```

**优点**：mesh VPN 端到端加密 / 零信任 / 跨 OS
**缺点**：需双端都装客户端

### 6.3 SSH Reverse Tunnel

```bash
# daemon 在内网 NAT 后，主动反向连到公网 jumphost
$ ssh -R 8080:localhost:8080 jumphost.example.com -N

# CLI 端
$ qwen --daemon http://jumphost.example.com:8080 --token $QWEN_TOKEN
```

**优点**：纯 SSH 协议，无第三方依赖
**缺点**：手动管理隧道存活 / 无 HTTPS 默认

### 6.4 直接公网部署（云端 daemon）

```yaml
# k8s Service + Ingress + Let's Encrypt
apiVersion: networking.k8s.io/v1
kind: Ingress
spec:
  tls:
  - hosts: [daemon.qwen.example.com]
    secretName: qwen-tls
  rules:
  - host: daemon.qwen.example.com
    http: ...
```

**Stage 6 SaaS 默认**。

### 6.5 方案选择决策

| 场景 | 推荐 |
|---|---|
| 个人 / 单人开发 / 家庭 NAS daemon | Tailscale |
| 团队 / 公司内网 daemon | Cloudflare Tunnel / Tailscale |
| Stage 6 SaaS（公网 daemon）| Ingress + Let's Encrypt |
| 临时测试 / 演示 | Cloudflare quick tunnel |
| 安全要求高 | mTLS + Tailscale + IP allowlist |

## 七、性能优化：Local Echo

### 7.1 问题

50ms RTT 下，每个键击 round-trip：

```
T=0    用户按 'h'
T=0    CLI sendKey('h')
T=50   daemon ack → 显示 'h'
```

50ms 视觉滞后用户能感知。100ms+ 网络环境下不可用。

### 7.2 Local Echo 设计

```
T=0    用户按 'h'
T=0    CLI 立即在屏幕渲染 'h'（local echo）
T=0    CLI sendKey('h') 发到 daemon（异步）
T=50   daemon ack（不影响 UI 已渲染）
```

**实现**：

```ts
// packages/cli/src/ui/InputBox.tsx
function InputBox() {
  const [localValue, setLocalValue] = useState('')
  const { sendKey } = useDaemonClient()
  
  const handleKey = (key: string) => {
    setLocalValue(v => v + key)        // 立即本地渲染
    sendKey(key)                         // 异步发 daemon
  }
  
  return <Input value={localValue} onKey={handleKey} />
}
```

### 7.3 哪些场景必须 local echo

| 场景 | local echo? | 原因 |
|---|---|---|
| Prompt 输入框 keystroke | ✓ | 高频，必须 |
| Submit prompt | ✗ | 低频 + 需 daemon 确认 |
| Tool call 决策（y/n）| ✓ | 用户希望立即看到 |
| LLM streaming 输出 | ✗ | 是 daemon 主动 push |
| 文件补全 `@file` | ✗ | 需要 daemon 端 readdir |
| 历史 Ctrl-R 检索 | ✗ | 需要 daemon transcript 检索 |

### 7.4 与 daemon 状态对账

local echo 仅是显示层乐观更新；实际状态以 daemon 为准。如果 daemon 拒绝（如内容超长）：

```
T=0   CLI 显示 "Hello world... [LONG TEXT 50KB]"
T=50  daemon 返回 { error: 'attachment_required', threshold: 10240 }
T=51  CLI UI 提示 "Auto-promoting to attachment..."
T=52  CLI POST attachment endpoint
T=53  CLI 替换 prompt 中的 inline content 为 attachment ref
```

最差情况：50ms 后 UI 短暂闪烁更新，用户可接受。

## 八、离线模式与降级

### 8.1 `--daemon-or-local`

```bash
$ qwen --daemon https://daemon.qwen.example.com \
       --daemon-or-local \
       chat
```

启动时尝试 daemon → 失败立即 fallback 到本地子进程模式（拓扑 A）。

### 8.2 daemon 不可达检测

```ts
async function tryDaemon(url: string, token: string) {
  try {
    const resp = await fetch(`${url}/v1/health`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(3000)
    })
    if (!resp.ok) throw new Error(`status ${resp.status}`)
    return true
  } catch (e) {
    return false
  }
}

if (await tryDaemon(daemonUrl, token)) {
  await runDaemonClient(daemonUrl, token)
} else {
  if (flags.daemonOrLocal) {
    console.warn('Daemon unreachable, falling back to local mode')
    await runLocalSubprocess()
  } else {
    process.exit(1)
  }
}
```

### 8.3 本地缓存

CLI 可缓存少量数据本地：

```
~/.qwen/cache/
├─ session_history/<sid>.jsonl     # 最近 7 个 session 的 transcript snapshot
├─ tools_manifest.json              # daemon /v1/tools 缓存
└─ skills_index.json                # /v1/skills 缓存
```

允许离线浏览历史 session（read-only）。

### 8.4 降级模式 UX

```
┌──────────────────────────────────────────┐
│ ⚠ Offline mode                            │
│ Daemon unreachable. Showing cached data.  │
│ [r] Retry daemon  [l] Switch to local    │
└──────────────────────────────────────────┘
```

## 九、SSE 重连体验（远端模式特殊性）

笔记本远端模式下 **断网频繁**：换 wifi / 进电梯 / hotspot 切换 / VPN 重连。

### 9.1 重连参数

```jsonc
{
  "reconnect": {
    "maxRetries": -1,                       // 无限
    "backoffMs": [1000, 2000, 5000, 10000, 30000],
    "jitter": 0.2,
    "resetAfterSuccessMs": 60000            // 1 分钟稳定后重置 backoff
  }
}
```

### 9.2 UX 状态指示

```
正常:    ● Connected · sess-abc · alice@daemon.qwen.example.com
重连中:  ◐ Reconnecting (attempt 3, in 5s) · sess-abc
失败:    ○ Disconnected · last seen 2min ago · [r] Retry now
恢复:    ● Reconnected · resuming session... [✓ caught up]
```

### 9.3 与 transcript-first 重建协调

CLI 重连时传 `Last-Event-ID`：daemon 通过 PR#3739 transcript-first fork resume 重建 session（如果命中其他 pod）→ 拉 events from Last-Event-ID + 1 → 客户端 UI 无缝续接。

## 十、与 §13 TUI 兼容性的关系

[§13](./13-tui-compatibility.md) 讨论了 TUI 在单进程 vs daemon 下的兼容性，**Local-Local 拓扑（§13 主题）**已覆盖；**本章补充 Remote-Remote 拓扑**。

| 维度 | §13 Local | §17 Remote |
|---|---|---|
| Ink 组件 | 共用 | 共用 |
| HttpAcpAdapter | 同 host fast path | 跨 host RPC + TLS |
| 5 类本地依赖 | daemon spawn 直达 | **必须走 capability 反向 RPC** |
| Latency | < 1ms | 30-100ms RTT |
| Local echo | 不需要 | **必需** |
| 离线降级 | 通常不需要（同机不会断）| **必需** |

§13 + §17 合起来构成完整的 TUI 部署矩阵。

## 十一、与 VSCode Remote-SSH 的对比借鉴

| 维度 | VSCode Remote-SSH | qwen daemon Remote |
|---|---|---|
| 协议 | 自定义 stdio over SSH | HTTP/SSE over TLS |
| 安装位置 | thin client 本地 + server 自动安装到远端 | CLI 本地（任何 OS）+ daemon 远端运维管理 |
| 文件访问 | server 端 fs API | daemon 端 fs API |
| Terminal 调起 | server 端 spawn pty | daemon 端 spawn pty + SSE 流 |
| 编辑器 | server 端是 VSCode 自身（不需调起编辑器）| daemon emit `open_editor` capability → CLI spawn $EDITOR |
| Clipboard | VSCode 内置 sync | OSC 52 / capability |
| Browser 调起 | VSCode `vscode.env.openExternal` 自动转 | daemon emit `open_browser` capability |
| 多端共享 | 单 client 独占 | **多 client 共 session（[决策 §1](./03-architectural-decisions.md)）**|
| 离线模式 | 不可用 | `--daemon-or-local` fallback |
| Tunnel | SSH | HTTPS + TLS |
| Auth | SSH key | Bearer + 可选 mTLS |

**关键借鉴点**：
- VSCode Remote-SSH 把"自动安装 server"做得好——qwen 可以做 `qwen daemon ssh-deploy <host>` 一键远端安装
- VSCode Remote-Tunnel（更新版）走 HTTPS + tunnel —— 与 qwen 设计一致

**关键差异**：
- qwen 是"多 thin client + 共 session"模型（live collaboration）；VSCode Remote-SSH 是"单 client + server"
- qwen capability 反向 RPC 抽象出 5 类，VSCode 直接是 IDE protocol（更厚）

## 十二、端到端 Setup 流程示例

### 12.1 个人开发者 + 家里 NAS daemon（Tailscale）

```bash
# === 在 NAS 上 ===
# 1. 装 daemon
$ npm i -g @qwen/daemon
$ qwen daemon init --port 8080 --tls=disabled  # Tailscale 加密足够
$ qwen tenant create personal --owner $USER

# 2. 装 Tailscale
$ curl -fsSL https://tailscale.com/install.sh | sh
$ tailscale up

# 3. 启 daemon
$ qwen daemon start

# === 在 Laptop ===
# 1. 装 Tailscale + qwen CLI
$ tailscale up
$ npm i -g @qwen/cli

# 2. 拿 token (一次性)
$ ssh nas 'qwen token create personal --scope "*"'
qwen_dev_t-personal_xxxx....

# 3. 配 profile
$ qwen profile add nas \
    --url http://nas:8080 \
    --token qwen_dev_t-personal_xxxx....

# 4. 用
$ qwen --profile nas chat
```

### 12.2 团队共享 daemon（Cloudflare Tunnel）

```bash
# === Ops 在公司 daemon 服务器 ===
$ cloudflared tunnel login
$ cloudflared tunnel create qwen-team
$ cloudflared tunnel route dns qwen-team daemon.team.example.com
$ cloudflared tunnel run --url http://localhost:8080 qwen-team &

$ qwen tenant create team-alpha --members alice,bob,charlie

# === 团队成员 ===
$ qwen profile add team \
    --url https://daemon.team.example.com \
    --token $TEAM_TOKEN

$ qwen --profile team chat
```

### 12.3 Stage 6 SaaS

```bash
# === 用户首次登录 ===
$ qwen login
Browser opened for OAuth login...
✓ Logged in as alice@example.com
✓ Default profile created: prod (https://daemon.qwen.cloud)

# === 用 ===
$ qwen chat                 # 用默认 profile prod
```

## 十三、多端共 session 远端 UX

[决策 §1 'single' scope + §6 fan-out](./03-architectural-decisions.md) 在远端模式下尤其有价值：

```
工程师 Alice 在公司 daemon 上有 session sess-A:
  ├─ 早上：办公室笔记本 CLI 接入 sess-A
  ├─ 中午：会议室 IDE Web UI 接入 sess-A，看到上午 transcript
  ├─ 路上：手机微信 Bot 接入 sess-A，问 "进度如何？"
  └─ 晚上：家里 desktop CLI 接入 sess-A，继续

任何时刻 sess-A 内：
  - prompt 串行（同一时间只一个用户在输入）
  - events 全部 fan-out 到所有 subscribers
  - permission 第一个回应的 client 决定
```

远端模式天然消除"必须用某台机器"的束缚。

## 十四、安全考量

### 14.1 防止 capability 反向 RPC 滥用

daemon emit `open_browser` 可能是钓鱼攻击向量（如果 daemon 被入侵）：

| 攻击 | 防御 |
|---|---|
| 恶意 daemon emit `open_browser → http://phishing.com` | CLI 显示 URL 给用户确认（critical urgency 必须 prompt）|
| 恶意 daemon emit `clipboard → write` 覆盖密码 | clipboard write 不静默；显示 "daemon 写入了剪贴板" |
| 恶意 daemon emit `file_picker` 诱导上传敏感文件 | 用户主动操作；CLI 显示哪些文件被读 |
| daemon emit `open_editor` 写恶意 vim modeline | tmpfile 用 `/tmp/qwen-edit-<random>`，不在 git 工作树 |

CLI 端的 capability handler 应该**明确显示意图给用户**。

### 14.2 防止跨 tenant 嗅探

CLI 端必须验证收到的 SSE event `session_id` 与自己订阅的 sessionId 匹配。daemon 端 routing bug 不应导致跨 session 数据泄漏。

### 14.3 Token 安全

- 不写入 git tracked 文件
- `~/.qwen/profiles/*.json` 权限 600
- macOS Keychain / Windows Credential Manager / Linux libsecret 集成（可选）
- 短期 OAuth refresh token 优于长期 bearer token

## 十五、与决策的协同

| 决策 | Remote 模式影响 |
|---|---|
| §1 sessionScope='single' | Remote 模式下尤其有价值，跨设备共 session |
| §3 MCP per-workspace | MCP 在 daemon 端 spawn，看到的是 daemon 端 fs（拓扑 C 正确） |
| §4 FileReadCache per-session | session-private 跨设备共享时仍正确（cache 在 daemon 端）|
| §5 Permission 第 4 mode 'daemon-http' | Remote 是 daemon-http 的常见使用场景 |
| §6 多 client fan-out + first responder | Remote 多端协作的核心 |
| §11 多租户 + sandbox | Remote 是多租户的常见部署 |
| §12 越权防御 | Remote 加固：cookie HMAC + mTLS + IP allowlist |
| §16 HA | Remote SSE 重连协议（Last-Event-ID）必需 |

## 十六、Stage 1-6 各阶段 Remote 支持矩阵

| Stage | Remote-Remote | Capability RPC | NAT 穿透 | 备注 |
|---|---|---|---|---|
| Stage 1 (HTTP-bridge) | ⚠ 仅 localhost | ✗ | ✗ | MVP 先做 local-local |
| Stage 2 (原生 daemon) | ✓ 实验性 | partial（editor / clipboard）| ✓ | 推 Tailscale 模式 |
| Stage 3 (完整 daemon) | ✓ | ✓ 全 5 类 | ✓ | 默认推荐 remote |
| Stage 4 (多租户) | ✓ | ✓ | ✓ | + tenant 隔离 |
| Stage 5 (sandbox) | ✓ | ✓ | ✓ | + sandbox 在 daemon 端 |
| Stage 6 (SaaS HA) | ✓✓ 主部署模式 | ✓ | mTLS + Cloudflare | Stage 6 默认就是 Remote |

## 十七、一句话总结

**Qwen daemon CLI 远端连接 = HTTP/SSE+TLS+Bearer token 设计天然支持，推荐拓扑 C（workspace 与 daemon 同机），通过 Client Capability 反向 RPC 协议（5 类：editor/clipboard/browser/notification/file_picker）让 daemon 可"调起"本地 editor 等本机依赖。NAT 穿透 Cloudflare Tunnel / Tailscale / SSH reverse tunnel 三选一。Local echo 抹平 keystroke RTT，LLM streaming 50ms 几乎无感。SSE Last-Event-ID 自动重连让笔记本网络抖动无感（继承 §16 协议）。`--daemon-or-local` flag 支持离线降级到本地子进程模式。Stage 6 SaaS 部署模式默认就是 Remote-Remote。与 VSCode Remote-SSH 设计哲学一致但更进一步：多 client 共 session 的 live collaboration 是 Remote 模式下的杀手级特性。**

---

[← 返回 README](./README.md) · [下一篇：多端协调策略 →](./18-client-coordination.md)
