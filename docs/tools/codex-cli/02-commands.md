# 2. Codex CLI 命令系统——开发者参考

> Codex CLI 拥有 15 个 CLI 子命令、28 个 TUI 斜杠命令、9 个代理工具、52 个 Feature Flag——在命令数量上不及 Claude Code（79 命令）和 Qwen Code（~40 命令），但在安全控制（5 种审批模式 + 4 级沙箱）和 IDE 集成（90+ JSON-RPC 方法）上具备独特优势。
>
> **Qwen Code 对标**：review 子命令（独立 CLI 入口 vs 仅斜杠命令）、MCP 双向支持（客户端+服务器 vs 仅客户端）、Feature Flag 管理（52 个 vs 无）、会话 resume/fork（vs 无持久化）

## 为什么命令架构设计值得研究

Code Agent 的命令系统面临一个共性问题：如何在"CLI 子命令"和"TUI 斜杠命令"之间划分职责？Codex CLI 的答案是：

- **CLI 子命令**（`codex review`、`codex cloud`、`codex mcp`）→ 可在 CI/CD 管道中脚本化调用，不依赖交互式 TUI
- **TUI 斜杠命令**（`/compact`、`/fork`、`/plan`）→ 仅在交互会话中可用，面向人类开发者

这种分离让 Codex 成为唯一可以在非交互模式下执行代码审查（`codex review --base main`）的主流 Agent。

### 竞品命令系统对比

| Agent | CLI 子命令 | TUI 斜杠命令 | 合计 | 独立审查入口 | 会话 resume |
|-------|-----------|-------------|------|-------------|------------|
| **Codex CLI** | 15 | 28 | 43 | `codex review` ✓ | `codex resume` ✓ |
| **Claude Code** | ~8 | ~79 | ~87 | `/review` 仅 TUI | 崩溃恢复 ✓ |
| **Qwen Code** | ~5 | ~40 | ~45 | 无 | 无 |
| **Gemini CLI** | ~5 | ~30 | ~35 | 无 | `gemini resume` ✓ |
| **Copilot CLI** | ~4 | ~20 | ~24 | 无 | 无 |

---

## CLI 子命令（15 个）

### 子命令总表

| 子命令 | 别名 | 说明 | Qwen Code 有无 |
|--------|------|------|---------------|
| `exec` | `e` | 执行任务（默认子命令） | 等价于 `qwen-code` 直接执行 |
| `review` | — | 代码审查（支持 `--uncommitted`/`--base`/`--commit`） | 无独立审查入口 |
| `login`/`logout` | — | 认证管理（OAuth 流程） | 有 |
| `mcp` | — | MCP 客户端管理（6 个子操作） | 有（仅客户端） |
| `mcp-server` | — | 以 MCP 服务器模式运行 | 无 |
| `app-server` | — | IDE 集成 JSON-RPC 服务器 | 无 |
| `cloud` | — | 云端任务（实验性，5 个子操作） | 无 |
| `resume` | — | 恢复之前的会话 | 无 |
| `fork` | — | 从已有会话分叉 | 无 |
| `apply` | `a` | 将 agent diff 应用到工作树 | 无 |
| `features` | — | 功能标志管理（list/enable/disable） | 无 |
| `sandbox` | — | 沙箱测试（macos/linux/windows） | 无 |
| `completion` | — | Shell 补全脚本生成 | 有 |
| `debug` | — | 调试信息输出 | 无 |

**Qwen Code 对标**：Codex 的 15 个子命令中有 8 个（`review`、`mcp-server`、`app-server`、`cloud`、`resume`、`fork`、`apply`、`features`）在 Qwen Code 中无对应。最具参考价值的是 `review`（CI 友好的独立审查入口）和 `resume`/`fork`（会话持久化）。

### review 子命令详解

`codex review` 是最值得 Qwen Code 借鉴的子命令——它将代码审查从交互式 TUI 解耦为独立 CLI 入口，可在 CI/CD 管道中脚本化调用。

```bash
codex review --uncommitted              # 审查 staged + unstaged + untracked 更改
codex review --base main                # 审查相对于 main 分支的更改
codex review --commit abc1234           # 审查特定 commit
codex review --title "Auth Module" --base main  # 带标题的审查
echo "check error handling" | codex review -    # 从 stdin 读取指令
```

