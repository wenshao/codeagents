# 4. 工具与代理系统

## 工具系统

注册在 ToolRegistry 中的工具（17 核心 + 6 任务追踪 = 23 内置）：

| Agent | 显示名 | 用途 | 条件 |
|------|--------|------|------|
| **glob** | FindFiles | 文件模式匹配搜索 | 始终可用 |
| **read_file** | ReadFile | 读取文件内容（支持行范围） | 始终可用 |
| **write_file** | WriteFile | 创建/覆写文件 | 始终可用 |
| **replace** | Edit | 编辑文件（instruction 或 old/new string） | 始终可用 |
| **list_directory** | ReadFolder | 列出目录内容 | 始终可用 |
| **read_many_files** | ReadManyFiles | 批量读取多个文件 | 始终可用 |
| **grep_search** | SearchText | 正则内容搜索 | 始终可用 |
| **google_web_search** | GoogleSearch | Web 搜索（带 Grounding 引用） | 始终可用 |
| **web_fetch** | WebFetch | 抓取 URL 内容（HTML→Text，250KB 限制） | 始终可用 |
| **run_shell_command** | — | 执行 Shell 命令（支持后台/交互模式） | 始终可用 |
| **ask_user** | Ask User | 向用户提问（多种问题类型+选项） | 始终可用 |
| **save_memory** | MemoryTool | 存储事实到 GEMINI.md | 始终可用 |
| **get_internal_docs** | — | 检索内部文档 | 始终可用 |
| **activate_skill** | — | 按名称激活自定义技能 | 始终可用 |
| **write_todos** | — | 创建/更新任务列表 | 始终可用 |
| **enter_plan_mode** | — | 进入只读规划模式 | 始终可用 |
| **exit_plan_mode** | — | 退出规划模式（输出 plan 文件） | 始终可用 |
| **tracker_create_task** | — | 创建任务 | 始终可用 |
| **tracker_update_task** | — | 更新任务状态/内容 | 始终可用 |
| **tracker_get_task** | — | 获取任务详情 | 始终可用 |
| **tracker_list_tasks** | — | 列出所有任务 | 始终可用 |
| **tracker_add_dependency** | — | 添加任务依赖关系 | 始终可用 |
| **tracker_visualize** | — | 可视化任务层级 | 始终可用 |

此外，MCP 工具以 `mcp_{serverName}_{toolName}` 格式动态注册，支持通配符策略（`mcp_*`、`mcp_serverName_*`）。工具发现命令注册的工具以 `discovered_tool_` 前缀标识。

**Plan Mode 可用工具**：
- **自动允许**：glob、grep_search、read_file、list_directory、google_web_search、activate_skill、get_internal_docs、codebase_investigator、cli_help
- **需确认**：ask_user、save_memory、MCP 工具（readOnlyHint=true）
- **受限写入**：write_file/replace 仅限 `.gemini/tmp/.../plans/*.md` 文件

## 多代理系统

| 代理 | 类型 | 工具权限 | 模型 | 用途 |
|------|------|----------|------|------|
| **generalist** | 子代理 | 完全访问 | 继承主模型 | 通用多步骤任务，20 轮/10 分钟 |
| **codebase_investigator** | 子代理 | 只读（glob/grep/ls/read_file） | gemini-3-flash-preview（回退 gemini-2.5-pro） | 代码库分析和架构映射，10 轮/3 分钟 |
| **memory_manager** | 子代理（条件） | 读写（ask_user/edit/glob/grep/ls/read/write） | flash（gemini-3-flash-preview） | 记忆增删改、去重、组织，10 轮/5 分钟 |
| **cli_help** | 子代理 | get_internal_docs | flash（gemini-3-flash-preview） | 回答 CLI 功能问题，10 轮/3 分钟 |
| **browser** | 子代理（条件） | 浏览器 MCP 工具 | gemini-3-flash-preview（回退 gemini-2.5-flash） | Web 自动化（导航、点击、截图分析），50 轮/10 分钟 |

- browser 和 memory_manager 为**条件注册**代理，需在设置中启用
- 支持通过配置文件定义**自定义代理**（独立模型、提示、最大步数、工具过滤）
- 支持**远程代理**（A2A 协议，通过 agentCardUrl 注册）
- 代理终止模式：`GOAL`（成功）、`MAX_TURNS`、`TIMEOUT`、`ERROR`、`ABORTED`、`ERROR_NO_COMPLETE_TASK_CALL`

## MCP 集成

**协议支持**：Stdio、SSE 传输
**配置方式**：
```jsonc
// settings.json
{
  "mcp": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    }
  }
}
```

**MCP 工具命名**：`mcp_{serverName}_{toolName}`（如 `mcp_github_create_issue`）
**OAuth 支持**：MCPOAuthConfig，Token 存储支持 Keychain/文件/混合模式
**自动发现**：从配置、扩展、工作区自动发现并注册
**策略通配符**：`mcp_*`（所有 MCP）、`mcp_serverName_*`（特定服务器所有工具）

## 扩展系统

**扩展结构**：
```typescript
{
  name: string
  version: string
  isActive: boolean
  path: string
  installMetadata?: ExtensionInstallMetadata
  mcpServers?: Record<string, MCPServerConfig>  // MCP 服务器
  contextFiles: string[]                         // 上下文文件
  excludeTools?: string[]                        // 排除工具
  hooks?: { [K in HookEventName]?: HookDefinition[] }  // Hook
  settings?: ExtensionSetting[]                  // 设置项
  skills?: SkillDefinition[]                     // 技能
  agents?: AgentDefinition[]                     // 代理
  themes?: CustomTheme[]                         // 自定义主题
  rules?: PolicyRule[]                           // 策略规则
  checkers?: SafetyCheckerRule[]                 // 安全检查器
  plan?: { directory?: string }                  // 规划配置
}
```

**安装方式**：
- `git` — 从 Git 仓库
- `local` — 本地目录
- `link` — 符号链接
- `github-release` — GitHub Release 归档

**官方扩展**：CloudRun、Security（`/security:analyze`）、Hugging Face、Monday.com、ElevenLabs、Jules、Conductor、Endor Labs、Data Commons、AlloyDB、BigQuery、Cloud SQL 等数据库扩展

## A2A 协议（Agent-to-Agent）

- **框架**：Express.js 5.1.0
- **端口**：通过 `CODER_AGENT_PORT` 环境变量配置，默认自动分配
- **协议**：HTTP/JSON
- **认证方式**：API Key、OAuth2、Google Credentials、HTTP、Gateway
- **活动事件**：TOOL_CALL_START、TOOL_CALL_END、THOUGHT_CHUNK、ERROR
- **远程代理**：通过 `agentCardUrl` 注册，支持 HTTP 认证（v0.33.0+）
