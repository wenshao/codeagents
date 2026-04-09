# 2. Copilot CLI 命令系统——开发者参考

> Copilot CLI 共有 34 个独立命令 + 5 组别名、12 个核心工具、21 个浏览器工具、48+ 个 GitHub 平台工具、3 个内置代理。本文分析其命令注册/工具分类/代理定义设计，为 Code Agent 开发者提供命令系统架构参考。
>
> **Qwen Code 对标**：YAML 声明式代理定义、功能标志门控、7 级指令搜索链、code-review 代理的假阳性过滤策略

## 为什么 Copilot CLI 的工具分类值得研究

### 问题定义

CLI Agent 的工具规模存在"膨胀困境"——工具越多，系统提示越长，token 消耗越大，模型选择工具的准确度越低。Copilot CLI 的解法是**分层分域**：

| 层级 | 工具数 | 加载时机 | 场景 |
|------|--------|---------|------|
| 核心工具 | 12 个 | 始终可用 | 基础编码操作 |
| 浏览器工具 | 21 个 | 按需加载（首次需 `browser_install`） | 前端测试/网页交互 |
| GitHub 平台工具 | 48+ 个 | 通过 MCP 端点按需启用 | GitHub 工作流集成 |
| 代理 | 3 个 | 用户显式调用 | 专用任务（review/explore/task） |

**Qwen Code 对标**：Qwen Code 的 ~30 个工具全量加载到系统提示。如果未来扩展到 80+ 个工具，可参考 Copilot 的分层策略，或参考 Claude Code 的 ToolSearch 延迟加载方案。

### 竞品命令系统对比

| Agent | 命令数 | 工具数 | 代理数 | 扩展机制 |
|-------|--------|--------|--------|---------|
| **Copilot CLI** | 34 | 67+ | 3 | MCP + Plugin + 自定义代理 |
| **Claude Code** | ~79 | 42 | Coordinator/Swarm | Skill + Plugin |
| **Gemini CLI** | ~30 | ~20 | 无 | TOML + Skill |
| **Qwen Code** | ~40 | ~30 | Arena + Agent Team | BundledSkillLoader |

---

## 一、斜杠命令（34 个独立命令 + 5 组别名）

源码中斜杠命令在 `commands/` 模块注册，每个命令对应独立处理函数。部分命令受功能标志（feature flag）门控。

### 1.1 命令分类

| 类别 | 命令 | 数量 | 开发者参考 |
|------|------|------|-----------|
| **会话管理** | `/clear`(`/new`)、`/compact`、`/context`、`/session`、`/resume`、`/rename`、`/share` | 7 | 会话生命周期管理 |
| **权限控制** | `/allow-all`(`/yolo`)、`/reset-allowed-tools` | 2 | 渐进式信任模型 |
| **导航** | `/cwd`(`/cd`)、`/add-dir`、`/list-dirs` | 3 | 工作目录管理 |
| **代理调用** | `/agent`、`/review`、`/delegate`、`/plan` | 4 | 内置代理入口 |
| **模型与配置** | `/model`(`/models`)、`/experimental`、`/theme` | 3 | 运行时配置 |
| **扩展** | `/mcp`、`/plugin`、`/lsp`、`/skills` | 4 | MCP/LSP/插件管理 |
| **认证** | `/login`、`/logout`、`/user` | 3 | GitHub OAuth |
| **系统** | `/exit`(`/quit`)、`/help`、`/feedback`、`/terminal-setup`、`/usage`、`/init`、`/ide`、`/diff` | 8 | 基础设施 |

### 1.2 功能标志门控命令

以下命令需通过 `/experimental` 启用对应 feature flag 后才可见：

| 命令 | 功能标志 | 说明 | Qwen Code 启示 |
|------|---------|------|----------------|
| `/plan` | `PLAN_COMMAND` | 任务规划拆解 | Qwen Code 可参考此模式管理实验性命令 |
| `/plugin` | `PLUGIN_COMMAND` | 插件管理 | 插件系统的渐进式发布 |
| `/delegate` | `CCA_DELEGATE` | 子代理委派 | 多 Agent 委派的门控 |
| `/diff` | 实验性标记 | 工作区差异查看 | — |
| `/ide` | 实验性标记 | IDE 集成 | — |

