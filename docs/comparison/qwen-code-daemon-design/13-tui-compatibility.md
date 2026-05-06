# 13 — TUI 单进程 vs Daemon 兼容性

> [← 上一篇：水平越权防御](./12-horizontal-privilege-defense.md) · [回到 README](./README.md)

> Qwen Code 的 TUI（基于 Ink + React）在单进程和 Daemon 两种模式下的兼容性分析。**结论：显示层 / 状态层 100% 兼容（同一组组件 + Context shape），数据源层用 HttpAcpAdapter 替换，5 类本地依赖功能需要 case-by-case fallback**。

## 一、TL;DR — 4 层兼容性矩阵

| 层 | 单进程 TUI | Daemon TUI | 兼容性 |
|---|---|---|:---:|
| **显示层（Ink 组件）** | `BackgroundTasksDialog.tsx` / `AgentExecutionDisplay.tsx` 等 | **同一组组件**（直接复用 `packages/cli/src/ui/components/`）| ✅ **100%** |
| **状态层（React Context / hooks）** | `BackgroundTaskViewContext` / `SessionContext` 等 | 同一份 Context shape | ✅ **100%** |
| **数据源层** | in-process（`Session.handleXxx()` 直接 import）| **HttpAcpAdapter 翻译 SSE → React state** | ⚠️ **替换** |
| **本地依赖功能** | 直接读 fs / spawn editor / clipboard | **需 daemon RPC 或 client fallback** | ⚠️ **5 类 case-by-case** |

**多 TUI 客户端共 session** 是 daemon 模式的免费红利（决策 §1 默认 `single` + §6 fan-out 启用）。

## 二、Qwen TUI 现状（单进程模式）

### 2.1 组件结构

源码位置 `packages/cli/src/ui/`：

```
packages/cli/src/ui/
├─ components/
│   ├─ background-view/                    # PR#3488/3720/3791/3836 (4 kinds)
│   │   ├─ BackgroundTasksPill.tsx          (~40 行 · 状态行运行计数)
│   │   ├─ BackgroundTasksDialog.tsx        (~470 行 · 4 kinds 统一 dialog)
│   │   └─ MonitorDetailBody.tsx            (PR#3791 Monitor 详情)
│   ├─ subagents/runtime/AgentExecutionDisplay.tsx  (3 档 compact/default/verbose)
│   ├─ messages/ToolGroupMessage.tsx         (焦点锁 PR#3771)
│   ├─ permission/PermissionRequestDialog.tsx
│   ├─ mcp/                                  (MCP 连接状态)
│   ├─ agent-view/                           (subagent 视图)
│   ├─ views/                                (主视图 / 设置视图)
│   └─ shared/                                (复用 UI primitives)
├─ contexts/
│   ├─ AppContext.tsx                        (顶层应用状态)
│   ├─ BackgroundTaskViewContext.tsx          (4 kinds 任务状态)
│   ├─ SessionContext.tsx                     (session 状态)
│   ├─ KeypressContext.tsx                    (键盘事件)
│   ├─ ShellFocusContext.tsx                  (焦点锁实现 PR#3771)
│   ├─ StreamingContext.tsx                   (流式输出)
│   ├─ OverflowContext.tsx                    (输出截断)
│   ├─ ConfigContext.tsx                      (配置)
│   ├─ SettingsContext.tsx                    (settings)
│   ├─ UIActionsContext.tsx                   (UI action dispatcher)
│   ├─ UIStateContext.tsx                     (UI state)
│   ├─ AgentViewContext.tsx                   (agent 视图)
│   ├─ CompactModeContext.tsx                 (compact 模式)
│   └─ VimModeContext.tsx                     (Vim 输入)
├─ hooks/                                     (业务逻辑 hooks)
│   ├─ atCommandProcessor.ts                  (@文件路径补全)
│   ├─ slashCommandProcessor.ts               (/命令处理)
│   ├─ shellCommandProcessor.ts               (!shell 命令)
│   ├─ useAgentsManagerDialog.ts
│   ├─ useAgentStreamingState.ts
│   └─ ...
├─ commands/                                  (slash 命令实现)
├─ editors/                                   (输入编辑器)
├─ themes/                                    (主题，OSC 11 检测)
├─ layouts/                                   (TUI 布局)
└─ noninteractive/                            (headless 模式 UI)
```

**关键观察**：所有组件 + Contexts 都**通过 React 抽象**与具体数据源解耦——组件只关心 props / Context value 的 shape，不关心数据从哪里来。

