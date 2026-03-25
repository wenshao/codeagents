# 2. Claude Code 用户使用指南

> 从安装到精通，面向新用户和进阶用户的完整指南。

---

## 快速开始（2 分钟）

### 安装

```bash
# 推荐方式
curl -fsSL https://claude.ai/install.sh | bash

# macOS Homebrew
brew install --cask claude-code

# 验证
claude --version
```

### 第一次使用

```bash
# 进入项目目录
cd your-project

# 启动交互式会话
claude

# 直接提问
claude "这个项目的技术栈是什么？"

# 管道模式（脚本/CI 使用）
claude -p "修复 src/auth.ts 中的 bug" > fix.txt
```

首次启动会引导你登录 Anthropic 账户。

---

## 日常使用

### 对话式开发

```
你: 修复登录页面的表单验证
Claude: [读取相关文件] → [分析代码] → [编辑文件] → [运行测试]
      已修复 src/components/LoginForm.tsx 中的验证逻辑。
      主要更改：添加了邮箱格式和密码强度检查。

你: 再加一个用户名长度限制
Claude: [编辑文件] → 已添加用户名 3-20 字符长度限制。

你: /commit
Claude: [分析 diff] → [生成消息] → 已提交: "Add form validation for login page"
```

### 常用操作速查

| 你想做什么 | 命令 |
|-----------|------|
| 提问不修改代码 | 直接问（Claude 会判断是否需要编辑） |
| 审查代码 | `/review` 或 `/code-review --comment` |
| 提交代码 | `/commit` |
| 提交+推送+创建 PR | `/commit-push-pr` |
| 简化优化代码 | `/simplify` |
| 切换模型 | `/model`（Sonnet 日常，Opus 复杂任务） |
| 查看费用 | `/cost` |
| 压缩上下文 | `/compact`（或等自动触发） |
| 恢复之前的会话 | `/resume` |
| 回退到之前的状态 | `/rewind` 或按 `Esc` |

---

## 理解命令体系

Claude Code 有 **~60 个命令**，分四种类型：

### prompt 类型（LLM 执行）

这类命令把提示词发给 LLM，LLM 用工具完成任务。

```bash
/review          # 代码审查（4-6 个并行代理，置信度过滤）
/commit          # Git 提交（分析 diff，生成消息）
/commit-push-pr  # 一键提交+推送+创建 PR
/init            # 初始化项目（生成 CLAUDE.md）
/simplify        # 代码简化（3 个并行代理：复用/质量/效率）
/batch           # 大规模并行变更（5-30 个 worktree 代理）
```

### local-jsx 类型（本地 UI）

渲染终端 UI 组件，不调用 LLM。

```bash
/model           # 模型选择器
/config          # 配置面板
/permissions     # 权限管理
/mcp             # MCP 服务器管理
/memory          # 记忆编辑器
/resume          # 会话恢复选择器
/plan            # 规划模式开关
/diff            # 查看文件变更
/hooks           # Hook 配置查看
```

### local 类型（直接执行）

不调用 LLM，直接在本地执行。

```bash
/compact         # 压缩上下文（三层压缩算法）
/clear           # 清除对话历史
/context         # 可视化上下文使用率（彩色网格）
/cost            # 查看 token 消耗和费用
/doctor          # 诊断安装健康状态
/vim             # 切换 Vim 编辑模式
/voice           # 语音模式（Push-to-talk）
/rewind          # 回退到之前的检查点
```

### Skill 类型（可扩展）

通过 SKILL.md 文件定义，可以自己创建。

```bash
/loop 5m /review     # 每 5 分钟循环审查
/schedule            # 远程定时任务（CCR 云端）
/security-review     # 安全审查（插件）
/simplify            # 代码简化（内置 Skill）
```

---

## 进阶技巧

### 1. 利用子代理并行加速

```
你: 请并行完成以下三件事：
    1. 修复 auth 模块的 bug
    2. 给 utils 添加单元测试
    3. 更新 README 文档

Claude: [启动 3 个并行子代理]
        Agent 1: 修复 auth...
        Agent 2: 编写测试...
        Agent 3: 更新文档...
        全部完成。
```

Claude 会自动使用 Agent 工具启动子代理。你也可以明确要求"并行"。

### 2. 使用 /btw 避免上下文污染

```
你: [正在讨论复杂的数据库迁移]

你: /btw TypeScript 的 Record 类型怎么用？

Claude: [在独立上下文中回答，不影响主对话]
        Record<K, V> 创建一个键为 K、值为 V 的对象类型...

你: [继续数据库迁移讨论，上下文未被污染]
```

### 3. 自定义 CLAUDE.md

在项目根目录创建 `CLAUDE.md`：

```markdown
# 项目规范

## 技术栈
- Next.js 14 + TypeScript + Tailwind
- PostgreSQL + Prisma ORM

## 构建命令
- `pnpm test` 运行测试
- `pnpm lint` 代码检查

## 编码规范
- 函数式组件 + React Hooks
- Conventional Commits 格式
- 不要修改 prisma/migrations/ 目录
```

