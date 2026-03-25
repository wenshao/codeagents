# 2. Copilot CLI 命令、工具与代理详解（v0.0.403 源码分析）

本章基于 `@anthropic-ai/claude-code@0.0.403` npm 包源码逆向分析，完整记录所有斜杠命令、内置工具、浏览器工具、GitHub 平台工具、内置代理定义及自定义指令加载机制。

---

## 斜杠命令（38 个，含别名）

源码中斜杠命令在 `commands/` 模块注册，每个命令对应独立处理函数。部分命令受功能标志（feature flag）门控，未启用时不可见。

| # | 命令 | 别名 | 类别 | 说明 |
|---|------|------|------|------|
| 1 | `/init` | — | 项目 | 初始化项目配置，生成 `AGENTS.md` 或 `.github/copilot-instructions.md` |
| 2 | `/allow-all` | `/yolo` | 权限 | 允许所有工具执行，跳过逐次确认弹窗 |
| 3 | `/clear` | `/new` | 会话 | 清除当前对话历史，重置上下文窗口 |
| 4 | `/cwd` | `/cd` | 导航 | 切换当前工作目录（CWD），影响所有文件操作的相对路径解析 |
| 5 | `/exit` | `/quit` | 系统 | 退出 Copilot CLI 进程 |
| 6 | `/model` | `/models` | 模型 | 列出可用模型或切换当前模型（等价于 `COPILOT_MODEL` 环境变量） |
| 7 | `/add-dir` | — | 导航 | 添加额外工作目录到允许列表，代理可读写该目录下的文件 |
| 8 | `/agent` | — | 代理 | 调用内置代理（`/agent explore`、`/agent task`），传递任务描述 |
| 9 | `/compact` | — | 上下文 | 压缩对话上下文窗口，保留关键信息丢弃冗余，缓解 token 上限 |
| 10 | `/context` | — | 上下文 | 查看当前上下文内容，包括已加载文件、系统提示、自定义指令等 |
| 11 | `/experimental` | — | 系统 | 启用或查看实验性功能标志（feature flags） |
| 12 | `/diff` | — | 代码 | 查看当前工作区的 Git 差异（实验性，需 feature flag） |
| 13 | `/feedback` | — | 系统 | 提交保密反馈调查，数据发送到 GitHub 反馈通道 |
| 14 | `/ide` | — | 集成 | IDE 集成控制（实验性），用于与 VS Code 等编辑器交互 |
| 15 | `/help` | — | 系统 | 显示所有可用命令的帮助信息 |
| 16 | `/list-dirs` | — | 导航 | 列出所有已添加的工作目录 |
| 17 | `/login` | — | 认证 | GitHub 账户认证登录，支持 OAuth 设备流和 PAT |
| 18 | `/logout` | — | 认证 | 退出 GitHub 账户，清除本地认证凭据 |
| 19 | `/mcp` | — | 扩展 | 管理 MCP（Model Context Protocol）服务器，查看/添加/移除 |
| 20 | `/plan` | — | 代理 | 创建执行计划，拆解复杂任务为步骤（需 `PLAN_COMMAND` 功能标志） |
| 21 | `/review` | — | 代理 | 快捷调用 `code-review` 内置代理审查代码变更 |
| 22 | `/reset-allowed-tools` | — | 权限 | 重置工具允许列表，恢复到默认的逐次确认模式 |
| 23 | `/session` | — | 会话 | 管理会话，查看会话 ID、元数据 |
| 24 | `/skills` | — | 工具 | 查看当前可用的所有工具/技能列表 |
| 25 | `/plugin` | — | 扩展 | 管理插件（需 `PLUGIN_COMMAND` 功能标志） |
| 26 | `/terminal-setup` | — | 系统 | 配置终端集成，设置 shell 钩子以获取更好的上下文感知 |
| 27 | `/theme` | — | 系统 | 切换颜色主题（暗色/亮色/自定义） |
| 28 | `/usage` | — | 系统 | 查看当前使用量、配额消耗和 premium 请求余量 |
| 29 | `/user` | — | 系统 | 查看当前已认证的 GitHub 用户信息 |
| 30 | `/share` | — | 会话 | 分享当前对话，生成可访问的链接 |
| 31 | `/delegate` | — | 代理 | 委派任务给子代理执行（需 `CCA_DELEGATE` 功能标志） |
| 32 | `/rename` | — | 会话 | 重命名当前会话的显示名称 |
| 33 | `/resume` | — | 会话 | 恢复之前中断或保存的会话 |
| 34 | `/lsp` | — | 集成 | 查看已配置的 LSP（Language Server Protocol）服务器连接状态 |

