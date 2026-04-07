# 1. Claude Code 概述——Code Agent 开发者视角

> **阅读对象**：正在开发 Qwen Code / Gemini CLI 等 CLI Code Agent 的工程师
>
> **核心问题**：Claude Code 做对了什么？哪些设计值得借鉴？哪些是 Anthropic 独有优势无法复制？

## 一、为什么要研究 Claude Code

Claude Code 是目前功能最完整的 CLI Code Agent——79 个斜杠命令、42 个内置工具、5 层设置体系、24 种 Hook 事件、多 Agent 协作、100 万 token 上下文。它在 SWE-bench 等编程基准上持续领先，且是唯一在内部使用 Kairos（Always-On 自治模式）的 Agent。

对于 Qwen Code 开发者，Claude Code 的价值不在于它的模型能力（那是 Anthropic 独有的），而在于它的**工程架构**——这些模式可以在任何模型上复现。

## 二、能力矩阵速查

| 能力领域 | Claude Code | Qwen Code | 差距 | 详见 |
|---------|-------------|-----------|------|------|
| **上下文管理** | 5 层压缩 + 自动裁剪 | 单一 70% 手动压缩 | 大 | [07-会话](./07-session.md) |
| **工具系统** | 42 工具 + 延迟加载 (ToolSearch) | ~30 工具 + 全量加载 | 中 | [04-工具](./04-tools.md) |
| **命令系统** | 79 命令 + 插件扩展 | ~40 命令 | 中 | [02-命令](./02-commands.md) |
| **安全模型** | 5 层设置 + 沙箱 + 24 种 Hook | 权限规则 + Hook | 中 | [06-设置](./06-settings.md) |
| **多 Agent** | Coordinator/Swarm + Kairos | Arena + Agent Team | 中 | [09-多Agent](./09-multi-agent.md) |
| **会话恢复** | 崩溃检测 + 合成续行 | 无 | 大 | [07-会话](./07-session.md) |
| **记忆系统** | CLAUDE.md + Auto Dream + Team Memory | 简单笔记 | 大 | [07-会话](./07-session.md) |
| **Prompt 缓存** | 静态/动态分区 + 工具 Schema 锁定 | 基础缓存 | 中 | [03-架构](./03-architecture.md) |
| **启动性能** | TCP preconnect + 键盘捕获 | 无优化 | 大 | [03-架构](./03-architecture.md) |
| **终端渲染** | DEC 2026 同步 + 差分渲染 | 标准 Ink | 中 | [11-终端渲染](./11-terminal-rendering.md) |
| **远程控制** | WebSocket/SSE Bridge | 无 | 大 | [08-Remote](./08-remote-control.md) |
| **Speculation** | 预测执行 + Tab 接受 | 已实现但默认关闭 | 小 | [10-Prompt](./10-prompt-suggestions.md) |

## 三、架构概览（开发者视角）

### 3.1 技术栈

| 组件 | Claude Code | 开发者启示 |
|------|-------------|-----------|
| 运行时 | Bun（v2.1.88 前为 Bun 打包的 JS）| Bun 的启动速度和 Node.js 兼容性值得考虑 |
| UI 框架 | Ink (React for CLI) | 与 Qwen Code/Gemini CLI 相同 |
| 构建 | esbuild bundler | 单文件 bundle 减少依赖 |
| 二进制分发 | Node.js SEA → 后改为 Rust 原生 | 原生二进制 = 亚秒启动 + 防反编译 |
| 源码规模 | ~1800 文件，56 个顶层模块 | 远大于 Qwen Code (~500 文件) |

### 3.2 模块结构

```
claude-code/
├─ tools/         43 目录    # 工具系统（Read/Write/Edit/Bash/Agent/...）
├─ services/      36 目录    # 后端服务（compact/MCP/analytics/memory/...）
├─ commands/      101 目录   # 斜杠命令
├─ components/    144 项     # TUI 组件（React/Ink）
├─ hooks/         85 项      # React hooks
├─ tasks/         9 项       # 任务系统（LocalAgent/RemoteAgent/Dream/...）
├─ state/         6 项       # 全局状态管理
├─ bridge/        31 项      # REPL 远程桥接
├─ utils/         大量       # 工具函数
├─ coordinator/   1 项       # 协调器模式（Swarm）
├─ plugins/       2 项       # 插件系统
├─ memdir/        8 项       # 记忆目录/检索
├─ context/       9 项       # 上下文管理
├─ constants/     多项       # 常量 + 系统提示
└─ proactive/     —          # Kairos 主动行为（已 DCE 移除）
```

