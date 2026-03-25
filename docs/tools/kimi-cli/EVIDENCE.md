# Kimi CLI 遥测与安全分析证据

## 遥测系统
- **无遥测** — 递归搜索零结果
- 无 PostHog/Sentry/Mixpanel/任何分析 SDK

## 数据采集
- **不采集**: Machine ID、MAC 地址、主机名、硬件信息
- `metadata.py` 使用 MD5(工作目录路径) 仅用于本地会话目录命名
- `environment.py` 检测 OS/arch/shell 仅用于本地环境适配

## 外发请求
- 仅 LLM API 调用（用户配置的 provider）
- 无任何分析端点

## 安全系统
- `soul/approval.py`: 工具审批系统（approve/reject/approve-for-session）
- `ApprovalState`: YOLO 模式 + 按操作自动审批集合
- 子代理拒绝有专门的严格消息防止重试绕过

来源: src/kimi_cli/ (GitHub 源码分析)
