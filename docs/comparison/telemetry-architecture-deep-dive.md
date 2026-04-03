# 遥测 (Telemetry) 架构 Deep-Dive

> AI Agent 收集什么数据、如何上报、用户如何控制？本文基于 Claude Code（v2.1.89 源码分析）和 Qwen Code（v0.15.0 开源）的源码分析，对比两者在遥测 (Telemetry) 架构、事件体系和隐私控制方面的差异。

---

## 1. 架构总览

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **遥测框架** | 自定义 1P Logger + OpenTelemetry | QwenLogger（RUM）+ OpenTelemetry |
| **上报端点** | Anthropic 内部 API + Datadog | 阿里云 RUM + OTLP（可配置） |
| **事件数量** | ~656 个 `tengu_*` 事件 | ~50 个事件类型 |
| **采样策略** | 按事件类型动态采样（GrowthBook） | 批量刷新（1,000 条 / 60 秒） |
| **调试追踪** | Perfetto（Chrome Trace，ant-only） | 标准 OTLP Span |
| **PII 保护** | 元数据禁止原始字符串 | 选择性 prompt 日志控制 |
| **禁用方式** | `DISABLE_TELEMETRY=true` | `QWEN_TELEMETRY_ENABLED=false` |

---

## 2. Claude Code：双通道遥测

### 2.1 事件日志通道（1P Event Logging）

```typescript
// 源码: services/analytics/firstPartyEventLogger.ts
// 使用 @opentelemetry/sdk-logs 的 LoggerProvider + BatchLogRecordProcessor
// 自定义 Exporter: FirstPartyEventLoggingExporter
// 端点: ${BASE_API_URL}/api/event_logging/batch
// 批量配置通过 GrowthBook 动态控制（tengu_1p_event_batch_config）
```

**事件类型**（~656 个唯一 `tengu_*` 前缀，源码 `grep -roh` 统计；含动态构造事件名时约 782 个）：

| 类别 | 示例 |
|------|------|
| Agent 生命周期 | `tengu_agent_created`, `tengu_agent_tool_selected`, `tengu_agent_tool_completed` |
| API 交互 | `tengu_api`, `tengu_api_error`, `tengu_api_cache_breakpoints` |
| 工具执行 | `tengu_tool_*`, `tengu_streaming_tool_execution_used` |
| 会话管理 | `tengu_session_*`, `tengu_compact_*` |
| Feature Flag | `tengu_amber_flint`, `tengu_amber_prism` |
| 安全 | `tengu_cancel`, `tengu_pre_stop_hooks_cancelled` |
| UI | `tengu_brief_mode_toggled`, `tengu_conversation_forked` |

**PII 保护**：

```typescript
// 源码: services/analytics/index.ts
// 元数据类型标注: AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
// → 开发者必须显式声明元数据不含代码或文件路径
// → 类型系统阻止意外记录敏感信息
```

### 2.2 Perfetto 调试追踪（ant-only）

```typescript
// 源码: utils/telemetry/perfettoTracing.ts
// 格式: Chrome Trace Event (JSON)，在 ui.perfetto.dev 或 chrome://tracing 查看
// 启用: CLAUDE_CODE_PERFETTO_TRACE=1 或 CLAUDE_CODE_PERFETTO_TRACE=<path>
// 输出: ~/.claude/traces/trace-<session-id>.json
// 事件上限: 100K 条（超出时淘汰最老的 50%，约 30MB）
```

**Perfetto 追踪捕获**：

| 捕获内容 | 详情 |
|----------|------|
| Agent 层级 | 父子 swarm 关系 |
| API 请求 | TTFT、TTLT、prompt 长度、cache 统计 |
| 工具执行 | 名称、耗时、token 用量 |
| 用户等待 | 输入等待时间 |
| Speculation | 推测执行标记 |

### 2.3 采样 (Sampling) 与降级 (Fallback)

```typescript
// 按事件采样 (Sampling): GrowthBook tengu_event_sampling_config（每事件 0-1 概率）
// 第三方 Provider: 自动禁用分析（Bedrock/Vertex/Foundry）
// 测试环境: NODE_ENV === 'test' 时禁用
// 隐私模式: isTelemetryDisabled() 检查
```

