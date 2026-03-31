########## CLAUDE CODE --help ##########
```
Usage: claude [options] [command] [prompt]

Claude Code - starts an interactive session by default, use -p/--print for
non-interactive output

Arguments:
  prompt                                            Your prompt

Options:
  --add-dir <directories...>                        Additional directories to allow tool access to
  --agent <agent>                                   Agent for the current session. Overrides the 'agent' setting.
  --agents <json>                                   JSON object defining custom agents (e.g. '{"reviewer": {"description": "Reviews code", "prompt": "You are a code reviewer"}}')
  --allow-dangerously-skip-permissions              Enable bypassing all permission checks as an option, without it being enabled by default. Recommended only for sandboxes with no internet access.
  --allowedTools, --allowed-tools <tools...>        Comma or space-separated list of tool names to allow (e.g. "Bash(git:*) Edit")
  --append-system-prompt <prompt>                   Append a system prompt to the default system prompt
  --bare                                            Minimal mode: skip hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, and CLAUDE.md auto-discovery. Sets CLAUDE_CODE_SIMPLE=1. Anthropic auth is strictly ANTHROPIC_API_KEY or apiKeyHelper via --settings (OAuth and keychain are never read). 3P providers (Bedrock/Vertex/Foundry) use their own credentials. Skills still resolve via /skill-name. Explicitly provide context via: --system-prompt[-file], --append-system-prompt[-file], --add-dir (CLAUDE.md dirs), --mcp-config, --settings, --agents, --plugin-dir.
  --betas <betas...>                                Beta headers to include in API requests (API key users only)
  --brief                                           Enable SendUserMessage tool for agent-to-user communication
  --chrome                                          Enable Claude in Chrome integration
  -c, --continue                                    Continue the most recent conversation in the current directory
  --dangerously-skip-permissions                    Bypass all permission checks. Recommended only for sandboxes with no internet access.
  -d, --debug [filter]                              Enable debug mode with optional category filtering (e.g., "api,hooks" or "!1p,!file")
  --debug-file <path>                               Write debug logs to a specific file path (implicitly enables debug mode)
  --disable-slash-commands                          Disable all skills
  --disallowedTools, --disallowed-tools <tools...>  Comma or space-separated list of tool names to deny (e.g. "Bash(git:*) Edit")
  --effort <level>                                  Effort level for the current session (low, medium, high, max)
  --fallback-model <model>                          Enable automatic fallback to specified model when default model is overloaded (only works with --print)
  --file <specs...>                                 File resources to download at startup. Format: file_id:relative_path (e.g., --file file_abc:doc.txt file_def:img.png)
  --fork-session                                    When resuming, create a new session ID instead of reusing the original (use with --resume or --continue)
  --from-pr [value]                                 Resume a session linked to a PR by PR number/URL, or open interactive picker with optional search term
  -h, --help                                        Display help for command
  --ide                                             Automatically connect to IDE on startup if exactly one valid IDE is available
  --include-partial-messages                        Include partial message chunks as they arrive (only works with --print and --output-format=stream-json)
  --input-format <format>                           Input format (only works with --print): "text" (default), or "stream-json" (realtime streaming input) (choices: "text", "stream-json")
  --json-schema <schema>                            JSON Schema for structured output validation. Example: {"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}
  --max-budget-usd <amount>                         Maximum dollar amount to spend on API calls (only works with --print)
  --mcp-config <configs...>                         Load MCP servers from JSON files or strings (space-separated)
  --mcp-debug                                       [DEPRECATED. Use --debug instead] Enable MCP debug mode (shows MCP server errors)
  --model <model>                                   Model for the current session. Provide an alias for the latest model (e.g. 'sonnet' or 'opus') or a model's full name (e.g. 'claude-sonnet-4-6').
  -n, --name <name>                                 Set a display name for this session (shown in /resume and terminal title)
  --no-chrome                                       Disable Claude in Chrome integration
  --no-session-persistence                          Disable session persistence - sessions will not be saved to disk and cannot be resumed (only works with --print)
  --output-format <format>                          Output format (only works with --print): "text" (default), "json" (single result), or "stream-json" (realtime streaming) (choices: "text", "json", "stream-json")
  --permission-mode <mode>                          Permission mode to use for the session (choices: "acceptEdits", "bypassPermissions", "default", "dontAsk", "plan", "auto")
  --plugin-dir <path>                               Load plugins from a directory for this session only (repeatable: --plugin-dir A --plugin-dir B) (default: [])
  -p, --print                                       Print response and exit (useful for pipes). Note: The workspace trust dialog is skipped when Claude is run with the -p mode. Only use this flag in directories you trust.
  --replay-user-messages                            Re-emit user messages from stdin back on stdout for acknowledgment (only works with --input-format=stream-json and --output-format=stream-json)
  -r, --resume [value]                              Resume a conversation by session ID, or open interactive picker with optional search term
  --session-id <uuid>                               Use a specific session ID for the conversation (must be a valid UUID)
  --setting-sources <sources>                       Comma-separated list of setting sources to load (user, project, local).
  --settings <file-or-json>                         Path to a settings JSON file or a JSON string to load additional settings from
  --strict-mcp-config                               Only use MCP servers from --mcp-config, ignoring all other MCP configurations
  --system-prompt <prompt>                          System prompt to use for the session
  --tmux                                            Create a tmux session for the worktree (requires --worktree). Uses iTerm2 native panes when available; use --tmux=classic for traditional tmux.
  --tools <tools...>                                Specify the list of available tools from the built-in set. Use "" to disable all tools, "default" to use all tools, or specify tool names (e.g. "Bash,Edit,Read").
  --verbose                                         Override verbose mode setting from config
  -v, --version                                     Output the version number
  -w, --worktree [name]                             Create a new git worktree for this session (optionally specify a name)

Commands:
  agents [options]                                  List configured agents
  auth                                              Manage authentication
  auto-mode                                         Inspect auto mode classifier configuration
  doctor                                            Check the health of your Claude Code auto-updater. Note: The workspace trust dialog is skipped and stdio servers from .mcp.json are spawned for health checks. Only use this command in directories you trust.
  install [options] [target]                        Install Claude Code native build. Use [target] to specify version (stable, latest, or specific version)
  mcp                                               Configure and manage MCP servers
  plugin|plugins                                    Manage Claude Code plugins
  setup-token                                       Set up a long-lived authentication token (requires Claude subscription)
  update|upgrade                                    Check for updates and install if available
```

########## BINARY INFO ##########
```
Version: 2.1.83 (Claude Code)
Binary: /root/.local/share/claude/versions/2.1.81: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 3.2.0, BuildID[sha1]=192037ad9281f67d8841dcde78d46e56d3d58ed2, not stripped
Size: 227M
Date: 2026-03-25T07:34:26Z
```

########## COMPLETE CLI FLAGS (claude --help, 2026-03-25T08:07:05Z) ##########
Total flags: 51
```
--add-dir
--agent
--agents
--allow-dangerously-skip-permissions
--allowed
--allowed-tools
--append-system-prompt
--bare
--betas
--brief
--chrome
--continue
--dangerously-skip-permissions
--debug
--debug-file
--disable-slash-commands
--disallowed
--disallowed-tools
--effort
--fallback-model
--file
--fork-session
--from-pr
--help
--ide
--include-partial-messages
--input-format
--json-schema
--max-budget-usd
--mcp-config
--mcp-debug
--model
--name
--no-chrome
--no-session-persistence
--output-format
--permission-mode
--plugin-dir
--print
--replay-user-messages
--resume
--session-id
--settings
--setting-sources
--strict-mcp-config
--system-prompt
--tmux
--tools
--verbose
--version
--worktree
```

