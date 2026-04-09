# Copilot CLI 源码分析（面向 Code Agent 开发者）

> 本系列文档基于 Copilot CLI 二进制反编译（Node.js SEA，133MB）和 npm 包 v0.0.403 源码分析，提炼出对 Qwen Code、Gemini CLI 等 Code Agent 开发者有参考价值的架构设计和实现模式。
>
> **阅读对象**：正在开发或改进 CLI Code Agent 的工程师
>
> **不是**：Copilot CLI 用户手册或功能介绍

## 文档索引

| 文档 | 开发者关注点 | Qwen Code 对标 |
|------|------------|----------------|
| [01-概述与对标](./01-overview.md) | 能力矩阵、架构差异速查、可借鉴 vs 不可复制 | GitHub 集成差距 + 多模型路由参考 |
| [02-命令系统](./02-commands.md) | 34 命令 + 67 工具 + 3 代理的注册/分类/权限设计 | YAML 代理定义 + 假阳性过滤 + 7 级指令链 |
| [03-技术架构](./03-architecture.md) | SEA 二进制、双模式加载器、模型路由、无限会话、安全模型 | 二进制分发 + 模型适配 + 压缩策略 |
| [EVIDENCE.md](./EVIDENCE.md) | 二进制分析原始证据 | — |

## 如何使用本系列

1. **快速定位差距**：从 [01-概述](./01-overview.md) 的能力矩阵找到你关心的领域
2. **深入命令/工具**：进入 [02-命令系统](./02-commands.md) 查看工具分类和代理定义细节
3. **理解架构**：从 [03-技术架构](./03-architecture.md) 了解二进制打包、模型路由、会话压缩
4. **查阅证据**：所有技术声明在 [EVIDENCE.md](./EVIDENCE.md) 中有源码/二进制分析支撑

## 核心发现速查

| 发现 | 开发者价值 |
|------|-----------|
| YAML 声明式代理定义 | 无需硬编码即可定义代理（模型 + 工具 + 提示），用户可自定义 |
| 7 级指令搜索链 | 兼容 CLAUDE.md/GEMINI.md/AGENTS.md，降低迁移成本 |
| 模型特定 system prompt | 不同模型注入差异化行为修正指令 |
| code-review 假阳性过滤 | 8 维度 + 8 排除 + 置信度门槛，可直接复用 |
| 双模式加载器 | SEA 原生优先 + npm 回退，零依赖安装 |
| 48 个 GitHub API 直调工具 | API 直调比 Bash + CLI 更安全可控 |

## 相关文档

- [Copilot CLI 用户指南](../../guides/copilot-cli-user-guide.md)
- [Claude Code vs Copilot CLI 对比](../../comparison/claude-code-vs-copilot-cli.md)
- [功能矩阵对比](../../comparison/features.md)

## 分析方法

- **二进制分析**：Node.js SEA（133MB）的 strings / 解压 / 资源提取
- **npm 包分析**：`@github/copilot@0.0.403` 源码分析（index.js 15MB + sdk 11MB）
- **官方文档**：[docs.github.com/copilot](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- **CLI 帮助**：`copilot --help` 完整输出（57 个参数）

**源码版本**：v0.0.403（npm `@github/copilot`），原生二进制 v1.0.11
**最后更新**：2026-03
