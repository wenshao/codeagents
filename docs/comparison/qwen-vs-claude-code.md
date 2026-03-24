# Qwen Code vs Claude Code：深度对比

> Qwen Code（开源，Gemini CLI 分叉）vs Claude Code（闭源，Rust 原生）——两个头部 AI 编程代理的全面对比

## 定位对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **开发者** | Anthropic | 阿里云 |
| **定位** | Anthropic 官方终端代理 | 阿里云开源终端代理 |
| **语言** | Rust（闭源） | TypeScript（开源，Gemini CLI 分叉） |
| **许可证** | 专有 | Apache-2.0 |
| **模型** | Claude 系列（锁定） | Qwen + OpenAI + Anthropic + Gemini（5 提供商） |
| **上下文** | 100 万 token（Opus 4.6） | 100 万 token（Qwen3 商用版） |
| **免费层** | Claude Pro/Max 订阅内含 | 每天 1000 次免费（OAuth） |
| **插件仓库** | 13 个官方插件 | 扩展系统 + Claude/Gemini 格式转换 |

---

## 1. 代理循环

### Claude Code

```
用户输入
  → 系统提示 + CLAUDE.md 项目指令
  → Claude LLM（流式）
  → 工具调用解析
  → PreToolUse Hook（验证/修改）
  → 权限检查（allow/ask/deny）
  → 工具执行（可能沙箱）
  → PostToolUse Hook（反馈）
  → 结果回传 LLM
  → 重复直到完成
  → Stop Hook（验证完成合理性）
```

- **REPL 模式**：交互式会话，流式响应
- **子代理**：通过 `Task` 工具生成自主代理
- **计划模式**：用户请求后逐步规划再执行
- **自动记忆**：跨会话学习用户偏好

### Qwen Code

```
用户输入
  → 系统提示 + system.md 项目指令
  → ContentGenerator（多提供商）
  → CoreToolScheduler 调度
  → Hook 触发（PreToolUse）
  → PermissionManager 检查
  → 工具执行（可能沙箱）
  → Hook 触发（PostToolUse）
  → 结果回传 LLM
  → Loop 检测（Levenshtein）
  → 重复，最多 100 轮
```

- **MAX_TURNS = 100**：硬性轮次上限
- **Arena 模式**：多代理竞争/协作
- **Token 限制**：Session 级 Token 预算
- **会话录制**：JSONL 持久化

### 关键差异

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 轮次上限 | 无明确上限 | 100 轮 |
| 循环检测 | Stop Hook 验证 | Levenshtein 距离检测 |
| 子代理 | Task 工具 + Agent 定义 | 子代理管理器 + Arena |
| 计划模式 | 用户触发 | Plan 模式 + 审批工作流 |
| 项目指令 | CLAUDE.md | system.md |
| 会话恢复 | `--resume` 标志 | `getResumedSessionData()` |

---

## 2. 工具系统

### Claude Code 内置工具

| 工具 | 说明 | 权限默认 |
|------|------|---------|
| **Read** | 读取文件 | allow |
| **Write** | 创建/写入文件 | ask |
| **Edit** | 修改文件（差异预览） | ask |
| **Bash** | 执行 Shell 命令 | ask |
| **Glob** | 文件模式匹配 | allow |
| **Grep** | 正则内容搜索 | allow |
| **WebFetch** | 抓取 URL 内容 | ask |
| **WebSearch** | 网络搜索 | ask |
| **AskUserQuestion** | 向用户提问 | allow |
| **Task** | 生成子代理 | allow |
| **Skill** | 加载技能 | allow |
| **TodoWrite** | 任务管理 | allow |
| **NotebookEdit** | Jupyter Notebook | ask |
| **MCP 工具** | 外部 MCP 服务器 | 可配置 |

### Qwen Code 内置工具

