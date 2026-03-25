# 定价与成本对比

> 2026 年 3 月数据。AI 编程工具的费用模式差异巨大——从完全免费到每月 $200+。

## 定价模式总览

| 工具 | 模式 | 月费 | 免费层 | 按量计费 |
|------|------|------|--------|---------|
| **Claude Code** | 订阅 + API | Pro $20, Max $100/$200 | 无 | API: 按 token |
| **Copilot CLI** | 订阅 | Free/Pro $10/Business $19/Enterprise $39 | ✓（有限） | Premium Requests 配额 |
| **Codex CLI** | API 按量 | 无月费 | 无 | 按 token |
| **Aider** | API 按量（自带 key） | 无月费 | 无（需 API key） | 取决于所选模型 |
| **Gemini CLI** | API + 免费层 | 无月费 | **1,500 次/天**（Gemini API） | API 按量 |
| **Qwen Code** | 免费 + API | 无月费 | **1,000 次/天**（OAuth） | DashScope 按量 |
| **Kimi CLI** | API 按量 | 无月费 | 有限免费额度 | Moonshot API 按量 |
| **Goose** | API 按量（自带 key） | 无月费 | 无 | 取决于所选模型 |
| **OpenCode** | API 按量 | 无月费 | 无 | 取决于提供商 |

## Claude Code 详细定价

| 计划 | 月费 | 包含 | 模型 | Opus 用量 |
|------|------|------|------|----------|
| **Pro** | $20 | 有限使用 | Sonnet 4.6（默认） | 有限 |
| **Max (5x)** | $100 | 高速率 | Opus 4.6（默认） | 高 |
| **Max (20x)** | $200 | 最高速率 | Opus 4.6（默认） | 最高 |
| **API** | 按量 | 无限（按 token） | 全部 | 无限 |

API 按量价格（参考）：

| 模型 | 输入 $/M tokens | 输出 $/M tokens |
|------|----------------|----------------|
| Sonnet 4.6 | $3 | $15 |
| Opus 4.6 | $15 | $75 |
| Haiku 4.5 | $0.80 | $4 |

## Copilot CLI 详细定价

| 计划 | 月费 | Premium Requests | 免费模型 |
|------|------|-----------------|---------|
| **Free** | $0 | 有限 | gpt-5-mini (0x), gpt-4.1 (0x) |
| **Pro** | $10 | 500/月 | 同上 |
| **Business** | $19/人 | 500/月 | 同上 |
| **Enterprise** | $39/人 | 1000/月 | 同上 |

模型倍率：

| 倍率 | 模型 |
|------|------|
| 0x（免费） | gpt-5-mini, gpt-4.1 |
| 0.33x | claude-haiku-4.5, gpt-5.1-codex-mini |
| 1x | claude-sonnet-4.5, gpt-5.2-codex, gemini-3-pro |
| 3x | claude-opus-4.5 |

## 典型任务成本估算

> 以下为粗略估算，实际取决于任务复杂度、上下文大小和工具调用次数。

### 场景 1：修复一个简单 Bug（~5 分钟）

| 工具 | 模型 | 估算 token | 估算费用 |
|------|------|-----------|---------|
| Claude Code (Pro) | Sonnet 4.6 | ~50K in + ~10K out | 包含在 $20/月 |
| Claude Code (API) | Sonnet 4.6 | ~50K in + ~10K out | ~$0.30 |
| Copilot CLI (Pro) | claude-sonnet-4.5 | 1 premium request | 包含在 $10/月 |
| Codex CLI | gpt-5.1-codex | ~50K in + ~10K out | ~$0.20 |
| Aider | claude-sonnet-4.6 | ~30K in + ~5K out | ~$0.17 |
| Gemini CLI | gemini-2.5-pro | ~50K in + ~10K out | 免费层 |
| Qwen Code | qwen3.5-plus | ~50K in + ~10K out | 免费层 |

### 场景 2：开发一个新功能（~30 分钟）

| 工具 | 模型 | 估算 token | 估算费用 |
|------|------|-----------|---------|
| Claude Code (Pro) | Sonnet 4.6 | ~500K in + ~100K out | 包含在 $20/月 |
| Claude Code (API) | Sonnet 4.6 | ~500K in + ~100K out | ~$3.00 |
| Claude Code (API) | Opus 4.6 | ~500K in + ~100K out | ~$15.00 |
| Copilot CLI (Pro) | claude-sonnet-4.5 | ~10 premium requests | 包含在 $10/月 |
| Codex CLI | gpt-5.1-codex | ~500K in + ~100K out | ~$2.00 |
| Aider | claude-sonnet-4.6 | ~300K in + ~50K out | ~$1.65 |
| Gemini CLI | gemini-2.5-pro | ~500K in + ~100K out | 免费层（可能触发限制） |

### 场景 3：大规模重构（~2 小时）

| 工具 | 模型 | 估算 token | 估算费用 |
|------|------|-----------|---------|
| Claude Code (Max) | Opus 4.6 | ~2M in + ~500K out | 包含在 $100/月 |
| Claude Code (API) | Opus 4.6 | ~2M in + ~500K out | ~$67.50 |
| Copilot CLI (Pro) | claude-opus-4.5 | ~30 requests (3x) | 可能超出 500 配额 |
| Codex CLI | gpt-5.1-codex-max | ~2M in + ~500K out | ~$15.00 |
| Aider | claude-opus-4.6 | ~1M in + ~200K out | ~$30.00 |

## 成本优化建议

| 策略 | 适用工具 | 说明 |
|------|---------|------|
| **选择小模型做简单任务** | 全部 | Haiku/mini 比 Opus 便宜 10-20 倍 |
| **利用免费层** | Gemini CLI, Qwen Code, Copilot | 日常简单任务可完全免费 |
| **Prompt Caching** | Claude Code, Aider | 减少重复系统提示的 token 费用 |
| **上下文压缩** | 全部 | 定期 /compact 减少 token 累积 |
| **Aider 的 /architect** | Aider | 用强模型规划、弱模型执行，节省 50%+ |
| **Copilot 免费模型** | Copilot CLI | gpt-5-mini 和 gpt-4.1 为 0x 倍率 |
| **订阅 vs API** | Claude Code | 日均 >$3.3 时 Max $100 更划算 |