### 2.2 单进程数据流

```
┌─────────────────────────────────────────────────────┐
│ qwen 主进程（单进程模式）                            │
│                                                      │
│  ┌──────────────────────────────────┐               │
│  │ Ink TUI（React 树）                 │               │
│  │ ├─ BackgroundTasksPill           │               │
│  │ │   └─ useBackgroundTaskView()    │               │
│  │ ├─ BackgroundTasksDialog          │               │
│  │ │   └─ 同 hook                    │               │
│  │ └─ ToolGroupMessage（焦点锁）      │               │
│  └──────────────────────────────────┘               │
│              ↑                                       │
│  ┌──────────────────────────────────┐               │
│  │ React Contexts                    │               │
│  │ ├─ BackgroundTaskViewContext      │               │
│  │ ├─ SessionContext                 │               │
│  │ └─ ...                            │               │
│  └──────────────────────────────────┘               │
│              ↑                                       │
│  ┌──────────────────────────────────┐               │
│  │ Provider（订阅 in-process registry）│               │
│  │ - subscribeToBackgroundTaskRegistry()              │
│  │ - subscribeToSessionEmitter()                      │
│  └──────────────────────────────────┘               │
│              ↑                                       │
│  ┌──────────────────────────────────┐               │
│  │ core (in-process)                 │               │
│  │ ├─ BackgroundTaskRegistry          │               │
│  │ ├─ Session                        │               │
│  │ ├─ MCP / LSP managers              │               │
│  │ └─ LLM HTTP client                 │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

**特点**：所有数据通过函数调用 / EventEmitter 在同一 V8 isolate 内传递，零开销。

## 三、Daemon TUI 数据流

```
TUI process (lightweight)              daemon process
                                       (持有所有状态)
┌────────────────────────────┐        ┌─────────────────────┐
│ Ink TUI (React 树)          │        │ HTTP / SSE server   │
│ ├─ BackgroundTasksPill      │        │                     │
│ ├─ BackgroundTasksDialog     │        │                     │
│ └─ 其他组件                  │        │                     │
└────────────────────────────┘        │                     │
              ↑                        │                     │
┌────────────────────────────┐        │                     │
│ React Contexts              │        │                     │
│ (与单进程模式同 shape)       │        │                     │
└────────────────────────────┘        │                     │
              ↑                        │                     │
┌────────────────────────────┐        │                     │
│ HttpAcpAdapter              │←HTTP/SSE→│ HttpAcpAdapter   │
│ - subscribeSse()            │        │ (server side)       │
│ - onSessionNotification()   │        │                     │
└────────────────────────────┘        │                     │
                                       └─────────────────────┘
              ↓                                  ↑
              │ keypress events                  │
              │ /edit / file completion          │
              ↓                                  ↓
┌────────────────────────────┐        ┌─────────────────────┐
│ 本地资源                    │        │ core (in-process)   │
│ - stdin keypress            │        │ ├─ Session          │
│ - $EDITOR spawn             │        │ ├─ MCP / LSP        │
│ - 剪贴板 OSC 52             │        │ ├─ Background       │
│ - 终端能力（OSC 11 主题）   │        │ └─ FileReadCache    │
└────────────────────────────┘        └─────────────────────┘
```

## 四、4 层各自详解

### 4.1 显示层（100% 兼容）

```ts
// packages/cli/src/ui/components/background-view/BackgroundTasksDialog.tsx
// 单进程和 daemon 模式都用同一份代码

export function BackgroundTasksDialog() {
  const { tasks, selectedTaskId, dispatch } = useBackgroundTaskView()
  
  return (
    <Box flexDirection="column">
      {tasks.map((task) => (
        <Box key={task.id}>
          <Text>[{task.kind}] {task.title}</Text>
          {task.kind === 'monitor' && <MonitorDetailBody task={task} />}
        </Box>
      ))}
    </Box>
  )
}
```

**这个组件不知道 tasks 从哪里来**——单进程模式下来自 `BackgroundTaskRegistry.publish()`，daemon 模式下来自 SSE event。组件代码 0 改动。

### 4.2 状态层（100% 兼容）

```ts
// packages/cli/src/ui/contexts/BackgroundTaskViewContext.tsx
interface BackgroundTaskViewValue {
  tasks: BackgroundTask[]              // ← 4 kinds 统一类型
  pillCount: { running, completed, failed, cancelled }
  selectedTaskId: string | null
  dispatch: (action: BackgroundTaskAction) => void
}

