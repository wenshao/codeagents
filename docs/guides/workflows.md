# 5. 实操工作流教程

本指南通过五个真实开发场景，演示如何使用不同的 Code Agent 工具完成实际任务。每个工作流包含具体的命令示例和提示词，你可以直接复制使用。

> **前置条件**：请先阅读 [入门指南](getting-started.md) 完成工具安装和基本配置。

---

## 简介

阅读工具文档只是第一步，真正的生产力提升来自于掌握完整的工作流。本教程覆盖以下五个高频场景：

| 工作流 | 核心任务 | 推荐工具 |
|--------|----------|----------|
| 修复 GitHub Issue | 从 issue 到 PR 的完整闭环 | Claude Code / Aider |
| 添加新功能 | 多文件协调开发 | Cursor / Claude Code |
| 代码审查与重构 | 质量改进和架构优化 | Claude Code / Aider |
| 调试生产问题 | 日志分析与问题定位 | Goose / Claude Code |
| 多文件批量修改 | 大规模一致性变更 | Aider / SWE-agent |

---

## 工作流 1：修复 GitHub Issue

### 场景描述

你在 GitHub 上收到一个 bug 报告：用户在提交表单时遇到 500 错误，issue 编号为 `#142`。需要分析问题、修复代码、编写测试并提交 PR。

### Claude Code 工作流

**第一步：读取并理解 Issue**

```bash
# 启动 Claude Code 并让它读取 issue
claude

> 读取 GitHub issue #142 的内容，分析问题原因并制定修复计划
```

Claude Code 会通过 `gh` 命令自动拉取 issue 内容，然后分析相关代码。

**第二步：定位问题代码**

```
> 根据 issue 中的错误描述，搜索相关的表单提交处理代码，找出导致 500 错误的根因
```

Claude Code 会搜索代码库，找到相关文件并分析调用链。

**第三步：实施修复**

```
> 修复这个 bug。确保处理空值的边界情况，并添加适当的错误信息返回给用户
```

**第四步：编写测试**

```
> 为这次修复编写单元测试，覆盖正常提交、空值提交和无效数据三种情况
```

**第五步：提交 PR**

```
> 创建一个 PR 修复 #142，包含清晰的描述说明修复了什么问题以及如何修复的
```

Claude Code 会自动完成 git add、commit、push 并使用 `gh pr create` 创建 PR。

### Aider 工作流

**第一步：了解 Issue 并添加相关文件**

```bash
# 先手动查看 issue
gh issue view 142

# 启动 aider 并加入相关文件
aider src/handlers/form.py src/validators/input.py tests/test_form.py
```

**第二步：描述问题让 Aider 修复**

```
> issue #142 报告表单提交时出现 500 错误。问题在于 form.py 的 submit_handler
> 函数没有处理 email 字段为空的情况。请修复这个问题，在 validator 中添加空值
> 检查，并在 handler 中返回 400 而不是让异常冒泡到 500。
```

Aider 会同时编辑多个文件并显示 diff。

**第三步：添加测试**

```
> 在 test_form.py 中添加测试用例：test_submit_empty_email 和
> test_submit_missing_fields，验证修复后返回正确的错误码和消息
```

**第四步：提交代码**

```
> /commit
```

Aider 会自动生成 commit message 并提交。然后手动创建 PR：

```bash
git push origin fix/issue-142
gh pr create --title "Fix #142: Handle empty email in form submission" \
  --body "修复表单提交时 email 为空导致的 500 错误"
```

### 关键差异对比

| 对比维度 | Claude Code | Aider |
|----------|-------------|-------|
| Issue 读取 | 自动通过 gh 拉取 | 需手动查看后粘贴或描述 |
| 文件发现 | 自动搜索整个代码库 | 需手动添加相关文件 (`/add`) |
| 上下文管理 | 自动管理，按需读取 | 显式控制，使用 repo-map 辅助 |
| 代码编辑 | 直接修改文件 | 显示 diff 后确认应用 |
| Git 操作 | 自动完成完整 PR 流程 | 自动 commit，PR 需手动创建 |
| 适合场景 | 不确定问题在哪里时 | 已知需要改哪些文件时 |

---

## 工作流 2：添加新功能

### 场景描述

需要为一个 Web 应用添加「用户通知偏好设置」功能，包括数据库模型、API 接口、前端页面。

