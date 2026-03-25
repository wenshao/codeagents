# 2. 命令与交互

## 斜杠命令（会话内）

| 命令 | 用途 |
|------|------|
| `/init` | 分析代码库，生成 AGENTS.md（见 [03-architecture.md](03-architecture.md) 详细说明） |
| `/compact [FOCUS]` | 压缩上下文历史（可指定保留重点） |
| `/clear`, `/reset` | 清除上下文 |
| `/yolo` | 切换 YOLO 模式 |
| `/plan` | 切换 Plan 模式 |
| `/model` | 切换模型和思维模式 |
| `/sessions`, `/resume` | 列出并切换/恢复会话 |
| `/new` | 创建新会话 |
| `/export` | 导出会话 |
| `/import` | 导入上下文 |
| `/editor` | 配置外部编辑器 |
| `/add-dir` | 添加工作目录 |
| `/mcp` | 显示 MCP 状态 |
| `/task` | 后台任务浏览器（TUI） |
| `/web` | 抓取网页内容加入上下文 |
| `/help` | 显示帮助 |
| `/version` | 显示版本信息 |
| `/changelog` | 显示更新日志 |
| `/feedback` | 提交反馈 |
| `/exit`, `/quit` | 退出 |
| `/skill:<name>` | 加载标准 Skill |
| `/flow:<name>` | 执行 Flow Skill |

> **注意：** 认证（登录/登出）和用量查看通过 CLI 参数或配置命令处理，而非交互式斜杠命令。

## 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl-X` | 切换 Agent ↔ Shell 模式 |
| `Ctrl-C` | 中断当前操作 |
| `Ctrl-D` | 退出 |
| `Ctrl-O` | 在外部编辑器中打开输入 |
| `Ctrl-V` | 粘贴文本/图片/视频 |
| `Ctrl-E` | 展开审批预览详情 |
| `Shift-Tab` | 切换 Plan 模式 |
| `1/2/3/4` | 审批面板快捷操作（审批/会话审批/拒绝/拒绝+反馈） |

## CLI 参数

```bash
# 交互式会话（默认 Shell 模式）
kimi

# 带提示启动
kimi -p "重构 auth 模块"

# 非交互模式（适合脚本/CI）
kimi --print -p "解释这段代码"

# 流式 JSON 输出
kimi --print --stream-json -p "..."

# 指定模型和思维模式
kimi -m claude-sonnet --thinking

# 恢复会话
kimi -S <session-id>
kimi -C    # 继续上一个会话

# YOLO 模式（自动审批所有操作）
kimi --yolo

# 指定工作目录和附加目录
kimi -w /path/to/project --add-dir /path/to/docs

# 登录/登出
kimi login
kimi logout

# Web UI
kimi web [--port 5494]
kimi web --network --auth-token <token>    # 网络访问模式

# ACP 模式（IDE 集成）
kimi acp

# MCP 服务器管理
kimi mcp list
kimi mcp add --transport stdio my-server -- command args
kimi mcp add --transport http --auth oauth my-server https://mcp.example.com
kimi mcp remove my-server
kimi mcp auth my-server
kimi mcp test my-server

# 插件管理
kimi plugin install https://github.com/org/repo.git
kimi plugin install https://github.com/org/repo.git/plugins/my-plugin  # monorepo
kimi plugin list
kimi plugin uninstall my-plugin

# 导出会话
kimi export [session-id]

# 系统信息
kimi info [--json]

# 可视化仪表板
kimi vis

# Wire 模式（自定义 UI）
kimi --wire
```
