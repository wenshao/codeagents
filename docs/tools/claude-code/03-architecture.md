# 3. Claude Code 技术架构（Bun 字节码反编译）

> 以下基于 v2.1.81 二进制反编译分析（Bun `@bytecode @bun-cjs` 格式）。入口 `$bunfs/root/src/entrypoints/cli.js`，构建时间 `2026-03-20T21:26:18Z`。

## 系统提示结构（反编译重构）

从二进制 rodata 段提取的系统提示由 8 个模块化章节动态拼装：

| 章节 | 构建函数 | 核心内容 |
|------|----------|----------|
| `# System` | `uo1()` | 运行时行为：工具执行、权限模式、标签系统、上下文压缩说明 |
| `# Doing tasks` | `bo1()` | 软件工程焦点、过度工程警告、安全编码、反向兼容规避 |
| `# Using your tools` | `mo1()` | 工具优先级（Read>cat, Edit>sed）、并行调用、子代理指导 |
| `# Tone and style` | `Uo1()` | 无 emoji、简洁、file_path:line_number 格式、句号结尾 |
| `# Output efficiency` | 内联 | "直奔主题，先给答案后给推理，跳过填充词" |
| `# Executing actions with care` | `xo1()` | 可逆性/爆炸半径框架、风险操作用户确认 |
| `# Committing changes` | 内联 | Git 安全协议：绝不修改 git config、绝不 force push、绝不 amend |
| `# auto memory` | 内联 | 4 种记忆类型（user/feedback/project/reference），MEMORY.md 索引 |

**关键安全指令（从二进制提取的原文）：**

```
"Carefully consider the reversibility and blast radius of actions."

"A user approving an action (like a git push) once does NOT mean that they
approve it in all contexts, so unless actions are authorized in advance in
durable instructions like CLAUDE.md files, always confirm first."

"NEVER update the git config"
"NEVER run destructive git commands (push --force, reset --hard, checkout .,
 restore ., clean -f, branch -D) unless the user explicitly requests"
"CRITICAL: Always create NEW commits rather than amending"
```

**工具优先级指令（反编译提取）：**

| 指令 | 含义 |
|------|------|
| `Read > cat, head, tail, sed` | 读文件用 Read 工具 |
| `Edit > sed, awk` | 编辑用 Edit 工具 |
| `Write > echo, cat heredoc` | 创建文件用 Write 工具 |
| `Glob > find, ls` | 搜索文件用 Glob 工具 |
| `Grep > grep, rg` | 搜索内容用 Grep 工具 |
| `Bash` 仅用于"系统命令和终端操作" | Bash 是最后手段 |

## 内部变量名映射（反编译提取）

| Minified | 原始名 | 类型 |
|----------|--------|------|
| `L8` | Read | 核心工具 |
| `y8` | Edit | 核心工具 |
| `Z9` | Write | 核心工具 |
| `CD` | Bash | 核心工具 |
| `jK` | Glob | 核心工具 |
| `F_` | Grep | 核心工具 |
| `Hf` | Agent | 核心工具 |
| `CP` | WebFetch | 延迟工具 |
| `sE` | WebSearch | 延迟工具 |
| `Qj` | NotebookEdit | 延迟工具 |
| `xw` | Skill | 系统工具 |
| `Tz` | ToolSearch | 系统工具 |
| `f4` | AskUserQuestion | 交互工具 |
| `ZT` / `Mh` | TaskCreate / TaskUpdate | 任务工具 |

## Feature Flags（tengu_ 前缀，反编译提取）

| Flag | 用途 |
|------|------|
| `tengu_defer_all_bn4` | 启用延迟工具加载 |
| `tengu_defer_caveat_m9k` | 延迟工具使用警告 |
| `tengu_turtle_carbon` | ultrathink 模式 |
| `tengu_marble_anvil` | thinking edits（清空思维） |
| `tengu_hawthorn_steeple` | 内容去重 |
| `tengu_hawthorn_window` | 去重窗口大小 |

## 内置输出风格（反编译提取）

| 风格 | 描述 |
|------|------|
| **Explanatory** | 解释实现选择和代码库模式——"提供教育性洞察" |
| **Learning** | 暂停并要求用户编写代码——"通过动手实践学习" |

## 构建常量

```
VERSION: "2.1.81"
BUILD_TIME: "2026-03-20T21:26:18Z"
PACKAGE_URL: "@anthropic-ai/claude-code"
FEEDBACK_CHANNEL: "https://github.com/anthropics/claude-code/issues"
README_URL: "https://code.claude.com/docs/en/overview"
```

## 运行时

| 项目 | 详情 |
|------|------|
| **二进制格式** | ELF 64-bit LSB executable, x86-64, dynamically linked |
| **大小** | ~227 MB（单文件可执行） |
| **运行时** | **Bun v1.2**（非 Node.js），Bun 编译的单文件打包 |
| **UI 框架** | Ink（React for CLI）+ Yoga 布局引擎 |
| **分发方式** | `curl install.sh` 下载二进制到 `~/.local/share/claude/versions/` |

## 内嵌原生模块

