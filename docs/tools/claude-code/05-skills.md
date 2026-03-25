# 5. Skill 与插件系统

## Skill 系统实现机制

> 以下基于 v2.1.81 二进制逆向分析和运行时观察。Skill 是 Claude Code 的命令扩展机制——用户看到的 `/commit`、`/review`、`/loop` 等都是 Skill。

### Skill 定义格式（SKILL.md）

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
model: sonnet                  # 使用的模型（可选，默认继承）
effort: high                   # 推理努力级别
context: fork                  # 执行上下文（fork = 独立上下文）
shell: bash                    # Shell 类型
---

你的技能提示内容...可以使用 ${CLAUDE_SKILL_DIR} 引用技能目录
```

### Skill 加载路径（优先级从高到低）

| 来源 | 路径 | 说明 |
|------|------|------|
| 管理员策略 | `~/.claude/settings.json` 中的 policySettings | 企业管控，不可覆盖 |
| 用户级 | `~/.claude/skills/` | 个人全局技能 |
| 项目级 | `<project>/.claude/skills/` | 项目共享技能（可提交到 Git） |
| 附加目录 | `--add-dir` 指定目录的 `.claude/skills/` | 运行时附加 |
| 旧版 commands | `.claude/commands/` 目录（DEPRECATED） | 向后兼容 |

### Skill 类型

| 类型 | 注册方式 | 执行方式 |
|------|----------|----------|
| **prompt** | SKILL.md 文件 | 将 Markdown 内容作为提示发送给 LLM |
| **local-jsx** | 代码内注册 | 渲染本地 React/Ink UI 组件 |
| **local** | 代码内注册 | 直接本地执行（不调用 LLM） |

### Skill 加载流程（源码分析）

```
启动 → pdA() 扫描所有 Skill 目录
     → 读取每个 SKILL.md 的 Frontmatter
     → hw() 解析 YAML 元数据
     → 去重（同一文件不同路径只保留一个）
     → 条件 Skill 暂存到 TTH Map（等待匹配文件被访问时激活）
     → 无条件 Skill 注册到 Vn Map（全局命令注册表）
```

**条件激活（Conditional Skills）**：
- Skill 的 Frontmatter 中可设置 `paths` 字段（glob 模式数组）
- 只有当用户操作匹配的文件时，该 Skill 才被激活
- 使用 `ignore` 库匹配（类似 .gitignore 规则）
- 一旦激活，发射 `tengu_dynamic_skills_changed` 事件通知 UI 更新

**去重机制**：
- 使用文件内容哈希（crypto SHA）判断是否为同一 Skill
- 多个路径发现同一文件时，保留先发现的，记录来源

### 内置 Skill 详情

| Skill | 实现 | 工作流 |
|-------|------|--------|
| `/commit` | prompt 类型 | 分析 `git diff --staged`，生成提交消息，执行 `git commit` |
| `/review` | prompt 类型 | 获取 diff 或 PR 信息，分析代码变更，生成审查意见 |
| `/commit-push-pr` | prompt 类型 | commit + push + 创建 PR 一键完成 |
| `/init` | prompt 类型 | 分析项目结构，生成/更新 CLAUDE.md |
| `/init-verifiers` | prompt 类型 | 创建 verifier Skill 用于自动化验证代码变更 |
| `/loop` | prompt 类型 | 按间隔重复执行命令（默认 10 分钟），如 `/loop 5m /review` |
| `/schedule` | prompt 类型 | 管理 cron 定时远程代理任务（创建/更新/列出/执行） |
| `/simplify` | prompt 类型 | 审查已修改代码的复用性、质量和效率 |
| `/update-config` | prompt 类型 | 通过对话式界面修改 settings.json |
| `/claude-api` | prompt 类型 | 导入 anthropic SDK 时自动触发，辅助 API 开发 |

**自定义 Skill 示例**（`.claude/skills/my-skill/SKILL.md`）：
```markdown
---
name: 我的自定义技能
description: 执行自定义操作
user-invocable: true
allowed-tools: ["Bash", "Edit"]
---

你的技能提示内容...
```

## 插件系统

Claude Code 通过 `/plugin` 命令管理插件，支持从 marketplace 安装：

### 插件管理
```bash
/plugin                  # 查看插件管理界面
/plugin install <name>   # 安装插件
/plugin list             # 列出已安装插件
```

### 官方插件示例

| 插件 | 用途 |
|------|------|
| **security-review** | 安全漏洞审查，对应 `/security-review` 命令 |
| **pr-comments** | PR 评论处理，对应 `/pr-comments` 命令 |

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
