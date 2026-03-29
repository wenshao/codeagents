# 5. Qwen Code 配置系统

> 来源：[官方文档](https://qwenlm.github.io/qwen-code-docs/zh/users/configuration/settings/)（2026-03 访问），v0.3.0+ 嵌套结构格式

## 配置层级（7 层优先级）

| 层级 | 配置来源 | 说明 |
|------|----------|------|
| 1（最低） | 默认值 | 硬编码默认值 |
| 2 | 系统默认配置文件 | `/etc/qwen-code/system-defaults.json` |
| 3 | 用户配置文件 | `~/.qwen/settings.json` |
| 4 | 项目配置文件 | `.qwen/settings.json` |
| 5 | 系统配置文件 | `/etc/qwen-code/settings.json`（企业管控） |
| 6 | 环境变量 | `QWEN_*` 系列 + `.env` 文件 |
| 7（最高） | 命令行参数 | `--model`、`--yolo` 等 |

## 设置文件位置

| 文件类型 | Linux | macOS | Windows |
|----------|-------|-------|---------|
| 系统默认 | `/etc/qwen-code/system-defaults.json` | `/Library/Application Support/QwenCode/system-defaults.json` | `C:\ProgramData\qwen-code\system-defaults.json` |
| 用户设置 | `~/.qwen/settings.json` | 同 | 同 |
| 项目设置 | `.qwen/settings.json` | 同 | 同 |
| 系统设置 | `/etc/qwen-code/settings.json` | `/Library/Application Support/QwenCode/settings.json` | `C:\ProgramData\qwen-code\settings.json` |

> **环境变量引用**：`settings.json` 中字符串值支持 `$VAR_NAME` 或 `${VAR_NAME}` 语法引用环境变量。

## 设置项参考

> 以下覆盖官方文档中的所有分类。路径可通过 `QWEN_CODE_SYSTEM_DEFAULTS_PATH` 和 `QWEN_CODE_SYSTEM_SETTINGS_PATH` 环境变量覆盖。

### general（常规）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `general.preferredEditor` | string | — | 打开文件的首选编辑器 |
| `general.vimMode` | boolean | `false` | 启用 Vim 键绑定 |
| `general.enableAutoUpdate` | boolean | `true` | 自动检查并安装更新 |
| `general.gitCoAuthor` | boolean | `true` | Git 提交自动添加 Co-authored-by |
| `general.checkpointing.enabled` | boolean | `false` | 启用会话检查点（支持恢复） |
| `general.defaultFileEncoding` | string | `"utf-8"` | 新建文件编码（`"utf-8"` 或 `"utf-8-bom"`） |

### output（输出）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output.format` | string | `"text"` | CLI 输出格式：`"text"` 或 `"json"` |

### model（模型）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model.name` | string | — | 会话使用的模型 |
| `model.maxSessionTurns` | number | `-1` | 单次会话最大交互轮数（-1 无限制） |
| `model.generationConfig` | object | — | 高级生成参数（详见用户指南 modelProviders 章节） |
| `model.chatCompression.contextPercentageThreshold` | number | `0.7` | 压缩触发阈值（0~1，0.7 = 70%）。设为 0 禁用压缩 |
| `model.skipNextSpeakerCheck` | boolean | `false` | 跳过下一轮发言者检查 |
| `model.skipLoopDetection` | boolean | `false` | 禁用循环检测（频繁误报时可启用） |
| `model.skipStartupContext` | boolean | `false` | 跳过启动时发送工作区上下文 |
| `model.enableOpenAILogging` | boolean | `false` | 启用 OpenAI API 调用日志 |
| `model.openAILoggingDir` | string | — | 日志目录（支持 `~`、相对路径、绝对路径） |

### ui（界面）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ui.theme` | string | — | 颜色主题 |
| `ui.customThemes` | object | `{}` | 自定义主题定义 |
| `ui.hideTips` | boolean | `false` | 隐藏提示信息 |
| `ui.hideBanner` | boolean | `false` | 隐藏横幅 |
| `ui.hideFooter` | boolean | `false` | 隐藏底部页脚 |
| `ui.showLineNumbers` | boolean | `true` | 代码块显示行号 |
| `ui.showMemoryUsage` | boolean | `false` | 显示内存使用量 |
| `ui.showCitations` | boolean | `true` | 显示引用来源 |
| `ui.hideWindowTitle` | boolean | `false` | 隐藏窗口标题栏 |
| `ui.accessibility.enableLoadingPhrases` | boolean | `true` | 加载状态提示语（无障碍时禁用） |
| `ui.accessibility.screenReader` | boolean | `false` | 屏幕阅读器模式 |
| `ui.customWittyPhrases` | string[] | `[]` | 自定义加载提示语列表 |
| `ui.enableWelcomeBack` | boolean | `true` | 返回项目时显示"欢迎回来"对话框 |

### ide（IDE 集成）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ide.enabled` | boolean | `false` | 启用 IDE 集成模式 |
| `ide.hasSeenNudge` | boolean | `false` | 用户是否已看到 IDE 提示 |

### tools（工具）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tools.approvalMode` | string | `"default"` | 审批模式：`plan`/`default`/`auto-edit`/`yolo` |
| `tools.sandbox` | boolean/string | — | 沙箱环境（`true`/`false`/`"docker"`/`"podman"`） |
| `tools.shell.enableInteractiveShell` | boolean | `false` | 使用 node-pty 交互式 Shell |
| `tools.core` | string[] | — | 内置工具白名单（支持命令级限制） |
| `tools.exclude` | string[] | — | 排除工具黑名单 |
| `tools.allowed` | string[] | — | 跳过确认的工具列表 |
| `tools.discoveryCommand` | string | — | 工具发现命令 |
| `tools.callCommand` | string | — | 自定义工具调用命令 |
| `tools.useRipgrep` | boolean | `true` | 使用 ripgrep 搜索 |
| `tools.useBuiltinRipgrep` | boolean | `true` | 使用内置 ripgrep 二进制（`false` 时用系统 `rg`） |
| `tools.truncateToolOutputThreshold` | number | `25000` | 工具输出截断字符数 |
| `tools.truncateToolOutputLines` | number | `1000` | 截断时保留最大行数 |

> **安全提示**：`tools.exclude` 中对 Shell 的命令级限制基于简单字符串匹配，易被绕过。建议用 `tools.core` 显式声明允许的命令。

### context（上下文）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `context.fileName` | string/string[] | — | 上下文文件名（默认 `QWEN.md`，支持数组） |
| `context.includeDirectories` | string[] | `[]` | 额外包含的目录（最多 5 个） |
| `context.fileFiltering.respectGitIgnore` | boolean | `true` | 搜索时遵守 .gitignore |
| `context.fileFiltering.respectQwenIgnore` | boolean | `true` | 搜索时遵守 .qwenignore |
| `context.importFormat` | string | — | 导入记忆时使用的格式 |
| `context.loadFromIncludeDirectories` | boolean | `false` | `/memory refresh` 是否从所有目录加载 QWEN.md |
| `context.fileFiltering.enableFuzzySearch` | boolean | `true` | 启用模糊搜索（大项目可禁用提升性能） |
| `context.fileFiltering.enableRecursiveFileSearch` | boolean | `true` | @ 补全时递归搜索文件 |

### mcpServers（MCP 服务器）

| 属性 | 类型 | 说明 |
|------|------|------|
| `command` | string | Stdio 启动命令 |
| `args` | string[] | 命令参数 |
| `env` | object | 环境变量 |
| `cwd` | string | 工作目录 |
| `url` | string | SSE 服务器 URL |
| `httpUrl` | string | Streamable HTTP 服务器 URL |
| `headers` | object | 自定义 HTTP 头 |
| `timeout` | number | 超时（毫秒） |
| `trust` | boolean | 信任服务器（跳过确认） |
| `description` | string | 服务器描述 |
| `includeTools` | string[] | 工具白名单 |
| `excludeTools` | string[] | 工具黑名单（优先于 includeTools） |

> 连接优先级：`httpUrl` > `url` > `command`

### mcp（MCP 全局配置）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mcp.serverCommand` | string | — | 启动 MCP 服务器的命令 |
| `mcp.allowed` | string[] | — | 允许连接的 MCP 服务器白名单 |
| `mcp.excluded` | string[] | — | 禁止连接的黑名单（优先于 allowed） |

> 优先级：`httpUrl` > `url` > `command`

### privacy（隐私）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `privacy.usageStatisticsEnabled` | boolean | `true` | 使用统计收集 |

### security（安全）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `security.folderTrust.enabled` | boolean | `false` | 文件夹信任 |
| `security.auth.selectedType` | string | — | 当前认证类型 |
| `security.auth.enforcedType` | string | — | 强制认证类型（企业用） |
| `security.auth.useExternal` | boolean | — | 使用外部认证流程 |

### advanced（高级）

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `advanced.autoConfigureMemory` | boolean | `false` | 自动配置 Node.js 内存限制 |
| `advanced.dnsResolutionOrder` | string | — | DNS 解析顺序 |
| `advanced.excludedEnvVars` | string[] | `["DEBUG","DEBUG_MODE"]` | 从项目上下文排除的环境变量 |
| `advanced.bugCommand` | object | — | `/bug` 命令 URL 覆盖 |
| `advanced.tavilyApiKey` | string | — | Tavily Web 搜索 API Key（旧格式） |

### telemetry（遥测）

| 设置 | 说明 |
|------|------|
| `telemetry.enabled` | 遥测开关 |
| `telemetry.target` | 遥测目标（`local`/`gcp`） |
| `telemetry.otlpEndpoint` | OTLP 端点 |
| `telemetry.otlpProtocol` | OTLP 协议（`grpc`/`http`） |
| `telemetry.logPrompts` | 日志中包含用户提示词 |
| `telemetry.outfile` | 本地遥测输出文件路径 |
| `telemetry.useCollector` | 使用外部 OTLP 收集器 |

## 配置迁移（旧格式→新格式）

v0.3.0 起，旧的否定式命名自动迁移为肯定式：

| 旧设置 | 新设置 |
|--------|--------|
| `disableAutoUpdate` + `disableUpdateNag` | `general.enableAutoUpdate` |
| `disableLoadingPhrases` | `ui.accessibility.enableLoadingPhrases` |
| `disableFuzzySearch` | `context.fileFiltering.enableFuzzySearch` |
| `disableCacheControl` | `model.generationConfig.enableCacheControl` |

> 布尔值自动取反：`disableAutoUpdate: true` → `enableAutoUpdate: false`

## 完整示例

```json
{
  "general": {
    "vimMode": true,
    "preferredEditor": "code"
  },
  "ui": {
    "theme": "GitHub",
    "hideTips": false
  },
  "model": {
    "name": "qwen3-coder-plus",
    "maxSessionTurns": 10,
    "generationConfig": {
      "timeout": 60000,
      "contextWindowSize": 128000,
      "samplingParams": { "temperature": 0.2, "max_tokens": 4096 }
    }
  },
  "tools": {
    "approvalMode": "default",
    "sandbox": "docker"
  },
  "context": {
    "fileName": ["QWEN.md", "CONTEXT.md"],
    "includeDirectories": ["~/shared-context"]
  },
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": { "DATABASE_URL": "$DATABASE_URL" }
    }
  },
  "privacy": {
    "usageStatisticsEnabled": true
  }
}
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `QWEN_TELEMETRY_ENABLED` | 遥测开关（覆盖 settings） |
| `QWEN_SANDBOX` | 沙箱模式 |
| `SEATBELT_PROFILE` | macOS Seatbelt 配置（`permissive-open`/`strict`） |
| `NO_COLOR` | 禁用彩色输出 |
| `TAVILY_API_KEY` | Tavily Web 搜索 API Key |
| `DEBUG` / `DEBUG_MODE` | 启用调试日志 |
| `QWEN_CODE_SYSTEM_DEFAULTS_PATH` | 覆盖系统默认配置文件路径 |
| `QWEN_CODE_SYSTEM_SETTINGS_PATH` | 覆盖系统设置文件路径 |
| `QWEN_CODE_LANG` | 设置 UI 语言 |
| `CLI_TITLE` | 自定义 CLI 标题 |

## 沙箱

沙箱默认禁用，以下场景自动或手动启用：
- `--sandbox` / `-s` 参数
- `QWEN_SANDBOX` 环境变量
- `--yolo` 模式下默认启用沙箱
- 支持 Docker / Podman / macOS Seatbelt / 自定义命令

macOS Seatbelt 配置文件（通过 `SEATBELT_PROFILE` 环境变量切换）：
- `permissive-open`（默认）：仅限制写入
- `strict`：严格模式
- 自定义：`.qwen/sandbox-macos-<profile>.sb`

## 信任文件夹

通过 `security.folderTrust.enabled: true` 启用。未信任的文件夹中，Qwen Code 会：
- 忽略 `.qwen/settings.json` 和 `.env` 文件
- 禁用扩展
- 强制手动工具确认

## 退出码

| 码 | 错误 | 说明 |
|---|------|------|
| 41 | FatalAuthenticationError | 认证失败 |
| 42 | FatalInputError | 无效输入 |
| 44 | FatalSandboxError | 沙箱错误 |
| 52 | FatalConfigError | settings.json 无效 |
| 53 | FatalTurnLimitedError | 达到最大轮数 |