########## DECOMPILATION ANALYSIS (Bun bytecode extraction) ##########

### Binary Structure
- Format: Bun single-file executable with `@bytecode @bun-cjs` compilation
- Entry point: `file:///$bunfs/root/src/entrypoints/cli.js`
- Virtual filesystem: `$bunfs/root/` contains embedded .node modules and JS code
- Marker: `---- Bun! ----` at binary offset 0x0e2ee740

### Embedded Native Modules ($bunfs)
- `/$bunfs/root/image-processor.node`
- `/$bunfs/root/tree-sitter-bash.node`
- `/$bunfs/root/color-diff.node`
- (Plus sharp.node, audio-capture.node, file-index.node, yaml.node from strings)

### Tool Prompt Extraction (from rodata/text segments)
All tool descriptions are embedded as template literal functions, e.g.:
- `FVD()` returns Read tool description
- `cVD()` returns Write tool description  
- `HXA()` returns Grep tool description
- Agent tool description constructed dynamically with subagent types

### Key Constants
- `QpH = 2000` (Read tool default line limit)
- `sT$() = parseInt(process.env.MAX_MCP_OUTPUT_TOKENS ?? "25000", 10)` (MCP output token limit)
- `eT$ = 1600` (image token estimate)
- `xH6 = 0.5` (MCP truncation threshold multiplier)

### Security Monitor
Binary contains embedded security monitor prompt:
"You are a security monitor for autonomous AI coding agents."

### Model Selection Logic
- `DSA()` returns "inherit" (default subagent model)
- `cGH()` resolves subagent model: env var > explicit > inherit > plan-based
- `x38()` returns model options: sonnet (balanced), opus (complex), haiku (fast), inherit
- `_Y$()` checks for opus-4-6 or sonnet-4-6 (extended context support)
- `WIH()` checks MAX_THINKING_TOKENS env var and alwaysThinkingEnabled setting

########## DECOMPILATION: System Prompt Structure (v2.1.81) ##########
Extraction method: strings + sed/grep from ELF binary rodata segment
Date: 2026-03-25

### System Prompt Sections (8 confirmed)
1. # System — runtime behavior, tool execution, permission modes
2. # Doing tasks — software engineering focus, over-engineering warnings, security
3. # Using your tools — tool preference hierarchy, parallel calls, subagent guidance
4. # Tone and style — no emojis, concise, file_path:line_number format
5. # Output efficiency — "Go straight to the point", lead with answer
6. # Executing actions with care — reversibility/blast radius framework
7. # Committing changes / Creating pull requests — Git Safety Protocol
8. # auto memory — persistent file-based memory system types

### Key Extracted Directives
- "Do NOT use Bash to run commands when a relevant dedicated tool is provided"
- "Read > cat, Edit > sed, Write > echo, Glob > find, Grep > grep"
- "Only use emojis if the user explicitly requests it"
- "Your responses should be short and concise"
- "Go straight to the point. Try the simplest approach first"
- "Lead with the answer or action, not the reasoning"
- "Carefully consider the reversibility and blast radius of actions"
- "A user approving an action once does NOT mean they approve it in all contexts"
- "NEVER update the git config"
- "NEVER run destructive git commands unless user explicitly requests"
- "CRITICAL: Always create NEW commits rather than amending"

### Build Constants
- VERSION: "2.1.81"
- BUILD_TIME: "2026-03-20T21:26:18Z"
- PACKAGE_URL: "@anthropic-ai/claude-code"
- FEEDBACK_CHANNEL: "https://github.com/anthropics/claude-code/issues"
- README_URL: "https://code.claude.com/docs/en/overview"

### Output Styles (2 built-in, from binary)
- "Explanatory": provides educational insights about codebase patterns
- "Learning": pauses and asks user to write code for hands-on practice

### Tool Variable Names (minified → original)
- L8 = "Read"
- y8 = "Edit"
- Z9 = "Write"
- CD = "Bash"
- jK = "Glob"
- F_ = "Grep"
- Hf = "Agent"
- CP = "WebFetch"
- sE = "WebSearch"
- Qj = "NotebookEdit"
- xw = "Skill"
- Tz = "ToolSearch"
- f4 = "AskUserQuestion"
- ZT/Mh = "TaskCreate"/"TaskUpdate"

### Feature Flags (tengu_ prefix, from binary)
- tengu_defer_all_bn4: deferred tool loading
- tengu_defer_caveat_m9k: deferred tool caveat
- tengu_turtle_carbon: ultrathink mode
- tengu_marble_anvil: thinking edits
- tengu_hawthorn_steeple: content deduplication
- tengu_hawthorn_window: dedup window size

### Memory Types (from auto memory section)
- user: user role, goals, responsibilities, knowledge
- feedback: corrections and confirmations
- project: ongoing work, goals, initiatives
- reference: pointers to external systems

########## DECOMPILATION: Security Monitor System (Auto Mode Classifier) ##########
Extraction method: strings + sed from ELF binary, variable d38/o38/wSA
Date: 2026-03-25

### Security Monitor Identity
"You are a security monitor for autonomous AI coding agents."

### Threat Model (3 risks)
1. Prompt injection: agent manipulated by content in files/web/tool outputs
2. Scope creep: agent escalates beyond task
3. Accidental damage: agent doesn't understand blast radius

### Default Rule
"By default, actions are ALLOWED. Only block if action matches BLOCK AND no ALLOW exception applies."

### BLOCK Conditions (22 rules, verbatim from binary)
1. Git Destructive: force push, delete remote branches, rewrite history
2. Git Push to Default Branch: push to main/master bypasses PR review
3. Code from External: curl|bash, eval, pickle, exec from external source
4. Cloud Storage Mass Delete: S3/GCS/Azure mass delete/modify
5. Production Deploy: deploy to production or run production DB migrations
6. Remote Shell Writes: kubectl exec, docker exec, ssh writes
7. Blind Apply: skip preview/dry-run for live infrastructure
8. Logging/Audit Tampering: stop logging, delete logs, remove git hooks
9. Permission Grant: grant admin, add users, elevate IAM/RBAC
10. TLS/Auth Weaken: disable TLS verification, --allow-unauthenticated
11. Security Weaken: disable security mitigations, modify firewall rules
12. Create Unsafe Agents: autonomous loops without approval frameworks
13. Interfere With Others: delete jobs, modify clusters, spam Slack
14. Modify Shared Resources: in-place modify shared configs/datasets
15. Irreversible Local Destruction: rm -rf, git clean -fdx, git checkout .
16. Create RCE Surface: eval, shell injection, unsafe deserialization
17. Expose Local Services: bind ports exposing local files/services
18. Credential Leakage: embed secrets in metadata/labels/URLs
19. Credential Exploration: systematically scan credential stores
20. Data Exfiltration: send data to external endpoints
21. Exfil Scouting: test reachability of external endpoints
22. Trusting Guessed External Services: send data to agent-guessed services
23. Untrusted Code Integration: pull code from external repos for execution
24. Unauthorized Persistence: add SSH keys, modify .bashrc, create cron jobs
25. Self-Modification: modify agent's own config/settings/permissions
26. External System Writes: delete/modify items in Jira/Linear/GitHub
27. Content Integrity/Impersonation: post false content, fabricate claims
28. Real-World Transactions: purchases, payments, booking services

