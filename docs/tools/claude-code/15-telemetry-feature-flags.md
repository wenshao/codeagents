# 15. 遥测与 Feature Flag——开发者参考

> Claude Code 的遥测系统有 891+ 个事件、双 sink 架构（Datadog + 1P）、GrowthBook 远程特性开关。Feature Flag 不仅控制功能灰度，还控制遥测采样率和 sink 熔断——形成了一个**可观测性驱动的功能发布体系**。
>
> **Qwen Code 对标**：Qwen Code 有 OpenTelemetry 基础遥测（~40 事件），无远程 Feature Flag。Claude Code 的 GrowthBook 集成（远程灰度、A/B 测试、线上熔断）和隐私保护模式（_PROTO_ key 分级、用户分桶）是主要参考。

## 一、为什么 Code Agent 需要遥测和 Feature Flag

### 问题定义

Code Agent 比普通 CLI 工具复杂得多——它的行为取决于模型、用户输入、项目状态的组合，难以在发布前穷尽测试：

| 场景 | 无遥测 | 有遥测 |
|------|-------|--------|
| 新功能上线后崩溃率上升 | 用户投诉后才知道 | 实时告警，分钟级发现 |
| Prompt Cache 命中率下降 | API 成本莫名上涨 | 看到 `tengu_compact_cache_sharing_fallback` 事件激增 |
| 某个 MCP 服务器频繁超时 | 用户以为是 Agent 卡了 | `tengu_mcp_server_connection_failed` 定位到具体服务器 |
| 新版 Shell 安全检查误判 | 用户被阻止正常操作 | `tengu_tool_use_rejected_in_prompt` 分析误判模式 |

Feature Flag 解决的是**发布风险**——新功能不再是"全量上线或全量回滚"，而是可以按百分比灰度、按用户类型分组、出问题秒级熔断。

### 竞品遥测对比

| Agent | 事件数 | 基础设施 | 远程 Feature Flag | 隐私保护 |
|-------|--------|---------|-------------------|---------|
| **Claude Code** | 891+ | Datadog + 1P BigQuery | ✓ GrowthBook（6h/20m 刷新） | _PROTO_ 分级、用户分桶、MCP 工具名脱敏 |
| **Gemini CLI** | ~50 | Google Cloud（Trace/Monitoring/Logging） | — | 用户选择退出 |
| **Qwen Code** | ~40 | OpenTelemetry + 阿里云/本地 | — | `logPrompts` 开关 |
| **Copilot CLI** | 未公开 | GitHub 内部 | ✓ 通过 GitHub 平台 | 企业级隐私 |

## 二、GrowthBook Feature Flag 系统

### 2.1 架构

```
┌─────────────────────────────────────────────────┐
│  GrowthBook 服务端（Anthropic 托管）             │
│  管理 Feature Flag 值 + A/B 实验配置             │
└────────────────────┬────────────────────────────┘
                     │ HTTPS polling
                     │ 外部用户: 每 6 小时
                     │ 内部用户: 每 20 分钟
                     ▼
┌─────────────────────────────────────────────────┐
│  Claude Code 本地 GrowthBook Client             │
│  ├─ 内存缓存（运行时）                           │
│  ├─ 磁盘缓存（~/.claude/config.json）           │
│  └─ 环境变量覆盖（开发调试用）                    │
└────────────────────┬────────────────────────────┘
                     │ feature('FLAG_NAME')
                     ▼
┌─────────────────────────────────────────────────┐
│  功能代码                                        │
│  if (getGrowthBookFeatureValue('tengu_kairos'))  │
│    → 启用 Kairos 自治模式                        │
└─────────────────────────────────────────────────┘
```

### 2.2 两类 Feature Flag

| 类型 | 评估时机 | 机制 | 用途 |
|------|---------|------|------|
| **编译时 Flag** | `bun:bundle` 构建 | `feature('KAIROS')` → Dead Code Elimination | 内部功能完全不存在于外部构建 |
| **运行时 Flag** | GrowthBook 远程评估 | `getGrowthBookFeatureValue('tengu_kairos')` | 灰度发布、A/B 测试、线上熔断 |

**编译时 Flag 列表**（22 个）：
`KAIROS`、`KAIROS_BRIEF`、`KAIROS_CHANNELS`、`KAIROS_DREAM`、`KAIROS_GITHUB_WEBHOOKS`、`KAIROS_PUSH_NOTIFICATION`、`PROACTIVE`、`CACHED_MICROCOMPACT`、`EXPERIMENTAL_SKILL_SEARCH`、`VERIFICATION_AGENT`、`TOKEN_BUDGET`、`COORDINATOR_MODE`、`BUILDING_CLAUDE_APPS`、`RUN_SKILL_GENERATOR`、`AGENT_TRIGGERS`、`AGENT_TRIGGERS_REMOTE`、`REVIEW_ARTIFACT`、`VOICE_MODE`、`CHICAGO_MCP`、`COWORKER_TYPE_TELEMETRY`、`TRANSCRIPT_CLASSIFIER` 等

**运行时 Flag 示例**：
- `tengu_kairos`：Kairos 自治模式用户级开关
- `tengu_kairos_cron`：Cron 调度器熔断（每 tick 检查）
- `tengu_kairos_cron_config`：Jitter 调优参数
- `tengu_log_datadog_events`：Datadog 事件路由白名单
- `tengu_1p_event_batch_config`：1P 事件批处理配置
- `tengu_event_sampling_config`：事件采样率
- `tengu_frond_boric`：遥测 sink 熔断开关

