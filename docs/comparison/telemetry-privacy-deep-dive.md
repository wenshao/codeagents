# 37. 遥测与隐私实现深度对比

> 遥测数据采集是 AI 编程代理最敏感的话题。从"零遥测"到"782 个事件类型 + 硬件指纹 + Machine ID"，各工具的隐私立场差异巨大。

## 隐私等级总览

| 等级 | 工具 | 默认状态 | Machine ID | 硬件采集 | 事件规模 |
|------|------|---------|-----------|---------|---------|
| **A（零遥测）** | **Kimi CLI** | N/A | ✗ | ✗ | 0 |
| **A（零遥测）** | **OpenCode** | N/A | ✗ | ✗ | 0 |
| **B（Opt-in）** | **Aider** | 关闭 | ✗（随机 UUID） | OS/架构 | 少量 |
| **B（Opt-in）** | **Goose** | 关闭 | ✗（随机 UUID） | OS/架构 | 少量 |
| **C（默认开启）** | **Claude Code** | **开启** | **✓** | CPU/hostname | **782 事件** |
| **C（默认开启）** | **Gemini CLI** | **开启** | **✓** | CPU/GPU/RAM | **194 键** |
| **C（默认开启）** | **Qwen Code** | **开启** | ✓（继承） | 继承 | 40+ RUM |
| **D（不透明）** | **Copilot CLI** | **开启** | 未确认 | 平台信息 | 未公开 |
| **D（不透明）** | **Codex CLI** | **开启** | 未确认 | 平台信息 | 未公开 |
| **D（不透明）** | **Qoder CLI** | **开启** | ✓（getMachineKey） | 未确认 | 未公开 |

---

## 一、Claude Code：782 事件 + Machine ID（采集最广）

> 来源：EVIDENCE.md（二进制反编译 v2.1.81）

### 遥测端点

| 端点 | 用途 |
|------|------|
| `api.anthropic.com/api/claude_code/metrics` | 主遥测 |
| `http-intake.logs.us5.datadoghq.com/api/v` | Datadog 日志（US5） |
| `api.segment.io` | Segment 分析 |
| `api.anthropic.com/api/claude_code/organizations/metrics_enabled` | 组织遥测开关 |

### Machine ID 采集方式

| 平台 | 方法 |
|------|------|
| **macOS** | `ioreg -rd1 -c IOPlatformExpertDevice` → `IOPlatformUUID` |
| **Linux** | `/etc/machine-id`（主）→ `/var/lib/dbus/machine-id`（备） |
| **Windows** | `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography\MachineGuid` |
| **FreeBSD** | `/etc/hostid` 或 `kenv -q smbios.system.uuid` |

### 782 事件类型 + 功能标志

`tengu_` 前缀事件覆盖所有代理行为：

| 事件类别 | 示例 | 说明 |
|---------|------|------|
| `tengu_agent_*` | agent_start, agent_stop | 代理生命周期 |
| `tengu_api_*` | api_call, api_error, **api_opus_fallback_triggered** | API 调用与 fallback |
| `tengu_auto_mode_*` | auto_mode_start | 自动模式 |
| `tengu_session_*` | session_start, session_end | 会话管理 |
| `tengu_tool_*` | tool_use, tool_result | 工具使用追踪 |
| `tengu_dynamic_skills_changed` | — | 技能激活/停用 |
| `tengu_compact_*` | compact_start, compact_end | 压缩操作 |

**功能标志（Feature Flags，从二进制提取）**：

```
tengu_defer_all_bn4        — 延迟工具加载（ToolSearch）
tengu_defer_caveat_m9k     — 延迟工具提示消息
tengu_turtle_carbon        — Ultrathink 模式（扩展思维）
tengu_marble_anvil         — Thinking Edits（思考中编辑建议）
tengu_hawthorn_steeple     — 内容去重
tengu_hawthorn_window      — 去重窗口大小配置
```

### 发送的数据字段

```json
{
  "accountUuid": "...",           // Anthropic 账号 ID
  "organizationUuid": "...",      // 组织 ID
  "userType": "external",         // 用户类型
  "subscriptionType": "pro",      // 订阅层级
  "rateLimitTier": "tier_1",      // 速率限制层级
  "platform": "darwin-arm64",     // 平台信息（oOH() 函数）
  "firstTokenTime": 1234,         // 首 token 延迟（ms）
  // CI 环境额外字段：
  "githubActionsMetadata": {
    "GITHUB_ACTOR": "...",
    "GITHUB_REPOSITORY": "org/repo",
    "GITHUB_REPOSITORY_OWNER": "org"
  }
}
```

### 禁用方式

```bash
export DISABLE_TELEMETRY=true
# 或
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true
```

---

## 二、Gemini CLI：194 键 + 完整硬件画像

