# Computer Use 桌面自动化 Deep-Dive

> AI Agent 能否操作桌面应用——截图、点击、打字、读剪贴板？本文基于 Claude Code（v2.1.89 源码分析）的源码分析，介绍其 Computer Use 桌面自动化架构。Qwen Code 目前无此功能。

---

## 1. 架构总览

```
Claude Code CLI
  ↓ MCP 协议
Computer Use MCP Server（进程内 stdio 传输）
  ↓ NAPI
┌─────────────────────────────────┐
│ @ant/computer-use-swift         │ ← 截图（SCContentFilter）
│ @ant/computer-use-input (Rust)  │ ← 鼠标/键盘（enigo）
└─────────────────────────────────┘
  ↓ macOS API
NSWorkspace / TCC / IOKit
```

| 维度 | 详情 |
|------|------|
| **集成方式** | MCP Server（进程内，stdio 传输） |
| **截图** | `SCContentFilter`（macOS ScreenCaptureKit） |
| **输入控制** | Rust `enigo` NAPI 绑定 |
| **权限** | TCC Accessibility + Screen Recording |
| **门控** | GrowthBook `tengu_malort_pedway` + Max/Pro 订阅 |
| **工具名** | `mcp__computer-use__*` |

---

## 2. 截图捕获

```typescript
// 源码: utils/computerUse/swiftLoader.ts
// 通过 NAPI 加载 @ant/computer-use-swift
// 方法: captureExcluding(), captureRegion(), screenshot
// JPEG 质量: 0.75
// 坐标缩放: 逻辑坐标 → 物理像素 → API 目标尺寸
```

**终端豁免**：截图时自动隐藏终端窗口（避免截到 Agent 自身 UI）。通过 `getTerminalBundleId()` 检测当前终端：iTerm、Terminal.app、Ghostty、Kitty、Warp、VS Code。

---

## 3. 鼠标/键盘控制

| 操作 | 实现 | 参数 |
|------|------|------|
| `moveMouse()` | 瞬移 + 50ms 稳定延迟 | x, y |
| `click()` | 支持修饰键（press/release 括号化） | button, modifiers |
| `drag()` | ease-out-cubic 动画，60fps，2000px/s，最大 0.5s | start, end |
| `scroll()` | 垂直优先 | dx, dy |
| `key()` / `keys()` | 通过 DispatchQueue.main 分发 | key name, modifiers |
| `holdKey()` | press/release 追踪防止修饰键卡住 | key, action |
| `type()` | 剪贴板粘贴（含回读验证）或直接 typeText() | text |

**Run Loop 排空**：`drainRunLoop()` 确保 main-queue dispatch 事件到达——30s 超时上限，orphan 标志防护。

> 源码: `utils/computerUse/executor.ts`

---

## 4. TCC 权限

```typescript
// 源码: utils/computerUse/hostAdapter.ts#L47-L54
// 启动时检查:
checkAccessibility()    // 辅助功能权限（鼠标/键盘控制）
checkScreenRecording()  // 屏幕录制权限（截图捕获）
// 两项均需批准才能使用 Computer Use
```

---

## 5. MCP 集成

```typescript
// 源码: utils/computerUse/setup.ts#L23-L53
// Server 配置:
{
  type: 'stdio',                                    // 进程内传输
  command: process.execPath,                        // 自身二进制
  args: ['--computer-use-mcp'],                     // MCP 入口
  scope: 'dynamic',                                 // 按需启动
}
// 工具名: mcp__computer-use__screenshot, mcp__computer-use__click, ...
// 权限: buildComputerUseTools() 自动添加 allowed tools（绕过权限提示）
```

**CallTool 覆盖**（源码: `utils/computerUse/wrapper.tsx`）：拦截 MCP callTool，注入权限对话框、状态管理、锁获取和截图持久化。

---

## 6. 门控与限制

| 门控 | 条件 |
|------|------|
| GrowthBook | `tengu_malort_pedway` 特性开关 |
| 订阅 | Max / Pro 订阅（Ant 用户绕过） |
| 平台 | 仅 macOS（SCContentFilter 依赖） |
| 并发 | 文件锁（`computerUseLock.ts`）防止并发 CU 会话 |
| 中止 | Cmd+Escape 热键（`escHotkey.ts` 通过 event-tap 注册） |

**子门控**（GrowthBook 动态配置）：
- `pixelValidation` — 像素级操作验证
- `clipboardPasteMultiline` — 多行剪贴板粘贴
- `mouseAnimation` — 鼠标拖拽动画
- `hideBeforeAction` — 操作前隐藏终端
- `autoTargetDisplay` — 自动选择目标显示器
- `clipboardGuard` — 剪贴板保护

---

## 7. 关键源码文件

| 文件 | 职责 |
|------|------|
| `utils/computerUse/mcpServer.ts` | MCP Server 入口 |
| `utils/computerUse/executor.ts` | 鼠标/键盘/截图执行 |
| `utils/computerUse/hostAdapter.ts` | TCC 权限检查 |
| `utils/computerUse/swiftLoader.ts` | SCContentFilter NAPI |
| `utils/computerUse/inputLoader.ts` | enigo/keyboard NAPI |
| `utils/computerUse/gates.ts` | GrowthBook 门控 |
| `utils/computerUse/setup.ts` | MCP 配置 |
| `utils/computerUse/wrapper.tsx` | CallTool 覆盖 |
| `utils/computerUse/computerUseLock.ts` | 并发文件锁 |
| `utils/computerUse/escHotkey.ts` | Cmd+Escape 中止热键 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。Computer Use 仅限 macOS，需 Max/Pro 订阅。
