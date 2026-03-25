# Codex CLI

**开发者：** OpenAI
**许可证：** Apache-2.0
**仓库：** [github.com/openai/codex](https://github.com/openai/codex)
**Stars：** 约 20k+
**语言：** TypeScript（Ink + React TUI）
**最后更新：** 2026-03

## 概述

Codex CLI 是 OpenAI 官方推出的开源终端编程代理，代号"lightweight coding agent that runs in your terminal"。项目基于 TypeScript 构建，使用 Ink + React 渲染终端界面（TUI），采用 Apache-2.0 开源许可证。Codex CLI 的核心设计理念是**安全第一**——默认在网络隔离的沙箱中执行所有命令，防止恶意代码或意外操作对系统造成危害。

主要特点：

- **OpenAI 第一方工具**：直接由 OpenAI 团队开发维护，与 OpenAI API 深度集成
- **终端原生体验**：基于 Ink + React 的现代 CLI 界面，支持富文本输出
- **三种自主级别**：从建议模式到完全自主，用户可精细控制代理行为
- **默认网络隔离**：沙箱机制阻断网络访问，限制文件写入范围
- **多平台支持**：macOS（seatbelt）、Linux（Docker/Bubblewrap）、Windows（WSL2）
- **多模态输入**：支持传入截图和图片进行分析
- **Function Calling**：使用 OpenAI 结构化工具调用协议

## 三种自主级别

Codex CLI 提供三种审批模式（approval mode），控制代理的自主程度：

### suggest 模式（建议模式）

```bash
codex --approval-mode suggest "重构这个函数"
# 或直接启动，默认就是 suggest
codex
```

| 项目 | 说明 |
|------|------|
| 文件读取 | 需要用户确认 |
| 文件写入 | 需要用户确认 |
| 命令执行 | 需要用户确认 |
| 风险等级 | 最低 |
| 适用场景 | 学习代码、审查建议、不熟悉的代码库 |

代理会生成建议的命令或代码修改，但**不会自动执行任何操作**。每一步都需要用户显式确认后才会执行。适合初次使用或对代码库不熟悉时使用。

### auto-edit 模式（自动编辑模式）

```bash
codex --approval-mode auto-edit "修复这个 bug"
```

| 项目 | 说明 |
|------|------|
| 文件读取 | 自动执行 |
| 文件写入 | 自动执行 |
| 命令执行 | 需要用户确认 |
| 风险等级 | 中等 |
| 适用场景 | 日常开发、代码重构、bug 修复 |

代理可以**自动读写文件**，但执行 shell 命令仍需用户确认。这是日常开发中最常用的模式，兼顾效率和安全性。

### full-auto 模式（完全自主模式）

```bash
codex --approval-mode full-auto "修复所有测试并确保通过"
# 简写形式
codex --full-auto "修复所有测试"
```

| 项目 | 说明 |
|------|------|
| 文件读取 | 自动执行 |
| 文件写入 | 自动执行 |
| 命令执行 | 自动执行（沙箱内） |
| 风险等级 | 较高（依赖沙箱保护） |
| 适用场景 | 批量任务、CI/CD 集成、自动化流水线 |

代理完全自主执行所有操作，**必须在沙箱环境中运行**。适合批量处理、自动化任务或 CI/CD 流水线集成。

## 沙箱机制详情

Codex CLI 的沙箱是其核心安全特性，**默认启用网络隔离**，并限制文件写入范围。

### macOS 沙箱（seatbelt）

macOS 上使用 `sandbox-exec` 和 seatbelt profiles 实现隔离：

- **网络访问**：完全阻断（deny network*）
- **文件写入**：仅允许当前工作目录（`$PWD`）和临时目录（`$TMPDIR`）
- **文件读取**：允许大部分系统路径（只读）
- **进程创建**：允许（在沙箱内）

### Linux 沙箱

Linux 上提供两种沙箱方案：

| 方案 | 工具 | 特点 |
|------|------|------|
| Docker | `docker run` | 完整容器隔离，资源限制 |
| Bubblewrap | `bwrap` | 轻量级命名空间隔离，启动快 |

- **Docker 模式**：将工作目录挂载到容器内，容器内无网络访问
- **Bubblewrap 模式**：使用 Linux 命名空间隔离，不需要 root 权限

### 可写目录配置

可以通过配置指定额外的可写目录：

```yaml
# ~/.codex/config.yaml
sandbox:
  writable_dirs:
    - /tmp
    - /home/user/projects
```

### Windows

Windows 不直接支持，需通过 WSL2 运行，沙箱机制与 Linux 相同。

## 多模态输入

Codex CLI 支持图片/截图输入，可以用于 UI 分析、bug 复现等场景。

### 使用方式

```bash
# 直接在交互式会话中粘贴图片（拖拽或剪贴板粘贴）
codex
# 然后在对话中粘贴截图

# 通过文件路径传入图片
codex "分析这个截图中的 UI 问题" < screenshot.png
```

支持的格式：PNG、JPEG、GIF、WebP

典型使用场景：
- 根据设计稿实现 UI
- 分析截图中的报错信息
- 对比设计稿和实际效果的差异

## 工具系统

Codex CLI 使用 OpenAI Function Calling 协议，内置以下工具：

| 工具 | 功能 | 说明 |
|------|------|------|
| `shell` | 执行 shell 命令 | 在沙箱中执行，受审批模式控制 |
| `read_file` | 读取文件内容 | 支持读取任意文本文件 |
| `write_file` | 写入文件 | 创建或覆盖文件 |
| `apply_patch` | 应用补丁 | 使用 unified diff 格式精确修改文件 |

### apply_patch 工具

`apply_patch` 是 Codex CLI 的核心编辑工具，使用类 unified diff 格式：

```
*** Begin Patch
*** Update File: src/main.ts
@@@ -10,3 +10,4 @@@
 import { foo } from './foo';
 import { bar } from './bar';
+import { baz } from './baz';

*** End Patch
```

该工具允许模型精确修改文件的特定部分，而不需要重写整个文件。

## CODEX.md 配置

`CODEX.md` 是 Codex CLI 的项目级指令文件，类似于 Claude Code 的 `CLAUDE.md`。代理在启动时会自动读取该文件作为系统提示的一部分。

### 文件位置与层级

| 位置 | 作用域 | 优先级 |
|------|--------|--------|
| `~/.codex/instructions.md` | 全局（用户级） | 最低 |
| 项目根目录 `CODEX.md` | 项目级 | 中 |
| 当前目录 `CODEX.md` | 目录级 | 最高 |

### 推荐内容

```markdown
# CODEX.md

## 项目概述
这是一个 React + TypeScript 的前端项目。

## 技术栈
- React 18
- TypeScript 5
- Tailwind CSS

## 编码规范
- 使用函数组件和 Hooks
- 文件名使用 kebab-case
- 组件名使用 PascalCase

## 测试
- 使用 Vitest 运行测试：`npm test`
- 测试文件放在 `__tests__` 目录

## 构建
- 开发：`npm run dev`
- 生产：`npm run build`
```

## 配置详情

### 配置文件

Codex CLI 支持 YAML 和 JSON 两种配置格式：

```yaml
# ~/.codex/config.yaml
model: o4-mini
approval_mode: auto-edit
```

```json
// ~/.codex/config.json
{
  "model": "o4-mini",
  "approval_mode": "auto-edit"
}
```

### 环境变量

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥（必需） | `sk-proj-...` |
| `OPENAI_BASE_URL` | 自定义 API 端点 | `https://api.openai.com/v1` |
| `OPENAI_ORG_ID` | OpenAI 组织 ID | `org-...` |
| `CODEX_HOME` | Codex 配置目录 | `~/.codex` |

### 自定义模型端点

通过 `OPENAI_BASE_URL` 可以连接 OpenAI 兼容的第三方 API：

```bash
# 使用第三方 OpenAI 兼容端点
export OPENAI_BASE_URL="https://your-proxy.example.com/v1"
export OPENAI_API_KEY="your-key"
codex --model your-model "写一个排序函数"
```

## 模型支持

### 官方支持模型

| 模型 | 说明 | 特点 |
|------|------|------|
| `o4-mini` | **默认模型** | 快速、经济，适合日常编码 |
| `o3` | 高级推理模型 | 更强的推理能力，适合复杂任务 |
| `o3-mini` | 轻量推理模型 | 推理能力与成本的平衡 |
| `gpt-4.1` | GPT-4.1 | 大上下文窗口，强代码能力 |
| `gpt-4.1-mini` | GPT-4.1 Mini | 轻量版 GPT-4.1 |
| `gpt-4.1-nano` | GPT-4.1 Nano | 最轻量，最低延迟 |
| `gpt-4o` | GPT-4o | 多模态模型 |

### 模型选择建议

```bash
# 日常编码（默认，快速且经济）
codex "实现登录功能"

# 复杂架构设计（使用 o3）
codex --model o3 "重新设计这个模块的架构"

# 大文件分析（使用 gpt-4.1，上下文窗口大）
codex --model gpt-4.1 "分析这个大型代码库"
```

### 自定义模型

通过 OpenAI 兼容端点可以使用第三方模型，但 Codex CLI 主要针对 OpenAI 模型优化，第三方模型可能存在兼容性问题。

## CLI 命令详情

### 基本用法

```bash
codex [选项] [提示词]
```

### 完整参数参考

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--model` | `-m` | 指定使用的模型 | `o4-mini` |
| `--approval-mode` | | 审批模式：suggest/auto-edit/full-auto | `suggest` |
| `--full-auto` | | `--approval-mode full-auto` 的简写 | - |
| `--quiet` | `-q` | 安静模式，减少输出 | `false` |
| `--config` | `-c` | 指定配置文件路径 | `~/.codex/config.yaml` |
| `--no-project-doc` | | 不加载 CODEX.md | `false` |
| `--project-doc` | | 指定额外的项目指令文件 | - |
| `--help` | `-h` | 显示帮助信息 | - |
| `--version` | `-v` | 显示版本号 | - |

### 使用示例

```bash
# 交互式会话（默认 suggest 模式）
codex

# 直接执行任务
codex "重构这个函数，添加类型注解"

# 完全自主模式 + 指定模型
codex --full-auto --model o3 "修复所有 lint 错误并运行测试"

# 安静模式（适合脚本集成）
codex -q "生成 API 文档"

# 指定额外项目指令
codex --project-doc ./docs/INSTRUCTIONS.md "按照规范开发"

# 管道输入
cat error.log | codex "分析这个错误日志"
```

## 安装

```bash
# 通过 npm 全局安装
npm install -g @openai/codex

# 设置 API key
export OPENAI_API_KEY="sk-..."

# 验证安装
codex --version

# 启动交互式会话
codex
```

### 系统要求

- **Node.js**：>= 22
- **操作系统**：macOS 12+、Ubuntu 22.04+/Debian 12+、Windows（WSL2）
- **Git**：推荐安装（用于版本控制相关功能）

## 定价

Codex CLI 本身免费开源，但使用 OpenAI API 需要付费。费用取决于所选模型和 token 用量。

### 模型定价参考

| 模型 | 输入价格（每百万 token） | 输出价格（每百万 token） |
|------|--------------------------|--------------------------|
| `o4-mini` | $1.10 | $4.40 |
| `o3` | $2.00 | $8.00 |
| `gpt-4.1` | $2.00 | $8.00 |
| `gpt-4.1-mini` | $0.40 | $1.60 |
| `gpt-4.1-nano` | $0.10 | $0.40 |
| `gpt-4o` | $2.50 | $10.00 |

> 注：以上价格为 OpenAI 官方 API 定价，可能随时调整。实际费用取决于任务复杂度和对话长度。

### 成本控制建议

- 日常简单任务使用默认 `o4-mini`，成本最低
- 仅在需要强推理能力时使用 `o3`
- 使用 `--quiet` 模式减少不必要的输出 token
- 通过 CODEX.md 提供清晰的项目上下文，减少模型试错

## 优势

1. **OpenAI 官方**：第一方支持，模型兼容性最佳
2. **开源**：Apache-2.0 许可，可自由修改和部署
3. **安全沙箱**：默认网络隔离，业界领先的安全机制
4. **简洁设计**：专注 CLI 体验，低复杂度，易于上手
5. **多平台沙箱**：macOS/Linux/Windows 均有隔离方案
6. **灵活的自主级别**：三种模式适应不同场景需求

## 劣势

1. **模型锁定**：仅支持 OpenAI 模型（可通过兼容端点部分绕过）
2. **功能较简**：相比 Claude Code、Qwen Code 功能较少
3. **无 MCP 支持**：不支持模型上下文协议，无法扩展工具
4. **无 Git 原生集成**：不像 Aider 那样自动提交代码
5. **无 Web 搜索**：不支持联网搜索（沙箱设计决定）
6. **编辑能力有限**：主要依赖 apply_patch，不如一些工具的多样化编辑方式

## 使用场景

- **最适合**：OpenAI API 用户、需要安全沙箱的自动化场景、CI/CD 集成
- **适合**：日常代码编辑、快速原型、bug 修复、代码重构
- **不太适合**：需要多模型切换、复杂 Git 工作流、需要 MCP 扩展的场景

## 与其他工具对比

| 特性 | Codex CLI | Claude Code | Qwen Code | Aider | Gemini CLI |
|------|----------|-------------|-----------|-------|------------|
| 开源 | Apache-2.0 | 闭源 | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| 默认模型 | o4-mini | Claude Sonnet | Qwen3 | 多模型 | Gemini 2.5 Pro |
| 多模型支持 | 仅 OpenAI | 仅 Claude | 多模型 | 多模型 | 仅 Gemini |
| 沙箱 | 默认启用 | 可选 | 可选 | 无 | 可选 |
| 网络隔离 | 默认 | 可选 | 无 | 无 | 无 |
| MCP 支持 | 无 | 有 | 有 | 无 | 有 |
| Git 集成 | 无 | 有 | 无 | 自动提交 | 无 |
| 多模态 | 图片 | 图片 | 图片 | 无 | 图片 |
| 自主级别 | 3 级 | 2 级 | 3 级 | 1 级 | 3 级 |
| 项目指令 | CODEX.md | CLAUDE.md | - | .aider* | GEMINI.md |
| 技术栈 | TypeScript/Ink | Rust/TypeScript | TypeScript | Python | TypeScript/Ink |
| 定价模式 | API 按量 | API 按量/订阅 | API 按量 | 免费+API | API 按量 |

## 资源链接

- [GitHub 仓库](https://github.com/openai/codex)
- [OpenAI 公告](https://openai.com/index/introducing-codex/)
- [npm 包](https://www.npmjs.com/package/@openai/codex)
