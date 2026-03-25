# Gemini CLI 遥测与安全分析证据

## 遥测系统（双管道）
1. **OpenTelemetry (OTLP)**: 支持 GCP 直连、OTLP collector、本地文件
2. **Clearcut**: Google 分析服务 `https://play.googleapis.com/log?format=json&hasfast=true`
   - Console: GEMINI_CLI, Source: CONCORD
   - 缓冲 1000 事件，每 60 秒刷新

## 采集数据（194 个事件元数据键）
- 模型名、嵌入模型、沙箱状态、审批模式
- 认证类型、MCP 服务器数、扩展数
- **CPU 信息**（型号）、**CPU 核心数**、**GPU 信息**（型号）、**RAM 总量 GB**（via `systeminformation`库）
- OS platform、OS release、Node.js 版本、Docker 检测
- GitHub Actions: workflow 名、仓库名（hashed）、事件名、PR 号
- Installation ID: 持久化 UUID 存储于 `~/.gemini/`
- 用户 email（Google 账户缓存）
- 历史 Google 账户列表

## 安全系统
- **AllowedPathChecker**: 路径遍历防护（符号链接解析）
- **Conseca**: LLM 驱动的最小权限安全策略生成器（默认关闭）
- **沙箱**: macOS Seatbelt, Linux seccomp BPF, Windows C# 实现
- **环境变量清洗**: 阻止 TOKEN/SECRET/PASSWORD/KEY 等模式

## 隐私控制
- `GEMINI_TELEMETRY_ENABLED=false` 禁用 OTLP
- 免费用户有明确 opt-in/out 界面
- 提示内容默认不记录（需 `GEMINI_TELEMETRY_LOG_PROMPTS` 开启）

来源: packages/core/src/telemetry/, packages/core/src/safety/ (GitHub 源码分析)

## 深度补充（源码级分析）

### 遥测端点（精确）
1. **OpenTelemetry**: 可配置端点（GCP 直连 / OTLP collector / 本地文件）
2. **Clearcut**: `https://play.googleapis.com/log?format=json&hasfast=true`
   - Console type: `GEMINI_CLI`, Log source: `CONCORD`
   - 缓冲: max 1000 事件，每 60 秒刷新，失败重试 max 100

### Machine ID（源码: utils/installationManager.ts）
- 生成: `randomUUID()` 持久化到 `~/.gemini/`
- 错误回退: 硬编码 `'123456789'`
- 附加到每个遥测事件

### 硬件采集（源码: telemetry/, via systeminformation 库）
| 采集项 | API | 用途 |
|--------|-----|------|
| CPU 型号 | `os.cpus()` | 遥测 |
| CPU 核心数 | `os.cpus().length` | 遥测 |
| GPU 型号 | `si.graphics()` | 遥测 |
| RAM 总量 GB | `si.mem()` | 遥测 |
| OS/release | `os.platform()/release()` | 遥测 |
| Node.js 版本 | `process.version` | 遥测 |
| Docker 检测 | 文件检查 | 环境识别 |

### 用户追踪（源码: utils/userAccountManager.ts）
- 当前 Google 账户 email
- 历史账户列表（old array）
- 总生命周期账户数

### 事件元数据键数（源码: telemetry/constants.ts）
- **194 个** EventMetadataKey 枚举值
- 涵盖: 模型、认证、MCP、工具、文件操作、token 用量（7 类细分）

### 安全系统

#### AllowedPathChecker（源码: safety/built-in.ts）
- 路径遍历防护 + 符号链接解析
- 可配置 included/excluded 参数名

#### Conseca（源码: safety/conseca/）
- LLM 驱动安全策略生成器（使用 Gemini Flash）
- 基于最小权限原则生成每提示安全策略
- 策略执行器验证每个工具调用
- 产出: allow/deny/ask_user + 理由
- **默认关闭**（enableConseca 配置项）

#### 沙箱实现
- macOS: Apple Seatbelt (sandbox-exec)，动态构建 SBPL profile
- Linux: seccomp BPF 过滤器（x64/arm64/arm/ia32 架构特定字节码）
  - 阻止 ptrace 系统调用（返回 EPERM）
  - 架构不匹配则 KILL 进程
  - 过滤器写入 `/tmp/gemini-cli-seccomp-{pid}.bpf`
- Windows: 独立 C# 实现（GeminiSandbox.cs）

#### 环境变量清洗（源码: environmentSanitization.ts）
**始终允许**: PATH, HOME, SHELL, TERM, LANG, TMPDIR, GitHub Actions 上下文
**始终阻止**: CLIENT_ID, DB_URI, CONNECTION_STRING, AWS/Azure/Google 云标识, DATABASE_URL
**模式阻止名**: TOKEN, SECRET, PASSWORD, KEY, AUTH, CREDENTIAL, CREDS, PRIVATE, CERT
**模式阻止值**: RSA/SSH/EC/PGP 私钥, URL 嵌入凭据, ghp_/gho_/ghu_ tokens, AIzaSy_ keys, AKIA_ keys, eyJ_ JWTs, Stripe keys, Slack tokens
**严格模式**: GitHub Actions 中阻止所有非白名单变量

### 隐私通知（3 层，源码: cli/src/ui/privacy/）
1. **API Key 用户**: 链接 Google APIs TOS
2. **免费用户**: 明确告知"Google 采集提示词、代码、输出、编辑、使用信息和反馈"，"人工审查员可能阅读"，数据"与 Google 账户断开连接"后保留最多 18 个月，有 opt-in/out 选择
3. **付费用户 (Vertex)**: 链接 Gemini Code Assist 隐私通知

### 研究数据采集（可选参与）
- `GEMINI_CLI_RESEARCH_OPT_IN_STATUS`
- `GEMINI_CLI_RESEARCH_CONTACT_EMAIL`
- `GEMINI_CLI_RESEARCH_USER_ID`
- `GEMINI_CLI_RESEARCH_FEEDBACK_*`
- `GEMINI_CLI_RESEARCH_SURVEY_RESPONSES`

### 环境变量（遥测相关，8 个）
| 变量 | 用途 |
|------|------|
| `GEMINI_TELEMETRY_ENABLED` | 启用/禁用 OTLP |
| `GEMINI_TELEMETRY_TARGET` | local/gcp |
| `GEMINI_TELEMETRY_LOG_PROMPTS` | 记录完整提示内容 |
| `GEMINI_TELEMETRY_OUTFILE` | 写入文件 |
| `GEMINI_TELEMETRY_USE_COLLECTOR` | 使用 OTLP collector |
| `GEMINI_TELEMETRY_USE_CLI_AUTH` | CLI 认证遥测 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | 标准 OTLP 端点覆盖 |
| `GOOGLE_CLOUD_PROJECT` | GCP 项目 ID |

来源: GitHub 源码直接分析 (packages/core/src/telemetry/, safety/, permissions/)
