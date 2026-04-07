# 3. Claude Code 技术架构——开发者参考

> 本文分析 Claude Code 的核心架构：Bootstrap 启动链、QueryEngine 推理循环、22 个 Feature Flag DCE、Prompt Cache 分区、5 层压缩策略、重试退避等。这些模式大多与模型无关，可在 Qwen Code 等 Agent 中复现。
>
> **Qwen Code 对标**：启动优化（TCP preconnect）、核心循环（Mid-Turn Queue Drain）、Prompt Cache 分区、API 重试策略

---

## 1. 运行时与二进制格式

| 项目 | 详情 |
|------|------|
| **二进制格式** | ELF 64-bit LSB executable, x86-64, dynamically linked |
| **大小** | ~227 MB（单文件可执行） |
| **打包方式** | Bun 编译的单文件可执行（`bun build --compile`），内嵌 `Bun.embeddedFiles` |
| **构建工具** | Bun bundler（`bun:bundle` 编译时特性门控 + `Bun.spawn`/`Bun.hash` 等运行时 API） |
| **UI 框架** | Ink（定制 fork，内嵌于代码库，非外部依赖）+ React 19 + Yoga 布局引擎 |
| **React 编译器** | 使用 `react/compiler-runtime`（`_c` 缓存函数），非手写 memo |
| **分发方式** | npm `@anthropic-ai/claude-code` 或 `curl` 下载到 `~/.local/share/claude/versions/` |

### Bun 运行时检测

```typescript
// 源码: utils/bundledMode.ts#L7-L22
export function isRunningWithBun(): boolean {
  return process.versions.bun !== undefined   // Bun 运行时检测
}

export function isInBundledMode(): boolean {   // 编译后单文件检测
  return typeof Bun !== 'undefined'
    && Array.isArray(Bun.embeddedFiles)
    && Bun.embeddedFiles.length > 0
}
```

已确认使用的 Bun 运行时 API：`Bun.spawn()`（进程创建）、`Bun.hash()`（快速哈希）、`Bun.which()`（命令查找）、`Bun.embeddedFiles`（内嵌文件）、`Bun.stringWidth()`（终端宽度计算）、`Bun.serve()`（WebSocket 服务）。

### 内嵌原生模块

| 模块 | 用途 |
|------|------|
| `tree-sitter-bash.node` | Bash AST 解析（命令安全校验） |
| `tree-sitter-typescript.node` | TypeScript AST 解析 |
| `tree-sitter-json.node` / `tree-sitter-yaml.node` | JSON/YAML 解析 |
| `tree-sitter-kotlin.node` | Kotlin 解析 |
| `sharp.node` / `image-processor.node` | 图片处理（Sharp 库） |
| `audio-capture.node` | 音频捕获（语音模式） |
| `file-index.node` | 文件索引（代码搜索） |
| `color-diff.node` | 颜色 diff 显示 |
| `resvg.wasm` | SVG 渲染（WebAssembly） |

### 构建时特性门控（Dead Code Elimination）

Bun bundler 的 `feature()` 函数在编译时求值，未启用的特性分支被完全移除：

```typescript
// 源码: entrypoints/cli.tsx#L1
import { feature } from 'bun:bundle'

// 编译时条件——external 构建中 feature('DUMP_SYSTEM_PROMPT') 为 false，整个分支 DCE
if (feature('DUMP_SYSTEM_PROMPT') && args[0] === '--dump-system-prompt') { ... }

// 条件导入——未命中时 require 不执行，模块不进入 bundle
const SleepTool = feature('PROACTIVE') || feature('KAIROS')
  ? require('./tools/SleepTool/SleepTool.js').SleepTool
  : null
```

已知的特性门控：

| Feature Flag | 控制内容 |
|-------------|----------|
| `DUMP_SYSTEM_PROMPT` | `--dump-system-prompt` 调试命令（ant-only） |
| `DAEMON` | Daemon worker 模式 |
| `BRIDGE_MODE` | Remote Control 桥接模式 |
| `VOICE_MODE` | `/voice` 语音交互 |
| `COORDINATOR_MODE` | 多代理 Coordinator 调度 |
| `PROACTIVE` / `KAIROS` | Assistant 模式（Kairos） |
| `AGENT_TRIGGERS` / `AGENT_TRIGGERS_REMOTE` | Cron 调度触发器 |
| `BASH_CLASSIFIER` | Bash 命令 AI 分类器（ant-only） |
| `ABLATION_BASELINE` | Harness 消融实验基线 |
| `TERMINAL_PANEL` | 终端面板捕获工具 |
| `WEB_BROWSER_TOOL` | Web 浏览器工具 |
| `WORKFLOW_SCRIPTS` | 工作流脚本 |
| `HISTORY_SNIP` | 历史剪辑工具 |
| `UDS_INBOX` | Unix Domain Socket 邮箱 |
| `CONTEXT_COLLAPSE` | 上下文折叠 |
| `MCP_SKILLS` | MCP 技能注册 |
| `CHICAGO_MCP` | Computer Use MCP |
| `OVERFLOW_TEST_TOOL` | 溢出测试工具 |
| `MONITOR_TOOL` | 监控工具 |
| `KAIROS_GITHUB_WEBHOOKS` | GitHub Webhook 订阅 |
| `KAIROS_PUSH_NOTIFICATION` | 推送通知 |

> **注意**：`feature()` 是编译时宏，非运行时判断。External 构建中大量 ant-only 代码被完整剥离。

---

## 2. Bootstrap 启动链

启动链分三级，每级延迟加载以压缩启动延迟：

```
cli.tsx (entrypoint)
  │
  ├─ 快速路径 (zero import)
  │   --version → console.log(MACRO.VERSION) → 退出
  │
  ├─ 专用路径 (minimal import)
  │   --dump-system-prompt    → 输出系统提示 → 退出
  │   --claude-in-chrome-mcp  → Chrome 扩展 MCP → 退出
  │   --chrome-native-host    → Chrome 原生宿主 → 退出
  │   --computer-use-mcp      → Computer Use MCP → 退出
  │   --daemon-worker=<kind>  → Daemon Worker → 退出
  │   remote-control / rc     → Bridge 模式 → 退出
  │
  └─ 主路径 → import main.tsx
        │
        ├─ 并行预取（模块顶层 side-effect）
        │   ├── profileCheckpoint('main_tsx_entry')   // 启动计时
        │   ├── startMdmRawRead()                     // MDM 策略子进程
        │   └── startKeychainPrefetch()               // macOS 钥匙串 OAuth + API Key
        │
        ├─ Commander.js 命令注册
        │   ├── 全局选项: --model, --print, --continue, --resume, --permission-mode, --mcp-config, --agent ...
        │   └── 子命令: remote-control, config, mcp, session, ...
        │
        ├─ init() (entrypoints/init.ts，memoized 仅执行一次)
        │   ├── enableConfigs()                       // 启用配置系统
        │   ├── applySafeConfigEnvironmentVariables()  // 安全环境变量（Trust 前）
        │   ├── applyExtraCACertsFromConfig()          // CA 证书（Bun TLS 缓存前）
        │   ├── setupGracefulShutdown()               // SIGINT/SIGTERM 处理
        │   ├── initialize1PEventLogging()            // 第一方事件日志（异步）
        │   ├── configureGlobalMTLS() + configureGlobalAgents()  // mTLS + 代理
        │   ├── preconnectAnthropicApi()              // TCP+TLS 预连接（~100-200ms）
        │   └── initializePolicyLimitsLoadingPromise()  // 策略限制 Promise 初始化
        │
        ├─ main.tsx 命令处理器
        │   ├── initializeGrowthBook()                // Feature Flag 服务
        │   ├── loadPolicyLimits()                    // 策略限制加载
        │   ├── loadRemoteManagedSettings()           // 远程托管设置
        │   └── initializeTelemetryAfterTrust()       // 遥测初始化（延迟到 Trust Dialog 之后）
        │
        └─ launchRepl() → Ink render → REPL 循环
```

