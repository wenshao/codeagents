# Claude Code 源码分析（面向 Code Agent 开发者）

> 本系列文档基于 Claude Code 源码分析（~1800 文件）和二进制逆向分析，提炼出对 Qwen Code、Gemini CLI 等 Code Agent 开发者有参考价值的架构设计和实现模式。
>
> **阅读对象**：正在开发或改进 CLI Code Agent 的工程师
>
> **不是**：Claude Code 用户手册或功能介绍

## 文档索引

| 文档 | 开发者关注点 | Qwen Code 对标 |
|------|------------|----------------|
| [01-概述与对标](./01-overview.md) | 核心能力矩阵、架构差异速查 | 功能差距一览 |
| [02-命令系统](./02-commands.md) | 79 命令的注册/加载/权限设计 | 斜杠命令架构参考 |
| [03-技术架构](./03-architecture.md) | Bootstrap 链、QueryEngine 循环、Feature Flag DCE、Provider 通信 | 核心循环 + 启动优化 |
| [04-工具系统](./04-tools.md) | 42 工具的 Zod Schema、权限模型、延迟加载、安全校验 | 工具注册 + ToolSearch |
| [05-Skill 系统](./05-skills.md) | Skill 定义格式、加载优先级、内置 Skill | Skill/技能架构 |
| [06-设置与安全](./06-settings.md) | 5 层设置、沙箱隔离、24 种 Hook 事件、权限模型 | 安全加固路线 |
| [07-会话与记忆](./07-session.md) | 5 层上下文压缩、CLAUDE.md 记忆、团队记忆、MCP、文件检查点 | 上下文管理 + 记忆系统 |
| [08-Remote Control](./08-remote-control.md) | WebSocket/SSE 桥接、会话生命周期、安全纵深 | 远程控制架构 |
| [09-多 Agent 系统](./09-multi-agent.md) | Leader-Worker、Swarm 三后端、邮箱通信、任务管理、Kairos | 多 Agent 编排 |
| [10-Prompt Suggestions](./10-prompt-suggestions.md) | 预测生成、12 条过滤规则、Speculation 推测执行 | 智能补全 |
| [11-终端渲染](./11-terminal-rendering.md) | DEC 2026 同步输出、差分渲染、缓存池化 | 防闪烁 + 渲染性能 |
| [12-Hook 系统](./12-hooks.md) | 27 种事件、6 种处理器（含 LLM 推理决策）、hookify 自动规则 | Hook 事件覆盖度 + prompt/agent Hook |
| [13-系统提示](./13-system-prompt.md) | 动态拼装、静态/动态分区、Prompt Cache 优化、`<system-reminder>` 注入 | Prompt Cache 分区 + QWEN.md 注入方式 |
| [14-MCP 集成](./14-mcp.md) | 6 种传输、OAuth + XAA、Channel 消息、断线重连、资源订阅 | MCP 资源/Prompt 支持 + 重连策略 |
| [EVIDENCE.md](./EVIDENCE.md) | 二进制分析原始证据 | — |

## 如何使用本系列

1. **快速定位差距**：从 [01-概述](./01-overview.md) 的能力矩阵找到你关心的领域
2. **深入架构**：进入对应章节查看 Claude Code 的实现细节
3. **对照改进**：每个章节的"开发者参考"小节提供 Qwen Code 的对标分析和实现建议
4. **查阅证据**：所有技术声明在 [EVIDENCE.md](./EVIDENCE.md) 中有源码/二进制分析支撑

## 相关文档

- [Qwen Code 改进建议报告（Claude Code 对比）](../../../docs/comparison/qwen-code-improvement-report.md)
- [Qwen Code 上游 backport 报告（Gemini CLI 对比）](../../../docs/comparison/qwen-code-gemini-upstream-report.md)
- [/review 功能改进建议](../../../docs/comparison/qwen-code-review-improvements.md)

## 分析方法

- **源码分析**：基于公开的反编译/source map 分析结果
- **二进制分析**：ELF x86-64 二进制的 `strings` / `readelf` / 反编译
- **官方文档**：[code.claude.com/docs](https://code.claude.com/docs/en)
- **网络搜索**：GitHub Blog、社区分析、第三方拆解