**开发者参考**：Copilot CLI 的 7 个功能标志（`CUSTOM_AGENTS`、`CCA_DELEGATE`、`CONTINUITY`、`PLAN_COMMAND`、`PLUGIN_COMMAND`、`LSP_TOOLS`、`AUTOPILOT_MODE`）存储在本地配置中，跨会话保持。与 Claude Code 的 22 个 build-time Feature Flag + GrowthBook 远程灰度不同，Copilot 的标志完全由用户本地控制——更简单但缺乏远程灰度能力。

---

## 二、核心工具（12 个）

核心工具是 Copilot CLI 执行代码操作的基础能力集。

### 2.1 工具清单与对比

| # | 工具名 | 参数 | Claude Code 对标 | Qwen Code 对标 |
|---|--------|------|-----------------|----------------|
| 1 | `bash` | `command`, `timeout?` | Bash 工具（相同） | Bash 工具（相同） |
| 2 | `create` | `file_path`, `content` | Write 工具 | Write 工具 |
| 3 | `edit` | `file_path`, `old_string`, `new_string` | Edit 工具（相同接口） | Edit 工具（相同接口） |
| 4 | `replace` | `file_path`, `content` | Write 工具（覆盖模式） | Write 工具 |
| 5 | `view` | `file_path`, `offset?`, `limit?` | Read 工具 | Read 工具 |
| 6 | `glob` | `pattern`, `path?` | Glob 工具（相同） | Glob 工具（相同） |
| 7 | `grep` | `pattern`, `path?`, `include?` | Grep 工具（相同） | Grep 工具（相同） |
| 8 | `search` | `query`, `path?` | 无直接对标（语义搜索） | 无 |
| 9 | `fetch` | `url` | WebFetch 工具 | WebFetch 工具 |
| 10 | `git_apply_patch` | `patch` | 无（通过 Bash git apply） | 无 |
| 11 | `search_code_subagent` | `query` | Agent 工具（子代理模式） | 无 |
| 12 | `lsp` | `action`, `params` | LSP 客户端（内置） | LSP 支持 |

**关键差异分析**：

- **`search`（语义搜索）**：Copilot CLI 内置基于嵌入向量的语义搜索，Claude Code 和 Qwen Code 均缺少此能力。这允许自然语言查询代码库（如"处理用户认证的代码"），而非依赖精确的 grep 模式。
- **`search_code_subagent`**：启动独立的代码搜索子代理，深度搜索代码库回答复杂查询。类似 Claude Code 的 Agent 工具 fork 模式。
- **`git_apply_patch`**：直接接受 unified diff 格式补丁，比 Claude Code 通过 Bash 调用 `git apply` 更安全（参数可校验）。

### 2.2 工具权限模型

| 模式 | 触发方式 | 行为 | Qwen Code 对标 |
|------|---------|------|----------------|
| suggest（默认） | 初始状态 | 每次工具调用弹窗确认 | 类似 Qwen Code 默认行为 |
| allow-all | `/allow-all` 或 `/yolo` | 跳过所有确认 | 类似 `--dangerously-skip-permissions` |
| AUTOPILOT_MODE | `Shift+Tab` 切换 | 代理自主持续执行 | 无对标（Qwen Code 无此模式） |

**渐进式信任**是一个值得注意的设计——用户不需要在"全手动"和"全自动"之间二选一，而是有中间态。`Shift+Tab` 热键切换 Autopilot 特别方便，不打断工作流。

---

## 三、浏览器工具（21 个，基于 Playwright）

浏览器工具是 Copilot CLI 的差异化能力之一。基于 Playwright 集成，提供完整的无头浏览器自动化。

### 3.1 工具清单

