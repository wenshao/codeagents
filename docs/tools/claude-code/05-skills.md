# 5. Skill 与插件系统——开发者参考

> Skill 是 Claude Code 的命令扩展机制——`/commit`、`/review`、`/loop`、`/batch` 都是 Skill。本文分析 14 个内置 Skill 的完整实现、加载机制和插件打包，为 Code Agent 开发者设计可扩展命令系统提供参考。
>
> **Qwen Code 对标**：Qwen Code 有 3 个 bundled skill（loop/review/qc-helper），Claude Code 有 14 个。本文的 Skill 设计模式（Feature Flag 门控、动态 prompt 生成、多 Agent 并行）可直接参考。

## 为什么需要 Skill 系统

### 问题定义

Code Agent 的功能需求在持续增长——`/commit`、`/review`、`/batch`、`/loop`——但不是所有功能都需要编译进核心代码：

| 需求类型 | 内置命令 | Skill |
|---------|---------|-------|
| 清屏、切换模型 | ✓（永远需要） | — |
| 代码审查、提交 | — | ✓（可迭代 prompt 优化） |
| 项目特定工作流 | — | ✓（用户自定义） |
| 实验性功能 | — | ✓（Feature Flag 门控） |

**核心优势**：Skill 是纯 Markdown——修改 SKILL.md 即可调整行为，**不需要重新编译或发布新版本**。这是 Qwen Code `/review` 能快速迭代的原因（见 [review 改进建议](../../comparison/qwen-code-review-improvements.md)）。

### 竞品 Skill/扩展系统对比

| Agent | 扩展机制 | 格式 | 内置数量 | 用户自定义 |
|-------|---------|------|---------|-----------|
| **Claude Code** | Skill（SKILL.md）+ Plugin（plugin.json） | Markdown + YAML Frontmatter | 14 Skill + 13 Plugin | ✓ 用户/项目级 |
| **Gemini CLI** | Skill（SKILL.md）+ TOML Command | Markdown / TOML | 1 Skill (skill-creator) | ✓ .gemini/skills/ |
| **Qwen Code** | Skill（SKILL.md） | Markdown + YAML Frontmatter | 3 Skill (loop/review/qc-helper) | ✓ 用户/项目级 |
| **Copilot CLI** | Plugin（plugin.json 打包 agents/skills/hooks/MCP） | JSON + Markdown | 13+ Plugin | ✓ marketplace |
| **Cursor** | 无独立扩展机制 | — | — | .cursorrules |

**关键差异**：Claude Code 的 Skill 数量（14 个）远超竞品，且覆盖了从"大规模并行变更"（/batch，5-30 Agent）到"会话流程捕获"（/skillify，4 轮访谈）的广泛场景。Qwen Code 的 3 个 Skill 覆盖面有限。

## 一、Skill 定义格式（SKILL.md）

每个 Skill 是一个 Markdown 文件，通过 YAML Frontmatter 声明元数据：

```markdown
---
name: 技能显示名
description: 技能描述（用于模型判断何时调用）
user-invocable: true          # 是否在 / 菜单中显示
disable-model-invocation: false # 是否禁止模型主动调用
allowed-tools: ["Bash", "Edit", "Read"]  # 允许使用的工具
argument-hint: "<参数说明>"    # 参数提示
when_to_use: "当用户要求..."   # 触发条件描述
model: sonnet                  # 使用的模型（可选）
effort: high                   # 推理努力级别
context: fork                  # 执行上下文（fork = 独立上下文）
---

你的技能提示内容...可以使用 ${CLAUDE_SKILL_DIR} 引用技能目录
```

## 二、Skill 加载路径（优先级从高到低）

| 来源 | 路径 | 说明 |
|------|------|------|
| 管理员策略 | `~/.claude/settings.json` 中的 policySettings | 企业管控，不可覆盖 |
| 用户级 | `~/.claude/skills/` | 个人全局技能 |
| 项目级 | `<project>/.claude/skills/` | 项目共享技能（可提交到 Git） |
| 附加目录 | `--add-dir` 指定目录的 `.claude/skills/` | 运行时附加 |
| 旧版 commands | `.claude/commands/` 目录（DEPRECATED） | 向后兼容 |

