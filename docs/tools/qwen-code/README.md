# Qwen Code 架构文档（面向贡献者和开发者）

> Qwen Code 是阿里云 Qwen 团队的开源 AI 编程代理（Apache-2.0），基于 Gemini CLI fork 并大幅增强。本系列文档面向**项目贡献者和开发者**——了解当前架构、已知差距和改进方向。
>
> **源码**：[github.com/QwenLM/qwen-code](https://github.com/QwenLM/qwen-code)

## 文档索引

| 文档 | 内容 | 改进方向 |
|------|------|---------|
| [01-概述](./01-overview.md) | 核心能力、与上游差异、已知差距 | 差距速查 |
| [02-命令](./02-commands.md) | 41 命令 + CLI 参数 | 命令差距 |
| [03-架构](./03-architecture.md) | Agent Loop、Arena、CoreToolScheduler、多 Provider | 核心循环改进 |
| [04-工具](./04-tools.md) | 16 核心工具 + MCP | 工具差距 |
| [05-设置](./05-settings.md) | 7 层配置 + Hook 系统 | Hook 扩展 |
| [06-扩展](./06-extensions.md) | 三格式扩展兼容 | 扩展生态 |

## 当前状态速查

| 维度 | Qwen Code 现状 | vs Claude Code | vs 上游 Gemini CLI |
|------|----------------|---------------|-------------------|
| 工具数 | 16 | 42（差 26） | 23（差 7） |
| 命令数 | ~41 | ~79（差 38） | ~41（接近） |
| Hook 事件 | ~12 | 27（差 15） | 11（接近） |
| 上下文压缩 | 单一 70% | 5 层递增 | 单阈值 50% |
| 记忆系统 | 简单笔记 | CLAUDE.md + Auto Dream | GEMINI.md |
| 安全 | AST 只读检测 | 沙箱 + 23 项检查 | sandbox + 环境变量净化 |
| 多 Agent | Arena + Agent Team | Coordinator/Swarm + Kairos | A2A + Subagent |
| 渲染 | 标准 Ink（闪烁） | 自建 Ink fork（无闪烁） | SlicingMaxSizedBox |
| 崩溃恢复 | 无 | 3 种检测 + 合成续行 | 无 |

## 改进报告

- [**Claude Code 对比改进报告**](../../comparison/qwen-code-improvement-report.md)——240 项改进建议，22 个社区 PR 追踪
- [**Gemini CLI 上游 backport 报告**](../../comparison/qwen-code-gemini-upstream-report.md)——42 项可 backport 改进
- [**/review 功能改进建议**](../../comparison/qwen-code-review-improvements.md)——9 项改进（P0 确定性分析 ~ P3 报告持久化）
- [**工具输出限高防闪烁**](../../comparison/tool-output-height-limiting-deep-dive.md)——Gemini CLI vs Qwen Code 渲染对比

## 活跃 PR 进展（22 个追踪中）

已合并：#2525 ✓（Speculation）、#2854 ✓（Mid-Turn Queue Drain）、#2889 ✓（危险操作指导）

关键 open PR：#2936（Fork Subagent）、#2932（/review 增强）、#2886（Agent Team）、#2921（/plan）