> **别名统计：** `/yolo` → `/allow-all`、`/new` → `/clear`、`/cd` → `/cwd`、`/quit` → `/exit`、`/models` → `/model`，共 5 组别名，总计 34 个独立命令 + 5 个别名 = 39 个入口（源码中按命令名去重后为 34 个独立处理器）。

### 功能标志门控命令

以下命令需要通过 `/experimental` 启用对应的 feature flag 后才可使用：

| 命令 | 所需功能标志 | 说明 |
|------|-------------|------|
| `/diff` | 实验性标记 | 工作区差异查看 |
| `/ide` | 实验性标记 | IDE 集成 |
| `/plan` | `PLAN_COMMAND` | 任务规划 |
| `/plugin` | `PLUGIN_COMMAND` | 插件管理 |
| `/delegate` | `CCA_DELEGATE` | 子代理委派 |

---

## 核心工具（12 个）

核心工具是 Copilot CLI 执行代码操作的基础能力集，在 `tools/` 模块中定义。所有工具通过统一的 tool-calling 协议被模型调用。

| # | 工具名 | 参数 | 说明 |
|---|--------|------|------|
| 1 | `bash` | `command`, `timeout?` | 执行任意 shell 命令，支持超时控制；沙箱模式下受限 |
| 2 | `create` | `file_path`, `content` | 创建新文件，写入完整内容；若文件已存在则覆盖 |
| 3 | `edit` | `file_path`, `old_string`, `new_string` | 基于精确字符串匹配的差异编辑，替换 `old_string` 为 `new_string` |
| 4 | `replace` | `file_path`, `content` | 完整替换文件内容，等价于 create 但语义上用于已有文件 |
| 5 | `view` | `file_path`, `offset?`, `limit?` | 查看文件内容，支持行号偏移和行数限制，用于大文件分段读取 |
| 6 | `glob` | `pattern`, `path?` | 按 glob 模式匹配搜索文件名（如 `**/*.ts`），返回匹配路径列表 |
| 7 | `grep` | `pattern`, `path?`, `include?` | 按正则表达式搜索文件内容，支持文件类型过滤 |
| 8 | `search` | `query`, `path?` | 语义搜索，基于嵌入向量在代码库中查找相关代码片段 |
| 9 | `fetch` | `url` | 获取 URL 内容，支持网页和 API 端点，返回文本内容 |
| 10 | `git_apply_patch` | `patch` | 应用 Git 格式的补丁（unified diff），用于批量文件修改 |
| 11 | `search_code_subagent` | `query` | 启动代码搜索子代理，深度搜索代码库回答复杂查询 |
| 12 | `lsp` | `action`, `params` | LSP 工具，调用语言服务器获取类型信息、定义跳转等（需 `LSP_TOOLS` 标志） |

### 工具执行权限

工具执行受三级权限控制：

1. **suggest 模式（默认）：** 每次工具调用弹窗请求用户确认
2. **allow-all 模式：** `/allow-all` 或 `/yolo` 后跳过所有确认
3. **AUTOPILOT_MODE（实验性）：** 代理自主执行直到任务完成，通过 `Shift+Tab` 切换

---

## 浏览器工具（21 个，基于 Playwright）

