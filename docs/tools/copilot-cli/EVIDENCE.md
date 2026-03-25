########## COPILOT CLI --help ##########
```
Usage: copilot [options] [command]

GitHub Copilot CLI - An AI-powered coding assistant.

Start an interactive session to chat with Copilot, or use -p/--prompt for
non-interactive scripting. Copilot can edit files, run shell commands, search
your codebase, and more — all with configurable permissions.

Run `copilot <command> --help` for details on any subcommand.

Options:
  --effort, --reasoning-effort <level>  Set the reasoning effort level (choices:
                                        "low", "medium", "high", "xhigh")
  --acp                                 Start as Agent Client Protocol server
  --add-dir <directory>                 Add a directory to the allowed list for
                                        file access (can be used multiple times)
  --add-github-mcp-tool <tool>          Add a tool to enable for the GitHub MCP
                                        server instead of the default CLI subset
                                        (can be used multiple times). Use "*"
                                        for all tools.
  --add-github-mcp-toolset <toolset>    Add a toolset to enable for the GitHub
                                        MCP server instead of the default CLI
                                        subset (can be used multiple times). Use
                                        "all" for all toolsets.
  --additional-mcp-config <json>        Additional MCP servers configuration as
                                        JSON string or file path (prefix with @)
                                        (can be used multiple times; augments
                                        config from ~/.copilot/mcp-config.json
                                        for this session)
  --agent <agent>                       Specify a custom agent to use
  --allow-all                           Enable all permissions (equivalent to
                                        --allow-all-tools --allow-all-paths
                                        --allow-all-urls)
  --allow-all-paths                     Disable file path verification and allow
                                        access to any path
  --allow-all-tools                     Allow all tools to run automatically
                                        without confirmation; required for
                                        non-interactive mode (env:
                                        COPILOT_ALLOW_ALL)
  --allow-all-urls                      Allow access to all URLs without
                                        confirmation
  --allow-tool[=tools...]               Tools the CLI has permission to use;
                                        will not prompt for permission
  --allow-url[=urls...]                 Allow access to specific URLs or domains
  --alt-screen[=value]                  Use the terminal alternate screen buffer
                                        (on|off)
  --autopilot                           Enable autopilot continuation in prompt
                                        mode
  --available-tools[=tools...]          Only these tools will be available to
                                        the model
  --banner                              Show the startup banner
  --bash-env[=value]                    Enable BASH_ENV support for bash shells
                                        (on|off)
  --config-dir <directory>              Set the configuration directory
                                        (default: ~/.copilot)
  --continue                            Resume the most recent session
  --deny-tool[=tools...]                Tools the CLI does not have permission
                                        to use; will not prompt for permission
  --deny-url[=urls...]                  Deny access to specific URLs or domains,
                                        takes precedence over --allow-url
  --disable-builtin-mcps                Disable all built-in MCP servers
                                        (currently: github-mcp-server)
  --disable-mcp-server <server-name>    Disable a specific MCP server (can be
                                        used multiple times)
  --disallow-temp-dir                   Prevent automatic access to the system
                                        temporary directory
  --enable-all-github-mcp-tools         Enable all GitHub MCP server tools
                                        instead of the default CLI subset.
                                        Overrides --add-github-mcp-toolset and
                                        --add-github-mcp-tool options.
  --excluded-tools[=tools...]           These tools will not be available to the
                                        model
  --experimental                        Enable experimental features
  -h, --help                            display help for command
  -i, --interactive <prompt>            Start interactive mode and automatically
                                        execute this prompt
  --log-dir <directory>                 Set log file directory (default:
                                        ~/.copilot/logs/)
  --log-level <level>                   Set the log level (choices: "none",
                                        "error", "warning", "info", "debug",
                                        "all", "default")
  --max-autopilot-continues <count>     Maximum number of continuation messages
                                        in autopilot mode (default: unlimited)
  --model <model>                       Set the AI model to use
  --mouse[=value]                       Enable mouse support in alt screen mode
                                        (on|off)
  --no-alt-screen                       Disable the terminal alternate screen
                                        buffer
  --no-ask-user                         Disable the ask_user tool (agent works
                                        autonomously without asking questions)
  --no-auto-update                      Disable downloading CLI update
                                        automatically (disabled by default in CI
                                        environments)
  --no-bash-env                         Disable BASH_ENV support for bash shells
  --no-color                            Disable all color output
  --no-custom-instructions              Disable loading of custom instructions
                                        from AGENTS.md and related files
  --no-experimental                     Disable experimental features
  --no-mouse                            Disable mouse support in alt screen mode
  --output-format <format>              Output format: 'text' (default) or
                                        'json' (JSONL, one JSON object per line)
                                        (choices: "text", "json")
  -p, --prompt <text>                   Execute a prompt in non-interactive mode
                                        (exits after completion)
  --plain-diff                          Disable rich diff rendering (syntax
                                        highlighting via diff tool specified by
                                        git config)
  --plugin-dir <directory>              Load a plugin from a local directory
                                        (can be used multiple times)
  --resume[=sessionId]                  Resume from a previous session
                                        (optionally specify session ID or task
                                        ID)
  -s, --silent                          Output only the agent response (no
                                        stats), useful for scripting with -p
  --screen-reader                       Enable screen reader optimizations
  --secret-env-vars[=vars...]           Environment variable names whose values
                                        are stripped from shell and MCP server
                                        environments and redacted from output
                                        (e.g.,
                                        --secret-env-vars=MY_KEY,OTHER_KEY)
  --share[=path]                        Share session to markdown file after
                                        completion in non-interactive mode
                                        (default: ./copilot-session-<id>.md)
  --share-gist                          Share session to a secret GitHub gist
                                        after completion in non-interactive mode
  --stream <mode>                       Enable or disable streaming mode
                                        (choices: "on", "off")
  -v, --version                         show version information
  --yolo                                Enable all permissions (equivalent to
                                        --allow-all-tools --allow-all-paths
                                        --allow-all-urls)

Commands:
  help [topic]                          Display help information
  init                                  Initialize Copilot instructions
  login [options]                       Authenticate with Copilot
  plugin                                Manage plugins
  update                                Download the latest version
  version                               Display version information

Help Topics:
  commands     Interactive Mode Commands
  config       Configuration Settings
  environment  Environment Variables
  logging      Logging
  permissions  Permissions

Examples:
  # Start interactive mode
  $ copilot

  # Start interactive mode and automatically execute a prompt
  $ copilot -i "Fix the bug in main.js"

  # Execute a prompt in non-interactive mode (exits after completion)
  $ copilot -p "Fix the bug in main.js" --allow-all-tools

  # Enable all permissions with a single flag
  $ copilot -p "Fix the bug in main.js" --allow-all
  $ copilot -p "Fix the bug in main.js" --yolo

  # Start with a specific model
  $ copilot --model gpt-5.2

  # Resume the most recent session
  $ copilot --continue

  # Resume a previous session using session picker
  $ copilot --resume

  # Resume a specific session by ID
  $ copilot --resume=<session-id>

  # Start a new session with a specific UUID
  $ copilot --resume=0cb916db-26aa-40f2-86b5-1ba81b225fd2

  # Resume with auto-approval
  $ copilot --allow-all-tools --resume

  # Allow access to additional directory
  $ copilot --add-dir /home/user/projects

  # Allow multiple directories
  $ copilot --add-dir ~/workspace --add-dir /tmp

  # Disable path verification (allow access to any path)
  $ copilot --allow-all-paths

  # Allow all git commands except git push
  $ copilot --allow-tool='shell(git:*)' --deny-tool='shell(git push)'

  # Allow all file editing
  $ copilot --allow-tool='write'

  # Allow all but one specific tool from MCP server with name "MyMCP"
  $ copilot --deny-tool='MyMCP(denied_tool)' --allow-tool='MyMCP'

  # Allow GitHub API access (defaults to HTTPS)
  $ copilot --allow-url=github.com

  # Deny access to specific domain over HTTPS
  $ copilot --deny-url=https://malicious-site.com
  $ copilot --deny-url=malicious-site.com

  # Allow all URLs without confirmation
  $ copilot --allow-all-urls

  # Initialize Copilot instructions for a repository
  $ copilot init

Learn More:
  Use `copilot <command> --help` for more information about a command.
  Read the documentation at https://docs.github.com/copilot/how-tos/copilot-cli
```

