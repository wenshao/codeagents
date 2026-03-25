# 3. Claude Code 技术架构

> 以下基于 v2.1.81 二进制分析。Claude Code 是闭源产品，无公开源码。

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
