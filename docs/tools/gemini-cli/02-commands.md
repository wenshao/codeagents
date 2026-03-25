# 2. Gemini CLI 命令详解

## CLI 命令

```bash
# 启动交互式会话
gemini

# 非交互模式（Headless）
gemini -p "解释这段代码"

# 恢复会话
gemini --resume <session-id>

# 查看版本
gemini --version
```

## 斜杠命令（会话内，41 个命令）

```bash
# 核心操作
/help            # 查看帮助
/clear           # 清除对话
/compress        # 压缩上下文
/copy            # 复制内容
/quit            # 退出
/commands        # 列出所有可用命令

# 代理 & 工具
/agents          # 查看/调用代理
/tools           # 查看可用工具
/skills          # 管理技能
/plan            # 进入规划模式

# 记忆 & 会话
/memory          # 查看/添加/清除记忆
/chat            # 对话管理
/restore         # 恢复检查点
/resume          # 恢复会话
/rewind          # 回退操作（也可按 Esc Esc）

# 配置
/settings        # 修改设置
/model           # 切换模型
/theme           # 切换主题
/permissions     # 查看权限
/policies        # 查看策略
/hooks           # 管理 Hook
/auth            # 认证管理
/profile         # 配置文件

# 扩展 & MCP
/extensions      # 管理扩展（安装/启用/禁用）
/mcp             # 管理 MCP 服务器

# 开发
/stats           # 查看统计信息（含 Token 缓存）
/shortcuts       # 查看快捷键
/bug             # 报告 Bug
/upgrade         # 升级版本
/about           # 关于信息
/docs            # 查看文档

# IDE
/ide             # IDE 集成管理
/editor          # 编辑器设置

# 终端
/shells          # Shell 管理
/vim             # Vim 模式
/terminalSetup   # 终端设置

# 其他
/init            # 初始化项目配置
/setupGithub     # 设置 GitHub
/privacy         # 隐私设置
/directory       # 目录管理
/corgi           # 彩蛋
```

## IDE 集成

| 编辑器 | 状态 | 说明 |
|--------|------|------|
| **VS Code** | 官方扩展（Preview） | "Gemini CLI Companion"，需 VS Code 1.99+。工作区上下文（最近 10 文件、光标位置、选区最多 16KB）、原生 Diff 查看器、命令面板集成（Ctrl+S 接受 Diff） |
| **Zed** | 官方支持 | v0.19.0+ 集成 |
| **Positron IDE** | 官方支持 | v0.28.0+ 支持 |
| **Google Colab** | 预装 | v0.22.0+ 预装在 Colab 环境 |
| **Vertex AI Workbench** | 原生可用 | Cloud 环境直接使用 |
| **Neovim** | 社区插件 | nvim Gemini Companion、gemini-cli.nvim |

**VS Code 扩展命令**：
- `gemini.diff.accept`（Ctrl+S / Cmd+S）— 接受 Diff
- `gemini.diff.cancel` — 关闭 Diff 编辑器
- `gemini-cli.runGeminiCLI` — 启动 CLI
- `gemini-cli.showNotices` — 第三方通知