> 源码: `entrypoints/cli.tsx#L33-L106`、`main.tsx#L1-L80`

### 远程环境特殊处理

```typescript
// 源码: entrypoints/cli.tsx#L9-L14
if (process.env.CLAUDE_CODE_REMOTE === 'true') {
  process.env.NODE_OPTIONS = existing
    ? `${existing} --max-old-space-size=8192`
    : '--max-old-space-size=8192'   // 容器环境 16GB，子进程限 8GB
}
```

### 消融实验基线

```typescript
// 源码: entrypoints/cli.tsx#L21-L26
if (feature('ABLATION_BASELINE') && process.env.CLAUDE_CODE_ABLATION_BASELINE) {
  // 关闭 thinking、compact、auto memory、background tasks 等
  // 用于 harness-science L0 消融实验
  for (const k of ['CLAUDE_CODE_SIMPLE', 'CLAUDE_CODE_DISABLE_THINKING', ...]) {
    process.env[k] ??= '1'
  }
}
```

---

## 3. 模块架构

```
claude-code/  # 源码目录结构
├── entrypoints/              # 入口点
│   ├── cli.tsx               # Bootstrap 入口（快速路径分发）
│   ├── init.ts               # 初始化（配置/遥测/安全）
│   └── mcp.ts                # MCP Server 入口
├── main.tsx                  # 主 CLI 入口（4,683 行，Commander 注册）
├── QueryEngine.ts            # 核心对话引擎（1,295 行）
├── Tool.ts                   # 工具接口定义 & ToolPermissionContext
├── tools.ts                  # 工具注册表（getAllBaseTools / getTools）
├── commands.ts               # 命令注册表（~88 命令，含 ant-only）
├── cost-tracker.ts           # 成本追踪器
│
├── state/                    # 状态管理
│   ├── store.ts              # 通用 Store（35 行 pub/sub）
│   ├── AppStateStore.ts      # AppState 类型定义
│   └── AppState.tsx          # React Provider + 订阅
│
├── services/                 # 后端服务
│   ├── api/
│   │   ├── client.ts         # Anthropic SDK 客户端工厂（390 行）
│   │   ├── claude.ts         # 核心 API 调用 + 流式处理（3,419 行）
│   │   ├── withRetry.ts      # 重试与退避（823 行）
│   │   ├── errors.ts         # 错误分类
│   │   ├── logging.ts        # Usage 追踪
│   │   ├── bootstrap.ts      # Bootstrap 数据预取
│   │   └── promptCacheBreakDetection.ts  # 缓存断裂检测
│   ├── analytics/
│   │   ├── index.ts          # logEvent() 中央遥测
│   │   ├── growthbook.ts     # Feature Flag 服务
│   │   ├── datadog.ts        # Datadog APM
│   │   └── firstPartyEventLogger.ts  # 第一方事件
│   ├── mcp/                  # MCP 客户端/服务端
│   ├── compact/              # 会话压缩
│   ├── PromptSuggestion/     # Prompt 建议 + Speculation
│   ├── policyLimits/         # 策略限制
│   └── remoteManagedSettings/  # 远程托管设置
│
├── tools/                    # 39 个工具实现
│   ├── BashTool/             # Bash 执行 + 安全校验（23 项检查）
│   ├── FileEditTool/         # 文件编辑（差分替换）
│   ├── FileReadTool/         # 文件读取
│   ├── FileWriteTool/        # 文件写入
│   ├── GlobTool/             # 文件搜索
│   ├── GrepTool/             # 内容搜索
│   ├── AgentTool/            # 子代理生成
│   ├── SkillTool/            # Skill 调用
│   ├── WebSearchTool/        # Web 搜索
│   ├── WebFetchTool/         # Web 抓取
│   ├── TaskCreateTool/ ...   # 任务管理工具集
│   └── ...
│
├── commands/                 # ~88 斜杠命令（含 ant-only）
├── components/               # React/Ink UI 组件
├── hooks/                    # React Hooks
├── skills/                   # Skill 加载与注册
├── coordinator/              # 多代理 Coordinator
├── bridge/                   # Remote Control 桥接
├── assistant/                # Assistant（Kairos）模式
├── daemon/                   # Daemon Worker
├── memdir/                   # Auto Memory 系统
├── ink/                      # Ink 渲染引擎（差分渲染/防闪烁）
├── cli/                      # 非交互模式
│   ├── print.ts              # Headless 模式（5,594 行）
│   ├── structuredIO.ts       # SDK 结构化 I/O
│   └── remoteIO.ts           # 远程 I/O
│
├── utils/                    # 工具函数
│   ├── permissions/          # 权限系统
│   ├── sandbox/              # 沙箱管理
│   ├── hooks/                # Hook 事件系统
│   ├── model/                # 模型选择与路由
│   ├── settings/             # 设置加载
│   ├── bash/                 # Bash 解析（shell-quote, tree-sitter）
│   ├── systemPrompt.ts       # 系统提示组装
│   ├── context.ts            # 上下文窗口管理
│   ├── config.ts             # 配置文件加载
│   ├── fastMode.ts           # Fast Mode 管理
│   ├── fileHistory.ts        # 文件历史追踪
│   ├── gracefulShutdown.ts   # 优雅退出
│   └── startupProfiler.ts    # 启动性能分析
│
└── constants/                # 编译时常量
    ├── prompts.ts            # 系统提示模板
    ├── betas.ts              # Beta 头
    ├── oauth.js              # OAuth 配置
    └── tools.js              # 工具常量
```

---

## 4. 核心运行时循环

### 4.1 QueryEngine — 对话引擎

`QueryEngine` 是核心类，实现 `AsyncGenerator` 模式驱动多轮对话：

