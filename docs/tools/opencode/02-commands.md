# 2. 命令与工具

## CLI 命令

```bash
# 启动 TUI
opencode

# 非交互模式执行
opencode run "重构这个函数"

# 指定代理（如 plan 模式）
opencode --agent plan

# 仅启动 HTTP 服务器
opencode serve

# 启动工作区服务（实验性）
opencode workspace-serve

# 管理认证
opencode auth login anthropic

# 列出可用模型
opencode models

# 管理 MCP 服务器
opencode mcp list

# 管理代理
opencode agent list

# 会话管理
opencode session list

# 统计信息
opencode stats

# Web 控制台
opencode web

# 卸载
opencode uninstall
```

## 工具系统

> **⚠ 重大修正（第 N 轮审核）：** 原文档基于旧 TypeScript 版本。OpenCode 当前为 **Go 实现**（`internal/` 目录），工具列表已完全不同。

### 当前工具（Go 版，源码：`internal/llm/agent/tools.go`，12 个）

| 工具 | 用途 | 来源 |
|------|------|------|
| **bash** | Shell 命令执行 | Go 源码确认 |
| **edit** | 文件编辑 | Go 源码确认 |
| **write** | 文件写入 | Go 源码确认 |
| **view** | 读取文件内容（带行号） | Go 源码确认 |
| **glob** | 文件模式匹配搜索 | Go 源码确认 |
| **grep** | 正则内容搜索 | Go 源码确认 |
| **ls** | 列出目录内容 | Go 源码确认 |
| **fetch** | 抓取 Web 内容 | Go 源码确认 |
| **patch** | 应用代码补丁 | Go 源码确认 |
| **sourcegraph** | Sourcegraph 代码搜索 | Go 源码确认 |
| **agent** | 启动搜索子代理 | Go 源码确认 |
| **diagnostics** | LSP 诊断（需 LSP 客户端） | Go 源码确认（条件加载） |

**TaskAgent 只读工具子集**（用于子代理）：glob, grep, ls, sourcegraph, view

### 内置命令（2 个，源码：`RegisterCommand`）

| 命令 | 用途 |
|------|------|
| `init` | 初始化项目（创建/更新 OpenCode.md） |
| `compact` | 压缩会话（摘要后创建新会话） |

支持自定义命令：`~/.config/opencode/commands/` 和 `.opencode/commands/` 目录。

### 快捷键（Go TUI，源码：`internal/tui/tui.go`）

| 快捷键 | 功能 |
|--------|------|
| **Ctrl+K** | 命令面板（**非 Ctrl+P**，原文档有误） |
| Ctrl+L | 查看日志 |
| Ctrl+S | 切换会话 / 发送消息 |
| Ctrl+F | 文件选择器（上传） |
| Ctrl+O | 模型选择 |
| Ctrl+T | 切换主题 |
| Ctrl+N | 新建会话 |
| Ctrl+E | 打开外部编辑器 |
| Ctrl+H / Ctrl+? | 切换帮助 |
| @ | 补全对话框 |
| Esc | 取消 |

## 多代理系统

| 代理 | 类型 | 权限 | 用途 |
|------|------|------|------|
| **build** | 主代理 | 完全访问 + question + plan_enter | 默认代理，代码开发、文件编辑 |
| **plan** | 主代理 | 只读（edit deny）+ plan_exit | 代码分析、规划，只能写 plan 文件 |
| **general** | 子代理 | 受限（无 todo） | 复杂多步骤研究，可并行执行 |
| **explore** | 子代理 | 只读（grep/glob/list/read/bash/webfetch/websearch/codesearch） | 快速代码库搜索，支持 quick/medium/thorough |
| **compaction** | 隐藏 | 全部 deny | 会话压缩 |
| **title** | 隐藏 | 内部 | 自动标题生成 |
| **summary** | 隐藏 | 内部 | 自动摘要生成 |

- 支持通过 `opencode.json` 定义自定义代理（独立模型、温度、系统提示、最大步数）
- 子代理通过 `@general`、`@explore` 消息引用调用

## 命令面板（Ctrl+P）

v1.0.0 新增命令面板，类似 VS Code 的 Ctrl+P 快速操作入口，提供快速切换代理、模型、会话等功能。

## 权限系统

```
规则优先级：远程 → 全局 → 项目 → .opencode → 内联
权限类型（config schema 定义）：
  read, edit, glob, grep, list, bash, task,
  external_directory, todowrite, todoread, question,
  webfetch, websearch, codesearch, lsp, doom_loop, skill
  + catchall（任意自定义 key）
操作：allow / deny / ask
```

- 基于 Tree-sitter 的 bash 命令 AST 解析，自动提取目录和操作
- `.env*` 文件默认 ask 确认（`.env.example` 除外）
- 外部目录默认 ask 确认
- Doom Loop 保护：连续权限拒绝自动中断
- Provider whitelist/blacklist：`enabled_providers` / `disabled_providers` 配置

## 配置

```jsonc
// opencode.json 或 .opencode/opencode.json
{
  "agent": {
    "build": {
      "model": "anthropic/claude-sonnet-4"
    },
    // 自定义代理
    "my-agent": {
      "description": "Custom agent",
      "mode": "subagent",
      "model": "openai/gpt-5.4",
      "temperature": 0.7,
      "steps": 50
    }
  },
  "provider": {
    "anthropic": { "apiKey": "${ANTHROPIC_API_KEY}" },
    // 自定义 provider
    "my-local": {
      "api": "http://localhost:11434/v1",
      "models": {
        "llama3": { "id": "llama3" }
      }
    }
  },
  "plugin": ["opencode-plugin-example"],
  "permission": {
    "read": "allow",
    "edit": { "**": "allow", "*.env": "ask" },
    "bash": "ask",
    "external_directory": { "*": "ask" }
  },
  // Provider 白/黑名单
  "enabled_providers": ["anthropic", "openai"],
  "disabled_providers": ["groq"]
}
```

**配置优先级（低→高）**：
1. 远程 `.well-known/opencode`（企业）
2. 全局 `~/.config/opencode/opencode.json`
3. `OPENCODE_CONFIG` 环境变量
4. 项目 `opencode.json`
5. `.opencode/opencode.json`
6. `OPENCODE_CONFIG_CONTENT` 内联 JSON
