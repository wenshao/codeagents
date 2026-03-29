# 2. Qwen Code 命令系统

Qwen Code 提供 41 个内置斜杠命令，加上从 MCP prompts、bundled skills 和用户自定义文件动态加载的命令。

> 源码: `packages/cli/src/services/BuiltinCommandLoader.ts`（注册所有内置命令）
>
> **注**: 本文档统计为 41 个命令。v0.12 及更早版本为 40 个（39 斜杠 + 1 Skill `/review`），
> v0.13.0 新增 `/loop` 命令（源码: `commands/loopCommand.ts`），增至 41。

## 命令加载机制

命令有 4 个来源（按优先级）：

| 来源 | 加载器 | 位置 |
|------|--------|------|
| 内置命令 | `BuiltinCommandLoader` | `packages/cli/src/ui/commands/*.ts` |
| MCP 提示 | `McpPromptLoader` | MCP 服务器暴露的 prompts |
| 技能命令 | `BundledSkillLoader` | `.qwen/skills/` |
| 文件命令 | `FileCommandLoader` | `.qwen/commands/*.md` 或 `~/.qwen/commands/*.md` |

## 内置命令一览

### 核心命令

| 命令 | 别名 | 用途 | 源码 |
|------|------|------|------|
| `/help` | `?` | 显示帮助信息 | `commands/helpCommand.ts` |
| `/status` | `about` | 显示版本信息 | `commands/aboutCommand.ts` |
| `/auth` | `login` | 管理认证与登录 | `commands/authCommand.ts` |
| `/model` | — | 切换模型 | `commands/modelCommand.ts` |
| `/clear` | `reset`, `new` | 清除对话历史 | `commands/clearCommand.ts` |
| `/compress` | `summarize` | 压缩上下文 | `commands/compressCommand.ts` |
| `/context` | — | 查看 token 用量 | `commands/contextCommand.ts` |
| `/copy` | — | 复制上次回复 | `commands/copyCommand.ts` |
| `/tools` | — | 查看可用工具列表 | `commands/toolsCommand.ts` |
| `/settings` | — | 查看/修改设置 | `commands/settingsCommand.ts` |
| `/permissions` | — | 管理权限规则 | `commands/permissionsCommand.ts` |
| `/memory` | — | 查看/编辑记忆 | `commands/memoryCommand.ts` |
| `/mcp` | — | 管理 MCP 服务器 | `commands/mcpCommand.ts` |

### 会话管理

| 命令 | 别名 | 用途 | 源码 |
|------|------|------|------|
| `/restore` | — | 恢复历史会话检查点 | `commands/restoreCommand.ts` |
| `/resume` | — | 继续上次会话 | `commands/resumeCommand.ts` |
| `/export` | — | 导出当前会话 | `commands/exportCommand.ts` |
| `/quit` | `exit` | 退出 | `commands/quitCommand.ts` |

### 开发辅助

| 命令 | 别名 | 用途 | 源码 |
|------|------|------|------|
| `/agents` | — | 管理子代理 | `commands/agentsCommand.ts` |
| `/skills` | — | 查看可用技能 | `commands/skillsCommand.ts` |
| `/approval-mode` | — | 切换审批模式（plan/default/auto-edit/yolo） | `commands/approvalModeCommand.ts` |
| `/stats` | `usage` | 显示统计信息 | `commands/statsCommand.ts` |
| `/editor` | — | 设置外部编辑器 | `commands/editorCommand.ts` |
| `/hooks` | — | 管理 Hook 配置 | `commands/hooksCommand.ts` |
| `/init` | — | 初始化项目配置（生成 QWEN.md） | `commands/initCommand.ts` |
| `/trust` | — | 管理信任设置 | `commands/trustCommand.ts` |
| `/summary` | — | 生成对话摘要 | `commands/summaryCommand.ts` |
| `/setup-github` | — | 设置 GitHub Actions | `commands/setupGithubCommand.ts` |

### 终端与 UI

| 命令 | 别名 | 用途 | 源码 |
|------|------|------|------|
| `/theme` | — | 切换颜色主题 | `commands/themeCommand.ts` |
| `/vim` | — | 切换 Vim 编辑模式 | `commands/vimCommand.ts` |
| `/terminal-setup` | — | 配置终端集成 | `commands/terminalSetupCommand.ts` |
| `/ide` | — | IDE 集成管理 | `commands/ideCommand.ts` |
| `/directory` | `dir` | 目录管理 | `commands/directoryCommand.tsx` |
| `/language` | — | 切换 UI 语言 | `commands/languageCommand.ts` |

### 信息与反馈

| 命令 | 别名 | 用途 | 源码 |
|------|------|------|------|
| `/bug` | — | 报告 Bug | `commands/bugCommand.ts` |
| `/docs` | — | 打开文档 | `commands/docsCommand.ts` |

### Qwen Code 独有命令

