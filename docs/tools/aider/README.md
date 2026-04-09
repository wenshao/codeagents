# Aider 源码分析（面向 Code Agent 开发者）

> 本系列文档基于 Aider 开源仓库 Python 源码直接分析，提炼出对 Qwen Code、Gemini CLI 等 Code Agent 开发者有参考价值的架构设计和实现模式。重点关注 Repo Map（Tree-sitter + PageRank）、14 种编辑格式、弱模型分离等 Aider 独有创新。
>
> **阅读对象**：正在开发或改进 CLI Code Agent 的工程师
>
> **不是**：Aider 用户手册或功能介绍

## 文档索引

| 文档 | 开发者关注点 | Qwen Code 对标 |
|------|------------|----------------|
| [01-概述与对标](./01-overview.md) | 核心能力矩阵、Python 技术栈、Git 原生设计 | 功能差距 + 可借鉴模式 |
| [02-命令详解](./02-commands.md) | 42 个命令的 cmd_ 反射分发、SwitchCoder 模式切换 | 命令注册 + 编辑格式切换 |
| [03-技术架构](./03-architecture.md) | 代理循环、Repo Map PageRank、14 种编辑格式、消息分块、后台压缩、Git 三标志归因 | Repo Map + 编辑格式 + 弱模型分离 |
| [EVIDENCE.md](./EVIDENCE.md) | 源码分析证据 | — |

## 如何使用本系列

1. **快速定位差距**：从 [01-概述](./01-overview.md) 的能力矩阵找到你关心的领域
2. **深入架构**：进入对应章节查看 Aider 的实现细节
3. **对照改进**：每个章节的"Qwen Code 对标"小节提供对标分析和实现建议
4. **查阅证据**：所有技术声明在 [EVIDENCE.md](./EVIDENCE.md) 中有源码路径支撑

## 分析方法

- **源码分析**：GitHub 公开仓库 Python 源码直接分析
- **关键文件**：`base_coder.py`（2485 行）、`commands.py`（1712 行）、`repomap.py`（867 行）、`repo.py`（622 行）
- **官方文档**：[aider.chat/docs](https://aider.chat/docs/)

## 相关文档

- [Qwen Code 改进建议报告（Claude Code 对比）](../../../docs/comparison/qwen-code-improvement-report.md)
- [功能矩阵对比](../../../docs/comparison/features.md)

**开发者：** Paul Gauthier
**许可证：** GPL-3.0
**仓库：** [github.com/Aider-AI/aider](https://github.com/Aider-AI/aider)
**Stars：** 约 43k