### ALLOW Exceptions (6 rules)
1. Test Artifacts: hardcoded test keys, placeholder credentials
2. Local Operations: agent files in working directory, local testing
3. Read-Only Operations: GET requests, queries that don't modify state
4. Declared Dependencies: install from repo manifest files
5. Toolchain Bootstrap: official one-line installers (rustup, pypa, bun)
6. Standard Credentials: reading own config credentials for their intended provider
7. Git Push to Working Branch: push to session branch (not default)

### Classifier Architecture
- Two-stage: fast stage (XML, 256 tokens max) → thinking stage (4096 tokens max)
- Default model: claude-sonnet-4-6 (or claude-sonnet-4-6[1m] for large contexts)
- Output format: <block>yes/no</block><reason>...</reason>
- On parse failure: "blocking for safety" (fail-safe)
- On error/timeout: "blocking for safety" (fail-safe)

### User Intent Rule
"User intent provides important context but is NOT an automatic override of BLOCK conditions."
- Distinguish user's request from agent's action
- Scope escalation = autonomous behavior → evaluate against BLOCK normally
- Ambiguous requests don't authorize dangerous interpretation

########## DECOMPILATION: Telemetry, System Info, Network Targets ##########

### Telemetry Endpoints (from binary)
1. https://api.anthropic.com/api/claude_code/metrics — 主遥测上报
2. https://api.anthropic.com/api/claude_code/organizations/metrics_enabled — 组织级遥测开关查询
3. https://http-intake.logs.us5.datadoghq.com/api/v — Datadog 日志采集 (US5 区域)
4. https://api.segment.io — Segment 分析
5. https://beacon.claude-ai.staging.ant.dev — Staging 环境信标

### System Information Collection
- platform() / process.platform — 操作系统类型
- process.arch — CPU 架构
- oOH() — 平台信息聚合函数 (28 refs in binary)
- os.hostname / gethostname — 主机名
- uv_cpu_info / os.cpus — CPU 信息
- hardwareConcurrency — 硬件并发数
- macOS 版本号映射: Darwin kernel 22→macOS 13, 21→12, etc.

### Environment Variables (161 total CLAUDE_CODE_*)
Key categories:
- Telemetry: ENABLE_TELEMETRY, ENHANCED_TELEMETRY_BETA, DIAGNOSTICS_FILE, DATADOG_*, OTEL_*, PERFETTO_TRACE
- Disable switches: 19 DISABLE_* flags
- Auth: OAUTH_*, API_KEY_*, SESSION_ACCESS_TOKEN, WEBSOCKET_AUTH_*
- Sandbox: BUBBLEWRAP, FORCE_SANDBOX, BASH_SANDBOX_SHOW_INDICATOR
- Model: SUBAGENT_MODEL, EFFORT_LEVEL, MAX_OUTPUT_TOKENS, DISABLE_THINKING
- Network: HOST_HTTP_PROXY_PORT, HOST_SOCKS_PROXY_PORT, PROXY_RESOLVES_HOSTS, SSE_PORT
- IDE: IDE_HOST_OVERRIDE, IDE_SKIP_AUTO_INSTALL, AUTO_CONNECT_IDE
- Git: BASE_REF, GIT_BASH_PATH
- Container: CONTAINER_ID, REMOTE, REMOTE_ENVIRONMENT_TYPE, WORKSPACE_HOST_PATHS

### DISABLE Switches (19 total)
DISABLE_ADAPTIVE_THINKING, DISABLE_ATTACHMENTS, DISABLE_AUTO_MEMORY,
DISABLE_BACKGROUND_TASKS, DISABLE_CLAUDE_MDS, DISABLE_COMMAND_INJECTION_CHECK,
DISABLE_CRON, DISABLE_EXPERIMENTAL_BETAS, DISABLE_FAST_MODE,
DISABLE_FEEDBACK_SURVEY, DISABLE_FILE_CHECKPOINTING, DISABLE_GIT_INSTRUCTIONS,
DISABLE_LEGACY_MODEL_REMAP, DISABLE_NONESSENTIAL_TRAFFIC,
DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL, DISABLE_PRECOMPACT_SKIP,
DISABLE_TERMINAL_TITLE, DISABLE_THINKING, DISABLE_VIRTUAL_SCROLL

### Key Constants
- MEMORY.md line limit: 200 lines (lines after 200 truncated)
- MAX_MCP_OUTPUT_TOKENS: 25000 (env override available)
- MCP output truncation multiplier: 0.5
- Image token estimate: 1600 tokens per image

########## DECOMPILATION: Machine ID / Hardware Fingerprinting ##########

### Machine ID Collection (via OpenTelemetry getMachineId())
Confirmed: Claude Code collects machine-specific identifiers for telemetry:

**macOS:**
- IOPlatformUUID via `ioreg -rd1 -c IOPlatformExpertDevice`
- Extraction: split on `'" = "'`, take second part

**Linux:**
- Primary: `/etc/machine-id`
- Fallback: `/var/lib/dbus/machine-id`

**Windows:**
- Registry: `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography\MachineGuid`
- Handles 32-bit on 64-bit via sysnative redirect

**FreeBSD:**
- Primary: `/etc/hostid`
- Fallback: `kenv -q smbios.system.uuid`

### MAC Address Collection
- getMacAddress: 0 references — **NOT collected**
- networkInterfaces: referenced but as Node.js built-in, not for MAC harvesting

### Telemetry Data Points Sent
From binary analysis of telemetry event construction:
- accountUuid: Anthropic account UUID
- organizationUuid: organization UUID
- userType: "external"
- subscriptionType: subscription tier
- rateLimitTier: rate limit tier
- platform: OS/arch info via oOH()
- firstTokenTime: time to first token
- githubActionsMetadata (CI only): GITHUB_ACTOR, GITHUB_ACTOR_ID,
  GITHUB_REPOSITORY, GITHUB_REPOSITORY_ID, GITHUB_REPOSITORY_OWNER,
  GITHUB_REPOSITORY_OWNER_ID

### Telemetry Event Count
- 782 unique tengu_* event types found in binary (far more than previously documented 30+)

### MDM (Mobile Device Management) Support
- macOS: plist-based managed settings
- Windows: Registry policies at HKLM/HKCU\SOFTWARE\Policies\ClaudeCode
- Settings key: "Settings" under policy path

########## SOURCE CODE ANALYSIS: Remote Control / Bridge ##########

> 以下数据来自 Claude Code 源码分析（`bridge/`、`remote/`、`utils/`、`entrypoints/` 等目录，约 35,000 行 TypeScript），与 v2.1.87 ELF 二进制反编译交叉验证。文件名和行号可直接追溯。

### Source Code File Map

