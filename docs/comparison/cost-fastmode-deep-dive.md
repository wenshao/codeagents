# 成本追踪与 Fast Mode Deep-Dive

> 用户如何了解 AI Agent 的实际花费？能否在速度和成本之间灵活切换？本文基于 Claude Code（v2.1.89 源码分析）和 Qwen Code（v0.15.0 开源）的源码分析，对比两者在成本追踪、Fast Mode 速度分级和并发会话管理方面的差异。

---

## 1. 架构总览

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **成本显示** | USD 金额 + 按模型分项 + cache 效率 | Token 计数 + 请求数 + cache 效率百分比 |
| **成本持久化** | 按 session ID 存储在项目配置中 | 无持久化 |
| **Fast Mode** | ✅ Opus 4.6 标准/快速切换（$5→$30/Mtok） | ❌（仅 `--fast` 指定备用模型） |
| **并发 Session** | ✅ PID 文件追踪 + 后台 Agent 脱附 | 无跨终端追踪 |

---

## 2. Claude Code：USD 成本追踪

### 2.1 成本累计

```typescript
// 源码: cost-tracker.ts
// 每次 API 响应后调用:
addToTotalSessionCost(model, usage)
  → calculateUSDCost(model, usage)     // 按定价表计算 USD
  → addToTotalModelUsage(model, usage)  // 按模型分项累计
  → getCostCounter().add(cost)          // OpenTelemetry 指标
```

### 2.2 /cost 命令输出

```
Total cost:            $1.25
Total duration (API):  2m 45s
Total duration (wall): 5m 30s
Total code changes:    25 lines added, 8 lines removed

Usage by model:
  Opus 4.6:    100,000 input, 45,000 output, 5,000 cache read, 2,500 cache write ($0.95)
  Sonnet 4.6:  50,000 input, 12,000 output ($0.30)
```

**关键信息**：
- USD 金额精确到分
- Cache read / write tokens 分开显示——用户可判断 prompt cache 效率
- 按模型分项——用户可识别哪个模型消耗最多
- API 时间 vs 总时间——区分网络延迟和工具执行时间

### 2.3 会话成本持久化

```typescript
// 源码: cost-tracker.ts
// 保存到项目配置:
saveCurrentSessionCosts() → config.projects[projectPath] = {
  lastSessionId, lastCost, lastAPIDuration, lastModelUsage, lastLinesChanged
}
// --resume 恢复时:
restoreCostStateForSession() → 检查 sessionId 匹配后恢复累积成本
```

### 2.4 Fast Mode

```typescript
// 源码: utils/fastMode.ts
// 切换: /fast 命令 或 设置 fastMode: true
// 定价: Opus 4.6 Standard $5/$25 → Fast $30/$150 per Mtok

// 冷却机制:
type FastModeState =
  | { status: 'active' }
  | { status: 'cooldown'; resetAt: number; reason: 'rate_limit' | 'overloaded' }

// 429 错误 → triggerFastModeCooldown(resetTimestamp, reason)
// 冷却结束 → 自动恢复 active
```

**与重试集成**（源码: `services/api/withRetry.ts`）：
- 短 `retry-after`（<20s）：保持 Fast Mode 重试（保留 cache）
- 长 `retry-after`：进入冷却，回退到 Standard
- Overage rejection：永久禁用 Fast Mode

### 2.5 并发 Session 管理

```typescript
// 源码: utils/concurrentSessions.ts
// PID 文件: ~/.claude/sessions/{pid}.json
{
  pid: 12345,
  sessionId: "abc-123",
  cwd: "/path/to/project",
  kind: "interactive" | "bg" | "daemon" | "daemon-worker",
  name: "background-session-name",
  startedAt: 1704067200000
}
// countConcurrentSessions() — 扫描 PID 文件，过滤已退出进程
// 自动清理: registerCleanup() 在退出时删除 PID 文件
```

---

## 3. Qwen Code：Token 统计

### 3.1 /stats 命令

```typescript
// 源码: qwen-code/packages/cli/src/ui/components/StatsDisplay.tsx
// 显示内容:
// - Session ID、工具调用（成功/失败）、成功率
// - Wall time、Agent 活跃时间、API 时间占比
// - 按模型分项: 模型名、请求数、输入/输出 tokens
// - Cache 效率: "{cacheEfficiency.toFixed(1)}% of input from cache"
```

### 3.2 无 USD 成本计算

Qwen Code 的 `/stats` 显示 token 数量和 cache 效率百分比，但**不计算 USD 金额**——因为支持多 Provider（Google/Qwen/Anthropic/OpenAI），定价差异大，难以统一计算。

### 3.3 /model --fast

```typescript
// 源码: qwen-code/packages/cli/src/ui/commands/modelCommand.ts
// /model --fast <modelName> → 设置后台任务的备用快速模型
// 与 Claude Code 的 Fast Mode 不同：
// - Claude: 同一模型的不同推理速度（相同 Opus 4.6，不同 QPS/价格）
// - Qwen: 指定另一个更快的模型（如用 Haiku 替代 Opus）
```

---

## 4. 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 成本单位 | **USD 金额** | Token 数量 |
| 按模型分项 | ✅ 含 cache read/write 分项 | ✅ 含 cache 效率百分比 |
| 成本持久化 | ✅ 跨 `--resume` 累加 | ❌ |
| Fast Mode | ✅ 同模型速度切换 + 冷却 + 重试集成 | ⚠️ `--fast` 指定备用模型（非速度分级） |
| 并发追踪 | ✅ PID 文件 + 后台脱附 | ❌ |
| 代码变更统计 | ✅ lines added/removed | ❌ |

---

## 5. 关键源码文件

### Claude Code

| 文件 | 职责 |
|------|------|
| `cost-tracker.ts` | 成本累计、持久化、/cost 格式化 |
| `utils/modelCost.ts` | 定价表（7 个价格档） |
| `utils/fastMode.ts` | Fast Mode 状态机 + 冷却 |
| `commands/fast/fast.tsx` | /fast 命令 UI |
| `commands/cost/cost.ts` | /cost 命令 |
| `utils/concurrentSessions.ts` | PID 追踪 + 并发计数 |

### Qwen Code

| 文件 | 职责 |
|------|------|
| `packages/cli/src/ui/components/StatsDisplay.tsx` | 统计 UI |
| `packages/cli/src/ui/commands/statsCommand.ts` | /stats 命令 |
| `packages/cli/src/ui/commands/modelCommand.ts` | /model --fast |
| `packages/core/src/telemetry/metrics.ts` | OpenTelemetry 指标 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。