// Context shape 不变；仅 Provider 实现不同
const BackgroundTaskViewContext = createContext<BackgroundTaskViewValue>(...)
```

**Provider 切换**：

```tsx
// 单进程模式 Provider
<InProcessBackgroundTaskProvider>
  <App />
</InProcessBackgroundTaskProvider>

// daemon 模式 Provider
<HttpBackgroundTaskProvider adapter={httpAcpAdapter}>
  <App />
</HttpBackgroundTaskProvider>

// 但 <App /> 内部组件用 useBackgroundTaskView() 读 Context value 的代码完全相同
```

### 4.3 数据源层（替换，但有 adapter）

```ts
// 单进程模式 Provider 实现
function InProcessBackgroundTaskProvider({ children }) {
  const [tasks, setTasks] = useState([])
  
  useEffect(() => {
    const registry = config.getBackgroundTaskRegistry()
    const unsub = registry.subscribe((event) => {
      // event 来自 EventEmitter
      setTasks(prev => applyEvent(prev, event))
    })
    return unsub
  }, [])
  
  return <Context.Provider value={{ tasks, ... }}>{children}</Context.Provider>
}

// daemon 模式 Provider 实现
function HttpBackgroundTaskProvider({ adapter, children }) {
  const [tasks, setTasks] = useState([])
  
  useEffect(() => {
    const unsub = adapter.onSessionNotification((notif) => {
      // notif 来自 SSE event，但 shape 与单进程模式同
      if (notif.type === 'task_added') setTasks(prev => [...prev, notif.task])
      if (notif.type === 'task_status_changed') updateTask(notif.taskId, notif.status)
      // ...
    })
    return unsub
  }, [])
  
  return <Context.Provider value={{ tasks, ... }}>{children}</Context.Provider>
}
```

**关键点**：两种 Provider 的 React state 结构（tasks 数组的 entry shape）**完全相同**——因为 daemon 端用 ACP zod schema 序列化 SessionNotification，反序列化后就是与 in-process EventEmitter 同 shape 的对象。

### 4.4 本地依赖功能（5 类 case-by-case）

#### 4.4.1 文件路径补全（atCommandProcessor.ts）

```ts
// 单进程: 直接读本地 fs
const files = await fs.promises.readdir(workspaceRoot)

// daemon 同 host: 仍直接读本地 fs（最快）
//   workspace 路径在客户端能解析
//   节省 daemon 一次 RPC 往返

// daemon 跨 host: 走 daemon RPC
const res = await fetch(`${daemonUrl}/workspace/${wsId}/file?prefix=${prefix}`)
const files = await res.json()
```

**TUI 自动判断**：

```ts
function getFileCompletions(prefix: string) {
  const config = useConfig()
  if (config.daemon?.sameHost ?? true) {
    return readLocalFs(prefix)         // 同 host 走本地
  } else {
    return fetchDaemonFs(prefix)       // 跨 host 走 RPC
  }
}
```

#### 4.4.2 `/edit` 打开本地编辑器

```ts
// packages/cli/src/ui/editors/...
// 单进程和 daemon 模式都一样：spawn $EDITOR

// 即使 daemon 在远端，编辑器仍要跑在用户本地终端附近
spawn(process.env.EDITOR, [tempFilePath], { stdio: 'inherit' })

// 但文件本身在哪？
// - 同 host: temp file 在本地 /tmp，daemon 也能读
// - 跨 host: daemon download → 本地 temp → spawn editor → 上传回 daemon
```

**跨 host 完整流程**：

```ts
async function editFileViaDaemon(workspaceId: string, path: string) {
  // 1. 从 daemon 拉文件
  const content = await fetch(`${daemonUrl}/workspace/${workspaceId}/file?path=${path}`)
    .then(r => r.text())
  
  // 2. 写到本地 temp
  const tempPath = `/tmp/qwen-edit-${randomId()}`
  await fs.writeFile(tempPath, content)
  
  // 3. spawn 本地 editor
  await spawnSync(process.env.EDITOR, [tempPath], { stdio: 'inherit' })
  
  // 4. 读回修改后的内容
  const modified = await fs.readFile(tempPath, 'utf-8')
  
  // 5. 上传到 daemon（受 PR#3774 prior-read 守卫，确保走过 read 路径）
  await fetch(`${daemonUrl}/workspace/${workspaceId}/file`, {
    method: 'POST',
    body: JSON.stringify({ path, content: modified }),
  })
  
  // 6. 删本地 temp
  await fs.unlink(tempPath)
}
```

#### 4.4.3 剪贴板（OSC 52 / clipboard 命令）

```ts
// 终端 OSC 52 escape sequence，与 daemon 无关
process.stdout.write(`\x1b]52;c;${base64(text)}\x07`)

