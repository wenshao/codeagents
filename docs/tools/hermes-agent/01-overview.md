# Hermes Agent — 概述

## 产品定位

Hermes Agent 由 **Nous Research** 开发，定位是 **"The self-improving AI agent"**（自我改进的 AI 代理）。官方 README 的一句话描述：

> "It's the only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions."

与 Claude Code / Qwen Code / Codex CLI 等"编程终端助手"不同，Hermes 是**跨平台多渠道的个人 AI 代理**：它既可以在 CLI 里写代码，也可以在 Telegram / Discord / Slack / WhatsApp / Signal / Email / WeChat / DingTalk / Feishu / Matrix / Mattermost / SMS / BlueBubbles / Home Assistant **14 个渠道**里作为聊天机器人响应你。

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

或从 PyPI：

```bash
pip install hermes-agent
```

## 支持的模型提供商

源码：`README.md:16`

- **Nous Portal**（Nous Research 自家推理服务）
- **OpenRouter**（200+ 模型聚合）
- **z.ai / GLM**（智谱 AI）
- **Kimi / Moonshot**
- **MiniMax**
- **OpenAI**（及任何 OpenAI 兼容端点）
- **Anthropic**（通过 `anthropic>=0.39.0` 依赖）
- 自定义端点

使用 `openai>=2.21.0` + `anthropic>=0.39.0` 双 SDK，并通过 `Credential Pool`（`agent/credential_pool.py`）支持同一 Provider 配置多个 API Key、自动轮换、速率限制追踪、失败自动切换。

**4 种 Key 选择策略**：

| 策略 | 行为 |
|---|---|
| `fill_first` | 用完一个再换下一个（配额最大化） |
| `round_robin` | 轮询（负载均衡） |
| `random` | 随机 |
| `least_used` | 最少使用优先 |

**冷却时间**：429（速率限制）或 402（配额不足）后默认冷却 **1 小时**（`EXHAUSTED_TTL_429_SECONDS = 60 * 60`）。

## 与其他 18 款 Code Agent 的核心差异

| 差异点 | Hermes | 其他 Code Agent |
|---|---|---|
| **自主 Skill 创建** | 后台 review 子代理自动决定是否沉淀 skill | 全部是用户手工创建 / 预置 |
| **Skill 自改进** | `skill_manage(action='patch')` — 发现 skill 过时立即修补 | 无自修补机制 |
| **冻结快照 Memory** | 会话开始拍快照注入 system prompt，会话内 disk 持久化但不再改 system prompt（保护 prompt cache） | Claude Code 2.1+ 有类似 auto-memory，但大多数 agent 没有这个"缓存保护"设计 |
| **跨会话 FTS5 搜索** | SQLite FTS5 全文索引所有历史会话 + Gemini Flash 摘要 | 只有 Codex CLI resume 和 Claude Code /resume 能回到旧会话，但不能"模糊搜索历史" |
| **Nudge 计数器** | 两个独立计数器（用户回合数 10 / 工具调用数 10）触发后台 review 子代理 | 无主动触发机制，全部被动等待用户命令 |
| **多渠道** | 14 个消息平台 + 1 个 CLI | 大多数是纯 CLI（OpenHands 有 Web UI，Continue 有 VS Code） |
| **6 种执行环境后端** | Local / Docker / SSH / Daytona / Singularity / Modal（统一 `BaseEnvironment` 接口） | 绝大多数只有 Local，Codex CLI 有三平台 OS 沙箱，OpenHands 有 Docker |
| **MCP 双向** | 既是 Client（`tools/mcp_tool.py`）也是 Server（`mcp_serve.py` 暴露 9 工具 + channels_list） | 多数只是 Client |

## 代码规模

```
$ find /root/git/hermes-agent -name "*.py" | wc -l
822
$ find /root/git/hermes-agent -name "*.py" | xargs wc -l
  369014 total
```

**369,014 行 Python** — 是 codeagents 矩阵中**最大的 Python 代码库**（对比 Aider ~30K / OpenHands ~60K / SWE-agent ~20K / Kimi CLI ~20K）。

## 核心依赖（摘自 `pyproject.toml`）

```python
dependencies = [
  "openai>=2.21.0,<3",
  "anthropic>=0.39.0,<1",
  "pydantic>=2.12.5,<3",
  "prompt_toolkit>=3.0.52,<4",  # 交互式 CLI
  "rich>=14.3.3,<15",
  "tenacity>=9.1.4,<10",
  "httpx[socks]>=0.28.1,<1",
  "exa-py>=2.9.0,<3",            # 搜索工具
  "firecrawl-py>=4.16.0,<5",     # 网页抓取
  "fal-client>=0.13.1,<1",       # 图像生成
  "edge-tts>=7.2.7,<8",          # 免费 TTS
]
```

**可选依赖**：
- `modal` — Modal serverless 环境后端
- `daytona` — Daytona 云环境后端
- `messaging` — Telegram / Discord / Slack 聊天渠道
- `cron` — 定时任务
- `matrix` — Matrix 协议
- `voice` — 本地语音识别（faster-whisper + sounddevice）
- `honcho` — 外部 memory provider（Honcho.ai）

## 自我定位

Hermes 明确区别于"IDE 助手"或"编程终端"。从 `RELEASE_v0.4.0.md` 和 `AGENTS.md` 的线索看，它的目标是成为**"个人 AI 伴侣"** —— 能够：

1. 在你写代码时帮你写代码（CLI + skill）
2. 在你聊天时在 Telegram/Signal/Slack 等渠道回答你
3. 在后台定时任务中（`cron` + `cronjob_tools.py`）主动做事
4. 持续学习你的偏好和专业知识（Memory 闭环）
5. 把经验沉淀为可复用的 skill（Skill 闭环）

这和 **Claude Code 的 Kairos（Always-On Agent）** 在愿景上最接近——两者都是"长期运行、主动行动、跨会话记忆"的范式——但实现路径和重点不同（详见 [03-closed-learning-loop.md](./03-closed-learning-loop.md) 和 [closed-learning-loop-deep-dive.md](../../comparison/closed-learning-loop-deep-dive.md)）。

## 下一步

- 闭环学习的技术细节 → [03-closed-learning-loop.md](./03-closed-learning-loop.md)
- 工具和渠道清单 → [04-tools-channels.md](./04-tools-channels.md)
- 架构和 System Prompt 分层 → [02-architecture.md](./02-architecture.md)
- 技术声明的源码引用 → [EVIDENCE.md](./EVIDENCE.md)
