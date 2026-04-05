# Qwen Code 改进建议 — P2 用户体验与交互增强

> 中等优先级改进项（用户体验方向）。每项包含：问题场景、现状分析、改进前后对比、实现成本评估、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. /plan 计划模式（P2）

你让 Agent 做一个复杂任务："重构认证模块，从 JWT 迁移到 OAuth2"。Agent 立刻开始改代码——但它可能理解不全需求，直接动手导致方向偏差。Plan 模式解决这个问题——通过明确的"规划→审批→执行"三阶段流程：

```
规划阶段（收集需求 + 制定计划）→ 用户审批（确认计划是否正确）→ 执行阶段（按计划实施）
```

**Claude Code 的实现——/plan 命令**：

| 特性 | 说明 |
|------|------|
| 命令入口 | `/plan` 或 `/plan open` 打开当前会话计划 |
| UI 组件 | Ink JSX 渲染计划卡片（含状态、步骤、审批按钮） |
| 计划格式 | Markdown checklist（`- [ ]` 未做，`- [x]` 已完成） |
| 审批流 | 用户确认后才能执行，防止 Agent 自作主张 |
| 退出工具 | `exitPlanMode` 工具请求用户批准退出 |

**工作流程**：

| 步骤 | 做什么 |
|------|--------|
| 1. 用户输入 `/plan` | 进入计划模式 |
| 2. Agent 分析需求 | 生成 Markdown 计划（含步骤、依赖、风险） |
| 3. 渲染计划卡片 | 显示状态（Draft/Approved/Executing）、进度、步骤列表 |
| 4. 用户审批 | 按 Enter 批准或要求修改 |
| 5. Agent 执行计划 | 按计划逐步执行，勾选完成步骤 |

**关键设计细节**：
- 计划模式期间 Agent 不能直接编辑文件（必须通过 `exitPlanMode` 获得批准）
- 计划文件持久化到 `.claude/plans/` 目录，可按 `/plan open` 重新查看
- 支持增量更新——执行中发现新步骤可追加到计划
- `plan_mode` 状态抑制其他功能（如 prompt suggestion 在计划模式期间不触发）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/plan/plan.tsx` | `/plan` 命令入口、Ink 组件 |
| `tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts` | 退出计划 + 审批流 |
| `utils/planMode/` | 计划持久化、状态管理 |

**Qwen Code 现状**：已有 `exitPlanMode` 工具（支持退出规划模式），但缺少 `/plan` 命令主动查看/管理当前计划。用户无法在规划期间查看进度或修改计划。

**Qwen Code 修改方向**：① 新建 `/plan` 命令（`commands/plan.tsx`）；② Ink 组件渲染计划卡片（状态 + 步骤 + 进度）；③ 从 AppState 读取当前计划并显示；④ 支持非交互模式（`/plan` 输出纯文本计划）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：Ink UI 布局（状态卡片、步骤列表、进度条）

**改进前后对比**：
- **改进前**：规划期间无法查看计划全貌——只能等 Agent 执行完才知道做了什么
- **改进后**：`/plan` 显示当前计划（状态 + 步骤 + 进度）——随时掌握 Agent 在做什么

**意义**：复杂任务需要明确的计划可视性和审批流程——防止 Agent 方向偏差。
**缺失后果**：用户无法主动查看/管理计划——只能等 Agent 执行完。
**改进收益**：`/plan` = 计划可视化 + 进度追踪 + 审批流程——用户掌控全局。

---

<a id="item-2"></a>

### 2. /review PR 审查（P2）

你在 GitHub 上创建了一个 PR，想让 Agent 自动审查代码质量、找出潜在 Bug、检查测试覆盖。但当前流程是：手动切到浏览器 → 打开 PR 页面 → 复制 diff → 粘贴给 Agent → 等待分析。更糟的是，PR 可能包含 10+ 文件、500+ 行变更，手动整理 diff 费时且容易遗漏。

**Claude Code 的解决方案——/review 命令**：

一键自动 PR 审查——使用 `gh` CLI 获取 PR 列表、详情、diff，然后用模型分析代码：

```bash
/review              # 审查当前分支的 PR
/review 123          # 审查 PR #123
/review --ultra      # UltraReview（远程深度审查，10-20 分钟）
```

**工作流程**：

| 步骤 | 做什么 |
|------|--------|
| 1. `gh pr list` | 获取当前分支关联的 PR（或指定 PR 号） |
| 2. `gh pr view` | 获取 PR 标题、描述、作者、标签 |
| 3. `gh pr diff` | 获取完整 diff（限制 1MB） |
| 4. 构建 Prompt | 注入 PR 元数据 + diff + 审查指导 |
| 5. 模型分析 | 按 4 步流程审查（PR 列表→详情→Diff→分析） |
| 6. 输出报告 | 代码正确性、项目规范、性能影响、测试覆盖、安全考虑 |

**审查 Prompt 模板**（4 步流程）：

```
1. 使用 `gh pr list` 获取当前仓库和分支上所有开放 PR 的列表
2. 使用 `gh pr view <number>` 获取每个 PR 的详情
3. 使用 `gh pr diff <number>` 获取每个 PR 的 diff
4. 分析代码变更并提供反馈