```
用户输入 → processUserInput() → QueryEngine.submitMessage()
  │
  ├─ 组装系统提示 (fetchSystemPromptParts)
  ├─ 加载 Memory Prompt (loadMemoryPrompt)
  ├─ 序列化对话历史 (normalizeMessagesForAPI)
  ├─ 构造工具列表 (getTools)
  │
  ├─ API 调用 (query → queryModelWithStreaming)
  │   └─ for await (const part of stream)  ← SSE 事件流
  │       ├─ message_start      → 初始化 usage
  │       ├─ content_block_start → 创建内容块（text/tool_use/thinking）
  │       ├─ content_block_delta → 累积部分内容
  │       ├─ content_block_stop  → 完成内容块
  │       ├─ message_delta       → 更新 stop_reason
  │       └─ message_stop        → 结束流
  │
  ├─ 工具调用处理
  │   ├─ 权限检查 (canUseTool)
  │   ├─ Hook 触发 (PreToolUse / PostToolUse)
  │   ├─ 工具执行 → 收集结果
  │   └─ 结果注入对话历史 → 继续下一轮
  │
  └─ 终止条件
      ├─ stop_reason === 'end_turn'   → 正常结束
      ├─ stop_reason === 'max_tokens' → 输出截断
      ├─ 用户中断 (AbortController)   → 中止
      └─ Token 预算耗尽               → 触发 compact
```

> 源码: `QueryEngine.ts#L1-L100`

### 4.2 两种运行模式

| 模式 | 入口 | 用途 |
|------|------|------|
| **交互模式** (REPL) | `components/REPL.tsx` → Ink render | 终端交互，React 驱动 UI |
| **Headless 模式** | `cli/print.ts:runHeadless()` | `--print` 管道模式、SDK 集成、CI |

交互模式使用 Ink 的 React 渲染循环，每次状态变更触发 re-render；Headless 模式无 UI 依赖，直接输出 JSON/文本流。

### 4.3 进程模型

Claude Code 是 **单进程事件循环**，子进程用于：

| 场景 | 方式 |
|------|------|
| Agent 工具调用 | `AgentTool` spawn 子 Claude Code 进程 |
| MDM 策略读取 | `plutil`（macOS）/ `reg query`（Windows）子进程 |
| Keychain 预取 | macOS Keychain 读取子进程 |
| Bash 命令执行 | `child_process.spawn` 执行用户命令 |
| Daemon Worker | `--daemon-worker=<kind>` 轻量工作进程 |

---

## 5. 状态管理

### 5.1 Store 模式

极简 pub/sub Store，35 行代码：

```typescript
// 源码: state/store.ts#L10-L34
export function createStore<T>(initialState: T, onChange?: OnChange<T>): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()
  return {
    getState: () => state,
    setState: (updater) => {
      const prev = state
      const next = updater(prev)
      if (Object.is(next, prev)) return  // 引用相等跳过
      state = next
      onChange?.({ newState: next, oldState: prev })
      for (const listener of listeners) listener()
    },
    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
```

### 5.2 AppState 类型

`AppState` 是全局状态的单一来源，通过 React Context 分发：

```typescript
// 源码: state/AppStateStore.ts#L89-L158（精简）
type AppState = DeepImmutable<{
  settings: SettingsJson                    // 用户设置
  verbose: boolean                          // 详细模式
  mainLoopModel: ModelSetting               // 当前模型
  mainLoopModelForSession: ModelSetting     // 会话级模型
  statusLineText: string | undefined        // 状态栏文本
  isBriefOnly: boolean                      // Brief 模式
  toolPermissionContext: ToolPermissionContext  // 权限上下文
  agent: string | undefined                 // --agent 指定的代理
  kairosEnabled: boolean                    // Assistant 模式
  // Speculation 状态
  speculation: SpeculationState             // idle | active
  // Remote Control 桥接状态
  replBridgeEnabled: boolean
  replBridgeConnected: boolean
  replBridgeSessionActive: boolean
  replBridgeConnectUrl: string | undefined
  replBridgeSessionUrl: string | undefined
  // ...
}> & {
  tasks: { [taskId: string]: TaskState }    // 后台任务
  agentNameRegistry: Map<string, AgentId>   // 代理名称注册表
  mcp: { clients, tools, commands, resources }  // MCP 状态
  plugins: { enabled, disabled, commands, errors }  // 插件状态
  agentDefinitions: AgentDefinitionsResult  // .claude/agents/ 定义
  fileHistory: FileHistoryState             // 文件历史快照
  attribution: AttributionState             // Commit 归属追踪
}
```

### 5.3 Speculation 状态

`SpeculationState` 管理 Prompt Suggestion 的推测执行：

```typescript
// 源码: state/AppStateStore.ts#L58-L77
type SpeculationState =
  | { status: 'idle' }
  | {
      status: 'active'
      id: string                          // 推测 ID
      abort: () => void                   // 取消函数
      startTime: number
      messagesRef: { current: Message[] } // 可变引用——避免每条消息 spread
      writtenPathsRef: { current: Set<string> }  // 覆盖层写入路径
      boundary: CompletionBoundary | null
      suggestionLength: number
      toolUseCount: number
      isPipelined: boolean                // 流水线模式
    }
```

---

## 6. API 通信层

### 6.1 多 Provider 客户端工厂

`getAnthropicClient()` 根据配置创建不同 Provider 的 SDK 客户端：

