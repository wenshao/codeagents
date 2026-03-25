# GitHub Copilot CLI 用户使用指南

> 基于 v0.0.403 源码分析、SEA 二进制反编译（34 命令、67 工具、3 代理、14+ 模型）编写。

---

## 目录

1. [快速上手](#1-快速上手)
2. [日常使用](#2-日常使用)
3. [三个内置代理](#3-三个内置代理)
4. [代码审查 /review](#4-代码审查-review)
5. [模型选择](#5-模型选择)
6. [自定义指令](#6-自定义指令)
7. [MCP 配置](#7-mcp-配置)
8. [权限系统](#8-权限系统)
9. [自动驾驶模式](#9-自动驾驶模式)
10. [/plan 计划模式](#10-plan-计划模式)
11. [浏览器自动化](#11-浏览器自动化)
12. [GitHub 集成](#12-github-集成)
13. [/delegate 委派](#13-delegate-委派)
14. [费用管理](#14-费用管理)
15. [实用技巧](#15-实用技巧)
16. [常见问题](#16-常见问题)
17. [深度文档链接](#17-深度文档链接)

---

## 1. 快速上手

### 安装

提供四种安装方式，选择任意一种即可：

```bash
# 方式一：安装脚本（macOS / Linux，推荐）
curl -fsSL https://gh.io/copilot-install | bash

# 方式二：Homebrew（macOS / Linux）
brew install copilot-cli

# 方式三：WinGet（Windows）
winget install GitHub.Copilot

# 方式四：npm（全平台，需 Node.js）
npm install -g @github/copilot
```

安装完成后，终端中输入 `copilot` 即可启动。

### 登录认证

首次启动时需要登录 GitHub 账户：

```bash
# 交互式登录（OAuth 设备流，浏览器跳转授权）
copilot login

# 或使用 PAT（Personal Access Token）
# 创建带 "Copilot Requests" 权限的 fine-grained PAT
export GH_TOKEN=ghp_xxxxxxxxxxxxxxxx
copilot
```

### 第一次对话

```bash
# 启动交互式会话
copilot

# 启动并立即发送提示
copilot -i "帮我修复 main.js 中的 bug"

# 非交互式（执行完自动退出，适合脚本）
copilot -p "列出所有 TODO 注释" --allow-all-tools
```

---

## 2. 日常使用

### 常用对话示例

```
> 帮我重构 utils.ts 中的 parseDate 函数，支持 ISO 8601 格式
> 运行测试并修复失败的用例
> 解释 src/auth/ 目录下的认证流程
> 创建一个 GitHub Actions 工作流，每次 PR 时自动运行 lint
```

### 常用斜杠命令速查表

| 命令 | 别名 | 说明 |
|------|------|------|
| `/help` | — | 显示所有可用命令 |
| `/clear` | `/new` | 清除对话历史，开始新会话 |
| `/model` | `/models` | 切换或查看当前模型 |
| `/compact` | — | 压缩上下文，释放 token 空间 |
| `/context` | — | 查看当前已加载的上下文 |
| `/allow-all` | `/yolo` | 跳过所有工具执行确认 |
| `/review` | — | 启动代码审查代理 |
| `/agent` | — | 调用内置代理（explore / task） |
| `/plan` | — | 创建实现计划（需启用功能标志） |
| `/cwd` | `/cd` | 切换工作目录 |
| `/add-dir` | — | 添加额外工作目录 |
| `/mcp` | — | 管理 MCP 服务器 |
| `/share` | — | 分享当前对话 |
| `/session` | — | 管理会话 |
| `/resume` | — | 恢复之前的会话 |
| `/exit` | `/quit` | 退出 CLI |

### 会话管理

```bash
# 继续上次对话
copilot --continue

# 恢复指定会话
copilot --resume=<session-id>

# 分享对话到 Markdown 文件
copilot -p "分析项目架构" --share

# 分享到 GitHub Gist
copilot -p "分析项目架构" --share-gist
```

---

## 3. 三个内置代理

Copilot CLI 内置三个专用代理，各有独立的模型、工具权限和行为约束。

### explore 代理 -- 快速探索

```
> /agent explore 这个项目的认证机制是怎么实现的？
> /agent explore 找到所有使用 Redis 缓存的地方
```

- **模型：** claude-haiku-4.5（轻量快速）
- **工具：** 仅 grep、glob、view、lsp（只读，不修改文件）
- **特点：** 回答限制 300 字以内，最大化并行工具调用，1-3 次工具调用完成回答
- **适用场景：** 理解代码结构、查找函数定义、回答关于项目的问题

### task 代理 -- 执行任务

```
> /agent task 运行所有单元测试
> /agent task 执行 npm run build 并报告结果
> /agent task 运行 eslint 检查
```

- **模型：** claude-haiku-4.5
- **工具：** 全部工具（`*`）
- **特点：** 成功时返回简短摘要（如 "All 247 tests passed"），失败时返回完整错误输出
- **适用场景：** 运行测试、构建、lint、安装依赖等重复性任务

### code-review 代理 -- 代码审查

```
> /review
> /agent code-review 审查我在 auth 模块的改动
```

- **模型：** claude-sonnet-4.5
- **工具：** 全部工具（但被提示约束为只读）
- **特点：** 高信噪比，只报告真正重要的问题
- **适用场景：** 提交前审查、PR 前自检

---

## 4. 代码审查 /review

`/review` 是调用 code-review 代理的快捷命令。该代理遵循严格的审查原则。

### 审查范围

代理会自动检测要审查的内容：
1. 有暂存更改（staged） -- 审查 `git diff --staged`
2. 有未暂存更改（unstaged） -- 审查 `git diff`
3. 工作目录干净 -- 审查当前分支与 main 的差异

### 只报告这些问题

| 类别 | 说明 |
|------|------|
| Bugs / 逻辑错误 | 代码逻辑缺陷 |
| 安全漏洞 | SQL 注入、XSS、认证绕过等 |
| 竞态条件 | 并发访问问题 |
| 内存泄漏 | 资源未释放 |
| 缺失错误处理 | 可能导致崩溃 |
| 错误假设 | 对数据或状态的不正确假设 |
| 破坏性 API 变更 | 公共接口不兼容改动 |
| 性能问题 | 可衡量的性能退化 |

### 绝不评论这些

代码风格、命名规范、拼写、"建议做 X"、微重构、文档缺失、主观的"最佳实践"。

### 输出格式

```markdown
## Issue: 未处理的空指针异常
**File:** src/auth/login.ts:47
**Severity:** High
**Problem:** user.profile 可能为 null，直接访问 .name 会崩溃
**Evidence:** 在 L32 的 getUserById 返回值中 profile 字段标记为可选
**Suggested fix:** 添加空值检查或使用可选链 (?.)
```

如果没有值得报告的问题，代理只会回复：`No significant issues found in the reviewed changes.`

---

## 5. 模型选择

### 可用模型

通过 `/model` 命令查看和切换，或使用 `--model` 参数、`COPILOT_MODEL` 环境变量指定。

| 模型 | 倍率 | 特点 |
|------|------|------|
| gpt-5-mini | 0x（免费） | 支持 thinking 模式，日常使用推荐 |
| gpt-4.1 | 0x（免费） | 免费模型 |
| gpt-5.2-codex | 1x | 默认主力模型，支持 thinking + apply-patch |
| gpt-5.1-codex-max | — | 更强的 Codex 模型 |
| claude-sonnet-4.5 | 1x | code-review 代理默认模型 |
| claude-opus-4.5 | 3x | 最强 Claude，高倍率 |
| claude-haiku-4.5 | — | explore/task 代理默认，快速轻量 |
| gemini-3-pro | 1x | Google Gemini 系列 |

### 切换模型

```bash
# 命令行参数
copilot --model claude-sonnet-4.5

# 交互式切换
> /model gpt-5-mini

# 环境变量
export COPILOT_MODEL=gpt-5.2-codex

# 子代理模型
export COPILOT_AGENT_MODEL=claude-haiku-4.5
```

### 推理努力级别

部分模型（GPT-5 系列）支持调节推理深度：

```bash
copilot --effort high    # low / medium / high / xhigh
```

---

## 6. 自定义指令

Copilot CLI 的一大特色是**兼容多种指令文件格式**，会在启动时按以下顺序搜索并全部加载：

| 优先级 | 文件 | 兼容性 |
|--------|------|--------|
| 1 | `CLAUDE.md`（项目根目录及父目录） | 兼容 Claude Code |
| 2 | `GEMINI.md`（项目根目录） | 兼容 Gemini CLI |
| 3 | `AGENTS.md`（项目根目录） | Copilot CLI 原生 |
| 4 | `.github/instructions/**/*.instructions.md` | GitHub 规范 |
| 5 | `.github/copilot-instructions.md` | Copilot 专用 |
| 6 | `~/.copilot/copilot-instructions.md` | 用户级全局 |
| 7 | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` 环境变量 | 自定义目录 |

这意味着如果你的项目已经有 `CLAUDE.md` 或 `GEMINI.md`，Copilot CLI 会直接读取它们，无需额外配置。

### 示例：项目级指令

在项目根目录创建 `AGENTS.md`（或复用已有的 `CLAUDE.md`）：

```markdown
# 项目指令

- 使用 TypeScript 严格模式
- 所有 API 端点必须有错误处理
- 测试使用 vitest，覆盖率目标 80%
- 提交信息遵循 Conventional Commits 规范
```

### 自定义代理

在 `.github/` 目录下创建 `.agent.md` 文件定义自定义代理（需启用 `CUSTOM_AGENTS` 功能标志）：

```
# .github/security-audit.agent.md
专门检查安全相关的代码问题，包括认证、授权、输入校验、密钥管理。
```

也兼容 Claude Code 的代理目录：`.claude/agents/*.agent.md`。

### 禁用自定义指令

```bash
copilot --no-custom-instructions
```

---

## 7. MCP 配置

MCP（Model Context Protocol）允许扩展 Copilot CLI 的工具能力。

### 配置文件

创建 `~/.copilot/mcp-config.json`：

```json
{
  "mcpServers": {
    "my-database": {
      "command": "node",
      "args": ["/path/to/db-mcp-server.js"],
      "env": {
        "DB_URL": "postgresql://localhost:5432/mydb"
      }
    },
    "my-api": {
      "url": "https://api.example.com/mcp",
      "transport": "sse"
    }
  }
}
```

### 命令行配置

```bash
# 额外 MCP 配置（JSON 字符串）
copilot --additional-mcp-config '{"mcpServers":{"test":{"command":"node","args":["server.js"]}}}'

# 从文件加载
copilot --additional-mcp-config @/path/to/mcp-config.json

# 环境变量
export COPILOT_MCP_JSON=/path/to/mcp-config.json
```

### GitHub MCP 工具管理

Copilot CLI 内置 GitHub MCP 服务器，默认启用部分工具：

```bash
# 启用所有 GitHub MCP 工具
copilot --enable-all-github-mcp-tools

# 添加特定工具
copilot --add-github-mcp-tool search_code

# 添加工具集
copilot --add-github-mcp-toolset all

# 禁用内置 MCP
copilot --disable-builtin-mcps

# 禁用特定 MCP 服务器
copilot --disable-mcp-server my-database
```

### 交互式管理

在会话中使用 `/mcp` 命令查看、添加或移除 MCP 服务器。

---

## 8. 权限系统

### 三种执行模式

| 模式 | 触发方式 | 安全级别 | 适用场景 |
|------|----------|----------|----------|
| suggest（默认） | 初始状态 | 最高 | 不熟悉的项目、敏感操作 |
| allow-all | `/allow-all` 或 `/yolo` | 低 | 信任环境、快速迭代 |
| autopilot | `Shift+Tab`（实验性） | 最低 | 自主完成复杂任务 |

### 细粒度工具权限

```bash
# 允许所有 git 命令，但禁止 git push
copilot --allow-tool='shell(git:*)' --deny-tool='shell(git push)'

# 允许文件编辑
copilot --allow-tool='write'

# 允许 MCP 服务器的所有工具，但禁止某个
copilot --deny-tool='MyMCP(denied_tool)' --allow-tool='MyMCP'

# 仅限特定工具可用
copilot --available-tools='bash,view,grep,glob'

# 排除特定工具
copilot --excluded-tools='browser_navigate,browser_click'
```

### URL 访问控制

```bash
# 允许特定域名
copilot --allow-url=github.com --allow-url=api.example.com

# 禁止特定域名（优先级高于 allow）
copilot --deny-url=malicious-site.com

# 允许所有 URL
copilot --allow-all-urls
```

### 文件路径控制

```bash
# 添加额外允许目录
copilot --add-dir ~/other-project --add-dir /tmp

# 允许所有路径
copilot --allow-all-paths

# 禁止临时目录
copilot --disallow-temp-dir
```

### 重置权限

在交互会话中，使用 `/reset-allowed-tools` 清空已授权的工具列表，恢复逐次确认模式。

---

## 9. 自动驾驶模式

> 实验性功能，需启用 `AUTOPILOT_MODE` 功能标志。

自动驾驶（Autopilot）模式让代理自主持续工作，无需每步确认。

### 启用方式

```bash
# 交互模式中按 Shift+Tab 切换
# 或命令行启动
copilot --autopilot

# 限制最大持续次数
copilot --autopilot --max-autopilot-continues 20
```

### 工作方式

启用后，代理会：
1. 分析任务，制定计划
2. 自动执行工具调用（无需确认）
3. 持续迭代直到任务完成或达到最大次数
4. 遇到需要人工决策的情况时停下来询问（除非也禁用了 `--no-ask-user`）

### 完全自主模式

```bash
# 完全自主：不确认、不提问
copilot -p "修复所有 lint 错误" --autopilot --no-ask-user --allow-all
```

---

## 10. /plan 计划模式

> 需启用 `PLAN_COMMAND` 功能标志（通过 `/experimental` 命令）。

`/plan` 命令让代理先制定实现计划，再执行代码修改。

### 使用方式

```
> /plan 重构认证模块，从 JWT 迁移到 OAuth 2.0

代理会生成：
1. 分析当前 JWT 实现的文件和依赖
2. 设计 OAuth 2.0 认证流程
3. 列出需要修改的文件清单
4. 说明每个文件的具体改动
5. 指出潜在的风险和向后兼容性问题
```

计划确认后，代理按计划逐步执行，每步完成后报告进度。

---

## 11. 浏览器自动化

Copilot CLI 集成了 21 个基于 Playwright 的浏览器工具，支持完整的无头浏览器自动化。

### 首次使用

需要先安装浏览器：

```
> 安装浏览器（代理会自动调用 browser_install）
```

### 典型工作流

```
> 打开 http://localhost:3000 并截图
> 填写登录表单，用户名 admin，密码 test123
> 点击 "提交" 按钮
> 检查页面上是否显示 "登录成功"
```

### 可用的浏览器工具（21 个）

| 工具 | 说明 |
|------|------|
| `browser_navigate` | 导航到 URL |
| `browser_snapshot` | 获取页面可访问性树（比截图更高效） |
| `browser_take_screenshot` | 页面截图 |
| `browser_click` | 点击元素 |
| `browser_fill_form` | 填写表单 |
| `browser_type` | 输入文本 |
| `browser_press_key` | 模拟按键 |
| `browser_select_option` | 选择下拉选项 |
| `browser_hover` | 悬停 |
| `browser_drag` | 拖拽 |
| `browser_evaluate` | 执行 JavaScript |
| `browser_console_messages` | 获取控制台消息 |
| `browser_network_requests` | 获取网络请求 |
| `browser_file_upload` | 上传文件 |
| `browser_handle_dialog` | 处理对话框 |
| `browser_navigate_back` | 后退 |
| `browser_resize` | 调整视口 |
| `browser_tabs` | 管理标签页 |
| `browser_wait_for` | 等待条件 |
| `browser_install` | 安装浏览器 |
| `browser_close` | 关闭浏览器 |

### 实用场景

- 前端功能测试和调试
- 截图对比 UI 变更
- 自动化表单填写和提交
- 检查 API 返回的页面渲染结果

---

## 12. GitHub 集成

Copilot CLI 内置 48+ 个 GitHub 平台工具，通过 GitHub API 提供深度集成。

### Actions 与 Workflows（12 个工具）

```
> 列出最近失败的 CI 运行
> 获取 workflow run #1234 的日志
> 分析上次构建失败的原因
> 手动触发 deploy 工作流
```

主要工具：`list_workflow_runs`、`get_workflow_logs`、`get_job_logs`、`summarize_job_log_failures`、`actions_run_trigger`

### Pull Requests（7 个工具）

```
> 获取 PR #42 的详细信息
> 查看 PR #42 的文件变更
> 列出所有等待审查的 PR
> 搜索包含 "auth" 关键词的 PR
```

主要工具：`get_pull_request`、`get_pull_request_files`、`list_pull_requests`、`search_pull_requests`

### Issues（3 个工具）

```
> 读取 Issue #100 的详细内容
> 列出所有标记为 bug 的 Issue
> 搜索与内存泄漏相关的 Issue
```

### 安全扫描（4 个工具）

```
> 列出仓库的代码扫描告警
> 查看密钥扫描告警详情
> 有没有高危安全漏洞？
```

主要工具：`list_code_scanning_alerts`、`get_code_scanning_alert`、`list_secret_scanning_alerts`、`get_secret_scanning_alert`

### 其他 GitHub 工具

- **Git 对象（5 个）：** 查看 commit、分支、标签
- **文件与搜索（4 个）：** 跨仓库代码搜索、获取远程文件内容
- **设计系统（12 个）：** GitHub Primer 组件、图标、设计令牌查询

---

## 13. /delegate 委派

> 需启用 `CCA_DELEGATE` 功能标志。

`/delegate` 命令可以将任务委派给远程子代理执行，类似 GitHub Copilot coding agent 在云端创建 PR。

```
> /delegate 创建一个 PR，修复 Issue #42 中描述的 bug
> /delegate 给 README 添加安装说明
```

子代理在独立上下文中工作，完成后返回结果（如 PR 链接）。

---

## 14. 费用管理

### Premium Requests 机制

Copilot CLI 使用 GitHub Copilot 的 premium request 配额。不同模型消耗不同倍率。

| 模型 | 倍率 | 说明 |
|------|------|------|
| gpt-5-mini | 0x | **免费**，不消耗配额 |
| gpt-4.1 | 0x | **免费**，不消耗配额 |
| gpt-5.2-codex | 1x | 标准消耗 |
| claude-sonnet-4.5 | 1x | 标准消耗 |
| claude-opus-4.5 | 3x | 高消耗 |
| gemini-3-pro | 1x | 标准消耗 |

### 省钱策略

1. **日常使用免费模型：** `copilot --model gpt-5-mini` 零消耗
2. **查看用量：** `/usage` 命令查看当前配额消耗
3. **用 explore/task 代理：** 它们使用 claude-haiku-4.5，消耗低
4. **压缩上下文：** `/compact` 减少 token 消耗
5. **只在关键时刻用高倍率模型：** claude-opus-4.5（3x）留给复杂任务

### 设置默认免费模型

```bash
# 在 shell 配置文件中添加
export COPILOT_MODEL=gpt-5-mini
```

---

## 15. 实用技巧

### /compact -- 压缩上下文

长对话后 token 快耗尽时，使用 `/compact` 压缩上下文窗口，保留关键信息丢弃冗余。Copilot CLI 还支持自动后台压缩（无限会话功能），到达阈值时自动触发。

### /context -- 查看上下文

`/context` 显示当前加载的所有内容：系统提示、自定义指令、已读取的文件等。调试提示词问题时很有用。

### /skills -- 查看可用工具

`/skills` 列出当前所有可用的工具和技能，包括核心工具、浏览器工具、GitHub 工具和 MCP 工具。

### 自定义代理（.agent.md）

在 `.github/` 下创建 `.agent.md` 文件，定义项目特定的代理角色：

```markdown
# .github/db-migration.agent.md
你是数据库迁移专家。当用户需要修改数据库 schema 时：
1. 生成 migration 文件
2. 更新 ORM 模型
3. 编写回滚脚本
4. 运行迁移测试
```

### 非交互式脚本集成

```bash
# CI/CD 中使用
copilot -p "运行 lint 并修复所有可自动修复的问题" \
  --allow-all --silent --output-format json

# 静默模式只输出代理回复
copilot -p "列出所有 TODO" -s
```

### 环境变量速查

| 变量 | 说明 |
|------|------|
| `COPILOT_MODEL` | 默认模型 |
| `COPILOT_AGENT_MODEL` | 子代理模型 |
| `COPILOT_MCP_JSON` | MCP 配置文件路径 |
| `COPILOT_ALLOW_ALL` | 等同 `--allow-all-tools` |
| `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` | 额外指令目录 |
| `GH_TOKEN` / `GITHUB_TOKEN` | GitHub 认证令牌 |
| `COPILOT_FIREWALL_ENABLED` | 启用网络防火墙 |
| `COPILOT_ENABLE_ALT_PROVIDERS` | 启用第三方模型 |

### 功能标志管理

通过 `/experimental` 命令启用实验性功能：

| 标志 | 控制范围 |
|------|----------|
| `CUSTOM_AGENTS` | 自定义代理加载 |
| `CCA_DELEGATE` | `/delegate` 命令 |
| `PLAN_COMMAND` | `/plan` 命令 |
| `PLUGIN_COMMAND` | `/plugin` 命令 |
| `AUTOPILOT_MODE` | 自动驾驶模式 |
| `LSP_TOOLS` | LSP 集成 |
| `CONTINUITY` | 跨终端会话恢复 |

---

## 16. 常见问题

### Q: Copilot CLI 和 GitHub Copilot VS Code 扩展有什么区别？

Copilot CLI 是终端原生的 AI 代理，拥有完整的文件编辑、Shell 执行、浏览器自动化能力。VS Code 扩展主要在编辑器内提供补全和内联聊天。CLI 更适合复杂的多步骤任务。

### Q: 可以免费使用吗？

可以。使用 gpt-5-mini 或 gpt-4.1 模型时不消耗 premium request 配额（0x 倍率）。但需要 GitHub 账户和 Copilot 订阅。

### Q: 如何在 CI/CD 中使用？

使用非交互式模式配合 PAT 认证：

```bash
export GH_TOKEN=${{ secrets.COPILOT_TOKEN }}
copilot -p "运行测试" --allow-all --silent --no-auto-update
```

### Q: 支持哪些操作系统？

macOS、Linux、Windows。原生二进制分别为 `copilot-darwin-arm64`、`copilot-linux-x64`、`copilot-win32-x64` 等。

### Q: 自定义指令文件用哪个格式？

推荐使用 `AGENTS.md`（Copilot CLI 原生格式）。如果你的项目已有 `CLAUDE.md` 或 `GEMINI.md`，Copilot CLI 也会自动读取。

### Q: 如何查看 token 消耗？

使用 `/usage` 命令查看当前会话和总体的 premium request 消耗。

### Q: 如何调试代理行为？

```bash
# 查看详细日志
copilot --log-level debug

# 查看日志文件
ls ~/.copilot/logs/
```

---

## 17. 深度文档链接

### 本项目分析文档

| 文档 | 内容 |
|------|------|
| [01-概述](../tools/copilot-cli/01-overview.md) | 核心功能、安装、模型、定价 |
| [02-命令与工具](../tools/copilot-cli/02-commands.md) | 34 命令 + 67 工具 + 3 代理详解 |
| [03-技术架构](../tools/copilot-cli/03-architecture.md) | SEA 反编译、系统提示词、运行时分析 |
| [EVIDENCE.md](../tools/copilot-cli/EVIDENCE.md) | 原始证据（--help 输出、代理 YAML、二进制分析） |

### 官方资源

- [GitHub Copilot CLI 仓库](https://github.com/github/copilot-cli)
- [官方文档](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [Premium Requests 说明](https://docs.github.com/copilot/managing-copilot/monitoring-usage-and-entitlements/about-premium-requests)
- [Copilot 订阅计划](https://github.com/features/copilot/plans)