重点关注：
- 代码正确性（Bug、边界情况、错误处理）
- 项目规范（命名、架构、设计模式）
- 性能影响（时间复杂度、内存使用、N+1 查询）
- 测试覆盖（单元测试、集成测试、边界案例）
- 安全考虑（注入攻击、敏感数据暴露、权限检查）
```

**UltraReview（远程深度审查）**：
- 调用 Claude Code on the web 的 bughunter 服务
- 10-20 分钟深度分析（远长于本地审查）
- 查找更难发现的 Bug（逻辑错误、竞态条件、内存泄漏）
- 配额追踪 + 进度心跳

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/review/review.ts` | `/review` 命令、`gh` CLI 集成 |
| `commands/review/review.tsx` | Ink UI（PR 选择 + 审查报告） |
| `review.ts` | review / ultrareview 实现 |
| `commands/ultrareview/` | UltraReview 远程审查 |

**Qwen Code 现状**：无 `/review` 命令。用户需手动获取 PR diff 再交给 Agent 分析。Qwen Code 有 `/insight` 命令做会话分析，但没有 PR 专用审查工具。

**Qwen Code 修改方向**：① 新建 `/review` 命令（`commands/review.ts`）；② 集成 `gh` CLI（或 GitHub API）获取 PR 信息；③ 构建审查 Prompt（4 步流程 + 5 关注点）；④ 输出结构化审查报告。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：`gh` CLI 依赖检测（用户未安装时的回退）、大 diff 的分批处理

**改进前后对比**：
- **改进前**：审查 PR → 手动切浏览器 → 复制 diff → 粘贴给 Agent（~2 分钟）
- **改进后**：`/review` → 自动获取 PR + diff → 模型分析 → 输出报告（~30 秒）

**意义**：PR 审查是开发工作流的高频操作——自动化省时且更一致。
**缺失后果**：用户需手动获取 PR diff——打断工作流。
**改进收益**：`/review` = 一键自动 PR 审查——代码质量、规范、性能、安全全覆盖。

---

<a id="item-3"></a>

### 3. /branch 会话分支（P2）

你和 Agent 讨论了 20 轮，决定用"方案 A"重构认证模块。Agent 已经改了 5 个文件。但你突然想到："如果用方案 B（JWT 替换 Session）会不会更好？" 现在你面临两难：

- **继续方案 A**：放弃探索方案 B 的可能
- **尝试方案 B**：让 Agent 撤销方案 A 的所有修改，从头开始——但如果方案 B 不好，方案 A 的工作全部丢失
- **手动保存**：手动 `git stash`、复制对话历史……太繁琐

**Claude Code 的方案——/branch 命令**：从当前对话的任意位置创建一个"分支"，就像 git 分支一样——原始对话保留不动，分支独立探索：

```
原始 session（方案 A）：
  轮次 1 → 轮次 2 → ... → 轮次 20 → [继续方案 A]
                                    ↘
分支 session（方案 B）：              轮次 20 → "试试 JWT 方案" → ...
                                    （完整继承前 20 轮上下文）
```

**工作原理**：

| 步骤 | 做什么 |
|------|--------|
| 1. 用户输入 `/branch` | 触发分支创建 |
| 2. 复制 transcript JSONL | 完整对话历史复制到新文件 |
| 3. 写入溯源元数据 | `forkedFrom: { sessionId, messageUuid }` |
| 4. 自动命名 | 原名 + " (Branch)"，支持去重 |
| 5. 切换到分支 | 分支成为当前活跃 session |
| 6. 原始可恢复 | 随时 `--resume` 回到方案 A |