| 类别 | 工具 | 数量 |
|------|------|------|
| **导航** | `browser_navigate`, `browser_navigate_back`, `browser_close` | 3 |
| **交互** | `browser_click`, `browser_drag`, `browser_hover`, `browser_fill_form`, `browser_select_option`, `browser_type`, `browser_press_key`, `browser_file_upload`, `browser_handle_dialog` | 9 |
| **观察** | `browser_snapshot`, `browser_take_screenshot`, `browser_console_messages`, `browser_network_requests`, `browser_tabs` | 5 |
| **控制** | `browser_evaluate`, `browser_resize`, `browser_wait_for`, `browser_install` | 4 |

### 3.2 设计决策分析

**`browser_snapshot` vs `browser_take_screenshot`**：Copilot CLI 优先使用可访问性树快照（`browser_snapshot`）而非截图，因为文本数据比图像消耗更少 token 且更适合 LLM 解析。这与 Claude Code 的视觉能力形成对比——Claude Code 可以直接理解截图，但 Copilot 的做法在 token 效率上更优。

**Qwen Code 对标**：Qwen Code 目前没有浏览器自动化能力。如需补齐，有两种路径：
1. **内置 Playwright 集成**（Copilot 方案）——工具完整但增加二进制大小
2. **MCP 服务器**——通过外部 MCP 服务器提供浏览器能力，解耦且灵活

---

## 四、GitHub 平台工具（48+ 个）

GitHub 平台工具是 Copilot CLI 的核心竞争壁垒，按功能域分组：

| 功能域 | 工具数 | 代表工具 | Qwen Code 补齐方式 |
|--------|--------|---------|-------------------|
| Actions & Workflows | 12 | `actions_run_trigger`, `get_workflow_logs`, `summarize_job_log_failures` | GitHub MCP 服务器 |
| Pull Requests | 7 | `get_pull_request`, `get_pull_request_files`, `search_pull_requests` | `gh` CLI 或 GitHub MCP |
| Issues | 3 | `issue_read`, `list_issues`, `search_issues` | `gh` CLI |
| 代码扫描与安全 | 4 | `list_code_scanning_alerts`, `list_secret_scanning_alerts` | GitHub API |
| Git 对象 | 5 | `get_commit`, `list_branches`, `list_commits` | 本地 git 命令 |
| 文件与搜索 | 4 | `search_code`（跨仓库全文搜索）, `search_repositories` | GitHub API |
| Primer 设计系统 | 12 | `get_component`, `list_icons`, `list_tokens` | 不需要（GitHub 内部） |
| 实用工具 | 7 | `get_me`, `get_copilot_space`, `list_agents` | — |

**开发者参考**：Copilot CLI 的 GitHub 工具不是通过 Bash 调用 `gh` CLI 实现的，而是直接通过 API 层（`api.github.com` + `api.githubcopilot.com`）调用。这样做的好处是：
1. 参数校验更严格（Zod/JSON Schema 定义）
2. 权限控制更精细（不依赖 shell 环境）
3. 输出格式可控（直接结构化，无需解析命令输出）

而 Claude Code 的 `/review` 则通过 `Bash(gh pr diff:*)` 等受限 Bash 命令实现 GitHub 集成——灵活但安全性较弱。

---

## 五、内置代理系统（3 个 YAML 定义）

### 5.1 架构设计

内置代理在 `definitions/` 目录下以 `.agent.yaml` 格式定义，每个代理指定：
- **模型**：独立于主模型的专用模型
- **工具权限**：`"*"` 或工具白名单
- **系统提示**：通过 `promptParts` 模块化组合

```yaml
# 代理 YAML 定义结构
model: claude-sonnet-4.5
tools: "*"
promptParts:
  includeAISafety: true
  includeToolInstructions: true
  includeParallelToolCalling: true
prompt: |
  <system prompt content>
```

**Qwen Code 对标**：Qwen Code 的 Agent Team 使用代码定义代理。YAML 声明式定义的优势在于：
1. 用户可自定义代理（`.github/*.agent.md`）而无需修改源码
2. 代理定义与执行引擎解耦
3. 模型和工具权限一目了然

