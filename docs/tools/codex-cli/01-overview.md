# 1. Codex CLI 概述

**开发者：** OpenAI
**许可证：** Apache-2.0
**仓库：** [github.com/openai/codex](https://github.com/openai/codex)
**Stars：** ~68k
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

## 审批模式

Codex CLI 提供五种审批模式（approval mode），控制代理的自主程度：

> 验证方式：`codex --help` 输出确认 v0.116.0 二进制仅接受 untrusted/on-request/on-failure/never 四种值。`granular` 模式已在官方文档（developers.openai.com/codex/agent-approvals-security）中列出，但 v0.116.0 二进制尚未实现。`on-failure` 已从官方文档中完全移除，仅在二进制中保留向后兼容。

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

此模式已标记为 DEPRECATED，不建议使用。官方文档（developers.openai.com/codex/agent-approvals-security）已完全移除此模式，仅在 v0.116.0 二进制中保留向后兼容支持。

### granular 模式（官方文档确认，二进制未实现）

```bash
codex -a granular "精细控制审批"
# 注意：v0.116.0 返回 "error: invalid value 'granular'"
```

| 项目 | 说明 |
|------|------|
| 行为 | 细粒度控制：可分别配置 sandbox、rules、MCP、权限、skill 的审批策略 |
| 状态 | 官方文档确认，v0.116.0 二进制未实现（`codex -a granular` 返回 error），可能在更新版本中添加 |
| 适用场景 | 需要对不同操作类别设置不同审批策略的高级用户 |

### 便捷标志

| 标志 | 等价于 |
|------|--------|
| `--full-auto` | `--ask-for-approval on-request --sandbox workspace-write` |
| `--dangerously-bypass-approvals-and-sandbox` (`--yolo`) | 完全绕过审批和沙箱（危险） |

## 沙箱机制

Codex CLI 提供四种沙箱级别：

| 模式 | 说明 |
|------|------|
| `read-only` | 仅允许读取，禁止任何写入 |
| `restricted-read-access` | 平台策划的受限读取策略（macOS 专用），使用 Seatbelt 限制可读取的目录范围 |
| `workspace-write` | 允许读取全局 + 写入工作目录和临时目录 |
| `danger-full-access` | 不启用沙箱，完全访问（危险） |

```bash
codex --sandbox workspace-write "修复 bug"
codex --sandbox read-only "分析代码"
```

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

## 使用场景

- **最适合**：OpenAI API 用户、需要安全沙箱的自动化场景、CI/CD 集成、代码审查
- **适合**：日常代码编辑、快速原型、bug 修复、代码重构、多工具集成（通过 MCP）
- **不太适合**：需要多模型供应商切换、对二进制体积敏感的环境

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

## 验证记录

> 本文档通过二进制逆向分析和官方文档双重验证。

**二进制分析（v0.116.0，137MB ELF static-pie x86-64 Rust）：**
- CLI 子命令：通过 `codex --help` 确认 15 个子命令
- 审批模式：v0.116.0 二进制仅接受 untrusted/on-request/on-failure/never（granular 返回 invalid value 错误）；第六轮 Web 验证确认官方文档已列出 granular 模式并移除 on-failure 模式
- TUI 斜杠命令：通过 `strings` 提取 + 官方文档交叉验证确认 28 个
- Feature flags：通过 `codex features list` 确认 50+ 个
- 系统身份：确认 "You are Codex, based on GPT-5."
- App-Server 协议：通过 IPC 消息字符串提取确认 40+ 方法

**官方文档验证：**
- [斜杠命令](https://developers.openai.com/codex/cli/slash-commands) — 28 个命令完整列表
- [CLI 参考](https://developers.openai.com/codex/cli/reference) — 确认 `--ask-for-approval`（非 --approval-mode）
- [审批与安全](https://developers.openai.com/codex/agent-approvals-security)
- [Linux 沙箱](https://github.com/openai/codex/blob/main/codex-rs/linux-sandbox/README.md)

**已修正的错误（第二轮验证发现）：**
- `--approval-mode` → `--ask-for-approval`（二进制 --help 确认）
- `granular` 审批模式：v0.116.0 二进制未实现（`codex -a granular` 返回 error），但第六轮 Web 验证确认官方文档已列出，已恢复并标注
- 移除 6 个未经验证的斜杠命令（官方文档中不存在）
- 移除 3 个伪造的 CLI 参数（--quiet, --no-project-doc, --project-doc）

## 资源链接

- [GitHub 仓库](https://github.com/openai/codex)
- [OpenAI 公告](https://openai.com/index/introducing-codex/)
- [npm 包](https://www.npmjs.com/package/@openai/codex)
