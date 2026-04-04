# Deep Link 协议 Deep-Dive

> 如何从浏览器、IDE 或 Slack 一键启动 AI Agent 并预填充 prompt？本文基于 Claude Code（v2.1.89 源码分析）的源码分析，介绍其 `claude-cli://` URI scheme 的完整架构：协议解析、终端自动检测、GitHub 仓库解析和安全模型。Qwen Code 目前无此功能。

---

## 1. 架构总览

```
浏览器/IDE/Slack → claude-cli://open?q=...&cwd=...&repo=...
  ↓ OS Protocol Handler
URL Handler App（macOS .app / Linux .desktop / Windows Registry）
  ↓ --handle-uri
Claude Code CLI → parseDeepLink() → 解析参数
  ↓
terminalLauncher → 检测/启动终端
  ↓ 终端内启动
Claude Code REPL（预填充 prompt + 工作目录）
```

---

## 2. URI Scheme

**协议**：`claude-cli://`

**格式**：`claude-cli://open?q=<prompt>&cwd=<path>&repo=<owner/repo>`

| 参数 | 类型 | 说明 | 限制 |
|------|------|------|------|
| `q` | string | 预填充 prompt | ≤5,000 字符，无控制字符 |
| `cwd` | string | 工作目录 | 绝对路径，≤4,096 字符 |
| `repo` | string | GitHub 仓库 slug | `owner/repo` 格式 |

**安全**：所有参数 URL-decoded + Unicode 清理 + 控制字符拒绝 + shell-quoted。

> 源码: `utils/deepLink/parseDeepLink.ts`

---

## 3. 终端自动检测与启动

### 3.1 macOS（优先级从高到低）

| 终端 | 启动方式 | CWD 方法 |
|------|----------|----------|
| **iTerm** | AppleScript `create window` + `write text` | AppleScript 内置 |
| **Ghostty** | `open -na --args` | `--working-directory=<cwd>` |
| **Kitty** | `open -na --args` | `--directory <cwd>` |
| **Alacritty** | `open -na --args` | `--working-directory <cwd>` |
| **WezTerm** | `open -na --args` | `start --cwd <cwd>` |
| **Terminal.app** | AppleScript `do script` | AppleScript 内置 |

**检测顺序**：
1. 用户保存的偏好（`deepLinkTerminal` 配置）
2. `TERM_PROGRAM` 环境变量
3. Spotlight `mdfind` 查找 bundle ID
4. `/Applications/` 目录回退
5. Terminal.app（始终可用）

### 3.2 Linux

| 终端 | CWD 方法 |
|------|----------|
| ghostty, kitty, alacritty, wezterm | `--working-directory` / `--directory` / `--cwd` |
| gnome-terminal, konsole | `--working-directory` |
| xfce4-terminal, mate-terminal, tilix | `--working-directory` |
| xterm | `spawn({cwd})` |

**检测**：`$TERMINAL` → `x-terminal-emulator` → 优先级列表 `which()` 遍历

### 3.3 Windows

| 终端 | 启动方式 |
|------|----------|
| Windows Terminal (`wt.exe`) | `-d <cwd> -- cmd args` |
| PowerShell 7+ (`pwsh.exe`) | `-NoExit -Command "Set-Location; &"` |
| PowerShell 5.1 | 同上 |
| cmd.exe | `/k "cd /d '<cwd>' && <cmd>"` |

> 源码: `utils/deepLink/terminalLauncher.ts`

---

## 4. GitHub 仓库解析

```typescript
// 源码: utils/deepLink/protocolHandler.ts#L36-L75
// 优先级: 显式 cwd > repo 查找 > home 目录

// repo 查找:
getKnownPathsForRepo('owner/repo')
  → 扫描已知克隆路径（githubRepoPathMapping.ts）
  → filterExistingPaths()
  → 返回 MRU（最近使用）的克隆目录
```

**新鲜度检查**（源码: `utils/deepLink/banner.ts#L88-L102`）：
- 读取 `FETCH_HEAD` mtime
- 超过 7 天显示过期警告

---

## 5. 安全模型

### 5.1 来源警告 Banner

```
⚠ External deep link
Working directory: /path/to/project
Repo: owner/repo (last fetched 3 days ago)

Review the prompt below, then press Enter to submit.
```

- 用户必须按 Enter 确认——不自动执行
- Prompt 超过 1,000 字符时提示"scroll down to review"

### 5.2 协议注册

| 平台 | 注册方式 | 位置 |
|------|----------|------|
| macOS | `.app` bundle + LaunchServices | `~/Applications/Claude Code URL Handler.app/` |
| Linux | `.desktop` 文件 + xdg-mime | `$XDG_DATA_HOME/applications/` |
| Windows | Registry HKCU | `HKCU\Software\Classes\claude-cli` |

**自动注册**：后台 housekeeping 中 fire-and-forget，GrowthBook `tengu_lodestone_enabled` 门控，失败 24h 退避。

> 源码: `utils/deepLink/registerProtocol.ts`

---

## 6. CLI 参数

| 参数 | 用途 |
|------|------|
| `--handle-uri <url>` | OS 协议分发入口 |
| `--deep-link-origin` | 标记从 deep link 启动 |
| `--deep-link-repo <repo>` | 已解析的 GitHub slug |
| `--deep-link-last-fetch <ms>` | FETCH_HEAD mtime（显示新鲜度） |
| `--prefill <query>` | 预填充 prompt |

---

## 7. 关键源码文件

| 文件 | 职责 |
|------|------|
| `utils/deepLink/parseDeepLink.ts` | URI 解析 + 参数验证 |
| `utils/deepLink/protocolHandler.ts` | URI 分发 + repo 解析 |
| `utils/deepLink/terminalLauncher.ts` | 终端检测 + 跨平台启动 |
| `utils/deepLink/registerProtocol.ts` | 协议注册（macOS/Linux/Windows） |
| `utils/deepLink/terminalPreference.ts` | 终端偏好存储 |
| `utils/deepLink/banner.ts` | 来源安全警告 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。
