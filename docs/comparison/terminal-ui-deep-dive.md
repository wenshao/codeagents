# 34. 终端 UI/UX 框架深度对比

> 终端 UI 决定了开发者与 AI 代理的交互体验。从 Python prompt_toolkit 到 Ink+React 到 Rust 原生 GPU 渲染，技术栈选择影响启动速度、交互流畅度和扩展能力。

## 总览

| Agent | UI 框架 | 语言 | Vim 模式 | 主题 | 多客户端 | 启动速度 |
|------|--------|------|---------|------|---------|---------|
| **Claude Code** | Ink + React（Rust 原生二进制） | Rust | ✓ `/vim` | ✓ `/theme` `/color` | 终端 + Desktop + Mobile + Chrome | 亚秒级 |
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

## 各工具 UI 详解

### Claude Code：Rust 原生二进制 + Ink/React + 丰富交互命令

> 来源：02-commands.md、03-architecture.md（二进制分析 v2.1.81）

**渲染架构**：JSX → React 组件 → Ink 渲染引擎 → Yoga 布局 → ANSI 输出。二进制为 227MB ELF x86-64 Rust 原生二进制（由 Bun v1.2 构建工具链编译）。

**交互命令**：

| 命令 | 功能 |
|------|------|
| `/vim` | 切换 Vim 编辑模式（hjkl/i/a/Esc） |
| `/theme` | 主题选择器 UI |
| `/color` | 配色方案配置 |
| `/keybindings` | 打开 `~/.claude/keybindings.json` 自定义快捷键 |
| `/statusline` | 配置状态栏显示内容 |
| `/brief` | 切换简洁输出模式 |
| `/fast` | 切换快速模式（Haiku/低 effort Sonnet） |
| `/terminal-setup` | 终端环境设置（字体、颜色检测） |
| `/desktop` | 在 Claude Desktop 应用继续当前会话 |
| `/mobile` | 显示移动应用下载二维码 |
| `/chrome` | Claude in Chrome（Beta）设置 |
| Esc 键 | 显示 checkpoint 菜单，一键回退 |

**多客户端**：终端 CLI + Claude Desktop（Mac/Win）+ 移动应用 + Chrome 扩展 + Web（claude.ai/code）。

### Gemini CLI：Ink 6 + 模式切换 + 11 Hook 事件

> 源码：03-architecture.md、05-policies.md

**交互命令**：

| 命令 | 功能 |
|------|------|
| `/shortcuts` | 显示所有键盘快捷键 |
| `/theme` | 打开主题选择器 |
| `/footer`（别名 `statusline`） | 配置状态栏（`FooterConfigDialog` 组件） |
| `/vim` | 切换 Vim 模式 |
| Shift+Tab | 循环切换审批模式（DEFAULT → AUTO_EDIT → PLAN → YOLO） |
| Esc Esc | 触发 `/rewind`（RewindViewer 组件） |

**Hook 系统对 UI 的影响**：

11 个 Hook 事件中，`BeforeModel`/`AfterModel` 可拦截 LLM 调用前后的 UI 渲染；`BeforeToolSelection` 可在工具选择 UI 前注入自定义逻辑。

```jsonc
// settings.json Hook 配置
{
  "hooks": {
    "BeforeTool": [{
      "matcher": "shell",
      "hook": { "type": "command", "command": "node validate.js", "timeout": 5000 }
    }]
  }
}
```

### Aider：prompt_toolkit + Rich（1000+ 行 UI）

> 源码：`aider/io.py`（1000+ 行）

**独有交互**：

| 命令 | 功能 |
|------|------|
| `/voice` | 语音输入（OpenAI Whisper 转录） |
| `/paste` | 从剪贴板粘贴（PIL ImageGrab + pyperclip） |
| `/copy` | 复制最近回复到剪贴板 |
| `/multiline-mode` | 切换多行输入模式 |
| Tab 键 | prompt_toolkit 自动补全（文件名、命令） |

Rich 渲染组件：语法高亮代码块、彩色 diff、Markdown 表格、Panel 布局、进度条。

### Kimi CLI：双模式（TUI + Web UI）

> 源码：03-architecture.md

**Web UI**（`kimi web` 命令）：

```bash
kimi web --port 5494 --auth-token my-token --lan-only
```

基于 FastAPI + Uvicorn + React，提供：
- 多会话管理
- Git diff 预览面板
- 审批对话框（可视化权限确认）
- 数学公式渲染
- 文件变更面板

**Wire 协议 v1.6**：TurnBegin/TurnEnd、StepBegin、ContentPart、ToolCall、ToolResult、ApprovalRequest/Response——事件流协议驱动 UI 实时更新。

### OpenCode：37 主题 + 命令面板 + 4 客户端

> 源码：03-architecture.md

**架构演进**：v1.0 从 Go + Bubbletea 完全重写为 OpenTUI + SolidJS。

**SolidJS 信号驱动响应式**：不同于 React 的虚拟 DOM diff，SolidJS 使用 Signal 系统精确追踪依赖，仅更新实际变化的 UI 节点——性能更高、内存更低。

**4 种客户端**：