// 即使 TUI 远程连 daemon，也是在本地终端执行 OSC
// 完全 client-side，daemon 不参与
```

#### 4.4.4 键盘快捷键

```ts
// packages/cli/src/ui/contexts/KeypressContext.tsx
// 直接读 stdin，与 daemon 无关
useStdin().on('keypress', handler)

// daemon 模式: 同样在 TUI 进程内读 stdin
// 处理后通过 HTTP API 发命令到 daemon
```

#### 4.4.5 Git status 显示

```ts
// 状态行常显示 git branch / 修改文件数
// 单进程: 直接 git status
// daemon 模式:
//   - 同 host: 仍直接 git（节省 RPC）
//   - 跨 host: GET /workspace/:id/git/status
```

### 4.5 5 类本地依赖功能汇总

| 功能 | 单进程 | Daemon 同 host | Daemon 跨 host |
|---|---|---|---|
| 文件路径 Tab 补全 | 本地 fs | **本地 fs**（fast path）| daemon RPC |
| `/edit` 打开 $EDITOR | 直接 | **直接**（temp 在本地）| download → edit → upload |
| 剪贴板（OSC 52）| 终端能力 | 终端能力 | 终端能力 |
| 键盘快捷键 | stdin | stdin | stdin |
| Git status 显示 | 本地 git | **本地 git**（fast path）| daemon RPC |
| 终端主题检测（OSC 11）| 终端能力 | 终端能力 | 终端能力 |
| 大 paste 内容 | 本地处理 | 本地处理 + 上传 | 上传时 base64 |

**关键设计**：TUI 优先走**本地 fast path**（同 host），仅在跨 host 时回退到 daemon RPC。这避免了"明明 daemon 在本地仍走 HTTP"的不必要开销。

## 五、典型 TUI 启动流程

### 5.1 单进程模式（当前）

```bash
$ qwen
# 同一进程内启动 TUI + core + LLM 客户端
```

```
qwen process
├─ Ink TUI (React)
├─ core (Session / FileReadCache / MCP managers / ...)
└─ LLM HTTP client
```

### 5.2 Daemon 模式

```bash
# 终端 A: 启 daemon
$ qwen serve --port 5096
opencode-style: opencode serve listening on http://127.0.0.1:5096

# 终端 B: 启 TUI 客户端
$ qwen tui --connect http://localhost:5096
# 或
$ qwen --daemon                # 自动连本地 daemon
```

```
TUI process (lightweight)              daemon process
├─ Ink (React)              ←HTTP/SSE→ ├─ Session
├─ HttpAcpAdapter                       ├─ FileReadCache
├─ keypress / clipboard                 ├─ MCP / LSP
└─ 文件补全（如果同 host）              └─ LLM 调用
```

### 5.3 Daemon 自动启动（Stage 3）

参考 OpenCode 的 `createOpencodeServer()` 模式：

```bash
$ qwen
# 1. 检查 ~/.qwen/daemon.pid 是否有运行中 daemon
# 2. 如果没有 → 后台启 daemon → 等就绪
# 3. 启 TUI 连本地 daemon
# 用户体验: 与单进程 mode 命令一致，但底层走 daemon
```

## 六、多 TUI 客户端共 session（决策 §1 + §6 启用）

### 6.1 多 TUI 拓扑

```
                    daemon (sess-foo)
                       ↑↑↑
        ┌──────────────┼──────────────┐
       TUI A         TUI B          Web UI
      (CLI 终端 1)   (CLI 终端 2)    (浏览器)
```

### 6.2 实时同步行为

```
1. TUI A 用户输入 "请重构 src/foo.ts" → POST /session/sess-foo/prompt

2. daemon 接收 → Session.handlePrompt() 启动

3. daemon SSE 广播给所有订阅者:
     SSE event: { type: 'message_part', content: '我开始...' }
     
   所有 client 同时接收:
     - TUI A 的 SSE → 更新 React state → 屏幕实时显示
     - TUI B 的 SSE → 同样更新 → 屏幕实时显示
     - Web UI → 同样更新

4. daemon 决定调 Bash 触发 permission_request
   SSE event: { type: 'permission_request', requestId: 'r1', tool: 'Bash', ... }
   
   3 个 client 都通过 SSE 收到事件，弹 permission dialog:
     - TUI A: 终端 dialog 显示 "Allow Bash? y/n/x"
     - TUI B: 同样 dialog
     - Web UI: 浏览器对话框

