# 20. 查询状态转换模型——开发者参考

> 为什么 Agent 的核心循环不是简单的"循环直到 end_turn"？因为一个 query 可以因为**6 种完全不同的原因**继续到下一轮，每种原因需要不同的处理。本文分析 Claude Code 的查询转换模型。
>
> **Qwen Code 对标**：Qwen Code 的循环也有类似逻辑（工具完成→继续、token 截断→继续），但没有显式的 TransitionReason 类型——导致日志不可读、测试不精确。
>
> **致谢**：概念框架参考 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) s00c 章节。

## 一、为什么需要显式的转换原因

### 问题定义

一个 query（用户输入→Agent 处理→输出）可能跨多个 turn。每个 turn 结束后，系统需要决定"是否继续"。

但"继续"不是一个原因，而是**一族原因**：

| 转换原因 | 含义 | 处理方式 |
|---------|------|---------|
| `tool_result` | 工具执行完毕，模型需要结果 | 将结果注入消息，继续推理 |
| `max_tokens` | 输出 token 达到上限，被截断 | 让模型继续未完成的输出 |
| `compaction` | 上下文被压缩，需要重新对齐 | 注入压缩摘要，重试当前轮 |
| `retry` | 传输层失败，退避后重试 | 重发同一请求（可能换模型） |
| `stop_hook` | Stop Hook 说"还不该结束" | 注入 Hook 反馈，继续 |
| `budget` | 预算策略允许继续 | 正常继续 |

如果把这些都折叠为 `continue`，三个问题会迅速恶化：

1. **日志不可读**：看不出是"工具完成后继续"还是"重试后继续"
2. **测试不精确**：无法断言"这次继续是因为压缩"
3. **开发者心智模型模糊**：调试时不知道循环为什么没停

### Claude Code 的解决方案

每次跨轮时携带显式的 `TransitionReason`：

```
Turn N 结束
  │
  ├─ 评估转换原因
  │     ├─ tool_use_result → TransitionReason.TOOL_RESULT
  │     ├─ max_tokens hit → TransitionReason.MAX_TOKENS
  │     ├─ compact triggered → TransitionReason.COMPACTION
  │     ├─ transport error → TransitionReason.RETRY
  │     ├─ stop hook reject → TransitionReason.STOP_HOOK
  │     └─ budget allows → TransitionReason.BUDGET
  │
  └─ Turn N+1 根据原因调整行为
        ├─ TOOL_RESULT → 注入工具结果到消息
        ├─ MAX_TOKENS → 让模型续写
        ├─ COMPACTION → 注入摘要 + 重新构建系统提示
        ├─ RETRY → 退避延迟 + 可能降级模型
        └─ STOP_HOOK → 注入 Hook 反馈
```

## 二、状态转换图

```
                    ┌──────────────────────────┐
                    │     IDLE（等待输入）       │
                    └────────────┬─────────────┘
                                 │ 用户输入
                                 ▼
                    ┌──────────────────────────┐
                    │   QUERYING（API 请求中）   │◄──────────────┐
                    └────────────┬─────────────┘               │
                                 │ 流式响应                     │
                                 ▼                             │
                    ┌──────────────────────────┐               │
                    │  PROCESSING（处理响应）    │               │
                    └────────────┬─────────────┘               │
                                 │                             │
                    ┌────────────┼─────────────┐               │
                    │            │             │               │
                    ▼            ▼             ▼               │
              ┌──────────┐ ┌─────────┐ ┌───────────┐          │
              │ end_turn │ │tool_use │ │max_tokens │          │
              │ → IDLE   │ │→ EXEC   │ │→ CONTINUE │          │
              └──────────┘ └────┬────┘ └─────┬─────┘          │
                                │             │                │
                                ▼             │                │
                    ┌──────────────────┐      │                │
                    │ TOOL_EXECUTING   │      │                │
                    │ (权限→Hook→执行)  │      │                │
                    └────────┬─────────┘      │                │
                             │ 完成           │                │
                             ▼                ▼                │
                    ┌──────────────────────────────┐           │
                    │ TRANSITION                    │           │
                    │ reason = TOOL_RESULT          │───────────┘
                    │       | MAX_TOKENS            │
                    │       | COMPACTION            │
                    │       | RETRY                 │
                    │       | STOP_HOOK             │
                    └──────────────────────────────┘
```

## 三、Qwen Code 的改进方向

Qwen Code 的 `CoreToolScheduler` 和 `client.ts` 中有类似的循环逻辑，但转换原因是隐式的（通过 if-else 分支判断），没有显式的 `TransitionReason` 类型。

**建议**：

```typescript
// 新增 TransitionReason 枚举
enum TransitionReason {
  TOOL_RESULT = 'tool_result',
  MAX_TOKENS = 'max_tokens',
  COMPACTION = 'compaction',
  RETRY = 'retry',
  STOP_HOOK = 'stop_hook',
  BUDGET = 'budget',
}

// 每次跨轮时记录原因
interface QueryTransition {
  reason: TransitionReason;
  metadata: Record<string, unknown>; // 原因特定数据
  timestamp: number;
}
```

**收益**：日志可读性 + 测试精确性 + 调试效率。实现成本极低（~50 行枚举 + 日志改动）。
