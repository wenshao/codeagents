# 10. CLAUDE.md 写作指南

> 如何编写高效的 CLAUDE.md 项目指令文件，让 Claude Code 在每次会话中准确理解你的项目。基于 Anthropic 官方文档、社区最佳实践（Builder.io、HumanLayer、Arize）以及我们对 Claude Code 二进制的逆向分析。

---

## 1. 什么是 CLAUDE.md

CLAUDE.md 是 Claude Code 的**项目指令文件**。每次启动会话时，Claude Code 自动读取此文件，将其内容注入系统提示，作为整个会话的行为指导。

它的本质是一份**写给 AI 的项目说明书**：

- 告诉 Claude Code 你的项目用什么技术栈
- 如何构建、测试、部署
- 遵循哪些编码规范
- 有哪些不可触碰的限制

与 `.editorconfig` 规范编辑器行为类似，CLAUDE.md 规范 AI 代理的行为。

---

## 2. 文件层级与加载顺序

通过二进制分析，Claude Code 按以下顺序加载指令文件，后加载的内容可覆盖先加载的：

| 层级 | 路径 | 作用域 | 是否提交到 Git |
|------|------|--------|---------------|
| 1 | `~/.claude/CLAUDE.md` | 个人全局 | 否 |
| 2 | 项目根目录 `CLAUDE.md` | 项目共享 | 是（推荐） |
| 3 | 子目录 `CLAUDE.md` | 模块级别 | 是（可选） |

**补充配置**：`.claude/settings.local.json` 用于本地设置覆盖，不提交到 Git。

### 各层级的典型用途

**全局 `~/.claude/CLAUDE.md`**：个人编码风格偏好，跨所有项目生效。

```markdown
# 个人偏好
- 优先使用函数式编程风格
- 变量命名使用 camelCase
- 提交消息使用英文
- 回复我时使用中文
```

**项目根目录 `CLAUDE.md`**：团队共享的项目规范，提交到版本控制。

```markdown
# Project: my-saas-app
## 技术栈
TypeScript + Next.js 15 + Prisma + PostgreSQL

## 构建命令
- 开发：`pnpm dev`
- 测试：`pnpm test`
- 类型检查：`pnpm typecheck`
```

**子目录 `CLAUDE.md`**：特定模块的规则，仅在该目录下工作时生效。

```markdown
# packages/shared-ui
本包是共享 UI 组件库，所有组件必须：
- 导出 Storybook stories
- 包含单元测试
- 使用 CSS Modules，禁止内联样式
```

---

## 3. 推荐结构：WHAT / WHY / HOW 框架

一份优秀的 CLAUDE.md 应回答三个问题：

### WHAT — 这个项目是什么

```markdown
## 项目概述
电商平台后端 API，服务日活 50 万用户。
- 技术栈：Python 3.12 + FastAPI + SQLAlchemy 2.0 + Redis
- 数据库：PostgreSQL 16，读写分离
- 部署：Kubernetes on AWS EKS
- 关键依赖：Stripe（支付）、SendGrid（邮件）、S3（文件存储）
```

### WHY — 为什么这样做

```markdown
## 架构决策
- 使用 CQRS 模式分离读写，因为读写比为 100:1
- 所有 API 必须幂等，因为客户端会重试失败请求
- 禁止使用 ORM 的 lazy loading，因为会导致 N+1 查询
- 金额计算必须使用 Decimal，禁止 float
```

### HOW — 怎么操作

```markdown
## 开发命令
- 安装依赖：`uv sync`
- 启动开发服务器：`uv run uvicorn app.main:app --reload`
- 运行全部测试：`uv run pytest`
- 运行单个测试：`uv run pytest tests/test_orders.py -k "test_create_order"`
- 生成迁移：`uv run alembic revision --autogenerate -m "描述"`
- 代码格式化：`uv run ruff format .`
- 类型检查：`uv run mypy app/`

## 编码规范
- 所有 API 端点必须有 Pydantic response model
- 数据库查询封装在 Repository 类中
- 错误处理使用自定义异常类，不要裸抛 HTTPException
- 测试使用 factory_boy 生成测试数据，禁止硬编码

## Git 工作流
- 分支命名：`feat/xxx`、`fix/xxx`、`refactor/xxx`
- 提交消息：Conventional Commits 格式
- PR 必须包含测试，覆盖率不低于 80%
```

---

## 4. 长度建议

**推荐控制在 200 行以内**。根据社区实践数据，200 行以下的 CLAUDE.md 约有 80% 的遵循率；超过 500 行后，遵循率显著下降。

