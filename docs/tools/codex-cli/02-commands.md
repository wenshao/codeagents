# 2. 命令、工具与配置

## CLI 子命令

### 完整子命令列表

| 子命令 | 别名 | 功能 |
|--------|------|------|
| `exec` | `e` | 执行任务（默认子命令） |
| `review` | - | 代码审查 |
| `login` | - | 登录 OpenAI 账户 |
| `logout` | - | 登出 |
| `mcp` | - | MCP 客户端管理 |
| `mcp-server` | - | 作为 MCP 服务器运行 |
| `app-server` | - | IDE 集成的 JSON-RPC 服务器 |
| `completion` | - | Shell 补全脚本生成 |
| `sandbox` | - | 沙箱测试与调试 |
| `debug` | - | 调试信息输出 |
| `apply` | `a` | 应用补丁文件 |
| `resume` | - | 恢复之前的会话 |
| `fork` | - | 从已有会话分叉 |
| `cloud` | - | 云端任务（实验性） |
| `features` | - | 查看/管理功能标志 |

### exec（默认）

```bash
# 交互式会话
codex

# 直接执行任务
codex "重构这个函数，添加类型注解"
codex exec "修复 lint 错误"
codex e "编写单元测试"
```

### review（代码审查）

```bash
# 审查未提交的更改
codex review --uncommitted

# 审查与某个分支的差异
codex review --base main

# 审查特定提交
codex review --commit abc1234
```

### login / logout

```bash
codex login    # 交互式登录 OpenAI 账户
codex logout   # 登出
```

### apply

```bash
# 应用补丁文件
codex apply patch.diff
codex a patch.diff
```

### resume / fork

```bash
# 恢复之前的会话（通过 UUID）
codex resume <session-id>

# 从已有会话分叉
codex fork <session-id>
```

### completion

```bash
# 生成 shell 补全脚本
codex completion bash >> ~/.bashrc
codex completion zsh >> ~/.zshrc
codex completion fish >> ~/.config/fish/completions/codex.fish
```

### 完整参数参考

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--model` | `-m` | 指定使用的模型 | `o4-mini` |
| `--approval-mode` | `-a` | 审批模式：untrusted/on-request/never | `untrusted` |
| `--sandbox` | | 沙箱模式：read-only/workspace-write/danger-full-access | - |
| `--full-auto` | | `--approval-mode on-request --sandbox workspace-write` | - |
| `--quiet` | `-q` | 安静模式，减少输出 | `false` |
| `--config` | `-c` | 指定配置文件路径 | `~/.codex/config.toml` |
| `--no-project-doc` | | 不加载 CODEX.md | `false` |
| `--project-doc` | | 指定额外的项目指令文件 | - |
| `--oss` | | 使用本地 OSS 模型提供者 | - |
| `--local-provider` | | 指定本地模型提供者（lmstudio/ollama） | - |
| `--dangerously-bypass-approvals-and-sandbox` | | 绕过所有审批和沙箱 | - |
| `--help` | `-h` | 显示帮助信息 | - |
| `--version` | `-v` | 显示版本号 | - |

## 交互式斜杠命令

Codex CLI 在交互式会话中提供 20+ 个斜杠命令：

### 会话管理

| 命令 | 功能 |
|------|------|
| `/clear` | 清除当前对话上下文 |
| `/compact` | 压缩对话历史，释放上下文窗口空间 |
| `/history` | 显示对话历史记录 |
| `/status` | 显示当前会话状态 |
| `/resume` | 恢复之前的会话 |
| `/fork` | 从当前会话分叉出新会话 |
| `/undo` | 撤销上一步操作 |

### 代码与差异

| 命令 | 功能 |
|------|------|
| `/diff` | 显示当前会话产生的所有文件修改差异 |
| `/review` | 启动代码审查模式 |
| `/search` | 搜索代码内容 |

### 模型与设置

| 命令 | 功能 |
|------|------|
| `/model` | 切换或查看当前模型 |
| `/settings` | 查看或修改设置 |
| `/theme` | 切换界面主题 |
| `/modes` | 查看或切换审批模式 |

### 高级功能

| 命令 | 功能 |
|------|------|
| `/plan` | 让代理制定计划而不执行 |
| `/help` | 显示帮助信息 |
| `/apps` | 管理应用集成 |
| `/experimental` | 访问实验性功能 |
| `/skill` | 调用特定技能 |
| `/skills` | 列出可用技能 |
| `/agent` | 代理相关操作 |

## 代理工具系统

Codex CLI 的代理拥有以下工具：

### 核心工具

| 工具 | 功能 |
|------|------|
| `LocalShellCall` | 在沙箱中执行 shell 命令 |
| `ApplyPatch` | 使用类 unified diff 格式精确修改文件 |
| `WebSearchCall` | 网络搜索能力 |
| `McpToolCall` | 调用 MCP 服务器提供的工具 |
| `ImageGenerationCall` | 图片生成 |
| `GhostSnapshot` | 快照/检查点机制 |
| `Compaction` | 上下文压缩，保持对话窗口可控 |
| `DynamicToolCall` | 动态工具调用 |
| `ToolSearchCall` | 搜索可用工具 |

### CommandAction 子操作

| 操作 | 功能 |
|------|------|
| `Read` | 读取文件内容 |
| `Search` | 基于 ripgrep 的代码搜索 |
| `ListFiles` | 列出目录文件 |

### ApplyPatch 格式

```
*** Begin Patch
*** Update File: src/main.ts
@@@ -10,3 +10,4 @@@
 import { foo } from './foo';
 import { bar } from './bar';