## 三、Skill 加载流程

```
启动 → 扫描所有 Skill 目录
     → 读取每个 SKILL.md 的 Frontmatter
     → 解析 YAML 元数据
     → 去重（SHA 哈希判断同一文件不同路径只保留一个）
     → Feature Flag 门控检查
     → 条件 Skill 暂存（等待匹配文件被访问时激活）
     → 无条件 Skill 注册到全局命令表
```

**条件激活**：Frontmatter 中可设置 `paths` 字段（glob 模式），只有当用户操作匹配的文件时才激活。

## 四、14 个内置 Skill 详解

### 4.1 /batch — 大规模并行变更（开发者重点关注）

**门控**：无（始终可用）| **用户可调用**：是 | **禁止模型调用**：是

**设计理念**：将大规模机械性变更（迁移、重构、批量重命名）分解为 5-30 个独立并行单元，每个在独立 worktree 中执行并开 PR。

**三阶段编排**：

| 阶段 | 动作 | 关键实现 |
|------|------|---------|
| 1. Research/Plan | 理解范围，分解为独立单元 | 使用 `EnterPlanMode` 工具，MIN=5 MAX=30 个 Agent |
| 2. Spawn Workers | 全部并行启动 | `Agent` 工具 + `isolation: "worktree"` + `run_in_background: true` |
| 3. Track Progress | 渲染状态表 + PR 链接 | 后台 Agent 完成时更新 |

**Worker 模板**：simplify → 单测 → e2e → commit → push → PR，以 `PR: <url>` 结束。

**开发者启示**：这是 Claude Code 中最复杂的 Skill——展示了如何用 SKILL.md prompt 编排多个隔离 Agent 并行工作。Qwen Code 可以用类似模式实现 `/batch` 命令。

### 4.2 /simplify — 代码精简审查

**门控**：无 | **用户可调用**：是

**三 Agent 并行审查**：

| Agent | 审查维度 | 检查内容 |
|-------|---------|---------|
| Agent 1 | 代码复用 | 搜索已有工具函数、标记重复、建议替换 |
| Agent 2 | 代码质量 | 冗余状态、参数膨胀、复制粘贴、stringly-typed 代码 |
| Agent 3 | 效率 | 不必要计算、并发机会、热路径膨胀、TOCTOU、内存问题 |

审查后直接修复（跳过误报）。与 `/review` 的区别：`/simplify` 侧重已改代码的简化，`/review` 侧重发现问题。

### 4.3 /loop — 定时循环执行

**门控**：`AGENT_TRIGGERS` Feature Flag | **运行时检查**：`isKairosCronEnabled()`

**用法**：`/loop 5m /review`（每 5 分钟执行 `/review`）

**解析优先级**：
1. 前置间隔 token：`\d+[smhd]$`（如 `5m`、`2h`）
2. 后置 "every" 子句（如 `every 20m`）
3. 默认 10 分钟

**实现**：解析间隔 → 转换为 cron 表达式 → 调用 `CronCreate` 工具 → 立即执行一次。

### 4.4 /schedule — 远程定时 Agent

**门控**：`AGENT_TRIGGERS_REMOTE` + `tengu_surreal_dali` + `allow_remote_sessions` 策略

**与 /loop 的区别**：`/loop` 在本地 CLI 会话内循环（会话关闭则停止），`/schedule` 创建**远程** cron 任务（跨会话存活）。

**实现要点**：
- 需要 claude.ai OAuth 认证（非 API key）
- Base58 解码 MCP server ID（`mcpsrv_` 格式→UUID）
- 自动检测 repo 访问权限（GitHub App / web-setup）
- 用户本地时区自动转换为 UTC cron

### 4.5 /claude-api — API 开发辅助

**门控**：`BUILDING_CLAUDE_APPS` | **工具**：`Read`、`Grep`、`Glob`、`WebFetch`