```
┌─────────────────────────────────────────────────┐
│              getAnthropicClient()                │
│        源码: services/api/client.ts#L88          │
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐│
│  │ Direct   │  │ Bedrock  │  │ Vertex AI      ││
│  │ API      │  │ (AWS)    │  │ (GCP)          ││
│  ├──────────┤  ├──────────┤  ├────────────────┤│
│  │Anthropic │  │Anthropic │  │AnthropicVertex ││
│  │SDK 直连  │  │Bedrock   │  │+ GoogleAuth    ││
│  └──────────┘  └──────────┘  └────────────────┘│
│  ┌──────────────────────────────────────────────┤│
│  │ Azure Foundry                                ││
│  │ AnthropicFoundry + DefaultAzureCredential    ││
│  └──────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

| Provider | 认证方式 | 环境变量 |
|----------|----------|----------|
| **Direct API** | `ANTHROPIC_API_KEY` 或 OAuth Token | `ANTHROPIC_API_KEY` |
| **AWS Bedrock** | AWS SDK 默认凭证链 | `AWS_REGION`, `AWS_DEFAULT_REGION` |
| **Google Vertex** | `google-auth-library` | `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION` |
| **Azure Foundry** | API Key 或 Azure AD | `ANTHROPIC_FOUNDRY_RESOURCE`, `ANTHROPIC_FOUNDRY_API_KEY` |

客户端配置细节：

```typescript
// 源码: services/api/client.ts#L100-L150
const defaultHeaders = {
  'x-app': 'cli',                                    // 应用标识
  'User-Agent': getUserAgent(),                       // 用户代理
  'X-Claude-Code-Session-Id': getSessionId(),         // 会话 ID
  ...(containerId ? { 'x-claude-remote-container-id': containerId } : {}),
  ...(clientApp ? { 'x-client-app': clientApp } : {}),
}
// 超时: 默认 600 秒，可通过 API_TIMEOUT_MS 覆盖
timeout: parseInt(process.env.API_TIMEOUT_MS || String(600 * 1000), 10)
```

### 6.2 流式处理

SSE（Server-Sent Events）事件处理循环：

```typescript
// 源码: services/api/claude.ts#L1930-L2020（精简）
for await (const part of stream) {
  switch (part.type) {
    case 'message_start':       // → 初始化 partialMessage, 更新 usage
    case 'content_block_start': // → 创建 text/tool_use/thinking/server_tool_use 块
    case 'content_block_delta': // → 累积 text_delta / input_json_delta / thinking_delta
    case 'content_block_stop':  // → 完成内容块
    case 'message_delta':       // → 更新 stop_reason, usage
    case 'message_stop':        // → 结束
  }
}
```

**Stall 检测**（30 秒阈值）：

```typescript
// 源码: services/api/claude.ts#L1934-L1965
const STALL_THRESHOLD_MS = 30_000
if (lastEventTime !== null && timeSinceLastEvent > STALL_THRESHOLD_MS) {
  logEvent('tengu_streaming_stall', { stall_duration_ms, stall_count, ... })
}
```

### 6.3 API 端点

| 端点 | 用途 |
|------|------|
| `api.anthropic.com/v1/messages` | 核心 LLM API（Claude 模型调用） |
| `claude.ai/api/oauth/authorize` | OAuth 认证 |
| `claude.ai/api/claude_code/settings` | 远程设置获取 |
| `claude.ai/api/claude_code/policy_limits` | 策略限制查询 |
| `claude.ai/api/claude_code/team_memory` | 团队记忆（按仓库） |
| `claude.ai/api/claude_code/metrics` | 遥测上报 |
| `claude.ai/api/ws/speech_to_text/voice_stream` | 语音转文字（WebSocket） |
| `claude.ai/api/claude_cli_feedback` | 反馈提交 |

---

## 7. 模型选择与路由

### 7.1 模型解析优先级

```
1. /model 命令覆盖  (会话运行时)
2. --model CLI 参数  (启动时)
3. ANTHROPIC_MODEL 环境变量
4. 用户 settings 保存的配置
5. 订阅类型默认值
```

> 源码: `utils/model/model.ts#L80-L98`

### 7.2 默认模型

| 订阅类型 | 默认模型 |
|----------|----------|
| Max / Team Premium | Opus 4.6（1M context 如启用） |
| Pro / 其他 | Sonnet 4.6 |
| 3P Provider（Bedrock/Vertex） | Sonnet 4.5 |
| Ant 内部 | 由 Feature Flag 配置决定 |

### 7.3 Fast Mode

Fast Mode 使用相同模型但更高吞吐量的推理配置：

| 模式 | Opus 4.6 定价（每 Mtok） |
|------|--------------------------|
| Standard | $5 / $25（input / output） |
| **Fast Mode** | **$30 / $150** |

Fast Mode 与重试集成：

- 短 `retry-after`（<20s）：保持 Fast Mode 重试（保留 cache）
- 长 `retry-after`：进入冷却期，切换到 Standard
- Overage rejection：永久禁用 Fast Mode

> 源码: `services/api/withRetry.ts#L261-L314`

### 7.4 Advisor（服务端审查模型）

Advisor 是一种 **服务端工具**（`server_tool_use`），让后端使用更强的审查模型对完整对话历史进行审查：

| 项目 | 详情 |
|------|------|
| 触发方式 | 模型自主调用，无需用户参数 |
| 后端模型 | 由 Feature Flag `tengu_sage_compass` 配置（如 Opus 4.6 审查 Sonnet 输出） |
| 配置命令 | `/advisor <model>`（用户切换审查模型） |
| 结果类型 | `advisor_tool_result`（支持加密） |
| 成本追踪 | 独立追踪 advisor 的 token 用量，递归加入会话总成本 |

> 源码: `utils/advisor.ts`、`commands/advisor.ts`

### 7.5 Extended Thinking（扩展思维）

思维系统有编译时和运行时双重门控：

```
编译时: feature('ULTRATHINK')      → 代码是否包含在 bundle 中
运行时: tengu_turtle_carbon        → GrowthBook 控制是否启用
模型:   modelSupportsAdaptiveThinking()  → 仅 Claude 4.6+（Opus/Sonnet）
```

三种模式：

| 模式 | 行为 |
|------|------|
| `adaptive` | 模型自行决定是否使用思维（默认） |
| `enabled` + `budgetTokens` | 强制启用，指定 token 预算 |
| `disabled` | 完全禁用 |

配置方式：`MAX_THINKING_TOKENS` 环境变量 或 `alwaysThinkingEnabled` 设置。

> 源码: `utils/thinking.ts`

---

## 8. 上下文窗口管理

### 8.1 Context Window 解析

```
1. CLAUDE_CODE_MAX_CONTEXT_TOKENS 环境变量 (ant-only)
2. 模型名 [1m] 后缀  → 1,000,000
3. ModelCapability 数据库查询
4. Beta Header (CONTEXT_1M_BETA_HEADER)
5. Experimental Treatment (Sonnet 1M 实验)
6. Ant-only codename 配置
7. 默认: 200,000
```

> 源码: `utils/context.ts#L51-L98`

### 8.2 关键常量

| 常量 | 值 | 用途 |
|------|------|------|
| `MODEL_CONTEXT_WINDOW_DEFAULT` | 200,000 | 默认上下文窗口 |
| `COMPACT_MAX_OUTPUT_TOKENS` | 20,000 | Compact 操作最大输出 |
| `CAPPED_DEFAULT_MAX_TOKENS` | 8,000 | 默认 max_output_tokens 上限 |
| `ESCALATED_MAX_TOKENS` | 64,000 | 截断重试时的升级值 |
| `MAX_OUTPUT_TOKENS_DEFAULT` | 32,000 | 默认最大输出 |
| `MAX_OUTPUT_TOKENS_UPPER_LIMIT` | 64,000 | 最大输出上限 |

### 8.3 输出 Token 槽位优化

默认 `max_output_tokens` 被限制到 8,000（BQ p99 输出仅 4,911 tokens），避免 8-16× 的槽位过度预留。不到 1% 的请求触及限制，这些请求以 64,000 重试一次：

```
首次请求: max_output_tokens = 8,000 (CAPPED_DEFAULT_MAX_TOKENS)
         ↓ stop_reason === 'max_tokens'
重试:     max_output_tokens = 64,000 (ESCALATED_MAX_TOKENS)
```

> 源码: `utils/context.ts#L18-L25`

### 8.4 1M Context 支持

支持 1M 的模型（编译时列表）：

```typescript
// 源码: utils/context.ts#L43-L49
export function modelSupports1M(model: string): boolean {
  const canonical = getCanonicalName(model)
  return canonical.includes('claude-sonnet-4') || canonical.includes('opus-4-6')
}
```

可通过 `CLAUDE_CODE_DISABLE_1M_CONTEXT=true` 禁用（用于 HIPAA 合规）。

---

## 9. Prompt Caching

### 9.1 缓存范围