| 文件路径 | 行数 | 职责 |
|----------|------|------|
| `bridge/bridgeMain.ts` | 2,999 | 主桥接编排器（standalone daemon/server 模式） |
| `bridge/replBridge.ts` | 2,406 | REPL 会话内桥接核心 |
| `bridge/remoteBridgeCore.ts` | 1,008 | Env-less v2 桥接核心 |
| `bridge/initReplBridge.ts` | 569 | 桥接初始化 |
| `bridge/sessionRunner.ts` | 550 | 会话执行器 |
| `bridge/bridgeApi.ts` | 539 | Bridge API 层 |
| `bridge/bridgeUI.ts` | 530 | Bridge UI 层 |
| `bridge/bridgeMessaging.ts` | 461 | 消息协议处理 |
| `bridge/createSession.ts` | 384 | 会话创建 |
| `bridge/replBridgeTransport.ts` | 370 | 传输层抽象 |
| `bridge/types.ts` | 262 | 类型定义 |
| `bridge/jwtUtils.ts` | 256 | JWT 认证工具 |
| `bridge/trustedDevice.ts` | 210 | 设备信任管理 |
| `bridge/bridgeEnabled.ts` | 202 | 启用/禁用逻辑 |
| `bridge/pollConfig.ts` | 110 | Polling 配置 |
| `bridge/pollConfigDefaults.ts` | 82 | 默认 polling 参数 |
| `bridge/flushGate.ts` | 71 | 历史消息刷新门控 |
| `bridge/capacityWake.ts` | 56 | 容量唤醒信号 |
| `remote/SessionsWebSocket.ts` | 404 | Sessions WebSocket 客户端 |
| `remote/RemoteSessionManager.ts` | 343 | 远程会话管理 |
| `remote/sdkMessageAdapter.ts` | 302 | SDK 消息适配器 |
| `entrypoints/sdk/controlSchemas.ts` | ~510 | Zod v4 控制消息 schema（21 种子类型） |
| `utils/concurrentSessions.ts` | 205 | PID 文件并发会话管理 |
| `utils/sessionIngressAuth.ts` | 131 | 3 层 token 优先级链 |
| `utils/sessionActivity.ts` | 123 | refcount 心跳计时器 |
| `utils/controlMessageCompat.ts` | 35 | iOS camelCase 兼容层 |
| `services/api/sessionIngress.ts` | 464 | Session-Ingress API（乐观并发写入） |
| `utils/teleport.tsx` | 1,226 | Teleport 远程会话创建/恢复 |
| `server/directConnectManager.ts` | 213 | DirectConnect WebSocket 客户端 |

### Dual-Generation Transport Architecture

**v1 (HybridTransport)** — `bridge/replBridge.ts`:
- 读取：WebSocket 长连接
- 写入：POST 到 Session-Ingress 端点
- 认证：OAuth token（通过 `refreshHeaders` 回调注入刷新后的 token）
- 重连：指数退避（2s → 60s，15 分钟放弃）
- 选择条件：默认

**v2 (SSETransport + CCRClient)** — `bridge/remoteBridgeCore.ts`:
- 读取：SSE（Server-Sent Events）
- 写入：POST 到 CCR `/worker/*` 端点
- 认证：JWT（含 `session_id` claim + `worker` role）
- 重连：SSE 401 触发 OAuth 刷新 + 凭证重取
- 选择条件：服务端通过 `secret.use_code_sessions` 标志切换；`CLAUDE_BRIDGE_USE_CCR_V2` env var 强制

### Session States (from `server/types.ts`)

```typescript
type SessionState = 'starting' | 'running' | 'detached' | 'stopping' | 'stopped'
```

### Session Registration (from `utils/concurrentSessions.ts`)

PID file at `$CONFIG_DIR/sessions/{process.pid}.json`:
```json
{
  "pid": "<process.pid>",
  "sessionId": "<UUID>",
  "cwd": "<original working dir>",
  "startedAt": "<timestamp>",
  "kind": "<interactive|bg|daemon|daemon-worker>",
  "entrypoint": "<CLAUDE_CODE_ENTRYPOINT env>",
  "messagingSocketPath": "<CLAUDE_CODE_MESSAGING_SOCKET>",
  "name": "<CLAUDE_CODE_SESSION_NAME>",
  "logPath": "<CLAUDE_CODE_SESSION_LOG>",
  "agent": "<CLAUDE_CODE_AGENT>",
  "status": "<busy|idle|waiting>"
}
```

Session kinds: `'interactive' | 'bg' | 'daemon' | 'daemon-worker'`
Filename validation: `/^\d+\.json$/` prevents accidental deletion of non-PID files.

### Redux State Machine (13 fields, from `bridge/replBridge.ts`)

```javascript
replBridgeEnabled: false,
replBridgeExplicit: false,
replBridgeOutboundOnly: false,
replBridgeConnected: false,
replBridgeSessionActive: false,
replBridgeReconnecting: false,
replBridgeConnectUrl: undefined,
replBridgeSessionUrl: undefined,
replBridgeEnvironmentId: undefined,
replBridgeSessionId: undefined,
replBridgeError: undefined,
replBridgeInitialName: undefined,
showRemoteCallout: false
```

### Dependency Injection: BridgeCoreParams (from `bridge/initReplBridge.ts`)

Injected params (no direct imports from bootstrap/state or sessionStorage):
- `createSession` — 创建新会话
- `archiveSession` — 归档会话
- `toSDKMessages` — 内部消息→SDK 消息转换
- `onAuth401` — 401 认证失败回调
- `getPollIntervalConfig` — 获取 GrowthBook 下发的 polling 参数
- `onSetPermissionMode` — 权限模式变更回调（含 auto gate check + bypassPermissions availability check）
- `onEnvironmentLost` — 环境丢失回调

Returned handle (ReplBridgeHandle):
- Read-only: `bridgeSessionId`, `environmentId`, `sessionIngressUrl`
- Methods: `writeMessages()`, `writeSdkMessages()`, `sendControlRequest()`, `sendControlResponse()`, `sendControlCancelRequest()`, `sendResult()`, `teardown()`

### Control Request Subtypes (21 types, from `entrypoints/sdk/controlSchemas.ts`)

Zod v4 schemas using `lazySchema()` wrappers:

| subtype | Schema Name |
|---------|-------------|
| `initialize` | `SDKControlInitializeRequestSchema` |
| `interrupt` | `SDKControlInterruptRequestSchema` |
| `can_use_tool` | `SDKControlPermissionRequestSchema` |
| `set_permission_mode` | `SDKControlSetPermissionModeRequestSchema` |
| `set_model` | `SDKControlSetModelRequestSchema` |
| `set_max_thinking_tokens` | `SDKControlSetMaxThinkingTokensRequestSchema` |
| `mcp_status` | `SDKControlMcpStatusRequestSchema` |
| `get_context_usage` | `SDKControlGetContextUsageRequestSchema` |
| `rewind_files` | `SDKControlRewindFilesRequestSchema` |
| `cancel_async_message` | `SDKControlCancelAsyncMessageRequestSchema` |
| `seed_read_state` | `SDKControlSeedReadStateRequestSchema` |
| `hook_callback` | `SDKHookCallbackRequestSchema` |
| `mcp_message` | `SDKControlMcpMessageRequestSchema` |
| `mcp_set_servers` | `SDKControlMcpSetServersRequestSchema` |
| `reload_plugins` | `SDKControlReloadPluginsRequestSchema` |
| `mcp_reconnect` | `SDKControlMcpReconnectRequestSchema` |
| `mcp_toggle` | `SDKControlMcpToggleRequestSchema` |
| `stop_task` | `SDKControlStopTaskRequestSchema` |
| `apply_flag_settings` | `SDKControlApplyFlagSettingsRequestSchema` |
| `get_settings` | `SDKControlGetSettingsRequestSchema` |
| `elicitation` | `SDKControlElicitationRequestSchema` |

