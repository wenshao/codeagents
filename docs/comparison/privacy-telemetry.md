# 3. 隐私与遥测对比

> 各 CLI Agent 的数据采集、安全监控和隐私控制对比。基于源码分析和二进制反编译。

## 遥测系统对比

| 工具 | 遥测提供商 | 默认状态 | 采集 Machine ID | 采集硬件信息 | 采集 MAC 地址 |
|------|-----------|---------|-----------------|-------------|-------------|
| **Claude Code** | Anthropic Metrics + Datadog + Segment | 开启 | **是**（IOPlatformUUID / /etc/machine-id） | **是**（CPU、主机名、平台） | **否** |
| **Copilot CLI** | GitHub/Microsoft 内部 | 开启 | 未确认 | **是**（平台信息） | 未确认 |
| **Codex CLI** | OpenAI 内部 | 开启 | 未确认 | **是**（平台信息） | 未确认 |
| **Aider** | PostHog | **关闭**（opt-in，10% 采样） | **是**（随机 UUID） | **是**（OS、架构） | **否** |
| **Gemini CLI** | OpenTelemetry + Google Clearcut | 开启 | **是**（持久化 UUID） | **是**（CPU/GPU/RAM 详细） | **否** |
| **Kimi CLI** | **无** | — | **否** | **否** | **否** |
| **OpenCode** | **无** | — | **否** | **否** | **否** |
| **Goose** | PostHog | **关闭**（opt-in） | **是**（随机 UUID） | **是**（OS、架构） | **否** |
| **Qwen Code** | OTEL（重品牌）+ **阿里云 RUM**（新增） | 开启 | **是**（继承 Gemini UUID） | **是**（继承 CPU/GPU/RAM） | **否** |
| **Qoder CLI** | Qoder 自有（api1.qoder.sh） | 开启 | **是**（`getMachineKey`） | 未确认 | **否** |

## 遥测端点

| 工具 | 端点 | 说明 |
|------|------|------|
| **Claude Code** | `api.anthropic.com/api/claude_code/metrics` | 主遥测 |
| | `http-intake.logs.us5.datadoghq.com` | Datadog 日志 |
| | `api.segment.io` | Segment 分析 |
| **Aider** | `us.i.posthog.com` | PostHog |
| **Gemini CLI** | `play.googleapis.com/log` | Google Clearcut |
| | 可配置 OTLP 端点 | OpenTelemetry |
| **Goose** | `us.i.posthog.com/capture/` | PostHog |
| | 可配置 OTLP + Langfuse 端点 | OpenTelemetry + LLM 可观测 |
| **Qwen Code** | `gb4w8c3ygj-default-sea.rum.aliyuncs.com` | 阿里云 RUM（App ID: gb4w8c3ygj@851d5d500f08f92） |
| | 可配置 OTLP 端点（继承 Gemini） | OpenTelemetry（Clearcut 已移除） |
| **Kimi CLI** | **无** | — |
| **OpenCode** | **无** | — |

## 采集数据详情

### Claude Code（782 个 tengu_ 事件，二进制反编译）
- accountUuid, organizationUuid, subscriptionType, rateLimitTier
- Machine ID (IOPlatformUUID / /etc/machine-id / Windows Registry MachineGuid)
- platform, os_release, architecture
- firstTokenTime, model name
- GitHub Actions: GITHUB_ACTOR, GITHUB_REPOSITORY（含数字 ID）

### Gemini CLI（194 个事件元数据键，源码分析）
- Installation ID (持久化 UUID)
- 用户 email（Google 账户缓存）+ 历史账户列表
- CPU 型号 + 核心数, GPU 型号, RAM 总量 GB（via `systeminformation` 库）
- OS, Node.js 版本, Docker 检测, IDE 检测
- GitHub Actions: workflow 名, 仓库名（hashed）

### Aider（源码 analytics.py）
- 随机 UUID（非关联到账户）
- python_version, os_platform, os_release, machine, aider_version
- model 名（未知模型自动 redact 为 `provider/REDACTED`）

