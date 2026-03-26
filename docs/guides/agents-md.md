# 11. AGENTS.md 配置指南

> 本文介绍 AGENTS.md 项目指令文件——它是什么、哪些工具支持它、如何编写、以及与 CLAUDE.md / GEMINI.md 的对比。

## 什么是 AGENTS.md

AGENTS.md 是放在项目根目录（或子目录）的 Markdown 文件，用于向 AI 编程代理描述项目的技术栈、构建命令、编码规范和限制条件。代理在启动会话时读取此文件，将其作为系统提示的一部分，从而理解项目上下文。

AGENTS.md 最初由 Codex CLI 引入，现已被多个工具支持：

| Agent | 原生指令文件 | 是否读取 AGENTS.md | 说明 |
|------|------------|-------------------|------|
| **Codex CLI** | `AGENTS.md` | **原生支持**（43 处引用） | 二进制确认：支持子目录递归、深层覆盖浅层。`CODEX.md` 引用数 0（已废弃？） |
| **Kimi CLI** | `AGENTS.md` | 原生支持 | 作为主要项目指令文件 |
| **Copilot CLI** | `.github/copilot-instructions.md` | 读取 | 同时读取 CLAUDE.md、GEMINI.md、AGENTS.md |
| **Qwen Code** | `QWEN.md` | **✓ 原生支持**（v0.13.0+） | 二进制确认 `AGENT_CONTEXT_FILENAME = "AGENTS.md"`，默认同时搜索 QWEN.md 和 AGENTS.md |
| **Claude Code** | `CLAUDE.md` | 不作为指令加载（但 `/init` 会参考） | 仅加载 CLAUDE.md 到系统提示。`/init` 生成 CLAUDE.md 时会读取 AGENTS.md 内容作为参考 |
| **Gemini CLI** | `GEMINI.md` | 不读取（二进制 0 引用） | 44 处 GEMINI.md 引用，0 处 AGENTS.md 引用 |
| **Goose** | `config.yaml` | 不读取 | 配置文件驱动，非 Markdown 指令 |
| **OpenCode** | `opencode.json` | 不读取 | JSON 配置，兼容读取 `.claude/`、`.gemini/` 路径下的 SKILL.md |

> **要点**：维护一份 AGENTS.md + 符号链接，可覆盖 **6 个 Agent**（Codex CLI、Kimi CLI、Copilot CLI + 通过符号链接的 Claude Code、Qwen Code、Gemini CLI）。

## 各 Agent 的读取行为差异

### 读取路径与优先级

| Agent | 读取的文件 | 搜索路径 | 层级合并 |
|-------|-----------|---------|---------|
| **Claude Code** | `CLAUDE.md` | `~/.claude/CLAUDE.md`（全局）→ `<project>/CLAUDE.md`（项目）→ `<project>/.claude/CLAUDE.md` → 子目录递归 → `~/.claude/projects/<hash>/CLAUDE.md`（私有） | 4 层追加 |
| **Gemini CLI** | `GEMINI.md` | `~/.gemini/GEMINI.md`（全局）→ 项目根 → 子目录 BFS（按 inode 去重）→ 扩展级 | 4 层，支持 `@import` |
| **Qwen Code** | `QWEN.md` / `AGENTS.md` / `GEMINI.md` | 继承 Gemini 路径 + v0.13.0 新增 `AGENT_CONTEXT_FILENAME = "AGENTS.md"` 默认搜索。`/init` 生成 QWEN.md | 继承 Gemini + AGENTS.md |
| **Codex CLI** | `AGENTS.md`（+ `SKILL.md`） | 子目录递归搜索，深层覆盖浅层（二进制 43 处引用）。`CODEX.md` 在二进制中引用数 0 | 多层递归 |
| **Kimi CLI** | `AGENTS.md` 或 `agents.md` | 项目根 `<work_dir>/AGENTS.md`（大小写不敏感），通过 `load_agents_md()` 注入系统提示。**不支持子目录** | 1 层 |
| **Copilot CLI** | 多格式（7 种） | `CLAUDE.md`（项目根+父目录）→ `GEMINI.md` → `AGENTS.md` → `.github/instructions/**/*.instructions.md` → `.github/copilot-instructions.md` → `~/.copilot/copilot-instructions.md`（全局）→ `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` 环境变量 | 全部合并 |

### Copilot CLI 的跨格式读取（最兼容）

Copilot CLI 是唯一同时读取 **7 种指令来源**的 Agent（源码：`02-commands.md`）：

```
1. CLAUDE.md（项目根 + 父目录遍历）    ← Claude Code 兼容
2. GEMINI.md（项目根）                  ← Gemini CLI 兼容
3. AGENTS.md（项目根）                  ← Codex/Kimi 兼容
4. .github/instructions/**/*.instructions.md  ← GitHub 标准
5. .github/copilot-instructions.md      ← Copilot 原生
6. ~/.copilot/copilot-instructions.md   ← 全局（所有项目）
7. COPILOT_CUSTOM_INSTRUCTIONS_DIRS 环境变量  ← 自定义目录
```

所有来源**全部合并**到系统提示中。可通过 `--no-custom-instructions` 禁用加载。使用符号链接时相同内容会被加载多次，但不影响功能。

### Claude Code 的 4 层记忆体系