### 5.2 code-review 代理——假阳性过滤的设计标杆

| 项目 | 值 |
|------|-----|
| **模型** | `claude-sonnet-4.5`（质量优先） |
| **工具** | `*`（全部，但 prompt 禁止使用 edit/create） |
| **核心原则** | "finding your feedback should feel like finding a $20 bill in your jeans" |

**审查范围（8 个显式维度）**：

| 维度 | 说明 |
|------|------|
| Bugs and logic errors | 代码逻辑缺陷 |
| Security vulnerabilities | 安全漏洞 |
| Race conditions | 竞态条件和并发问题 |
| Memory leaks | 内存泄漏和资源管理 |
| Missing error handling | 缺失的错误处理 |
| Incorrect assumptions | 对数据或状态的错误假设 |
| Breaking API changes | 公共 API 的破坏性变更 |
| Performance issues | 可衡量的性能问题 |

**显式排除的假阳性（8 类禁止评论的内容）**：

| 禁止评论 | 原因 |
|----------|------|
| Style, formatting, naming | 代码风格不是 bug |
| Grammar/spelling | 拼写不影响功能 |
| "Consider doing X" suggestions | 建议不是 bug |
| Minor refactoring | 微重构不紧急 |
| Code organization | 主观偏好 |
| Missing documentation | 文档缺失不是 bug |
| "Best practices" without problems | 不防止实际问题的最佳实践 |
| Anything uncertain | **不确定就不报告** |

**审查流程（4 步）**：
1. **理解变更范围** — `git status` → staged/unstaged/branch diff
2. **理解上下文** — 读取周围代码，理解意图和不变量
3. **验证** — 尝试编译、运行测试
4. **仅报告高置信度问题** — 不确定就不报告

**关键约束**：`You Must NEVER Modify Code` — 所有工具仅用于调查，禁止使用 edit/create。

**Qwen Code 对标**：这套假阳性过滤策略（8 维度 + 8 排除 + 置信度门槛）可直接复用到 Qwen Code 的 `/review` 命令中。Claude Code 的 `/review` 使用更复杂的多代理并行审查 + 置信度评分机制，但 Copilot 的单代理方案更简单且已经很有效。

### 5.3 explore 代理——轻量级代码探索

| 项目 | 值 | 设计意图 |
|------|-----|---------|
| **模型** | `claude-haiku-4.5` | 快速响应优先，降低成本 |
| **工具** | 仅 `grep, glob, view, lsp`（4 个只读工具） | 最小工具集 = 安全 + 快速 |
| **回答限制** | 300 字以内 | 防止上下文膨胀 |
| **并行要求** | 最大化并行工具调用 | 减少往返延迟 |

**Qwen Code 对标**：explore 代理的设计体现了"约束即特性"——通过限制工具集和输出长度，保证了安全性和速度。Qwen Code 可以考虑类似的轻量级问答模式，使用小模型 + 只读工具快速回答代码问题。

### 5.4 task 代理——最小化上下文污染

| 项目 | 值 |
|------|-----|
| **模型** | `claude-haiku-4.5` |
| **工具** | `*`（全部） |

**输出策略**：
- **成功时**：单行摘要（如 "All 247 tests passed"、"Build succeeded in 45s"）
- **失败时**：完整错误输出（堆栈跟踪、编译错误、lint 问题）
- **禁止**：不尝试修复错误、不分析问题、不提建议、不重试
- **超时**：测试/构建 200-300 秒，lint 60 秒

**Qwen Code 对标**：task 代理的"成功时简短、失败时详细"输出策略是一个精巧的设计——它最小化了成功情况下的上下文污染，同时保留了失败情况下的调试信息。这个模式适用于任何 Agent 的子任务执行。

---

## 六、自定义指令搜索顺序（7 级）

Copilot CLI 在启动时按以下精确顺序搜索并加载自定义指令文件：

