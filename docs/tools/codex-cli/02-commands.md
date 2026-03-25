# 2. Codex CLI 命令、工具与配置详解（v0.116.0 二进制分析）

本章基于 Codex CLI v0.116.0 二进制文件的逆向分析与字符串提取，记录所有 CLI 子命令、TUI 斜杠命令、审批模式、代理工具、MCP 支持、App-Server 协议、Feature Flags 及完整配置体系。所有计数与枚举均可通过 `strings codex | grep` 复现。

---

## CLI 子命令（15 个）

从二进制入口点解析，Codex CLI 共注册 15 个子命令。

### 子命令总表

| 子命令 | 别名 | 说明 | 子命令参数 |
|--------|------|------|-----------|
| `exec` | `e` | 执行任务（默认子命令，无需显式写出） | `<prompt>` |
| `review` | - | 代码审查，对 diff 生成结构化反馈 | `--uncommitted`, `--base <branch>`, `--commit <sha>` |
| `login` | - | 管理登录（`login status` 为子操作，非别名） | `status` |
| `logout` | - | 登出当前账户，清除本地令牌 | - |
| `mcp` | - | MCP 客户端管理（6 个子操作） | `list`, `get`, `add`, `remove`, `login`, `logout` |
| `mcp-server` | - | 以 MCP 服务器模式运行（stdio 传输） | - |
| `app-server` | - | IDE 集成的 JSON-RPC 服务器（2 个生成子操作） | `generate-ts`, `generate-json-schema` |
| `completion` | - | 生成 shell 自动补全脚本 | `bash`, `zsh`, `fish` |
| `sandbox` | - | 沙箱测试与调试（3 个平台子操作） | `macos`, `linux`, `windows` |
| `debug` | - | 调试信息输出 | `app-server` |
| `apply` | `a` | 将 Codex agent 产生的最新 diff 通过 `git apply` 应用到本地工作树 | `<task-id>` |
| `resume` | - | 恢复之前的会话 | `<session-id>` |
| `fork` | - | 从已有会话分叉出新会话 | `<session-id>` |
| `cloud` | - | 云端任务管理（实验性，5 个子操作） | `exec`, `status`, `list`, `apply`, `diff` |
| `features` | - | 功能标志管理（3 个子操作） | `list`, `enable`, `disable` |

### exec（默认子命令）

不带子命令直接运行 `codex` 等价于 `codex exec`，进入交互式 TUI；带引号参数则直接执行单次任务。

```bash
# 交互式会话（等价于 codex exec）
codex

# 单次任务执行
codex "重构这个函数，添加类型注解"
codex exec "修复 lint 错误"
codex e "编写单元测试"

# 从标准输入读取上下文
cat error.log | codex "分析这段日志并修复根因"
```

### review（代码审查）

`review` 子命令对 git diff 执行结构化审查，输出问题列表与改进建议。支持 `--title <TITLE>` 可选参数在审查摘要中显示 commit 标题。

```bash
# 审查工作区未提交的更改
codex review --uncommitted

# 审查当前分支与 main 的差异
codex review --base main

# 审查特定 commit
codex review --commit abc1234

# 带标题的审查
codex review --commit abc1234 --title "Fix race condition"

# 管道输入自定义 diff
git diff HEAD~3 | codex review
```

### login / logout

```bash
codex login          # 管理登录（交互式 OAuth 流程）
codex login status   # 查看当前认证状态（子操作）
codex logout         # 登出，清除本地认证凭证
```

### mcp（6 个子操作）

```bash
codex mcp list                          # 列出已配置的 MCP 服务器
codex mcp get <server-name>             # 查看特定服务器详情与工具列表
codex mcp add <server-name> <cmd> [args...]  # 添加 MCP 服务器
codex mcp remove <server-name>          # 移除 MCP 服务器
codex mcp login <server-name>           # 对需要认证的 MCP 服务器登录
codex mcp logout <server-name>          # 登出 MCP 服务器
```

### app-server（IDE 集成）

App-Server 是 Codex CLI 为 IDE 插件提供的 JSON-RPC 服务器，支持 stdio（默认）和 WebSocket（`ws://`）两种传输方式。支持 `--session-source` 标记来源（默认 `vscode`，也支持 `cli`、`exec`、`mcp` 等）。

