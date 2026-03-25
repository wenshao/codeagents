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