| 范围 | 适用 Provider | TTL | 用途 |
|------|-------------|-----|------|
| `global` | 仅 First-Party | — | 全用户共享的静态系统提示 |
| `org` | 所有 Provider | `5m` / `1h` | 组织级临时缓存 |

### 9.2 系统提示缓存策略

系统提示被切分为多个块，每块独立缓存控制：

| 块 | 缓存策略 |
|----|----------|
| Attribution header | 无缓存（每次变化） |
| CLI 前缀（静态指令） | Org-scoped（跨 turn 粘性） |
| 静态内容（工具描述等） | Global（仅 First-Party） |
| 动态内容（git status 等） | 无缓存（每 turn 更新） |

> 源码: `utils/api.ts#L321-L435`

### 9.3 缓存断裂检测

```typescript
// 源码: services/api/promptCacheBreakDetection.ts
// Hash 以下内容检测缓存是否断裂：
// - 系统提示内容
// - 工具 schema
// - 模型、fast mode、beta headers、effort level
// - 单独检测每个工具描述的变化
// 最小 miss 阈值: 2,000 tokens（低于不告警）
```

---

## 10. 重试与退避

### 10.1 重试参数

| 参数 | 值 |
|------|------|
| 默认最大重试 | 10 次 (`DEFAULT_MAX_RETRIES`) |
| 基础延迟 | 500ms (`BASE_DELAY_MS`) |
| 退避公式 | `500ms × 2^(attempt-1)` + 25% 抖动 |
| 尊重 `retry-after` | 是 |

> 源码: `services/api/withRetry.ts#L52-L55`

### 10.2 前台 vs 后台查询

只有 **前台查询** 才在 529（过载）时重试，后台查询立即失败以避免级联放大：

```typescript
// 源码: services/api/withRetry.ts#L62-L82
const FOREGROUND_529_RETRY_SOURCES = new Set([
  'repl_main_thread',          // 主对话循环
  'sdk',                       // SDK 调用
  'agent:custom', 'agent:default', 'agent:builtin',  // Agent 调用
  'compact',                   // 压缩操作
  'auto_mode',                 // 安全分类器
  'verification_agent',        // 验证代理
  // ...
])
```

### 10.3 529 Opus 降级

连续 3 次 529 错误后，Opus 自动降级到 Sonnet：

```
Opus 请求 → 529 (×1) → 重试 → 529 (×2) → 重试 → 529 (×3)
  → 降级到 Sonnet（防止容量级联）
```

> 源码: `services/api/withRetry.ts#L54`, `MAX_529_RETRIES = 3`

### 10.4 连接错误恢复

| 错误类型 | 恢复策略 |
|----------|----------|
| 401/403（认证） | 清除凭证缓存，刷新 OAuth Token |
| ECONNRESET / EPIPE | 禁用 Keep-Alive 连接池 |
| AWS 凭证失效 | 清除 AWS 凭证缓存并刷新 |
| GCP 凭证失效 | 清除 GCP 凭证缓存并刷新 |

### 10.5 持久重试模式（Unattended）

ant-only 的 `CLAUDE_CODE_UNATTENDED_RETRY` 模式，用于无人值守会话：

```typescript
// 源码: services/api/withRetry.ts#L96-L98
const PERSISTENT_MAX_BACKOFF_MS = 5 * 60 * 1000       // 最大退避 5 分钟
const PERSISTENT_RESET_CAP_MS = 6 * 60 * 60 * 1000    // 6 小时后重置
const HEARTBEAT_INTERVAL_MS = 30_000                   // 30 秒心跳
```

---

## 11. 成本追踪

### 11.1 定价表

| 模型 | Input / Mtok | Output / Mtok | Cache Write / Mtok | Cache Read / Mtok |
|------|:----:|:-----:|:-----:|:-----:|
| Haiku 3.5 | $0.80 | $4 | $1 | $0.08 |
| Haiku 4.5 | $1 | $5 | $1.25 | $0.10 |
| Sonnet 4 / 4.5 / 4.6 | $3 | $15 | $3.75 | $0.30 |
| Opus 4 / 4.1 | $15 | $75 | $18.75 | $1.50 |
| Opus 4.5 / 4.6 (Standard) | $5 | $25 | $6.25 | $0.50 |
| Opus 4.6 (Fast Mode) | $30 | $150 | $37.50 | $3.00 |

> 源码: `utils/modelCost.ts#L36-L126`

Web Search: $0.01/次（$10/千次）。

### 11.2 成本计算公式

```typescript
// 源码: utils/modelCost.ts#L131-L142
cost = (input_tokens / 1M) × inputRate
     + (output_tokens / 1M) × outputRate
     + (cache_read_tokens / 1M) × cacheReadRate
     + (cache_write_tokens / 1M) × cacheWriteRate
     + web_search_requests × $0.01
```

### 11.3 会话成本持久化

成本按会话 ID 存储在项目配置中，支持 `--resume` 恢复时累加：

```
project/.claude/config.json → lastSessionId, lastCost, lastAPIDuration, lastSessionMetrics
```

---

## 12. 系统提示构建

### 12.1 系统提示章节

系统提示由 8 个模块化章节动态拼装：

| 章节 | 核心内容 |
|------|----------|
| `# System` | 运行时行为：工具执行、权限模式、标签系统、上下文压缩说明 |
| `# Doing tasks` | 软件工程焦点、过度工程警告、安全编码、反向兼容规避 |
| `# Using your tools` | 工具优先级（Read>cat, Edit>sed）、并行调用、子代理指导 |
| `# Tone and style` | 无 emoji、简洁、file_path:line_number 格式 |
| `# Output efficiency` | "直奔主题，先给答案后给推理，跳过填充词" |
| `# Executing actions with care` | 可逆性/爆炸半径框架、风险操作确认 |
| `# Committing changes` | Git 安全协议：绝不 force push、绝不 amend |
| `# auto memory` | 4 种记忆类型（user/feedback/project/reference），MEMORY.md 索引 |

### 12.2 组装优先级

```
源码: utils/systemPrompt.ts#L1-L124
1. --system-prompt 覆盖          → 完全替代
2. Coordinator 系统提示           → 多代理调度模式
3. Agent 系统提示                 → --agent 指定
4. 自定义系统提示                 → 用户配置
5. 默认系统提示                   → 标准 Claude Code 指令
6. Appended 系统提示              → 追加上下文
```

### 12.3 缓存分割

系统提示被 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 标记分割为静态/动态部分。静态部分跨用户缓存，动态部分（git status、当前日期等）每 turn 更新。

### 12.4 关键安全指令

```
"Carefully consider the reversibility and blast radius of actions."

"A user approving an action (like a git push) once does NOT mean that they
approve it in all contexts"

"NEVER update the git config"
"NEVER run destructive git commands (push --force, reset --hard, checkout .,
 restore ., clean -f, branch -D) unless the user explicitly requests"
"CRITICAL: Always create NEW commits rather than amending"
```

---

## 13. 消息类型

### 13.1 消息类型层次

