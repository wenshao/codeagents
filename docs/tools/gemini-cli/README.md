# Gemini CLI 源码分析（面向 Code Agent 开发者）

> Gemini CLI 是 **Qwen Code 的上游项目**（2025-10 fork）。本系列文档分析其架构设计，重点标注 Qwen Code 未 backport 的新功能和可借鉴模式。
>
> **阅读对象**：Qwen Code 开发者——了解上游做了什么、哪些值得 backport
>
> **源码**：[github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)

## 文档索引

| 文档 | 开发者关注点 | Qwen Code backport 价值 |
|------|------------|------------------------|
| [01-概述与对标](./01-overview.md) | 能力矩阵、fork 差距分析 | 上游新功能速查 |
| [02-命令详解](./02-commands.md) | 41 命令 + CLI 参数 | 命令差异对比 |
| [03-技术架构](./03-architecture.md) | AgentSession、调度器、模型路由 | 核心循环 + 调度器 |
| [04-工具与代理](./04-tools.md) | 23 工具 + 5 代理 + MCP + A2A | 工具差异 + trackerTools |
| [05-策略与安全](./05-policies.md) | TOML 策略引擎、Hook、沙箱 | 策略引擎 + sandbox |

## 核心定位：Qwen Code 的上游

```
2025-06-25  Gemini CLI v0.1.0 首次发布
2025-10-23  Qwen Code 最后同步上游（v0.8.2）
    ↓ (此后 Gemini CLI 独立演进 28 个大版本)
2026-03-30  Gemini CLI v0.36.0（当前最新）
    ↓
2026-04    差距：2041 个 commit、42 项可 backport 改进
```

**详细 backport 分析**：[Qwen Code 上游 backport 报告（42 项）](../../comparison/qwen-code-gemini-upstream-report.md)

## 相关文档

- [Qwen Code 上游 backport 报告](../../comparison/qwen-code-gemini-upstream-report.md)——42 项可 backport 改进
- [Qwen Code 改进建议报告](../../comparison/qwen-code-improvement-report.md)——240 项改进（Claude Code 对比）
- [工具输出限高防闪烁](../../comparison/tool-output-height-limiting-deep-dive.md)——Gemini CLI 的 SlicingMaxSizedBox
