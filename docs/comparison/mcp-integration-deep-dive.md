# 28. MCP 集成实现深度对比

> MCP（Model Context Protocol）正在成为 AI 编程代理的扩展标准。8/10 个工具支持 MCP，但实现深度差异巨大——从"全工具 MCP 原生"到"仅基础客户端"。

## 总览

| Agent | 架构角色 | 传输协议 | 工具命名 | 策略控制 | OAuth |
|------|---------|---------|---------|---------|-------|
| **Goose** | **全部工具基于 MCP** | Stdio/StreamableHTTP/Builtin | 标准 MCP 发现 | 4 模式 + Per-tool | ✗ |
| **Claude Code** | 扩展 | Stdio/SSE/Streamable-HTTP | `mcp__server__tool`（双下划线） | deny→ask→allow 3 层 | ✓ |
| **Gemini CLI** | 扩展 | Stdio/SSE | `mcp_{server}_{tool}`（单下划线） | **TOML 通配符 + 正则** | ✓ |
| **Kimi CLI** | 扩展 | Stdio/HTTP | 动态注册 | Per-tool 审批 + 超时 | ✓ |
| **Qwen Code** | 扩展 | Stdio/SSE/HTTP | `mcp_{server}_{tool}`（继承） | 继承 Gemini + **运行时启停** | ✓ |
| **Copilot CLI** | 内置 GitHub MCP | 专有 | GitHub 默认子集 | CLI 参数 | ✓ |
| **OpenCode** | 扩展 | StreamableHTTP/SSE/Stdio | — | 模式匹配 | ✓ |
| **Cline** | 扩展 | — | McpHub 前缀 | WebView 审批 | ✓ |
| **OpenHands** | 扩展 | FastMCP | — | 安全分析器 | ✗ |
| **Aider** | — | — | — | — | — |
| **SWE-agent** | — | — | — | — | — |

---

## 一、Goose：MCP 原生架构（全工具 MCP 驱动）