浏览器工具通过集成 Playwright 提供完整的无头浏览器自动化能力。首次使用前需通过 `browser_install` 安装浏览器二进制文件。

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `browser_click` | 点击页面元素，通过选择器或可访问性标签定位 |
| 2 | `browser_close` | 关闭浏览器实例，释放资源 |
| 3 | `browser_console_messages` | 获取浏览器控制台消息（log/warn/error） |
| 4 | `browser_drag` | 拖拽页面元素到指定位置 |
| 5 | `browser_evaluate` | 在页面上下文中执行任意 JavaScript 代码 |
| 6 | `browser_file_upload` | 上传文件到文件选择器元素 |
| 7 | `browser_fill_form` | 填写表单字段，支持输入框、文本区域等 |
| 8 | `browser_handle_dialog` | 处理浏览器原生对话框（alert/confirm/prompt） |
| 9 | `browser_hover` | 悬停在页面元素上，触发 hover 事件 |
| 10 | `browser_install` | 安装 Playwright 管理的浏览器二进制文件 |
| 11 | `browser_navigate` | 导航到指定 URL |
| 12 | `browser_navigate_back` | 后退到上一个页面 |
| 13 | `browser_network_requests` | 获取页面网络请求记录（URL、状态码、时间） |
| 14 | `browser_press_key` | 模拟键盘按键（Enter、Tab、快捷键等） |
| 15 | `browser_resize` | 调整浏览器视口大小 |
| 16 | `browser_select_option` | 选择下拉菜单中的选项 |
| 17 | `browser_snapshot` | 获取页面可访问性树快照，用于理解页面结构 |
| 18 | `browser_tabs` | 列出和管理浏览器标签页 |
| 19 | `browser_take_screenshot` | 截取页面截图，返回图像用于视觉分析 |
| 20 | `browser_type` | 在聚焦元素中输入文本 |
| 21 | `browser_wait_for` | 等待页面条件满足（元素出现、网络空闲、超时等） |

### 浏览器工具使用模式

典型工作流：`browser_install` → `browser_navigate` → `browser_snapshot` → 交互操作 → `browser_close`。`browser_snapshot` 返回可访问性树而非截图，消耗更少 token 且更适合 LLM 解析页面结构。

---

## GitHub 平台工具（48+ 个）

GitHub 平台工具通过 GitHub API 提供与仓库、PR、Issue、Actions 等资源的深度集成。这些工具在源码中按功能域分组注册。

### Actions 与 Workflows（12 个）

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `actions_get` | 获取指定 Action 的详细信息 |
| 2 | `actions_list` | 列出仓库可用的 Actions |
| 3 | `actions_run_trigger` | 手动触发 Action 运行（workflow_dispatch） |
| 4 | `get_workflow` | 获取工作流定义详情 |
| 5 | `get_workflow_run` | 获取指定工作流运行的状态和元数据 |
| 6 | `get_workflow_logs` | 获取工作流运行的完整日志 |
| 7 | `get_job_logs` | 获取单个作业的日志输出 |
| 8 | `list_workflows` | 列出仓库中所有工作流 |
| 9 | `list_workflow_runs` | 列出工作流的运行历史 |
| 10 | `list_workflow_jobs` | 列出指定运行中的所有作业 |
| 11 | `list_workflow_run_artifacts` | 列出运行产生的构建产物 |
| 12 | `summarize_job_log_failures` | 分析作业日志，提取失败原因和错误摘要 |

### Pull Requests（7 个）

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `get_pull_request` | 获取 PR 详细信息（标题、描述、状态、标签等） |
| 2 | `get_pull_request_comments` | 获取 PR 的评论和讨论 |
| 3 | `get_pull_request_files` | 获取 PR 的文件变更列表和差异 |
| 4 | `get_pull_request_reviews` | 获取 PR 的审查记录 |
| 5 | `get_pull_request_status` | 获取 PR 的 CI 检查状态和合并就绪状态 |
| 6 | `list_pull_requests` | 列出仓库的 PR（支持状态过滤） |
| 7 | `search_pull_requests` | 搜索 PR（支持复杂查询语法） |

### Issues（3 个）

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `issue_read` | 读取 Issue 详细信息（标题、描述、评论、标签等） |
| 2 | `list_issues` | 列出仓库 Issues（支持状态、标签过滤） |
| 3 | `search_issues` | 搜索 Issues（支持 GitHub 搜索语法） |

### 代码扫描与安全（4 个）

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `get_code_scanning_alert` | 获取指定代码扫描告警的详情 |
| 2 | `list_code_scanning_alerts` | 列出仓库的代码扫描告警 |
| 3 | `get_secret_scanning_alert` | 获取指定密钥扫描告警的详情 |
| 4 | `list_secret_scanning_alerts` | 列出仓库的密钥扫描告警 |

