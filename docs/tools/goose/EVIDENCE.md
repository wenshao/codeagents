# Goose 源码深度分析证据

## 基本信息
- 仓库: block/goose, Apache-2.0, Rust, 33k+ stars
- 架构: MCP 原生（所有工具通过 MCP 协议）
- SDK: rmcp (Rust MCP SDK)
- 已捐赠给 Linux Foundation Agentic AI Foundation (AAIF)

## 遥测系统（源码: crates/goose-cli/src/posthog.rs）

### PostHog
- API key: `phc_RyX5CaY01VtZJCQyhSR5KFh6qimUy81YwxsEpotAftT`
- 端点: `https://us.i.posthog.com/capture/`
- **默认关闭（opt-in）**

### Machine ID
- 生成: `Uuid::new_v4()` 持久化到 `telemetry_installation.json`
- 用作 PostHog distinct_id

### 采集数据（session_started 事件）
- os, arch, version, platform_version
- install_method (homebrew/cargo/desktop/binary)
- interface (CLI/desktop)
- provider, model
- extensions_count, extensions (名称列表)
- session_number, total_sessions, total_tokens
- db_schema_version

### 隐私保护
- 错误消息清洗: 用户路径/API keys/emails/bearer tokens/UUIDs → [REDACTED]
- 属性过滤: key/token/secret/password/credential 键自动移除
- 仅 session_started 和 onboarding_* 事件活跃（error/custom 已禁用）

### Opt-out
- `GOOSE_TELEMETRY_OFF=1` 环境变量
- `GOOSE_TELEMETRY_ENABLED=false` 配置
- Onboarding 事件绕过 opt-in（追踪漏斗）

## 安全系统

### SecurityManager + AdversaryInspector
- 提示注入检测: 模式匹配 + 可选 ML 分类器
- classification_client.rs: 调用 HuggingFace 兼容 ML 端点
- adversary_inspector.rs: LLM 审查使用 ~/.config/goose/adversary.md 规则
- 置信度阈值: 超过则触发用户确认

### RepetitionInspector
- tool_monitor.rs: 检测重复相同工具调用
- 防止无限循环

### SecurityPatterns + Scanner
- security/patterns.rs: 预定义注入模式
- security/scanner.rs: 模式扫描引擎
- 配置: SECURITY_PROMPT_ENABLED, SECURITY_PROMPT_CLASSIFIER_ENABLED, SECURITY_COMMAND_CLASSIFIER_ENABLED

### 权限系统
- 4 种模式: Auto, Approve, SmartApprove (默认), Chat
- 31 个危险环境变量阻止列表
- AllowOnce/AlwaysAllow/NeverAllow 每工具

## OpenTelemetry
- 完整 OTLP: traces + metrics + logs
- 通过标准 OTEL_* 环境变量配置
- 默认禁用（需配置端点）

## Langfuse（可选 LLM 可观测）
- LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY
- 每 5 秒批量发送 trace 数据
- 默认禁用

## MCP 原生架构
- Host → Client → Server 模型
- 传输: Stdio (本地), StreamableHttp (远程), Builtin (进程内)
- 扩展暴露: Tools (可执行函数), Resources (URI 数据), Prompts (模板)
- 配置: ~/.config/goose/config.yaml
- 安装: CLI, Desktop UI, 深链 (goose://extension?cmd=...)

## Recipe 系统
- YAML 定义的任务模板
- goose run recipe.yaml 执行
- 支持变量替换和条件步骤

来源: GitHub 源码 crates/goose/src/, crates/goose-cli/src/ (Rust)
