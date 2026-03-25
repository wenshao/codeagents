# AGENTS.md 配置指南

> 本文介绍 AGENTS.md 项目指令文件——它是什么、哪些工具支持它、如何编写、以及与 CLAUDE.md / GEMINI.md 的对比。

## 什么是 AGENTS.md

AGENTS.md 是放在项目根目录（或子目录）的 Markdown 文件，用于向 AI 编程代理描述项目的技术栈、构建命令、编码规范和限制条件。代理在启动会话时读取此文件，将其作为系统提示的一部分，从而理解项目上下文。

AGENTS.md 最初由 Codex CLI 引入，现已被多个工具支持：

| 工具 | 原生指令文件 | 是否读取 AGENTS.md | 说明 |
|------|------------|-------------------|------|
| **Codex CLI** | `CODEX.md` | 原生支持 | 最早引入 AGENTS.md 概念 |
| **Kimi CLI** | `AGENTS.md` | 原生支持 | 作为主要项目指令文件 |
| **Copilot CLI** | `.github/copilot-instructions.md` | 读取 | 同时读取 CLAUDE.md、GEMINI.md、AGENTS.md |
| **Qwen Code** | `GEMINI.md` | 读取 | 作为 Gemini CLI 分叉，优先读取 GEMINI.md |
| **Claude Code** | `CLAUDE.md` | 不读取 | 仅读取 CLAUDE.md |
| **Gemini CLI** | `GEMINI.md` | 不读取 | 仅读取 GEMINI.md |

> **要点**：如果你的团队同时使用多个 AI 编程工具，维护一份 AGENTS.md 能覆盖 Codex CLI、Kimi CLI 和 Copilot CLI 三个工具。

## 文件格式和结构

AGENTS.md 是标准 Markdown，没有特殊的 Frontmatter 要求。推荐使用以下结构：

```markdown
# Project: <项目名称>

## Overview
简要描述项目用途、技术栈和架构。

## Development
- Package manager: pnpm
- Test: `pnpm test`
- Lint: `pnpm lint`
- Build: `pnpm build`
- Type check: `pnpm typecheck`

## Conventions
- 函数式组件 + React hooks，禁止 class 组件
- API 路由放在 app/api/ 目录
- 提交消息使用 Conventional Commits 格式
- 变量命名使用 camelCase

## Restrictions
- 不要修改 prisma/migrations/ 中的已有迁移文件
- 不要提交 .env.local 或任何包含密钥的文件
- 不要删除或修改 CI/CD 配置文件
```

### 各区段作用

| 区段 | 作用 | 重要程度 |
|------|------|----------|
| **Overview** | 让代理理解项目背景，避免错误假设 | 高 |
| **Development** | 构建/测试/lint 命令，代理直接调用 | **最高** |
| **Conventions** | 编码风格和命名规范 | 高 |
| **Restrictions** | 明确禁止的操作，防止破坏性变更 | **最高** |

## 与 CLAUDE.md 和 GEMINI.md 的对比

三者本质相同——都是 Markdown 格式的项目指令文件，差别在于目标工具和社区约定：

| 特性 | AGENTS.md | CLAUDE.md | GEMINI.md |
|------|-----------|-----------|-----------|
| **目标工具** | Codex CLI、Kimi CLI、Copilot CLI | Claude Code | Gemini CLI、Qwen Code |
| **格式** | 纯 Markdown | 纯 Markdown | 纯 Markdown |
| **层级发现** | 项目根目录 | 项目根目录 + 子目录递归 | 项目根目录 + 子目录 BFS |
| **子目录规则** | Kimi CLI 支持子目录 | 支持，子目录 CLAUDE.md 追加到上下文 | 支持，按目录特定规则加载 |
| **@import 语法** | 不支持 | 不支持 | Gemini CLI 支持 `@import` 导入其他 Markdown |
| **记忆系统集成** | Kimi CLI 无独立记忆系统 | 跨会话学习存储到 `~/.claude/projects/` | `## Gemini Added Memories` 自动追加区段 |

### 多工具兼容策略

如果项目需要兼容多个 AI 编程工具，有两种策略：

**策略一：维护多个文件**（内容相同）
```
项目根目录/
├── CLAUDE.md          # Claude Code 读取
├── GEMINI.md          # Gemini CLI / Qwen Code 读取
├── AGENTS.md          # Codex CLI / Kimi CLI / Copilot CLI 读取
└── .github/copilot-instructions.md  # Copilot CLI 备选
```

