# Hermes Agent — 工具与渠道清单

## 工具（28+ 个内置工具）

源码路径：`/root/git/hermes-agent/tools/`

### Memory & Skill 学习闭环

| 工具 | 源文件 | 功能 |
|---|---|---|
| **memory** | `memory_tool.py` | 持久记忆管理（MEMORY.md + USER.md），冻结快照模式 |
| **skill_manage** | `skill_manager_tool.py` | 自主创建/编辑/patch skill，支持 `~/.hermes/skills/<name>/` 目录结构 |
| **session_search** | `session_search_tool.py` | 跨会话 FTS5 搜索 + Gemini Flash 摘要 |
| **skills_hub** | `skills_hub.py` | 与 agentskills.io 集成（社区 skill 市场） |
| **skills_sync** | `skills_sync.py` | Skill 同步（本地 ↔ 云） |
| **skills_guard** | `skills_guard.py` | Skill 安全扫描 |

### 核心执行

| 工具 | 源文件 | 功能 |
|---|---|---|
| **terminal** | `terminal_tool.py` | Shell 命令执行（通过 6 种环境后端） |
| **code_execution** | `code_execution_tool.py` | Python/JavaScript 代码执行 |
| **file_tools** | `file_tools.py` | 文件读写 |
| **file_operations** | `file_operations.py` | 扩展文件操作 |
| **todo** | `todo_tool.py` | 任务跟踪 |
| **interrupt** | `interrupt.py` | 中断处理 |
| **debug_helpers** | `debug_helpers.py` | 调试辅助 |

### Web & 浏览器

| 工具 | 源文件 | 功能 |
|---|---|---|
| **browser** | `browser_tool.py` / `browser_camofox.py` | Camofox（fork from Camoufox）浏览器自动化 |
| **web_tools** | `web_tools.py` | HTTP 请求、网页抓取（firecrawl + exa） |
| **url_safety** | `url_safety.py` | URL 安全检查 |
| **website_policy** | `website_policy.py` | 网站访问策略 |

### 多媒体

| 工具 | 源文件 | 功能 |
|---|---|---|
| **vision_tools** | `vision_tools.py` | 图像分析（Claude Vision） |
| **image_generation** | `image_generation_tool.py` | 图像生成（DALL-E / Fal / 等） |
| **tts** | `tts_tool.py` | 文本转语音（Edge TTS 免费） |
| **neutts_synth** | `neutts_synth.py` | Neural TTS 合成 |
| **transcription** | `transcription_tools.py` | 音频转写 |
| **voice_mode** | `voice_mode.py` | 语音模式（faster-whisper 本地 STT） |

### Agent / MCP / 定时

| 工具 | 源文件 | 功能 |
|---|---|---|
| **delegate** | `delegate_tool.py` | 派发子代理任务 |
| **mixture_of_agents** | `mixture_of_agents_tool.py` | MoA 多模型集成（多个模型投票） |
| **mcp** | `mcp_tool.py` | MCP 客户端（连接外部 MCP server） |
| **cronjob** | `cronjob_tools.py` | 定时任务 |
| **rl_training** | `rl_training_tool.py` | RL 训练编排 |

### 安全 & 凭证

| 工具 | 源文件 | 功能 |
|---|---|---|
| **approval** | `approval.py` | 命令审批工作流 |
| **credential_files** | `credential_files.py` | 凭证管理 |
| **osv_check** | `osv_check.py` | OSV 漏洞扫描（依赖检查） |
| **tirith_security** | `tirith_security.py` | Tirith 安全检查 |

### 输出处理

| 工具 | 源文件 | 功能 |
|---|---|---|
| **ansi_strip** | `ansi_strip.py` | 去除 ANSI 转义序列 |
| **binary_extensions** | `binary_extensions.py` | 二进制文件扩展名检测 |
| **patch_parser** | `patch_parser.py` | 补丁解析 |
| **fuzzy_match** | `fuzzy_match.py` | 模糊匹配 |

### 其他

| 工具 | 源文件 | 功能 |
|---|---|---|
| **clarify** | `clarify_tool.py` | 主动向用户澄清问题 |
| **send_message** | （channels/gateway） | 跨平台发送消息 |
| **checkpoint_manager** | `checkpoint_manager.py` | 检查点管理 |
| **process_registry** | `process_registry.py` | 进程注册表 |
| **registry** | `registry.py` | 工具注册表 |
| **env_passthrough** | `env_passthrough.py` | 环境变量透传 |
| **managed_tool_gateway** | `managed_tool_gateway.py` | 受管工具网关 |
| **budget_config** | `budget_config.py` | 预算配置 |
| **openrouter_client** | `openrouter_client.py` | OpenRouter 客户端 |
| **tool_backend_helpers** | `tool_backend_helpers.py` | 工具后端辅助 |

**工具总数 ≈ 40+**（目录下共 50 多个 `.py` 文件，其中部分是辅助模块）。

---

## 6 种执行环境后端

源码路径：`/root/git/hermes-agent/tools/environments/`

统一接口：`base.py`

```python
"""Base class for all Hermes execution environment backends.

Unified spawn-per-call model: every command spawns a fresh ``bash -c`` process.
A session snapshot (env vars, functions, aliases) is captured once at init and
re-sourced before each command. CWD persists via in-band stdout markers (remote)
or a temp file (local).
"""
```

### 后端列表

| 后端 | 源文件 | 用途 | 休眠支持 |
|---|---|---|---|
| **local** | `local.py` | 本地 bash 执行 | - |
| **docker** | `docker.py` | Docker 容器沙箱 | - |
| **ssh** | `ssh.py` | 远程 SSH 执行 | - |
| **daytona** | `daytona.py` | Daytona 云 SDK | ✅ 持久 sandbox，idle → start |
| **modal** | `modal.py` | Modal serverless | ✅ Snapshot + 唤醒 |
| **singularity** | `singularity.py` | Singularity 容器（HPC 科研场景） | - |