| 优先级 | 文件路径 | 作用域 | 兼容性 |
|--------|----------|--------|--------|
| 1 | `CLAUDE.md`（项目根目录及父目录） | 项目级 | 兼容 Claude Code |
| 2 | `GEMINI.md`（项目根目录） | 项目级 | 兼容 Gemini CLI |
| 3 | `AGENTS.md`（项目根目录） | 项目级 | Copilot CLI 原生 |
| 4 | `.github/instructions/**/*.instructions.md` | 仓库级 | GitHub 规范 |
| 5 | `.github/copilot-instructions.md` | 仓库级 | Copilot 专用 |
| 6 | `~/.copilot/copilot-instructions.md` | 用户级（全局） | 所有项目通用 |
| 7 | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` 环境变量 | 自定义目录 | 额外指令目录 |

**自定义代理文件路径**：

| 路径 | 说明 |
|------|------|
| `.github/*.agent.md` | 仓库级自定义代理（Markdown 格式） |
| `.claude/agents/*.agent.md` | 兼容 Claude Code 的代理定义 |

> **开发者参考**：Copilot CLI 的跨 Agent 指令兼容是一个降低迁移成本的策略——用户无需为每个 Agent 维护独立的指令文件。Qwen Code 可以考虑类似的兼容策略，优先读取 `QWEN.md`，同时 fallback 到 `CLAUDE.md` / `AGENTS.md`。

---

## 七、CLI 参数系统（57 个参数）

Copilot CLI 的 57 个 CLI 参数按功能域分组，值得关注的设计：

### 7.1 权限参数的粒度设计

| 粒度 | 参数 | 说明 |
|------|------|------|
| 全部允许 | `--allow-all` / `--yolo` | 工具 + 路径 + URL 全部放开 |
| 工具级 | `--allow-all-tools`, `--allow-tool <t>`, `--deny-tool <t>` | 工具粒度的白名单/黑名单 |
| 路径级 | `--allow-all-paths`, `--add-dir <d>` | 文件路径粒度 |
| URL 级 | `--allow-all-urls`, `--allow-url <u>`, `--deny-url <u>` | 网络访问粒度 |
| 敏感变量 | `--secret-env-vars <vars>` | 标记不应暴露的环境变量 |

**Qwen Code 对标**：Copilot CLI 将权限拆分为工具级、路径级、URL 级三个维度，比"全部允许或全部确认"更灵活。特别是 `--secret-env-vars` 标记敏感环境变量的做法，可防止 Agent 意外泄露密钥。

### 7.2 环境变量

| 变量 | 说明 |
|------|------|
| `COPILOT_MODEL` | 指定默认模型 |
| `COPILOT_AGENT_MODEL` | 子代理使用的模型（与主模型可不同） |
| `COPILOT_MCP_JSON` | MCP 服务器配置 |
| `COPILOT_FIREWALL_ENABLED` | 启用网络防火墙 |
| `COPILOT_ENABLE_ALT_PROVIDERS` | 启用第三方模型 |
| `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` | 额外指令目录 |
| `GH_TOKEN` / `GITHUB_TOKEN` | PAT 认证 |

---

## 八、工具数量汇总

| 类别 | 数量 | 与 Claude Code 对比 |
|------|------|-------------------|
| 斜杠命令（独立） | 34 | Claude Code ~79（少 53%） |
| 命令别名 | 5 | Claude Code 有更多别名 |
| 核心工具 | 12 | Claude Code 42（少 71%） |
| 浏览器工具 | 21 | Claude Code 无（Copilot 独有） |
| GitHub 平台工具 | 48+ | Claude Code 无（Copilot 独有） |
| 内置代理 | 3 | Claude Code Coordinator/Swarm |
| **总计工具能力** | **67+ 工具 + 34 命令** | **Claude Code 42 工具 + 79 命令** |

> **数量 vs 质量**：Copilot CLI 的工具总数（67+）远超 Claude Code（42），但大部分来自 GitHub 平台工具（48+）和浏览器工具（21）。如果去除这两类平台特定工具，核心编码工具仅 12 个，少于 Claude Code。数量优势来自平台集成，而非编码能力本身。
