# 3. 技术架构（二进制分析）

## 架构

### 包结构

```
@openai/codex (npm)
├── bin/codex.js          # Node.js 启动脚本（~6KB）
├── bin/rg                # ripgrep 入口脚本
└── node_modules/
    └── @openai/codex-linux-x64/   # 平台特定包（示例）
        └── vendor/
            └── x86_64-unknown-linux-musl/
                └── codex/codex    # Rust 原生二进制（~137MB）
```

### 平台二进制包

| 平台包 | 目标三元组 |
|--------|-----------|
| `@openai/codex-linux-x64` | `x86_64-unknown-linux-musl` |
| `@openai/codex-linux-arm64` | `aarch64-unknown-linux-musl` |
| `@openai/codex-darwin-x64` | `x86_64-apple-darwin` |
| `@openai/codex-darwin-arm64` | `aarch64-apple-darwin` |
| `@openai/codex-win32-x64` | `x86_64-pc-windows-msvc` |
| `@openai/codex-win32-arm64` | `aarch64-pc-windows-msvc` |

启动流程：`codex.js` 检测 `process.platform` + `process.arch` -> 解析对应平台包 -> `spawn()` 原生二进制并透传所有参数和信号。

## 沙箱详解

### macOS 沙箱（Seatbelt）

macOS 上使用 `sandbox-exec` 和 seatbelt profiles 实现隔离：

- **网络访问**：完全阻断（deny network*）
- **文件写入**：仅允许当前工作目录（`$PWD`）和临时目录（`$TMPDIR`）
- **文件读取**：允许大部分系统路径（只读）
- **进程创建**：允许（在沙箱内）

### Linux 沙箱

Linux 上提供两种沙箱方案：

| 方案 | 工具 | 特点 |
|------|------|------|
| Bubblewrap（默认） | `bwrap` | 轻量级命名空间隔离，不需要 root 权限 |
| Landlock（遗留） | 内核 LSM | 内核级文件访问控制，作为备选方案 |

### Windows 沙箱（实验性）

Windows 上使用受限令牌（restricted token）实现隔离，目前为实验性支持。

## Codex Cloud（实验性）

`codex cloud` 子命令允许将任务提交到云端执行：

```bash
# 提交云端任务
codex cloud exec "修复所有测试"

# 查看任务状态
codex cloud status <task-id>

# 列出所有云端任务
codex cloud list

# 应用云端任务的结果
codex cloud apply <task-id>

# 查看云端任务的差异
codex cloud diff <task-id>
```

Cloud 模式支持 best-of-N 多次尝试，选择最佳结果。此功能目前为实验性。

## App-Server 协议（IDE 集成）

`codex app-server` 启动 JSON-RPC 服务器，用于 VS Code 等 IDE 集成：

```bash
codex app-server
```

主要 JSON-RPC 方法：

| 方法 | 功能 |
|------|------|
| `thread/start` | 启动新对话线程 |
| `turn/start` | 开始新一轮对话 |
| `fs/readFile` | 读取文件内容 |
| `review/start` | 启动代码审查 |

## 多模态输入

Codex CLI 支持图片/截图输入，可以用于 UI 分析、bug 复现等场景。

```bash
# 交互式会话中粘贴图片（拖拽或剪贴板粘贴）
codex
# 然后在对话中粘贴截图

# 通过管道传入
cat error.log | codex "分析这个错误日志"
```

支持的格式：PNG、JPEG、GIF、WebP

## 与其他 Agent 对比

| 特性 | Codex CLI | Claude Code | Qwen Code | Aider | Gemini CLI |
|------|----------|-------------|-----------|-------|------------|
| 开源 | Apache-2.0 | 闭源 | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| 默认模型 | o4-mini | Claude Sonnet | Qwen3 | 多模型 | Gemini 2.5 Pro |
| 多模型支持 | OpenAI + OSS | 仅 Claude | 多模型 | 多模型 | 仅 Gemini |
| 沙箱 | 默认启用 | 可选 | 可选 | 无 | 可选 |
| 网络隔离 | 默认 | 可选 | 无 | 无 | 无 |
| MCP 支持 | 客户端+服务器 | 客户端 | 有 | 无 | 有 |
| Git 集成 | review 子命令 | 有 | 无 | 自动提交 | 无 |
| 多模态 | 图片 | 图片 | 图片 | 无 | 图片 |
| 交互命令 | 20+ 斜杠命令 | 斜杠命令 | 斜杠命令 | 斜杠命令 | 斜杠命令 |
| 会话持久化 | resume/fork | 有 | 无 | 无 | resume |
| 项目指令 | CODEX.md/AGENTS.md | CLAUDE.md | - | .aider* | GEMINI.md |
| 技术栈 | Rust + Node.js | Rust/TypeScript | TypeScript | Python | TypeScript/Ink |
| Cloud 执行 | 实验性 | 无 | 无 | 无 | 无 |
| 定价模式 | API 按量 | API 按量/订阅 | API 按量 | 免费+API | API 按量 |