---

## 3. Qwen Code：RUM + OTLP 双通道

### 3.1 QwenLogger（RUM 通道）

```typescript
// 源码: qwen-code/packages/core/src/telemetry/qwen-logger/qwen-logger.ts
// 类型: 单例 RUM (Real User Monitoring) Logger
// 端点: gb4w8c3ygj-default-sea.rum.aliyuncs.com（阿里云 RUM）
// 批量: 默认 1,000 条 / 60 秒刷新
// 队列: FixedDeque（溢出时丢弃最老事件）
```

**事件类型**（~50 种）：

| 类别 | 事件 |
|------|------|
| 会话 | `session_start`, `session_end` |
| 用户操作 | `new_prompt`, `retry`, `slash_command`, `user_feedback` |
| 工具 | `tool_call#<name>`, `file_operation#<name>`, `tool_output_truncated` |
| API | `api_request`, `api_response`, `api_cancel`, `api_error` |
| 错误 | `invalid_chunk`, `malformed_json_response`, `loop_detected` |
| 扩展 | `extension_install`, `extension_uninstall`, `extension_update` |
| Arena | `arena_session_started`, `arena_agent_completed` |
| Hook | `hook_call#<event_name>` |
| 压缩 | `chat_compression` |

### 3.2 OpenTelemetry 通道

```typescript
// 源码: qwen-code/packages/core/src/telemetry/sdk.ts
// 4 种 Exporter（可配置）:
// 1. OTLP gRPC   — OTLPTraceExporter + GZIP 压缩
// 2. OTLP HTTP   — OTLPTraceExporter[Http]
// 3. File        — FileSpanExporter（本地文件）
// 4. Console     — ConsoleSpanExporter（开发调试）
//
// Processor: BatchSpanProcessor, BatchLogRecordProcessor
// 检测: HttpInstrumentation（HTTP 请求自动追踪）
```

**遥测目标**：

| 目标 | 用途 |
|------|------|
| `TelemetryTarget.LOCAL` | 本地 OTEL Collector |
| `TelemetryTarget.GCP` | Google Cloud |
| `TelemetryTarget.QWEN` | 通义千问内部 |

### 3.3 RUM 事件协议

```typescript
// 源码: qwen-code/packages/core/src/telemetry/qwen-logger/event-types.ts
// RUM 事件层级:
// RumViewEvent     — 页面/视图导航
// RumActionEvent   — 用户交互
// RumResourceEvent — API/网络调用
// RumExceptionEvent — 错误
// 每类含 snapshot (JSON 序列化详细指标)
```

---

## 4. 隐私控制对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **全局禁用** | `DISABLE_TELEMETRY=true` | `QWEN_TELEMETRY_ENABLED=false` |
| **非必要流量** | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true` | — |
| **Prompt 日志** | 禁止（类型系统强制） | `telemetryLogPromptsEnabled()` 控制 |
| **3P Provider** | 自动禁用分析 | — |
| **MDM 控制** | ✅ 策略可关闭遥测 | ❌ |
| **采样** | 按事件动态（GrowthBook） | 全量批刷 |

---

## 5. 关键源码文件

### Claude Code

| 文件 | 职责 |
|------|------|
| `services/analytics/index.ts` | `logEvent()` 中央入口 + 队列 |
| `services/analytics/firstPartyEventLogger.ts` | 1P 事件日志（OTLP LoggerProvider） |
| `services/analytics/growthbook.ts` | Feature Flag + 采样配置 |
| `services/analytics/config.ts` | 禁用条件判断 |
| `utils/telemetry/perfettoTracing.ts` | Perfetto Chrome Trace |

### Qwen Code

| 文件 | 职责 |
|------|------|
| `packages/core/src/telemetry/qwen-logger/qwen-logger.ts` | RUM Logger 单例 |
| `packages/core/src/telemetry/qwen-logger/event-types.ts` | RUM 事件协议 |
| `packages/core/src/telemetry/sdk.ts` | OTLP Exporter 配置 |
| `packages/core/src/telemetry/config.ts` | 隐私控制 + 目标选择 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。