| 模块 | 用途 |
|------|------|
| `tree-sitter-bash.node` | Bash AST 解析 |
| `tree-sitter-typescript.node` | TypeScript AST 解析 |
| `tree-sitter-json.node` | JSON 解析 |
| `tree-sitter-yaml.node` | YAML 解析 |
| `tree-sitter-kotlin.node` | Kotlin 解析 |
| `sharp.node` / `image-processor.node` | 图片处理（Sharp 库） |
| `audio-capture.node` | 音频捕获（语音模式） |
| `file-index.node` | 文件索引（代码搜索） |
| `color-diff.node` | 颜色 diff 显示 |
| `yaml.node` | YAML 解析 |
| `resvg.wasm` | SVG 渲染（WebAssembly） |

## API 层

| 端点 | 用途 |
|------|------|
| `api.anthropic.com/v1/messages` | 核心 LLM API（Claude 模型调用） |
| `claude.ai/api/oauth/authorize` | OAuth 认证 |
| `claude.ai/api/claude_code/settings` | 远程设置获取 |
| `claude.ai/api/claude_code/policy_limits` | 策略限制查询 |
| `claude.ai/api/claude_code/team_memory` | 团队记忆（按仓库） |
| `claude.ai/api/ws/speech_to_text/voice_stream` | 语音转文字（WebSocket） |
| `claude.ai/api/claude_cli_feedback` | 反馈提交 |
| `claude.ai/api/claude_code/metrics` | 遥测上报 |

## 遥测系统（tengu）

内置 30+ 个 `tengu_` 前缀的遥测事件，涵盖：
- **代理生命周期**：`tengu_agent_created`、`tengu_agent_tool_selected`、`tengu_agent_tool_completed`
- **API 交互**：`tengu_api`、`tengu_api_error`、`tengu_api_opus_fallback_triggered`、`tengu_api_cache_breakpoints`
- **特性标志**：`tengu_amber_flint`、`tengu_amber_prism`、`tengu_amber_quartz_disabled`（A/B 测试系统）
- **压缩**：`tengu_compact_failed`
- **Skill 变更**：`tengu_dynamic_skills_changed`

## 消息类型（Content Block）

| 类型 | 说明 |
|------|------|
| `Text` | 文本内容 |
| `Thinking` / `RedactedThinking` | 思维过程（可编辑/可屏蔽） |
| `ToolUse` / `ServerToolUse` | 客户端/服务端工具调用 |
| `McpToolUse` / `McpToolResult` | MCP 工具调用与结果 |
| `WebSearchToolResult` / `WebFetchToolResult` | Web 搜索/抓取结果 |
| `CodeExecutionToolResult` / `BashCodeExecutionToolResult` | 代码执行结果 |
| `Compaction` | 压缩摘要 |
| `ContainerUpload` | 容器上传 |

## 内部特性（Codenames）

通过二进制分析发现的内部标识符：

| 代号 | 推测用途 |
|------|----------|
| **tengu** | 遥测系统（telemetry） |
| **penguin** | Penguin 模式（可能与 Linux 沙箱相关） |
| **grove** | 内部功能标识（具体用途未公开） |

### API 端点
Claude Code 与 Anthropic 后端通信使用以下 API 端点：
- **team_memory**：团队共享记忆同步
- **policy_limits**：策略限制查询
- **settings**：远程设置下发

## Chrome 扩展（Beta）

Claude Code 提供 Chrome 浏览器扩展，支持在终端代理中直接操作浏览器标签页。通过 MCP 协议桥接，提供以下工具：

| 工具 | 用途 |
|------|------|
| **tabs_context_mcp** | 获取当前打开的标签页上下文信息 |
| **tabs_create_mcp** | 创建新的浏览器标签页 |
| **read_page** | 读取页面内容（DOM 文本） |
| **read_console_messages** | 读取浏览器控制台消息 |
| **read_network_requests** | 读取网络请求记录 |
| **switch_browser** | 切换到指定标签页 |
| **navigate** | 导航到指定 URL |
| **resize_window** | 调整浏览器窗口大小 |

使用 `/web-setup` 命令配置 Chrome 扩展连接。

## 语音模式

通过 `/voice` 命令启动语音交互模式：

- **Push-to-talk**：按住快捷键说话，松开后自动转录为文字输入
- **语音识别**：基于 speech-to-text API 实现语音转文字
- **适用场景**：手不方便打字时、快速口述需求、代码审查讨论

## Teammates 与远程控制

### Teammates（tmux/iTerm2 协作）
Teammates 允许多个 Claude Code 实例以团队形式协作：

```bash
# 通过 tmux 启动多代理团队
claude --teammates "agent1:实现前端组件" "agent2:编写后端API" "agent3:编写测试"
```

- 每个代理运行在独立的 tmux/iTerm2 窗格中
- 每个代理使用独立的 Git worktree
- 代理之间可以通过消息进行协调
- 适合大规模重构和多模块并行开发

### Remote Control
```bash
# 在终端启用远程控制
/remote-control
```
允许通过 claude.ai/code 浏览器界面远程操控终端中的 Claude Code 实例，实现：
- 浏览器端查看终端代理的实时输出
- 从浏览器发送指令到终端代理
- 多设备协作
