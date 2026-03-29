# 5. 系统要求对比

> 各工具的运行环境要求。动态运行时版本与体积信息如有变化，请优先参考 [`../data/CHANGELOG.md`](../data/CHANGELOG.md) 记录的最近更新时间，并结合源码/安装包重新验证。

## 语言与运行时要求

| Agent | 实现语言 | 运行时 | 最低版本 | 安装方式 |
|------|---------|--------|---------|---------|
| **Claude Code** | TypeScript (Bun 编译) | **Bun**（内嵌，无需安装） | — | `curl install.sh \| bash` / `brew install` |
| **Copilot CLI** | TypeScript (Node.js SEA) | **Node.js ≥ 24**（回退模式） | v24+ | `curl install.sh \| bash` / `brew` / `npm` / `winget` |
| **Codex CLI** | Rust + Node.js 包装 | **Node.js ≥ 16**（仅启动器） | v16+ | `npm install -g @openai/codex` |
| **Gemini CLI** | TypeScript | **Node.js ≥ 20** | v20+ | `npm install -g @google/gemini-cli` |
| **Qwen Code** | TypeScript | **Node.js ≥ 20** | v20+ | `npm install -g @qwen-code/qwen-code` / `brew` |
| **Aider** | Python | **Python ≥ 3.10, < 3.15** | v3.10+ | `pip install aider-chat` / `brew` / `uv` |
| **Kimi CLI** | Python | **Python ≥ 3.12** | v3.12+ | `uv tool install kimi-cli` / `pip` |
| **Goose** | Rust | **Rust 1.92+**（编译时） | — | `brew install goose` / `cargo install` |
| **OpenCode** | TypeScript（Bun） | Bun 1.3+ | — | `brew install opencode` / `go install` |

> **注意：**
> - Claude Code 不依赖 Node.js——它是 Bun 编译的独立二进制
> - Copilot CLI 优先使用原生二进制，仅在回退时需要 Node.js ≥ 24（要求最高）
> - Codex CLI 的 Node.js 要求仅用于 npm 启动器（6KB），实际逻辑在 Rust 二进制中

## 操作系统支持

| Agent | macOS | Linux | Windows | WSL | Docker |
|------|-------|-------|---------|-----|--------|
| **Claude Code** | ✓ | ✓ | WSL 推荐 | ✓ | ✓ |
| **Copilot CLI** | ✓ | ✓ | ✓（原生） | ✓ | — |
| **Codex CLI** | ✓ (x64+arm64) | ✓ (x64+arm64) | ✓ (x64+arm64) | ✓ | — |
| **Gemini CLI** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Qwen Code** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Aider** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Kimi CLI** | ✓ | ✓ | WSL 推荐 | ✓ | — |
| **Goose** | ✓ | ✓ | WSL 推荐 | ✓ | — |
| **OpenCode** | ✓ | ✓ | ✓ | ✓ | — |

## 二进制大小

> 安装体积和包大小属于高频变化信息，详细数值建议与 `docs/data/CHANGELOG.md` 一起维护；本表保留量级与组成说明。

| Agent | 体积量级 | 包含内容 |
|------|---------|---------|
| **Claude Code** | ~200MB+ | Bun 运行时 + JS bundle + 原生模块 (tree-sitter, sharp, audio) |
| **Copilot CLI** | ~100MB+ | Node.js SEA + JS bundle + 原生模块 (keytar, pty) |
| **Codex CLI** | ~100MB+ | Rust 静态链接 (musl) + ripgrep |
| **Goose** | ~50MB | Rust 编译 (rmcp SDK) |
| **Gemini CLI** | ~50MB | TypeScript + WASM (tree-sitter) |
| **Qwen Code** | ~50MB | TypeScript + WASM (tree-sitter) |
| **Aider** | ~20MB | Python 包 + 依赖 |
| **Kimi CLI** | ~15MB | Python 包 + 依赖 |

## 沙箱依赖

| Agent | macOS 沙箱 | Linux 沙箱 | Windows 沙箱 |
|------|-----------|-----------|-------------|
| **Claude Code** | sandbox-exec (内置) | Docker (需安装) | — |
| **Codex CLI** | sandbox-exec (内置) | Bubblewrap/Landlock (需安装) | Restricted Tokens (内置) |
| **Gemini CLI** | sandbox-exec (内置) | seccomp BPF (内核支持) | C# 实现 (内置) |
| **Aider** | 无沙箱 | 无沙箱 | 无沙箱 |
| **Kimi CLI** | 无沙箱 | 无沙箱 | 无沙箱 |
| **Goose** | 无沙箱 | 无沙箱 | 无沙箱 |

## 网络要求

| Agent | 必需的网络访问 | 离线模式 |
|------|--------------|---------|
| **Claude Code** | Anthropic API (api.anthropic.com) | ✗（需要 API） |
| **Copilot CLI** | GitHub API (api.githubcopilot.com) | ✗ |
| **Codex CLI** | OpenAI API | 部分（--oss 本地模型） |
| **Aider** | 所选模型的 API | 部分（Ollama 本地模型） |
| **Gemini CLI** | Google API | ✗ |
| **Qwen Code** | DashScope/所选 API | 部分（本地模型） |
| **Kimi CLI** | Moonshot/所选 API | 部分（本地模型） |
| **Goose** | 所选模型的 API | 部分（Ollama 本地模型） |
| **OpenCode** | 所选模型的 API | 部分（本地模型） |

### Qoder CLI 补充

| 项目 | 值 |
|------|-----|
| 实现语言 | Go |
| 运行时 | 无需额外运行时（静态链接二进制） |
| 二进制大小 | ~40MB |
| 安装 | `npm install -g @qoder-ai/qodercli` |
| Node.js 要求 | 仅 npm 安装需要（二进制本身不依赖 Node.js） |