| 参数 | 说明 |
|------|------|
| `[PROMPT]` | 自定义审查指令，`-` 表示从 stdin 读取 |
| `--uncommitted` | 审查 staged + unstaged + untracked 更改 |
| `--base <BRANCH>` | 审查相对于指定分支的更改 |
| `--commit <SHA>` | 审查指定 commit 引入的更改 |
| `--title <TITLE>` | 审查摘要中显示的可选标题 |

**开发者启示**：Claude Code 的 `/review` 是 prompt 类型命令（需要在 TUI 中执行），而 Codex 的 `review` 是独立子命令（可 `codex review --base main > report.md`）。对于 CI 集成场景，独立子命令更实用。

### cloud 子命令（实验性）

```bash
codex cloud exec "大规模重构任务"    # 在云端隔离环境执行，支持 best-of-N
codex cloud status <task-id>        # 查看任务状态
codex cloud list                    # 列出所有云端任务
codex cloud apply <task-id>         # 将云端结果 diff 应用到本地
codex cloud diff <task-id>          # 查看 unified diff
```

**架构**：每个 Cloud 任务在 OpenAI 云端创建隔离环境，执行 best-of-N 尝试（N=1-4），完成后可将 diff 拉回本地应用。这与 Claude Code 的 Kairos（Always-On 自治模式）思路类似但实现不同——Codex 是"提交-拉取"模型，Kairos 是"持续运行"模型。