Claude 会在每次会话中自动读取并遵守这些规范。`/review` 还会检查代码是否违反 CLAUDE.md 中的规则。

### 4. 配置权限自动化

编辑 `~/.claude/settings.json`：

```json
{
  "permissions": {
    "allow": [
      "Read", "Glob", "Grep",
      "Bash(pnpm test)", "Bash(pnpm lint)",
      "Bash(git:*)", "Bash(gh pr:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)", "Write(.env*)"
    ]
  }
}
```

这样 Claude 执行测试、lint、git 操作时不再每次确认。

### 5. MCP 扩展能力

创建 `.mcp.json`（项目级）：

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {"DATABASE_URL": "postgresql://localhost:5432/mydb"}
    }
  }
}
```

现在 Claude 可以直接查询你的数据库。

### 6. Hook 自动化

使用 `/hookify` 自动创建 Hook：

```
你: /hookify 不要直接在 main 分支上提交

Claude: [分析需求] → 已创建 .claude/hookify.block-main-push.local.md
        规则立即生效，无需重启。
```

或手动创建 `.claude/hookify.warn-env.local.md`：

```markdown
---
name: warn-env-file
enabled: true
event: bash
pattern: cat.*\.env|echo.*\.env
action: warn
---

⚠️ 检测到可能读取 .env 文件的操作。请确认不会泄露敏感信息。
```

### 7. 利用 /plan 模式安全探索

```bash
/plan          # 进入规划模式（只读，不修改任何文件）

你: 分析这个项目的架构，画出模块依赖关系

Claude: [只读取文件，不编辑]
        项目架构分析：
        src/
        ├── api/ → 依赖 services/
        ├── services/ → 依赖 models/
        └── models/ → 独立
        建议将 utils/auth.ts 移到 services/ ...

/plan          # 退出规划模式，恢复正常编辑能力
```

### 8. 高效使用模型

| 场景 | 推荐模型 | 命令 |
|------|---------|------|
| 日常编码 | Sonnet 4.6 | `/model sonnet`（默认） |
| 复杂推理 | Opus 4.6 | `/model opus` |
| 快速问答 | Haiku 4.5 | `/model haiku` |
| 大文件分析 | Sonnet 4.6[1m] | `/model sonnet[1m]` |

Opus 比 Sonnet 贵 5 倍但推理更强。简单任务用 Sonnet，复杂架构决策用 Opus。

---

## 工作流示例

### 工作流 1：修复 Bug

```bash
claude                              # 启动
你: 用户报告登录后 session 丢失       # 描述问题
# Claude 自动：读取代码 → 定位问题 → 修复 → 运行测试
/review                             # 自审查
/commit                             # 提交
```

### 工作流 2：开发新功能

```bash
/plan                               # 先进入规划模式
你: 添加用户头像上传功能
# Claude 只读分析，不修改文件，输出实施计划
/plan                               # 退出规划模式

你: 按照计划实施
# Claude 编辑文件、创建组件、更新路由
/simplify                           # 优化代码质量
/review                             # 审查
/commit-push-pr                     # 提交+推送+创建 PR
```

### 工作流 3：持续监控

```bash
/loop 10m /review                   # 每 10 分钟审查代码
# 或
/schedule                           # 设置远程定时任务
```

### 工作流 4：大规模重构

```bash
/batch 将所有 console.log 替换为 logger.info
# Claude 自动：
# 1. 分析范围
# 2. 启动 5-30 个并行代理（每个在独立 worktree）
# 3. 每个代理处理一部分文件
# 4. 汇总结果
```

---

## 费用管理

### 查看费用

```bash
/cost              # 查看当前会话费用
/usage             # 查看整体使用量
/stats             # 详细统计
```

### 省钱技巧

| 技巧 | 方法 | 节省 |
|------|------|------|
| 用小模型做简单事 | `/model haiku` 回答问题 | 5-10x |
| 及时压缩 | `/compact` 在任务边界执行 | 减少累积 token |
| 利用缓存 | 保持会话连续性（`claude -c`） | Prompt Caching 生效 |
| 订阅 vs API | 日均 >$3.3 选 Max $100 | 上限封顶 |
| 规划先行 | `/plan` 想清楚再动手 | 减少返工 |

### 计划对比

| 计划 | 月费 | 适合 |
|------|------|------|
| Pro | $20 | 轻度使用 |
| Max 5x | $100 | 日常开发（默认 Opus） |
| Max 20x | $200 | 重度使用 |
| API | 按量 | CI/CD、批量任务 |

---

## 常见问题

### Claude 不理解我的项目

```bash
/init              # 让 Claude 分析项目并生成 CLAUDE.md
```

或手动创建 `CLAUDE.md` 告诉 Claude 项目的技术栈和规范。

### 上下文太长，Claude 开始遗忘

```bash
/compact           # 手动压缩
/compact 保留数据库相关讨论    # 压缩但保留特定话题
```

### 想回到之前的状态

```bash
/rewind            # 或按 Esc 键
# 选择回退点，恢复文件和对话
```

### Claude 执行了不想要的操作

按 `Esc` 立即中断当前操作。使用 `/rewind` 回退。

设置权限预防：
```json
{"permissions": {"deny": ["Bash(rm -rf:*)", "Write(.env*)"]}}
```

### 想在多个项目间切换

```bash
claude --resume    # 恢复之前的会话
claude -c          # 继续最近的对话
```

### 想让 Claude 更简洁/更详细

```bash
/config            # 打开配置面板，调整输出风格
# 或在 CLAUDE.md 中指定：
# "回答要简洁，每次不超过 3 句话"
```

---

## 安全须知

Claude Code 内置了业界最严格的安全系统：

- **28 条操作阻止规则**（如禁止 force push、禁止删除共享资源、禁止数据外泄）
- **双阶段安全分类器**（自动模式下，独立 LLM 评估每个操作的风险）
- **5 层设置优先级**（Managed > CLI > Local > Project > User）
- **沙箱隔离**（macOS Seatbelt / Linux Docker）

你不需要配置任何安全设置——默认就是安全的。但如果你在自动模式下运行（`--permission-mode auto`），安全分类器会额外保护你。

---

---

## 高频技巧（来自社区最佳实践）

> 以下技巧综合自 Builder.io、Anthropic 官方、DataCamp、awesome-claude-code 等高质量指南。

### 9. `.claudeignore` 减少 token 浪费

在项目根目录创建 `.claudeignore`（类似 .gitignore）：

```
node_modules/
dist/
build/
*.min.js
*.map
coverage/
.next/
```

> **效果：** 典型 Node.js 项目减少 ~25% token 消耗。Claude 不会读取被忽略的文件。

### 10. 反馈循环：让 Claude 自验证

**最高杠杆技巧**（Anthropic 官方推荐，质量提升 2-3 倍）：

```
你: 实现邮箱验证函数。
    测试用例：user@example.com → true，"invalid" → false。
    实现后运行测试。