| 工具 | 说明 | 权限默认 |
|------|------|---------|
| **edit** | 多部分文件编辑（diff） | ask |
| **write_file** | 创建/覆盖文件 | ask |
| **read_file** | 读取文件 | allow |
| **run_shell_command** | Shell 执行 | ask |
| **grep_search** | 全文搜索（ripgrep） | allow |
| **glob** | 文件模式匹配 | allow |
| **list_directory** | 目录列表 | allow |
| **web_fetch** | HTTP GET 请求 | ask |
| **web_search** | 网络搜索（Tavily/Google/DashScope） | ask |
| **agent** | 子代理生成 | allow |
| **skill** | 技能调用 | allow |
| **todo_write** | 任务管理 | allow |
| **save_memory** | 持久化记忆到 MD | allow |
| **exit_plan_mode** | 退出规划模式 | allow |
| **ask_user_question** | 用户交互 | allow |
| **lsp** | 语言服务器操作 | allow |
| **MCP 工具** | 外部 MCP 服务器 | 可配置 |

### 工具实现对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **编辑工具** | Edit（old_string/new_string） | edit（多部分 diff + 编码检测 + BOM） |
| **Shell** | Bash（4 模式：normal/sandbox/pipeline/interactive） | run_shell_command（AST 分析 + Tmux/iTerm2） |
| **搜索** | Grep（ripgrep 语法） | grep_search（ripgrep + gitignore） |
| **Web 搜索后端** | 内置 | Tavily/Google/DashScope（多后端） |
| **独有工具** | NotebookEdit | save_memory, exit_plan_mode, lsp |
| **工具定义** | Rust 内置（闭源） | DeclarativeTool 抽象类（TypeScript） |
| **输出流式** | 内置支持 | `updateOutput` 回调 |
| **工具发现** | 仅内置 + MCP | 命令行发现 + MCP + 扩展 |

### Edit 工具深度对比

**Claude Code Edit**：
- `old_string` / `new_string` 搜索替换
- `replace_all` 可选全局替换
- 差异预览，用户可修改后确认

**Qwen Code edit**：
- 同样的 `old_string` / `new_string` 模式
- 编码自动检测 + BOM 处理
- `safeLiteralReplace()` 安全处理 `$` 序列
- CRLF → LF 标准化
- 出现次数验证（确保唯一性）
- `modifyWithEditor()` 允许中间编辑

### Shell 工具深度对比

**Claude Code Bash**：
- 4 种执行模式：normal、sandbox、pipeline、interactive
- 沙箱模式：文件系统限制 + 网络隔离 + 进程隔离
- 受保护目录：`.git`、`.claude` 等

**Qwen Code run_shell_command**：
- AST 语义分析（`isShellCommandReadOnlyAST()`）
- 命令替换检测（`$()`、反引号）→ 自动拒绝
- 只读命令检测 → 自动允许
- 后台执行支持（`is_background`）
- Git commit 自动添加 co-author

---

## 3. 权限系统

### Claude Code：多层级精细权限

```
优先级（高→低）：
1. CLI 标志（--settings）
2. 项目本地（.claude/settings.local.json）
3. 项目级（.claude/settings.json）
4. 用户级（~/.claude/settings.json）
5. 组织级
6. 企业级（managed-settings.json）
7. 默认值

每个工具：allow | ask | deny
沙箱：文件系统 + 网络 + 进程隔离
绕过：--dangerously-skip-permissions（可被企业禁用）
```

### Qwen Code：配置驱动权限

```
优先级：deny(3) > ask(2) > default(1) > allow(0)

规则类型：
- persistentRules（设置文件持久化）
- sessionRules（会话级临时）

Shell 分析：
- 虚拟操作提取（文件/网络）
- 复合命令拆分
- 相对路径解析
```

### 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **层级数** | 7 层（企业→默认） | 2 层（持久 + 会话） |
| **沙箱** | ✓（文件/网络/进程） | ✓（Docker/Podman） |
| **企业管控** | ✓（managed-settings） | ✗ |
| **权限绕过** | ✓（可禁用） | ✓（yolo_mode） |
| **Shell 分析** | 沙箱隔离 | AST 语义分析 |
| **MCP 工具权限** | `mcp__plugin__tool` 格式 | 与内置工具同等 |
| **受保护路径** | .git, .claude | .env* 文件需确认 |

---

## 4. Hook 系统

### Claude Code Hook 事件