**策略二：维护一个 AGENTS.md + 符号链接**
```bash
# 主文件
echo "# Project instructions..." > AGENTS.md

# 符号链接
ln -s AGENTS.md CLAUDE.md
ln -s AGENTS.md GEMINI.md
```

> Copilot CLI 会同时读取 CLAUDE.md、GEMINI.md 和 AGENTS.md，所以使用策略二时 Copilot 会读取重复内容，但不影响功能。

## 不同项目类型的示例

### Python 项目

```markdown
# Project: data-pipeline

## Overview
Python 数据处理管道，使用 pandas + SQLAlchemy + Celery。

## Development
- Python 版本: 3.12+
- 包管理: uv
- 安装依赖: `uv sync`
- 测试: `uv run pytest`
- 类型检查: `uv run mypy src/`
- 格式化: `uv run ruff format src/`
- Lint: `uv run ruff check src/`

## Conventions
- 类型注解: 所有函数签名必须有完整类型注解
- 文档字符串: Google 风格 docstring
- 导入排序: isort 兼容（ruff 自动处理）
- 异步: I/O 密集操作使用 asyncio

## Restrictions
- 不要直接操作生产数据库，所有变更通过 Alembic 迁移
- 不要在代码中硬编码数据库连接字符串
- 不要修改 alembic/versions/ 中的已有迁移
```

### TypeScript 项目

```markdown
# Project: api-server

## Overview
Express.js API 服务器，TypeScript + Prisma + Redis。

## Development
- Runtime: Node.js 22+
- Package manager: pnpm
- Install: `pnpm install`
- Dev: `pnpm dev`
- Test: `pnpm test`
- Build: `pnpm build`
- Lint: `pnpm lint`
- Type check: `pnpm typecheck`

## Conventions
- 使用 zod 做输入验证
- 错误处理统一使用 AppError 类
- 数据库操作封装在 services/ 层
- 路由文件只做参数解析和响应格式化

## Restrictions
- 不要在 controller 层直接调用 Prisma
- 不要使用 any 类型
- 不要提交 .env 文件
```

### Rust 项目

```markdown
# Project: cli-tool

## Overview
Rust CLI 工具，基于 clap + tokio + serde。

## Development
- Rust edition: 2024
- Build: `cargo build`
- Test: `cargo test`
- Lint: `cargo clippy -- -D warnings`
- Format: `cargo fmt`
- Run: `cargo run -- <args>`

## Conventions
- 错误处理使用 thiserror + anyhow
- 公共 API 使用 #[must_use] 注解
- 所有 pub 函数需要文档注释
- 异步使用 tokio，避免 std::thread::spawn

## Restrictions
- 不要引入 unsafe 代码（除非有充分理由并加注释）
- 不要使用 unwrap()，使用 ? 操作符或 expect() 并说明原因
- 不要修改 Cargo.lock（由 CI 管理）
```

## 编写技巧

### 1. 保持简洁

代理的上下文窗口有限。AGENTS.md 应该精炼——50-100 行足够覆盖大多数项目。冗长的文档反而降低代理效率。

### 2. 始终包含构建命令

构建、测试、lint 命令是代理最常调用的——缺少这些信息会导致代理猜测或试错，浪费 token。

### 3. 明确指定规范

不要写"遵循项目既有风格"——代理不一定能正确推断风格。明确写出命名约定、文件组织、错误处理模式。

### 4. Restrictions 越具体越好

```markdown
# 差：太模糊
- 不要做危险操作

# 好：具体明确
- 不要修改 prisma/migrations/ 中的已有迁移文件
- 不要删除或修改 .github/workflows/ 下的 CI 配置
- 不要在代码中硬编码 API 密钥
```

### 5. 保持与 .gitignore 一致

AGENTS.md 应该提交到 Git。如果有不想共享的个人偏好，可以在工具特定的本地配置中设置（如 Claude Code 的 `.claude/settings.local.json`）。

## 相关资源

- 配置示例对比：`docs/guides/config-examples.md`
- Codex CLI 概述：`docs/tools/codex-cli/01-overview.md`
- Kimi CLI 概述：`docs/tools/kimi-cli/01-overview.md`
- Copilot CLI 概述：`docs/tools/copilot-cli/01-overview.md`
