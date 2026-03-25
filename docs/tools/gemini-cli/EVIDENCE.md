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
