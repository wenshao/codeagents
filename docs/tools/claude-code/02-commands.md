# 2. Claude Code 命令详解（v2.1.81）

> 基于 v2.1.81 二进制分析。Claude Code 共有四种命令类型、约 79 个斜杠命令。本文档逐一说明每个命令的功能、实现方式和使用示例。

---

## 命令类型说明

Claude Code 的斜杠命令按实现方式分为四种类型：

| 类型 | 标识 | 数量 | 执行方式 | 是否调用 LLM |
|------|------|------|----------|-------------|
| **prompt** | `prompt` | 6 个 | 将预设 Prompt 发送给 LLM，LLM 调用工具完成任务 | 是 |
| **local-jsx** | `local-jsx` | ~50 个 | 在本地渲染 React/Ink 终端 UI 组件 | 否 |
| **local** | `local` | ~11 个 | 直接在本地执行逻辑，无 UI 渲染 | 否 |
| **skill** | `skill/plugin` | 若干 | 通过插件系统或 Skill 机制注册的扩展命令 | 视情况 |

**prompt 类型**是最强大的命令——它们构造一段专用 Prompt（包含上下文信息），发送给 Claude 模型，由模型自主调用 Bash、Edit、Read 等工具来完成复杂任务（如提交代码、审查 PR）。

**local-jsx 类型**数量最多，覆盖了配置管理、会话管理、UI 设置等日常操作。它们在终端内渲染交互式 React/Ink 组件（列表选择、表单输入、状态展示等），不消耗 API token。

**local 类型**是最轻量的命令，直接执行本地逻辑（清除历史、压缩上下文、显示成本等），无需 UI 渲染，也不调用 LLM。

**skill 类型**由插件系统或内置 Skill 机制提供，可在运行时动态注册新命令。

---

## prompt 类型命令（6 个）

这 6 个命令的共同特征：将特定上下文和指令组合成 Prompt 发送给 Claude 模型，由模型自主使用工具（Bash、Read、Edit、Grep 等）来完成任务。用户看到的是 LLM 的完整执行过程（包含工具调用）。

---

### /review（`/code-review` 插件）