5. 用户在 TUI B 上按 y
   POST /permission/r1 { allow: true, respondedBy: 'tui-b' }
   
   daemon resolve pending → 广播 permission_resolved:
     - TUI A: 自动关闭 dialog（"resolved by tui-b"）
     - TUI B: 关闭自己的 dialog
     - Web UI: 关闭对话框

6. daemon 继续执行 → SSE 广播 tool_result + message_part
```

### 6.3 焦点锁与多 client 协调

PR#3771 引入的 `ShellFocusContext` 焦点锁机制在 daemon 模式下需要重新设计：

| 场景 | 单进程 | Daemon |
|---|---|---|
| 多个 subagent 触发审批 | 焦点锁单 TUI 内串行 | 仍单 TUI 内串行（每个 TUI 独立焦点）|
| 多 TUI client 同时订阅 | N/A（只有一个 TUI）| 每个 TUI 独立显示 + first responder wins |

`ShellFocusContext` 是 client-side 概念，daemon 不感知。每个 TUI 自己管理本地焦点。

## 七、与 OpenCode TUI 对比

OpenCode 也有 TUI（参考 `packages/opencode/src/server/routes/instance/tui.ts`）：

| 维度 | OpenCode TUI | Qwen TUI（本设计）|
|---|---|---|
| 实现语言 | TypeScript（React + Ink）| **TypeScript（React + Ink，同款）** |
| 渲染层 | Ink | **Ink（同款）** |
| 连接方式 | HTTP + SSE | **HTTP + SSE/WebSocket（同款）** |
| 数据源 adapter | OpenAPI codegen client | **HttpAcpAdapter（复用 ACP zod）** |
| 多 TUI 共 session | 支持 | **支持（决策 §1 默认 single）** |
| 单进程 mode 兼容 | ❌（OpenCode 无非 daemon mode）| ✅ **完全兼容**（保留 stdio ACP / process mode）|
| 文件补全 fast path | ❌（总走 daemon）| ✅ **同 host 走本地 fs** |
| Daemon 自动启动 | ✓ `createOpencodeServer()` | Stage 3 加 |

**Qwen TUI 独有 2 项优势**：

1. **保留单进程 mode** —— 用户可选不启 daemon（小项目 / 离线 / IDE 集成 / CI 一次性），与 daemon mode 体验完全一致（同一组组件）
2. **本地 fast path** —— 同 host 时文件补全 / git status 走本地 fs，比 OpenCode 必走 daemon RPC 更快

## 八、迁移路径

### 8.1 用户视角

```
旧（仅单进程）:
  $ qwen
  → 启 qwen 进程：TUI + core + LLM 一体

新（默认仍单进程，daemon opt-in）:
  $ qwen                           # 仍单进程，零改动
  $ qwen serve                     # 显式启 daemon
  $ qwen --daemon                  # 启 TUI 连本地 daemon (Stage 2 起)
  $ qwen --daemon=remote.com:8080  # 跨 host 连 (Stage 3 起)
  $ qwen tui --connect ...         # 仅 TUI 模式