| 客户端 | 技术 | 适用 |
|--------|------|------|
| TUI | OpenTUI + SolidJS | 终端内（主要） |
| Web Console | SolidJS 前端 | 浏览器（16 语言） |
| Tauri Desktop | Tauri v2 | 桌面原生 |
| Electron | Electron | 桌面兼容 |

**快捷键**：Ctrl+K（命令面板）、Ctrl+T（主题切换）、侧边栏开关。

### Warp：GPU 渲染终端（最高性能）

> 来源：warp.md

```
Rust 核心 → Metal(macOS) / Vulkan(Linux/Win) → GPU 硬件加速渲染
```

**块结构输出**：命令和输出被组织为可导航的"块"（Blocks），支持：
- Ctrl+Shift+↑/↓ 块导航
- 块级复制/搜索/书签
- 文本编辑器风格的输入框

**主题配置**（YAML）：

```yaml
# ~/.warp/themes/custom.yaml
accent: "#6366f1"
background: "#1e1e2e"
foreground: "#cdd6f4"
cursor: "#f5e0dc"
```

---

## 快捷键对比

| 快捷键 | Claude Code | Gemini CLI | Copilot CLI | OpenCode | Warp |
|--------|------------|-----------|------------|----------|------|
| **模式切换** | — | Shift+Tab | Shift+Tab | — | — |
| **Vim 模式** | `/vim` | `/vim` | ✗ | ✗ | 设置中 Vi Mode |
| **命令面板** | — | — | — | **Ctrl+K** | Ctrl+P |
| **主题切换** | `/theme` | `/theme` | `/theme` | **Ctrl+T** | 设置 |
| **回退** | **Esc** | — | — | — | — |
| **块导航** | — | — | — | — | Ctrl+Shift+↑/↓ |
| **剪贴板** | `/copy` | `/copy` | — | — | Cmd+C（块级） |
| **语音输入** | `/voice` | ✗ | ✗ | ✗ | ✗ |

---

## 独特 UI 创新

| 创新 | 工具 | 说明 |
|------|------|------|
| **37 种内置主题** | OpenCode | 目前主题最丰富的 CLI 工具 |
| **命令面板 Ctrl+K** | OpenCode | IDE 风格的快速命令搜索 |
| **Signal 驱动响应式** | OpenCode | SolidJS 信号系统，精确 UI 更新 |
| **GPU 渲染终端** | Warp | Metal/Vulkan 硬件加速，块结构输出 |
| **Arena 多终端** | Qwen Code | iTerm2/Tmux/InProcess 三种后端 |
| **Esc 键检查点** | Claude Code | 按 Esc 即可回退到任意检查点 |
| **Shift+Tab 模式切换** | Gemini CLI、Copilot CLI | 快捷键循环切换审批模式 |
| **Web UI 双模式** | Kimi CLI | `kimi web` 启动 localhost:5494 浏览器 UI |
| **4 客户端** | OpenCode | TUI + Web Console + Tauri Desktop + Electron |

---

## Follow-up Suggestions（后续建议）

Agent 在回复结束后引导用户下一步操作的能力差异：

| Agent | 后续建议方式 | 实现机制 |
|------|-----------|---------|
| **Claude Code** | `/suggestions` Skill | 分析使用数据，生成个性化改进建议 |
| **Codex CLI** | 系统提示内嵌 | "clearly stating assumptions, environment prerequisites, and next steps" |
| **Copilot CLI** | 压缩保留 + 检查点标题 | 压缩时保留 "next steps"；检查点生成 2-6 词标题 |
| **Aider** | 反射循环隐式 | lint/test 失败自动触发下一步修复（非用户选择） |
| **Gemini CLI** | 无显式机制 | — |
| **Kimi CLI** | 无显式机制 | — |
| **Goose** | 无显式机制 | — |

### Claude Code `/suggestions` 实现

```bash
/suggestions    # 分析使用数据，建议改进
```

- **类型**：Skill（prompt 驱动）
- **功能**：分析当前会话的使用模式，生成个性化建议
- **示例输出**：推荐启用的 Hook、常用命令快捷方式、配置优化建议

### Codex CLI 的 Next Steps 指令

系统提示中硬编码：

```
"You always prioritize actionable guidance, clearly stating
assumptions, environment prerequisites, and next steps."
```

每次回复末尾自然包含下一步操作建议，但不是独立 UI 组件。

### Copilot CLI 的检查点标题

压缩会话时保留结构化上下文：

```
Compaction preserves:
  - context（当前状态）
  - changes made（已完成的修改）
  - key references（关键引用）
  - next steps（下一步操作）
  - checkpoint title（2-6 词标题）
```

> **设计差异**：Claude Code 将后续建议作为独立 Skill 实现（用户主动调用）；Codex CLI 和 Copilot CLI 将其内嵌到系统提示和压缩逻辑中（自动包含在每次回复中）。前者给用户更多控制，后者更自然但不可定制。

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | 03-architecture.md（Rust 原生，Bun v1.2 构建） | 二进制分析 |
| Gemini CLI | 03-architecture.md（Ink 6.4 + React 19） | 开源 |
| Aider | 03-architecture.md（prompt-toolkit + Rich） | 开源 |
| OpenCode | 03-architecture.md（OpenTUI + SolidJS） | 开源 |
| Warp | warp.md（Metal/Vulkan） | 官方文档 |
