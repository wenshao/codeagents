# 基准测试概览

本文档涵盖 AI 编程代理的基准测试。

> **重要声明**：本文中标"~"的数字为近似值或社区测试估算，非官方发布数据。具体分数请以 [SWE-bench 排行榜](https://www.swebench.com/) 和各项目官方公告为准。

## SWE-bench

### 什么是 SWE-bench？

SWE-bench 是 Princeton NLP 开发的基准，使用真实 GitHub issues 评估 AI 代理的软件工程能力。

- **网站**：[swebench.com](https://www.swebench.com/)
- **仓库**：[github.com/princeton-nlp/SWE-bench](https://github.com/princeton-nlp/SWE-bench)

### 基准子集

| 子集 | 规模 | 说明 |
|------|------|------|
| SWE-bench Lite | 300 issues | 较简单的子集 |
| SWE-bench Verified | 500 issues | 人工验证，金标准 |
| SWE-bench Pro | 2000+ issues | 生产级任务 |

### 排行榜（参考值）

| Agent | SWE-bench Verified | 数据来源 |
|-------|-------------------|---------|
| SWE-agent (增强版) | ~74% | SWE-agent 论文/官方 |
| Claude Code | ~60% | Anthropic 公开数据 |
| OpenHands | ~55% | OpenHands 项目 |
| Aider | ~45% | Aider 排行榜 |

*注：各代理的测试条件（模型版本、重试次数、超时设置）可能不同，分数不完全可直接比较。*

> 以下工具（Continue、Cline、Codex CLI 等）**无公开的 SWE-bench 官方成绩**，此前文档中的数字为估算，已移除。

## 其他基准

### HumanEval

Python 编程问题（评估的是**模型**而非代理工具）：

| 模型 | Pass@1 | 说明 |
|------|--------|------|
| Claude Opus 4 | ~92% | Anthropic 公开 |
| GPT-4o | ~90% | OpenAI 公开 |
| Gemini 2.5 Pro | ~88% | Google 公开 |
| Qwen3-Coder | ~85% | 阿里云公开 |

*注：HumanEval 评估的是 LLM 模型的代码生成能力，与代理工具的集成效果不同。*

## 成本参考 (2026)

每百万 token 大约成本：

| 模型 | 输入 | 输出 |
|------|------|------|
| Claude Opus 4 | $15 | $75 |
| Claude Sonnet 4 | $3 | $15 |
| Claude Haiku 4 | $0.25 | $1.25 |
| GPT-4o | $2.50 | $10 |
| GPT-4o-mini | $0.15 | $0.60 |
| Gemini 2.5 Pro | $1.25 | $5 |
| Qwen3-Coder (API) | 按量付费 | — |
| Qwen3-Coder (OAuth) | 免费（1000 次/天） | — |

*定价可能变动，请以各提供商官网为准。*

## 数据来源

- [SWE-bench 排行榜](https://www.swebench.com/)
- [Aider 排行榜](https://aider.chat/docs/leaderboards/)
- [Artificial Analysis - Coding Agents](https://artificialanalysis.ai/insights/coding-agents-comparison)
- 各项目官方 README/公告

---

*本文档聚焦可验证的数据来源。此前版本中的速度对比、LiveCodeBench 分数、按任务类型排名等内容因缺乏可靠来源已移除。*