**核心设计**：
- **语言自动检测**：扫描项目文件，识别 Python/TypeScript/Java/Go/Ruby/C#/PHP/curl
- **懒加载文档**：247KB 的 Markdown 文档仅在调用时加载（不占启动 token）
- **语言过滤**：只注入检测到的语言的 API 文档
- **模板变量**：`{{OPUS_ID}}`、`{{SONNET_ID}}` 等动态替换为当前模型 ID

**开发者启示**：展示了 Skill 如何通过懒加载大量文档 + 语言自动检测来优化 token 使用。Qwen Code 可以用类似模式为 DashScope/OpenAI API 开发提供辅助。

### 4.6 /skillify — 会话流程捕获为 Skill

**门控**：无（内部用户专属） | **禁止模型调用**：是

**四轮访谈流程**：

| 轮次 | 内容 |
|------|------|
| 1 | 确认 skill 名称、描述、目标、成功标准 |
| 2 | 高层步骤、参数、inline vs fork 上下文、保存位置 |
| 3 | 每步细分——执行类型（直接/Task Agent/Teammate/人工）、产出物、检查点 |
| 4 | 确认触发短语和注意事项 |

**模板变量**：`{{sessionMemory}}`、`{{userMessages}}`、`{{userDescriptionBlock}}` 从当前会话提取。

最终生成完整 SKILL.md 并保存。

### 4.7 /remember — 记忆层级审查与提升

**门控**：`isAutoMemoryEnabled()` | **内部用户专属**

**工作流**：
1. 收集所有记忆层（CLAUDE.md / CLAUDE.local.md / auto-memory / team memory）
2. 分类每条 auto-memory 条目→目标层：
   - CLAUDE.md：项目约定（所有贡献者可见）
   - CLAUDE.local.md：个人偏好
   - Team memory：组织级知识
   - 保留 auto-memory：临时笔记
3. 识别清理项（重复/过时/冲突）
4. 输出结构化提案（不自动执行，需用户确认）

### 4.8 /update-config — 设置配置

**门控**：无 | **工具**：`Read`

**动态 prompt 生成**：从 Zod SettingsSchema 动态生成 JSON Schema，保证文档与代码同步。

**Hook 验证流程**（7 步）：去重检查 → 构建 → pipe-test → 写入 → 验证 → 证明 → 交接。

### 4.9 /keybindings-help — 键位自定义

**门控**：`isKeybindingCustomizationEnabled()` | **用户可调用**：否（自动触发）

**动态表格**：Available Contexts 和 Available Actions 表格从 `KEYBINDING_CONTEXTS` 和 `KEYBINDING_ACTIONS` 源码常量动态生成——确保文档永远与代码一致。

### 4.10 /debug — 会话诊断

**门控**：无 | **工具**：`Read`、`Grep`、`Glob`

**实现**：自动启用 debug 日志 → 读取最后 64KB（避免内存峰值）→ 显示最后 20 行 → 可选启动 `CLAUDE_CODE_GUIDE_AGENT_TYPE` Subagent 辅助理解。

### 4.11 /stuck — 卡死诊断（内部专属）

诊断 Claude Code 卡死/高 CPU/僵尸进程，自动发送诊断报告到 #claude-code-feedback Slack。

### 4.12 /verify — 运行验证（内部专属）

运行应用验证代码变更是否符合预期。

### 4.13 /claude-in-chrome — 浏览器自动化

**门控**：`shouldAutoEnableClaudeInChrome()` | **工具**：所有 `mcp__claude-in-chrome__*`

自动调用 Chrome 扩展的 MCP 工具（tabs_context、click、fill、screenshot 等）。

### 4.14 /lorem-ipsum — 长上下文测试（内部专属）

生成指定 token 数的填充文本。使用预验证的 200+ 个单 token 英文词列表，上限 500K token。

## 五、关键设计模式总结