| 类型 | 角色 | 说明 |
|------|------|------|
| `UserMessage` | user | 用户输入（文本/附件） |
| `AssistantMessage` | assistant | 模型响应（含工具调用） |
| `SystemMessage` | — | 内部系统事件 |
| `ProgressMessage` | — | 流式工具进度 |
| `ToolUseSummaryMessage` | — | 工具执行摘要 |
| `TombstoneMessage` | — | Compact 后的占位符 |

### 13.2 系统消息子类型

| 子类型 | 用途 |
|--------|------|
| `SystemLocalCommandMessage` | Bash/Shell 输出 |
| `SystemPermissionRetryMessage` | 权限重试 |
| `SystemCompactBoundaryMessage` | 压缩边界 |
| `SystemAPIErrorMessage` | API 错误 |
| `SystemBridgeStatusMessage` | Bridge 连接状态 |
| `SystemScheduledTaskFireMessage` | Cron 任务触发 |

### 13.3 Content Block 类型

| 类型 | 说明 |
|------|------|
| `text` | 文本内容 |
| `thinking` / `redacted_thinking` | 思维过程 / 脱敏思维（内容被遮蔽） |
| `tool_use` | 客户端工具调用 |
| `server_tool_use` | 服务端工具（如 `advisor`、`web_search`） |
| `tool_result` | 工具执行结果 |
| `mcp_tool_use` / `mcp_tool_result` | MCP 工具调用与结果 |

### 13.4 消息流转

```
用户输入 → UserMessage
  ↓
序列化为 ContentBlockParam[] → API
  ↓
流式响应 → 累积为 AssistantMessage
  ↓
提取 tool_use → 权限检查 → 执行
  ↓
工具结果 → ToolResultBlockParam[] → 注入历史
  ↓
循环直到 stop_reason === 'end_turn' 或预算耗尽
  ↓
最终响应 → ToolUseSummaryMessage
```

---

## 14. 工具系统

### 14.1 工具注册表

`getAllBaseTools()` 返回所有可用工具，`getTools()` 根据上下文过滤：

```typescript
// 源码: tools.ts#L193-L200
export function getAllBaseTools(): Tools {
  return [
    AgentTool, TaskOutputTool, BashTool,
    // 当内嵌搜索工具可用时跳过 Glob/Grep
    ...(hasEmbeddedSearchTools() ? [] : [GlobTool, GrepTool]),
    FileReadTool, FileEditTool, FileWriteTool,
    NotebookEditTool, WebFetchTool, WebSearchTool,
    // ... 条件工具
  ]
}
```

### 14.2 核心工具清单

| 类别 | 工具 | 说明 |
|------|------|------|
| **文件** | FileReadTool, FileEditTool, FileWriteTool | 读/编辑/写 |
| **搜索** | GlobTool, GrepTool | 文件搜索 / 内容搜索 |
| **执行** | BashTool, PowerShellTool | Shell 命令执行 |
| **代理** | AgentTool, SendMessageTool | 子代理生成 / 消息传递 |
| **团队** | TeamCreateTool, TeamDeleteTool | 团队创建/删除 |
| **任务** | TaskCreateTool, TaskGetTool, TaskUpdateTool, TaskListTool, TaskOutputTool, TaskStopTool | 后台任务管理 |
| **Web** | WebSearchTool, WebFetchTool | Web 搜索 / 抓取 |
| **Skill** | SkillTool | 用户技能调用 |
| **编辑器** | NotebookEditTool | Jupyter 编辑 |
| **MCP** | ListMcpResourcesTool, ReadMcpResourceTool | MCP 资源 |
| **交互** | AskUserQuestionTool | 向用户提问 |
| **计划** | EnterPlanModeTool, ExitPlanModeV2Tool | 计划模式 |
| **Worktree** | EnterWorktreeTool, ExitWorktreeTool | Git Worktree |
| **调度** | CronCreateTool, CronDeleteTool, CronListTool, RemoteTriggerTool | Cron 调度 |
| **搜索** | ToolSearchTool | 延迟工具搜索 |
| **配置** | ConfigTool | 运行时配置修改 |
| **LSP** | LSPTool | Language Server Protocol |
| **内部** | BriefTool, TungstenTool, REPLTool, SleepTool | 特殊用途 |

### 14.3 条件工具加载

工具通过三种机制条件加载：

```typescript
// 1. feature() 编译时门控——未启用的工具从 bundle 中移除
const SleepTool = feature('PROACTIVE') || feature('KAIROS')
  ? require('./tools/SleepTool/SleepTool.js').SleepTool : null

// 2. USER_TYPE 运行时门控——ant vs external
const REPLTool = process.env.USER_TYPE === 'ant'
  ? require('./tools/REPLTool/REPLTool.js').REPLTool : null

// 3. isEnabled() 方法——工具自行判断是否可用
const tools = getAllBaseTools().filter(tool => tool.isEnabled())
```

### 14.4 工具执行管线

```
模型输出 tool_use block
  ↓
ToolPermissionContext.canUseTool() — 权限检查
  ├─ allow → 继续
  ├─ deny  → 返回 PermissionDenial
  └─ ask   → 弹出确认对话框
  ↓
PreToolUse Hook 触发
  ↓
工具 execute() 方法
  ↓
PostToolUse / PostToolUseFailure Hook 触发
  ↓
结果序列化为 tool_result → 注入对话历史
```

---

## 15. 权限与安全模型

### 15.1 权限模式

| 模式 | 行为 |
|------|------|
| `default` | 危险操作询问用户 |
| `acceptEdits` | 自动接受文件编辑，其余询问 |
| `bypassPermissions` | 跳过所有权限检查 |
| `plan` | 只读模式，禁止修改 |
| `dontAsk` | 不询问，直接拒绝未授权操作 |
| `auto` | AI 分类器自动判断（ant-only） |

### 15.2 权限规则来源

规则来源按优先级从低到高排列（后者覆盖前者）：

```typescript
// 源码: utils/settings/constants.ts#L7-L22 + utils/permissions/permissions.ts#L109-L114
const PERMISSION_RULE_SOURCES = [
  'userSettings',      // 1. 用户全局设置（~/.claude/settings.json）—— 最低
  'projectSettings',   // 2. 项目共享设置（.claude/settings.json）
  'localSettings',     // 3. 本地设置（.claude/config.local.json，gitignore）
  'flagSettings',      // 4. --settings CLI 标志
  'policySettings',    // 5. 企业策略（MDM 下发）
  'cliArg',            // 6. CLI 参数（--permission-mode 等）
  'command',           // 7. 斜杠命令 frontmatter
  'session',           // 8. 会话运行时 —— 最高
]
```

**判决优先级**：在同一来源内，**Deny > Ask > Allow**（deny 规则始终优先于 allow）。

> 源码: `utils/permissions/permissions.ts#L1071-L1156`

### 15.3 Bash 安全校验（23 项）

`bashSecurity.ts` 对每条 Bash 命令执行 23 项安全检查：

