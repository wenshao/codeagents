# 21. 工具执行运行时——开发者参考

> 当模型一次返回 5 个工具调用时，哪些可以并行？哪些必须串行？并发结果如何排序？长时间工具如何报告进度？工具能修改共享上下文吗？——这些问题属于**工具执行运行时**，不是工具注册。
>
> **Qwen Code 对标**：Qwen Code 的 `CoreToolScheduler` 已实现 Agent 工具并行 + 其他工具串行。但缺少进度消息、上下文修改器合并、并发安全分类。
>
> **致谢**：概念框架参考 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) s02b 章节。

## 一、工具注册 vs 工具执行运行时

| 层 | 关注的问题 | 典型代码 |
|---|-----------|---------|
| **工具注册**（04-tools.md 已覆盖） | Schema 定义、名称映射、权限声明 | `ToolSpec`、`ToolDispatchMap` |
| **工具执行运行时**（本文） | 并发调度、进度报告、结果排序、上下文合并 | `ToolExecutionBatch`、`TrackedTool` |

## 二、核心问题

### 2.1 并发安全分类

不是所有工具都能并行——需要显式分类：

| 分类 | 含义 | 典型工具 |
|------|------|---------|
| **并发安全** | 可与同类工具并行，不破坏共享状态 | `read_file`、`grep`、`glob`、只读 MCP |
| **非并发安全** | 修改共享状态，必须串行 | `write_file`、`edit`、修改应用状态的工具 |
| **上下文修改器** | 不仅返回结果，还修改后续工具的执行环境 | `cd`（改工作目录）、权限工具 |

### 2.2 并发执行模型

Claude Code 的 `StreamingToolExecutor` 将一批工具调用分区后并发执行：

```
模型返回: [read_file(a.ts), read_file(b.ts), edit(c.ts), grep("TODO")]
                                                    │
                                                    ▼
                                              并发安全分区
                                                    │
                                    ┌───────────────┼───────────┐
                                    │               │           │
                              ┌─────▼─────┐   ┌────▼────┐  ┌──▼──┐
                              │ 并行批次 1  │   │串行批次 │  │并行 2│
                              │ read(a.ts) │   │edit(c.ts)│  │grep │
                              │ read(b.ts) │   └────┬────┘  └──┬──┘
                              └─────┬─────┘        │          │
                                    │               │          │
                                    └───────────────┼──────────┘
                                                    │
                                              结果排序（原始顺序）
                                                    │
                                              上下文修改器合并
                                                    │
                                              返回主循环
```

### 2.3 Gemini CLI 的 Wave-based 调度器

Gemini CLI（Qwen Code 上游）在 v0.35 引入了 `scheduler.ts`，采用波次调度：

```
[read, read, write, read]
  → Wave 1: [read, read] 并发执行
  → Wave 2: [write] 串行执行
  → Wave 3: [read] 执行
```

Qwen Code 未 backport 此功能——见 [backport 报告 #40](../comparison/qwen-code-gemini-upstream-report-details.md#item-40)。

### 2.4 进度消息

长时间运行的工具（如 `npm install`、`git clone`）应在执行期间报告进度，而非让用户面对沉默：

```
工具开始 → "正在安装依赖..."
         → "已安装 42/100 个包..."
         → "运行 postinstall 脚本..."
工具完成 → 返回结果
```

### 2.5 结果排序

并行执行的工具可能以任意顺序完成。但返回给模型的结果应保持**原始调用顺序**——否则模型可能困惑。

## 三、Qwen Code 的改进方向

| 改进 | 当前状态 | 建议 | 优先级 |
|------|---------|------|--------|
| 并发安全分类 | Agent 工具并行，其他串行 | 对所有工具标记 `concurrencySafe: boolean` | P2 |
| Wave-based 调度 | 未 backport | 从上游复制 `scheduler.ts` | P2 |
| 进度消息 | 无 | 工具执行超过 3 秒时发射进度事件 | P2 |
| 上下文修改器合并 | 无 | 识别修改 CWD/环境变量的工具，串行执行 | P3 |