```

### 8.2 开发者视角

`packages/cli/src/ui/components/` **0 行修改**——只需新写 Provider 实现：

| 文件 | Stage 2 改动 |
|---|---|
| `packages/cli/src/ui/components/*` | 0 行（已用 Context）|
| `packages/cli/src/ui/contexts/*Context.tsx` | 0 行（shape 不变）|
| `packages/cli/src/ui/providers/in-process/*` | 抽出现有 Provider 到此 |
| `packages/cli/src/ui/providers/http-daemon/*` | **新增**（~500-1000 行 Provider 集 + adapter）|
| `packages/cli/src/cli/cmd/serve.ts` | 新增（参考 OpenCode）|
| `packages/cli/src/cli/cmd/tui-connect.ts` | 新增 |

## 九、3 阶段路线图

```
Stage 1 (Stage 1 daemon http-bridge): TUI 不动，仍单进程跑 ACP agent
  └─ TUI 体验与现状 100% 一致
  └─ daemon 在 ACP agent 子进程外面包了 HTTP 桥接，TUI 不感知

Stage 2 (Stage 2 原生 daemon): 新增 qwen tui --connect 命令
  └─ TUI 通过 HttpAcpAdapter 连 daemon
  └─ HttpBackgroundTaskProvider / HttpSessionProvider 等新 Provider
  └─ 单进程 qwen 命令保留作 reference
  └─ 多 TUI 共 session（决策 §1 默认 single）
  └─ 本地 fast path（同 host 文件补全 / git）

Stage 3 (对标 OpenCode): TUI 默认 daemon mode
  └─ qwen 命令优先尝试连本地 daemon
  └─ 失败回退到单进程
  └─ Daemon 自动启动机制（同 OpenCode createOpencodeServer）
  └─ 跨 host TUI 完整支持（含 /edit 远程文件协议）
```

## 十、TUI 兼容性测试矩阵

落地时必须保证以下场景在两种模式下行为一致：

| 测试场景 | 单进程 | Daemon |
|---|---|---|
| 用户输入 prompt → 看到 message_part 流 | ✓ | ✓ |
| Agent 调 Bash → permission dialog → 用户 approve | ✓ | ✓ |
| 4 kinds 后台任务（agent/shell/monitor/dream）pill + dialog | ✓ | ✓ |
| Subagent 输出实时显示（PR#3721 visual height bound）| ✓ | ✓ |
| Ctrl+C 取消 prompt | ✓ | ✓（daemon 端 task_stop）|
| Ctrl+E / Ctrl+F 三档切换 | ✓ | ✓ |
| 焦点锁并发审批 | ✓ | ✓（每 TUI 独立焦点 + first responder）|
| @文件路径补全 | 本地 fs | 本地（同 host）/ daemon RPC（跨 host）|
| `/edit` 打开 $EDITOR | 直接 | 同上 |
| `/clear` 清屏 | ✓ | ✓ |
| `/tasks` 列表 | ✓ | ✓ + monitor 行（PR#3801）|
| 终端主题检测（OSC 11）| ✓ | ✓（client 终端能力）|
| 多 TUI 共 session | N/A（单 TUI）| ✓（daemon 独有）|
| Daemon 重启后 TUI 自动重连 | N/A | ✓（SSE auto-reconnect）|

## 十一、关键挑战与设计

### 11.1 SSE 断线重连

```ts
class HttpAcpAdapter {
  private sse: EventSource
  private retryDelay = 1000
  
  async start() {
    this.sse = new EventSource(`${this.baseUrl}/session/${this.sessionId}/events`, {
      headers: { 'Authorization': `Bearer ${this.token}` },
    })
    
    this.sse.onerror = () => {
      this.sse.close()
      // 指数退避重连
      setTimeout(() => this.start(), this.retryDelay)
      this.retryDelay = Math.min(this.retryDelay * 2, 30_000)
    }
    
    this.sse.onopen = () => {
      this.retryDelay = 1000  // 成功连接重置
      // 可选: 触发 LoadSession 重新拉取最新 transcript（处理断线期间的 missed events）
    }
  }
}
```

### 11.2 大 paste 内容处理

```ts
// 用户粘贴大段代码到 prompt
// 单进程: TUI 直接处理
// daemon 模式:
//   - 小内容(<10KB): HTTP body 直接送
//   - 大内容(>10KB): 先 POST /session/:id/attachment 获取 attachmentId
//     再 prompt body 引用 { type: 'attachment', id: attachmentId }
//   - 与 PR#3500 系列大 paste 自动外化设计协调
```

### 11.3 主题切换

```ts
// 主题状态在 TUI client 端（影响渲染颜色）
// daemon 不感知 theme

// PR#3460 已实现 OSC 11 自动检测
// daemon 模式下: TUI 检测自己的终端，daemon 仍传 raw text + tag，TUI 自己上色
```

## 十二、一句话总结

**TUI 的 Ink 组件 / React Context shape 单进程与 daemon 100% 兼容**（共用同一组 `packages/cli/src/ui/components/` + `contexts/`）—— 仅数据源层用 `HttpAcpAdapter` 替换 in-process Provider。**5 类本地依赖功能**（文件补全 / 编辑器 / 剪贴板 / 键盘 / git status）通过 client-side 处理 + 同 host fast path + 跨 host RPC 三层 fallback 优雅降级。**多 TUI 客户端共 session 是 daemon 模式的免费红利**（决策 §1 默认 `single` + §6 fan-out + first responder permission 自动启用）。**用户视角**：保留单进程命令兼容，daemon mode opt-in；Stage 3 默认连 daemon 但失败回退单进程，与 OpenCode `createOpencodeServer` 同款。

---

[← 回到 README](./README.md) · [下一篇：实体模型与层级关系 →](./14-entity-model.md)