| 事件 | 触发时机 | 输入 | 输出 |
|------|---------|------|------|
| **PreToolUse** | 工具执行前 | tool_name, tool_input | allow/deny/ask |
| **PostToolUse** | 执行成功后 | tool_name, tool_result | 附加上下文 |
| **UserPromptSubmit** | 用户提交输入 | user_prompt | 修改/阻止 |
| **Stop** | 代理尝试停止 | transcript | 允许/阻止停止 |
| **SubagentStop** | 子代理停止 | transcript | 允许/阻止 |
| **SessionStart** | 会话开始 | session_id | 上下文注入 |
| **SessionEnd** | 会话结束 | session_id | 清理 |
| **PreCompact** | 上下文压缩前 | messages | 保护关键信息 |
| **Notification** | 通知发送 | content | 修改/阻止 |
| **StopFailure** | API 错误终止 | error | 处理策略 |

### Qwen Code Hook 事件

| 事件 | 触发时机 |
|------|---------|
| **PreToolUse** | 工具执行前 |
| **PostToolUse** | 执行成功后 |
| **PostToolUseFailure** | 执行失败后 |
| **UserPromptSubmit** | 用户提交输入 |
| **SessionStart** | 会话开始 |
| **SessionEnd** | 会话结束 |
| **SubagentStart** | 子代理启动 |
| **SubagentStop** | 子代理停止 |
| **PreCompact** | 上下文压缩前 |
| **Stop** | 代理停止 |
| **Notification** | 通知发送 |
| **PermissionRequest** | 权限请求 |

### Hook 实现对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **事件数** | 10 | 12 |
| **独有事件** | StopFailure | PostToolUseFailure, SubagentStart, PermissionRequest |
| **Hook 类型** | Prompt（LLM 驱动）+ Command（脚本） | Command（脚本） |
| **执行方式** | 子进程 JSON stdin/stdout | 子进程 JSON stdin/stdout |
| **超时** | 可配置 | 可配置 |
| **企业管控** | ✓（allowManagedHooksOnly） | ✗ |
| **Prompt Hook** | ✓（LLM 推理决策） | ✗ |

**Claude Code 独有的 Prompt Hook**：
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [
        {"type": "prompt", "prompt": "检查这次编辑是否引入安全漏洞..."}
      ]
    }]
  }
}
```
Prompt Hook 用 LLM 推理来决策，比纯脚本更灵活但更慢。Qwen Code 没有这个概念。

---

## 5. 插件/扩展系统

### Claude Code：插件架构

```
plugin-name/
├── .claude-plugin/plugin.json   # 元数据
├── commands/                    # 斜杠命令（*.md）
├── agents/                      # 子代理定义（*.md）
├── skills/                      # 技能知识（*.md）
├── hooks/                       # 事件处理
└── .mcp.json                    # MCP 服务器
```

**13 个官方插件**：

| 插件 | 说明 |
|------|------|
| code-review | 4 个并行代理审查 PR，置信度评分 |
| feature-dev | 7 阶段特性开发流程 |
| commit-commands | `/commit`、`/commit-push-pr` 等 Git 工作流 |
| pr-review-toolkit | 6 个专用代理（注释/测试/错误/类型/质量/简化） |
| security-guidance | PreToolUse Hook 警告注入/XSS/eval |
| hookify | 对话式创建 Hook 规则 |
| agent-sdk-dev | Agent SDK 开发脚手架 |
| ralph-wiggum | 自引用迭代循环（写→测→调试） |
| plugin-dev | 插件开发工具包（7 个技能） |
| explanatory-output-style | 教育性实现解释 |
| learning-output-style | 交互式学习模式 |
| frontend-design | 高质量 UI/UX 实现 |
| claude-opus-4-5-migration | Opus 4.5 迁移 |

### Qwen Code：扩展系统

```
扩展支持三种格式：
├── Qwen Code 原生扩展（Git clone/Release）
├── Claude 插件转换（claude-converter.ts）
└── Gemini 扩展转换（gemini-converter.ts）
```

**扩展组件**：MCP 服务器、Skills、Subagents、Hooks

### 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **插件数量** | 13 个官方 | 社区为主 |
| **插件格式** | Markdown + JSON | Markdown + JSON |
| **跨工具兼容** | 仅 Claude Code | ✓ 转换 Claude/Gemini 格式 |
| **安装方式** | 插件市场 / 手动 | Git clone / Release |
| **企业管控** | ✓（strictKnownMarketplaces） | ✗ |

---

## 6. 技能系统

### Claude Code Skills

```markdown
<!-- skills/my-skill/SKILL.md -->
---
name: my-skill
description: 触发条件描述
allowed-tools: [Read, Edit, Bash]
---