**关键设计**：
- 分支独立文件（不修改原始 transcript）
- 完整的上下文继承（前 20 轮对话全部保留）
- 溯源链（`forkedFrom` 元数据追踪父子关系）
- 自动命名去重（`My Session (Branch)`、`My Session (Branch 2)`、...）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/branch/branch.ts` (296行) | `getUniqueForkName()`、transcript 复制 + `forkedFrom` 元数据 |

**Qwen Code 现状**：没有 `/branch` 命令。用户想探索替代方案只能：手动 `git stash` 保存文件变更 → 开新 session → 重新描述上下文 → 尝试新方案 → 不满意再手动恢复。

**Qwen Code 修改方向**：① 新建 `/branch` 命令；② `sessionService.ts` 新增 `forkSession()` 方法（复制 JSONL + 写入 `forkedFrom` 元数据）；③ 自动命名 + 去重（`getUniqueForkName()`）；④ `/resume` 命令支持列出原始和分支 session。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：JSONL transcript 的高效复制（大 session 可能有数 MB）

**改进前后对比**：
- **改进前**：想尝试替代方案 → 要么丢弃当前进度，要么手动保存/恢复
- **改进后**：`/branch` → 分支继承完整上下文独立探索 → 不满意随时切回原始

**意义**：探索替代方案是软件开发的日常——架构选型、算法对比、重构策略 A/B 测试。
**缺失后果**：探索替代方案必须丢弃当前进度——开发者不敢轻易尝试。
**改进收益**：`/branch` = 零风险探索——不满意切回原始，满意继续分支，两边进度都保留。

---

<a id="item-4"></a>

### 4. /doctor 环境诊断（P2）

你在新机器上部署 Agent，遇到各种问题：git 没配置导致无法 commit、node 版本不兼容导致启动失败、API Key 过期无法调用模型、代理设置错误无法联网。每次排查都要手动检查——`which git`、`node --version`、`echo $API_KEY`、`curl -I https://api.example.com`——费时且容易遗漏。

**Claude Code 的解决方案——/doctor 命令**：

一键系统诊断——检查所有关键依赖是否就绪，输出结构化报告：

```
Doctor Diagnosis
━━━━━━━━━━━━━━━━
✓ git 2.39.2
✓ node 20.11.0
✓ npm 10.2.4
✓ shell zsh 5.9
✓ API key configured
✓ Proxy: none
✓ Network: reachable
✓ Permissions: default

All checks passed.
```

**检查清单**：

| 检查项 | 检查什么 | 失败表现 |
|--------|---------|---------|
| git | 版本 + 用户配置（name/email） | "git not found" / "git user not configured" |
| node | 版本（要求 ≥ 特定版本） | "node version too old" |
| shell | 类型 + 版本（bash/zsh/fish） | "shell not detected" |
| API Key | 是否配置 + 是否有效 | "API key not set" / "API key invalid" |
| Proxy | 代理设置（HTTP_PROXY/HTTPS_PROXY） | "proxy configured" 显示代理地址 |
| Network | 网络可达性（ping API 端点） | "network unreachable" |
| Permissions | 默认权限模式（default/auto-edit/yolo） | "permission mode: yolo" |

**关键设计**：
- 每个检查独立执行（一个失败不影响其他）
- 失败项显示详细错误信息（如 `git` 失败显示 "Run `git config --global user.name 'Your Name'`"）
- 非交互模式也支持（`--non-interactive`）
- 结果可复制（便于贴到 Issue 报告）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/doctor/doctor.ts` | `/doctor` 命令实现、检查清单 |

**Qwen Code 现状**：无 `/doctor` 命令。用户遇到环境问题时，需手动排查——费时且可能遗漏关键检查项。

**Qwen Code 修改方向**：① 新建 `/doctor` 命令（`commands/doctor.ts`）；② 实现检查清单（git/node/shell/API Key/proxy/network/permissions）；③ 输出结构化报告（✓/✗ 标记 + 版本号）；④ 失败项显示修复建议。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行
- 开发周期：~1.5 天（1 人）
- 难点：各项检查的跨平台兼容性（macOS/Linux/Windows）

**改进前后对比**：
- **改进前**：排查环境问题 → 手动检查 6+ 项 → 费时且可能遗漏（~5 分钟）
- **改进后**：`/doctor` → 一键诊断 → 结构化报告 + 修复建议（~5 秒）

**意义**：环境诊断对用户体验很重要——尤其是新用户首次启动。
**缺失后果**：用户需手动排查环境问题——费时且容易遗漏。
**改进收益**：`/doctor` = 一键诊断 + 修复建议——新用户快速上手，老用户快速排障。

---

<a id="item-5"></a>

### 5. /cost 费用追踪（P2）

你使用 Agent 完成了一个复杂任务——重构了 10 个文件、执行了 50+ 工具调用、跑了 3 次测试。但你不知道这次花了多少钱——token 用量、API 调用次数、预估费用完全黑盒。对于按 token 计费的 API 用户来说，无法追踪成本是个严重问题。

**Claude Code 的解决方案——/cost 命令**：

显示当前 session 的 API 费用估算——输入 token、输出 token、总费用、模型单价：

```
Session Cost
━━━━━━━━━━━━
Input tokens:     125,430  ($3.76)
Output tokens:     18,920  ($0.95)
Total:            144,350  ($4.71)

Model: claude-sonnet-4-20250514
Pricing: $30/$15 per Mtok (input/output)
```

**关键设计**：
- 实时追踪（每轮 API 调用后更新）
- 按模型计费（不同模型单价不同）
- 分区显示（输入/输出 token 分别计费）
- 支持多 session 汇总（`/cost --all`）
- 费用预警（超过阈值时警告）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/cost/cost.tsx` | `/cost` 命令、Ink UI |
| `utils/costTracking.ts` | 费用计算、模型定价表 |

