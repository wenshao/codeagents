# 34. 终端 UI/UX 框架深度对比

> 终端 UI 决定了开发者与 AI 代理的交互体验。从 Python prompt_toolkit 到 Ink+React 到 Rust 原生 GPU 渲染，技术栈选择影响启动速度、交互流畅度和扩展能力。

## 总览

| 工具 | UI 框架 | 语言 | Vim 模式 | 主题 | 多客户端 | 启动速度 |
|------|--------|------|---------|------|---------|---------|
| **Claude Code** | Ink + React（Bun 编译） | Rust | ✓ `/vim` | ✓ `/theme` `/color` | 终端 + Desktop + Mobile + Chrome | 亚秒级 |
| **Gemini CLI** | Ink 6 + React 19 | TypeScript | ✗ | ✗ | 终端 | ~2-3 秒 |
| **Qwen Code** | Ink 6 + React 19（继承） | TypeScript | ✓ `/vim` | ✓ `/theme` | 终端 + Arena 多终端 | ~2-3 秒 |
| **Copilot CLI** | Ink（React for CLI） | TypeScript(SEA) | ✗ | ✗ | 终端 | ~1-2 秒 |
| **Aider** | prompt_toolkit + Rich | Python | ✗ | ✗ | 终端 | ~1 秒 |
| **Kimi CLI** | prompt_toolkit + Rich | Python | ✓（配置） | ✗ | 终端 + Web UI | ~1 秒 |
| **OpenCode** | **OpenTUI + Solid.js** | Go + TS | ✗ | **✓（37 种）** | TUI + Web + Tauri Desktop | ~1 秒 |
| **Goose** | Rust CLI + Electron | Rust | ✗ | ✓ Light/Dark/Ansi | CLI + Desktop | 亚秒级 |
| **Codex CLI** | Rust 原生 TUI | Rust | ✗ | ✗ | 终端 | 亚秒级 |
| **SWE-agent** | Textual + Rich | Python | ✗ | ✗ | 终端 + Web Inspector | ~2 秒 |
| **OpenHands** | FastAPI + React | Python | ✗ | ✗ | **Web UI** | ~5 秒 |
| **Cline** | VS Code WebView + React | TypeScript | ✗ | IDE 主题 | **IDE 原生** | IDE 启动 |
| **Warp** | Rust + Metal/Vulkan | Rust | ✓ | ✓（YAML） | **GPU 终端** | 亚秒级 |

---

## 三大 UI 技术流派

### 1. Ink + React（终端 React 组件）

**使用者**：Claude Code、Gemini CLI、Qwen Code、Copilot CLI

```
React 组件 → Ink 渲染引擎 → Yoga 布局计算 → ANSI 终端输出
```

**优势**：组件化开发、声明式 UI、React 生态复用
**劣势**：Node.js/Bun 运行时依赖、内存占用较高

### 2. prompt_toolkit + Rich（Python 终端）

**使用者**：Aider、Kimi CLI

```
prompt_toolkit（输入处理 + 补全）+ Rich（富文本渲染 + 颜色 + 表格）
```

**优势**：最轻量、Python 生态成熟、学术研究友好
**劣势**：UI 复杂度受限、无组件化

### 3. Rust 原生 / GPU 渲染

**使用者**：Goose、Codex CLI、Warp

```
Rust 原生 CLI / Metal(macOS) + Vulkan(Linux/Win) GPU 渲染
```

**优势**：最快启动、最低内存、跨平台原生性能
**劣势**：UI 开发门槛高、插件生态受限

---

## 独特 UI 创新

| 创新 | 工具 | 说明 |
|------|------|------|
| **37 种内置主题** | OpenCode | 目前主题最丰富的 CLI 工具 |
| **命令面板 Ctrl+P** | OpenCode | IDE 风格的快速命令搜索 |
| **Signal 驱动响应式** | OpenCode | SolidJS 信号系统，精确 UI 更新 |
| **GPU 渲染终端** | Warp | Metal/Vulkan 硬件加速，块结构输出 |
| **Arena 多终端** | Qwen Code | iTerm2/Tmux/InProcess 三种后端 |
| **Esc 键检查点** | Claude Code | 按 Esc 即可回退到任意检查点 |
| **Shift+Tab 模式切换** | Gemini CLI、Copilot CLI | 快捷键循环切换审批模式 |
| **Web UI 双模式** | Kimi CLI | `kimi web` 启动 localhost:5494 浏览器 UI |
| **4 客户端** | OpenCode | TUI + Web Console + Tauri Desktop + Electron |

---

## 证据来源

| 工具 | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | 03-architecture.md（Bun v1.2 编译） | 二进制分析 |
| Gemini CLI | 03-architecture.md（Ink 6.4 + React 19） | 开源 |
| Aider | 03-architecture.md（prompt-toolkit + Rich） | 开源 |
| OpenCode | 03-architecture.md（OpenTUI + SolidJS） | 开源 |
| Warp | warp.md（Metal/Vulkan） | 官方文档 |
