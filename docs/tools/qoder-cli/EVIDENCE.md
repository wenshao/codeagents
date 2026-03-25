# Qoder CLI 二进制分析证据

## 基本信息
- 包: @qoder-ai/qodercli v0.1.35
- 二进制: /usr/local/lib/node_modules/@qoder-ai/qodercli/bin/qodercli
- 格式: ELF 64-bit LSB executable, x86-64, statically linked, stripped
- 大小: 43 MB
- 语言: Go
- 内部包根: code.alibaba-inc.com/qoder-core/qodercli/

## CLI --help 完整输出
```
Qoder is a powerful terminal-based AI assistant that helps with software development tasks.

Usage:
  qodercli [flags]
  qodercli [command]

Job Management Commands:
  jobs         List concurrent job(s)
  rm           Remove concurrent job(s)

Additional Commands:
  commit       Commit AI-generated code and record AI contribution statistics
  completion   Generate the autocompletion script for the specified shell
  feedback     Submit feedback with optional images
  help         Help about any command
  install      Install qodercli to the standard location
  mcp          Manage MCP (Model Context Protocol) servers
  status       Show account and CLI status
  update       Check remote version and self-update to the latest release

Flags:
  --agents, --allowed-tools, --attachment, --branch, -c/--continue,
  --dangerously-skip-permissions, --disallowed-tools, --experimental-mcp-load,
  --input-format, --max-output-tokens, --max-turns, --model, -f/--output-format,
  --path, -p/--print, -q/--quiet, -r/--resume, --summarize-tool,
  -v/--version, --with-claude-config, -w/--workspace, --worktree, --yolo
```

## MCP --help 输出
```
Available Commands: add, auth, get, list, remove
```

## status 输出
```
Version: 0.1.35
Username: [redacted]
Email: [redacted]@alibaba-inc.com
User Type: personal_standard
Plan: Free
```

## 内部包结构（30+ 包）
acp/, cmd/(commit/endpoint/feedback/install/jobs/login/mcp/status/update),
core/(agent/auth/config/mcp/permission/rule), tui/(components/event/render/state/styles/theme),
packages/

## SDK 引用计数
openai-go: 11,464 | anthropic-sdk-go: 3,901 | mcp-go: 744 | cobra: 1,009

## API 端点
api1.qoder.sh, api3.qoder.sh, center.qoder.sh, openapi.qoder.sh,
download.qoder.com, docs.qoder.com, forum.qoder.com,
api.openai.com (BYOK), dashscope.aliyuncs.com (BYOK)

## Machine ID
getMachineKey 函数存在于二进制中（设备标识）

## 10 个内置主题
catppuccin, dracula, flexoki, gruvbox, monokai, onedark, qoder, tokyonight, tron + default

## 提取时间
2026-03-25