| 命令 | 用途 | 源码 |
|------|------|------|
| `/arena` | **Arena 模式**——多模型在隔离 Git worktree 中竞争执行 | `commands/arenaCommand.ts` |
| `/language` | **切换 UI 语言**（中/英/日/德/俄/葡） | `commands/languageCommand.ts` |
| `/insight` | **代码洞察**——分析代码库生成个性化洞察 | `commands/insightCommand.ts` |
| `/extensions` | **扩展管理**——安装/卸载/列表 | `commands/extensionsCommand.ts` |
| `/btw` | **快速旁问**——不中断主对话的侧边提问 | `commands/btwCommand.ts` |

### Skill 命令

| 命令 | 用途 | 实现 |
|------|------|------|
| `/review` | 代码审查（四代理并行） | Skill（`skills/bundled/review/SKILL.md`） |

> `/review` 的四个审查维度（源码: `packages/core/src/skills/bundled/review/SKILL.md`）：
> 1. **Correctness & Security** — 逻辑错误、空值处理、竞态条件、注入漏洞
> 2. **Code Quality** — 代码风格一致性、命名规范、重复代码
> 3. **Performance** — N+1 查询、内存泄漏、不必要重渲染
> 4. **Undirected Audit** — 无预设维度，全新视角审查

## 子命令

| 父命令 | 子命令 | 用途 |
|--------|--------|------|
| `/agents` | `manage` | 管理子代理（查看/编辑/删除） |
| `/agents` | `create` | 创建新子代理 |
| `/arena` | `start` | 启动 Arena 会话 |
| `/arena` | `stop` | 停止 Arena 会话 |
| `/arena` | `status` | 查看 Arena 状态 |
| `/arena` | `select` / `choose` | 选择最佳结果并合并 diff |
| `/directory` | `add` | 添加目录到工作区 |
| `/directory` | `show` | 显示所有工作区目录 |
| `/export` | `html` / `md` / `json` / `jsonl` | 导出为不同格式 |
| `/extensions` | `explore` | 打开扩展市场 |
| `/extensions` | `install` | 安装扩展 |
| `/extensions` | `manage` | 管理已安装扩展 |
| `/hooks` | `list` / `enable` / `disable` | 列出/启用/禁用 Hook |
| `/ide` | `status` / `install` / `enable` / `disable` | IDE 集成管理 |
| `/language` | `ui` | 设置 UI 语言 |
| `/memory` | `show` / `add` / `refresh` | 查看/添加/刷新记忆 |
| `/stats` | `model` / `tools` | 模型/工具使用统计 |

## 其他命令类型

> 来源：[官方文档](https://qwenlm.github.io/qwen-code-docs/zh/users/features/commands/)

除斜杠命令外，Qwen Code 还支持 3 种命令类型：

### @ 命令（文件/目录注入）

```bash
@src/auth/login.ts       # 将文件内容注入为上下文
@src/components/          # 将目录结构注入为上下文
```

### ! 命令（Shell 执行）

```bash
!git status              # 直接执行 Shell 命令
!npm test                # 运行测试
!                        # 单独 ! 进入 Shell 模式
```

### 自定义命令（Markdown 文件）

在 `~/.qwen/commands/`（用户级）或 `.qwen/commands/`（项目级）放置 `.md` 文件：

```markdown
---
name: deploy
description: 部署到测试环境
---

请执行以下部署步骤：
1. 运行 !{npm run build} 构建项目
2. 读取 @{deploy.config.json} 获取配置
3. 使用 {{args}} 作为目标环境参数
```

支持变量（处理顺序：`@{...}` → `!{...}` → `{{args}}`）：
- `{{args}}`——参数注入
- `!{command}`——Shell 命令执行
- `@{filepath}`——文件内容注入

**目录映射规则**：`commands/git/commit.md` → `/git:commit`

> **注**：TOML 格式命令文件已弃用但仍受支持，便于旧命令迁移。`!` 命令执行时自动设置 `QWEN_CODE=1` 环境变量。`@` 路径含空格时用 `\` 转义（如 `@My\ Documents/file.txt`）。

项目级命令优先于用户级。

## CLI 参数

```bash
# 交互模式
qwen

# 直接提问
qwen "解释这段代码"

# 非交互模式
qwen --non-interactive --prompt "重构 auth 模块"

# 使用特定模型
qwen --model qwen3-coder-plus

# 指定 API Key
qwen --api-key $DASHSCOPE_API_KEY

# 恢复会话
qwen --resume

# 指定会话 ID
qwen --session-id <id>
```

## 与 Gemini CLI 命令对比

| 命令 | Gemini CLI | Qwen Code | 差异 |
|------|-----------|-----------|------|
| `/arena` | ❌ | ✅ | Qwen 新增 |
| `/language` | ❌ | ✅ | Qwen 新增 |
| `/insight` | ❌ | ✅ | Qwen 新增 |
| `/extensions` | ❌ | ✅ | Qwen 新增（Gemini 用 `/mcp`） |
| `/btw` | ❌ | ✅ | Qwen 新增 |
| `/approval-mode` | `/plan` | `/approval-mode` | 重命名，增加 auto-edit/yolo |
| 其余命令 | ✅ | ✅ | 继承，功能一致 |