**开发者启示**：Claude Code 的模块拆分粒度极细——每个工具一个目录、每个命令一个文件。这种结构支持 Feature Flag 的 Dead Code Elimination（DCE），让内部特性（如 Kairos、Proactive）在外部构建中完全不存在。Qwen Code 可以参考这种 Feature Flag + DCE 模式来管理实验性功能。

### 3.3 核心循环

```
用户输入
  │
  ├─ processSlashCommand()    ← 斜杠命令拦截
  │     ↓ (非命令)
  ├─ QueryEngine.run()        ← 核心推理循环
  │     ├─ buildSystemPrompt() ← 动态构建系统提示
  │     ├─ API 请求（流式）
  │     ├─ 流式工具调用解析    ← StreamingToolExecutor
  │     ├─ 工具批次执行
  │     ├─ Mid-Turn Queue Drain ← 工具间检查用户输入
  │     └─ 循环直到模型返回 end_turn
  │
  └─ 上下文压缩检查           ← 5 层压缩策略
```

**与 Qwen Code 的关键差异**：
1. **StreamingToolExecutor**：Claude Code 在 API 流式返回工具调用时就开始解析和准备执行，而非等整个响应完成。这减少了用户等待时间。
2. **Mid-Turn Queue Drain**：工具批次之间检查用户是否有新输入，允许中途注入指令。Qwen Code 的 PR#2854 正在实现此功能。
3. **5 层上下文压缩**：不是简单的"超过 70% 就压缩"，而是从轻量（cache_edits 裁剪）到重量（全量 compact）逐级升级。

## 四、可借鉴 vs 不可复制

### 可借鉴的工程模式（与模型无关）

| 模式 | 核心价值 | 实现复杂度 |
|------|---------|-----------|
| 5 层上下文压缩 | 延长有效会话 3-5 倍 | 中 |
| ToolSearch 延迟加载 | 减少 50%+ 系统提示 token | 小 |
| Fork Subagent + Prompt Cache 共享 | 多 Agent 省 80%+ 费用 | 中 |
| StreamingToolExecutor | 减少工具执行等待 | 中 |
| Mid-Turn Queue Drain | 用户可中途注入指令 | 中 |
| 24 种 Hook 事件 | 企业级可扩展性 | 大 |
| Feature Flag DCE | 安全管理实验性功能 | 小 |
| CLAUDE.md 记忆系统 | 跨会话知识传递 | 中 |
| 崩溃恢复 + 合成续行 | 长任务不丢失 | 大 |
| Prompt Cache 分区（静态/动态） | 缓存命中率最大化 | 中 |

### Anthropic 独有优势（不可复制）

| 优势 | 为什么不可复制 |
|------|---------------|
| Claude 模型能力 | 模型是 Anthropic 核心资产 |
| 100 万 token 上下文 | 依赖 Claude 模型的长上下文能力 |
| Kairos Always-On 模式 | 需要 Anthropic 的 API 配额和推送基础设施 |
| GrowthBook 远程特性开关 | 依赖 Anthropic 的 SaaS 基础设施 |
| 遥测驱动的模型调优 | 需要大规模用户反馈数据 |

## 五、阅读路线推荐

### 如果你想改进上下文管理
→ [07-会话与记忆](./07-session.md)：5 层压缩、Auto Dream、Team Memory

### 如果你想优化工具系统
→ [04-工具系统](./04-tools.md)：ToolSearch 延迟加载、Zod Schema 校验、权限模型

### 如果你想做多 Agent 协作
→ [09-多 Agent 系统](./09-multi-agent.md)：Leader-Worker、Swarm 三后端、Kairos

### 如果你想解决终端闪烁
→ [11-终端渲染](./11-terminal-rendering.md)：DEC 2026 同步输出、差分渲染

### 如果你想加强安全
→ [06-设置与安全](./06-settings.md)：5 层设置、沙箱、Hook 事件

## 六、源码验证

本系列所有技术声明通过以下方式验证：

1. **源码分析**：~1800 文件 TypeScript 反编译分析
2. **二进制分析**：ELF x86-64 二进制的 strings / readelf / 反编译
3. **官方文档**：[code.claude.com/docs](https://code.claude.com/docs/en)
4. **网络搜索**：GitHub Blog、社区分析、第三方拆解文章

原始证据见 [EVIDENCE.md](./EVIDENCE.md)。