技能内容，Markdown 格式...
```

- 自动加载：基于触发条件自然语言匹配
- 通过 `Skill` 工具调用
- 支持在插件中分发

### Qwen Code Skills

```yaml
# skills/my-skill/SKILL.md
---
name: my-skill
description: 技能描述
tools: [bash, grep, read_file]
extends: bundled  # 可选：扩展内置技能
---

技能内容，Markdown 格式...
```

- 4 个级别：project / user / extension / bundled
- 支持 `extends: bundled` 扩展内置技能
- 动态 XML 列表注入到工具描述中

### 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **触发方式** | 自然语言条件 | 显式调用 |
| **级别** | 插件内 | project/user/extension/bundled |
| **技能组合** | 通过插件 | `extends: bundled` |
| **分发** | 插件市场 | Git / 扩展 |

---

## 7. MCP 支持

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **传输方式** | stdio, SSE, HTTP, WebSocket | stdio, SSE |
| **OAuth** | ✓（SSE 服务器） | ✓ |
| **配置方式** | `.mcp.json` 或 `plugin.json` | `settings.json` |
| **工具命名** | `mcp__plugin_name_server__tool` | 与内置工具平级 |
| **环境变量** | `${CLAUDE_PLUGIN_ROOT}` 等 | `${HOME}` 等 |
| **服务器管理** | 插件级别 | 全局配置 |

---

## 8. 子代理/多代理

### Claude Code

```markdown
<!-- agents/code-explorer.md -->
---
name: code-explorer
description: 探索代码库结构
  <example>用户要求理解项目架构时触发</example>
model: sonnet
tools: [Read, Grep, Glob]
---

你是代码探索专家...
```

- **自然语言触发**：description 中的 `<example>` 标签教 Claude 何时触发
- **模型选择**：sonnet / opus / haiku / inherit
- **工具限制**：明确列出可用工具
- **颜色标识**：blue / yellow / green / red

### Qwen Code

```typescript
interface SubagentConfig {
  name: string;
  description: string;
  tools?: string[];
  systemPrompt: string;
  level: 'session' | 'project' | 'user' | 'extension' | 'builtin';
  modelConfig?: Partial<ModelConfig>;
  color?: string;
}
```

- **5 个级别**：session / project / user / extension / builtin
- **Arena 模式**：Team / Swarm / Arena 三种协作模式
- **多终端后端**：Tmux / iTerm2 / 进程内
- **独立模型**：每个子代理可配置不同模型

### 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **触发方式** | 自然语言 + 手动 | 手动 / agent 工具 |
| **代理定义** | Markdown | TypeScript / TOML |
| **Arena** | ✗ | ✓（Team/Swarm/Arena） |
| **可视化并行** | ✗ | ✓（Tmux/iTerm2 分屏） |
| **模型选择** | sonnet/opus/haiku/inherit | 任意配置的模型 |
| **官方代理** | 13 插件中的多个代理 | 内置 builtin |

---

## 9. 配置系统

### Claude Code

```
~/.claude/
├── settings.json          # 用户全局设置
├── CLAUDE.md              # 用户级指令
└── 插件数据

.claude/
├── settings.json          # 项目设置
├── settings.local.json    # 本地设置（不提交）
├── CLAUDE.md              # 项目指令
├── commands/              # 自定义命令
└── 插件数据

7 层优先级：企业 → 组织 → 用户 → 项目 → 本地 → CLI 标志
```

### Qwen Code

```
~/.qwen/
├── settings.json          # 全局设置
├── locales/               # 6 种语言包
├── skills/                # 用户技能
├── agents/                # 用户代理
└── tmp/<hash>/chats/      # 会话存储