**Qwen Code 现状**：无 `/cost` 命令。用户无法直接查看 session 费用——只能通过 `/stats` 查看基础统计（不含费用估算）。对于按 token 计费的 DashScope API 用户，成本黑盒。

**Qwen Code 修改方向**：① 新建 `/cost` 命令（`commands/cost.tsx`）；② 从 API 响应中提取 token 用量（input/output）；③ 按模型单价计算费用；④ Ink UI 显示（输入/输出/总计）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）
- 难点：获取准确的模型定价（DashScope/Gemini 各模型单价）

**改进前后对比**：
- **改进前**：完成任务 → 不知道花了多少钱——成本黑盒
- **改进后**：`/cost` → 显示输入/输出 token + 费用——成本透明

**意义**：API 用户需要追踪费用——尤其是长会话和高频使用场景。
**缺失后果**：用户无法了解 session 费用——成本不可控。
**改进收益**：`/cost` = 实时费用追踪——输入/输出 token + 模型单价 + 总费用一目了然。

---

<a id="item-6"></a>

### 6. /session 会话管理（P2）

你运行 Agent 一段时间后，积累了多个 session——有的在做重构、有的在修 Bug、有的在做代码审查。但当前只能看到最近一个 session——无法列出所有会话、无法按项目名称搜索、无法删除旧 session。更麻烦的是，你无法知道每个 session 的工作状态（进行中/已完成/已放弃）。

**Claude Code 的解决方案——/session 命令**：

会话管理——列出、搜索、删除、重命名 session：

```bash
/session              # 列出所有 session
/session --search auth  # 搜索包含 "auth" 的 session
/session rename "New Name"  # 重命名当前 session
/session delete <id>   # 删除指定 session
/session clear         # 删除所有已完成 session
```

**显示格式**：

| ID | 名称 | 目录 | 状态 | 时间 |
|----|------|------|------|------|
| 12345 | Refactor Auth | /project-a | completed | 2h ago |
| 12346 | Fix Login Bug | /project-a | active | now |
| 12347 | Code Review | /project-b | abandoned | 1d ago |

**关键设计**：
- 从 transcript 文件扫描（`.claude/sessions/*.jsonl`）
- 状态推断：`completed`（最后一条消息是 assistant 回复）、`active`（最近 30 分钟有活动）、`abandoned`（超过 24 小时无活动）
- 删除确认（防止误删活跃 session）
- 搜索支持（按 session 名称/目录/内容）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/session/session.tsx` | `/session` 命令、Ink UI |

**Qwen Code 现状**：无 `/session` 命令。用户可以通过 `--resume` 恢复最近 session，但无法列出/搜索/管理历史 session。

**Qwen Code 修改方向**：① 新建 `/session` 命令（`commands/session.tsx`）；② 扫描 `.qwen/sessions/` 目录；③ 解析 transcript 提取元数据（名称、目录、时间、状态）；④ Ink UI 列表显示；⑤ 支持 `--search`/`--delete`/`--rename` 子命令。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：状态推断逻辑（如何区分 completed vs abandoned）、大 session 文件的快速扫描

**改进前后对比**：
- **改进前**：管理多个 session → 只能靠记忆——不知道哪个在做哪个任务
- **改进后**：`/session` → 列表显示所有 session + 状态 + 搜索——一目了然

**意义**：多 session 管理是高频使用场景——尤其是并行处理多个任务。
**缺失后果**：用户无法列出/搜索/管理 session——只能恢复最近一个。
**改进收益**：`/session` = 会话列表 + 搜索 + 删除 + 重命名——多任务管理不再混乱。

---

<a id="item-7"></a>

### 7. /share 分享会话（P2）

你让 Agent 解决了一个复杂的 Bug——花了 30 轮对话、尝试了 5 种方案、最终找到了根因。你想把这次排查过程分享给团队——但当前只能手动复制粘贴整个对话历史到文档或聊天工具，格式混乱且丢失代码高亮。

**Claude Code 的解决方案——/share 命令**：

生成可分享链接——将整个 session 导出为格式化的 HTML/Markdown，或上传到云端生成 URL：

```bash
/share              # 生成分享链接（上传到云端）
/share --copy       # 复制 Markdown 格式到剪贴板
/share --html       # 导出为 HTML 文件
```

**分享链接格式**（云端 URL）：
```
https://claude.ai/share/<session-id>
```

页面显示：
- Session 名称 + 时间
- 完整对话历史（用户消息 + Agent 回复 + 工具调用）
- 代码块语法高亮
- 可折叠的工具结果
- 时间戳显示每轮耗时

**关键设计**：
- 隐私保护：默认不分享（用户必须显式执行 `/share`）
- 脱敏处理：自动隐藏 API Key、密码等敏感信息
- 有效期：分享链接 7 天过期（可配置）
- 只读：查看者不能修改原始 session

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/share/share.ts` | `/share` 命令、云端上传 |