### 完整参数参考

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--model` | `-m` | 指定使用的模型 | `gpt-5.1-codex` |
| `--ask-for-approval` | `-a` | 审批模式（5 种） | `untrusted` |
| `--sandbox` | `-s` | 沙箱模式（4 级） | — |
| `--full-auto` | — | `--ask-for-approval on-request --sandbox workspace-write` | — |
| `--config` | `-c` | 覆盖配置值（`key=value`，支持点路径） | — |
| `--profile` | `-p` | 使用 config.toml 中的配置 profile | — |
| `--oss` | — | 使用本地 OSS 模型提供者 | — |
| `--local-provider` | — | 指定本地模型提供者（`lmstudio`/`ollama`） | — |
| `--image` | `-i` | 附加图片到初始提示（可重复） | — |
| `--enable`/`--disable` | — | 启用/禁用功能标志 | — |
| `--search` | — | 启用网络搜索（web_search 工具） | — |
| `--cd` | `-C` | 指定工作根目录 | 当前目录 |
| `--add-dir` | — | 添加额外可写目录 | — |
| `--remote` | — | 连接远程 app-server WebSocket | — |
| `--no-alt-screen` | — | 禁用备用屏幕（内联 TUI） | — |
| `--dangerously-bypass-approvals-and-sandbox` | — | 绕过所有安全限制（极危险） | — |

> 验证方式：`codex --help` 确认。`--reasoning-effort` 不是独立 CLI 参数，需通过 `-c model_reasoning_effort=high` 设置。

---

## TUI 斜杠命令（28 个，官方文档验证）

> 来源：[官方斜杠命令文档](https://developers.openai.com/codex/cli/slash-commands)，28 个命令。Rust 编译的二进制中命令名以 enum 形式存储，以官方文档为权威来源。

### 命令分类与 Qwen Code 对标

| 类别 | 命令 | 功能 | Qwen Code 有无 |
|------|------|------|---------------|
| **会话** | `/compact` | 压缩对话历史，释放上下文 | 有（/compact） |
| | `/fork` | 从当前状态分叉新会话 | 无 |
| | `/resume` | 恢复之前的会话 | 无 |
| | `/new` | 开始新会话 | 有 |
| | `/status` | 显示模型、token 用量、审批模式 | 有（/status） |
| | `/statusline` | 切换底部状态栏 | 无 |
| | `/copy` | 复制最近回复到剪贴板 | 有 |
| | `/exit`, `/quit` | 退出会话 | 有 |
| | `/clear` | 清屏 | 有 |
| **模型** | `/model` | 切换或查看模型 | 有（/model） |
| | `/permissions` | 查看/修改权限 | 有 |
| | `/personality` | 查看/设置代理人格 | 无 |
| | `/fast` | 切换快速模式 | 无 |
| | `/debug-config` | 显示调试配置 | 无 |
| **工具** | `/agent` | 与内置代理交互 | 有 |
| | `/mcp` | 管理 MCP 服务器 | 有 |
| | `/apps` | 管理 ChatGPT Apps | 无（OpenAI 独有） |
| | `/experimental` | 查看/切换实验性功能 | 无 |
| **工作流** | `/plan` | 制定计划而不执行 | 有（/plan） |
| | `/review` | 交互式代码审查 | 无 |
| | `/feedback` | 向代理提供反馈 | 无 |
| | `/diff` | 显示文件修改差异 | 有（/diff） |
| | `/mention` | 引用文件/符号到上下文 | 有（@引用） |
| | `/ps` | 显示后台进程状态 | 无 |
| **系统** | `/logout` | 登出 | 有 |
| | `/init` | 初始化项目（生成 CODEX.md） | 有（/init） |
| | `/sandbox-add-read-dir` | 添加目录到沙箱只读列表 | 无 |

**开发者分析**：28 个斜杠命令中，Qwen Code 缺失的关键命令包括：`/fork`（会话分叉）、`/review`（代码审查）、`/personality`（代理人格）、`/feedback`（反馈调整）、`/ps`（后台进程）。其中 `/fork` 和 `/review` 的实现价值最高。

> **第四轮验证修正记录：** 移除 13 个未经官方文档或二进制双重验证的命令（/help, /history, /memories, /prompts, /realtime, /rename, /session, /settings, /share, /shell, /skills, /tasks, /tools）。

---

## 代理工具系统

### 系统身份

从二进制中提取的系统提示片段确认：

> **"You are Codex, a coding agent based on GPT-5."**

### 工具对比

| 工具名 | 功能 | Codex CLI | Claude Code 对应 |
|--------|------|----------|-----------------|
| `LocalShellCall` | 沙箱内执行 shell 命令 | ✓ | `Bash` |
| `ApplyPatch` | 自有 diff 格式修改文件 | ✓ | `Edit`（逐文件） |
| `WebSearchCall` | 网络搜索 | ✓ | `WebSearch` |
| `McpToolCall` | 调用 MCP 服务器工具 | ✓ | `mcp__*` |
| `ImageGenerationCall` | DALL-E 图片生成 | ✓ | 无 |
| `GhostSnapshot` | 环境快照/检查点 | ✓ | 无（有文件检查点） |
| `Compaction` | 主动压缩上下文 | ✓ | 自动 5 层压缩 |
| `DynamicToolCall` | 动态注册运行时工具 | ✓ | 无（延迟加载不同） |
| `ToolSearchCall` | 搜索可用工具 | ✓ | `ToolSearch`（延迟加载） |

**Qwen Code 对标**：Codex 仅 9 个工具走"精简路线"，通过 `LocalShellCall` 内的 `CommandAction` 子操作（Read/Search/ListFiles）替代独立工具。Claude Code 走"全面覆盖"路线（42 工具）。Qwen Code（~30 工具）处于中间位置。关键差异在于 Codex 的 `ApplyPatch` 支持单次调用修改多文件，效率高于逐文件 `Edit`。

### CommandAction 子操作

`LocalShellCall` 内部支持轻量级子操作，无需启动完整 shell：

| 操作 | 功能 | 说明 |
|------|------|------|
| `Read` | 读取文件内容 | 支持行范围读取 |
| `Search` | 基于 ripgrep 的代码搜索 | 正则 + glob 过滤 |
| `ListFiles` | 列出目录文件 | 递归/非递归 |

### ApplyPatch 格式规范

Codex 使用自有的补丁格式（非标准 unified diff），以三个 `@` 符号区分：

```
*** Begin Patch
*** Add File: src/new-module.ts
+// 新文件内容
+export function newFeature() {
+  return true;
+}

*** Update File: src/main.ts
@@@ -10,3 +10,4 @@@
 import { foo } from './foo';
 import { bar } from './bar';
+import { baz } from './baz';

*** Delete File: src/deprecated.ts

