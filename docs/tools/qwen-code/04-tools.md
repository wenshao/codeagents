# 4. Qwen Code 工具系统

Qwen Code 内置 16 个核心工具，加上通过 MCP 动态发现的工具和命令发现的工具。

> 源码: `packages/core/src/config/config.ts`（L2146-2194 工具注册）
> 工具名称定义: `packages/core/src/tools/tool-names.ts`

## 工具注册机制

| 来源 | 注册方式 | 位置 |
|------|---------|------|
| 核心工具 | `config.ts` 静态注册 | `packages/core/src/tools/*.ts` |
| MCP 工具 | `McpClientManager` 动态发现 | `packages/core/src/tools/mcp-client-manager.ts` |
| 发现的工具 | `ToolRegistry` 运行时注册 | `packages/core/src/tools/tool-registry.ts` |

## 核心工具（16 个）

### 文件操作

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **ReadFile** | Read | 读取文件内容，支持行范围、图片/PDF | `file_path`, `offset?`, `limit?` | `tools/read-file.ts` |
| **WriteFile** | Edit | 创建/覆写文件 | `file_path`, `content` | `tools/write-file.ts` |
| **Edit** | Edit | 精确文本替换（old_string → new_string） | `file_path`, `old_string`, `new_string`, `replace_all?` | `tools/edit.ts` |
| **ListFiles** | Read | 列出目录内容 | `path`, `ignore?`, `file_filtering_options?` | `tools/ls.ts` |

### 搜索

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **Grep** | Search | 基于 ripgrep 的正则搜索 | `pattern`, `path?`, `glob?`, `limit?` | `tools/grep.ts` |
| **Glob** | Search | 文件模式匹配 | `pattern`, `path?` | `tools/glob.ts` |

### 执行

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **Shell** | Execute | 执行 Shell 命令 | `command`, `is_background?`, `timeout?`, `description?`, `directory?` | `tools/shell.ts` |

### 网络

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **WebFetch** | Fetch | 抓取 URL 内容并用 AI 处理 | `url`, `prompt` | `tools/web-fetch.ts` |
| **WebSearch** | Fetch | Web 搜索（Tavily/Google/DashScope） | `query`, `provider?` | `tools/web-search/index.ts` |

> WebSearch 提供商（源码: `packages/core/src/tools/web-search/providers/`）：
> - Tavily: `providers/tavily-provider.ts`
> - Google: `providers/google-provider.ts`
> - DashScope: `providers/dashscope-provider.ts`

### 任务管理

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **TodoWrite** | Other | 创建/管理结构化任务列表 | `todos[]` | `tools/todoWrite.ts` |

### 记忆

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **SaveMemory** | Edit | 保存信息到长期记忆 | `fact`, `scope`（"global"/"project"） | `tools/memoryTool.ts` |

### 代理与技能

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **Agent** | Other | 启动子代理处理复杂任务 | `skill?`, 动态参数 | `tools/agent.ts` |
| **Skill** | Read | 执行技能 | `skill` | `tools/skill.ts` |
| **ExitPlanMode** | Other | 退出规划模式 | （无） | `tools/exitPlanMode.ts` |

### 交互

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **AskUserQuestion** | Other | 执行期间向用户提问 | `questions[]` | `tools/askUserQuestion.ts` |

### 代码智能

| 工具 | Kind | 用途 | 关键参数 | 源码 |
|------|------|------|---------|------|
| **LSP** | Other | 语言服务器协议集成 | （动态） | `tools/lsp.ts` |

## 条件工具

| 工具 | 条件 | 源码 |
|------|------|------|
| **ripGrep** | 系统安装了 ripgrep 时替代内置 Grep | `tools/ripGrep.ts` |

## MCP 动态工具

MCP 工具通过 `McpClientManager` 在运行时动态发现：

```
McpClientManager → McpClient.list_tools() → DiscoveredMCPTool[]
```

MCP 工具以 `mcp__serverName__toolName` 格式注册到 `ToolRegistry`。

## 工具权限分类

每个工具有 Kind 属性，影响权限行为：

| Kind | 默认权限行为 | 工具 |
|------|-------------|------|
| Read | 较宽松 | ReadFile, ListFiles, Grep, Glob, Skill |
| Edit | 需确认 | WriteFile, Edit, SaveMemory |
| Execute | 严格确认 | Shell |
| Fetch | 需确认 | WebFetch, WebSearch |
| Other | 视情况 | TodoWrite, Agent, ExitPlanMode, LSP, AskUserQuestion |

## 工具调度管线

源码: `packages/core/src/core/coreToolScheduler.ts`（1790 行）

```
LLM 工具调用请求
    │
    ▼
参数校验 → validating 状态
    │
    ▼
权限检查 → getDefaultPermission()
    │  deny > ask > allow > default
    ▼
Hook 触发 → PreToolUse
    │
    ▼
用户确认 → awaiting_approval（plan/default 模式）
    │
    ▼
工具执行 → executing 状态
    │  支持实时输出流、超时控制
    ▼
Hook 触发 → PostToolUse / PostToolUseFailure
    │
    ▼
结果返回 LLM → 继续循环或完成
```
