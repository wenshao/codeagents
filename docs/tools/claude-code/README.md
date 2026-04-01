# Claude Code 文档

> Anthropic 官方终端 AI 编程代理

| 文档 | 内容 |
|------|------|
| [01-概述](./01-overview.md) | 核心功能、安装、模型、定价 |
| [02-命令详解](./02-commands.md) | 79 命令完整说明 |
| [03-技术架构](./03-architecture.md) | 运行时、API、遥测、消息类型 |
| [04-工具系统](./04-tools.md) | 42 工具架构设计、Zod Schema、权限模型、安全机制、实现者 Checklist |
| [05-Skill 系统](./05-skills.md) | Skill 定义、加载、内置 Skill |
| [06-设置与安全](./06-settings.md) | 5 层设置、权限、沙箱、24 种 Hook 事件 |
| [07-会话与记忆](./07-session.md) | 会话存储、上下文压缩（5 层）、CLAUDE.md 记忆、团队同步、Worktree、文件检查点、MCP |
| [08-Remote Control](./08-remote-control.md) | 远程控制架构、会话生命周期、安全纵深、评价优缺点、7 款竞品对比 |
| [09-多代理系统](./09-multi-agent.md) | Leader-Worker 协作、Swarm 三后端、Agent 定义、邮箱通信、任务管理、协调模式、远程传送 |
| [10-Prompt Suggestions](./10-prompt-suggestions.md) | 下一步提示预测：生成流程、Prompt 模板、12 条过滤规则、Speculation 推测执行 |
| [11-终端渲染](./11-terminal-rendering.md) | 防闪烁：DEC 2026 同步输出、差分渲染、双缓冲、DECSTBM 硬件滚动、缓存池化、60fps 节流 |