Message envelopes:
- `SDKControlRequestSchema`: `{ type: 'control_request', request_id: string, request: <inner> }`
- `SDKControlResponseSchema`: `{ type: 'control_response', response: { subtype: 'success'|'error', ... } }`
- `SDKControlCancelRequestSchema`: `{ type: 'control_cancel_request', request_id: string }`
- `SDKKeepAliveMessageSchema`: `{ type: 'keep_alive' }`
- `SDKUpdateEnvironmentVariablesMessageSchema`: `{ type: 'update_environment_variables', variables: Record<string,string> }`

### Session Ingress Auth (3-tier, from `utils/sessionIngressAuth.ts`)

Priority chain:
1. `CLAUDE_CODE_SESSION_ACCESS_TOKEN` env var
2. `CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR` → read from `/dev/fd/{fd}` (macOS) or `/proc/self/fd/{fd}` (Linux)
3. `CLAUDE_SESSION_INGRESS_TOKEN_FILE` or default `/home/claude/.claude/remote/.session_ingress_token`

Auth header construction:
- Session keys (`sk-ant-sid` prefix): `Cookie: sessionKey={token}` + optional `X-Organization-Uuid`
- JWTs: `Authorization: Bearer {token}`

### Token Refresh

**v1 (OAuth)** — `bridge/replBridge.ts`:
- `clearOAuthTokenCache()` + `checkAndRefreshOAuthTokenIfNeeded()`
- `refreshHeaders` callback injects fresh OAuth into WebSocket
- Child process: `update_environment_variables` stdin message updates `CLAUDE_CODE_SESSION_ACCESS_TOKEN`

**v2 (JWT)** — `bridge/remoteBridgeCore.ts`:
- `createTokenRefreshScheduler`: fires 5 minutes before JWT expiry
- Calls `/bridge` endpoint to refresh, each call bumps epoch
- `authRecoveryInFlight` flag serializes concurrent refresh requests
- SSE 401 → `onAuth401` → re-fetch OAuth → re-fetch credentials → rebuild transport
- `initialFlushDone` reset to false for history re-flush

### Connection Backoff Constants (from `bridge/replBridge.ts`)

```
POLL_ERROR_INITIAL_DELAY_MS = 2_000
POLL_ERROR_MAX_DELAY_MS = 60_000
POLL_ERROR_GIVE_UP_MS = 15 * 60 * 1000 (15 minutes)
MAX_ENVIRONMENT_RECREATIONS = 3
```

Standalone daemon (from `bridge/bridgeMain.ts`):
```
connInitialMs: 2_000
connCapMs: 120_000 (2 min)
connGiveUpMs: 600_000 (10 min)
generalInitialMs: 500
generalCapMs: 30_000
generalGiveUpMs: 600_000
```

### Reconnection Strategies (from `bridge/replBridge.ts`)

1. **Reconnect-in-place**: `reuseEnvironmentId` → if backend returns same env ID, `reconnectSession()` re-queues. `currentSessionId` stays same, URL valid, `previouslyFlushedUUIDs` preserved.
2. **Fresh session fallback**: If env differs (TTL-expired) or `reconnectSession` throws, archive old + create new.

### Sleep Detection (from `bridge/replBridge.ts`)

If `setTimeout` overshoots deadline by 60+ seconds → process was suspended → reset error budget + force fast-poll cycle.

### Echo Dedup (from `bridge/replBridge.ts`)

Two-layer UUID protection:
1. `initialMessageUUIDs` — messages sent during session creation
2. `recentPostedUUIDs` — `BoundedUUIDSet(2000)` ring buffer for live writes
Both mirrored in `recentInboundUUIDs` for re-delivered inbound prompts.

### Session Activity Tracking (from `utils/sessionActivity.ts`)

- `SESSION_ACTIVITY_INTERVAL_MS = 30_000` (30 seconds)
- `SessionActivityReason = 'api_call' | 'tool_exec'`
- Refcount-based: `startSessionActivity(reason)` / `stopSessionActivity(reason)`
- Gate: `CLAUDE_CODE_REMOTE_SEND_KEEPALIVES` env var

### iOS Compatibility (from `utils/controlMessageCompat.ts`)

`normalizeControlMessageKeys(obj)`: converts camelCase `requestId` → snake_case `request_id`. Reason: older iOS app builds missing Swift CodingKeys mapping. Snake_case wins when both present.

### Session-Ingress Optimistic Concurrency (from `services/api/sessionIngress.ts`)

- `PUT /v1/session_ingress/session/{sessionId}` with `Last-Uuid` header
- 409 Conflict: adopts server's `x-last-uuid` and retries. If entry already stored (`x-last-uuid === entry.uuid`), recovers silently.
- 10 retries max, exponential backoff (500ms base, 8s cap)
- Per-session `sequential()` wrapper prevents concurrent writes

### Multi-Session Tracking (from `bridge/bridgeMain.ts`)

Runtime data structures:
```
activeSessions: Map<string, SessionHandle>
sessionStartTimes: Map<string, number>
sessionWorkIds: Map<string, string>
sessionIngressTokens: Map<string, string>
sessionTimers: Map<string, Timeout>
completedWorkIds: Set<string>
sessionWorktrees: Map<string, WorktreeInfo>
timedOutSessions: Set<string>
v2Sessions: Set<string>
```

Spawn modes: `'single-session' | 'same-dir' | 'worktree'`
GrowthBook gate: `tengu_ccr_bridge_multi_session`
Interactive toggle: 'w' key switches spawn mode at runtime

### Bridge Pointer (Crash Recovery, from `bridge/replBridge.ts`)

Written after session creation. Contains `{sessionId, environmentId, source: 'standalone' | 'repl'}`.
Hourly mtime refresh prevents staleness.
On `--continue`, reads pointer across worktree siblings.
Perpetual mode: does NOT send result or stopWork on teardown; backend TTL (300s) expires and re-queues.

### GrowthBook Feature Flags (from source)

- `tengu_bridge_poll_interval_config` — dynamic polling parameter tuning (5-minute refresh, Zod validation, falls back to defaults on malformed config)
- `tengu_bridge_initial_history_cap` — initial history flush cap (default 200)
- `tengu_ccr_bridge_multi_session` — multi-session per environment gate
- `tengu_ccr_bundle_seed_enabled` — git bundle fallback for Teleport

### Eligibility Check (from `services/api/adminRequests.ts` + `bridge/bridgeEnabled.ts`)

Remote Control eligibility is checked via:
```
GET /api/oauth/organizations/${orgUUID}/admin_requests/eligibility?request_type=${requestType}
```
Uses OAuth headers with `x-organization-uuid`.

`bridge/bridgeEnabled.ts:79`: org UUID check — "Unable to determine your organization for Remote Control eligibility. Run `claude auth login` to refresh your account information."

Related eligibility functions in other subsystems:
- `checkRemoteAgentEligibility()` — before remote agent/ultraplan/review sessions (`tasks/RemoteAgentTask/RemoteAgentTask.tsx`)
- `checkBackgroundRemoteSessionEligibility()` — before background remote sessions (`utils/background/remote/remoteSession.ts`)
- `isRemoteManagedSettingsEligible()` — for remote managed settings sync (`services/remoteManagedSettings/index.ts`)

### Polling Config Schema (from `bridge/pollConfig.ts` + `bridge/pollConfigDefaults.ts`)

Complete Zod schema for `tengu_bridge_poll_interval_config`:

