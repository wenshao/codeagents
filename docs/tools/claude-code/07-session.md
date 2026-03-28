# 7. 会话、记忆与 MCP

## 会话管理

### 上下文压缩
当对话历史接近上下文窗口限制时，Claude Code 自动压缩早期对话内容，保留关键信息：
- 自动触发：接近 ~95% token 上限时
- 手动触发：`/compact` 命令
- Hook 支持：PreCompact/PostCompact 事件允许自定义压缩前后行为

**压缩后 UI 行为**：压缩完成后清空屏幕旧对话，仅显示 "Summarized conversation" 标记——屏幕内容与模型上下文保持同步。详见[压缩后 UI 行为分析](../../comparison/context-compression-deep-dive.md)。

### 会话恢复
```bash
# 恢复最近会话
claude --resume

# 恢复指定会话
claude --resume <session-id>

# 继续上次对话
claude -c
```

### 检查点与回退（Checkpoint & Rewind）
- Claude Code 在每次工具调用前自动创建 Git 检查点
- 用户可通过 Esc 键回退到之前的状态
- 回退会恢复文件系统和对话历史

### Worktrees
```bash
# 在独立 worktree 中启动 Claude Code
claude --worktree
```
Git worktree 隔离允许多个 Claude Code 实例在不同分支上并行工作，互不干扰。EnterWorktree/ExitWorktree 工具支持在会话内动态切换 worktree。

## 内存系统

Claude Code 的记忆系统通过 CLAUDE.md 文件跨会话保存项目知识和用户偏好：

### CLAUDE.md 层级结构

```
~/.claude/CLAUDE.md                      # 全局记忆（所有项目通用偏好）
<project-root>/CLAUDE.md                 # 项目级记忆（提交到 Git 共享给团队）
<project-root>/.claude/CLAUDE.md         # 项目隐藏配置目录下的记忆
<subdirectory>/CLAUDE.md                 # 子目录级记忆（操作该目录文件时加载）
~/.claude/projects/<project-hash>/CLAUDE.md  # 用户私有的项目特定记忆（不提交到 Git）
```

### 记忆内容类型
- **项目知识**：架构决策、技术栈说明、构建/测试命令
- **代码规范**：编码风格、命名约定、文件组织规则
- **用户偏好**：语言偏好、交互风格、常用工作流

### 记忆管理
- **自动学习**：Claude Code 在对话中识别到有价值的项目知识时，自动提议保存到 CLAUDE.md
- **手动管理**：`/memory` 命令查看和编辑记忆文件（在外部编辑器中打开）
- **层级合并**：会话开始时自动加载所有层级的 CLAUDE.md，合并为系统提示的一部分
- **与 Gemini CLI 对比**：机制类似（分层 Markdown 文件），但 Claude Code 使用 CLAUDE.md，Gemini CLI 使用 GEMINI.md

## CLAUDE.md 项目配置

CLAUDE.md 是 Claude Code 的项目级指令文件，类似于 Gemini CLI 的 GEMINI.md。它告诉 Claude Code 项目的背景、规范和偏好。

### 层级结构

| 位置 | 作用域 | 说明 |
|------|--------|------|
| `~/.claude/CLAUDE.md` | 全局 | 所有项目通用的个人偏好 |
| 项目根目录 `CLAUDE.md` | 项目 | 项目级指令，提交到 Git 共享给团队 |
| 子目录 `CLAUDE.md` | 目录 | 仅在操作该目录内文件时加载 |
| `.claude/CLAUDE.md` | 项目（隐藏） | 项目配置目录下的指令 |

### 内容建议

```markdown
# CLAUDE.md

## 项目概述
这是一个 React + TypeScript 前端项目，使用 Vite 构建。

## 开发命令
- `npm run dev` - 启动开发服务器
- `npm test` - 运行测试
- `npm run lint` - 代码检查
- `npm run build` - 构建生产版本

## 代码规范
- 使用 TypeScript strict 模式
- 组件使用函数式组件 + Hooks
- 文件命名使用 kebab-case
- 测试文件使用 .test.ts 后缀
```

## MCP 集成

Claude Code 支持 Model Context Protocol（MCP），允许接入外部工具服务器：

### 传输协议

| 协议 | 说明 | 适用场景 |
|------|------|----------|
| **stdio** | 通过标准输入/输出通信 | 本地进程，最常用 |
| **sse** | Server-Sent Events | 远程服务器 |
| **streamable-http** | 可流式 HTTP | 云端部署 |

### 配置方式

**项目级**（`.claude/settings.json`）：
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    },
    "remote-server": {
      "type": "sse",
      "url": "https://mcp.example.com/sse"
    }
  }
}
```

### 工具命名
MCP 工具以 `mcp__serverName__toolName` 格式注册（双下划线分隔）。例如：
- `mcp__github__create_issue`
- `mcp__filesystem__read_file`