### Git 对象（5 个）

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `get_commit` | 获取提交详情（作者、消息、变更文件） |
| 2 | `list_branches` | 列出仓库分支 |
| 3 | `list_commits` | 列出提交历史 |
| 4 | `list_tags` | 列出仓库标签 |
| 5 | `get_tag` | 获取标签详情 |

### 文件与搜索（4 个）

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `get_file_contents` | 通过 API 获取仓库文件内容（无需本地克隆） |
| 2 | `search_code` | GitHub 代码搜索（跨仓库全文搜索） |
| 3 | `search_repositories` | 搜索 GitHub 仓库 |
| 4 | `search_users` | 搜索 GitHub 用户 |

### GitHub Design（Primer 设计系统）（11 个）

这组工具用于查询 GitHub Primer 设计系统的组件、图标、模式和设计令牌：

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `get_color_usage` | 获取颜色使用指南 |
| 2 | `get_component` | 获取组件定义和属性 |
| 3 | `get_component_accessibility` | 获取组件的可访问性指南 |
| 4 | `get_component_examples` | 获取组件使用示例 |
| 5 | `get_component_usage` | 获取组件使用规范 |
| 6 | `get_icon` | 获取图标信息 |
| 7 | `get_pattern` | 获取设计模式定义 |
| 8 | `get_typography_usage` | 获取排版使用指南 |
| 9 | `list_components` | 列出所有 Primer 组件 |
| 10 | `list_icons` | 列出所有可用图标 |
| 11 | `list_patterns` | 列出所有设计模式 |
| 12 | `list_tokens` | 列出所有设计令牌 |

### Copilot 与实用工具（6 个）

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | `get_copilot_space` | 获取 Copilot 工作空间信息 |
| 2 | `get_selection` | 获取当前编辑器选择的代码（IDE 集成时） |
| 3 | `list_agents` | 列出可用的代理 |
| 4 | `get_me` | 获取当前认证用户信息 |
| 5 | `get_current_time` | 获取当前时间 |
| 6 | `get_diagnostics` | 获取系统诊断信息 |
| 7 | `convert_time` | 时区时间转换 |

---

## 内置代理（3 个 YAML 定义）

内置代理在安装包的 `definitions/` 目录下以 `.agent.yaml` 格式定义。每个代理指定独立的模型、工具权限和系统提示。

### code-review

```yaml
model: claude-sonnet-4.5
tools: "*"   # 全部工具
```

- **触发方式：** `/review` 命令
- **设计目标：** 高信噪比代码审查
- **系统提示核心约束：**
  - 禁止修改代码，只做只读分析
  - 只报告真正重要的问题：bugs、安全漏洞、逻辑错误、竞态条件（race conditions）、内存泄漏（memory leaks）、缺失的错误处理（missing error handling）、破坏性 API 变更（breaking API changes）、性能问题（performance issues）
  - 不评论代码风格、格式、命名等主观偏好
  - 对每个发现的问题必须说明具体风险和影响

### explore

```yaml
model: claude-haiku-4.5
tools: [grep, glob, view, lsp]   # 仅限只读探索工具
```

- **触发方式：** `/agent explore <问题描述>`
- **设计目标：** 快速代码库探索和问答
- **系统提示核心约束：**
  - 回答控制在 300 字以内
  - 最大化并行工具调用（同时发出多个 grep/glob 请求）
  - 不修改任何文件，仅读取和分析
  - 优先使用 grep/glob 定位代码，view 查看细节

### task

```yaml
model: claude-haiku-4.5
tools: "*"   # 全部工具
```

- **触发方式：** `/agent task <任务描述>`
- **设计目标：** 执行具体的开发任务（测试、构建、lint 等）
- **系统提示核心约束：**
  - 成功时：返回简短摘要（一两句话）
  - 失败时：返回完整的错误输出和上下文，便于调试
  - 自主运行命令直到任务完成或确认失败

---

## 自定义指令搜索顺序

Copilot CLI 在启动时按以下精确顺序搜索并加载自定义指令文件。先找到的文件优先级更高，所有找到的文件内容会被拼接到系统提示中。