> 来源：EVIDENCE.md（源码分析）

### 遥测端点

```
play.googleapis.com/log?format=json&hasfast=true
```

Google Clearcut 分析：Console=GEMINI_CLI, Source=CONCORD
- 缓冲区：1000 事件
- 刷新间隔：60 秒
- 最大重试：100 次

### 硬件采集（systeminformation 库）

| 采集项 | 详情 |
|--------|------|
| CPU | 型号 + 核心数 |
| **GPU** | 型号（独有） |
| **RAM** | 总量 GB |
| OS | 平台/版本 |
| Node.js | 版本号 |
| Docker | 是否在容器中 |

### 用户追踪

- 当前 Google 账号邮箱
- 历史账号列表
- 生命周期账号计数

### 环境变量保护（模式匹配）

```
始终阻止：*TOKEN*, *SECRET*, *PASSWORD*, *KEY*, *AUTH*, *CREDENTIAL*, *PRIVATE*, *CERT*
显式阻止：CLIENT_ID, DB_URI, CONNECTION_STRING
```

### 禁用方式

```bash
export GEMINI_TELEMETRY_ENABLED=false
```

---

## 三、Qwen Code：Aliyun RUM 替换 Clearcut

> 来源：EVIDENCE.md（源码分析）

### 关键变化：分叉后遥测重建

| 组件 | Gemini CLI（上游） | Qwen Code（分叉） |
|------|-------------------|-------------------|
| 主遥测 | Google Clearcut | **Aliyun RUM** |
| 端点 | `play.googleapis.com` | `gb4w8c3ygj-*.rum.aliyuncs.com` |
| App ID | — | `gb4w8c3ygj@851d5d500f08f92` |
| OTLP | 可配置 | 继承 |

### Aliyun RUM 事件类型

`RumViewEvent`、`RumActionEvent`、`RumExceptionEvent`、`RumResourceEvent`
- 40+ 事件：session、prompts、tool calls、API、arena、auth、subagent、skills

### 禁用方式

```bash
export QWEN_TELEMETRY_ENABLED=false
```

---

## 四、Aider：Opt-in 10% 采样（最克制）

> 来源：EVIDENCE.md（源码分析）

### PostHog 分析

```python
# 10% 采样：仅 UUID 前 6 位 hex < 10% 的用户被提示
PERCENT = 10
ph.capture(distinct_id=random_uuid, event=event, properties=super_properties)
```

### 采集内容

- Python 版本、OS 平台、架构
- Aider 版本
- 模型名称（未知模型自动脱敏为 `provider/REDACTED`）

### 不采集

- MAC 地址、hostname、IP
- 文件内容、Git 数据、环境变量

### 禁用方式

```bash
aider --analytics false
# 或在配置中
permanently_disable: true
```

---

## 五、Goose：Opt-in + 错误脱敏

> 来源：EVIDENCE.md（源码分析）

### PostHog + 隐私保护

```rust
// 自动脱敏：用户路径、API 密钥、邮箱、Bearer token、UUID → [REDACTED]
// 属性过滤：自动移除 key/token/secret/password/credential 键
```

### 禁用方式

```bash
export GOOSE_TELEMETRY_OFF=1
```

---

## 六、零遥测工具

### Kimi CLI

递归搜索零结果——无 PostHog、Sentry、Mixpanel 或任何分析 SDK。`metadata.py` 仅用 MD5(工作目录路径) 做本地会话命名。

### OpenCode

递归搜索零结果——无分析 SDK、无报告端点。

---

## 禁用方式速查

| Agent | 环境变量 |
|------|---------|
| Claude Code | `DISABLE_TELEMETRY=true` |
| Gemini CLI | `GEMINI_TELEMETRY_ENABLED=false` |
| Qwen Code | `QWEN_TELEMETRY_ENABLED=false` |
| Aider | `--analytics false` 或 `permanently_disable: true` |
| Goose | `GOOSE_TELEMETRY_OFF=1` |
| Copilot CLI | 未公开 |
| Codex CLI | 未公开 |
| Kimi CLI | 无需（零遥测） |
| OpenCode | 无需（零遥测） |

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | EVIDENCE.md（259-309 行） | 二进制反编译 |
| Gemini CLI | EVIDENCE.md（遥测章节） | 开源 |
| Qwen Code | EVIDENCE.md（RUM 配置） | 开源 |
| Aider | EVIDENCE.md（PostHog API key） | 开源 |
| Goose | EVIDENCE.md（PostHog 脱敏） | 开源 |
| Kimi CLI | EVIDENCE.md（零遥测确认） | 开源 |
| OpenCode | EVIDENCE.md（零遥测确认） | 开源 |
| 综合对比 | privacy-telemetry.md | 跨 Agent 对比文档 |