| 长度 | 遵循率 | 建议 |
|------|--------|------|
| < 100 行 | ~90% | 小型项目的理想长度 |
| 100-200 行 | ~80% | 中大型项目的推荐上限 |
| 200-500 行 | ~60% | 考虑拆分到子目录或 Skills |
| > 500 行 | < 50% | 必须拆分，否则关键指令会被忽略 |

**原因**：CLAUDE.md 内容占用上下文窗口。过长的指令会与代码内容、对话历史竞争有限的 token 空间。

---

## 5. 应该写什么

### 写 Claude 猜不到的命令

```markdown
# 好 — 自定义脚本，Claude 无法从 package.json 推断
- 数据库重置：`./scripts/reset-db.sh --seed`
- 生成 API 客户端：`make gen-client`
- 本地 HTTPS：`mkcert -install && ./scripts/dev-ssl.sh`
```

### 写与默认行为不同的规范

```markdown
# 好 — 显式声明非标准做法
- 测试文件放在 `__tests__/` 目录（不是与源码同级）
- 使用 tabs 缩进，宽度 4（不是 spaces）
- import 排序：stdlib > third-party > local，每组之间空一行
```

### 写测试运行器的特殊用法

```markdown
# 好 — 非标准 flag 和环境变量
- 集成测试：`TEST_DB=true pytest tests/integration/ -x --timeout=30`
- 快照更新：`pnpm test -- -u`
- 覆盖率报告：`pytest --cov=app --cov-report=html`
```

### 写架构决策和约束

```markdown
# 好 — 防止 Claude 做出错误的架构变更
- 不要引入新的 ORM（当前使用原生 SQL + sqlc）
- 所有新端点必须通过 API Gateway，不要直接暴露服务
- 前端状态管理只使用 Zustand，不要引入 Redux
```

### 写常见陷阱

```markdown
# 好 — 避免反复踩坑
- `pnpm install` 后必须运行 `pnpm prisma generate`，否则类型报错
- M1 Mac 上 `sharp` 需要 `--platform=linux` flag（Docker 环境）
- CI 中 `NODE_ENV=test` 时数据库连接字符串从 `.env.test` 读取
```

---

## 6. 不应该写什么

### 不要写 Claude 能从代码推断的信息

```markdown
# 坏 — Claude 读 package.json 就知道
- 项目使用 React 18
- 使用 ESLint 做代码检查
- 使用 TypeScript 5.3
```

### 不要写标准惯例

```markdown
# 坏 — Claude 已经知道这些
- 函数应该有清晰的命名
- 代码应该有注释
- 不要使用 var，使用 const/let
```

### 不要写详细的 API 文档

```markdown
# 坏 — 太长，应该链接而非内联
## API 端点清单
POST /api/users - 创建用户，参数：name, email, password...
GET /api/users/:id - 获取用户详情...
（后面还有 50 个端点）

# 好 — 指向文档
- API 文档见 `docs/api.md` 或访问 http://localhost:8000/docs
```

### 不要逐文件描述

```markdown
# 坏 — 项目结构 Claude 自己可以 glob/grep 发现
- src/utils/format.ts：格式化工具函数
- src/utils/validate.ts：校验工具函数
- src/hooks/useAuth.ts：认证 Hook
```

---

## 7. 不同项目类型的示例

### Python（FastAPI + pytest）

```markdown
# CLAUDE.md

## Stack
Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, pytest

## Commands
- Install: `uv sync`
- Dev: `uv run uvicorn app.main:app --reload --port 8000`
- Test: `uv run pytest -x -q`
- Single test: `uv run pytest tests/test_foo.py::test_bar -v`
- Migrate: `uv run alembic upgrade head`
- Lint: `uv run ruff check . --fix`

## Conventions
- 路由定义在 `app/routers/`，每个资源一个文件
- 业务逻辑在 `app/services/`，不要放在路由函数里
- 所有数据库操作通过 `app/repositories/` 层
- 测试使用 httpx.AsyncClient，不要用 TestClient（async 兼容）
- 环境变量通过 `app/config.py` 的 pydantic Settings 读取

## Restrictions
- 不要修改 `alembic/versions/` 中已有的迁移文件
- 不要在路由层直接操作数据库 session
```

### TypeScript（Next.js + Prisma）