你: [粘贴截图] 实现这个设计。完成后截图对比原图，列出差异并修复。
```

关键：**给 Claude 一个检查自身工作的方法**——测试命令、linter 输出、截图对比。

### 11. CLAUDE.md 最佳实践

**控制长度：** 保持在 200 行以内。过长会导致规则被忽略（~80% 遵守率 vs 过长时下降）。

**WHAT/WHY/HOW 框架：**
```markdown
## WHAT（技术栈和结构）
Next.js 14 + TypeScript + Prisma

## WHY（目的和约束）
电商平台，需要 SEO 友好，支持多语言

## HOW（工作流规则）
- 先写测试再实现
- 提交前运行 pnpm lint
```

**多级层级：**
- `~/.claude/CLAUDE.md` — 个人全局默认
- `项目根/CLAUDE.md` — 项目共享
- `子目录/CLAUDE.md` — 模块级覆盖

**关键区分：** CLAUDE.md 是**建议**（~80% 遵守）。需要 100% 强制执行的规则用 **Hooks**。

### 12. `/clear` 纪律

```bash
# 完成一个任务后，开始另一个前
/clear

# 修正 3 次仍不对？不要继续修正——清除重来
/clear
# 用更好的初始提示重新开始
```

> **社区共识：** 一个干净的会话 + 更好的提示，几乎总是优于一个长会话 + 多次修正。

### 13. 先规划再执行（最常被推荐的模式）

```
你: 我想添加 Google OAuth 登录。
    先创建一个计划，不要写代码。
    列出需要修改的文件和步骤。

Claude: [只读分析] 计划如下：
        1. 安装 next-auth
        2. 修改 src/auth/...
        ...

你: 计划看起来可以。开始实施。
    写完后运行测试套件，修复任何失败。
```

> **经验法则：** 如果你能一句话描述 diff，跳过规划。否则先规划。

### 14. 写手/审查者分离

```bash
# 会话 A：实现
claude
你: 实现 API 限流中间件

# 会话 B（新会话）：审查
claude
你: 审查 @src/middleware/rateLimiter.ts
    检查边界条件、竞态、与现有中间件的一致性

# 会话 A：修复
你: 以下是审查反馈：[粘贴会话 B 的输出]
    请修复这些问题。
```

> **原理：** 新会话没有"我刚写的代码"的偏见，审查更客观。

### 15. 用 `@` 引用文件

```
你: 参考 @src/widgets/HotDogWidget.tsx 的实现模式，
    创建一个新的 CalendarWidget

你: 修复 @src/auth/session.ts:42 附近的 token 刷新逻辑
```

> **一个好的示例文件胜过十段描述。**

---

## 延伸阅读

- [60+ 命令完整参考](../tools/claude-code/02-commands.md)
- [技术架构（反编译分析）](../tools/claude-code/03-architecture.md)
- [Skill 与插件系统](../tools/claude-code/05-skills.md)
- [设置与安全（含 28 条 BLOCK 规则）](../tools/claude-code/06-settings.md)
- [配置示例对比](./config-examples.md)
- [/review 深度分析](../comparison/review-command.md)
- [/simplify 深度分析](../comparison/simplify-command.md)
- [官方文档](https://code.claude.com/docs)
