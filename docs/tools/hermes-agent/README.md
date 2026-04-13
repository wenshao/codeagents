# Hermes Agent

> Nous Research 的"自我改进"AI 代理。当前 19 款 Code Agent 中**唯一**将**闭环学习系统**（Closed Learning Loop）作为核心卖点的产品。

**仓库**：https://github.com/NousResearch/hermes-agent
**版本**：0.8.0（2026 年 4 月）
**许可证**：MIT
**语言**：Python >=3.11，822 个 `.py` 文件 / **369,014 行 Python 代码**
**本地源码**：`/root/git/hermes-agent`

## 文件结构

| 文件 | 内容 |
|------|------|
| [01-overview.md](./01-overview.md) | 产品定位、安装、模型/渠道支持、与其他 Agent 的差异化 |
| [02-architecture.md](./02-architecture.md) | 整体架构、`run_agent.py` 主循环、System Prompt 分层、AIAgent 子代理 |
| [03-closed-learning-loop.md](./03-closed-learning-loop.md) | **核心篇**：持久 Memory（冻结快照）/ 自主 Skill / FTS5 跨会话搜索 / Nudge 触发器 |
| [04-tools-channels.md](./04-tools-channels.md) | 28 个内置工具 + 14 个消息渠道 + 6 种执行环境后端 |
| [EVIDENCE.md](./EVIDENCE.md) | 全部技术声明的源码引用（`path:line` + quoted snippets） |

## 一句话

**"经验 → 存储 → 召回 → 改进"** — 代理不需要用户说"记住这个"，它会用两个计数器（用户回合 / 工具调用）自动触发后台 review 子代理，决定哪些经验值得沉淀为 memory 或 skill，未来对话中自动召回。

## 与 codeagents 对比矩阵的关系

| 维度 | Hermes | Claude Code | Qwen Code |
|---|---|---|---|
| 代码规模 | 369K Python | ~512K Rust | ~439K TS |
| 开源 | ✓ MIT | ✗ 专有 | ✓ Apache-2.0 |
| 自主学习闭环 | ✓ 原生 | ⚠ Kairos 异步 Agent | ⚠ PR #3087 开发中 |
| Skill 自创自改 | ✓ | ⚠ 用户手工创建 | ⚠ 用户手工创建 |
| 跨会话 FTS5 搜索 | ✓ SQLite FTS5 + Gemini Flash 摘要 | ⚠ 仅当前 project | ⚠ 仅当前 project |
| 消息渠道 | **14 个**（Telegram/Discord/Slack/WhatsApp/Signal/Matrix/Email/SMS/WeChat/WeCom/DingTalk/Feishu/Mattermost/BlueBubbles） | CLI | CLI + VS Code |
| 执行环境 | **6 种**（Local/Docker/SSH/Daytona/Singularity/Modal） | Local + Kairos | Local + Seatbelt/Docker/Podman |
| MCP 双向 | ✓ Client + Server | Client | Client |

## 快速导航

- 想了解闭环学习系统如何工作？ → [03-closed-learning-loop.md](./03-closed-learning-loop.md)
- 想看和 Claude Code / qwen-code 的横向对比？ → [closed-learning-loop-deep-dive.md](../../comparison/closed-learning-loop-deep-dive.md)
- 想验证某个技术声明？ → [EVIDENCE.md](./EVIDENCE.md)