```bash
codex app-server                     # 启动 JSON-RPC 服务器（stdio）
codex app-server --listen ws://0.0.0.0:8080  # WebSocket 传输
codex app-server generate-ts         # 生成 TypeScript 类型定义
codex app-server generate-json-schema  # 生成 JSON Schema 定义
codex debug app-server               # 调试模式启动 app-server
```

### sandbox（沙箱测试）

```bash
codex sandbox macos     # 测试 macOS Seatbelt 沙箱配置（别名：seatbelt）
codex sandbox linux     # 测试 Linux 沙箱配置（bubblewrap 默认，别名：landlock）
codex sandbox windows   # 测试 Windows 沙箱配置（restricted token）
```

### cloud（云端任务，实验性）

```bash
codex cloud exec "大规模重构任务"    # 在云端执行任务
codex cloud status <task-id>        # 查看云端任务状态
codex cloud list                    # 列出所有云端任务
codex cloud apply <task-id>         # 将云端任务结果应用到本地
codex cloud diff <task-id>          # 查看云端任务产生的 diff
```

### features（功能标志管理）

```bash
codex features list                 # 列出所有功能标志及其状态
codex features enable <flag-name>   # 启用指定功能标志
codex features disable <flag-name>  # 禁用指定功能标志
```

### apply / resume / fork

```bash
codex apply <task-id>               # 将 agent 产生的最新 diff 通过 git apply 应用到本地
codex a <task-id>                   # 同上（别名）

codex resume <session-uuid>         # 恢复指定会话（--last 恢复最近会话）
codex fork <session-uuid>           # 从指定会话分叉出新会话（--last 分叉最近会话）
```

### completion

```bash
codex completion bash >> ~/.bashrc
codex completion zsh >> ~/.zshrc
codex completion fish >> ~/.config/fish/completions/codex.fish
```