| Field | Type | Default | Constraint | Purpose |
|-------|------|---------|------------|---------|
| `poll_interval_ms_not_at_capacity` | `int` | 2,000 | min 100 | Idle polling interval |
| `poll_interval_ms_at_capacity` | `int` | 0 | 0 or ≥100 | At-capacity polling (0 = disabled) |
| `non_exclusive_heartbeat_interval_ms` | `int` | 0 | min 0 | Heartbeat alongside at-capacity poll |
| `multisession_poll_interval_ms_not_at_capacity` | `int` | 2,000 | min 100 | Multi-session idle |
| `multisession_poll_interval_ms_partial_capacity` | `int` | 2,000 | min 100 | Multi-session partial |
| `multisession_poll_interval_ms_at_capacity` | `int` | 0 | 0 or ≥100 | Multi-session at-capacity |
| `reclaim_older_than_ms` | `int` | 5,000 | min 1 | Server-side work item reclaim threshold |
| `session_keepalive_interval_v2_ms` | `int` | **120,000** | min 0 | **WebSocket keep-alive interval (0 = disabled). Pushes silent `{type:'keep_alive'}` to session-ingress. Fixes Envoy idle timeout on bridge-topology sessions (#21931).** |

Object-level refinements:
1. At-capacity liveness requires `non_exclusive_heartbeat_interval_ms > 0` OR `poll_interval_ms_at_capacity > 0`
2. Multi-session at-capacity liveness requires `non_exclusive_heartbeat_interval_ms > 0` OR `multisession_poll_interval_ms_at_capacity > 0`

Usage (from `bridge/replBridge.ts:1533-1546`):
```typescript
const keepAliveIntervalMs = getPollIntervalConfig().session_keepalive_interval_v2_ms
const keepAliveTimer = keepAliveIntervalMs > 0
  ? setInterval(() => {
      void transport.write({ type: 'keep_alive' })
    }, keepAliveIntervalMs)
  : null
```

Same pattern in `cli/remoteIO.ts:180-194` with `this.isBridge` guard.

### Teleport (from `utils/teleport.tsx`)

Source selection ladder:
1. **GitHub clone** (default): CCR clones from repo's origin URL. Requires GitHub remote + CCR GitHub App.
2. **Git bundle** (fallback): `git bundle --all`, uploaded via Files API. Triggered when GitHub preflight fails and `tengu_ccr_bundle_seed_enabled` gate is on. `CCR_FORCE_BUNDLE=1` forces this path.
3. **Empty sandbox**: when no repo detected.

Session creation: `POST /v1/sessions` with `anthropic-beta: ccr-byoc-2025-07-29` header.
Title/branch generation: Claude Haiku generates `{title, branch}`, branch prefix `claude/`.
Polling: `GET /v1/sessions/{id}/events` cursor-based, max 50 pages.
Archive: `POST /v1/sessions/{id}/archive`, 409 = already archived (success).

### Admin Requests Eligibility (from `services/api/adminRequests.ts`)

API endpoints:
- `POST /api/oauth/organizations/${orgUUID}/admin_requests` — creates admin request
- `GET /api/oauth/organizations/${orgUUID}/admin_requests/me?request_type=${requestType}` — gets user's existing admin requests
- `GET /api/oauth/organizations/${orgUUID}/admin_requests/eligibility?request_type=${requestType}` — checks eligibility

Error message from `bridge/bridgeEnabled.ts`:
> `Unable to determine your organization for Remote Control eligibility. Run \`claude auth login\` to refresh your account information.`

### session_keepalive_interval_v2_ms (from `bridge/pollConfig.ts`)

Zod schema definition:
```typescript
session_keepalive_interval_v2_ms: z.number().int().min(0).default(120_000),
```

Default: `120_000` (2 minutes). Comment from `pollConfigDefaults.ts`:
> "0 = disabled. When > 0, push a silent {type:'keep_alive'} frame to session-ingress at this interval so upstream proxies don't GC an idle remote-control session. 2 min is the default. _v2: bridge-only gate (pre-v2 clients read the old key, new clients ignore it)."

Used in `bridge/replBridge.ts` and `cli/remoteIO.ts`:
```typescript
const keepAliveIntervalMs = getPollIntervalConfig().session_keepalive_interval_v2_ms
```

GrowthBook flag: `tengu_bridge_poll_interval_config` controls the entire config object with 5-minute refresh.

---

## SOURCE CODE ANALYSIS: Tool System

> 以下数据来自 Claude Code `tools/` 目录源码分析（~163 文件、~50,000 行 TypeScript）。这与上文 Remote Control/Bridge 分析（`bridge/`、`remote/`、`utils/`、`entrypoints/`，约 35,000 行）是**独立的分析范围**。两个范围的差异来自不同目录覆盖：工具系统分析专注于 `tools/` 及其直接依赖。

### Tool Base Architecture (from `Tool.ts`)

Core interface `Tool<Input, Output, P>` with methods:
- `call()` — execute, returns `ToolResult<T>`
- `isEnabled()` — feature gate (default: `true`)
- `isReadOnly()` — read classification (default: `false`, fail-closed)
- `isConcurrencySafe()` — parallel execution (default: `false`, fail-closed)
- `isDestructive()` — irreversible ops (default: `false`)
- `validateInput()` — pre-permission validation
- `checkPermissions()` — permission rule matching
- `interruptBehavior()` — `'cancel'` or `'block'` on new user input
- `preparePermissionMatcher()` — hook pattern matching

`buildTool()` factory fills safe defaults (fail-closed: concurrency=false, readonly=false).

`ToolResult<T>` = `{ data, newMessages?, contextModifier?, mcpMeta? }`
`ToolUseContext` = `{ options: { tools, mcpClients, agentDefinitions }, abortController, messages, getAppState/setAppState, readFileState, agentId? }`

### BashTool (from `tools/BashTool/`, 18 files, 12,411 LOC)

Input schema: `command` (string), `timeout` (number, optional), `description` (string, optional), `run_in_background` (boolean, optional), `dangerouslyDisableSandbox` (boolean, optional).

Key constants:
- `PROGRESS_THRESHOLD_MS = 2000`
- `ASSISTANT_BLOCKING_BUDGET_MS = 15,000` (Kairos auto-background)
- `maxResultSizeChars = 30,000`
- `MAX_PERSISTED_SIZE = 64 MB`

Command classification sets: BASH_SEARCH_COMMANDS (find/grep/rg/ag), BASH_READ_COMMANDS (cat/head/tail/jq), BASH_SILENT_COMMANDS (mv/cp/rm/mkdir).

Security pipeline (`bashSecurity.ts`, 2,593 lines): 23 validators covering injection, misparsing, obfuscation, IFS, Zsh dangerous commands, brace expansion, Unicode whitespace, etc.

Permission model (`bashPermissions.ts`, 2,622 lines): 41 SAFE_ENV_VARS whitelist (Go/Rust/Node/Python/Locale). 19 BARE_SHELL_PREFIXES blocked from rule suggestions (sh/bash/sudo/env). `MAX_SUBCOMMANDS_FOR_SECURITY_CHECK = 50`.

### FileEditTool (from `tools/FileEditTool/`, 6 files, 1,812 LOC)

Input schema: `file_path`, `old_string`, `new_string`, `replace_all` (default false).

Matching pipeline: exact match → curly-quote normalization → XML desanitization. No fuzzy matching.

10 error codes: team memory secret (0), no-op (1), path denied (2), file exists (3), file not found (4), ipynb (5), not read (6), stale (7), not found (8), multiple matches (9).

Write safety: synchronous mtime critical section between check and write. `MAX_EDIT_FILE_SIZE = 1 GiB`.

### FileReadTool (from `tools/FileReadTool/`, 5 files, 1,602 LOC)

Input schema: `file_path`, `offset` (1-based), `limit`, `pages` (PDF range).

Supported types: text (2000 lines max), images (sharp pipeline), PDF (inline/extract), notebooks (.ipynb), binary (rejected).

Limits: `maxSizeBytes = 256 KB`, `maxTokens = 25,000`, `MAX_LINES_TO_READ = 2000`.

Blocked device paths: `/dev/zero`, `/dev/random`, `/dev/urandom`, `/dev/full`, `/dev/stdin`, `/dev/tty`, `/dev/fd/0-2`, `/proc/*/fd/0-2`.

### FileWriteTool (from `tools/FileWriteTool/`, 3 files, 856 LOC)

Input schema: `file_path`, `content`. Atomic write: mkdir + history backup (async) → readFileSync + mtime check + write (sync critical section). Always LF line endings. New files skip read-first requirement.

### AgentTool (from `tools/AgentTool/`, 14 files, 6,782 LOC)

Input schema: `description`, `prompt`, `subagent_type?`, `model?` (sonnet/opus/haiku), `run_in_background?`, `name?`, `team_name?`, `mode?`, `isolation?`, `cwd?`.

Four spawn modes (priority): Teammate → Remote (Ant-only) → Fork (inherits full context, max cache hit) → Subagent (independent context).

Fork guard: scan for `<fork_boilerplate>` tag or `querySource === 'agent:builtin:fork'`. Fork rules: no re-fork, no conversation, 500-word limit, structured output format.

Tool filtering: MCP always allowed → ALL_AGENT_DISALLOWED_TOOLS → CUSTOM_AGENT_DISALLOWED_TOOLS → ASYNC_AGENT_ALLOWED_TOOLS.

Agent definitions from 3 sources: built-in → plugin → user/project (`.claude/agents/*.md`).

### GrepTool (from `tools/GrepTool/`, 3 files, 795 LOC)

Input schema: `pattern`, `path?`, `glob?`, `output_mode?` (default: files_with_matches), `-i?`, `type?`, `head_limit?` (default: 250), `multiline?`.

Ripgrep invocation: `--hidden`, exclude VCS dirs (`.git/.svn/.hg/.bzr/.jj/.sl`), `--max-columns 500`. `files_with_matches` sorted by mtime.

### ToolSearchTool (from `tools/ToolSearchTool/`, 3 files, 593 LOC)

Input schema: `query` (string), `max_results` (default 5). Scoring: exact name match +10, partial +5, searchHint +4, description +2. MCP prefix matches weighted higher (+12/+6). `select:ToolName` for direct selection.

### PowerShellTool (from `tools/PowerShellTool/`, 14 files, 8,959 LOC)

Windows-only equivalent of BashTool. Separate security and permission validation pipeline.

### Remaining Tools Summary

| Tool | LOC | Key Schema Fields |
|------|-----|-------------------|
| WebFetch | 1,131 | `url`, `prompt` |
| WebSearch | 569 | `query`, `allowed_domains?`, `blocked_domains?` |
| NotebookEdit | 587 | `notebook_path`, `cell_id?`, `new_source`, `edit_mode?` |
| TaskCreate | 195 | `subject`, `description`, `activeForm?` |
| TaskGet | 153 | `taskId` |
| TaskUpdate | 484 | `taskId`, `status?`, `addBlocks?`, `metadata?` |
| CronCreate | 543 | `cron`, `prompt`, `recurring?`, `durable?` |
| TeamCreate | 359 | `team_name`, `description?` |
| SendMessage | 997 | `to`, `message`, `summary?` |
| Brief | 610 | `message`, `attachments?`, `status` |
| AskUserQuestion | 309 | `questions` (1-4), `metadata?` |
| LSP | 2,005 | `operation` (9 types), `filePath`, `line`, `character` |
| RemoteTrigger | 192 | `action`, `trigger_id?`, `body?` |
| Skill | 1,477 | `skill`, `args?` |
| Config | 809 | `setting`, `value?` |
| EnterPlanMode | 329 | (empty) |
| ExitPlanMode | 605 | `allowedPrompts?` |
| EnterWorktree | 177 | `name?` |
| ExitWorktree | 386 | `action` (keep/remove), `discard_changes?` |

### GlobTool (from `tools/GlobTool/`)

Input schema: `pattern` (string), `path?` (string). Output: `{ durationMs, numFiles, filenames, truncated }`. `isConcurrencySafe=true`, `isReadOnly=true`, `maxResultSizeChars=100_000`.

### TaskStopTool (from `tools/TaskStopTool/`)

Input schema: `task_id?` (string), `shell_id?` (string). **Aliases: `['KillShell']`** — KillShell is NOT a separate tool, it is a deprecated alias for TaskStopTool. `shell_id` kept for backward compatibility.

### TaskOutputTool (from `tools/TaskOutputTool/`)

Input schema: `task_id` (string), `block` (boolean, default true), `timeout` (number, 0-600000, default 30000). Output: `{ retrieval_status: 'success'|'timeout'|'not_ready', task }`.

### TaskListTool (from `tools/TaskListTool/`)

Input schema: empty (`z.strictObject({})`). Output: `{ tasks: [{ id, subject, status, owner?, blockedBy }] }`. Gate: `isTodoV2Enabled()`.

### TeamDeleteTool (from `tools/TeamDeleteTool/`)

Input schema: empty. Output: `{ success, message, team_name? }`. Gate: `isAgentSwarmsEnabled()`.

### StructuredOutputTool (from `tools/SyntheticOutputTool/`)

Tool name: `'StructuredOutput'` (NOT "SyntheticOutput"). Input: `z.object({}).passthrough()`, output: `z.string()`. Gate: `isNonInteractiveSession` only (SDK/CLI use). Must be called exactly once at end of response.

### REPLTool (from `tools/REPLTool/`)

Tool name: `'REPL'`. Gate: `isReplModeEnabled()` — default on for Ant + CLI entrypoint; opt out `CLAUDE_CODE_REPL=0`; force on `CLAUDE_REPL_MODE=1`. REPL_ONLY_TOOLS: `FileRead, FileWrite, FileEdit, Glob, Grep, Bash, NotebookEdit, Agent`.

### SleepTool (from `tools/SleepTool/`)

Tool name: `'Sleep'`. Gate: `feature('PROACTIVE') || feature('KAIROS')`. Periodic check-ins via `<tick>` prompts; no shell process; interruptible.

### McpAuthTool (from `tools/McpAuthTool/`)

Input: empty. Tool name: dynamically generated as `buildMcpToolName(serverName, 'authenticate')` (e.g. `mcp__myserver__authenticate`). Pseudo-tool for unauthenticated MCP servers; starts OAuth flow; auto-removed when real tools available.

### ReadMcpResourceTool (from `tools/ReadMcpResourceTool/`)

Input: `server` (string), `uri` (string). Output: `{ contents: [{ uri, mimeType?, text?, blobSavedTo? }] }`.

### ListMcpResourcesTool (from `tools/ListMcpResourcesTool/`)

Input: `server?` (string). Output: `z.array({ uri, name, mimeType?, description?, server })`.

### Key Identifiers

| Identifier | Value | Source |
|------------|-------|--------|
| `MAX_JOBS` | `50` | `tools/ScheduleCronTool/CronCreateTool.ts` |
| `MAX_LSP_FILE_SIZE_BYTES` | `10_000_000` (10 MB) | `tools/LSPTool/LSPTool.ts` |
| `max_uses` (WebSearch) | `8` | `tools/WebSearchTool/WebSearchTool.ts` |
| `DEFAULT_HEAD_LIMIT` | `250` | `tools/GrepTool/GrepTool.ts` |
| `SAFE_SKILL_PROPERTIES` | Set of 25 property names | `tools/SkillTool/SkillTool.ts` |
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | Env var override; default 25000 | `tools/FileReadTool/limits.ts` |
| `web_search_20250305` | Anthropic beta tool type | `tools/WebSearchTool/WebSearchTool.ts` |
| `isLspConnected()` | Checks LSP server manager | `services/lsp/manager.ts` |
| `isAgentSwarmsEnabled()` | Ant=always; External=`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` or `--agent-teams` + GB gate `tengu_amber_flint` | `utils/agentSwarmsEnabled.ts` |
| `isTodoV2Enabled()` | `CLAUDE_CODE_ENABLE_TASKS` env or `!isNonInteractiveSession()` | `utils/tasks.ts` |
| `getFileReadIgnorePatterns()` | Returns `Map<root, string[]>` from deny-read rules | `utils/permissions/filesystem.ts` |
| `interpretCommandResult()` | `(command, exitCode, stdout, stderr) => { isError, message? }` | `tools/BashTool/commandSemantics.ts` |

### MultiEditTool — Not a Separate Tool

Source code confirms: `MultiEdit` is only a UI verb mapping in `bridge/sessionRunner.ts:74` (`MultiEdit: 'Editing'`). The actual implementation is FileEditTool with `replace_all: boolean` in its schema. There is NO separate MultiEditTool file in `tools/`.

## Tool System Deep-Dive Evidence (4.4-4.6)

### BashTool Security Pipeline (Section 4.4)

**Source**: `tools/BashTool/bashSecurity.ts` (2,593 LOC)

- `BASH_SECURITY_CHECK_IDS`: numeric IDs 1-23 for validators
- Pre-validator gates: `CONTROL_CHAR_RE` blocks `\x00-\x08,\x0B,\x0C,\x0E-\x1F,\x7F`; `hasShellQuoteSingleQuoteBug()` detects `'\''`
- Early validators (can return allow): `validateEmpty`, `validateIncompleteCommands` (ID 1), `validateSafeCommandSubstitution` (ID 8), `validateGitCommit` (ID 12)
- Main validators: `validateJqCommand` (2/3), `validateObfuscatedFlags` (4), `validateShellMetacharacters` (5), `validateDangerousVariables` (6), `validateCommentQuoteDesync` (22), `validateQuotedNewline` (23), `validateNewlines` (7), `validateIFSInjection` (11), `validateProcEnvironAccess` (13), `validateDangerousPatterns` (8), `validateRedirections` (9/10), `validateBackslashEscapedWhitespace` (15), `validateBackslashEscapedOperators` (21), `validateUnicodeWhitespace` (18), `validateMidWordHash` (19), `validateBraceExpansion` (16), `validateZshDangerousCommands` (20), `validateMalformedTokenInjection` (14)
- `nonMisparsingValidators`: `validateNewlines`, `validateRedirections` — their ask results are deferred

**Command semantics**: `tools/BashTool/commandSemantics.ts` — `COMMAND_SEMANTICS` Map with entries for grep/rg/diff/test/find. `interpretCommandResult(command, exitCode, stdout, stderr) → { isError, message? }`.

**Safe env vars**: `tools/BashTool/bashPermissions.ts` — `SAFE_ENV_VARS` array (41 entries), `ANT_ONLY_SAFE_ENV_VARS` (28 entries). Forbidden: PATH, LD_PRELOAD, LD_LIBRARY_PATH, DYLD_*, PYTHONPATH, NODE_PATH, etc.

**Timeouts**: `utils/timeouts.ts` — `DEFAULT_TIMEOUT_MS = 120_000`, `MAX_TIMEOUT_MS = 600_000`. Env overrides: `BASH_DEFAULT_TIMEOUT_MS`, `BASH_MAX_TIMEOUT_MS`.

**Sandbox**: `utils/sandbox/sandbox-adapter.ts` — `SandboxManager.wrapWithSandbox()`. Uses `@anthropic-ai/sandbox-runtime` (bubblewrap/bwrap on Linux, macOS sandbox profile). Filesystem: allowWrite `['.', getClaudeTempDir()]`, denyWrite settings/bare git files.

**Background**: `COMMON_BACKGROUND_COMMANDS` list (npm, node, python, cargo, make, docker, webpack, vite, jest, pytest, etc.). `ASSISTANT_BLOCKING_BUDGET_MS = 15_000`. `MAX_TASK_OUTPUT_BYTES = 5 * 1024 * 1024 * 1024` (5 GB).

### Query Loop (Section 4.5)

**Source**: `query.ts` (1,730 LOC), `QueryEngine.ts` (1,296 LOC), `services/tools/toolExecution.ts` (1,746 LOC), `services/tools/StreamingToolExecutor.ts` (366 LOC)

- `queryLoop()` is `async function*` yielding `StreamEvent | RequestStartEvent | Message`
- State object: `{ messages, toolUseContext, autoCompactTracking, maxOutputTokensRecoveryCount, turnCount, transition }`
- Streaming tool execution gated by `tengu_streaming_tool_execution2` feature flag
- `StreamingToolExecutor.addTool()` called per streamed `tool_use` block; `getCompletedResults()` polled during stream
- Concurrency: safe tools parallel, non-safe serial; `siblingAbortController` cancels siblings on Bash error
- `MAX_OUTPUT_TOKENS_RECOVERY_LIMIT = 3` retries
- ToolResult type in `Tool.ts` lines 321-341: `{ data, newMessages?, contextModifier?, mcpMeta? }`
- Attachments: `utils/attachments.ts` (3,998 LOC), ~60 attachment types, rendered via `createAttachmentMessage()` as `<system-reminder>` XML

### Permission System (Section 4.6)

**Source**: `utils/permissions/permissions.ts`, `utils/permissions/permissionRuleParser.ts`, `utils/permissions/PermissionMode.ts`

- Entry point: `hasPermissionsToUseTool()` → `hasPermissionsToUseToolInner()` (Phase 1) + post-processing (Phase 2)
- Steps: 1a (deny rules) → 1b (ask rules) → 1c (tool.checkPermissions) → 1d (deny) → 1e (user interaction) → 1f (content ask) → 1g (safety check, bypass-immune) → 2a (bypass) → 2b (always allow) → 3 (passthrough→ask)
- PermissionMode enum: default, acceptEdits, plan, bypassPermissions, dontAsk, auto, bubble
- Auto mode classifier: `classifyYoloAction()` in `yoloClassifier.ts` — two-stage XML classification
- Safe tool allowlist: `SAFE_YOLO_ALLOWLISTED_TOOLS` in `classifierDecision.ts` (~25 tools)
- Circuit breaker: `tengu_auto_mode_config.enabled` GrowthBook gate (enabled/disabled/opt-in)
- Denial limits: consecutive ≥3 or total ≥20 → fallback to user prompt
- Permission rule format: `ToolName`, `ToolName(content)`, `ToolName(prefix:*)`
- Rule sources (8): userSettings, projectSettings, localSettings, flagSettings, policySettings, cliArg, command, session
- `ToolPermissionContext` accessed via `context.getAppState().toolPermissionContext` — always reads latest state