### Cursor 工作流

**第一步：用 @ 引用建立上下文**

在 Cursor 的 Composer（`Cmd+I`）中输入：

```
为项目添加用户通知偏好功能。

参考以下现有代码的模式：
@src/models/user.py - 数据模型的定义方式
@src/routes/profile.py - API 路由的组织方式
@src/templates/settings.html - 前端页面的模板结构
@docs/api.md - API 文档格式

需要创建：
1. NotificationPreference 数据模型（邮件通知、推送通知、通知频率）
2. GET/PUT /api/notifications/preferences 接口
3. 设置页面中的通知偏好面板
4. 对应的单元测试
```

**第二步：逐步审查生成的代码**

Cursor 会在 Composer 面板中展示所有要创建和修改的文件。逐个审查：

- 点击每个文件查看 diff
- 对不满意的部分直接在对话中要求修改
- 确认后点击 "Accept All" 应用变更

**第三步：使用内联编辑微调**

选中某段代码，按 `Cmd+K` 进行内联编辑：

```
将通知频率从字符串改为枚举类型，支持 REALTIME、DAILY、WEEKLY 三个值
```

**第四步：使用 Background Agent 运行测试**

如果有 Cursor 的 Background Agent 功能：

```
运行所有通知相关的测试，修复失败的用例，确保测试全部通过
```

Background Agent 会在后台自动运行测试、分析失败原因并修复代码。

### Claude Code 工作流

**第一步：制定计划**

```bash
claude

> 我需要为项目添加用户通知偏好功能。请先分析现有代码结构和模式，然后制定
> 一个实施计划。功能包括：数据模型、REST API、前端页面和测试。不要开始写代码，
> 先给我看计划。
```

Claude Code 会扫描项目结构，分析现有代码模式，输出一份分步计划。

**第二步：按计划逐步实施**

```
> 按照计划执行第一步：创建 NotificationPreference 数据模型和数据库迁移
```

审查输出后继续：

```
> 很好，继续第二步：创建 API 路由和处理函数
```

```
> 继续第三步：创建前端设置页面
```

**第三步：运行测试验证**

```
> 为新功能编写完整的测试，然后运行测试套件确保所有测试通过
```

**第四步：整理提交**

```
> 将所有变更按逻辑分成多个 commit 提交：模型变更一个、API 一个、前端一个、测试一个
```

### 两种方式的选择建议

| 场景 | 推荐工具 | 原因 |
|------|----------|------|
| 需要大量前端可视化调整 | Cursor | 实时预览 + 内联编辑更高效 |
| 后端为主的功能开发 | Claude Code | 自动搜索依赖和调用链更强 |
| 团队有统一 IDE 习惯 | Cursor | 降低切换成本 |
| 需要复杂的 git 操作 | Claude Code | 原生支持完整 git 工作流 |

---

## 工作流 3：代码审查与重构

### 场景描述

团队成员提交了一个大 PR（修改了 15 个文件），你需要进行代码审查，之后对遗留代码进行重构。

### Claude Code 审查工作流

**第一步：审查 PR**

```bash
claude

> 审查 PR #89 的所有变更。关注以下方面：
> 1. 是否有潜在的 bug 或边界情况未处理
> 2. 是否符合项目的代码风格
> 3. 是否有性能问题
> 4. 测试覆盖是否充分
```

Claude Code 会自动执行 `gh pr diff 89` 获取变更，逐文件分析。

**第二步：查看特定文件的细节**

```
> 重点分析 src/services/payment.py 的变更，这个文件处理支付逻辑，需要特别仔细
```

**第三步：提交审查意见**

```
> 将审查发现整理成 PR review comment 提交到 GitHub，对有问题的代码行添加行内评论
```

**第四步：审查后的重构**

发现代码中有重复模式后，进行重构：

```
> 我注意到 payment.py、subscription.py 和 refund.py 中有大量重复的金额计算
> 和验证逻辑。请将这些公共逻辑提取到一个新的 MoneyUtils 工具类中，然后
> 更新三个文件使用这个工具类。确保所有现有测试仍然通过。
```

### Aider /architect 模式

Aider 的 architect 模式特别适合大规模重构，因为它将「规划」和「执行」分为两个模型处理。