### 完整参数参考

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--model` | `-m` | 指定使用的模型 | `gpt-5.1-codex` |
| `--ask-for-approval` | `-a` | 审批模式（4 种）：untrusted/on-request/on-failure/never | `untrusted` |
| `--sandbox` | `-s` | 沙箱模式：`read-only` / `workspace-write` / `danger-full-access` | - |
| `--full-auto` | - | 便捷别名 = `--ask-for-approval on-request --sandbox workspace-write` | - |
| `--config` | `-c` | 覆盖配置值（`key=value` 格式，支持点路径如 `foo.bar.baz`） | - |
| `--profile` | `-p` | 使用 config.toml 中定义的配置 profile | - |
| `--oss` | - | 使用本地 OSS 模型提供者（验证 LM Studio 或 Ollama 运行中） | - |
| `--local-provider` | - | 指定本地模型提供者（`lmstudio` / `ollama`） | - |
| `--image` | `-i` | 附加图片到初始提示（可重复使用） | - |
| `--enable` | - | 启用功能标志（可重复，等价于 `-c features.<name>=true`） | - |
| `--disable` | - | 禁用功能标志（可重复，等价于 `-c features.<name>=false`） | - |
| `--search` | - | 启用实时网络搜索（web_search 工具） | - |
| `--cd` | `-C` | 指定代理工作根目录 | 当前目录 |
| `--add-dir` | - | 添加额外可写目录（配合主工作区使用） | - |
| `--remote` | - | 连接远程 app-server WebSocket 端点 | - |
| `--no-alt-screen` | - | 禁用备用屏幕模式（内联 TUI，保留终端滚动历史） | - |
| `--dangerously-bypass-approvals-and-sandbox` | - | 绕过所有审批和沙箱（极危险，仅限外部沙箱环境） | - |
| `--help` | `-h` | 显示帮助信息 | - |
| `--version` | `-V` | 显示版本号 | - |

> 验证方式：`codex --help` 确认 `--version` 简写为 `-V`（大写）。`--config` 是覆盖配置值而非指定配置文件路径。`--reasoning-effort` 不是独立 CLI 参数，需通过 `-c model_reasoning_effort=high` 设置。`--yolo` 别名未在 `codex --help` 中出现。

---

## 审批模式（4 种）

> 验证方式：`codex --help` 输出确认仅接受 untrusted/on-request/on-failure/never 四种值。`codex -a granular` 返回 "error: invalid value 'granular'"。`granular` 模式不存在，`suggest` 和 `full-auto` 是别名而非独立模式。

| 模式 | 说明 |
|------|------|
| `untrusted` | **默认模式**。仅执行受信任的命令，其他操作需用户确认 |
| `on-request` | 模型自行决定何时询问用户。适合半自动工作流 |
| `on-failure` | **已弃用**。仅在操作失败时询问用户 |
| `never` | 从不询问用户审批，执行失败时将错误反馈给模型继续尝试 |

### 模式选择逻辑

```
codex                              → untrusted（默认）
codex -a on-request                → 模型决定何时询问
codex -a never                     → 从不询问，自动执行
codex --full-auto                  → on-request + workspace-write 沙箱（便捷别名）
codex --dangerously-bypass-...     → 绕过一切（仅限测试环境）
```

### 沙箱与审批模式的交互

| 审批模式 | 沙箱 = read-only | 沙箱 = workspace-write | 沙箱 = danger-full-access |
|----------|-----------------|----------------------|--------------------------|
| `untrusted` | 每次询问 | 每次询问 | 每次询问 |
| `on-request` | 模型决定 | 模型决定（推荐组合） | 模型决定 |
| `never` | 自动执行 | 自动执行 | 自动执行 |

---

## TUI 斜杠命令（28 个，官方文档验证）

> 来源：[官方斜杠命令文档](https://developers.openai.com/codex/cli/slash-commands)，28 个命令。
> 注：Rust 编译的二进制中命令名以 enum 形式存储，无法通过 `strings` 直接提取，以官方文档为权威来源。

### 会话控制

| 命令 | 功能 | 验证来源 |
|------|------|----------|
| `/compact` | 压缩对话历史，释放上下文窗口空间 | 官方文档 + 二进制提示文本 |
| `/fork` | 从当前对话状态分叉出新会话 | 官方文档 + CLI 子命令 |
| `/resume` | 恢复之前的会话 | 官方文档 + CLI 子命令 |
| `/new` | 开始新的会话 | 官方文档 |
| `/status` | 显示会话状态（模型、token 用量、审批模式等） | 官方文档 |
| `/statusline` | 切换底部状态栏的显示/隐藏 | 官方文档 |
| `/copy` | 复制最近的代理回复到剪贴板 | 官方文档 |
| `/exit` | 退出当前会话 | 官方文档 |
| `/quit` | 退出当前会话（同 /exit） | 官方文档 |
| `/clear` | 清除当前屏幕/对话显示 | 官方文档 |

### 模型与配置

| 命令 | 功能 | 验证来源 |
|------|------|----------|
| `/model` | 切换或查看当前使用的模型 | 官方文档 + 二进制（16 refs） |
| `/permissions` | 查看或修改当前权限设置 | 官方文档 |
| `/personality` | 查看或设置代理人格 | 官方文档 |
| `/fast` | 切换快速模式 | 官方文档 |
| `/debug-config` | 显示当前调试配置信息 | 官方文档 |

### 工具与扩展

| 命令 | 功能 | 验证来源 |
|------|------|----------|
| `/agent` | 与内置代理交互 | 官方文档 |
| `/mcp` | 管理 MCP 服务器连接 | 官方文档 + 二进制（3 refs） |
| `/apps` | 管理 ChatGPT Apps（Connectors） | 官方文档 |
| `/experimental` | 查看与切换实验性功能 | 官方文档 + 二进制（8 refs） |

### 工作流

| 命令 | 功能 | 验证来源 |
|------|------|----------|
| `/plan` | 让代理制定计划而不执行 | 官方文档 + 二进制（4 refs） |
| `/review` | 在交互会话中启动代码审查 | 官方文档 + 二进制（3 refs）+ CLI 子命令 |
| `/feedback` | 向代理提供反馈 | 官方文档 |
| `/diff` | 显示当前会话产生的文件修改差异 | 官方文档 |
| `/mention` | 引用文件或符号，添加到上下文 | 官方文档 + 二进制（1 ref） |
| `/ps` | 显示当前后台进程状态 | 官方文档 |

### 系统与认证

| 命令 | 功能 | 验证来源 |
|------|------|----------|
| `/logout` | 登出当前账户 | 官方文档 |
| `/init` | 初始化项目配置（生成 CODEX.md 等） | 官方文档 + 二进制（1 ref） |
| `/sandbox-add-read-dir` | 将目录添加到沙箱只读访问列表 | 官方文档 |

> **第四轮验证修正记录：** 移除 13 个未经官方文档或二进制双重验证的命令（/help, /history, /memories, /prompts, /realtime, /rename, /session, /settings, /share, /shell, /skills, /tasks, /tools）。这些命令在二进制中均 0 匹配，官方文档中也未列出。补充 /agent 和 /resume（官方文档确认）。

---

## 代理工具系统

### 系统身份

从二进制中提取的系统提示片段确认代理身份：

> **"You are Codex, a coding agent based on GPT-5."**

### 核心工具列表

| 工具名 | 功能 | 需要审批 |
|--------|------|---------|
| `LocalShellCall` | 在沙箱中执行 shell 命令 | 取决于审批模式 |
| `ApplyPatch` | 使用 Codex 专有 diff 格式精确修改文件 | 取决于审批模式 |
| `WebSearchCall` | 网络搜索（Bing/Google 后端） | 否 |
| `McpToolCall` | 调用 MCP 服务器提供的外部工具 | 取决于工具声明 |
| `ImageGenerationCall` | 调用 DALL-E 生成图片 | 否 |
| `GhostSnapshot` | 创建环境快照/检查点 | 否 |
| `Compaction` | 主动压缩上下文，保持对话窗口可控 | 否 |
| `DynamicToolCall` | 动态注册与调用运行时工具 | 取决于工具 |
| `ToolSearchCall` | 在大型工具集中搜索可用工具 | 否 |

### CommandAction 子操作

`LocalShellCall` 内部支持以下轻量级子操作，无需启动完整 shell：

| 操作 | 功能 | 说明 |
|------|------|------|
| `Read` | 读取文件内容 | 支持行范围读取 |
| `Search` | 基于 ripgrep 的代码搜索 | 正则 + glob 过滤 |
| `ListFiles` | 列出目录文件 | 递归/非递归 |

### ApplyPatch 格式规范

Codex 使用自有的补丁格式（非标准 unified diff），格式标记以三个 `@` 符号区分：

```
*** Begin Patch
*** Add File: src/new-module.ts
+// 新文件的完整内容
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