| 优先级 | 文件路径 | 作用域 | 兼容性 |
|--------|----------|--------|--------|
| 1 | `CLAUDE.md`（项目根目录及父目录） | 项目级 | 兼容 Claude Code |
| 2 | `GEMINI.md`（项目根目录） | 项目级 | 兼容 Gemini CLI |
| 3 | `AGENTS.md`（项目根目录） | 项目级 | Copilot CLI 原生 |
| 4 | `.github/instructions/**/*.instructions.md` | 仓库级 | GitHub 规范 |
| 5 | `.github/copilot-instructions.md` | 仓库级 | Copilot 专用 |
| 6 | `~/.copilot/copilot-instructions.md` | 用户级（全局） | 所有项目通用 |
| 7 | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` 环境变量 | 自定义目录 | 额外指令目录 |

> **跨工具兼容性：** Copilot CLI 同时读取 `CLAUDE.md` 和 `GEMINI.md`，意味着为 Claude Code 或 Gemini CLI 编写的项目指令文件可以直接被 Copilot CLI 复用，无需额外适配。

### 自定义代理定义

| 文件路径 | 说明 |
|----------|------|
| `.github/*.agent.md` | 仓库级自定义代理（Markdown 格式） |
| `.claude/agents/*.agent.md` | 兼容 Claude Code 的代理定义 |

自定义代理需启用 `CUSTOM_AGENTS` 功能标志（通过 `/experimental` 命令）。

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `COPILOT_MODEL` | 指定默认模型（如 `claude-sonnet-4.5`） |
| `COPILOT_AGENT_MODEL` | 指定子代理使用的模型 |
| `COPILOT_MCP_JSON` | MCP 服务器配置 JSON 文件路径 |
| `COPILOT_FIREWALL_ENABLED` | 启用网络防火墙（限制出站请求） |
| `COPILOT_ENABLE_ALT_PROVIDERS` | 启用第三方模型提供商（GPT、Gemini 等） |
| `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` | 额外自定义指令目录（逗号分隔路径列表） |
| `GH_TOKEN` / `GITHUB_TOKEN` | GitHub Personal Access Token 认证 |

---

## 权限系统

### 执行模式

| 模式 | 触发方式 | 说明 |
|------|----------|------|
| suggest（默认） | 初始状态 | 每次工具调用弹窗请求用户确认，最安全 |
| allow-all | `/allow-all` 或 `/yolo` | 跳过所有确认，适合信任环境下的高效操作 |
| AUTOPILOT_MODE | `Shift+Tab` 切换 | 实验性，代理自主持续工作直到任务完成或失败 |

### 文件访问控制

- 默认仅允许访问当前工作目录及其子目录
- `/add-dir <路径>` 添加额外允许访问的目录
- `/list-dirs` 查看所有已授权目录
- 工具调用时自动校验路径，拒绝越界访问

### 工具权限列表

- 用户确认工具执行后，该工具被加入允许列表（allowlist），后续同类调用自动通过
- `/reset-allowed-tools` 清空允许列表，恢复逐次确认
- `/skills` 查看当前所有可用工具及其状态

---

## 功能标志（Feature Flags）

通过 `/experimental` 命令管理。启用后存储在本地配置中，跨会话保持。

| 标志 | 控制范围 | 说明 |
|------|----------|------|
| `CUSTOM_AGENTS` | `/agent` + 自定义代理 | 启用 `.agent.md` 自定义代理加载 |
| `CCA_DELEGATE` | `/delegate` 命令 | 启用子代理委派功能 |
| `CONTINUITY` | 会话系统 | 会话持续性，支持跨终端恢复 |
| `PLAN_COMMAND` | `/plan` 命令 | 启用任务规划功能 |
| `PLUGIN_COMMAND` | `/plugin` 命令 | 启用插件管理功能 |
| `LSP_TOOLS` | `lsp` 工具 + `/lsp` 命令 | 启用 Language Server Protocol 集成 |
| `AUTOPILOT_MODE` | 执行模式 | 启用自动驾驶模式（`Shift+Tab` 切换） |

---

## 工具数量汇总

| 类别 | 数量 |
|------|------|
| 斜杠命令（含别名） | 38 |
| 核心工具 | 12 |
| 浏览器工具（Playwright） | 21 |
| GitHub 平台工具 | 48+ |
| 内置代理 | 3 |
| **总计工具能力** | **80+ 工具 + 38 命令** |