- **类型：** prompt（内置 Skill） + code-review 插件（多代理编排）
- **功能：** 自动化代码审查，多代理并行审计 + 置信度评分过滤假阳性
- **作者：** Boris Cherny (boris@anthropic.com)，Anthropic 官方插件
- **源码：** [`plugins/code-review/`](https://github.com/anthropics/claude-code/tree/main/plugins/code-review)

**使用示例：**
```bash
# 本地审查（输出到终端）
/code-review

# 审查并发布 PR 内联评论
/code-review --comment
```

**允许的工具**（源码 Frontmatter 限制）：
```
Bash(gh issue view:*), Bash(gh search:*), Bash(gh issue list:*),
Bash(gh pr comment:*), Bash(gh pr diff:*), Bash(gh pr view:*),
Bash(gh pr list:*), mcp__github_inline_comment__create_inline_comment
```

**9 步流水线（源码：`commands/code-review.md`）：**

| 步骤 | 代理 | 模型 | 任务 |
|------|------|------|------|
| 1 | 前置检查 | Haiku | 检查是否应跳过：已关闭/草稿/trivial/已审查。Claude 生成的 PR 仍然审查 |
| 2 | 收集规范 | Haiku | 搜集仓库中所有相关 CLAUDE.md 文件（根目录 + PR 涉及文件的目录） |
| 3 | 变更摘要 | Sonnet | 生成 PR 变更的结构化摘要 |
| 4a | CLAUDE.md 合规 #1 | Sonnet | 审计代码是否违反 CLAUDE.md 规范（仅检查文件路径匹配的 CLAUDE.md） |
| 4b | CLAUDE.md 合规 #2 | Sonnet | 冗余审计（双重检查降低遗漏率） |
| 4c | Bug 扫描 | **Opus** | 只关注 diff 本身，不读额外上下文。只标记重大缺陷 |
| 4d | 安全/逻辑分析 | **Opus** | 分析新增代码中的安全隐患和逻辑错误 |
| 5 | 并行验证 | Opus/Sonnet | 每个标记的问题由独立验证代理确认（Opus 验证 Bug，Sonnet 验证合规） |
| 6 | 过滤 | — | 移除未通过验证的问题 |
| 7 | 输出 | — | 终端输出审查报告；若无 `--comment` 则到此结束 |
| 8 | 评论准备 | — | 内部列出所有计划发布的评论（自检，不公开） |
| 9 | 发布评论 | — | 通过 MCP GitHub 工具发布内联 PR 评论 |

**审查维度（源码明确定义）：**

| 维度 | 检查内容 | 代理 |
|------|----------|------|
| **编译/解析错误** | 语法错误、类型错误、缺失导入、未解析引用 | Agent 3 (Opus) |
| **逻辑错误** | 无论输入如何都会产生错误结果的明确逻辑问题 | Agent 3 (Opus) |
| **安全问题** | 新增代码中的安全隐患 | Agent 4 (Opus) |
| **CLAUDE.md 合规** | 代码是否违反项目规范（必须引用被违反的具体规则） | Agent 1-2 (Sonnet) |

**显式排除的假阳性（源码明确列出不得标记）：**
- 已有代码中的问题（非 PR 引入）
- 看起来像 Bug 但实际正确的代码
- 资深工程师不会标记的吹毛求疵
- Linter 会捕获的问题（不要运行 linter 验证）
- 一般代码质量问题（除非 CLAUDE.md 明确要求）
- 代码中用 lint ignore 注释显式屏蔽的问题

**过滤机制（来源：命令源码 + README）：**

命令提示词实现：步骤 5 启动**并行验证代理**，每个标记的问题由独立代理确认真实性。未通过验证的问题在步骤 6 被移除。

README 描述的置信度评分体系（辅助理解）：

| 分数 | 含义 |
|------|------|
| 0 | 不确信，假阳性 |
| 25 | 有些确信，可能是真的 |
| 50 | 中度确信，真实但次要 |
| 75 | 高度确信，真实且重要 |
| 100 | 绝对确定，一定是真的 |

README 声明阈值 80 分（≥80 才通过），但命令源码中的实际过滤是通过验证代理的二元判断（通过/不通过）实现。

**PR 评论格式（源码定义）：**
```markdown
## Code review

Found 3 issues:

1. Missing error handling for OAuth callback (CLAUDE.md says "Always handle OAuth errors")
   https://github.com/owner/repo/blob/abc123.../src/auth.ts#L67-L72

2. Memory leak: OAuth state not cleaned up
   https://github.com/owner/repo/blob/abc123.../src/auth.ts#L88-L95
```

链接要求：必须使用完整 SHA（不能缩写）、`#L` 标记、至少 1 行上下文。

**实际效果**（来源：[TechCrunch 报道](https://techcrunch.com/2026/03/09/anthropic-launches-code-review-tool-to-check-flood-of-ai-generated-code/)）：
- 收到实质性审查评论的 PR 从 16% 提升到 54%
- 假阳性率 <1%

---

**关联插件：pr-review-toolkit（6 个专项审查代理）**

| 代理 | 专注领域 |
|------|---------|
| comment-analyzer | 注释准确性、文档完整性、注释腐化 |
| test-coverage | 测试覆盖率、边界条件、测试质量 |
| error-handling | 错误处理完整性、异常流程 |
| type-design | 类型设计、接口契约 |
| code-quality | 代码质量、复杂度、可维护性 |
| simplify | 代码简化、冗余消除 |

---

### /batch

- **类型：** prompt（内置 Skill）
- **功能：** 编排大规模并行变更——将大型任务拆分为多个子任务并行执行
- **来源：** [官方文档](https://code.claude.com/docs/en/slash-commands)

**使用示例：**
```bash
/batch 将所有 console.log 替换为 logger.info
/batch 为所有 API 端点添加错误处理
```

**工作原理：**
- 分析任务范围，识别可并行的子任务
- 启动多个子代理并行执行变更
- 汇总结果和变更报告

---

### /debug

- **类型：** prompt（内置 Skill）
- **功能：** 通过分析 debug 日志排查会话问题
- **来源：** [官方文档](https://code.claude.com/docs/en/slash-commands)

**使用示例：**
```bash
/debug
/debug 为什么上一步失败了
```

**工作原理：**
- 读取会话的 debug 日志文件
- 分析错误、异常和异常行为模式
- 提供排查建议和修复方案

---

### /commit

- **类型：** prompt（commit-commands 插件）
- **功能：** 分析 Git 暂存区变更，自动生成 commit message 并执行 `git commit`
- **源码：** [`plugins/commit-commands/`](https://github.com/anthropics/claude-code/tree/main/plugins/commit-commands)

**使用示例：**
```
/commit
/commit 请用中文写提交信息
```

**工作原理：**
1. 收集 `git status` 和 `git diff --staged` 信息
2. 将变更内容和仓库上下文发送给 LLM
3. LLM 分析变更性质（新功能、修复、重构等），生成规范的 commit message
4. 调用 Bash 工具执行 `git commit -m "..."` 完成提交
5. 默认在 commit message 末尾追加 `Co-Authored-By: Claude ...` 签名

**实现细节：**
- LLM 会查看最近的 commit 历史来匹配仓库的 commit message 风格
- 自动检测是否有未暂存的文件，并给出提醒
- 不会执行 `git add`——用户需要自己暂存文件
- 不会执行 `git push`——仅做本地提交

---

### /commit-push-pr

- **类型：** prompt
- **功能：** 一站式完成 commit + push + 创建 Pull Request 的完整工作流
- **别名：** 无

**使用示例：**
```
/commit-push-pr
/commit-push-pr 这个 PR 修复了登录页面的 XSS 漏洞
```

**工作原理：**
1. 与 `/commit` 相同的流程分析并提交变更
2. 推送当前分支到远程仓库（如需要会设置 upstream）
3. 调用 `gh pr create` 创建 Pull Request
4. LLM 自动生成 PR 标题和描述（包含变更摘要、测试计划等）
5. 返回创建好的 PR 链接

**实现细节：**
- 依赖 `gh` CLI 工具创建 PR
- LLM 会查看所有待合并的 commit（不仅是最新的）来撰写 PR 描述
- 自动检测 base 分支（通常是 main 或 master）

---

### /init

- **类型：** prompt
- **功能：** 分析项目结构，生成或更新 `CLAUDE.md` 项目指令文件
- **别名：** 无

**使用示例：**
```
/init
/init 请重点关注 Python 项目的配置
```

**工作原理：**
1. LLM 扫描项目目录结构、配置文件（package.json、pyproject.toml 等）、README 等
2. 分析项目的技术栈、构建系统、测试框架、代码规范
3. 生成 `CLAUDE.md` 文件，包含：
   - 项目概述和技术栈
   - 常用命令（构建、测试、lint）
   - 代码风格约定
   - 项目特定的 AI 行为指令
4. 如果 `CLAUDE.md` 已存在，则分析当前内容并进行增量更新

**实现细节：**
- `CLAUDE.md` 相当于项目级的系统提示，每次会话启动时自动加载
- 支持三层 CLAUDE.md：`~/.claude/CLAUDE.md`（全局）、项目根目录、子目录
- 生成的内容会参考项目实际配置，避免通用化的模板内容

---

### /init-verifiers

- **类型：** prompt
- **功能：** 为项目创建验证器 Skill，用于自动化代码变更验证
- **别名：** 无

**使用示例：**
```
/init-verifiers
```

**工作原理：**
1. LLM 分析项目结构，识别可用的验证手段（lint、type-check、test 等）
2. 生成验证器 Skill 配置，定义代码变更后的自动检查步骤
3. 验证器 Skill 可在后续的代码修改流程中被自动触发

**实现细节：**
- 验证器是一种特殊的 Skill，绑定到代码变更事件
- 可以验证类型安全性、代码风格、测试通过率等
- 生成的配置存储在 `.claude/` 目录下

---

### /insights

- **类型：** prompt
- **功能：** 生成会话洞察报告 / 年度回顾（year-in-review）
- **别名：** 无

**使用示例：**
```
/insights
```

**工作原理：**
1. 收集当前或历史会话数据（token 使用、工具调用、任务完成情况等）
2. LLM 分析使用模式，生成洞察报告
3. 可能包含使用频率、常见操作、效率指标等统计信息

---

## local-jsx 类型命令（~50 个）

这类命令在终端内渲染 React/Ink 交互式 UI 组件。它们不调用 LLM，不消耗 API token，响应速度极快。按功能分组如下：

---

### 会话管理

#### /resume

- **类型：** local-jsx
- **功能：** 恢复之前中断的会话，从历史会话列表中选择一个继续
- **别名：** 等同于 CLI `--resume` 参数

**使用示例：**
```
/resume
```

**实现细节：**
- 渲染一个交互式列表，显示最近的会话（包含时间戳、摘要）
- 选择后恢复完整的对话历史和上下文
- 会话数据存储在 `~/.claude/projects/<project-hash>/` 目录下

#### /session

- **类型：** local-jsx
- **功能：** 显示远程会话 URL 和二维码（别名：/remote）
- **别名：** `/remote`

**使用示例：**
```
/session
/remote
```

**实现细节：**
- 显示远程会话 URL 和二维码
- 可用于在其他设备上连接到当前会话

#### /rename

- **类型：** local-jsx
- **功能：** 重命名当前会话，设置一个有意义的名称
- **别名：** 无

**使用示例：**
```
/rename 修复登录 bug
/rename
```

**实现细节：**
- 如果不提供名称参数，渲染文本输入 UI
- 会话名称会显示在 `/resume` 的列表中，方便识别

#### /tag

- **类型：** local-jsx
- **功能：** 为当前会话打标签，便于分类和检索
- **别名：** 无

**使用示例：**
```
/tag bugfix
/tag
```

#### /export

- **类型：** local-jsx
- **功能：** 导出当前会话的对话历史
- **别名：** 无

**使用示例：**
```
/export
/export json
```

**实现细节：**
- 支持导出为 JSON、Markdown 等格式
- 导出内容包含完整的对话消息和工具调用记录

#### /rewind

- **类型：** local-jsx
- **功能：** 回退到之前的检查点——还原代码和/或对话历史
- **别名：** `/checkpoint`

**使用示例：**
```
/rewind
/checkpoint
```

**实现细节：**
- 渲染检查点选择 UI，列出可回退的历史节点
- 支持还原代码变更和/或对话历史
- 基于 Git checkpoint 机制实现文件状态回退

---

### 模型与配置

#### /model

- **类型：** local-jsx
- **功能：** 切换当前会话使用的 AI 模型
- **别名：** 无

**使用示例：**
```
/model
/model opus
/model sonnet
```

**实现细节：**
- 渲染模型选择列表，显示可用模型及其特性
- 可用模型取决于订阅计划和 API 配置
- 常见选项：`claude-sonnet-4-6`、`claude-opus-4-6`、`claude-haiku-4-5`
- 切换立即生效，影响后续所有 LLM 调用

#### /config

- **类型：** local-jsx
- **功能：** 打开或编辑 Claude Code 配置文件
- **别名：** 无

**使用示例：**
```
/config
/config set theme dark
```

**实现细节：**
- 渲染配置编辑 UI，展示当前生效的配置项
- 配置优先级（高到低）：system settings -> workspace -> user settings -> default
- 配置文件路径：`~/.claude/settings.json`（用户级）、`.claude/settings.json`（项目级）

#### /effort

- **类型：** local-jsx
- **功能：** 调整模型的推理努力程度（reasoning effort）
- **别名：** 无

**使用示例：**
```
/effort
/effort high
/effort low
```

**实现细节：**
- 渲染滑块或选项列表（low / medium / high）
- 较低的 effort 减少 token 消耗和延迟，适合简单任务
- 较高的 effort 提高推理深度，适合复杂分析任务
- 对应 API 参数中的 `thinking` / `budget_tokens` 设置

#### /fast

- **类型：** local-jsx
- **功能：** 快速切换到低延迟模式（使用更快的模型或更低的 effort）
- **别名：** 无

**使用示例：**
```
/fast
```

**实现细节：**
- 一键切换到 Haiku 或低 effort Sonnet 模式
- 适合需要快速响应的简单操作
- 再次执行可切换回默认模式

#### /permissions

- **类型：** local-jsx
- **功能：** 管理工具权限设置（允许/拒绝/总是允许等）
- **别名：** `/allowed-tools`

**使用示例：**
```
/permissions
```

**实现细节：**
- 渲染权限管理 UI，列出所有工具及其当前权限状态
- 权限分为：`allow`（允许）、`deny`（拒绝）、`ask`（每次询问）
- 设置存储在 `~/.claude/settings.json` 的 `permissions` 字段
- 支持按路径、按项目设置不同权限策略

#### /hooks

- **类型：** local-jsx
- **功能：** 管理 Prompt Hook 配置（24 种事件类型的钩子函数）
- **别名：** 无

**使用示例：**
```
/hooks
```

**实现细节：**
- 渲染 Hook 管理 UI，列出已配置的 Hook 及其触发事件
- 支持的事件类型包括：PreToolUse、PostToolUse、Notification、Stop 等
- Hook 可以是 Shell 命令或 LLM 推理驱动的决策逻辑
- 配置存储在 settings.json 的 `hooks` 字段

#### /privacy-settings

- **类型：** local-jsx
- **功能：** 管理隐私设置（数据收集、遥测等选项）
- **别名：** 无

**使用示例：**
```
/privacy-settings
```

#### /rate-limit-options

- **类型：** local-jsx
- **功能：** 查看和配置速率限制相关选项
- **别名：** 无

**使用示例：**
```
/rate-limit-options
```

**实现细节：**
- 显示当前 API 速率限制状态
- 可配置达到限制时的行为（等待/切换模型/通知）

#### /extra-usage

- **类型：** local-jsx
- **功能：** 查看额外用量信息和配额详情
- **别名：** 无

**使用示例：**
```
/extra-usage
```

---

### 上下文与文件

#### /add-dir

- **类型：** local-jsx
- **功能：** 将额外目录添加到当前会话的工作上下文中
- **别名：** 无

**使用示例：**
```
/add-dir /path/to/another/project
/add-dir ../shared-lib
```

**实现细节：**
- 渲染目录选择 UI 或直接接受路径参数
- 添加后，LLM 的文件操作工具可以访问该目录
- 不会改变实际的工作目录，仅扩展文件访问范围
- 适合跨项目引用代码

#### /diff

- **类型：** local-jsx
- **功能：** 显示当前会话中 Claude 所做的所有文件变更的 diff 视图
- **别名：** 无

**使用示例：**
```
/diff
```

**实现细节：**
- 渲染彩色 diff 视图，显示所有被修改文件的变更
- 基于 Git checkpoint 机制追踪变更
- 可用于在提交前审查 Claude 所做的修改

#### /status

- **类型：** local-jsx
- **功能：** 显示当前会话和项目的状态信息
- **别名：** 无

**使用示例：**
```
/status
```

**实现细节：**
- 显示当前模型、会话时长、token 使用量
- 显示项目信息（Git 分支、工作目录）
- 显示 MCP 服务器连接状态

#### /plan

- **类型：** local-jsx
- **功能：** 切换计划模式（Plan Mode）——LLM 只分析和规划，不执行修改
- **别名：** 无

**使用示例：**
```
/plan
/plan on
/plan off
```

**实现细节：**
- 开启后 LLM 的可用工具被限制为只读工具（Read、Glob、Grep、WebFetch 等）
- Write、Edit、MultiEdit、Bash 等修改性工具被禁用
- 适合先让 Claude 分析问题、制定方案，再手动确认后执行
- 再次执行 `/plan` 切换回正常模式

#### /tasks

- **类型：** local-jsx
- **功能：** 查看和管理后台任务（通过 Task 工具创建的异步任务）
- **别名：** `/bashes`

**使用示例：**
```
/tasks
```

**实现细节：**
- 列出所有活跃和已完成的后台任务
- 显示每个任务的状态、进度、输出摘要
- 任务由 LLM 通过 TaskCreate 工具创建，用于并行处理

#### /brief

- **类型：** local-jsx
- **功能：** 切换简洁输出模式，减少 Claude 的回复冗长度
- **别名：** 无

**使用示例：**
```
/brief
/brief on
/brief off
```

**实现细节：**
- 开启后在系统提示中加入简洁输出指令
- Claude 会减少解释性文字，更直接地输出结果

#### /btw

- **类型：** local-jsx
- **功能：** 在当前对话流中插入旁注（by the way），不影响主任务
- **别名：** 无

**使用示例：**
```
/btw 顺便帮我检查一下 package.json 的版本号
```

---

### 工具与扩展

#### /mcp

- **类型：** local-jsx
- **功能：** 管理 MCP（Model Context Protocol）服务器连接
- **别名：** 无

**使用示例：**
```
/mcp
```

**实现细节：**
- 渲染 MCP 服务器管理 UI，显示已配置和已连接的服务器
- 支持三种传输协议：Stdio、SSE、Streamable-HTTP
- MCP 工具以 `mcp__serverName__toolName` 格式注册到 LLM 的工具列表
- 配置存储在 settings.json 的 `mcpServers` 字段

#### /plugin

- **类型：** local-jsx
- **功能：** 管理 Claude Code 插件（安装、卸载、查看、配置）
- **别名：** `/plugins`、`/marketplace`

**使用示例：**
```
/plugin
/plugin install security-review
```

**实现细节：**
- 渲染插件管理 UI，包含 marketplace 浏览和已安装插件列表
- 插件可以注册新的斜杠命令、工具、Hook 等
- 已知官方插件：security-review、pr-comments、code-review 等

#### /skills

- **类型：** local-jsx
- **功能：** 查看和管理可用的 Skill（技能）
- **别名：** 无

**使用示例：**
```
/skills
```

**实现细节：**
- 列出所有已注册的 Skill，包括内置 Skill 和插件提供的 Skill
- Skill 是可复用的能力模块，LLM 通过 Skill 工具调用它们
- 支持 Skill 的启用/禁用管理

#### /agents

- **类型：** local-jsx
- **功能：** 管理多代理配置（Teammates 功能）
- **别名：** 无

**使用示例：**
```
/agents
```

**实现细节：**
- 渲染代理管理 UI，查看和配置 Teammates
- Teammates 使用 tmux/iTerm2 分屏，每个代理独立 worktree
- 每个代理可以分配不同的模型和角色

#### /ide

- **类型：** local-jsx
- **功能：** 配置 IDE 集成（VS Code、JetBrains 等编辑器连接）
- **别名：** 无

**使用示例：**
```
/ide
```

---

### 记忆与认证

#### /memory

- **类型：** local-jsx
- **功能：** 查看和编辑 Claude 的项目记忆文件（CLAUDE.md）
- **别名：** 无

**使用示例：**
```
/memory
```

**实现细节：**
- 渲染记忆管理 UI，显示当前生效的所有 CLAUDE.md 文件
- 支持编辑全局（`~/.claude/CLAUDE.md`）和项目级（`./CLAUDE.md`）记忆
- 记忆内容在每次会话启动时自动加载到系统提示

#### /login

- **类型：** local-jsx
- **功能：** 登录 Claude 账号（Anthropic 账号或 OAuth 认证）
- **别名：** 无

**使用示例：**
```
/login
```

**实现细节：**
- 渲染 OAuth 认证流程 UI
- 支持 Anthropic 直连账号和企业 SSO
- 认证令牌存储在系统密钥环或 `~/.claude/` 目录

#### /logout

- **类型：** local-jsx
- **功能：** 登出当前账号，清除认证令牌
- **别名：** 无

**使用示例：**
```
/logout
```

---

### UI 与显示

#### /color

- **类型：** local-jsx
- **功能：** 配置终端输出的颜色方案
- **别名：** 无

**使用示例：**
```
/color
```

**实现细节：**
- 渲染颜色选择 UI
- 可切换浅色/深色/自定义配色

#### /theme

- **类型：** local-jsx
- **功能：** 切换 Claude Code 的终端主题
- **别名：** 无

**使用示例：**
```
/theme
/theme dark
/theme light
```

**实现细节：**
- 渲染主题选择 UI，预览不同主题效果
- 影响语法高亮、diff 显示、UI 组件等视觉元素

#### /copy

- **类型：** local-jsx
- **功能：** 将 Claude 的最后一条回复复制到系统剪贴板
- **别名：** 无

**使用示例：**
```
/copy
```

**实现细节：**
- 调用系统剪贴板 API（pbcopy/xclip/xsel 等）
- 复制纯文本格式的回复内容

#### /stats

- **类型：** local-jsx
- **功能：** 显示当前会话的详细统计信息
- **别名：** 无

**使用示例：**
```
/stats
```

**实现细节：**
- 渲染统计面板，包含：
  - 总 token 数（输入/输出/缓存）
  - 工具调用次数和分布
  - 会话持续时间
  - 模型使用情况

#### /usage

- **类型：** local-jsx
- **功能：** 显示 API 用量和配额信息
- **别名：** 无

**使用示例：**
```
/usage
```

**实现细节：**
- 渲染用量面板，显示当前计费周期的 API 使用量
- 对于订阅用户显示配额剩余
- 对于 API 用户显示费用统计

#### /help

- **类型：** local-jsx
- **功能：** 显示所有可用命令的帮助信息
- **别名：** 无

**使用示例：**
```
/help
/help commit
```

**实现细节：**
- 渲染分类的命令列表，每个命令带简短描述
- 支持查看特定命令的详细帮助

#### /feedback

- **类型：** local-jsx
- **功能：** 提交反馈给 Anthropic 团队
- **别名：** 无

**使用示例：**
```
/feedback
```

**实现细节：**
- 渲染反馈表单 UI
- 可附带会话上下文一起提交

---

### 远程与集成

#### /remote-control

- **类型：** local-jsx
- **功能：** 启动远程控制模式，桥接到 claude.ai/code 浏览器界面
- **别名：** `/rc`

**使用示例：**
```
/remote-control
```

**实现细节：**
- 渲染远程控制配置 UI
- 向 Anthropic API 注册会话（WebSocket/SSE 双向通信）
- 允许在浏览器中操作终端会话
- 支持跨设备远程操作

#### /remote-env

- **类型：** local-jsx
- **功能：** 配置远程环境设置（远程服务器上的 Claude Code 实例）
- **别名：** 无

**使用示例：**
```
/remote-env
```

#### /desktop

- **类型：** local-jsx
- **功能：** 在 Claude Desktop 中继续当前会话（别名：/app）
- **别名：** `/app`

**使用示例：**
```
/desktop
/app
```

#### /mobile

- **类型：** local-jsx
- **功能：** 显示下载 Claude 移动应用的二维码（别名：/ios, /android）
- **别名：** `/ios`、`/android`

**使用示例：**
```
/mobile
/ios
/android
```

#### /install-github-app

- **类型：** local-jsx
- **功能：** 安装 Claude Code GitHub App 到仓库（用于 PR 自动审查等功能）
- **别名：** 无

**使用示例：**
```
/install-github-app
```

**实现细节：**
- 渲染安装引导 UI
- 引导用户完成 GitHub App 的授权和仓库绑定
- 安装后支持 GitHub 事件触发的自动化任务

#### /web-setup

- **类型：** local-jsx
- **功能：** 配置 Web 集成设置（Chrome 扩展等）
- **别名：** 无

**使用示例：**
```
/web-setup
```

---

### 系统

#### /exit

- **类型：** local-jsx
- **功能：** 退出 Claude Code 会话
- **别名：** `/quit`、Ctrl+C 两次、Ctrl+D

**使用示例：**
```
/exit
```

#### /install

- **类型：** local-jsx
- **功能：** 安装 Claude Code 原生构建
- **别名：** 无

**使用示例：**
```
/install
```

#### /upgrade

- **类型：** local-jsx
- **功能：** 升级到 Max 计划获取更高速率限制和更多 Opus 用量
- **别名：** 无

**使用示例：**
```
/upgrade
```

**实现细节：**
- 引导用户升级到 Max 计划
- 展示不同计划的速率限制和 Opus 用量对比

#### /terminal-setup

- **类型：** local-jsx
- **功能：** 配置终端环境（shell 集成、快捷键等）
- **别名：** 无

**使用示例：**
```
/terminal-setup
```

#### /install-slack-app

- **类型：** local-jsx
- **功能：** 安装 Claude Slack 应用
- **别名：** 无

**使用示例：**
```
/install-slack-app
```

#### /reload-plugins

- **类型：** local-jsx
- **功能：** 激活当前会话中待处理的插件变更
- **别名：** 无

**使用示例：**
```
/reload-plugins
```

#### /chrome

- **类型：** local-jsx
- **功能：** Claude in Chrome（Beta）设置
- **别名：** 无

**使用示例：**
```
/chrome
```

#### /passes

- **类型：** local-jsx
- **功能：** 分享 Claude Code 免费体验周给朋友，赚取额外用量
- **别名：** 无

**使用示例：**
```
/passes
```

#### /think-back

- **类型：** local-jsx
- **功能：** 2025 年 Claude Code 年度回顾
- **别名：** 无

**使用示例：**
```
/think-back
```

**实现细节：**
- 展示 2025 年 Claude Code 使用回顾
- 统计年度使用数据和里程碑

#### /branch

- **类型：** local-jsx
- **功能：** 创建当前对话的分支（别名：/fork）
- **别名：** `/fork`

**使用示例：**
```
/branch
/fork
```

**实现细节：**
- 创建当前对话的分支，分叉出一个新的对话路径
- 支持在不同分支中探索不同的解决方案

---

## local 类型命令（~11 个）

这类命令直接在本地执行，既不调用 LLM 也不渲染复杂 UI。它们是最轻量的命令，执行速度最快。

---

### /compact

- **类型：** local
- **功能：** 压缩当前上下文窗口，保留关键信息并释放 token 空间
- **别名：** 无

**使用示例：**
```
/compact
/compact 请保留关于数据库迁移的上下文
```

**工作原理——三层压缩体系：**

1. **微压缩（micro）：** 自动对过长的工具输出进行截断和摘要，在消息级别减少 token 占用
2. **自动压缩（auto）：** 当上下文使用率达到 ~95% 时自动触发完整压缩，使用 `compact-2026-01-12` 专用 API 端点
3. **手动压缩（manual）：** 用户执行 `/compact` 时触发，可附带保留指令

**实现细节：**
- 使用 `compact-2026-01-12` 专用 API 端点进行压缩
- 压缩过程由专门的模型完成，非用户的聊天模型
- 压缩后保留对话的关键决策、代码变更记录、未完成任务
- 可选参数指定需要优先保留的上下文
- 压缩比通常在 3:1 到 10:1 之间，取决于对话内容

---

### /clear

- **类型：** local
- **功能：** 完全清除当前对话历史，重新开始
- **别名：** 无

**使用示例：**
```
/clear
```

**实现细节：**
- 彻底清空对话消息列表
- CLAUDE.md 和系统提示在下一轮对话时重新加载
- 不影响 Git 历史和文件系统状态
- 与 `/compact` 不同：`/clear` 不保留任何上下文

---

### /context

- **类型：** local
- **功能：** 可视化当前上下文窗口的使用情况
- **别名：** 无

**使用示例：**
```
/context
```

**实现细节：**
- 显示一个彩色网格，展示上下文空间的使用比例
- 不同颜色表示不同类型的内容（系统提示、对话、工具输出等）
- 显示已使用 / 总计 token 数
- 当接近容量上限时给出压缩建议

---

### /cost

- **类型：** local
- **功能：** 显示当前会话的 token 消耗和费用
- **别名：** 无

**使用示例：**
```
/cost
```

**实现细节：**
- 显示输入 token 数、输出 token 数、缓存 token 数
- 按模型定价计算估算费用
- 显示累计费用和本次对话费用
- 对于订阅用户显示配额使用情况而非费用

---

### /doctor

- **类型：** local
- **功能：** 诊断 Claude Code 安装健康状况
- **别名：** 无

**使用示例：**
```
/doctor
```

**实现细节：**
- 执行一系列诊断检查：
  - 认证状态（API Key / OAuth 令牌是否有效）
  - 配置文件语法检查（settings.json 是否合法）
  - MCP 服务器连接测试（每个服务器的可达性）
  - Git 环境检查（git 版本、仓库状态）
  - Shell 环境检查（PATH、必要工具是否存在）
  - 网络连通性检查（API 端点可达性）
- 输出诊断报告，标记通过/失败/警告的项目
- 对失败项提供修复建议

---

### /vim

- **类型：** local
- **功能：** 切换 Vim 编辑模式和 Normal 编辑模式
- **别名：** 无

**使用示例：**
```
/vim
```

**实现细节：**
- 切换终端输入框的编辑模式
- Vim 模式下支持 hjkl 移动、i/a 进入插入模式、Esc 返回普通模式等
- 状态持久化到用户配置中

---

### /voice

- **类型：** local
- **功能：** 切换语音模式（Push-to-talk 语音输入）
- **别名：** 无

**使用示例：**
```
/voice
```

**实现细节：**
- 启动麦克风录音，通过 WebSocket 连接到 speech-to-text API
- Push-to-talk 模式：按住指定键说话，松开后自动转写为文本输入
- 转写结果填充到输入框中，用户确认后发送
- 需要系统麦克风权限

---

### /keybindings

- **类型：** local
- **功能：** 打开快捷键绑定配置文件
- **别名：** 无

**使用示例：**
```
/keybindings
```

**实现细节：**
- 打开 `~/.claude/keybindings.json` 配置文件
- 允许自定义终端内的快捷键映射

---

### /release-notes

- **类型：** local
- **功能：** 显示当前版本的发布说明
- **别名：** 无

**使用示例：**
```
/release-notes
```

**实现细节：**
- 获取并显示当前安装版本（v2.1.81）的更新日志
- 包含新功能、bug 修复、重大变更等信息

---

### /files

- **类型：** local
- **功能：** 列出当前上下文中已加载的文件
- **别名：** 无

**使用示例：**
```
/files
```

**实现细节：**
- 显示 LLM 上下文中所有通过 Read 工具加载过的文件
- 包含文件路径和大致 token 占用
- 有助于了解 LLM 当前"看到了"哪些文件

---

## Skill 类型命令

Skill 命令由插件系统或内置 Skill 机制提供，可以在运行时动态注册。它们通过 Skill 工具被 LLM 调用，也可以作为斜杠命令直接执行。

---

### /loop

- **类型：** skill（内置）
- **功能：** 按固定间隔循环执行指定命令或提示（默认每 10 分钟）
- **源码提取：** 从 v2.1.81 二进制中逆向获取完整定义
- **触发条件：** 用户要求"定期"、"每隔"、"持续监控"等循环任务时自动触发

**使用示例：**
```bash
/loop /review                    # 每 10 分钟审查代码（默认间隔）
/loop 5m /babysit-prs            # 每 5 分钟检查 PR 状态
/loop 30m check the deploy       # 每 30 分钟检查部署
/loop 1h /standup 1              # 每小时执行 standup
/loop check the deploy every 20m # 自然语言指定间隔
```

**参数格式（源码定义）：**
- 间隔格式：`Ns`（秒）、`Nm`（分）、`Nh`（时）、`Nd`（天）
- 最小粒度：1 分钟
- 默认间隔：`10m`（源码变量 `OeH = "10m"`）
- 若未指定间隔，自动使用默认值

**实现机制：**
- `/loop` 将目标命令注册为循环任务
- 每次执行相当于重新发送指定的提示或斜杠命令
- 适用场景：CI/CD 监控、PR 巡检、持续审查、部署状态轮询
- 通过 `/tasks` 查看和管理正在运行的循环任务

**与 /schedule 的区别：**
- `/loop` 是**本地循环**——在当前会话中持续运行，关闭终端即停止
- `/schedule` 是**远程定时**——在 Anthropic 云端创建 cron 任务，独立于本地会话

---

### /schedule

- **类型：** skill（内置）
- **功能：** 创建和管理 cron 定时调度的远程 Agent 任务（CCR = Claude Code Remote）
- **源码提取：** 从 v2.1.81 二进制中逆向获取完整 `RemoteTrigger` 工具定义
- **工具依赖：** `RemoteTrigger`（通过 `ToolSearch` 按需加载）、`AskUserQuestion`

**使用示例：**
```bash
/schedule                        # 交互式选择操作（创建/列出/更新/执行）
/schedule list                   # 列出所有定时任务
/schedule create                 # 创建新的定时任务
/schedule run <trigger_id>       # 立即执行指定任务
```

**支持的操作（源码 `RemoteTrigger` 工具）：**

| 操作 | 参数 | 说明 |
|------|------|------|
| `list` | — | 列出所有 trigger |
| `get` | `trigger_id` | 获取单个 trigger 详情 |
| `create` | `body: {...}` | 创建 trigger |
| `update` | `trigger_id`, `body: {...}` | 部分更新 trigger |
| `run` | `trigger_id` | 立即执行 trigger |

**注意：** 不支持删除——需到 `https://claude.ai/code/scheduled` 网页操作。

**Create body 结构（源码定义）：**
```json
{
  "name": "AGENT_NAME",
  "cron_expression": "0 9 * * 1-5",
  "enabled": true,
  "job_config": {
    "ccr": {
      "environment_id": "ENVIRONMENT_ID",
      "session_context": {
        "model": "claude-sonnet-4-6",
        "sources": [
          {"git_repository": {"url": "https://github.com/ORG/REPO"}}
        ],
        "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
      },
      "events": [{"data": {"uuid": "<v4-uuid>", "type": "user", "content": [{"type": "text", "text": "你的任务提示"}]}}]
    }
  }
}
```

**架构：**
- 每个 trigger 在 Anthropic 云端创建一个完全隔离的远程会话（CCR）
- 远程会话有独立的 Git checkout、工具集和可选的 MCP 连接
- 通过 MCP Connector（`mcpsrv_` 前缀）连接到 claude.ai 上配置的 MCP 服务器
- 认证通过 OAuth 内部处理（不使用 curl）

---

### /security-review

- **类型：** skill（由插件提供）
- **功能：** 对代码进行安全漏洞分析
- **别名：** 无

**使用示例：**
```
/security-review
/security-review src/auth/
```

**实现细节：**
- 由 security-review 插件提供
- 分析代码中的常见安全漏洞：
  - SQL 注入、XSS、CSRF
  - 硬编码凭据、不安全的加密
  - 权限提升、路径遍历
- 生成安全审查报告，按严重程度分级

---

### /pr-comments

- **类型：** skill（由插件提供）
- **功能：** 处理 Pull Request 上的评论，自动回复或执行修改
- **别名：** 无

**使用示例：**
```
/pr-comments
/pr-comments 123
```

**实现细节：**
- 由 pr-comments 插件提供
- 读取 PR 上的 review comments
- LLM 分析评论内容，自动生成回复或执行代码修改
- 支持处理 inline comments 和 general comments
- 使用 `gh` CLI 与 GitHub API 交互

---

### /simplify

- **类型：** skill（内置）
- **功能：** 审查已修改代码的复用性、质量和效率，自动修复发现的问题
- **源码提取：** 从 v2.1.81 二进制中逆向获取完整提示词（`q7_` 变量）

**使用示例：**
```bash
/simplify
/simplify 重点关注性能问题
```

**三阶段工作流（源码定义）：**

**Phase 1: 识别变更** — 运行 `git diff`（或 `git diff HEAD`）获取所有变更文件

**Phase 2: 启动三个并行审查代理** — 通过 Agent 工具同时启动，每个代理获得完整 diff

| 代理 | 审查维度 | 检查项 |
|------|----------|--------|
| **Agent 1: 代码复用** | 搜索已有工具函数 | 1. 搜索可替代新代码的已有 utility/helper 2. 标记重复已有功能的新函数 3. 标记可用已有工具替代的内联逻辑（手写字符串处理、手动路径操作、自定义环境检查、临时类型守卫等） |
| **Agent 2: 代码质量** | 检查 hacky 模式 | 1. **冗余状态**：复制已有状态、可推导的缓存值 2. **参数膨胀**：给函数加新参数而非重构 3. **复制粘贴变体**：近重复代码块应统一抽象 4. **抽象泄漏**：暴露应封装的内部细节 5. **字符串类型化**：用原始字符串代替已有的常量/枚举/branded type 6. **不必要的 JSX 嵌套**：无布局作用的包装元素 7. **不必要的注释**：解释"做了什么"的注释（好的命名已说明）、叙述性注释、引用调用者的注释——删除；仅保留非显而易见的"为什么" |
| **Agent 3: 效率审查** | 检查性能问题 | 1. **不必要的工作**：冗余计算、重复文件读取、重复 API 调用、N+1 模式 2. **错过并发**：可并行的独立操作串行执行 3. **热路径膨胀**：启动或每请求/每渲染热路径中添加阻塞工作 4. **循环中的无操作更新**：轮询/定时器/事件处理器中无条件触发状态更新（应加变更检测守卫） 5. **不必要的存在检查**：操作前先检查文件/资源是否存在（TOCTOU 反模式）——直接操作并处理错误 6. **内存**：无界数据结构、缺失清理、事件监听器泄漏 7. **过于宽泛的操作**：读取整个文件却只需要部分、加载所有项却只过滤一个 |

**Phase 3: 修复问题** — 根据三个代理的发现自动修复代码

---

### /claude-api

- **类型：** skill
- **功能：** 与 Claude API 相关的辅助功能
- **别名：** 无

**使用示例：**
```
/claude-api
```

---

### /update-config

- **类型：** skill
- **功能：** 通过对话方式更新配置
- **别名：** 无

**使用示例：**
```
/update-config
```

---

### /keybindings-help

- **类型：** skill
- **功能：** 显示快捷键帮助信息和可用的键位映射
- **别名：** 无

**使用示例：**
```
/keybindings-help
```

---

### /statusline

- **类型：** skill
- **功能：** 配置 Claude Code 状态栏 UI
- **别名：** 无

**使用示例：**
```
/statusline
```

---

### /suggestions

- **类型：** skill
- **功能：** 分析使用数据并建议改进
- **别名：** 无

**使用示例：**
```
/suggestions
```

---

## 命令快速索引表

| 命令 | 类型 | 一句话说明 |
|------|------|-----------|
| `/review` | prompt | 审查代码变更，生成 Review 报告 |
| `/commit` | prompt | 分析暂存区，自动生成 commit message 并提交 |
| `/commit-push-pr` | prompt | 提交 + 推送 + 创建 PR 一站式流程 |
| `/init` | prompt | 分析项目，生成 CLAUDE.md |
| `/init-verifiers` | prompt | 创建代码验证器 Skill |
| `/insights` | prompt | 会话洞察 / 年度回顾 |
| `/resume` | local-jsx | 恢复历史会话 |
| `/session` | local-jsx | 显示远程会话 URL 和二维码（别名：/remote） |
| `/rename` | local-jsx | 重命名当前会话 |
| `/tag` | local-jsx | 为会话打标签 |
| `/export` | local-jsx | 导出对话历史 |
| `/rewind` | local-jsx | 回退到之前的检查点（别名：/checkpoint） |
| `/model` | local-jsx | 切换 AI 模型 |
| `/config` | local-jsx | 编辑配置 |
| `/effort` | local-jsx | 调整推理 effort |
| `/fast` | local-jsx | 切换快速模式 |
| `/permissions` | local-jsx | 管理工具权限（别名：/allowed-tools） |
| `/hooks` | local-jsx | 管理 Prompt Hook |
| `/privacy-settings` | local-jsx | 隐私设置 |
| `/rate-limit-options` | local-jsx | 速率限制选项 |
| `/extra-usage` | local-jsx | 额外用量信息 |
| `/add-dir` | local-jsx | 添加工作目录 |
| `/diff` | local-jsx | 查看文件变更 diff |
| `/status` | local-jsx | 显示状态信息 |
| `/plan` | local-jsx | 切换计划模式 |
| `/tasks` | local-jsx | 管理后台任务（别名：/bashes） |
| `/brief` | local-jsx | 切换简洁模式 |
| `/btw` | local-jsx | 插入旁注 |
| `/mcp` | local-jsx | 管理 MCP 服务器 |
| `/plugin` | local-jsx | 管理插件（别名：/plugins, /marketplace） |
| `/skills` | local-jsx | 查看 Skill 列表 |
| `/agents` | local-jsx | 管理多代理 |
| `/ide` | local-jsx | IDE 集成配置 |
| `/memory` | local-jsx | 管理项目记忆 |
| `/login` | local-jsx | 登录账号 |
| `/logout` | local-jsx | 登出账号 |
| `/color` | local-jsx | 配置颜色方案 |
| `/theme` | local-jsx | 切换主题 |
| `/copy` | local-jsx | 复制回复到剪贴板 |
| `/stats` | local-jsx | 显示会话统计 |
| `/usage` | local-jsx | 显示 API 用量 |
| `/help` | local-jsx | 显示帮助 |
| `/feedback` | local-jsx | 提交反馈 |
| `/remote-control` | local-jsx | 远程控制模式（别名：/rc） |
| `/remote-env` | local-jsx | 远程环境设置 |
| `/desktop` | local-jsx | 在 Claude Desktop 中继续当前会话（别名：/app） |
| `/mobile` | local-jsx | 显示下载 Claude 移动应用的二维码（别名：/ios, /android） |
| `/install-github-app` | local-jsx | 安装 GitHub App |
| `/install-slack-app` | local-jsx | 安装 Claude Slack 应用 |
| `/reload-plugins` | local-jsx | 激活当前会话中待处理的插件变更 |
| `/chrome` | local-jsx | Claude in Chrome（Beta）设置 |
| `/web-setup` | local-jsx | Web 集成设置 |
| `/exit` | local-jsx | 退出会话（别名：/quit） |
| `/install` | local-jsx | 安装 Claude Code 原生构建 |
| `/upgrade` | local-jsx | 升级到 Max 计划获取更高速率限制和更多 Opus 用量 |
| `/terminal-setup` | local-jsx | 终端环境设置 |
| `/passes` | local-jsx | 分享免费体验周给朋友，赚取额外用量 |
| `/think-back` | local-jsx | 2025 年 Claude Code 年度回顾 |
| `/branch` | local-jsx | 创建当前对话的分支（别名：/fork） |
| `/compact` | local | 压缩上下文（三层压缩体系） |
| `/clear` | local | 清除对话历史 |
| `/context` | local | 可视化上下文使用情况 |
| `/cost` | local | 显示 token 消耗和费用 |
| `/doctor` | local | 诊断安装健康状况 |
| `/vim` | local | 切换 Vim 编辑模式 |
| `/voice` | local | 切换语音输入模式 |
| `/keybindings` | local | 打开快捷键配置 |
| `/release-notes` | local | 显示版本发布说明 |
| `/files` | local | 列出上下文中的文件 |
| `/loop` | skill | 循环执行命令 |
| `/schedule` | skill | 定时调度任务 |
| `/security-review` | skill | 安全漏洞分析 |
| `/pr-comments` | skill | 处理 PR 评论 |
| `/simplify` | skill | 简化代码 |
| `/claude-api` | skill | Claude API 辅助 |
| `/update-config` | skill | 对话式更新配置 |
| `/keybindings-help` | skill | 快捷键帮助 |
| `/statusline` | skill | 配置 Claude Code 状态栏 UI |
| `/suggestions` | skill | 分析使用数据并建议改进 |

---

> 本文档基于 Claude Code v2.1.81 二进制分析整理。命令列表和行为可能随版本更新而变化。
