# 2. Gemini CLI 命令详解（39 个命令文件，源码：packages/cli/src/ui/commands/）

## 命令基础架构

### SlashCommand 接口

每个斜杠命令都实现 `SlashCommand` 接口：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `string` | 命令名（不含 `/`） |
| `description` | `string` | 帮助文本中显示的描述 |
| `kind` | `CommandKind` | 固定为 `BUILT_IN` |
| `autoExecute` | `boolean` | `true` = 输入后立即执行，无需确认 |
| `altNames` | `string[]` | 别名列表（如 `/quit` 的别名 `exit`） |
| `hidden` | `boolean` | 隐藏命令，不出现在 `/help` 列表中 |
| `isSafeConcurrent` | `boolean` | 是否可在并发会话中安全执行 |
| `subCommands` | `SubCommand[]` | 子命令定义（name + description） |
| `action` | `function` | 执行函数，返回 `ActionReturn` |

### Action 返回类型

命令的 `action` 函数返回 `ActionReturn`，决定 UI 行为：

| 返回类型 | 行为 |
|----------|------|
| `message` | 在聊天区域显示一条消息（最常见） |
| `dialog` | 打开内置对话框（auth、settings、model、theme、privacy、editor、sessionBrowser） |
| `custom_dialog` | 渲染自定义 React 组件（如 RewindViewer、HooksDialog） |
| `quit` | 退出 CLI |
| `submit_prompt` | 将文本作为用户输入提交给模型 |
| `confirm_action` | 弹出确认对话框，用户确认后执行回调 |
| `logout` | 执行登出流程 |

---

## 有子命令的命令（16 个）

### /agents — 代理管理

- **返回类型**：`message`
- **子命令**：
  - `list` — 列出所有已注册代理及其状态
  - `enable` — 启用指定代理
  - `disable` — 禁用指定代理

### /auth — 认证管理

- **返回类型**：`dialog`（打开 `auth` 对话框）
- **子命令**：
  - `signin`（别名 `login`）— 登录 Google 账户
  - `signout`（别名 `logout`）— 登出当前账户

### /chat — 会话管理

- **别名**：`/resume`
- **返回类型**：`dialog`（打开 `sessionBrowser` 对话框）/ `message`
- **子命令**：
  - `save` — 保存当前会话
  - `resume`（别名 `load`）— 恢复已保存的会话
  - `list` — 列出所有已保存会话
  - `delete` — 删除指定会话
  - `export` — 导出会话为文件

### /commands — 命令管理

- **返回类型**：`message`
- **子命令**：
  - `reload` — 重新加载所有命令（开发调试用）

### /extensions — 扩展管理

- **返回类型**：`message`
- **子命令**：
  - `list` — 列出已安装扩展
  - `update` — 更新扩展到最新版本
  - `explore` — 浏览可用扩展市场
  - `install` — 安装指定扩展
  - `uninstall` — 卸载指定扩展
  - `enable` — 启用已安装扩展
  - `disable` — 禁用已安装扩展
  - `config` — 配置扩展参数

### /hooks — Hook 管理

- **返回类型**：`custom_dialog`（渲染 `HooksDialog` 组件）
- **默认行为**：打开 panel 视图显示所有 Hook
- **子命令**：
  - `enable` — 启用指定 Hook
  - `disable` — 禁用指定 Hook

### /mcp — MCP 服务器管理

- **返回类型**：`message`
- **子命令**：
  - `list` — 列出所有 MCP 服务器及连接状态
  - `auth` — 为 MCP 服务器配置认证
  - `enable` — 启用指定 MCP 服务器
  - `disable` — 禁用指定 MCP 服务器
  - `restart` — 重启指定 MCP 服务器

### /memory — 记忆管理

- **返回类型**：`message`
- **子命令**：
  - `show` — 显示当前记忆内容
  - `add` — 添加新记忆条目
  - `reload`（别名 `refresh`）— 从文件重新加载记忆
  - `list` — 列出所有记忆条目

### /model — 模型管理

- **返回类型**：`dialog`（打开 `model` 对话框）
- **默认行为**：打开模型选择对话框
- **子命令**：
  - `set` — 直接设置指定模型（如 `/model set gemini-2.5-pro`）

### /permissions — 权限管理

- **返回类型**：`message`
- **子命令**：
  - `trust` — 信任当前工作目录，授予完全权限

### /plan — 规划模式

- **返回类型**：`message`
- **子命令**：
  - `copy` — 复制当前计划内容到剪贴板

### /policies — 策略管理

- **返回类型**：`message`
- **子命令**：
  - `list` — 列出所有生效的策略及其来源

### /skills — 技能管理

- **返回类型**：`message`
- **子命令**：
  - `list` — 列出所有可用技能
  - `link` — 关联外部技能文件
  - `enable` — 启用指定技能
  - `disable` — 禁用指定技能