> 来源：[Goose MCP 文档](https://block.github.io/goose/docs/)，`rmcp` Rust SDK

**所有工具都通过 MCP 协议实现**，没有"内置工具"概念：

```
Host（Goose）
  ├── Client 1 → MCP Server: developer（Builtin 进程内）
  ├── Client 2 → MCP Server: memory（Builtin 进程内）
  ├── Client 3 → MCP Server: custom-tool（Stdio 子进程）
  └── Client 4 → MCP Server: remote-service（StreamableHTTP）
```

### 三种传输方式

| 传输 | 方式 | 适用 |
|------|------|------|
| **Stdio** | 子进程 stdin/stdout | 本地工具 |
| **StreamableHTTP** | HTTP 远程 | 远程服务 |
| **Builtin** | 进程内直接调用 | 内置核心工具 |

### 配置示例

```yaml
# ~/.config/goose/config.yaml
extensions:
  developer:
    type: builtin
  custom-tool:
    type: stdio
    command: "uv"
    args: ["run", "path/to/extension"]
    env:
      API_KEY: "${ENV_VAR}"
    timeout: 300
```

### 权限控制

4 种审批模式 × Per-tool 规则（AllowOnce / AlwaysAllow / NeverAllow）。

---

## 二、Claude Code：双下划线命名 + Streamable-HTTP

> 来源：`claude --help` v2.1.83、06-settings.md

### 工具命名约定

```
mcp__serverName__toolName
```

示例：`mcp__github__create_issue`、`mcp__filesystem__read_file`

### 权限规则

```json
{
  "permissions": {
    "allow": ["mcp__filesystem__read_file"],
    "ask": ["mcp__github__*"],
    "deny": ["mcp__dangerous__*"]
  }
}
```

规则语法支持通配符：`mcp__serverName__*` 匹配特定服务器的所有工具。

### 配置

```jsonc
// .claude/settings.json
{
  "mcp": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "..." }
    }
  }
}
```

### OAuth + Channels

- OAuth 认证通过 `claude.ai/api/oauth/authorize`
- Token 存储在系统 Keychain
- **Channels**（研究预览 2026-03-20）：MCP 服务器可主动推送消息到会话

---

## 三、Gemini CLI：TOML 策略引擎（最细粒度控制）

> 源码：`packages/core/src/policy/`

### 工具命名约定

```
mcp_{serverName}_{toolName}
```

注意：**单下划线**（与 Claude Code 的双下划线不同）。

### TOML 策略控制

```toml
# 通配符匹配所有 MCP 工具
[[tool_policies]]
tool_name_pattern = "mcp_*"
approval_mode = "ask"

# 特定服务器自动批准
[[tool_policies]]
tool_name_pattern = "mcp_filesystem_*"
approval_mode = "auto"

# 正则匹配参数
[[tool_policies]]
tool_name_pattern = "mcp_shell_execute"
argsPattern = "npm (test|lint)"
approval_mode = "auto"

# 基于 MCP 注解匹配
[[tool_policies]]
tool_name_pattern = "*"
toolAnnotation.readOnlyHint = true
approval_mode = "auto"
```

### 5 层策略优先级

| 层级 | 来源 |
|------|------|
| Admin（最高） | `/etc/gemini-cli/policies` |
| User | `~/.gemini/policies/*.toml` |
| Workspace | `.gemini/policies/*.toml` |
| Extension | 扩展定义 |
| Default（最低） | 9 个内置策略 |

### OAuth 支持

- MCPOAuthConfig：token 存储模式（Keychain / file / hybrid）
- OAuth 2.0 device flow

---

## 四、Kimi CLI：超时控制 + 管理命令

> 源码：`src/kimi_cli/soul/toolset.py`，SDK：`fastmcp`

### 管理命令（最丰富）

```bash
kimi mcp list          # 列出 MCP 服务器
kimi mcp add <name>    # 添加
kimi mcp remove <name> # 移除
kimi mcp auth <name>   # OAuth 认证
kimi mcp test <name>   # 测试连接
```

### 超时控制

```toml
[mcp.client]
tool_call_timeout_ms = 60000    # MCP 工具调用超时 60 秒
```

### 凭证自动注入

Plugin 系统自动将 `api_key` + `base_url` 从 LLM 配置注入 MCP 服务器，支持 OAuth token 实时刷新。

---

## 五、Copilot CLI：内置 GitHub MCP

> 来源：官方文档 + 二进制分析

### 默认工具子集

Copilot CLI 内置 `github-mcp-server`，但**默认不启用所有工具**：

```bash
# 启用特定工具
--add-github-mcp-tool <tool>

# 启用工具集
--add-github-mcp-toolset <set>

# 启用所有
--enable-all-github-mcp-tools

# 额外 MCP 配置
--additional-mcp-config <json>

# 禁用内置
--disable-builtin-mcps
```

配置文件：`~/.copilot/mcp-config.json`

---

## 工具命名约定对比

| Agent | 命名格式 | 示例 |
|------|---------|------|
| **Claude Code** | `mcp__server__tool`（双下划线） | `mcp__github__create_issue` |
| **Gemini CLI** | `mcp_{server}_{tool}`（单下划线） | `mcp_github_create_issue` |
| **Qwen Code** | 继承 Gemini（单下划线） | `mcp_github_create_issue` |
| **Goose** | 标准 MCP 发现 | 由 MCP 协议决定 |
| **其他** | 未标准化 | — |

> **互操作性问题**：Claude Code 和 Gemini CLI 的命名约定不同（双下划线 vs 单下划线），同一个 MCP 服务器在两个工具中的工具名称不一致。

---

## MCP 支持成熟度评估

| 维度 | Goose | Claude Code | Gemini CLI | Kimi CLI | 其他 |
|------|-------|------------|-----------|---------|------|
| 传输协议 | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★★☆☆☆ |
| 策略控制 | ★★★☆☆ | ★★★★☆ | **★★★★★** | ★★★☆☆ | ★★☆☆☆ |
| 管理命令 | ★★★☆☆ | ★★★☆☆ | ★★★☆☆ | **★★★★★** | ★★☆☆☆ |
| OAuth | ✗ | ✓ | **✓✓** | ✓ | 部分 |
| 原生程度 | **全原生** | 扩展 | 扩展 | 扩展 | 扩展 |

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Goose | [官方文档](https://block.github.io/goose/docs/) + EVIDENCE.md | 开源 |
| Claude Code | `claude --help` + 06-settings.md | 二进制 + 文档 |
| Gemini CLI | 05-policies.md + 04-tools.md | 开源 |
| Kimi CLI | 03-architecture.md + EVIDENCE.md | 开源 |
| Copilot CLI | 03-architecture.md + EVIDENCE.md | SEA 反编译 |
