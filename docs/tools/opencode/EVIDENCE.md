# OpenCode 遥测与安全分析证据

## 遥测系统
- **无遥测** — 递归搜索零结果
- 无分析 SDK、无报告端点

## 数据采集
- **不采集**: Machine ID、UUID、主机名、硬件指纹
- 无外发分析请求

## 安全系统
- `permission/permission.go`: 基础工具权限审批
- 按请求 approve/deny + 会话级持久化授予
- 无提示注入检测、无 ML 分类器

来源: internal/ (GitHub 源码分析)