支持三种操作：`Add File`（新建）、`Update File`（修改）、`Delete File`（删除）。

---

## MCP 支持

### 作为 MCP 客户端

Codex CLI 内置 MCP 客户端，可连接任意 MCP 服务器扩展工具能力。

**CLI 管理：**

```bash
codex mcp list                                    # 列出所有已配置服务器
codex mcp get <name>                              # 查看服务器详情与工具列表
codex mcp add <name> <command> [args...]           # 添加服务器
codex mcp remove <name>                            # 移除服务器
codex mcp login <name>                             # 服务器认证
codex mcp logout <name>                            # 服务器登出
```

**配置文件声明（config.toml）：**

```toml
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "ghp_xxx" }
```

代理通过 `McpToolCall` 工具调用已配置的 MCP 服务器。MCP 工具支持 `tool_call_mcp_elicitation` feature flag 启用交互式参数征询。

### 作为 MCP 服务器

```bash
codex mcp-server    # 以 stdio MCP 服务器模式运行
```

暴露 Codex 的所有代理能力供其他 MCP 客户端（如 Claude Code、Cursor）调用。

---

## App-Server 协议方法（90+）

App-Server 使用 JSON-RPC 2.0 over stdio（也支持 `ws://` WebSocket 传输），为 IDE 插件（VS Code 扩展等）提供完整的 Codex 能力接口。从二进制提取的命名空间与方法如下：