*** End Patch
```

**开发者启示**：Claude Code 的 `Edit` 工具使用 `old_string → new_string` 精确替换，每次只改一个位置。Codex 的 `ApplyPatch` 更接近传统 diff，单次可修改多文件。对于大规模重构场景，batch patch 效率更高；对于精确编辑场景，string replacement 更安全。

---

## MCP 双向支持

Codex CLI 是唯一同时支持 MCP 客户端和服务器模式的主流 CLI Agent。

### 作为 MCP 客户端

```bash
codex mcp list                                    # 列出所有已配置服务器
codex mcp add <name> <command> [args...]           # 添加服务器
codex mcp remove <name>                            # 移除服务器
codex mcp login <name>                             # OAuth 认证（HTTP MCP）
```

配置文件声明（`~/.codex/config.toml`）：

```toml
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "ghp_xxx" }
```

### 作为 MCP 服务器

```bash
codex mcp-server    # 以 stdio MCP 服务器模式运行
```

支持 MCP 协议版本 `2024-11-05`，暴露 tools、resources、prompts 能力。其他 Agent（如 Claude Code、Cursor）可通过 MCP 协议调用 Codex 的代理能力。

**Qwen Code 对标**：Qwen Code 仅支持 MCP 客户端模式。增加 MCP 服务器模式可以让 Qwen Code 被其他 Agent 调用，形成 Agent 组合——例如 Claude Code 调用 Qwen Code 作为"代码生成后端"。

---

## Feature Flags（52 个）

Codex CLI 拥有完善的 Feature Flag 系统，52 个标志分为 5 种状态。这是 Claude Code（22 个 build-time Feature Flag）之外唯一有系统化 Feature Flag 管理的 Agent。

### Stable（默认开启，10 个）

| 标志名 | 说明 | 开发者关注点 |
|--------|------|------------|
| `fast_mode` | 跳过部分确认加速执行 | 类似 Claude Code 的快速模式 |
| `multi_agent` | 多代理协作 | 主代理可分派子任务给子代理 |
| `personality` | 代理人格自定义 | Claude Code 无此功能 |
| `shell_snapshot` | Shell 状态快照 | 上下文恢复用 |
| `shell_tool` | 内置 shell 执行 | 核心工具 |
| `enable_request_compression` | 请求压缩 | 减少传输开销 |
| `skill_mcp_dependency_install` | 技能 MCP 依赖自动安装 | 简化配置 |
| `unified_exec` | 统一执行模式 | 内部架构 |
| `undo` | 撤销操作（默认关闭） | Claude Code 有文件检查点 |
| `use_legacy_landlock` | 旧版沙箱（默认关闭） | 向后兼容 |

### Experimental（4 个）

| 标志名 | 说明 | 开发者关注点 |
|--------|------|------------|
| `guardian_approval` | 安全审查子代理，自动审查高风险操作 | 额外 token 消耗，类似"安全 Agent" |
| `apps` | ChatGPT Apps/Connectors 集成 | OpenAI 生态独有 |
| `js_repl` | 持久 Node.js REPL（需 Node >= v22.22.0） | 交互式 JS 执行 |
| `tui_app_server` | App-Server 驱动的 TUI | 架构统一化方向 |

### Under Development（关键，18 个）

| 标志名 | 说明 | Qwen Code 启示 |
|--------|------|---------------|
| `codex_hooks` | Hook 系统 | Claude Code 有 24 种，Qwen Code 有基础 Hook |
| `voice_transcription` | 语音转录输入 | 新交互模态 |
| `realtime_conversation` | 实时语音对话 | 多模态方向 |
| `memories` | 代理记忆系统 | Claude Code 有 CLAUDE.md + Auto Dream |
| `plugins` | 插件系统 | Claude Code 已有插件机制 |
| `enable_fanout` | 子任务扇出并行 | 类似 Claude Code 的 Swarm |
| `child_agents_md` | 子代理 AGENTS.md | 多代理指令继承 |
| `image_generation` | 图片生成 | DALL-E 集成 |
| `code_mode` | 代码模式 | 专注代码场景 |
| `apply_patch_freeform` | 自由格式 ApplyPatch | 容错性更高的补丁 |

**开发者分析**：Codex 的 Feature Flag 是运行时管理的（`codex features enable/disable`），Claude Code 的是 build-time DCE（编译时移除）。运行时方式更灵活（用户可自行启用），但安全性低于编译时移除（无法通过 strings 提取未发布功能）。Qwen Code 目前无 Feature Flag 系统，建议至少实现运行时 Feature Flag 来管理实验性功能。

---

## 配置系统

### 配置文件（TOML 格式）

```toml
# ~/.codex/config.toml
model = "gpt-5.1-codex"
approval_mode = "untrusted"
sandbox = "workspace-write"
model_reasoning_effort = "medium"
plan_mode_reasoning_effort = "high"
personality = "简洁专业，优先使用中文回复"
compact_prompt = "保留关键上下文，压缩冗余对话"

# 自定义模型提供者
[model_providers.local]
base_url = "http://localhost:1234/v1"
api_key = "lm-studio"

# MCP 服务器
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "."]

# 多代理配置
[agents.reviewer]
model = "gpt-5.1-codex"
instructions = "你是一个代码审查专家"