**Qwen Code 现状**：无 `/share` 命令。用户无法直接分享 session——只能手动复制对话历史。Qwen Code 有 `/export` 命令导出对话到文件，但没有云端分享链接。

**Qwen Code 修改方向**：① 新建 `/share` 命令（`commands/share.ts`）；② 将 session 导出为 Markdown/HTML 格式；③ （可选）上传到阿里云 OSS 生成 URL；④ `--copy` 选项复制 Markdown 到剪贴板（OSC 52）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：云端上传（需要后端支持）、脱敏处理（识别并隐藏敏感信息）

**改进前后对比**：
- **改进前**：分享 session → 手动复制粘贴 → 格式混乱 + 丢失高亮（~5 分钟）
- **改进后**：`/share` → 生成链接/复制 Markdown → 格式完整 + 代码高亮（~3 秒）

**意义**：分享 session 是协作场景的刚需——团队学习、排查记录、最佳实践沉淀。
**缺失后果**：用户无法直接分享——只能手动复制，格式差且易丢失信息。
**改进收益**：`/share` = 一键生成链接/Markdown——格式完整 + 代码高亮 + 脱敏保护。

---

<a id="item-8"></a>

### 8. /diff 代码差异查看（P2）

你让 Agent 修改了 10 个文件后，想快速查看具体改了什么——哪些行加了、哪些行删了。但当前只能手动切到另一个终端执行 `git diff`——打断工作流，而且 diff 输出没有语法高亮，大文件难以浏览。

**Claude Code 的解决方案——/diff 命令**：

内嵌 diff 查看——在终端内显示结构化差异，支持语法高亮和文件过滤：

```bash
/diff               # 显示所有未提交变更
/diff --staged      # 显示已暂存变更
/diff src/auth/     # 只显示指定目录的 diff
/diff --stat        # 只显示统计信息（文件数 + 行数）
```

**显示格式**：

```diff
--- a/src/auth/middleware.ts
+++ b/src/auth/middleware.ts
@@ -15,7 +15,7 @@
-  const token = req.headers.authorization;
+  const token = req.headers.authorization?.split(' ')[1];
```

**关键设计**：
- Rust NAPI  bindings 快速着色（比纯 JS 快 10×）
- 行号 gutter（显示 `15 |`）
- 语法高亮（TypeScript/Python/Markdown 等）
- 文件头分隔线（`─── src/auth/middleware.ts ───`）
- 限制：50 文件上限、1MB/文件、400 行/文件（防止大 diff 卡顿）
- merge/rebase 期间自动跳过

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/diff/diff.tsx` | `/diff` 命令、Ink UI |
| `utils/gitDiff.ts` (532行) | diff 解析、限制逻辑 |

**Qwen Code 现状**：无 `/diff` 命令。用户需手动执行 `git diff`——无语法高亮、无文件过滤、无行数限制。

**Qwen Code 修改方向**：① 新建 `/diff` 命令（`commands/diff.tsx`）；② 调用 `git diff` 获取 diff；③ 解析 diff 格式（`---`/`+++`/`@@`/`+`/`-`）；④ 语法高亮（使用现有 highlight.js 或类似库）；⑤ Ink UI 渲染（颜色 + 行号 + 文件头）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：diff 解析的正确性（处理边缘情况如二进制文件、merge commit）、语法高亮性能

**改进前后对比**：
- **改进前**：查看变更 → 手动 `git diff` → 切换终端 + 无高亮（~10 秒）
- **改进后**：`/diff` → 内嵌显示 + 语法高亮 + 文件过滤（~2 秒）

**意义**：diff 查看是代码工作流的基础操作——内嵌显示减少上下文切换。
**缺失后果**：用户需手动切终端执行 `git diff`——打断工作流。
**改进收益**：`/diff` = 内嵌差异查看 + 语法高亮 + 文件过滤——变更一目了然。

---

<a id="item-9"></a>

### 9. /rename 重命名会话（P2）

你运行 Agent 完成了一个任务——session 的自动命名是 "Refactor auth module and add tests and update docs"。这个名称太长且不直观——第二天你想找到这个 session 时完全想不起来它做了什么。你希望能给 session 起一个简短易记的名称，如 "Auth Refactor"。

**Claude Code 的解决方案——/rename 命令**：

重命名当前 session——修改 session 元数据中的名称字段：

```bash
/rename "Auth Refactor"    # 重命名当前 session
```

**工作原理**：
- 修改 `.claude/sessions/<id>.json` 中的 `name` 字段
- 名称显示在 `/session` 列表、`--resume` 选择器、终端标题栏
- 名称长度限制：≤ 100 字符
- 支持特殊字符（空格、中文、emoji）

**关键设计**：
- 立即生效（不需重启 session）
- 名称持久化（写入 session 元数据文件）
- 空名称拒绝（必须提供非空名称）
- 名称历史记录（可选——保留原始自动名称）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/rename/rename.ts` | `/rename` 命令、元数据修改 |