| 模式 | 使用的 Skill | 开发者启示 |
|------|------------|-----------|
| **多 Agent 并行** | batch（5-30 Agent）、simplify（3 Agent） | 用 prompt 编排并行，无需代码改动 |
| **Feature Flag 门控** | loop、schedule、claude-api | 实验性功能可安全灰度发布 |
| **懒加载大文档** | claude-api（247KB） | 避免启动时占用 token |
| **动态 prompt 生成** | update-config（Schema→文档）、keybindings（常量→表格） | 保证文档与代码同步 |
| **4 轮访谈** | skillify | 复杂 Skill 创建的交互式引导 |
| **Worktree 隔离** | batch | 并行 Agent 互不干扰 |
| **条件激活** | keybindings、remember、loop | 按需加载减少菜单噪音 |
| **模板变量** | skillify（`{{sessionMemory}}`）、claude-api（`{{OPUS_ID}}`） | 运行时注入上下文 |
| **禁止模型调用** | batch、skillify、debug | 仅用户手动触发，防止 LLM 自行调用 |

## 六、插件系统

Claude Code 通过 `/plugin` 命令管理插件，支持从 marketplace 安装。

### 插件结构
```
.claude-plugin/
  plugin.json            # 插件元数据和配置
  commands/              # 自定义斜杠命令
  agents/                # 代理模板
  skills/                # 技能定义
  hooks/                 # Hook 脚本
  .mcp.json              # 插件 MCP 服务器配置
```

### 官方插件一览

| 插件 | 核心功能 | 实现模式 |
|------|---------|---------|
| **code-review** | 多 Agent 并行 PR 审查 + 置信度过滤 | 9 步流水线，4 并行 Agent |
| **pr-review-toolkit** | 6 个专项审查 Agent | 注释/测试/错误处理/类型/质量/简化 |
| **feature-dev** | 7 阶段引导式功能开发 | Discovery → 探索 → 提问 → 架构 → 实现 → 审查 → 反思 |
| **security-guidance** | 安全编码指导 | PreToolUse Hook 拦截不安全操作 |
| **hookify** | 对话分析自动创建 Hook | 检测挫败信号 → 生成规则文件 → 即时生效 |
| **commit-commands** | Git 提交/推送/创建 PR | 分析 diff + 历史风格 + 生成消息 |

### feature-dev 7 阶段流程

| 阶段 | 核心动作 |
|------|---------|
| 1. Discovery | 理解需求，确认问题和约束 |
| 2. Exploration | 2-3 并行 explorer Agent 各探索不同方面 |
| 3. Questions | **关键**——识别歧义、边界条件、集成点，向用户提问 |
| 4. Architecture | 2-3 并行 architect Agent：最小变更 vs 干净架构 vs 务实平衡 |
| 5. Implementation | 按选定方案实现 |
| 6. Review | 代码审查和测试 |
| 7. Reflection | 回顾和总结 |

## 补充：Monorepo 中的 Skill 发现机制

> 参考：[claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) 的 Monorepo Skills 发现报告

**Skill 与 CLAUDE.md 的加载行为不同**：CLAUDE.md 向上遍历目录树（祖先加载），Skill 使用嵌套目录按需发现。

### 发现层级

| 层级 | 路径 | 作用范围 |
|------|------|---------|
| Enterprise | 托管设置 | 组织所有用户 |
| Personal | `~/.claude/skills/<name>/SKILL.md` | 所有项目 |
| Project | `.claude/skills/<name>/SKILL.md` | 当前项目 |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | 插件启用时 |
| **嵌套目录** | `packages/frontend/.claude/skills/<name>/SKILL.md` | **编辑该目录文件时按需发现** |

### 按需发现

嵌套 Skill 不在会话启动时预加载——仅当用户编辑对应子目录的文件时才被发现。Skill 的 description 字段始终在上下文中（供 Claude 知道有哪些 Skill 可用），但完整内容仅在 Skill 被调用时加载。Subagent 预加载的 Skill（`benefits-from` 字段）是例外——在 Agent 启动时注入完整内容。

**Qwen Code 对标**：Qwen Code 的 Skill 发现机制来自 Gemini CLI fork，需要验证是否支持嵌套目录按需发现和 description/content 分离加载。
