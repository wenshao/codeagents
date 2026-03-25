# 配置示例对比

> 同一个项目（Node.js Web 应用）在不同工具中的配置写法并排对比。

## 项目指令文件

### Claude Code — `CLAUDE.md`

```markdown
# Project: my-webapp

## 技术栈
- Next.js 14 + TypeScript + Tailwind CSS
- PostgreSQL + Prisma ORM
- Jest 测试框架

## 规范
- 使用 pnpm 而非 npm
- 组件使用函数式 + hooks，禁止 class 组件
- API 路由放在 app/api/ 目录
- 提交消息使用 Conventional Commits 格式

## 构建与测试
- `pnpm test` 运行测试
- `pnpm lint` 运行 ESLint
- `pnpm build` 构建生产版本

## 注意事项
- 不要修改 prisma/migrations/ 目录中的已有迁移
- 环境变量在 .env.local 中，不要提交
```

### Codex CLI — `CODEX.md`

```markdown
# Project: my-webapp

Tech stack: Next.js 14, TypeScript, Tailwind CSS, PostgreSQL, Prisma

## Commands
- Test: `pnpm test`
- Lint: `pnpm lint`
- Build: `pnpm build`

## Rules
- Use pnpm, not npm
- Functional components with hooks only
- API routes in app/api/
- Conventional Commits format
- Never modify existing migrations in prisma/migrations/
- Never commit .env.local
```

### Gemini CLI / Qwen Code — `GEMINI.md`

```markdown
# Project: my-webapp

## 技术栈
Next.js 14 + TypeScript + Tailwind CSS + PostgreSQL + Prisma

## 构建命令
- pnpm test
- pnpm lint
- pnpm build

## 编码规范
- 函数式组件 + hooks
- API 路由放 app/api/
- Conventional Commits

## 禁止
- 不修改 prisma/migrations/ 已有文件
- 不提交 .env.local
```

### Kimi CLI — `AGENTS.md`

```markdown
# Project: my-webapp

## Overview
A Next.js 14 web application with TypeScript, Tailwind CSS, PostgreSQL and Prisma ORM.

## Development
- Package manager: pnpm
- Test: `pnpm test`
- Lint: `pnpm lint`
- Build: `pnpm build`

## Conventions
- Functional components with React hooks
- API routes under app/api/
- Conventional Commits for git messages

## Restrictions
- Do not modify existing Prisma migrations
- Do not commit .env.local
```

### Copilot CLI — `.github/copilot-instructions.md`

```markdown
This is a Next.js 14 project with TypeScript, Tailwind CSS, PostgreSQL and Prisma.

Use pnpm for all package operations. Use functional components with hooks.
Place API routes in app/api/. Follow Conventional Commits format.

Test: pnpm test | Lint: pnpm lint | Build: pnpm build

Never modify files in prisma/migrations/. Never commit .env.local.
```

> **注意：** Copilot CLI 同时读取 CLAUDE.md、GEMINI.md、AGENTS.md，所以上述任何格式都可用。

### Cursor — `.cursor/rules/project.mdc`

```markdown
---
description: Project conventions for my-webapp
globs: ["**/*.ts", "**/*.tsx"]
alwaysApply: true
---

- Next.js 14 + TypeScript + Tailwind CSS + PostgreSQL + Prisma
- Use pnpm, functional components with hooks only
- API routes in app/api/, Conventional Commits
- Run: pnpm test | pnpm lint | pnpm build
- Never modify prisma/migrations/ or commit .env.local
```

## 权限配置

### Claude Code — `~/.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(pnpm test)",
      "Bash(pnpm lint)",
      "Bash(pnpm build)",
      "Bash(git:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Write(.env*)"
    ]
  },
  "model": "claude-sonnet-4-6"
}
```

### Codex CLI — `~/.codex/config.toml`

```toml
model = "gpt-5.1-codex"

[sandbox]
type = "workspace-write"

[shell_environment_policy]
inherit = "all"
```

### Gemini CLI — `~/.gemini/settings.json`

```json
{
  "theme": "dark",
  "model": "gemini-2.5-pro",
  "checkpointing": { "enabled": true },
  "sandbox": { "enabled": true }
}
```

## MCP 配置

### Claude Code — `.mcp.json`（项目级）

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": { "DATABASE_URL": "postgresql://localhost:5432/mydb" }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" }
    }
  }
}
```

### Copilot CLI — `~/.copilot/mcp-config.json`

```json
{
  "servers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": { "DATABASE_URL": "postgresql://localhost:5432/mydb" }
    }
  }
}
```

### Codex CLI — `~/.codex/config.toml`（MCP 部分）

```toml
[mcp_servers.postgres]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-postgres"]

[mcp_servers.postgres.env]
DATABASE_URL = "postgresql://localhost:5432/mydb"
```

### Kimi CLI — `~/.kimi/mcp.json`

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": { "DATABASE_URL": "postgresql://localhost:5432/mydb" }
    }
  }
}
```

## 配置文件路径速查

| 配置 | Claude Code | Copilot CLI | Codex CLI | Gemini CLI | Kimi CLI |
|------|------------|-------------|-----------|-----------|----------|
| **项目指令** | `CLAUDE.md` | `.github/copilot-instructions.md` | `CODEX.md` | `GEMINI.md` | `AGENTS.md` |
| **全局设置** | `~/.claude/settings.json` | `~/.copilot/` | `~/.codex/config.toml` | `~/.gemini/settings.json` | `~/.kimi/config.toml` |
| **项目设置** | `.claude/settings.json` | — | `.codex/` | `.gemini/settings.json` | — |
| **MCP 配置** | `.mcp.json` | `~/.copilot/mcp-config.json` | config.toml 内 | `~/.gemini/mcp.json` | `~/.kimi/mcp.json` |
| **忽略文件** | `.claudeignore` | — | — | `.geminiignore` | — |
| **记忆/知识** | `~/.claude/projects/` | `~/.copilot/` | `~/.codex/` | `~/.gemini/GEMINI.md` | `AGENTS.md` |