.qwen/
├── settings.json          # 项目设置
├── system.md              # 项目指令
├── skills/                # 项目技能
└── agents/                # 项目代理

4 层优先级：默认 → 全局 → 项目 → 环境变量 → CLI
```

---

## 10. 独有特性

### 仅 Claude Code 有

| 特性 | 说明 |
|------|------|
| **Prompt Hook** | LLM 推理驱动的 Hook 决策 |
| **7 层设置优先级** | 企业→组织→用户→项目→本地→CLI |
| **Bash 沙箱** | 文件系统+网络+进程隔离（4 种模式） |
| **13 个官方插件** | code-review、feature-dev、security 等 |
| **自然语言代理触发** | `<example>` 标签教 LLM 何时触发 |
| **ralph-wiggum 迭代** | Stop Hook 阻止退出，自动重复 |
| **hookify 对话式规则** | 聊天创建 Hook 规则 |
| **企业管控** | managed-settings、strictKnownMarketplaces |
| **Git Worktree** | 隔离分支并行工作 |
| **自动记忆** | 跨会话学习用户偏好 |
| **NotebookEdit** | Jupyter Notebook 编辑 |
| **StopFailure 事件** | API 错误特殊处理 |

### 仅 Qwen Code 有

| 特性 | 说明 |
|------|------|
| **免费 OAuth** | 通义账号每天 1000 次 |
| **5 提供商** | Qwen + OpenAI + Anthropic + Gemini + Vertex |
| **Arena 模式** | 多代理竞争/协作（Team/Swarm/Arena） |
| **Tmux/iTerm2 分屏** | 可视化并行代理 |
| **6 语言 UI** | 中/英/日/德/俄/葡 |
| **扩展格式转换** | Claude/Gemini 扩展自动转换 |
| **Loop 检测** | Levenshtein 距离检测重复调用 |
| **save_memory** | 持久化记忆到 Markdown |
| **LSP 工具** | 语言服务器协议操作 |
| **Session Token 限制** | 硬性 Token 预算 |
| **Shell AST 分析** | 命令语义级安全检查 |
| **PostToolUseFailure** | 工具失败专用 Hook |
| **PermissionRequest 事件** | 权限对话框 Hook |

---

## 11. 适用场景

| 场景 | 推荐 | 原因 |
|------|------|------|
| **复杂推理** | Claude Code | Claude 模型推理能力最强 |
| **企业部署** | Claude Code | 7 层设置 + 企业管控 + 沙箱 |
| **免费使用** | Qwen Code | OAuth 1000 次/天 |
| **多模型切换** | Qwen Code | 5 提供商灵活切换 |
| **中文开发** | Qwen Code | 6 语言 UI + Qwen 模型中文能力 |
| **代码审查** | Claude Code | code-review 插件（4 并行代理） |
| **多代理协作** | Qwen Code | Arena + Tmux 可视化 |
| **安全敏感** | Claude Code | 沙箱 + Prompt Hook + 企业管控 |
| **开源定制** | Qwen Code | 完整源码 + Apache-2.0 |
| **插件生态** | Claude Code | 13 官方插件 + 市场 |

---

## 12. 总结

**Claude Code** 是闭源但功能最完善的商业代理——Rust 原生性能、Prompt Hook 的 LLM 驱动决策、7 层企业管控、13 个官方插件构成了最成熟的生态。但模型锁定和付费门槛是限制。

**Qwen Code** 是功能最丰富的开源代理——5 提供商灵活接入、Arena 多代理框架、6 语言国际化、免费 OAuth 额度构成了最有吸引力的开源方案。但作为 Gemini CLI 分叉，部分代码仍带上游痕迹。

两者在工具系统、Hook 架构、技能系统上有**高度相似性**（均为声明式工具 + 事件 Hook + Markdown 技能），说明业界正在收敛到一套共同的代理架构模式。

---

*分析基于 Claude Code 插件仓库（v2.1.81）和 Qwen Code 本地源码，截至 2026 年 3 月。*