########## BINARY INFO ##########
```
Version: GitHub Copilot CLI 1.0.11.
Run 'copilot update' to check for updates.
npm package: 0.0.403
Binary: /usr/local/lib/node_modules/@github/copilot/node_modules/@github/copilot-linux-x64/copilot: ELF 64-bit LSB executable, x86-64, version 1 (GNU/Linux), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=7ec13eaf1ff43c56457f45f1bc288c1884fbe4e2, for GNU/Linux 3.2.0, with debug_info, not stripped, too many notes (256)
Size: 133M
Date: 2026-03-25T07:34:39Z
```

########## AGENT DEFINITIONS ##########
--- code-review.agent.yaml ---
```yaml
name: code-review
displayName: Code Review Agent
description: >
  Reviews code changes with extremely high signal-to-noise ratio. Analyzes staged/unstaged
  changes and branch diffs. Only surfaces issues that genuinely matter - bugs, security
  issues, logic errors. Never comments on style, formatting, or trivial matters.
model: claude-sonnet-4.5
tools:
  - "*"
promptParts:
  includeAISafety: true
  includeToolInstructions: true
  includeParallelToolCalling: true
  includeCustomAgentInstructions: false
  includeEnvironmentContext: false
prompt: |
  You are a code review agent with an extremely high bar for feedback. Your guiding principle: finding your feedback should feel like finding a $20 bill in your jeans after doing laundry - a genuine, delightful surprise. Not noise to wade through.

  **Environment Context:**
  - Current working directory: {{cwd}}
  - All file paths must be absolute paths (e.g., "{{cwd}}/src/file.ts")

  **Your Mission:**
  Review code changes and surface ONLY issues that genuinely matter:
  - Bugs and logic errors
  - Security vulnerabilities
  - Race conditions or concurrency issues
  - Memory leaks or resource management problems
  - Missing error handling that could cause crashes
  - Incorrect assumptions about data or state
  - Breaking changes to public APIs
  - Performance issues with measurable impact

  **CRITICAL: What You Must NEVER Comment On:**
  - Style, formatting, or naming conventions
  - Grammar or spelling in comments/strings
  - "Consider doing X" suggestions that aren't bugs
  - Minor refactoring opportunities
  - Code organization preferences
  - Missing documentation or comments
  - "Best practices" that don't prevent actual problems
  - Anything you're not confident is a real issue

  **If you're unsure whether something is a problem, DO NOT MENTION IT.**

  **How to Review:**

  1. **Understand the change scope** - Use git to see what changed:
     - First check if there are staged/unstaged changes: `git --no-pager status`
     - If there are staged changes: `git --no-pager diff --staged`
     - If there are unstaged changes: `git --no-pager diff`
     - If working directory is clean, check branch diff: `git --no-pager diff main...HEAD` (adjust branch name if user specifies)
     - For recent commits: `git --no-pager log --oneline -10`
     
     **Important:** If the working directory is clean (no staged/unstaged changes), review the branch diff against main instead. There are always changes to review if you're on a feature branch.

  2. **Understand context** - Read surrounding code to understand:
     - What the code is trying to accomplish
     - How it integrates with the rest of the system
     - What invariants or assumptions exist

  3. **Verify when possible** - Before reporting an issue, consider:
     - Can you build the code to check for compile errors?
     - Are there tests you can run to validate your concern?
     - Is the "bug" actually handled elsewhere in the code?
     - Do you have high confidence this is a real problem?

  4. **Report only high-confidence issues** - If you're uncertain, don't report it

  **CRITICAL: You Must NEVER Modify Code.**
  You have access to all tools for investigation purposes only:
  - Use `bash` to run git commands, build, run tests, execute code
  - Use `view` to read files and understand context
  - Use `grep` and `glob` to find related code
  - Do NOT use `edit` or `create` to change files

  **Output Format:**

  If you find genuine issues, report them like this:
  ```
  ## Issue: [Brief title]
  **File:** path/to/file.ts:123
  **Severity:** Critical | High | Medium
  **Problem:** Clear explanation of the actual bug/issue
  **Evidence:** How you verified this is a real problem
  **Suggested fix:** Brief description (but do not implement it)
  ```

  If you find NO issues worth reporting, simply say:
  "No significant issues found in the reviewed changes."

  Do not pad your response with filler. Do not summarize what you looked at. Do not give compliments about the code. Just report issues or confirm there are none.

  Remember: Silence is better than noise. Every comment you make should be worth the reader's time.
```
--- explore.agent.yaml ---
```yaml
name: explore
displayName: Explore Agent
description: >
  Fast codebase exploration and answering questions. Uses grep, glob, and view
  tools in a separate context window to search files and understand code structure.
  Returns focused answers under 300 words. Safe to call in parallel.
model: claude-haiku-4.5
tools:
  - grep
  - glob
  - view
  - lsp
promptParts:
  includeAISafety: true
  includeToolInstructions: true
  includeParallelToolCalling: true
  includeCustomAgentInstructions: false
  includeEnvironmentContext: false
prompt: |
  You are an exploration agent specialized in rapid codebase analysis and answering questions efficiently.

  **Environment Context:**
  - Current working directory: {{cwd}}
  - All file paths must be absolute paths (e.g., "{{cwd}}/src/file.ts")
  - When using the view tool, always prepend {{cwd}} to relative paths to make them absolute

  Your role is to use available tools to:
  - Search for files by name patterns using the glob tool
  - Search for code patterns and content using the grep tool  
  - Read file contents using the view tool
  - Answer questions about the codebase structure, content, and patterns

  **CRITICAL: Prioritize speed, efficiency, AND BREVITY:**
  - Aim to answer questions in 1-3 tool calls when possible
  - Use targeted searches instead of broad exploration
  - Only read files that are directly relevant to answering the question
  - Stop searching once you have enough information to provide a useful answer
  - **Keep your answer under 300 words** - be direct and concise
  - Avoid creating large tables, long lists, or exhaustive documentation
  - Focus on answering the specific question asked, not providing comprehensive overviews

  **CRITICAL: MAXIMIZE PARALLEL TOOL CALLING:**
  - **ALWAYS call ALL independent tools in parallel in a SINGLE response**
  - If you need to search multiple patterns, call grep multiple times IN PARALLEL
  - If you need to find multiple file types, call glob multiple times IN PARALLEL
  - If you need to read multiple files, call view multiple times IN PARALLEL
  - Only make sequential calls when a later call depends on results from an earlier one
  - Parallelism is KEY to speed - use it aggressively

  Best practices:
  - Start with parallel tool calls for initial exploration (multiple grep/glob patterns at once)
  - Use glob patterns to narrow down which files to search (e.g., "**/*.ts" or "src/**/*.test.js")
  - Always use absolute paths for view tool (e.g., "{{cwd}}/src/agents/prompts.ts")
  - Cite specific files and line numbers when relevant
  - Provide a focused summary, not exhaustive details
  - Use bullet points instead of tables for readability

  Remember: Your goal is rapid exploration through MAXIMUM PARALLELISM and quick, concise answers. Be direct and helpful. Keep responses brief.
```
--- task.agent.yaml ---
```yaml
name: task
displayName: Task Agent
description: >
  Execute development commands like tests, builds, linters, and formatters.
  Returns brief summary on success, full output on failure. Keeps main context
  clean by minimizing verbose output.
model: claude-haiku-4.5
tools:
  - "*"
promptParts:
  includeAISafety: true
  includeToolInstructions: true
  includeParallelToolCalling: true
  includeCustomAgentInstructions: false
  includeEnvironmentContext: false
prompt: |
  You are a command execution agent that runs development commands and reports results efficiently.

  **Environment Context:**
  - Current working directory: {{cwd}}
  - You have access to all CLI tools including bash, file editing, grep, glob, etc.

  **Your role:**
  Execute commands such as:
  - Running tests (e.g., "npm run test", "pytest", "go test")
  - Building code (e.g., "npm run build", "make", "cargo build")
  - Linting code (e.g., "npm run lint", "eslint", "ruff")
  - Installing dependencies (e.g., "npm install", "pip install")
  - Running formatters (e.g., "npm run format", "prettier")

  **CRITICAL - Output format to minimize context pollution:**
  - On SUCCESS: Return brief one-line summary
    * Examples: "All 247 tests passed", "Build succeeded in 45s", "No lint errors found", "Installed 42 packages"
  - On FAILURE: Return full error output for debugging
    * Include complete stack traces, compiler errors, lint issues
    * Provide all information needed to diagnose the problem
  - Do NOT attempt to fix errors, analyze issues, or make suggestions - just execute and report
  - Do NOT retry on failure - execute once and report the result

  **Best practices:**
  - Use appropriate timeouts: tests/builds (200-300 seconds), lints (60 seconds)
  - Execute the command exactly as requested
  - Report concisely on success, verbosely on failure

  Remember: Your job is to execute commands efficiently and minimize context pollution from verbose successful output while providing complete failure information for debugging.
```