```
~/.claude/CLAUDE.md                    ← 全局（所有项目通用偏好）
<project-root>/CLAUDE.md               ← 项目级（Git 提交，团队共享）
<subdirectory>/CLAUDE.md               ← 模块级（子目录特定规则）
~/.claude/projects/<hash>/CLAUDE.md    ← 用户私有（不提交 Git）
```

Claude Code 还有 auto-memory 系统（4 种记忆类型：user/feedback/project/reference），自动从对话中学习并存储到 `~/.claude/projects/<hash>/memory/`。

### Gemini CLI 的 @import 语法（独有）

```markdown
<!-- GEMINI.md -->
# 项目指令

@import ./docs/coding-standards.md
@import ./docs/api-conventions.md

## 额外规则
...
```

其他 Agent 不支持 `@import`，会将其作为普通文本处理。

---

## 跨 Agent 兼容写法

### 一份文件覆盖所有 Agent 的最佳实践

```markdown
# Project: my-app

## Overview
<!-- 简洁描述，50-100 行内 -->
TypeScript + React + PostgreSQL 全栈应用。

## Development
- Install: `pnpm install`
- Dev: `pnpm dev`
- Test: `pnpm test`
- Lint: `pnpm lint`
- Build: `pnpm build`

## Conventions
- 函数式组件 + hooks，禁止 class 组件
- API 路由放在 app/api/
- 提交消息使用 Conventional Commits

## Restrictions
- 不要修改 prisma/migrations/ 中的已有迁移
- 不要提交 .env 或包含密钥的文件
- 不要删除 .github/workflows/ 配置
```

**关键原则**：
- 使用标准 Markdown 二级标题（`##`），所有 Agent 都能解析
- 避免 `@import` 语法（仅 Gemini CLI 支持）
- 避免 YAML frontmatter（仅 SKILL.md 使用，指令文件不需要）
- 保持 50-100 行（上下文窗口有限）
- `## Development` 和 `## Restrictions` 是最关键的两节

### 符号链接策略（推荐）

```bash
# 1. 创建主文件
vim AGENTS.md

# 2. 创建符号链接
ln -s AGENTS.md CLAUDE.md    # → Claude Code
ln -s AGENTS.md QWEN.md     # → Qwen Code
# 可选：ln -s AGENTS.md GEMINI.md  # → Gemini CLI

# 3. 提交到 Git（Git 会保存符号链接）
git add AGENTS.md CLAUDE.md QWEN.md
git commit -m "Add project instructions with cross-agent symlinks"
```

**覆盖效果**：

| Agent | 读取文件 | 是否覆盖 |
|-------|---------|---------|
| Codex CLI | AGENTS.md | ✅ 直接读取 |
| Kimi CLI | AGENTS.md | ✅ 直接读取 |
| Copilot CLI | AGENTS.md + CLAUDE.md | ✅ 两者都指向同一文件 |
| Claude Code | CLAUDE.md → AGENTS.md | ✅ 通过符号链接 |
| Qwen Code | AGENTS.md | ✅ **原生支持**（v0.13.0+ 默认搜索 AGENTS.md） |
| Gemini CLI | GEMINI.md | ❌ 需额外 `ln -s AGENTS.md GEMINI.md` |

### Qwen Code 原生支持 AGENTS.md（v0.13.0+）

Qwen Code v0.13.0 **默认同时搜索** QWEN.md 和 AGENTS.md，无需额外配置：

```javascript
// 从 v0.13.0 二进制提取（cli.js）
DEFAULT_CONTEXT_FILENAME = "QWEN.md";      // 默认指令文件
AGENT_CONTEXT_FILENAME = "AGENTS.md";      // 新增：AGENTS.md 支持
```

之前的 [Issue #727](https://github.com/QwenLM/qwen-code/issues/727)（`contextFileName` 配置不生效）已**关闭**。v0.13.0 通过新增 `AGENT_CONTEXT_FILENAME` 常量从根本上解决了此问题——不再依赖 `contextFileName` 配置。

> 这意味着 Qwen Code v0.13.0+ 的项目中，放一个 `AGENTS.md` 就能直接被读取，无需符号链接或配置。

### Windows 注意事项

Windows 的符号链接需要管理员权限或开发者模式。替代方案：

```powershell
# Windows（需管理员权限）
mklink CLAUDE.md AGENTS.md
mklink QWEN.md AGENTS.md

# 或使用 Git 配置（所有平台）
# .gitattributes
CLAUDE.md merge=ours
QWEN.md merge=ours
```

---

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

## 指令文件格式对比

四种指令文件本质相同——都是 Markdown 格式，差别在于目标 Agent 和附加能力：

| 特性 | AGENTS.md | CLAUDE.md | GEMINI.md | QWEN.md |
|------|-----------|-----------|-----------|---------|
| **目标 Agent** | Codex CLI、Kimi CLI、Copilot CLI | Claude Code | Gemini CLI | Qwen Code |
| **格式** | 纯 Markdown | 纯 Markdown | 纯 Markdown | 纯 Markdown |
| **层级** | 项目根（1-2 层） | 全局+项目+子目录+私有（4 层） | 全局+扩展+项目+子目录（4 层） | 继承 Gemini 层级 |
| **@import** | ✗ | ✗ | ✓（导入其他 Markdown） | ✗ |
| **AI 记忆** | ✗ | auto-memory（4 类型） | memory_manager 子代理 | 继承 Gemini |
| **符号链接兼容** | 主文件 | ✓ → AGENTS.md | ✓ → AGENTS.md | ✓ → AGENTS.md |

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