### 2.3 用户属性（A/B 分组依据）

GrowthBook 根据以下属性进行实验分组：

```typescript
{
  id: userId,
  sessionId,
  deviceID,
  platform,                // darwin/linux/win32
  organizationUUID,
  accountUUID,
  email,
  subscriptionType,        // pro/max/team/enterprise
  rateLimitTier,
  firstTokenTime           // 首次使用时间
}
```

### 2.4 开发者启示

对于 Qwen Code，GrowthBook 的核心价值是**线上熔断**：

```
新功能上线 → 5% 灰度 → 监控遥测 → 无异常 → 扩大到 50%
                                   → 发现问题 → 秒级关闭 Flag → 0% 影响
```

不需要发新版本、不需要用户升级——Feature Flag 远程翻转即可。Qwen Code 当前没有这个能力，所有功能都是"发版即全量"。

## 三、遥测架构

### 3.1 双 Sink 架构

```
logEvent('tengu_tool_use_success', metadata)
  │
  ├─ Event Queue（启动前缓冲）
  │
  ├─ Sink Router
  │     ├─ 检查 kill switch（tengu_frond_boric）
  │     ├─ 检查采样率（tengu_event_sampling_config）
  │     └─ 路由到 sink
  │
  ├─ Sink 1: Datadog
  │     ├─ 白名单过滤（64 个事件）
  │     ├─ _PROTO_ key 剥离（隐私保护）
  │     ├─ MCP 工具名脱敏
  │     └─ 15 秒批量发送（最多 100 条）
  │
  └─ Sink 2: 1P BigQuery
        ├─ 完整 metadata（含 _PROTO_ 字段）
        ├─ OpenTelemetry BatchLogRecordProcessor
        └─ 5 秒批量发送（最多 200 条，8 次指数退避重试）
```

### 3.2 隐私保护机制

| 机制 | 做法 | 保护什么 |
|------|------|---------|
| `_PROTO_*` key 分级 | Datadog 自动剥离，仅 1P BigQuery（特权列）可见 | PII 字段不泄漏到通用日志 |
| MCP 工具名脱敏 | `mcp__github__get_issue` → `"mcp_tool"` | 用户使用的 MCP 服务器名不泄漏 |
| 用户分桶 | SHA256(userId) → 30 个桶 | 唯一用户计数但不追踪个体 |
| 文件扩展名截断 | 超过 10 字符的扩展名替换为 `"other"` | 防止 hash 文件名泄漏 |
| 工具输入截断 | 字符串最长 512 字符，JSON 最大 4KB | 代码内容不进入遥测 |
| 类型系统强制 | `AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` | 编译时防止代码/路径进入 metadata |

### 3.3 Datadog 集成

- **端点**：`https://http-intake.logs.us5.datadoghq.com/api/v2/logs`
- **白名单**：64 个事件（API/OAuth/工具/会话/语音/团队记忆相关）
- **标签字段**：arch、model、platform、subscriptionType、toolName、userType、version 等 16 个
- **Feature Gate**：`tengu_log_datadog_events` 控制路由

## 四、891+ 遥测事件分类

| 类别 | 事件数 | 示例 |
|------|--------|------|
| API & 查询 | 30+ | `tengu_api_error`、`tengu_api_retry`、`tengu_api_529_background_dropped` |
| OAuth & 认证 | 30+ | `tengu_oauth_token_refresh_success`、`tengu_oauth_flow_start` |
| 工具执行 | 50+ | `tengu_tool_use_success`、`tengu_bash_tool_command_executed` |
| MCP | 50+ | `tengu_mcp_server_connection_failed`、`tengu_mcp_tool_call_auth_error` |
| 会话 & 启动 | 20+ | `tengu_init`、`tengu_started`、`tengu_exit`、`tengu_startup_perf` |
| 记忆 & 上下文 | 40+ | `tengu_memdir_loaded`、`tengu_compact`、`tengu_compact_failed` |
| 压缩 | 30+ | `tengu_compact_cache_sharing_success`、`tengu_partial_compact` |
| Bridge & 远程 | 80+ | `tengu_bridge_started`、`tengu_bridge_session_done` |
| Skill & 插件 | 50+ | `tengu_skill_loaded`、`tengu_plugin_installed` |
| 权限 | 30+ | `tengu_auto_mode_decision`、`tengu_auto_mode_denial_limit_exceeded` |
| 文件操作 | 30+ | `tengu_file_operation`、`tengu_binary_content_persisted` |
| 模型 & 配置 | 40+ | `tengu_config_model_changed`、`tengu_fast_mode_toggled` |

## 五、Qwen Code 改进建议

### P1：远程 Feature Flag

引入 Feature Flag 服务（GrowthBook 是开源的，也可以用 LaunchDarkly 或自建）。核心收益：

1. **灰度发布**：新功能按 5% → 20% → 50% → 100% 逐步放量
2. **线上熔断**：出问题时秒级关闭 Flag，无需发新版本
3. **A/B 测试**：对比不同 prompt/策略的效果

### P2：遥测事件扩展

当前 ~40 个事件覆盖基本操作。建议增加：
- API 缓存命中率事件（优化 Prompt Cache）
- 工具执行耗时事件（识别慢工具）
- 权限决策事件（分析权限模式使用模式）
- 崩溃/异常事件（主动发现问题）

### P3：隐私保护增强

参考 Claude Code 的类型系统强制（`AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS`）——通过编译时检查确保代码内容不进入遥测数据。