########## COMPLETE CLI FLAGS (copilot --help, 2026-03-25T08:07:04Z) ##########
Total flags: 57
```
  --effort, --reasoning-effort <level>  Set the reasoning effort level (choices:
  --acp                                 Start as Agent Client Protocol server
  --add-dir <directory>                 Add a directory to the allowed list for
  --add-github-mcp-tool <tool>          Add a tool to enable for the GitHub MCP
  --add-github-mcp-toolset <toolset>    Add a toolset to enable for the GitHub
  --additional-mcp-config <json>        Additional MCP servers configuration as
  --agent <agent>                       Specify a custom agent to use
  --allow-all                           Enable all permissions (equivalent to
                                        --allow-all-tools --allow-all-paths
                                        --allow-all-urls)
  --allow-all-paths                     Disable file path verification and allow
  --allow-all-tools                     Allow all tools to run automatically
  --allow-all-urls                      Allow access to all URLs without
  --allow-tool[=tools...]               Tools the CLI has permission to use;
  --allow-url[=urls...]                 Allow access to specific URLs or domains
  --alt-screen[=value]                  Use the terminal alternate screen buffer
  --autopilot                           Enable autopilot continuation in prompt
  --available-tools[=tools...]          Only these tools will be available to
  --banner                              Show the startup banner
  --bash-env[=value]                    Enable BASH_ENV support for bash shells
  --config-dir <directory>              Set the configuration directory
  --continue                            Resume the most recent session
  --deny-tool[=tools...]                Tools the CLI does not have permission
  --deny-url[=urls...]                  Deny access to specific URLs or domains,
  --disable-builtin-mcps                Disable all built-in MCP servers
  --disable-mcp-server <server-name>    Disable a specific MCP server (can be
  --disallow-temp-dir                   Prevent automatic access to the system
  --enable-all-github-mcp-tools         Enable all GitHub MCP server tools
                                        --add-github-mcp-tool options.
  --excluded-tools[=tools...]           These tools will not be available to the
  --experimental                        Enable experimental features
  --log-dir <directory>                 Set log file directory (default:
  --log-level <level>                   Set the log level (choices: "none",
  --max-autopilot-continues <count>     Maximum number of continuation messages
  --model <model>                       Set the AI model to use
  --mouse[=value]                       Enable mouse support in alt screen mode
  --no-alt-screen                       Disable the terminal alternate screen
  --no-ask-user                         Disable the ask_user tool (agent works
  --no-auto-update                      Disable downloading CLI update
  --no-bash-env                         Disable BASH_ENV support for bash shells
  --no-color                            Disable all color output
  --no-custom-instructions              Disable loading of custom instructions
  --no-experimental                     Disable experimental features
  --no-mouse                            Disable mouse support in alt screen mode
  --output-format <format>              Output format: 'text' (default) or
  --plain-diff                          Disable rich diff rendering (syntax
  --plugin-dir <directory>              Load a plugin from a local directory
  --resume[=sessionId]                  Resume from a previous session
  --screen-reader                       Enable screen reader optimizations
  --secret-env-vars[=vars...]           Environment variable names whose values
                                        --secret-env-vars=MY_KEY,OTHER_KEY)
  --share[=path]                        Share session to markdown file after
  --share-gist                          Share session to a secret GitHub gist
  --stream <mode>                       Enable or disable streaming mode
  --yolo                                Enable all permissions (equivalent to
                                        --allow-all-tools --allow-all-paths
                                        --allow-all-urls)
```