**Qwen Code 现状**：无 `/rename` 命令。Session 名称由 Agent 自动生成（通常是第一条消息的摘要），用户无法修改。

**Qwen Code 修改方向**：① 新建 `/rename` 命令（`commands/rename.ts`）；② 修改 session 元数据文件中的 `name` 字段；③ 验证名称（非空 + 长度限制）；④ 立即生效（更新内存中的 session 名称）。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~60 行
- 开发周期：~0.5 天（1 人）
- 难点：无

**改进前后对比**：
- **改进前**：session 名称自动生成——长且不直观——难以查找
- **改进后**：`/rename "Auth Refactor"`——简短易记——快速定位

**意义**：session 命名影响后续查找和恢复——用户自定义名称更符合记忆习惯。
**缺失后果**：自动生成的名称长且不直观——难以查找历史 session。
**改进收益**：`/rename` = 自定义 session 名称——简短易记、快速定位。

---

<a id="item-10"></a>

### 10. /upgrade 版本升级（P2）

新版本 Agent 发布了——包含重要的 Bug 修复和性能改进。但你不知道当前版本是多少、是否有新版本可用、升级需要做什么。你只能手动检查——`npm list -g` 看版本号 → 去 GitHub 看 Release Notes → 再手动执行 `npm update`——流程繁琐。

**Claude Code 的解决方案——/upgrade 命令**：

版本检查 + 一键升级——显示当前版本、最新版本、变更日志：

```bash
/upgrade              # 检查更新 + 提示升级
/upgrade --check      # 只检查更新（不升级）
/upgrade --changelog  # 显示变更日志
```

**工作流程**：

| 步骤 | 做什么 |
|------|--------|
| 1. 检查 npm registry | 获取最新版本号 |
| 2. 对比当前版本 | 判断是否需要升级 |
| 3. 显示变更日志 | 显示新版本的关键变更 |
| 4. 提示升级 | `Run: npm update -g @anthropic-ai/claude-code` |

**显示格式**：

```
Current version: 2.0.50
Latest version:  2.0.53

Changes in 2.0.53:
- Fixed: Shell command timeout issue
- Added: New /review command
- Improved: Tool execution speed by 30%

To upgrade: npm update -g @anthropic-ai/claude-code
```

**关键设计**：
- 非阻塞检查（后台异步，不阻塞启动）
- 版本号语义化（semver 对比）
- 变更日志从 GitHub Release API 获取
- 可选自动升级（`--auto` 标志）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/upgrade/upgrade.ts` | `/upgrade` 命令、npm registry 检查 |

**Qwen Code 现状**：无 `/upgrade` 命令。用户需手动检查版本和执行升级。Qwen Code 有 `/version` 显示当前版本号，但没有检查更新和升级指导。

**Qwen Code 修改方向**：① 新建 `/upgrade` 命令（`commands/upgrade.ts`）；② 查询 npm registry 获取最新版本；③ 对比当前版本（semver）；④ 如有新版本，显示变更日志 + 升级命令。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~120 行
- 开发周期：~1 天（1 人）
- 难点：npm registry API 的可靠性（可能需回退到 GitHub Release API）

**改进前后对比**：
- **改进前**：检查更新 → 手动 `npm list` + 查 GitHub → 手动升级（~1 分钟）
- **改进后**：`/upgrade` → 自动检查 + 显示变更 + 指导升级（~5 秒）

**意义**：版本升级是用户保持最新的关键——简化流程提高升级率。
**缺失后果**：用户需手动检查版本——升级率低，可能错过重要修复。
**改进收益**：`/upgrade` = 自动检查 + 变更日志 + 升级指导——用户快速保持最新。

---

<a id="item-11"></a>

### 11. Plugin 系统增强（P2）

当前 Qwen Code 的扩展机制主要是 Skills（SKILL.md 文件）。Skill 系统很好用，但有一个限制：一个 Skill 只能定义一个 prompt 模板——不能提供命令（commands）、hooks（生命周期钩子）、MCP 服务器配置、或子代理（agents）定义。

**Claude Code 的 Plugin 系统——组件容器**：

一个 Plugin 可以提供 5 种组件（`PluginComponent`）：

| 组件类型 | 说明 | 示例 |
|---------|------|------|
| `commands` | 用户可交互的命令 | `/review`、`/bughunter` |
| `skills` | 模型可调用的技能 | "React 组件规范"、"Python 测试指南" |
| `hooks` | 生命周期钩子 | session 启动时加载特定配置 |
| `mcpServers` | MCP 服务器配置 | 数据库查询 MCP、Slack MCP |
| `output-styles` | 输出样式 | Learning 模式、Explanatory 模式 |

**Plugin 来源**：
- `builtin` — 随 CLI 分发，用户可通过 `/plugin` UI 启用/禁用
- `marketplace` — 第三方插件市场
- `--plugin-dir` — 本地开发调试

**Plugin 加载流程**：

```
1. 启动时：initBuiltinPlugins() 注册内置插件
2. getCommands() 调用时（memoized by cwd）：
   ├── getPluginSkills()   → 从 plugin 的 skills/ 目录加载
   ├── getPluginCommands() → 从 plugin 的 commands/ 目录加载
   └── 合并到命令注册中心