## Feature Flags 完整清单（`codex features list` 输出）

> 证据：`codex features list` 实时输出，已记录在 [EVIDENCE.md](./EVIDENCE.md)

| Flag | 状态 | 默认 | 说明 |
|------|------|------|------|
| `shell_tool` | stable | true | Shell 工具 |
| `shell_snapshot` | stable | true | Shell 状态快照 |
| `fast_mode` | stable | true | 快速模式 |
| `personality` | stable | true | 人格自定义 |
| `multi_agent` | stable | true | 多代理支持 |
| `skill_mcp_dependency_install` | stable | true | Skill MCP 依赖自动安装 |
| `unified_exec` | stable | true | 统一执行模式 |
| `enable_request_compression` | stable | true | 请求压缩 |
| `undo` | stable | false | 撤销功能 |
| `use_legacy_landlock` | stable | false | 旧版 Landlock 沙箱 |
| `guardian_approval` | experimental | false | Guardian 审批系统（安全审查子代理） |
| `js_repl` | experimental | false | JavaScript REPL |
| `prevent_idle_sleep` | experimental | false | 防止空闲休眠 |
| `apps` | experimental | false | ChatGPT Apps/Connectors |
| `tui_app_server` | experimental | false | App-Server 驱动的 TUI |
| `codex_hooks` | under dev | false | Hook 系统 |
| `voice_transcription` | under dev | false | 语音转录 |
| `realtime_conversation` | under dev | false | 实时对话 |
| `memories` | under dev | false | 记忆系统 |
| `plugins` | under dev | false | 插件系统 |
| `enable_fanout` | under dev | false | 扇出并行 |
| `code_mode` | under dev | false | 代码模式 |
| `image_generation` | under dev | false | 图片生成 |
| `collaboration_modes` | removed | true | 协作模式（已移除） |
| `search_tool` | removed | false | 搜索工具（已移除） |
| `web_search_cached` | deprecated | false | 缓存 Web 搜索（已弃用） |

共 52 个 flag，其中 10 个 stable、4 个 experimental、18 个 under development、8 个 removed、2 个 deprecated。

## `codex review` 深度（`codex review --help` 提取）

```bash
codex review [OPTIONS] [PROMPT]

# 审查未提交的更改
codex review --uncommitted

# 审查相对于 main 分支的更改
codex review --base main

# 审查特定 commit 引入的更改
codex review --commit abc123

# 自定义审查指令
codex review "重点关注安全性"

# 从 stdin 读取指令
echo "check error handling" | codex review -

# 附加标题
codex review --title "Feature: Auth Module" --base main
```

**参数（`codex review --help` 确认）：**

| 参数 | 说明 |
|------|------|
| `[PROMPT]` | 自定义审查指令，`-` 表示从 stdin 读取 |
| `--uncommitted` | 审查 staged + unstaged + untracked 更改 |
| `--base <BRANCH>` | 审查相对于指定分支的更改 |
| `--commit <SHA>` | 审查指定 commit 引入的更改 |
| `--title <TITLE>` | 审查摘要中显示的可选标题 |

## `codex cloud` 深度（实验性）

```bash
codex cloud exec "fix all failing tests"   # 提交任务到云端
codex cloud status <TASK_ID>               # 查看任务状态
codex cloud list                           # 列出所有云端任务
codex cloud apply <TASK_ID>                # 将云端 diff 应用到本地
codex cloud diff <TASK_ID>                 # 查看云端任务的 unified diff
```

**架构：** 每个 Cloud 任务在 Anthropic/OpenAI 云端创建隔离环境，执行 best-of-N 尝试（N=1-4），完成后可将 diff 拉回本地应用。

## MCP 双向支持

**客户端模式（`codex mcp` 子命令）：**
```bash
codex mcp list                 # 列出已配置的 MCP 服务器
codex mcp add <name> <command> # 添加 MCP 服务器
codex mcp remove <name>        # 移除 MCP 服务器
codex mcp login <name>         # OAuth 认证（HTTP MCP）
codex mcp logout <name>        # 移除 OAuth 凭据
codex mcp get <name>           # 查看服务器详情
```

**服务器模式（`codex mcp-server`）：**
```bash
codex mcp-server               # 将 Codex 作为 MCP 服务器启动（stdio 传输）
```
支持 MCP 协议版本 `2024-11-05`，暴露 tools、resources、prompts 能力。