### /stats — 统计信息

- **返回类型**：`message`
- **默认行为**：显示当前 session 统计
- **子命令**：
  - `session` — 当前会话统计（Token 用量、缓存命中等）
  - `model` — 模型相关统计
  - `tools` — 工具调用统计

### /tools — 工具管理

- **返回类型**：`message`
- **子命令**：
  - `list` — 列出所有可用工具（内置 + MCP + 扩展）
  - `desc` — 显示指定工具的详细描述

---

## 简单命令（23 个）

### 信息类

| 命令 | 别名 | 返回类型 | 说明 |
|------|------|----------|------|
| `/about` | — | `message` | 显示版本、构建信息、运行环境 |
| `/help` | — | `message` | 列出所有非隐藏命令及描述 |
| `/docs` | — | `message` | 打开官方文档链接 |
| `/shortcuts` | — | `message` | 显示所有键盘快捷键 |
| `/directory` | — | `message` | 显示当前工作目录信息 |

### 会话操作

| 命令 | 别名 | 返回类型 | 说明 |
|------|------|----------|------|
| `/clear` | — | `message` | 清除当前对话历史，重置上下文 |
| `/compress` | `summarize`, `compact` | `submit_prompt` | 压缩对话上下文，让模型生成摘要替代完整历史 |
| `/copy` | — | `message` | 复制最近一条模型回复到剪贴板 |
| `/restore` | — | `message` | 恢复到最近的检查点 |
| `/rewind` | — | `custom_dialog`（渲染 `RewindViewer`） | 回退到之前的对话状态，可选择回退点 |

### 配置与设置

| 命令 | 别名 | 返回类型 / 对话框 | 说明 |
|------|------|-------------------|------|
| `/settings` | — | `dialog` → `settings` | 打开设置面板 |
| `/theme` | — | `dialog` → `theme` | 打开主题选择器 |
| `/privacy` | — | `dialog` → `privacy` | 打开隐私设置对话框 |
| `/editor` | — | `dialog` → `editor` | 打开编辑器配置对话框 |
| `/footer` | `statusline` | `custom_dialog`（渲染 `FooterConfigDialog`） | 配置底部状态栏显示内容 |
| `/vim` | — | `message` | 切换 Vim 模式开关 |
| `/init` | — | `message` | 在当前目录初始化 `GEMINI.md` 项目配置 |

### 终端与 Shell

| 命令 | 别名 | 返回类型 | 说明 |
|------|------|----------|------|
| `/shells` | `bashes` | `message` | 列出当前活跃的 Shell 进程 |
| `/terminal-setup` | — | `message` | 配置终端集成（字体、颜色等） |

### 账户与安全

| 命令 | 别名 | 返回类型 | 说明 |
|------|------|----------|------|
| `/setup-github` | — | `message` | 配置 GitHub 集成（OAuth 认证） |
| `/upgrade` | — | `message` | 检查并升级到最新版本 |
| `/bug` | — | `message` | 打开 Bug 报告页面 |

### 退出

| 命令 | 别名 | 返回类型 | 说明 |
|------|------|----------|------|
| `/quit` | `exit` | `quit` | 退出 CLI |

---

## 特殊命令

### /corgi — 隐藏彩蛋

- **hidden**: `true`（不出现在 `/help` 中）
- **返回类型**：`message`
- **行为**：显示 ASCII 柯基犬动画

### /profile — 开发专用

- **仅在开发模式可用**
- **返回类型**：`message`
- **行为**：显示性能分析数据

### /ide — IDE 集成

- **返回类型**：`message`
- **行为**：显示当前 IDE 连接状态，管理 VS Code / Zed 等编辑器集成

---

## 命令统计

| 分类 | 数量 |
|------|------|
| 39 个命令文件 | `packages/cli/src/ui/commands/` 目录 |
| 37 个注册命令 | 正常出现在命令系统中 |
| 1 个隐藏命令 | `/corgi`（`hidden: true`） |
| 1 个开发命令 | `/profile`（仅开发模式） |
| 16 个有子命令 | 提供细粒度操作 |
| 23 个简单命令 | 无子命令，直接执行 |

## 内置对话框映射

以下命令通过返回 `dialog` 类型打开内置对话框：

| 命令 | 对话框 ID |
|------|-----------|
| `/auth` | `auth` |
| `/settings` | `settings` |
| `/model` | `model` |
| `/theme` | `theme` |
| `/privacy` | `privacy` |
| `/editor` | `editor` |
| `/chat` | `sessionBrowser` |

## 自定义组件映射

以下命令通过返回 `custom_dialog` 类型渲染 React 组件：

| 命令 | React 组件 |
|------|------------|
| `/rewind` | `RewindViewer` |
| `/hooks` | `HooksDialog` |
| `/footer` | `FooterConfigDialog` |