**第一步：进入 architect 模式**

```bash
aider --architect
```

或在会话中切换：

```
> /chat-mode architect
```

**第二步：描述重构目标**

```
> 项目中的数据验证逻辑分散在各个 handler 文件中，我想统一迁移到一个集中的
> 验证层。请分析当前的验证逻辑分布，设计一个集中式验证架构，然后逐步重构。
```

在 architect 模式下，高能力模型（如 Claude Opus）负责生成重构方案，编辑模型（如 Claude Sonnet）负责执行具体的代码修改。

**第三步：添加需要重构的文件**

```
> /add src/handlers/*.py src/validators/*.py
```

**第四步：分步执行重构**

Architect 模型会输出分步计划，编辑模型逐步执行。你可以在每一步之后审查变更：

```
> /diff
```

查看当前的所有变更，确认后继续：

```
> 继续下一步重构
```

**第五步：验证重构结果**

```
> /run python -m pytest tests/ -v
```

### 审查与重构的最佳搭配

```
审查阶段：Claude Code（自动获取 PR diff，全局分析能力强）
     │
     ▼
规划阶段：Aider /architect（高能力模型做方案设计）
     │
     ▼
执行阶段：Aider（精确的多文件编辑 + 自动 commit）
     │
     ▼
验证阶段：Claude Code（运行测试 + 回归检查）
```

---

## 工作流 4：调试生产问题

### 场景描述

生产环境报警：API 响应时间从 200ms 飙升到 5s，部分请求超时。需要快速定位和修复问题。

### Goose + MCP 工具工作流

Goose 的优势在于可以通过 MCP 扩展连接各种外部工具。

**第一步：配置 MCP 扩展**

确保 `~/.config/goose/config.yaml` 中配置了相关的 MCP 扩展：

```yaml
extensions:
  grafana:
    type: stdio
    cmd: npx
    args: [-y, "@anthropic/grafana-mcp"]
    env:
      GRAFANA_URL: https://grafana.company.com
      GRAFANA_API_KEY: ${GRAFANA_API_KEY}
  sentry:
    type: stdio
    cmd: npx
    args: [-y, "@anthropic/sentry-mcp"]
    env:
      SENTRY_TOKEN: ${SENTRY_TOKEN}
```

**第二步：启动 Goose 并分析问题**

```bash
goose

> 生产环境 API 响应变慢，请帮我排查：
> 1. 先查看 Grafana 最近 1 小时的 API 响应时间面板
> 2. 检查 Sentry 中最近的错误报告
> 3. 分析是否有异常的数据库查询
```

Goose 会通过 MCP 工具调用 Grafana 和 Sentry 的 API，获取监控数据和错误日志。

**第三步：根据分析结果深入排查**

```
> Grafana 显示数据库查询时间异常上升，请进一步分析：
> 1. 查看慢查询日志中最近 1 小时的 TOP 10 查询
> 2. 检查是否有最近的代码部署引入了新的查询
```

**第四步：定位到具体代码**

```
> 慢查询指向 users 表的全表扫描。请查找代码中所有查询 users 表的地方，
> 找出缺少索引或 WHERE 条件的查询
```

### Claude Code 日志分析工作流

**第一步：获取并分析日志**

```bash
claude

> 我把最近的应用日志下载到了 /tmp/app-logs/ 目录。请分析这些日志，
> 找出 API 响应变慢的原因。重点关注：
> 1. 响应时间超过 1s 的请求
> 2. 数据库查询耗时
> 3. 错误和异常堆栈
```

**第二步：关联代码分析**

```
> 日志显示 /api/users/search 接口的数据库查询耗时从 50ms 增长到 3s。
> 请查看这个接口的实现代码，分析查询性能问题的根因
```

**第三步：实施修复**

```
> 问题是 search 函数在用户量增长后没有使用索引。请做以下修复：
> 1. 为 users 表添加复合索引的迁移脚本
> 2. 优化查询语句使用索引
> 3. 添加查询结果的分页限制
```

**第四步：添加监控防护**

```
> 为这个接口添加慢查询告警：如果数据库查询超过 500ms，记录 warning 日志。
> 同时添加一个简单的查询缓存，缓存热门搜索结果 5 分钟
```

### 调试工具选择

