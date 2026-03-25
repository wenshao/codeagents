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
