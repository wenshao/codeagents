# Codex CLI

**开发者：** OpenAI
**许可证：** Apache-2.0
**仓库：** [github.com/openai/codex](https://github.com/openai/codex)
**Stars：** 约 20k+

## 概述

Codex CLI 是 OpenAI 官方的开源终端编程代理。基于 TypeScript 构建（Ink + React TUI），使用 OpenAI 模型（GPT-4o、o3、o4-mini 等），特色是网络隔离沙箱执行和多平台支持（macOS、Linux、Windows via WSL2）。

## 核心功能

### 基础能力
- **终端原生**：基于 Ink + React 的 CLI
- **沙箱执行**：默认网络隔离，文件写入限制在当前目录和临时目录
- **多平台**：macOS（seatbelt）、Linux（Docker）、Windows（WSL2）
- **OpenAI 模型**：GPT-4o、o3、o4-mini、o3-mini 等
- **Function Calling**：结构化工具调用

### 独特功能
- **三种自主级别**：
  - `suggest`：仅建议命令，需确认后执行
  - `auto-edit`：自动读写文件，命令需确认
  - `full-auto`：完全自主（需沙箱）
- **网络隔离沙箱**：macOS 用 seatbelt profiles，Linux 用 Docker
- **多模态输入**：支持图片粘贴
- **CODEX.md 项目指令**：类似 Claude Code 的 CLAUDE.md

## 安装

```bash
# npm
npm install -g @openai/codex

# 设置 API key
export OPENAI_API_KEY="sk-..."

# 启动
codex
```

## 架构

- **语言**：TypeScript
- **CLI 框架**：Ink + React
- **主要模型**：GPT-4o（默认）、o3、o4-mini
- **沙箱**：
  - macOS：seatbelt（`sandbox-exec`）
  - Linux：Docker 容器
  - Windows：WSL2

## 优势

1. **OpenAI 官方**：第一方支持
2. **开源**：Apache-2.0 许可
3. **安全沙箱**：默认网络隔离
4. **简洁**：专注 CLI 体验，低复杂度
5. **多平台沙箱**：macOS/Linux/Windows 均有隔离

## 劣势

1. **模型锁定**：仅支持 OpenAI 模型
2. **功能较简**：相比 Claude Code、Qwen Code 功能较少
3. **无 MCP**：不支持模型上下文协议
4. **无 Git 原生集成**：不像 Aider 自动提交

## CLI 命令

```bash
# 交互式会话
codex

# 直接提问
codex "重构这个函数"

# 指定自主级别
codex --approval-mode full-auto "修复所有测试"

# 指定模型
codex --model o3 "分析代码架构"

# 安静模式
codex -q "添加错误处理"
```

## 配置

```yaml
# ~/.codex/config.yaml 或 codex.yaml
model: gpt-4o
approval_mode: suggest
```

项目级指令通过 `CODEX.md` 文件提供。

## 使用场景

- **最适合**：OpenAI 用户、需要安全沙箱的场景
- **适合**：简单代码编辑、快速原型
- **不太适合**：需要多模型切换、复杂 Git 工作流

## 与其他工具对比

| 特性 | Codex CLI | Claude Code | Qwen Code |
|------|----------|-------------|-----------|
| 开源 | ✓ | | ✓ |
| 多模型 | | | ✓ |
| 沙箱 | ✓（默认） | ✓（可选） | ✓（可选） |
| MCP | | ✓ | ✓ |
| Git 原生 | | ✓ | |

## 资源链接

- [GitHub](https://github.com/openai/codex)
- [OpenAI 公告](https://openai.com/index/introducing-codex/)