| 需求 | 推荐 | 原因 |
|------|------|------|
| 需要查看监控面板 | Goose + MCP | 可直接对接 Grafana/Datadog |
| 需要查看错误追踪 | Goose + MCP | 可直接对接 Sentry/Bugsnag |
| 分析本地日志文件 | Claude Code | 强大的文件读取和模式识别 |
| 定位代码层面问题 | Claude Code | 全代码库搜索和分析能力 |
| 需要修复代码 | Claude Code / Aider | 直接编辑代码并测试 |

---

## 工作流 5：多文件批量修改

### 场景描述

项目要从 `logging` 模块迁移到 `structlog`，涉及 50+ 个文件的修改。每个文件需要：更换 import 语句、修改 logger 初始化方式、将 `logger.info("msg")` 改为 `logger.info("msg", key=value)` 结构化格式。

### Aider 批量编辑工作流

Aider 的 repo-map 功能让它在大规模批量编辑中特别有效。

**第一步：准备工作**

```bash
# 先查看需要修改的文件范围
grep -rl "import logging" src/ | wc -l
# 输出: 53

# 启动 aider，使用高上下文模型
aider --model claude-sonnet-4-20250514
```

**第二步：分批添加文件**

不要一次添加所有 53 个文件，分模块处理：

```
> /add src/services/*.py
```

**第三步：描述批量修改规则**

```
> 请将所有已添加文件中的 logging 迁移到 structlog：
> 1. 将 `import logging` 替换为 `import structlog`
> 2. 将 `logger = logging.getLogger(__name__)` 替换为
>    `logger = structlog.get_logger(__name__)`
> 3. 将所有 logger.info/warning/error 调用中的 f-string 或 % 格式化
>    改为关键字参数形式。例如：
>    - 旧: logger.info(f"User {user_id} logged in")
>    - 新: logger.info("user_logged_in", user_id=user_id)
> 4. 保持 logger.exception 的调用方式不变
```

Aider 会逐个文件应用修改并显示 diff。

**第四步：处理下一批文件**

```
> /clear
> /add src/handlers/*.py
> 用同样的规则迁移这些文件中的 logging 到 structlog
```

**第五步：验证所有修改**

```
> /run python -m pytest tests/ -x -v
```

如果有测试失败，Aider 会自动分析失败原因并建议修复。

### SWE-agent 自动化工作流

SWE-agent 适合将重复性的修改任务完全自动化。

**第一步：创建任务描述**

创建一个任务文件 `task.md`：

```markdown
将项目中所有 Python 文件的 logging 模块迁移到 structlog。

具体规则：
1. 替换 import 语句
2. 替换 logger 初始化
3. 将格式化字符串改为结构化参数
4. 运行测试确保没有回归

不要修改 tests/ 目录下的测试文件中的 logging 调用。
```

**第二步：运行 SWE-agent**

```bash
python -m swe_agent run \
  --agent.model.name claude-sonnet-4-20250514 \
  --problem_statement.path task.md \
  --env.repo.path /path/to/your/project
```

SWE-agent 会自主完成以下步骤：
1. 扫描需要修改的文件
2. 逐个文件进行修改
3. 运行测试验证
4. 生成补丁文件

**第三步：审查生成的补丁**

```bash
# SWE-agent 的输出在 trajectories/ 目录下
# 审查生成的 patch
cat trajectories/*/patches/*.patch

# 手动应用补丁
git apply trajectories/*/patches/*.patch
```

### 批量修改策略对比

| 维度 | Aider | SWE-agent |
|------|-------|-----------|
| 交互性 | 交互式，可逐步确认 | 全自动，运行后查看结果 |
| 可控性 | 高，每步可介入 | 低，结果可能需要手动调整 |
| 效率 | 中等（需要分批处理） | 高（全自动执行） |
| 准确性 | 高（有 repo-map 辅助） | 中等（取决于任务复杂度） |
| 适合场景 | 规则明确但需判断的修改 | 机械性的统一替换 |

---

## 最佳实践

### 提示词编写

**具体胜过模糊**

```
# 不好
> 修复这个 bug

# 好
> 修复 src/auth/login.py 中 verify_token 函数的 bug：当 token 过期时
> 应该返回 401 而不是 500。错误日志：[粘贴具体错误]
```

**提供约束条件**