| 命名空间 | 实际方法（二进制提取） | 说明 |
|----------|---------|------|
| `account/*` | `account/read`, `account/updated`, `account/login/start`, `account/login/completed`, `account/login/cancel`, `account/logout` | 账户认证与登录流程 |
| `app/*` | `app/list`, `app/list/updated` | 应用列表管理 |
| `command/*` | `command/exec`, `command/exec/resize`, `command/exec/terminate`, `command/exec/write` | 命令执行、终端交互与生命周期 |
| `completion/*` | `completion/complete` | 补全请求 |
| `config/*` | `config/read`, `config/value/write`, `config/batchWrite`, `config/mcpServer/*` | 配置读写与批量操作 |
| `elicitation/*` | `elicitation/create` | 交互式参数征询创建 |
| `feedback/*` | `feedback/upload` | 用户反馈上传 |
| `fs/*` | `fs/copy`, `fs/remove`, `fs/readDirectory` | 文件系统操作 |
| `hook/*` | `hook/started`, `hook/completed` | 钩子生命周期事件 |
| `item/*` | `item/started`, `item/completed`, `item/plan/delta`, `item/tool/call` | 对话项事件与工具调用 |
| `model/*` | `model/list`, `model/rerouted` | 模型列表与重路由 |
| `notifications/*` | `notifications/initialized`, `notifications/message`, `notifications/cancelled`, `notifications/progress`, `notifications/elicitation/complete`, `notifications/resources/updated`, `notifications/tools/list_changed` | 通知推送与事件 |
| `turn/*` | `turn/start`, `turn/started`, `turn/completed`, `turn/interrupt`, `turn/steer`, `turn/diff/updated`, `turn/plan/updated` | 对话回合管理 |
| `thread/*` | `thread/start`, `thread/started`, `thread/list`, `thread/read`, `thread/resume`, `thread/fork`, `thread/rollback`, `thread/archive`, `thread/unarchive`, `thread/compact/start`, `thread/compacted`, `thread/name/set`, `thread/name/updated`, `thread/metadata/update`, `thread/status/changed`, `thread/realtime/*`, `thread/unsubscribe`, `thread/loaded/list` | 会话线程完整管理 |
| `review/*` | `review/start` | 代码审查 |
| `tasks/*` | `tasks/get`, `tasks/list`, `tasks/cancel`, `tasks/result` | 任务管理 |
| `fuzzyFileSearch/*` | `fuzzyFileSearch/search` (session start/stop/update) | 模糊文件搜索 |
| `mcpServer/*` | `mcpServer/reload`, `mcpServer/oauth/login` | MCP 服务器管理 |
| `skills/*` | `skills/list`, `skills/changed`, `skills/config/write` | 技能管理 |
| `plugin/*` | `plugin/install`, `plugin/list`, `plugin/read`, `plugin/uninstall` | 插件安装与管理 |
| `resources/*` | `resources/list`, `resources/read`, `resources/subscribe`, `resources/unsubscribe`, `resources/templates/list` | MCP 资源管理 |
| `roots/*` | `roots/list` | 根目录列表 |
| `tools/*` | `tools/list`, `tools/call` | 工具列表与调用 |
| `prompts/*` | `prompts/list`, `prompts/get` | 提示词管理 |
| `openai/*` | `openai/skills` | OpenAI 技能接口 |

生成类型定义：

```bash
codex app-server generate-ts > codex-protocol.ts
codex app-server generate-json-schema > codex-protocol.json
```

---

## Feature Flags（52 个，`codex features list` 提取）

`codex features list` 输出全部 52 个功能标志，含 stable、experimental、under development、deprecated、removed 五种状态。以下列出关键标志：

### Stable（默认开启）

| 标志名 | 说明 | 默认 |
|--------|------|------|
| `fast_mode` | 快速模式，跳过部分确认步骤加速执行 | 开启 |
| `multi_agent` | 多代理协作，主代理可分派子任务给子代理 | 开启 |
| `personality` | 代理人格自定义（语气、风格等） | 开启 |
| `shell_snapshot` | Shell 快照，捕获终端状态用于上下文恢复 | 开启 |
| `shell_tool` | Shell 工具（内置 shell 执行能力） | 开启 |
| `enable_request_compression` | 启用请求压缩 | 开启 |
| `skill_mcp_dependency_install` | 技能 MCP 依赖自动安装 | 开启 |
| `unified_exec` | 统一执行模式 | 开启 |

### Stable（默认关闭）