# Profile 支持
[profiles.work]
model = "gpt-5.1-codex"
approval_mode = "on-request"
```

### 指令文件层级

| 优先级 | 文件 | 作用域 | Claude Code 对应 |
|--------|------|--------|-----------------|
| 1（最低） | `~/.codex/instructions.md` | 全局（用户级） | `~/.claude/CLAUDE.md` |
| 2 | `CODEX.md` | 项目级 | `CLAUDE.md`（项目根） |
| 3 | `AGENTS.md` | 项目级（替代名称） | `CLAUDE.md`（各目录） |
| 4（最高） | `SKILL.md` | 技能级 | Skill Frontmatter |

**Qwen Code 对标**：Codex 的 4 级指令层级与 Claude Code 的 5 层设置体系思路一致——从全局到局部逐级细化。Qwen Code 建议至少实现全局/项目两级指令文件。

### 关键配置键

| 配置键 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `model` | string | 默认模型 | `gpt-5.1-codex` |
| `approval_mode` | string | 审批模式 | `untrusted` |
| `sandbox` | string | 沙箱级别 | `read-only` |
| `model_reasoning_effort` | string | 推理努力程度（low/medium/high） | `medium` |
| `personality` | string | 代理人格描述 | 空 |
| `compact_prompt` | string | 上下文压缩自定义提示 | 空 |
| `mcp_servers` | table | MCP 服务器配置表 | 空 |
| `model_providers` | table | 自定义模型提供者 | 空 |
| `agents` | table | 多代理配置 | 空 |
| `skills` | table | 技能配置 | 空 |
| `review_model` | string | 代码审查专用模型 | 空 |
| `developer_instructions` | string | 开发者指令（系统级） | 空 |

### 环境变量

| 环境变量 | 说明 |
|----------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥（必需，除非使用 OAuth） |
| `OPENAI_BASE_URL` | 自定义 API 端点 |
| `OPENAI_ORG_ID` | 组织 ID |
| `CODEX_HOME` | 配置目录（覆盖默认 `~/.codex`） |

---

## 会话系统

每个 Codex 会话拥有唯一 UUID，持久化存储在 `~/.codex/sessions/`。

### 会话生命周期

```
创建 → 活跃 → 暂停/退出 → resume 恢复 / fork 分叉
```

### 操作方式

```bash
# CLI 方式
codex resume <session-uuid>         # 恢复指定会话
codex resume --last                 # 恢复最近会话
codex fork <session-uuid>           # 从指定会话分叉
codex fork --last                   # 分叉最近会话

# TUI 斜杠命令
/fork                               # 从当前状态分叉
/resume                             # 恢复会话
```

**Qwen Code 对标**：Claude Code 有崩溃恢复（自动检测 + 合成续行），Gemini CLI 有 `gemini resume`。Qwen Code 缺少会话持久化，长任务中断后需从头开始。建议至少实现 resume 功能。

---

## 技能系统

### 概念

技能（Skills）是可复用的指令包，通过 `SKILL.md` 文件定义特定能力，可声明 MCP 依赖。

```markdown
# 技能名称

## 指令
描述此技能的行为规范...

## MCP 依赖
- server-name: 所需的 MCP 服务器
```

**开发者启示**：Codex 的技能系统与 Claude Code 的 Skill 系统类似——都是通过 Markdown 文件定义指令和约束。差异在于 Codex 的技能可以声明 MCP 依赖并自动安装（`skill_mcp_dependency_install` flag），Claude Code 的 Skill 依赖手动配置。

---

## 验证记录

> 本文档通过二进制逆向分析和官方文档双重验证。

**二进制分析（v0.116.0，137MB ELF static-pie x86-64 Rust）：**
- CLI 子命令：`codex --help` 确认 15 个子命令
- 审批模式：v0.116.0 仅接受 untrusted/on-request/on-failure/never（granular 返回 invalid value）
- TUI 斜杠命令：`strings` 提取 + 官方文档交叉验证确认 28 个
- Feature flags：`codex features list` 确认 52 个
- App-Server：IPC 消息字符串提取确认 90+ 方法

**官方文档验证：**
- [斜杠命令](https://developers.openai.com/codex/cli/slash-commands) — 28 个命令完整列表
- [CLI 参考](https://developers.openai.com/codex/cli/reference) — 确认 `--ask-for-approval`（非 --approval-mode）
- [审批与安全](https://developers.openai.com/codex/agent-approvals-security)