| ID | 检查项 | 风险 |
|:--:|--------|------|
| 1 | `INCOMPLETE_COMMANDS` | 不完整命令 |
| 2 | `JQ_SYSTEM_FUNCTION` | jq 系统函数注入 |
| 3 | `JQ_FILE_ARGUMENTS` | jq 文件参数 |
| 4 | `OBFUSCATED_FLAGS` | 混淆的命令标志 |
| 5 | `SHELL_METACHARACTERS` | Shell 元字符 |
| 6 | `DANGEROUS_VARIABLES` | 危险环境变量 |
| 7 | `NEWLINES` | 命令中的换行符 |
| 8 | `COMMAND_SUBSTITUTION` | `$()`、`${}` 等 12 种命令替换模式 |
| 9 | `INPUT_REDIRECTION` | 输入重定向 |
| 10 | `OUTPUT_REDIRECTION` | 输出重定向 |
| 11 | `IFS_INJECTION` | IFS 变量注入 |
| 12 | `GIT_COMMIT_SUBSTITUTION` | Git commit 替换 |
| 13 | `PROC_ENVIRON_ACCESS` | /proc/environ 访问 |
| 14 | `MALFORMED_TOKEN_INJECTION` | 畸形 token 注入 |
| 15 | `BACKSLASH_ESCAPED_WHITESPACE` | 反斜杠转义空白 |
| 16 | `BRACE_EXPANSION` | 花括号展开 |
| 17 | `CONTROL_CHARACTERS` | 控制字符 |
| 18 | `UNICODE_WHITESPACE` | Unicode 空白字符 |
| 19 | `MID_WORD_HASH` | 词中 # 号 |
| 20 | `ZSH_DANGEROUS_COMMANDS` | 18 个 Zsh 危险命令 |
| 21 | `BACKSLASH_ESCAPED_OPERATORS` | 反斜杠转义运算符 |
| 22 | `COMMENT_QUOTE_DESYNC` | 注释/引号不同步 |
| 23 | `QUOTED_NEWLINE` | 引号内换行 |

> 源码: `tools/BashTool/bashSecurity.ts#L77-L101`

### 15.4 Zsh 特殊防护

阻止 18 个 Zsh 特定危险命令：

```typescript
// 源码: tools/BashTool/bashSecurity.ts#L45-L74
const ZSH_DANGEROUS_COMMANDS = new Set([
  'zmodload',   // 模块加载——通往 mapfile/sysopen/ztcp 的入口
  'emulate',    // -c 标志是 eval 等价物
  'sysopen', 'sysread', 'syswrite', 'sysseek',  // zsh/system 文件操作
  'zpty',       // 伪终端命令执行
  'ztcp',       // TCP 网络连接
  'zsocket',    // Unix/TCP socket
  'mapfile',    // zsh/mapfile 关联数组（不可见文件 I/O）
  'zf_rm', 'zf_mv', 'zf_ln', 'zf_chmod', 'zf_chown', 'zf_mkdir', 'zf_rmdir', 'zf_chgrp',
  // ↑ zsh/files 内建命令——绕过 binary 检查
])
```

### 15.5 命令替换模式检测

12 种命令替换模式全部阻止（`<()` 和 `>()` 为独立检测）：

| 模式 | 说明 |
|------|------|
| `<()` / `>()` | 进程替换 |
| `=()` | Zsh 进程替换 |
| `=cmd`（词首） | Zsh EQUALS 展开（`=curl` → `/usr/bin/curl`） |
| `$()` | 命令替换 |
| `${}` | 参数替换 |
| `$[]` | 遗留算术展开 |
| `~[]` | Zsh 参数展开 |
| `(e:` | Zsh glob 限定符 |
| `(+` | Zsh glob 命令执行 |
| `} always {` | Zsh try/always 块 |
| `<#` | PowerShell 注释（纵深防御） |

> 源码: `tools/BashTool/bashSecurity.ts#L16-L41`

---

## 16. 命令系统

### 16.1 命令类型

```typescript
// 源码: types/command.ts
PromptCommand    // Skill/提示展开为对话（模型可调用）
LocalCommand     // 本地异步执行（带 loader）
LocalJSXCommand  // 终端 UI 命令（React 渲染）
```

### 16.2 命令分发

```typescript
// 源码: utils/handlePromptSubmit.ts#L120-L145
handlePromptSubmit(input)
  → 识别 /command 前缀
  → 匹配命令注册表
  → processUserInput() 执行
```

### 16.3 部分命令列表

源码中注册约 88 个斜杠命令（含 ant-only 和 feature-gated），external 构建中用户可见约 79 个：

| 命令 | 类型 | 说明 |
|------|------|------|
| `/help` | Local | 帮助信息 |
| `/clear` | Local | 清除对话 |
| `/compact` | Local | 压缩对话 |
| `/commit` | Prompt | 创建 Git commit |
| `/review` | Prompt | 代码审查 |
| `/model` | Local | 切换模型 |
| `/cost` | Local | 显示成本 |
| `/memory` | Local | 管理记忆 |
| `/config` | Local | 配置管理 |
| `/mcp` | Local | MCP 服务器管理 |
| `/resume` | Local | 恢复会话 |
| `/remote-control` | Local | 远程控制 |
| `/voice` | LocalJSX | 语音模式 |
| `/web-setup` | Local | Chrome 扩展配置 |
| `/init` | Local | 初始化 CLAUDE.md |
| `/tasks` | Local | 任务管理 |

---

## 17. Hook 事件系统

### 17.1 Hook 事件类型

24 种 Hook 事件（源码确认），用户可在 `settings.json` 中注册 Shell 命令响应：

| 事件 | 触发时机 | Matcher |
|------|----------|---------|
| `PreToolUse` | 工具执行前 | tool_name |
| `PostToolUse` | 工具执行后 | tool_name |
| `PostToolUseFailure` | 工具执行失败后 | tool_name |
| `UserPromptSubmit` | 用户提交输入 | — |
| `SessionStart` | 会话初始化 | source |
| `SubagentStart` | Agent 工具生成子代理 | — |
| `FileChanged` | 文件变更监控 | filenames |
| `PermissionRequest` | 权限对话框显示 | — |
| `Setup` | 仓库初始化/维护 | trigger (init/maintenance) |
| `Elicitation` | MCP 交互请求 | — |
| `ConfigChange` | 配置变更 | — |
| `WorktreeCreate` | Worktree 创建 | — |
| `CwdChanged` | 工作目录变更 | — |

> 源码: `utils/hooks/hooksConfigManager.ts#L26-L267`

### 17.2 Hook 响应 Schema

```typescript
// 源码: types/hooks.ts#L50-L166
syncHookResponseSchema = {
  decision?: 'approve' | 'deny' | 'block'   // 决策
  reason?: string                             // 原因
  additionalContext?: string                  // 追加上下文
  suppressOutput?: boolean                    // 抑制输出
  hookSpecificOutput?: Record<string, unknown>  // 特定输出
}
```

### 17.3 事件分发机制