+import { baz } from './baz';

*** End Patch
```

## MCP 支持

### 作为 MCP 客户端

Codex CLI 内置 MCP 客户端，可以连接外部 MCP 服务器扩展工具能力：

```bash
# 列出已配置的 MCP 服务器
codex mcp list

# 查看特定服务器详情
codex mcp get <server-name>

# 添加 MCP 服务器
codex mcp add <server-name> <command> [args...]

# 移除 MCP 服务器
codex mcp remove <server-name>

# MCP 服务器认证
codex mcp login <server-name>
codex mcp logout <server-name>
```

代理通过 `McpToolCall` 工具调用已配置的 MCP 服务器。

### 作为 MCP 服务器

Codex CLI 可以作为 MCP 服务器暴露自身能力，供其他 MCP 客户端调用：

```bash
# 以 MCP 服务器模式运行（stdio 传输）
codex mcp-server
```

这允许其他 MCP 兼容的工具（如 Claude Code）通过标准 MCP 协议调用 Codex 的能力。

## 配置系统

### 配置文件

配置文件为 TOML 格式，位于 `~/.codex/config.toml`（86 字段结构体）：

```toml
# ~/.codex/config.toml
model = "o4-mini"
approval_mode = "on-request"

# 支持 profiles
[profiles.work]
model = "gpt-5.1-codex"

[profiles.personal]
model = "o4-mini"
```

### 指令文件层级

Codex CLI 支持三种指令文件，按层级加载：

| 文件名 | 作用域 | 说明 |
|--------|--------|------|
| `~/.codex/instructions.md` | 全局（用户级） | 所有项目共享的指令 |
| `CODEX.md` | 项目级 | 项目根目录的指令文件 |
| `AGENTS.md` | 项目级 | 代理行为指令（替代名称） |
| `SKILL.md` | 技能级 | 定义特定技能的指令 |

### 环境变量

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥（必需） | `sk-proj-...` |
| `OPENAI_BASE_URL` | 自定义 API 端点 | `https://api.openai.com/v1` |
| `OPENAI_ORG_ID` | OpenAI 组织 ID | `org-...` |
| `CODEX_HOME` | Codex 配置目录 | `~/.codex` |

## 会话系统

Codex CLI 支持持久化会话，每个会话有唯一 UUID 标识：

```bash
# 恢复之前的会话
codex resume <session-uuid>

# 从已有会话分叉出新的会话
codex fork <session-uuid>

# 交互式恢复
# 在会话中使用 /resume 命令
```

会话数据持久化存储，允许跨终端窗口、跨时间恢复工作上下文。

## 代码审查

### codex review 子命令

```bash
# 审查工作区未提交的更改
codex review --uncommitted

# 审查当前分支与 main 的差异
codex review --base main

# 审查特定 commit
codex review --commit abc1234
```

### /review 交互命令

在交互式会话中输入 `/review` 可启动代码审查模式，代理会分析当前更改并提供审查意见。

## 技能系统

Codex CLI 支持技能（Skills）系统，通过 `SKILL.md` 文件定义特定能力：

- **SKILL.md 文件**：定义技能的指令和行为
- **`/skill` 命令**：在交互中调用特定技能
- **`/skills` 命令**：列出所有可用技能
- **`skill_mcp_dependency_install`**：功能标志，控制技能 MCP 依赖的自动安装

## 功能标志

Codex CLI 内置了功能标志系统，可通过 `codex features` 查看：

| 标志 | 功能 |
|------|------|
| `guardian_approval` | 安全审查子代理（guardian sub-agent 自动审批） |
| `multi_agent` | 多代理协作 |
| `collaboration_modes` | 协作模式 |
| `codex_hooks` | 钩子系统 |
| `voice_transcription` | 语音转录输入 |
| `realtime_conversation` | 实时对话模式 |
| `shell_snapshot` | Shell 快照 |