```
# 不好
> 添加缓存功能

# 好
> 为 /api/products 接口添加 Redis 缓存，要求：
> - 缓存时间 5 分钟
> - 使用项目已有的 redis_client（见 src/config/redis.py）
> - 缓存 key 格式：products:{category}:{page}
> - 写入新产品时清除对应分类的缓存
```

**分步执行复杂任务**

```
# 不好
> 把整个项目从 REST 迁移到 GraphQL

# 好
> 让我们分步将 API 迁移到 GraphQL：
> 第一步：先只为 User 模型创建 GraphQL schema 和 resolver，
> 保持 REST 接口不变，两者并行运行。我们之后再处理其他模型。
```

### 上下文管理

| 工具 | 上下文策略 |
|------|-----------|
| Claude Code | 让工具自动搜索，只在需要时用 `@file` 主动指定 |
| Aider | 精确使用 `/add` 和 `/drop` 管理，利用 `/tokens` 监控用量 |
| Cursor | 善用 `@` 引用，在 Composer 中限制上下文范围 |
| Goose | 通过 MCP 扩展按需接入外部上下文 |

### 代码审查习惯

1. **先看 diff 再接受**：任何工具生成的代码都应该在应用前审查
2. **分步提交**：大的变更拆成多个小 commit，方便回滚
3. **运行测试**：每次修改后都运行相关测试
4. **检查边界**：AI 生成的代码经常忽略错误处理和边界情况

```bash
# Claude Code：修改后立即验证
> 运行与修改文件相关的测试，确认没有回归

# Aider：使用内置命令运行测试
> /run pytest tests/test_modified_module.py -v

# Cursor：使用终端面板运行
# Ctrl+` 打开终端，手动运行测试
```

### 安全注意事项

- **不要把密钥写进提示词**：使用环境变量引用，如 `$API_KEY`
- **审查所有文件变更**：AI 可能意外修改配置文件或添加不安全的依赖
- **检查 .gitignore**：确保 AI 创建的临时文件和配置不会被提交
- **生产环境操作谨慎**：用 AI 生成数据库迁移或部署脚本时务必人工审查

---

## 工具组合推荐

不同任务适合不同的工具组合。以下是经过验证的高效搭配：

### 日常开发组合

```
主力工具：Claude Code（终端）或 Cursor（IDE）
辅助工具：Aider（Git 重度操作）

典型一天：
  早上 → Claude Code 处理 issue 和 PR review
  编码 → Cursor 进行功能开发
  提交 → Aider 整理 commit 和 PR
```

### 大型重构组合

```
规划：Claude Code（全局分析 + 方案设计）
执行：Aider /architect（分步重构 + 自动 commit）
验证：Claude Code（运行测试 + 回归检查）
```

### 全栈开发组合

```
后端 API：Claude Code（路由、模型、业务逻辑）
前端页面：Cursor（组件开发 + 实时预览）
数据库：Claude Code（迁移脚本 + 查询优化）
部署：Goose + MCP（对接 CI/CD 和云平台）
```

### 开源贡献组合

```
理解项目：Claude Code（快速分析大型代码库结构）
小修复：Aider（精确编辑 + 规范的 commit message）
大功能：Claude Code（规划）→ Aider（执行）
```

### 团队协作组合

```
代码审查：Claude Code（自动分析 PR）
知识共享：Cursor（IDE 内 AI 辅助降低学习曲线）
一致性保障：Aider + lint 规则（自动格式化和规范检查）
```

### 组合选择速查表

| 你的角色 | 推荐主力 | 推荐辅助 | 理由 |
|----------|----------|----------|------|
| 后端工程师 | Claude Code | Aider | 终端原生 + Git 深度集成 |
| 前端工程师 | Cursor | Claude Code | IDE 集成 + 可视化预览 |
| 全栈工程师 | Claude Code | Cursor | 后端命令行 + 前端 IDE |
| DevOps | Goose | Claude Code | MCP 扩展 + 脚本编写 |
| 开源维护者 | Claude Code | Aider | PR 审查 + 批量编辑 |
| 初学者 | Cursor | Claude Code | 低门槛 + 可视化学习 |

---

> **下一步**：根据你最常见的工作场景选择一个工作流，在实际项目中练习。熟练后再尝试工具组合，逐步找到最适合你的开发模式。