| 标志名 | 说明 | 默认 |
|--------|------|------|
| `undo` | 撤销操作支持 | 关闭 |
| `use_legacy_landlock` | 使用旧版 Landlock 沙箱 | 关闭 |

### Experimental

| 标志名 | 说明 | 默认 |
|--------|------|------|
| `guardian_approval` | Guardian 子代理安全审批，自动审查高风险操作（消耗更多 token） | 关闭 |
| `apps` | ChatGPT Apps（Connectors）集成，通过 `$` 引用 | 关闭 |
| `js_repl` | 持久 Node.js REPL，用于交互式 JavaScript 执行（需 Node >= v22.22.0） | 关闭 |
| `tui_app_server` | 使用 app-server 后端的 TUI 实现 | 关闭 |
| `prevent_idle_sleep` | 运行时阻止系统休眠 | 关闭 |

### Under Development（关键）

| 标志名 | 说明 | 默认 |
|--------|------|------|
| `codex_hooks` | 钩子系统，在特定事件点执行自定义逻辑 | 关闭 |
| `voice_transcription` | 语音转录输入，通过麦克风输入指令 | 关闭 |
| `realtime_conversation` | 实时对话模式（语音双向通信） | 关闭 |
| `tool_call_mcp_elicitation` | MCP 工具调用时支持交互式参数征询 | 关闭 |
| `memories` | 代理记忆系统 | 关闭 |
| `plugins` | 插件系统 | 关闭 |
| `image_generation` | 图片生成功能 | 关闭 |
| `code_mode` | 代码模式 | 关闭 |
| `apply_patch_freeform` | 自由格式 ApplyPatch | 关闭 |
| `enable_fanout` | 子任务扇出 | 关闭 |
| `child_agents_md` | 子代理 AGENTS.md 支持 | 关闭 |
| `request_permissions_tool` | 权限请求工具 | 关闭 |

### Removed / Deprecated

| 标志名 | 状态 |
|--------|------|
| `collaboration_modes` | removed（注意：是 modes 复数形式） |
| `search_tool` | removed |
| `remote_models` | removed |
| `web_search_cached` | deprecated |
| `web_search_request` | deprecated |

> 验证方式：`codex features list` 输出 52 个标志。之前文档的 `guardian_subagent` 和 `ghost_snapshot` 不是独立 feature flag（`ghost_snapshot` 是配置键）。`collaboration_mode` 实际名称为 `collaboration_modes`。`multi_agent`、`fast_mode`、`shell_snapshot`、`personality` 默认状态均为开启，非关闭。

管理命令：

```bash
codex features list                          # 查看所有标志
codex features enable realtime_conversation  # 启用指定标志
codex features disable multi_agent           # 禁用指定标志
```

---

## 配置系统

### 配置文件位置与格式

配置文件为 TOML 格式，存储在 `~/.codex/config.toml`。

### 关键配置键

| 配置键 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `approval_mode` | string | 审批模式（untrusted/on-request/on-failure/never） | `untrusted` |
| `sandbox` | string | 沙箱级别（read-only/workspace-write/danger-full-access） | `read-only` |
| `model` | string | 默认模型 | `gpt-5.1-codex` |
| `model_reasoning_effort` | string | 模型推理努力程度（low/medium/high） | `medium` |
| `plan_mode_reasoning_effort` | string | Plan 模式下的推理努力程度 | `high` |
| `personality` | string | 代理人格描述文本 | 空 |
| `compact_prompt` | string | 上下文压缩时使用的自定义提示 | 空 |
| `shell_environment_policy` | string | Shell 环境变量策略 | 默认策略 |
| `mcp_servers` | table | MCP 服务器配置表（见 MCP 章节） | 空 |
| `model_providers` | table | 自定义模型提供者配置 | 空 |
| `agents` | table | 多代理配置（需启用 multi_agent flag） | 空 |
| `skills` | table | 技能配置 | 空 |
| `plugins` | table | 插件配置 | 空 |
| `review_model` | string | 代码审查专用模型 | 空（使用默认模型） |
| `model_context_window` | number | 模型上下文窗口大小 | 模型默认值 |
| `model_auto_compact_token_limit` | number | 自动压缩触发 token 阈值 | 模型默认值 |
| `developer_instructions` | string | 开发者指令（系统级） | 空 |
| `model_instructions_file` | string | 模型指令文件路径 | 空 |
| `profile` | string | 使用的配置 profile 名称 | 空 |
| `history` | table | 会话历史配置 | 默认值 |
| `analytics` | table | 分析与遥测配置 | 默认值 |
| `ghost_snapshot` | table | Ghost 快照配置 | 默认值 |
| `tui` | table | TUI 显示配置（动画、提示、状态栏、主题等） | 默认值 |
| `project_root_markers` | array | 项目根目录标记文件列表 | 默认值 |
| `tool_output_token_limit` | number | 工具输出 token 上限 | 默认值 |