3. 运行时：/reload-plugins 命令清除缓存，重新加载
```

**Plugin 定义格式**（Markdown + frontmatter）：

```markdown
---
name: github-review
version: 1.0.0
commands:
  - name: review
    description: Review PRs with GitHub API
---

# GitHub Review Plugin

This plugin provides PR review capabilities using the GitHub API.

## Commands

### /review

Review the current branch's PR...
```

**关键设计**：
- 变量替换：`${CLAUDE_PLUGIN_ROOT}`、`${CLAUDE_SKILL_DIR}`、`${CLAUDE_SESSION_ID}`、`${user_config.X}`
- 启用/禁用：用户可通过 `/plugin` UI 切换 built-in plugins
- 缓存：`memoize` 加载结果，`clearPluginCommandCache()` 失效
- 错误处理：16 种 PluginError 类型（加载失败、解析错误、依赖缺失等）

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `plugins/builtinPlugins.ts` | 内置插件注册表 |
| `utils/plugins/loadPluginCommands.ts` | 从插件目录加载 Command 的核心逻辑 |
| `types/plugin.ts` | Plugin 类型定义 |
| `utils/plugins/schemas.ts` | PluginManifest JSON Schema |

**Qwen Code 现状**：Skill 系统支持良好（SKILL.md），但缺少 Plugin 概念——无法聚合多个组件（commands + skills + hooks + MCP servers）。用户也无法通过 UI 启用/禁用内置功能。

**Qwen Code 修改方向**：① 引入 Plugin 概念（`types/plugin.ts`）；② Plugin 作为组件容器（commands/skills/hooks/MCP）；③ `/plugin` UI 管理启用/禁用；④ 变量替换机制（`${PLUGIN_ROOT}` 等）；⑤ 缓存 + 失效策略。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~400 行
- 开发周期：~3 天（1 人）
- 难点：Plugin 与现有 Skill 系统的兼容性、变量替换的完整性

**改进前后对比**：
- **改进前**：扩展只能提供 Skill（prompt 模板）——无法聚合命令/hooks/MCP
- **改进后**：Plugin 提供多种组件——一个安装包包含完整功能——用户可启用/禁用

**意义**：Plugin 作为组件容器——聚合 commands/skills/hooks/MCP——扩展能力更强。
**缺失后果**：Skill 只能定义 prompt——无法提供更复杂的扩展（命令 + hooks + MCP）。
**改进收益**：Plugin 系统 = 组件容器 + 启用/禁用管理 + 变量替换——扩展能力大幅提升。

---

<a id="item-12"></a>

### 12. Task 统一框架（P2）

当前 Qwen Code 如果有多种后台执行体（Subagent、Shell 命令、Cron 任务等），它们可能各自独立管理——状态追踪、通知、内存管理分散在不同模块。这导致：难以统一查看所有后台任务、无法一致地切换前台/后台、内存管理策略不一致。

**Claude Code 的 Task 框架——统一任务管理**：

所有后台执行体统一为 `Task` 接口——共享注册、轮询、通知、内存管理机制：

```typescript
// Task 接口（极简设计）
type Task = {
  name: string
  type: TaskType
  kill(taskId: string): Promise<void>
}
```

**7 种 Task 类型**：

| 类型 | 说明 | 典型场景 |
|------|------|---------|
| `local_bash` | 本地 Shell 命令 | 运行测试、构建、lint |
| `local_agent` | 本地后台 Agent | 子代理并行执行 |
| `remote_agent` | 远程 Agent 会话 | CCR 远程审查 |
| `in_process_teammate` | 进程内队友 | Swarm 协作 |
| `local_workflow` | 工作流脚本 | 自动化流水线 |
| `monitor_mcp` | MCP 监控 | 监听 MCP 事件 |
| `dream` | 记忆整理 | Auto Dream 后台 consolidation |

**Task 状态机**：

```
pending → running → completed/failed/killed
                        ↑
                   notified=true（可被 GC 驱逐）
