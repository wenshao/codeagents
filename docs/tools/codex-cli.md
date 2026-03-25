# Codex CLI

**开发者：** OpenAI
**许可证：** Apache-2.0
**仓库：** [github.com/openai/codex](https://github.com/openai/codex)
**Stars：** 约 20k+
**语言：** Rust（原生二进制）+ Node.js（薄启动层）
**最后更新：** 2026-03

## 概述

Codex CLI 是 OpenAI 官方推出的开源终端编程代理。项目采用 Apache-2.0 开源许可证，核心架构为**薄 Node.js 启动层 + 原生 Rust 二进制**——npm 包 `@openai/codex` 仅包含一个 `codex.js` 启动脚本，负责检测平台后 spawn 对应的 Rust 编译二进制（约 137MB，静态链接 musl libc）。内部捆绑 ripgrep 用于代码搜索。

主要特点：

- **OpenAI 第一方工具**：直接由 OpenAI 团队开发维护，与 OpenAI API 深度集成
- **Rust 原生性能**：核心为静态编译的 Rust 二进制，非纯 Node.js/TypeScript 应用
- **丰富的交互命令**：20+ 个斜杠命令，支持会话管理、代码审查、技能系统等
- **多种审批模式**：从完全受限到完全自主，精细控制代理行为
- **默认沙箱隔离**：macOS Seatbelt、Linux Bubblewrap/Landlock、Windows 受限令牌
- **MCP 双向支持**：既是 MCP 客户端也可作为 MCP 服务器
- **多模态输入**：支持传入截图和图片进行分析
- **代码审查系统**：独立的 `codex review` 子命令和交互式 `/review` 命令
- **会话持久化**：支持 resume/fork 恢复和分叉会话
- **Cloud 任务**（实验性）：提交任务到云端执行

## 架构

### 包结构

```
@openai/codex (npm)
├── bin/codex.js          # Node.js 启动脚本（~6KB）
├── bin/rg                # ripgrep 入口脚本
└── node_modules/
    └── @openai/codex-linux-x64/   # 平台特定包（示例）
        └── vendor/
            └── x86_64-unknown-linux-musl/
                └── codex/codex    # Rust 原生二进制（~137MB）
```

### 平台二进制包

| 平台包 | 目标三元组 |
|--------|-----------|
| `@openai/codex-linux-x64` | `x86_64-unknown-linux-musl` |
| `@openai/codex-linux-arm64` | `aarch64-unknown-linux-musl` |
| `@openai/codex-darwin-x64` | `x86_64-apple-darwin` |
| `@openai/codex-darwin-arm64` | `aarch64-apple-darwin` |
| `@openai/codex-win32-x64` | `x86_64-pc-windows-msvc` |
| `@openai/codex-win32-arm64` | `aarch64-pc-windows-msvc` |

启动流程：`codex.js` 检测 `process.platform` + `process.arch` -> 解析对应平台包 -> `spawn()` 原生二进制并透传所有参数和信号。

## 审批模式

Codex CLI 提供四种审批模式（approval mode），控制代理的自主程度：

> 验证方式：`codex --help` 输出确认仅接受 untrusted/on-request/on-failure/never 四种值。`codex -a granular` 返回 "error: invalid value 'granular'"。

### untrusted 模式（默认）

```bash
codex -a untrusted "重构这个函数"
# 或直接启动，默认就是 untrusted
codex
```

| 项目 | 说明 |
|------|------|
| 行为 | 仅执行受信任的命令，无需审批；其他操作需要用户确认 |
| 风险等级 | 最低 |
| 适用场景 | 学习代码、审查建议、不熟悉的代码库 |

### on-request 模式

```bash
codex -a on-request "修复这个 bug"
```

| 项目 | 说明 |
|------|------|
| 行为 | 模型自行决定何时请求用户审批 |
| 风险等级 | 中等 |
| 适用场景 | 日常开发、代码重构、bug 修复 |

### never 模式

```bash
codex -a never "修复所有测试并确保通过"
```

| 项目 | 说明 |
|------|------|
| 行为 | 从不请求审批，执行失败时将错误反馈给模型继续尝试 |
| 风险等级 | 较高（依赖沙箱保护） |
| 适用场景 | 批量任务、CI/CD 集成、自动化流水线 |

### on-failure 模式（已弃用）

此模式已标记为 DEPRECATED，不建议使用。

### 便捷标志

| 标志 | 等价于 |
|------|--------|
| `--full-auto` | `--ask-for-approval on-request --sandbox workspace-write` |
| `--dangerously-bypass-approvals-and-sandbox` (`--yolo`) | 完全绕过审批和沙箱（危险） |

## 沙箱模式

Codex CLI 提供三种沙箱级别：

| 模式 | 说明 |
|------|------|
| `read-only` | 仅允许读取，禁止任何写入 |
| `workspace-write` | 允许读取全局 + 写入工作目录和临时目录 |
| `danger-full-access` | 不启用沙箱，完全访问（危险） |

```bash
codex --sandbox workspace-write "修复 bug"
codex --sandbox read-only "分析代码"
```

### macOS 沙箱（Seatbelt）

macOS 上使用 `sandbox-exec` 和 seatbelt profiles 实现隔离：

- **网络访问**：完全阻断（deny network*）
- **文件写入**：仅允许当前工作目录（`$PWD`）和临时目录（`$TMPDIR`）
- **文件读取**：允许大部分系统路径（只读）
- **进程创建**：允许（在沙箱内）

### Linux 沙箱

Linux 上提供两种沙箱方案：

| 方案 | 工具 | 特点 |
|------|------|------|
| Bubblewrap（默认） | `bwrap` | 轻量级命名空间隔离，不需要 root 权限 |
| Landlock（遗留） | 内核 LSM | 内核级文件访问控制，作为备选方案 |

### Windows 沙箱（实验性）

Windows 上使用受限令牌（restricted token）实现隔离，目前为实验性支持。

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

## 交互式斜杠命令

Codex CLI 在交互式会话中提供 20+ 个斜杠命令：

### 会话管理

| 命令 | 功能 |
|------|------|
| `/clear` | 清除当前对话上下文 |
| `/compact` | 压缩对话历史，释放上下文窗口空间 |
| `/status` | 显示当前会话状态 |
| `/resume` | 恢复之前的会话 |
| `/fork` | 从当前会话分叉出新会话 |

> 验证方式：`/history`、`/undo` 未出现在 developers.openai.com/codex/cli/slash-commands 官方文档中，已移除。

### 代码与差异

| 命令 | 功能 |
|------|------|
| `/diff` | 显示当前会话产生的所有文件修改差异 |
| `/review` | 启动代码审查模式 |
| `/mention` | 提及/引用文件或符号，添加到上下文 |
| `/copy` | 复制最近的代理回复到剪贴板 |

### 模型与设置

| 命令 | 功能 |
|------|------|
| `/model` | 切换或查看当前模型 |
| `/permissions` | 查看或修改当前权限设置 |

> 验证方式：`/config` 未出现在 developers.openai.com/codex/cli/slash-commands 官方文档中，已移除。
| `/personality` | 查看或设置代理人格 |
| `/fast` | 切换快速模式 |
| `/debug-config` | 显示当前调试配置信息 |
| `/statusline` | 切换底部状态栏的显示/隐藏 |

### 高级功能

| 命令 | 功能 |
|------|------|
| `/plan` | 让代理制定计划而不执行 |
| `/feedback` | 向代理提供反馈，引导其调整行为 |

> 验证方式：`/help`、`/skills` 未出现在 developers.openai.com/codex/cli/slash-commands 官方文档中，已移除。
| `/mcp` | 管理 MCP 服务器连接 |
| `/ps` | 显示当前后台进程状态 |
| `/new` | 开始新的会话 |
| `/exit` | 退出当前会话 |
| `/quit` | 退出当前会话（同 /exit） |
| `/init` | 初始化项目配置（生成 CODEX.md 等） |
| `/logout` | 在 TUI 内登出当前账户 |

> 验证方式：`/login` 未出现在 developers.openai.com/codex/cli/slash-commands 官方文档中，已移除。
| `/sandbox-add-read-dir` | 将指定目录添加到沙箱的只读访问列表 |
| `/apps` | 管理应用集成 |
| `/experimental` | 访问实验性功能 |
| `/agent` | 代理相关操作 |

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
| `--ask-for-approval` | `-a` | 审批模式：untrusted/on-request/on-failure/never | `untrusted` |
| `--sandbox` | | 沙箱模式：read-only/workspace-write/danger-full-access | - |
| `--full-auto` | | `--ask-for-approval on-request --sandbox workspace-write` | - |
| `--config` | `-c` | 指定配置文件路径 | `~/.codex/config.toml` |
| `--oss` | | 使用本地 OSS 模型提供者 | - |
| `--local-provider` | | 指定本地模型提供者（lmstudio/ollama） | - |
| `--dangerously-bypass-approvals-and-sandbox` | `--yolo` | 绕过所有审批和沙箱（危险） | - |
| `--help` | `-h` | 显示帮助信息 | - |
| `--version` | `-V` | 显示版本号 | - |

> 验证方式：`codex --help` 确认 `--version` 简写为 `-V`（大写）而非 `-v`。`--quiet`、`--no-project-doc`、`--project-doc` 不在 `codex --help` 输出中，已移除。`granular` 不是有效的审批模式值。

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

## 模型支持

### GPT 系列

| 模型 | 说明 |
|------|------|
| `gpt-4.1` | GPT-4.1，大上下文窗口 |
| `gpt-5` | GPT-5 基础版 |
| `gpt-5.1` | GPT-5.1 |
| `gpt-5.1-codex` | GPT-5.1 Codex 优化版 |
| `gpt-5.1-codex-max` | GPT-5.1 Codex 最大规格 |
| `gpt-5.1-codex-mini` | GPT-5.1 Codex 轻量版 |
| `gpt-5.2` | GPT-5.2 |
| `gpt-5.2-codex` | GPT-5.2 Codex 优化版 |
| `gpt-5.3-codex` | GPT-5.3 Codex 优化版 |
| `gpt-5.4` | GPT-5.4 |
| `gpt-5.4-pro` | GPT-5.4 Pro |
| `gpt-5-mini` | GPT-5 轻量版 |
| `gpt-5-nano` | GPT-5 最轻量版 |

### 推理系列（o-系列）

| 模型 | 说明 |
|------|------|
| `o1` ~ `o9` | OpenAI 推理模型系列 |
| `o4-mini` | **默认模型**，快速且经济 |

### 本地模型支持

```bash
# 使用 LM Studio 本地模型
codex --oss --local-provider lmstudio "分析代码"

# 使用 Ollama 本地模型
codex --oss --local-provider ollama "写一个函数"
```

通过 `--oss` 和 `--local-provider` 可连接本地运行的模型服务。

### 自定义端点

```bash
# 使用第三方 OpenAI 兼容端点
export OPENAI_BASE_URL="https://your-proxy.example.com/v1"
export OPENAI_API_KEY="your-key"
codex --model your-model "写一个排序函数"
```

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

## Codex Cloud（实验性）

`codex cloud` 子命令允许将任务提交到云端执行：

```bash
# 提交云端任务
codex cloud exec "修复所有测试"

# 查看任务状态
codex cloud status <task-id>

# 列出所有云端任务
codex cloud list

# 应用云端任务的结果
codex cloud apply <task-id>

# 查看云端任务的差异
codex cloud diff <task-id>
```

Cloud 模式支持 best-of-N 多次尝试，选择最佳结果。此功能目前为实验性。

## App-Server 协议（IDE 集成）

`codex app-server` 启动 JSON-RPC 服务器，用于 VS Code 等 IDE 集成：

```bash
codex app-server
```

主要 JSON-RPC 方法：

| 方法 | 功能 |
|------|------|
| `thread/start` | 启动新对话线程 |
| `turn/start` | 开始新一轮对话 |
| `fs/readFile` | 读取文件内容 |
| `review/start` | 启动代码审查 |

## 多模态输入

Codex CLI 支持图片/截图输入，可以用于 UI 分析、bug 复现等场景。

```bash
# 交互式会话中粘贴图片（拖拽或剪贴板粘贴）
codex
# 然后在对话中粘贴截图

# 通过管道传入
cat error.log | codex "分析这个错误日志"
```

支持的格式：PNG、JPEG、GIF、WebP

## 安装

```bash
# 通过 npm 全局安装
npm install -g @openai/codex

# 或通过 bun
bun install -g @openai/codex

# 设置 API key
export OPENAI_API_KEY="sk-..."

# 验证安装
codex --version

# 启动交互式会话
codex
```

### 系统要求

- **Node.js**：>= 22
- **操作系统**：macOS 12+、Ubuntu 22.04+/Debian 12+、Windows（实验性原生 + WSL2）
- **Git**：推荐安装（用于版本控制和审查功能）

## 定价

Codex CLI 本身免费开源，但使用 OpenAI API 需要付费。费用取决于所选模型和 token 用量。

### 模型定价参考

| 模型 | 输入价格（每百万 token） | 输出价格（每百万 token） |
|------|--------------------------|--------------------------|
| `o4-mini` | $1.10 | $4.40 |
| `gpt-4.1` | $2.00 | $8.00 |

> 注：以上价格为 OpenAI 官方 API 定价，可能随时调整。GPT-5 系列定价请参考 OpenAI 官网。

### 成本控制建议

- 日常简单任务使用默认 `o4-mini`，成本最低
- 仅在需要强推理能力时使用高级模型
- 使用 `/compact` 命令压缩上下文，减少 token 消耗
- 通过 CODEX.md 提供清晰的项目上下文，减少模型试错

## 优势

1. **OpenAI 官方**：第一方支持，模型兼容性最佳
2. **开源**：Apache-2.0 许可，可自由修改和部署
3. **Rust 原生性能**：核心为静态编译 Rust 二进制，启动快、内存效率高
4. **安全沙箱**：多平台沙箱隔离（Seatbelt/Bubblewrap/Landlock/受限令牌）
5. **MCP 双向支持**：既是客户端也可作为 MCP 服务器
6. **丰富的交互命令**：20+ 个斜杠命令覆盖开发全流程
7. **会话持久化**：支持 resume/fork，跨时间恢复工作
8. **代码审查**：内置 review 子命令和交互式审查
9. **Cloud 任务**：实验性云端执行支持 best-of-N
10. **IDE 集成**：app-server 提供 JSON-RPC 协议供编辑器对接

## 劣势

1. **模型锁定**：主要支持 OpenAI 模型（可通过兼容端点或 --oss 部分绕过）
2. **二进制体积大**：平台包约 137MB，下载和安装耗时
3. **Windows 支持有限**：原生 Windows 沙箱仍为实验性
4. **Cloud 功能未稳定**：cloud 子命令标记为实验性
5. **文档滞后**：官方文档未完整覆盖所有功能

## 使用场景

- **最适合**：OpenAI API 用户、需要安全沙箱的自动化场景、CI/CD 集成、代码审查
- **适合**：日常代码编辑、快速原型、bug 修复、代码重构、多工具集成（通过 MCP）
- **不太适合**：需要多模型供应商切换、对二进制体积敏感的环境

## 与其他工具对比

| 特性 | Codex CLI | Claude Code | Qwen Code | Aider | Gemini CLI |
|------|----------|-------------|-----------|-------|------------|
| 开源 | Apache-2.0 | 闭源 | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| 默认模型 | o4-mini | Claude Sonnet | Qwen3 | 多模型 | Gemini 2.5 Pro |
| 多模型支持 | OpenAI + OSS | 仅 Claude | 多模型 | 多模型 | 仅 Gemini |
| 沙箱 | 默认启用 | 可选 | 可选 | 无 | 可选 |
| 网络隔离 | 默认 | 可选 | 无 | 无 | 无 |
| MCP 支持 | 客户端+服务器 | 客户端 | 有 | 无 | 有 |
| Git 集成 | review 子命令 | 有 | 无 | 自动提交 | 无 |
| 多模态 | 图片 | 图片 | 图片 | 无 | 图片 |
| 交互命令 | 20+ 斜杠命令 | 斜杠命令 | 斜杠命令 | 斜杠命令 | 斜杠命令 |
| 会话持久化 | resume/fork | 有 | 无 | 无 | resume |
| 项目指令 | CODEX.md/AGENTS.md | CLAUDE.md | - | .aider* | GEMINI.md |
| 技术栈 | Rust + Node.js | Rust/TypeScript | TypeScript | Python | TypeScript/Ink |
| Cloud 执行 | 实验性 | 无 | 无 | 无 | 无 |
| 定价模式 | API 按量 | API 按量/订阅 | API 按量 | 免费+API | API 按量 |

## 资源链接

- [GitHub 仓库](https://github.com/openai/codex)
- [OpenAI 公告](https://openai.com/index/introducing-codex/)
- [npm 包](https://www.npmjs.com/package/@openai/codex)