### 完整配置示例

```toml
# ~/.codex/config.toml
model = "gpt-5.1-codex"
approval_mode = "untrusted"
sandbox = "workspace-write"
model_reasoning_effort = "medium"
plan_mode_reasoning_effort = "high"
personality = "简洁专业，优先使用中文回复"
compact_prompt = "保留关键上下文，压缩冗余对话"
shell_environment_policy = "inherit"

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

[profiles.personal]
model = "o3"
approval_mode = "untrusted"
```

### 指令文件层级

Codex CLI 按以下顺序加载指令，后加载的可覆盖先加载的：

| 优先级 | 文件 | 作用域 | 说明 |
|--------|------|--------|------|
| 1（最低） | `~/.codex/instructions.md` | 全局（用户级） | 所有项目共享的指令 |
| 2 | `CODEX.md` | 项目级 | 项目根目录的指令文件 |
| 3 | `AGENTS.md` | 项目级 | 代理行为指令（替代名称，与 CODEX.md 共存） |
| 4（最高） | `SKILL.md` | 技能级 | 定义特定技能的指令与约束 |

<!-- --no-project-doc 和 --project-doc 未在 codex --help 输出中确认，暂不列入文档。 -->

### 环境变量

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥（必需，除非使用 OAuth 登录） | `sk-proj-...` |
| `OPENAI_BASE_URL` | 自定义 API 端点 | `https://api.openai.com/v1` |
| `OPENAI_ORG_ID` | OpenAI 组织 ID | `org-...` |
| `CODEX_HOME` | Codex 配置目录（覆盖默认 `~/.codex`） | `/custom/path/.codex` |

---

## 会话系统

每个 Codex 会话拥有唯一 UUID 标识，会话数据持久化存储在 `~/.codex/sessions/` 目录下。

### 会话生命周期

```
创建 → 活跃 → 暂停/退出 → resume 恢复 / fork 分叉
```

### 操作方式

```bash
# CLI 方式
codex resume <session-uuid>         # 恢复指定会话
codex fork <session-uuid>           # 从指定会话分叉

# TUI 斜杠命令
/session                            # 查看当前会话信息
/fork                               # 从当前状态分叉
/rename                             # 重命名会话
/share                              # 分享会话
```

会话数据包含完整对话历史、工具调用记录、文件修改记录，允许跨终端窗口、跨时间恢复工作上下文。

---

## 技能系统

### 概念

技能（Skills）是可复用的指令包，通过 `SKILL.md` 文件定义特定能力。每个技能可声明自己的 MCP 依赖。

### 使用方式

```bash
# TUI 中调用
/skills                          # 列出所有可用技能

# 配置文件声明（config.toml）
[skills.deploy]
path = "./skills/deploy"
```

### SKILL.md 格式

```markdown
# 技能名称

## 指令
描述此技能的行为规范...

## MCP 依赖
- server-name: 所需的 MCP 服务器
```

---

## 代码审查

### codex review 子命令

```bash
codex review --uncommitted              # 审查未提交的更改
codex review --base main                # 审查与 main 分支的差异
codex review --commit abc1234           # 审查特定 commit
```

### /review 交互命令

在交互式会话中输入 `/review` 启动代码审查模式。代理会：

1. 收集当前 git diff
2. 分析代码变更的正确性、安全性、性能
3. 输出结构化审查意见与改进建议

### /feedback 反馈命令

`/feedback` 命令允许用户对代理的审查结果或代码修改提供反馈，代理据此调整后续行为。