```markdown
# CLAUDE.md

## Stack
TypeScript 5.5, Next.js 15 (App Router), Prisma 6, TailwindCSS 4

## Commands
- Install: `pnpm install && pnpm prisma generate`
- Dev: `pnpm dev`
- Test: `pnpm vitest run`
- Test watch: `pnpm vitest`
- Build: `pnpm build`
- DB push: `pnpm prisma db push`

## Conventions
- 使用 Server Components 为默认，仅必要时添加 "use client"
- API Routes 放在 `app/api/`，使用 Route Handlers
- 数据获取使用 Server Actions 或 Route Handlers，不要用 useEffect + fetch
- 样式使用 Tailwind，不要创建 CSS 文件
- Zod 用于所有表单验证和 API 输入校验

## Gotchas
- `pnpm install` 后必须 `pnpm prisma generate`
- 修改 `prisma/schema.prisma` 后需要重启 dev server
```

### Rust（Cargo workspace）

```markdown
# CLAUDE.md

## Stack
Rust 1.82, Cargo workspace, tokio async runtime

## Structure
Cargo workspace with 3 crates:
- `crates/core/` — 核心业务逻辑，无 IO 依赖
- `crates/server/` — HTTP 服务器（axum）
- `crates/cli/` — 命令行工具（clap）

## Commands
- Build: `cargo build`
- Test all: `cargo test --workspace`
- Test one crate: `cargo test -p core`
- Run server: `cargo run -p server`
- Clippy: `cargo clippy --workspace -- -D warnings`
- Format: `cargo fmt --all`

## Conventions
- 错误处理使用 thiserror（库代码）和 anyhow（应用代码）
- 所有 pub 函数必须有文档注释
- unsafe 代码需要注释说明为什么安全
- 新依赖必须在根 Cargo.toml 的 [workspace.dependencies] 声明
```

### Monorepo

```markdown
# CLAUDE.md (根目录)

## Structure
pnpm workspace monorepo:
- `apps/web` — Next.js 前端
- `apps/api` — NestJS 后端
- `packages/shared` — 共享类型和工具函数
- `packages/ui` — 共享 UI 组件

## Commands
- Install: `pnpm install`（根目录执行）
- Dev all: `pnpm dev`（turbo 并行启动所有 apps）
- Test all: `pnpm test`
- Test single package: `pnpm --filter @repo/web test`
- Build: `pnpm build`

## Important
- 修改 `packages/shared` 后需要重新 build：`pnpm --filter @repo/shared build`
- 跨包引用使用 workspace 协议：`"@repo/shared": "workspace:*"`
- 不要在 apps 中直接 import 另一个 app 的代码
```

---

## 8. CLAUDE.md vs Hooks：建议性 vs 确定性

CLAUDE.md 中的指令是**建议性的**，Claude Code 的遵循率约 80%。对于必须 100% 执行的规则，使用 Hooks。

| 对比维度 | CLAUDE.md | Hooks |
|---------|-----------|-------|
| 执行方式 | LLM 解读后自行遵循 | 脚本硬编码执行 |
| 遵循率 | ~80%（建议性） | 100%（确定性） |
| 适用场景 | 编码风格、架构偏好 | 安全检查、格式化、自动测试 |
| 配置位置 | `CLAUDE.md` 文件 | `.claude/settings.json` 的 `hooks` 字段 |

**实践建议**：

```
CLAUDE.md：不要提交包含 TODO 的代码      → 80% 遵循
Hook：PostToolUse 后自动运行 lint       → 100% 执行
```

将**偏好**放在 CLAUDE.md，将**强制规则**放在 Hooks。

---

## 9. 渐进式信息披露

不要把所有信息塞进 CLAUDE.md。利用 Claude Code 的 Skills 机制实现分层：

| 层级 | 放什么 | 何时加载 |
|------|--------|---------|
| CLAUDE.md | 每次会话都需要的核心信息 | 会话开始时自动加载 |
| Skills（`.claude/skills/`） | 特定任务的详细指导 | 按需加载（通过 `/skill` 或自动匹配） |
| 外部文档 | API 参考、设计文档 | Claude 主动读取文件 |

```markdown
# CLAUDE.md 中只写概要
## 数据库
使用 PostgreSQL + Prisma。迁移规范详见 .claude/skills/database-migrations.md

## 部署
使用 GitHub Actions + AWS ECS。部署流程详见 .claude/skills/deployment.md
```

这样 CLAUDE.md 保持精简，详细指导按需注入，最大化上下文空间利用率。

---

## 10. 维护策略

CLAUDE.md 应该像代码一样维护：