### Daytona 持久 Sandbox

源码：`tools/environments/daytona.py:75-87`

```python
if self._persistent:
    try:
        self._sandbox = self._daytona.get(sandbox_name)
        self._sandbox.start()
        logger.info("Daytona: resumed sandbox %s for task %s",
                    self._sandbox.id, task_id)
    except DaytonaError:
        self._sandbox = None
```

**流程**：
1. `persistent_filesystem=True` 下，按名称查找已有 sandbox
2. 找到 → `.start()` 从休眠状态唤醒
3. 找不到 → 新建

这让 Agent **空闲时零成本休眠，有任务时瞬时唤醒**，同时保留之前的文件系统状态。

### Modal 快照

源码：`tools/environments/modal.py:25-72`

```python
_SNAPSHOT_STORE = get_hermes_home() / "modal_snapshots.json"

def _load_snapshots() -> dict:
    return _load_json_store(_SNAPSHOT_STORE)
```

Modal sandbox 将快照 ID 保存在 `~/.hermes/modal_snapshots.json`，下次启动时从快照恢复。

**对比 Claude Code Kairos**：Kairos 是"Always-On"（一直运行），Hermes 的 Daytona/Modal 模式是"按需唤醒"，后者**成本更低**。

---

## 14 个消息渠道（Gateway 适配器）

源码路径：`/root/git/hermes-agent/gateway/` 和 `/root/git/hermes-agent/hermes/`

| 渠道 | 文件 | 类型 |
|---|---|---|
| **CLI** | `cli.py` / `hermes_cli/` | 命令行 |
| **Telegram** | `gateway/telegram.py` | 即时消息 |
| **Discord** | `gateway/discord.py` | 即时消息 |
| **Slack** | `gateway/slack.py` | 企业消息 |
| **WhatsApp** | `gateway/whatsapp.py` | 即时消息 |
| **Signal** | `gateway/signal.py` | 加密即时消息 |
| **Matrix** | `gateway/matrix.py` | 开源联邦协议 |
| **Email** | `gateway/email.py` | 邮件 |
| **SMS** | `gateway/sms.py` | 短信 |
| **WeChat** | `gateway/weixin.py` | 企业消息（中国） |
| **WeCom** | `gateway/wecom.py` | 企业微信 |
| **DingTalk** | `gateway/dingtalk.py` | 钉钉 |
| **Feishu / Lark** | `gateway/feishu.py` | 飞书 |
| **Mattermost** | `gateway/mattermost.py` | 开源 Slack 替代 |
| **BlueBubbles** | `gateway/bluebubbles.py` | iMessage 桥接 |
| **Home Assistant** | `gateway/homeassistant.py` | 智能家居 |

**这是 codeagents 矩阵中**渠道最多的 Agent**。大多数 Code Agent 只支持 CLI + IDE，极少有跨消息平台的设计。

### 为什么这么多渠道？

Hermes 的产品定位不是"编程助手"而是"个人 AI 代理"——作者（Nous Research）的愿景是让 Agent 能**随时随地响应你**：

- 在 Telegram 里快速问一个问题
- 在 Signal 里安全讨论敏感话题
- 在邮件里处理长表单
- 在 WeChat 里用中文沟通
- 在 Home Assistant 里控制家里的灯

这和 Claude Code 的"开发者终端"定位完全不同，是一个**生活化的 AI 代理**。

---

## MCP 双向集成

### MCP Client（连接外部 MCP Server）

源码：`tools/mcp_tool.py:1-60`

```python
"""
MCP (Model Context Protocol) Client Support

Connects to external MCP servers via stdio or HTTP/StreamableHTTP transport,
discovers their tools, and registers them into the hermes-agent tool registry
so the agent can call them like any built-in tool.
"""
```

**支持的 transport**：
- stdio（命令 + 参数）
- HTTP / StreamableHTTP（URL）

### MCP Server（把 Hermes 自己暴露为 MCP）

源码：`mcp_serve.py:1-28`

```python
"""
Hermes MCP Server — expose messaging conversations as MCP tools.

Starts a stdio MCP server that lets any MCP client (Claude Code, Cursor, Codex,
etc.) list conversations, read message history, send messages, poll for live
events, and manage approval requests across all connected platforms.

Matches OpenClaw's 9-tool MCP channel bridge surface:
  conversations_list, conversation_get, messages_read, attachments_fetch,
  events_poll, events_wait, messages_send, permissions_list_open,
  permissions_respond

Plus: channels_list (Hermes-specific extra)
"""
```

**9 个 OpenClaw 兼容的 MCP 工具 + 1 个 Hermes 特有的 `channels_list`**。

这让 **Claude Code / Cursor / Codex CLI** 等 MCP Client 可以通过 MCP 协议：

- 列出 Hermes 所有已连接的聊天平台
- 读取历史对话
- 发送消息到任何平台
- 管理审批请求
- 轮询/等待事件

**实用场景**：你在 Claude Code 里写代码，让它通过 Hermes MCP Server 给 Telegram 发一条通知；或者让 Claude Code 读取 Hermes 里已经有的跨平台对话历史作为上下文。

---

## 下一步

- 闭环学习系统 → [03-closed-learning-loop.md](./03-closed-learning-loop.md)
- 架构与 System Prompt 分层 → [02-architecture.md](./02-architecture.md)
- 源码引用 → [EVIDENCE.md](./EVIDENCE.md)