```typescript
// 源码: utils/hooks/hookEvents.ts#L61-L81
registerHookEventHandler()   // 注册全局处理器（单例）
emit()                       // 发射事件（无处理器时队列化，最大 100）
shouldEmit()                 // 门控检查
emitHookStarted()            // 执行开始
emitHookProgress()           // 执行进度
emitHookResponse()           // 完成结果（success/error/cancelled）
```

---

## 18. 插件系统

Claude Code 支持插件扩展，插件可提供 hooks、commands、agents、output styles 和 MCP 集成：

### 18.1 插件作用域

| 作用域 | 位置 | 说明 |
|--------|------|------|
| `global` | 用户级（`~/.claude/plugins/`） | 所有项目生效 |
| `project` | 项目级（`.claude/plugins/`） | 仅当前仓库 |
| `flag` | 会话级（`--plugin-dir` 参数） | 仅当前会话 |

### 18.2 插件生命周期

```
settings.json → installed_plugins.json → loadPluginHooks()
  ├─ loadPluginCommands()    → 注册斜杠命令
  ├─ loadPluginAgents()      → 注册代理定义
  ├─ loadPluginHooks()       → 注册 Hook 回调
  └─ 文件监视器 → needsRefresh → /reload-plugins 或自动刷新
```

### 18.3 Marketplace

- 官方 Anthropic marketplace：默认自动更新
- 第三方 marketplace：不自动更新
- 安装状态独立追踪：`installationStatus` 含 `pending → installing → installed / failed` 状态机

> 源码: `utils/plugins/`（15+ 文件）

---

## 19. 自动更新

| 项目 | 详情 |
|------|------|
| **npm 渠道** | `@anthropic-ai/claude-code`（JavaScript 安装） |
| **原生渠道** | GCS bucket 下载编译二进制（主要用于 ant） |
| **Release 渠道** | `stable`（默认）/ `latest`（前沿） |
| **并发锁** | 5 分钟超时 + 过期锁回收（TOCTOU-safe） |
| **版本约束** | `tengu_version_config` 最低版本 / `tengu_max_version_config` 最高版本（Kill Switch） |
| **禁用方式** | `isAutoUpdaterDisabled()` 配置检查 |

> 源码: `utils/autoUpdater.ts`

---

## 20. 遥测系统

### 20.1 遥测端点

| 端点 | 用途 |
|------|------|
| `api.anthropic.com/api/claude_code/metrics` | 主遥测上报 |
| Datadog（`http-intake.logs.us5.datadoghq.com`） | APM 日志 |
| Segment（`api.segment.io`） | 用户分析 |

### 20.2 遥测初始化策略

遥测延迟到 Trust Dialog 之后初始化，避免未授权数据采集：

```
信任对话 → 远程托管设置加载 → initializeTelemetryAfterTrust()
  → OpenTelemetry SDK 懒加载（~400KB）
```

### 20.3 Feature Flag 服务（GrowthBook）

```typescript
// 源码: services/analytics/growthbook.ts
initializeGrowthBook()                    // 初始化
getFeatureValue_CACHED_MAY_BE_STALE()     // 磁盘缓存（可能过期）
getFeatureValue_CACHED_WITH_REFRESH()     // 异步刷新后使用
```

### 20.4 遥测事件规模

- **782 个唯一 `tengu_*` 事件类型**
- 主要分类：`tengu_agent_*`、`tengu_api_*`、`tengu_auto_mode_*`、`tengu_session_*`、`tengu_tool_*`

### 20.5 Machine ID 采集

| 平台 | 方式 |
|------|------|
| macOS | `IOPlatformUUID`（`ioreg -rd1 -c IOPlatformExpertDevice`） |
| Linux | `/etc/machine-id` → `/var/lib/dbus/machine-id` |
| Windows | `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` |
| FreeBSD | `/etc/hostid` → `kenv -q smbios.system.uuid` |

> MAC 地址**未被采集**。

### 20.6 tengu Feature Flags

| Flag | 用途 |
|------|------|
| `tengu_defer_all_bn4` | 延迟工具加载 |
| `tengu_defer_caveat_m9k` | 延迟工具使用警告 |
| `tengu_turtle_carbon` | Ultrathink 模式 |
| `tengu_marble_anvil` | Thinking Edits（清空思维） |
| `tengu_hawthorn_steeple` | 内容去重 |
| `tengu_hawthorn_window` | 去重窗口大小 |
| `tengu_chomp_inflection` | Prompt Suggestion |

### 20.7 隐私控制

| 变量 | 作用 |
|------|------|
| `DISABLE_TELEMETRY=true` | 完全禁用遥测 |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true` | 禁用非必要网络流量 |
| `CLAUDE_CODE_ENABLE_TELEMETRY=false` | 禁用遥测 |

### 20.8 MDM 企业管理

| 平台 | 策略路径 |
|------|----------|
| macOS | plist 托管设置（`plutil` 读取） |
| Windows | `HKLM\SOFTWARE\Policies\ClaudeCode` / `HKCU\SOFTWARE\Policies\ClaudeCode` |

### 20.9 环境变量总量

**161 个 `CLAUDE_CODE_*` 环境变量**，其中 19 个 `DISABLE_*` 开关。

### 20.10 启动性能分析

```typescript
// 源码: utils/startupProfiler.ts
profileCheckpoint('main_tsx_entry')       // 模块求值开始
profileCheckpoint('init_function_start')  // init() 开始
profileCheckpoint('init_configs_enabled') // 配置启用
profileReport()                           // 输出计时报告
```

---

## 21. 关键依赖

| 类别 | 依赖 | 用途 |
|------|------|------|
| **AI SDK** | `@anthropic-ai/sdk` | Anthropic API 客户端 |
| **UI** | `ink`, `react` | 终端 React 渲染 |
| **CLI** | `@commander-js/extra-typings` | 类型安全命令行解析 |
| **MCP** | `@modelcontextprotocol/sdk` | MCP 协议客户端 |
| **校验** | `zod` | 运行时 Schema 验证 |
| **解析** | `@babel/parser` | JS/TS AST 解析 |
| **工具** | `lodash-es` | 工具函数 |
| **样式** | `chalk`, `strip-ansi` | 终端着色 / ANSI 剥离 |
| **遥测** | `@opentelemetry/*`（懒加载） | OpenTelemetry SDK |
| **gRPC** | `@grpc/grpc-js`（懒加载） | gRPC 传输 |
| **云认证** | `@azure/identity`, `google-auth-library` | Azure / GCP 认证 |
| **YAML** | `js-yaml` | YAML 解析 |
| **序列化** | `protobuf` | Protocol Buffer |

---

## 22. 内部代号

| 代号 | 用途 |
|------|------|
| **tengu** | 遥测系统（事件前缀） |
| **kairos** | Assistant 模式（长期运行代理） |
| **grove** | 内部功能标识 |
| **penguin** | Linux 沙箱模式 |
| **chicago** | Computer Use MCP |
| **tungsten** | 内部调试工具 |
| **bagel** | UI Footer 项 |
| **companion** / **buddy** | 伴侣动画系统 |

> **免责声明**: 以上分析基于 2026 年 Q1 反编译源码，后续版本可能已变更。