### 定期修剪

- 每月审查一次，删除过时的信息
- 如果一条规则 Claude 已经自己做对了（通过代码推断），就删掉它
- 合并重复的规则

### 通过观察验证

```bash
# 开一个新会话，给 Claude 一个相关任务，观察它是否遵循 CLAUDE.md
# 如果它忽略了某条规则，考虑：
# 1. 规则是否措辞不清晰？→ 重写
# 2. 规则是否被淹没在太多内容中？→ 精简
# 3. 规则是否必须遵守？→ 改用 Hook
```

### 版本控制

- 项目根目录的 CLAUDE.md 提交到 Git
- 在 PR Review 中审查 CLAUDE.md 的变更
- 重大变更在提交消息中注明

---

## 11. 跨工具兼容性

CLAUDE.md 不仅被 Claude Code 读取。以下工具也会加载它：

| 工具 | 是否读取 CLAUDE.md | 原生指令文件 |
|------|-------------------|-------------|
| Claude Code | 是（原生） | `CLAUDE.md` |
| Copilot CLI | 是 | `.github/copilot-instructions.md` |
| Codex CLI | 否 | `CODEX.md` / `AGENTS.md` |
| Gemini CLI | 否 | `GEMINI.md` |
| Kimi CLI | 否 | `AGENTS.md` |

如果团队同时使用 Claude Code 和 Copilot CLI，一份 CLAUDE.md 可以同时服务两个工具。

> 如果需要一份指令文件覆盖更多工具，参考 [AGENTS.md 配置指南](agents-md.md)。

---

## 12. .claudeignore 减少 Token 浪费

`.claudeignore` 文件告诉 Claude Code 忽略特定文件和目录，减少不必要的文件读取和上下文占用。语法与 `.gitignore` 相同。

```gitignore
# .claudeignore
node_modules/
dist/
build/
.next/
coverage/
*.min.js
*.lock
vendor/
__pycache__/
*.pyc
```

**典型效果**：一个中型 Node.js 项目，添加 `.claudeignore` 后，Claude Code 的文件搜索速度提升约 30%，上下文中的噪音文件减少 50% 以上。

---

## 13. 常见错误与修正

### 错误 1：写成了 README

```markdown
# 坏 — 这是给人看的介绍，不是给 AI 的指令
## Welcome to MyApp!
MyApp is a revolutionary platform that helps users manage their tasks
efficiently. It was founded in 2023 and has over 10,000 users...
```

```markdown
# 好 — 直接告诉 AI 需要知道什么
## Stack: TypeScript + Next.js 15 + Supabase
## Build: `pnpm build`
## Test: `pnpm vitest run`
```

### 错误 2：指令互相矛盾

```markdown
# 坏 — 前后矛盾
- 所有函数必须有 JSDoc 注释
- 代码应该自解释，减少注释
```

```markdown
# 好 — 明确适用范围
- 导出的公共 API 函数必须有 JSDoc 注释
- 内部私有函数只在逻辑复杂时添加注释
```

### 错误 3：过于笼统

```markdown
# 坏 — 太模糊，AI 无法执行
- 写好代码
- 注意安全
- 性能要好
```

```markdown
# 好 — 具体可执行
- 所有 SQL 查询使用参数化，禁止字符串拼接
- API 响应时间超过 200ms 时需要添加缓存
- 列表接口必须分页，默认 page_size=20
```

### 错误 4：信息过时

定期检查这些易过时的内容：
- 依赖版本号（让 Claude 从 package.json/Cargo.toml 读取）
- 团队成员名单（不需要放在 CLAUDE.md）
- 已弃用的 API 端点（及时清理）
- 已完成的迁移说明（完成后删除）

### 错误 5：把秘密写进 CLAUDE.md

```markdown
# 坏 — CLAUDE.md 会提交到 Git
- API Key: sk-xxxxx
- Database password: mypassword123

# 好 — 指向环境变量
- 所有密钥从环境变量读取，参考 `.env.example`
- 本地开发密钥找团队 lead 获取
```

---

## 总结

| 原则 | 说明 |
|------|------|
| 精简 | 控制在 200 行以内，只写 Claude 需要但无法推断的信息 |
| 具体 | 提供可执行的命令和规则，避免模糊描述 |
| 分层 | 核心指令在 CLAUDE.md，详细指导在 Skills |
| 维护 | 像代码一样审查和修剪，删除过时内容 |
| 互补 | 建议性规则用 CLAUDE.md，强制性规则用 Hooks |
