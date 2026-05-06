# Qwen Code Daemon 架构设计（系列文档）

> Qwen Code 引入 HTTP daemon 模式的完整设计方案。基于 [SDK / ACP / Daemon 架构 Deep-Dive](../sdk-acp-daemon-architecture-deep-dive.md) 第七章"Qwen Code 引入 daemon 的工作量评估"展开为可执行的工程蓝图。
>
> 设计目标：**~2-3 周 MVP / ~1.5-2 月对标 OpenCode**，最大化复用 Qwen Code 已有的 ACP / Channels / WebUI / SDK Transport 抽象。

## 文档列表

| # | 文档 | 内容 |
|---|---|---|
| 01 | [架构总览](./01-overview.md) | daemon 模型本质、与 subprocess 模型的对比、与 OpenCode 的设计差异概述 |
| 02 | [现有资产盘点](./02-existing-assets.md) | Qwen Code 中 7 项可复用基础设施 + 复用度评估 |
| 03 | [6 个架构决策](./03-architectural-decisions.md) | session 共享语义、状态进程模型、MCP 生命周期等关键设计选择 |
| 04 | [HTTP API 设计](./04-http-api.md) | 路由结构、请求/响应 schema（复用 ACP zod schema）、WebSocket 事件 |
| 05 | [进程模型与工作目录隔离](./05-process-model.md) | AsyncLocalStorage 上下文传播、子进程 spawn 边界、`process.cwd()` 不变性 |
| 06 | [MCP / FileReadCache / LSP 资源共享](./06-mcp-resources.md) | 跨 session 资源共享策略、生命周期管理 |
| 07 | [权限流与认证](./07-permission-auth.md) | bearer token 鉴权、user permission flow（PR#3723 共享 L3→L4 复用）、跨 client 审批 UX |
| 08 | [3 阶段路线图](./08-roadmap.md) | Stage 1 MVP（~1 周 HTTP-bridge）/ Stage 2 原生（~3 周）/ Stage 3 完整（~2 月）|
| 09 | [与 OpenCode 详细对比](./09-comparison-with-opencode.md) | 路由、技术栈、设计哲学的逐项对照 |
| 10 | [SDK / ACP 协议兼容性](./10-protocol-compatibility.md) | 单进程 vs Daemon 4 层兼容性矩阵 + 双向 RPC 同步→异步处理 + 用户代码 0 改动证明 |

## 一句话 TL;DR

```
Qwen Code 已有 ACP agent 838 行 + Channels 多路由设施 + WebUI 包 + SDK Transport 抽象
                                  ↓
        把 ACP NDJSON 协议通过 HTTP+WebSocket 桥接成 daemon
                                  ↓
              ~2-3 周 MVP，~1.5-2 月对标 OpenCode
```

**核心设计哲学**（与 OpenCode 一致）：
- daemon 内部不再 spawn CLI 子进程；core 通过 import 加载到 daemon 进程内
- 多 session 共享 daemon 进程；用 `AsyncLocalStorage` 做 cwd / context 隔离
- LSP / MCP server / PTY 才是真正的子进程
- session 状态 SQLite 持久化 + 内存 Map cache

**与 OpenCode 不同的地方**：
- **复用 ACP NDJSON schema 作为内部 RPC**（OpenCode 用自定义 OpenAPI schema codegen）
- **Channels 多路由复用**（IM / WebUI / IDE 都走 SessionRouter）—— OpenCode 没有等价物
- **bearer token + PR#3723 共享 L3→L4 权限流**（OpenCode 用单密码）
- **默认跨 client 共享 session（live collaboration 模型）**：CLI + IDE + WebUI + 手机微信同时观察同一会话；任何 client 都可代为审批权限请求；prompt 串行 / 事件 fan-out / 任意 client 取消（OpenCode 是每 SDK call 独立 session）

## 与上游设计文档的关系

本系列是 [SDK / ACP / Daemon 架构 Deep-Dive §七](../sdk-acp-daemon-architecture-deep-dive.md#七qwen-code-引入-daemon-的工作量评估) 的展开。上游文档给出工作量估算 + 6 个架构决策点；本系列把这些决策点逐项展开为**可执行的工程蓝图**：

| 上游决策点 | 本系列对应文档 |
|---|---|
| Session 共享语义 | [03-架构决策](./03-architectural-decisions.md) §1 |
| 状态进程模型 | [05-进程模型](./05-process-model.md) |
| MCP server 生命周期 | [06-MCP/资源共享](./06-mcp-resources.md) |
| FileReadCache 共享 | [06-MCP/资源共享](./06-mcp-resources.md) §2 |
| Permission flow | [07-权限/认证](./07-permission-auth.md) |
| 多 client 并发请求 | [03-架构决策](./03-architectural-decisions.md) §6 |

## 与已合并 PR 的关系

5 月份的几个关键 PR**正在为 daemon 化扫清障碍**——本设计假设它们都已合并：

- **PR#3717** ✓ FileReadCache（session-scoped + `(dev,ino)` key）—— daemon 模式下天然支持跨 client 共享
- **PR#3739** ✓ Background agent resume + transcript-first fork resume —— daemon 重启后 session 可恢复的基础
- **PR#3723** ✓ 共享 L3→L4 permission flow —— Interactive / Non-Interactive / ACP 三模式权限决策合一，daemon 是第 4 种
- **PR#3642** ✓ `/tasks` + managed background shell pool —— 跨 session 任务调度框架
- **PR#3810** ✓ FileReadCache invalidation 5 路径修复 —— 长 session 正确性保障

加上 PR#3739 / PR#3717 提供的 session resume + cache 基础，daemon 化在 5 月初已经具备**全部前置条件**。

> **免责声明**：本系列是 codeagents 项目的设计提案，不代表 Qwen Code 团队官方路线图。所有"工作量估算"是基于源码可见复用度的推测，实际开发可能因团队优先级、API 稳定性要求等变化。