### Goose（源码 posthog.rs）
- installation_id (随机 UUID)
- os, arch, version, platform_version
- provider, model, extensions 列表
- session_number, total_sessions, total_tokens
- 错误信息自动清洗（路径、密钥、邮箱 redact）

## 隐私控制

| 工具 | 禁用方式 | 默认 |
|------|----------|------|
| **Claude Code** | `DISABLE_TELEMETRY=true` 或 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true` | 开启 |
| **Copilot CLI** | 无明确公开方式 | 开启 |
| **Codex CLI** | 无明确公开方式 | 开启 |
| **Aider** | `--analytics false` 或 `permanently_disable` 或不 opt-in | **关闭** |
| **Gemini CLI** | `GEMINI_TELEMETRY_ENABLED=false` + 免费用户 opt-in/out UI | 开启 |
| **Kimi CLI** | 无需禁用（无遥测） | — |
| **OpenCode** | 无需禁用（无遥测） | — |
| **Goose** | `GOOSE_TELEMETRY_OFF=1` 或 `GOOSE_TELEMETRY_ENABLED=false` | **关闭** |

## 安全监控系统

| 工具 | 安全分类器 | 沙箱 | 命令阻止 | 提示注入检测 |
|------|-----------|------|----------|-------------|
| **Claude Code** | **是**（双阶段 LLM 分类器，28 条 BLOCK 规则） | macOS Seatbelt + Linux 容器 | **是**（Security Monitor） | **是**（通过安全分类器） |
| **Copilot CLI** | **否** | 无原生沙箱 | **否** | **否** |
| **Codex CLI** | **是**（Guardian Approval，实验性） | macOS Seatbelt + Linux Bubblewrap/Landlock + Windows Restricted Tokens | **是**（审批系统） | **否** |
| **Aider** | **否** | **否** | **否** | **否** |
| **Gemini CLI** | **是**（Conseca LLM 策略生成器 + AllowedPathChecker） | macOS Seatbelt + Linux seccomp BPF + Windows C# | **是**（TOML 策略引擎） | **是**（Conseca） |
| **Kimi CLI** | **否** | **否** | **是**（审批系统） | **否** |
| **OpenCode** | **否** | **否** | **是**（基础权限） | **否** |
| **Goose** | **是**（AdversaryInspector + RepetitionInspector + 模式扫描） | **否** | **是**（SmartApprove） | **是**（模式 + ML 分类器） |

## 环境变量清洗

| 工具 | 清洗机制 | 阻止模式 |
|------|----------|----------|
| **Claude Code** | 未公开（闭源） | 未公开 |
| **Gemini CLI** | **全面**（`environmentSanitization.ts`） | TOKEN, SECRET, PASSWORD, KEY, AUTH, CREDENTIAL, 私钥模式, GitHub tokens, AWS keys, JWTs |
| **Codex CLI** | 31 个危险环境变量阻止列表 | PATH, LD_PRELOAD 等 |
| **Goose** | 31 个危险环境变量阻止列表 | 同 Codex |
| **Aider** | **无** | — |
| **Kimi CLI** | **无** | — |
| **OpenCode** | **无** | — |

## 证据来源

| 工具 | 分析方式 | 证据文件 |
|------|----------|----------|
| Claude Code | Bun 字节码反编译（v2.1.81） | `claude-code/EVIDENCE.md` |
| Copilot CLI | Node.js SEA 反编译（v1.0.11/0.0.403） | `copilot-cli/EVIDENCE.md` |
| Codex CLI | Rust 二进制 strings + --help（v0.116.0） | `codex-cli/EVIDENCE.md` |
| Aider | 源码 `aider/analytics.py` | `aider/EVIDENCE.md` |
| Gemini CLI | 源码 `packages/core/src/telemetry/` + `safety/` | `gemini-cli/EVIDENCE.md` |
| Kimi CLI | 源码 `src/kimi_cli/` 全量搜索 | `kimi-cli/EVIDENCE.md` |
| OpenCode | 源码 `internal/` 全量搜索 | `opencode/EVIDENCE.md` |
| Goose | 源码 `crates/goose/src/` + `crates/goose-cli/src/` | 源码分析 |