```

**框架机制**：

| 机制 | 说明 |
|------|------|
| 注册（`registerTask`） | 创建任务状态 → 添加到 AppState.tasks |
| 轮询（`pollTasks`） | 1000ms 间隔 → 读取磁盘输出 delta → 应用 offset + 驱逐 |
| 通知（`enqueueTaskNotification`） | 各任务类型自行发送完成/失败通知 |
| 内存管理（`evictTerminalTask`） | 终端任务 + notified + 超出 grace period → 删除 |
| 前台/后台切换（`registerForeground`） | Shell/Agent 任务支持一次性后台化 |

**关键设计**：
- **被动式任务管理**：Task 实现只提供 kill 逻辑，其余由外部驱动
- **Grace Period**：本地 Agent 任务终止后保留 30 秒供 UI 查看（`PANEL_GRACE_MS = 30000`）
- **消息上限**：队友消息上限 500 条（`TEAMMATE_MESSAGES_UI_CAP = 500`），超出丢弃最旧的
- **Stall Watchdog**：45 秒无输出增长 + 尾部匹配 prompt 模式 → 通知用户

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `Task.ts` | `TaskType`（7种）、`TaskStatus`（5种）、`Task` 接口 |
| `tasks.ts` | Task 注册中心、`getAllTasks()`、`getTaskByType()` |
| `utils/task/framework.ts` | `registerTask()`、`pollTasks()`、`generateTaskAttachments()`、`evictTerminalTask()` |
| `tasks/LocalAgentTask/LocalAgentTask.tsx` | 本地后台 Agent 任务 |
| `tasks/LocalShellTask/LocalShellTask.tsx` | 本地 Shell 任务 |
| `tasks/RemoteAgentTask/RemoteAgentTask.tsx` | 远程 Agent 任务 |
| `tasks/InProcessTeammateTask/InProcessTeammateTask.tsx` | 进程内队友任务 |
| `tasks/DreamTask/DreamTask.ts` | Dream 任务（记忆整理） |

**Qwen Code 现状**：Subagent、Shell、Cron 任务可能各自管理状态——缺少统一的 Task 框架。用户无法统一查看所有后台任务（`/tasks` 命令）。

**Qwen Code 修改方向**：① 定义统一 Task 接口（`types/task.ts`）；② 实现 Task 框架（`utils/task/framework.ts`）；③ 将 Subagent/Shell/Cron 适配为 Task 类型；④ 新建 `/tasks` 命令列出所有后台任务。

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~500 行
- 开发周期：~4 天（1 人）
- 难点：现有任务系统的重构（Subagent/Shell/Cron 状态管理迁移）

**改进前后对比**：
- **改进前**：后台任务分散管理——Subagent/Shell/Cron 各自独立——无法统一查看
- **改进后**：统一 Task 框架——所有任务共享注册/轮询/通知/内存管理——`/tasks` 一目了然

**意义**：统一 Task 框架简化后台任务管理——一致性 + 可观测性。
**缺失后果**：后台任务管理分散——难以统一查看/管理。
**改进收益**：Task 框架 = 统一接口 + 注册/轮询/通知/内存管理 + `/tasks` 命令——后台任务一目了然。

---

## 总结

本文件涵盖 12 项 P2 用户体验与交互增强改进：

| # | 改进点 | 优先级 | 开发周期 | 意义 |
|---|--------|:------:|:--------:|------|
| 1 | [/plan 计划模式](#item-1) | P2 | ~2 天 | 计划可视化 + 审批流程 |
| 2 | [/review PR 审查](#item-2) | P2 | ~2 天 | 自动 PR 审查 |
| 3 | [/branch 会话分支](#item-3) | P2 | ~2 天 | 零风险探索替代方案 |
| 4 | [/doctor 环境诊断](#item-4) | P2 | ~1.5 天 | 一键环境诊断 |
| 5 | [/cost 费用追踪](#item-5) | P2 | ~1 天 | API 费用透明化 |
| 6 | [/session 会话管理](#item-6) | P2 | ~2 天 | 列表/搜索/删除 session |
| 7 | [/share 分享会话](#item-7) | P2 | ~2 天 | 一键分享 session |
| 8 | [/diff 代码差异](#item-8) | P2 | ~2 天 | 内嵌 diff 查看 |
| 9 | [/rename 重命名会话](#item-9) | P2 | ~0.5 天 | 自定义 session 名称 |
| 10 | [/upgrade 版本升级](#item-10) | P2 | ~1 天 | 自动检查 + 升级指导 |
| 11 | [Plugin 系统增强](#item-11) | P2 | ~3 天 | 组件容器 + 启用管理 |
| 12 | [Task 统一框架](#item-12) | P2 | ~4 天 | 统一后台任务管理 |

**总计**：~23 天（1 人）

> **免责声明**: 以上分析基于 2026 年 Q1 Claude Code（`../claude-code-leaked`）与 Qwen Code（`../qwen-code`）源码对比，可能已过时。
