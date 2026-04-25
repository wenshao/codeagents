# Fullscreen TUI 深度对比 — 终端 alt-screen 模式

> **核心问题**：Claude Code 的 `/tui fullscreen` 背后是什么终端技术？为什么"无闪烁"？OpenCode / Codex / Qwen Code 各自怎么做？Qwen Code 能借鉴什么？
>
> **结论先行**：fullscreen 模式 = **alt-screen + DECSTBM 硬件滚动 + SGR mouse tracking + 虚拟滚动 + modal pager 键** 五件套组合。Claude Code 默认对内部用户开（外部需 `/tui fullscreen` 切换）；OpenCode 因为 OpenTUI 框架**强制 fullscreen**；Codex 给了三档可配；**Qwen Code 完全没有 fullscreen 概念**——是它最大的 TUI gap。

## 一、什么是 fullscreen 模式

### 1.1 alt-screen（alternate screen buffer）

终端协议层的概念，DEC 私有模式 `?1049`。终端实际上有**两块屏幕缓冲区**：

- **primary buffer（main screen）**：你 shell 历史所在的滚动区
- **alternate buffer（alt-screen）**：临时占用的全屏画布

切换由 ANSI 转义序列控制：

```
ESC [ ? 1049 h    ← 进入 alt-screen（保存 primary 状态）
ESC [ ? 1049 l    ← 离开 alt-screen（恢复 primary，alt 内容抹掉）
```

vim / less / htop / man 都用 alt-screen——你退出后 shell 历史还在，临时 UI 不污染。

### 1.2 fullscreen 模式 ≠ "把 TUI 弄大"

很多人误以为 fullscreen 就是"把窗口全屏"——实际上是切到 alt-screen，TUI 有了独立画布，可以做 **inline 模式做不到的事**：

| 能力 | inline 可用？ | fullscreen 可用？ | 原因 |
|---|---|---|---|
| 每次 render 整屏重绘 | ✅ | ✅ | 通用 |
| **DECSTBM 硬件滚动** | ❌ | ✅ | 只在 alt-screen 安全（不污染 scrollback） |
| **SGR 鼠标追踪**（DEC 1000/1002/1006） | ⚠️ 但会窃取终端原生鼠标 | ✅ | alt-screen 会自然交还鼠标 |
| **虚拟滚动**（只渲屏内 + 邻近） | ❌ | ✅ | 需要全屏画布做 viewport |
| **modal pager 键**（g/G、Ctrl+U/D） | ❌ | ✅ | 输入框抢键码冲突 |
| **sticky 顶部 header** | ❌ | ✅ | 需要固定坐标 |
| **bottom 浮层 modal** | ❌ | ✅ | 需要 absolute positioning |

inline 模式本质是"把 TUI 当 cat/ls 一样的命令"——按行追加到 stdout，享受 shell 滚动。fullscreen 模式是"把 TUI 当 vim 一样的应用"——独占画布做复杂渲染。

## 二、Claude Code 的实现（参考标杆）

源码：`/root/git/claude-code-leaked/utils/fullscreen.ts` (202 LOC) + `components/FullscreenLayout.tsx` (636 LOC) + `components/VirtualMessageList.tsx` (1081 LOC) + `components/ScrollKeybindingHandler.tsx` (1011 LOC) + `ink/log-update.ts` (773 LOC)

### 2.1 默认值的内外部分裂

[`utils/fullscreen.ts#112-130`](file:/root/git/claude-code-leaked/utils/fullscreen.ts)：

```ts
export function isFullscreenEnvEnabled(): boolean {
  if (isEnvDefinedFalsy(process.env.CLAUDE_CODE_NO_FLICKER)) return false
  if (isEnvTruthy(process.env.CLAUDE_CODE_NO_FLICKER)) return true
  if (isTmuxControlMode()) {
    // tmux -CC 集成模式自动 fallback
    return false
  }
  return process.env.USER_TYPE === 'ant'   // ← 内部默认开，外部默认关
}
```

- **Anthropic 内部用户（`USER_TYPE=ant`）**：默认 fullscreen
- **外部用户**：默认 inline，需 `CLAUDE_CODE_NO_FLICKER=1` 或运行时 `/tui fullscreen`
- **tmux -CC（iTerm2 集成模式）**：强制 inline（鼠标轮在该模式下死，alt-screen 反而毁体验）

### 2.2 DECSTBM 硬件滚动

DEC Set Top/Bottom Margin（DECSTBM, ANSI `ESC [ t ; b r`）告诉终端"只在指定行区域内滚动"。当新增一行时，终端**硬件层面**让顶部一行被推出去，不需要重绘整个屏幕。

[`ink/frame.ts#16`](file:/root/git/claude-code-leaked/ink/frame.ts)：

```ts
/** DECSTBM scroll optimization hint (alt-screen only, null otherwise). */
readonly scrollHint?: ScrollHint | null
```

[`ink/log-update.ts#166`](file:/root/git/claude-code-leaked/ink/log-update.ts)：

```ts
if (altScreen && next.scrollHint && decstbmSafe) {
  // 用 DECSTBM scroll，不重绘整个屏幕
}
```

**只有 alt-screen 才能用 DECSTBM**——inline 模式用了会污染 shell scrollback。

### 2.3 SGR 鼠标追踪

[`utils/fullscreen.ts#132-150`](file:/root/git/claude-code-leaked/utils/fullscreen.ts)：

```ts
export function isMouseTrackingEnabled(): boolean
```

启用后 Claude 接管鼠标——滚轮翻历史、点击 UI、文本选中走 Claude 自己的 selection。

可选择性 opt-out：`CLAUDE_CODE_DISABLE_MOUSE=1`——保留 alt-screen + 虚拟滚动 + 键盘快捷键，但鼠标交还终端（用户可用 tmux/kitty 的 copy-on-select）。

### 2.4 虚拟滚动（VirtualMessageList）

[`components/VirtualMessageList.tsx`](file:/root/git/claude-code-leaked/components/VirtualMessageList.tsx)（1081 LOC，仅 fullscreen 用）

只渲染屏内 + 邻近的消息。100+ 消息长会话不影响渲染开销，因为：
- React tree 只构建 viewport 内组件
- ScrollBox 容器维护 `scrollTop` / `scrollHeight`
- 滚动时只追加上方/下方消息，不重建整树

inline 模式做不到——所有消息直接打到 stdout，靠终端滚 scrollback。

### 2.5 Modal pager 键

[`components/ScrollKeybindingHandler.tsx`](file:/root/git/claude-code-leaked/components/ScrollKeybindingHandler.tsx)（1011 LOC）

| 键 | 作用 |
|---|---|
| `g` / `G` | 跳到顶 / 底 |
| `Ctrl+U` / `Ctrl+D` | 半页上 / 下 |
| `Ctrl+B` / `Ctrl+F` | 整页上 / 下 |
| `Shift+↑/↓` | 选区扩展 |

源码注释：

> "Only safe when there is no text input competing for those characters — i.e. transcript mode."

inline 模式因输入框抢键码冲突，不能启用这些。

### 2.6 FullscreenLayout 的浮层能力

[`components/FullscreenLayout.tsx`](file:/root/git/claude-code-leaked/components/FullscreenLayout.tsx) 的 props：

```ts
type Props = {
  scrollable: ReactNode;       // 滚动主区
  bottom: ReactNode;            // 固定底部（composer + spinner）
  overlay?: ReactNode;          // 滚动区内追加内容
  bottomFloat?: ReactNode;      // 浮于 ScrollBox 右下角（fullscreen only）
  modal?: ReactNode;            // 浮于全屏的 modal 对话框（fullscreen only）
  // ...
}
```

`bottomFloat` 和 `modal` 仅 fullscreen 可用——alt-screen 才能 absolute positioning。

### 2.7 sticky prompt header

`ScrollChromeContext` 让滚动子组件向上发送 sticky 信息，FullscreenLayout 在顶部固定显示当前正在被回应的 prompt。即便你滚到对话中段，依然能看到"正在回答什么问题"。

## 三、Codex 的实现（最接近 Claude Code）

源码：`/root/git/codex/codex-rs/tui/src/tui.rs` (660+ LOC) + `lib.rs#1397-1657`

Codex 同样支持 alt-screen，但**配置更细致**：

### 3.1 三档配置 + CLI flag

[`lib.rs#1633-1657`](file:/root/git/codex/codex-rs/tui/src/lib.rs)：

```rust
fn determine_alt_screen_mode(no_alt_screen: bool, tui_alternate_screen: AltScreenMode) -> bool {
    if no_alt_screen {
        false  // CLI --no-alt-screen 显式禁
    } else {
        match tui_alternate_screen {
            AltScreenMode::Always => true,           // tui.alternate_screen = "always"
            AltScreenMode::Never => false,           // = "never"
            AltScreenMode::Auto => {                 // = "auto"（默认）
                let info = terminal_info();
                !matches!(info.multiplexer, Some(Multiplexer::Zellij {}))
                // Zellij 自动 inline，其他默认 alt-screen
            }
        }
    }
}
```

**Auto 模式最聪明**：默认 alt-screen，但检测 Zellij 自动降级 inline（Zellij 自身的滚动 panes 与 alt-screen 冲突）。

### 3.2 动态切换（运行时 enter/leave）

[`tui.rs#509-665`](file:/root/git/codex/codex-rs/tui/src/tui.rs)：

```rust
pub fn enter_alt_screen(&mut self) -> Result<()> {
    if !self.alt_screen_enabled { return Ok(()); }
    let _ = execute!(self.terminal.backend_mut(), EnterAlternateScreen);
    let _ = execute!(self.terminal.backend_mut(), EnableAlternateScroll);
    if let Ok(size) = self.terminal.size() {
        self.alt_saved_viewport = Some(self.terminal.viewport_area);
        self.terminal.set_viewport_area(/* full screen */);
        let _ = self.terminal.clear();
    }
    self.alt_screen_active.store(true, Ordering::Relaxed);
    Ok(())
}

pub fn leave_alt_screen(&mut self) -> Result<()> {
    let _ = execute!(self.terminal.backend_mut(), DisableAlternateScroll);
    let _ = execute!(self.terminal.backend_mut(), LeaveAlternateScreen);
    if let Some(saved) = self.alt_saved_viewport.take() {
        self.terminal.set_viewport_area(saved);
    }
    self.alt_screen_active.store(false, Ordering::Relaxed);
    Ok(())
}
```

**保存 inline viewport** 切到 alt-screen，离开时恢复——支持运行时按需切换（如打开 transcript overlay 时进 alt-screen，关闭时回 inline）。

### 3.3 EnableAlternateScroll

```rust
let _ = execute!(self.terminal.backend_mut(), EnableAlternateScroll);
```

DEC 1007 模式：在 alt-screen 中，**让终端把鼠标滚轮事件翻译成方向键**——即使没启用完整 SGR 鼠标追踪，滚轮也能滚动 ScrollBox。

### 3.4 inline 模式的独门绝技：insert_history

源码：[`insert_history.rs`](file:/root/git/codex/codex-rs/tui/src/insert_history.rs)（824 LOC）

Codex 的 inline 模式不只是"渲染到屏幕"——它能**反向把消息插入到 shell scrollback**，让对话历史在 Claude Code 退出后仍在 shell 中可见。这是 Claude Code 的 inline 模式做不到的（仅"流式追加"）。

## 四、OpenCode 的实现（OpenTUI 强制 fullscreen）

源码：[`/root/git/opencode/packages/opencode/src/cli/cmd/tui/app.tsx#5, #68-91`](file:/root/git/opencode/packages/opencode/src/cli/cmd/tui/app.tsx)

```ts
import { createCliRenderer, MouseButton, type CliRendererConfig } from "@opentui/core"

function rendererConfig(_config: TuiConfig.Info): CliRendererConfig {
  const mouseEnabled = !Flag.OPENCODE_DISABLE_MOUSE && (_config.mouse ?? true)
  return {
    externalOutputMode: "passthrough",
    targetFps: 60,
    gatherStats: false,
    exitOnCtrlC: false,
    useKittyKeyboard: {},
    autoFocus: false,
    openConsoleOnError: false,
    useMouse: mouseEnabled,
    // ...
  }
}
```

**OpenTUI 框架默认全屏**——`createCliRenderer` 内部进 alt-screen + 启用 SGR 鼠标 + 60 FPS 渲染循环。**没有 inline 模式**。

OpenCode 的 ScrollBoxRenderable（`@opentui/core` 原语）是虚拟滚动的：

[`routes/session/index.tsx#241, #1058`](file:/root/git/opencode/packages/opencode/src/cli/cmd/tui/routes/session/index.tsx)：

```tsx
let scroll: ScrollBoxRenderable

<scrollbox
  ref={(r) => (scroll = r)}
  stickyScroll={true}
  stickyStart="bottom"
  flexGrow={1}
  // ...
>
```

OpenCode 在 fullscreen 上甚至**比 Claude Code 走得更远**——`stickyScroll`、`scrollAcceleration`、原生 mouse hover 都是 OpenTUI 直接给的。但代价是：

- **不能保留 shell scrollback**：用户退出 OpenCode，对话内容**全部消失**（alt-screen 抹掉）
- **无 inline fallback**：如果终端不支持 alt-screen 或 SGR 鼠标，OpenCode 直接不能工作
- **不能 ssh + tmux 内层叠用**：alt-screen 嵌套问题需要用户自己调

## 五、Qwen Code 的实现（完全没有）

实测：

```bash
$ grep -rn "EnterAlternateScreen\|altScreen\|alternate.screen\|enterAlternate" \
  /root/git/qwen-code/packages/cli/src/
# (无任何结果)
```

Qwen Code 用**标准 Ink 6**（`"ink": "^6.2.3"`），ink 默认 inline 渲染——逐行追加到 stdout。**完全没有 alt-screen 概念**：
- ❌ 不能切 fullscreen
- ❌ 没有 DECSTBM 硬件滚动
- ❌ 没有 SGR 鼠标追踪
- ❌ 没有虚拟滚动列表
- ❌ 没有 modal pager 键
- ❌ 没有 sticky prompt header
- ❌ 没有 bottomFloat / modal 浮层

Qwen Code 用 Ink 的 `<Static>` 当 append-only 历史区，加 `MaxSizedBox` 视觉裁剪解决"大输出闪烁"，但这是**应用层的补丁，不是底层 fullscreen**。详见 [显示信息密度对比](./display-density-deep-dive.md)。

## 六、四家对比

| 能力 | Claude Code v2.1.119 | Codex（latest） | OpenCode v1.14.24 | Qwen Code v0.15.2 |
|---|---|---|---|---|
| alt-screen 支持 | ✅（`/tui fullscreen` 切换） | ✅（`tui.alternate_screen` 三档配置） | ✅（强制） | ❌ |
| inline 模式 | ✅（默认外部用户） | ✅（默认 + insert_history 反向插入 scrollback） | ❌（没有） | ✅（唯一模式） |
| 运行时切换 | ✅ `/tui fullscreen` `/tui inline` | ✅ `enter_alt_screen()` / `leave_alt_screen()` | N/A | N/A |
| DECSTBM 硬件滚动 | ✅ Ink fork 自建 | ✅ ratatui 原生 | ✅ OpenTUI 原生 | ❌ |
| SGR 鼠标追踪 | ✅（可禁） | ✅ EnableAlternateScroll | ✅（可禁） | ❌ |
| 虚拟滚动 | ✅ VirtualMessageList | ✅ ScrollView | ✅ ScrollBoxRenderable | ❌（仅 Ink Static） |
| modal pager 键（g/G/Ctrl+U/D） | ✅ ScrollKeybindingHandler | ✅ | ✅（OpenTUI 原生） | ❌ |
| sticky prompt header | ✅ ScrollChromeContext | ⚠️ 部分 | ⚠️ 部分 | ❌ |
| bottomFloat / modal 浮层 | ✅ FullscreenLayout | ✅ | ✅ Dialog system | ❌ |
| 多路兼容（tmux -CC / Zellij） | ✅ 自动检测降级 | ✅ Zellij 自动检测 | ❌（用户自己调） | N/A |
| **保留 shell scrollback** | ✅（inline 模式） | ✅（inline + insert_history） | ❌ | ✅（唯一模式） |
| 鼠标点击 + hover | ✅ | ✅ | ✅（OpenTUI 最完整） | ❌ |

**总结**：
- **Claude Code**：生态最平衡——内外有别 + tmux -CC 自动降级 + 灵活切换
- **Codex**：最聪明——三档配置 + Zellij 自动降级 + insert_history 让 inline 也强大
- **OpenCode**：最激进——OpenTUI 强制全屏，能力最强但兼容性最差
- **Qwen Code**：垫底——完全没有 fullscreen 概念

## 七、Qwen Code 值得借鉴的具体路径

按"性价比"排序（成本低 + 收益高优先）：

### 路径 A：抄 OpenCode 模式（最激进，全栈替换）

放弃 Ink，改用 `@opentui/core` + `@opentui/solid` 重写整个 TUI。**收益最大**（全部 7 项 fullscreen 能力一次性拿到），**成本最高**（~30k 行代码 rewrite，破坏所有现有 snapshot 测试，与 Gemini CLI 上游彻底分叉）。**P3 长期重构**。

### 路径 B：抄 Codex 模式（hybrid）

保留 Ink 主体，单独加一个 alt-screen 切换层 + 自己实现 ScrollBox。Ink 6 不直接支持 alt-screen，需要：

1. 在 Ink render 之前调 `process.stdout.write('\x1b[?1049h')` 进 alt-screen
2. Ink render 完毕后退出 `'\x1b[?1049l'`
3. 自建 ScrollBox 组件（参考 OpenCode 设计）
4. 自建 ScrollKeybindingHandler（参考 Claude Code）

**收益**：5/7 项能力（DECSTBM、虚拟滚动、modal 键、浮层、sticky header）。**成本**：~5k 行新代码 + 测试调整。**P2 中期方案**。

### 路径 C：仅做"不闪烁"（对标 Claude Code 外部用户体验）

只做最小集——alt-screen + DECSTBM。不做虚拟滚动、不做 modal 键、不做 sticky header。

```ts
// 启动时
if (settings.tui === 'fullscreen' && !isTmuxControlMode()) {
  process.stdout.write('\x1b[?1049h')   // 进 alt-screen
}

// 退出时
if (alt_screen_active) {
  process.stdout.write('\x1b[?1049l')   // 退 alt-screen
}
```

加一个 [PR#3591 TUI flicker foundation](https://github.com/QwenLM/qwen-code/pull/3591)（已合并）的 follow-up：在 fullscreen 模式下让 DECSTBM 自动启用。**收益**：消除 Qwen 当前最痛的"大输出闪烁"问题。**成本**：~500 行代码。**P1 短期方案**。

### 路径 D：仅做 mouse 滚轮（最小可行）

只启用 `EnableAlternateScroll`（DEC 1007）：

```ts
process.stdout.write('\x1b[?1007h')  // wheel → arrow keys
```

让用户能用滚轮翻历史。**收益**：解决"长会话只能 PgUp 翻"的痛点。**成本**：~10 行代码。**P0 立即可做**，但要测试 tmux/iTerm 兼容性。

## 八、关键发现总结

1. **fullscreen 不是"窗口大小"问题，是 alt-screen 协议层问题**——决定了 7 项 TUI 高级能力是否可用。

2. **Claude Code 的内外部默认值分裂**（`USER_TYPE === 'ant'`）反映 Anthropic 内部用户已习惯 fullscreen，外部用户因终端兼容性顾虑保留 inline——**新功能 always 内部先 dogfood，验证后再外推**。

3. **Codex 的 `auto` 模式 + Zellij 检测**是最聪明的工程——**默认开但智能降级**，比 Claude Code 的 `tmux -CC` 自动降级覆盖更广（Zellij 用户群体不小）。

4. **OpenCode 的"all-in OpenTUI"激进策略**让 TUI 能力一步到位，但**牺牲了 inline fallback**——用户退出后对话历史全消失，这是 OpenCode 用户社区中常见的吐槽点。

5. **Qwen Code 的 fullscreen gap 是其当前最大的 TUI 短板**——比 banner、tool border、消息间距等"细节"严重得多。社区 [PR#3591](https://github.com/QwenLM/qwen-code/pull/3591) 已经修了"通用预切片"减少闪烁，但**没动 alt-screen**——这是上限受限的根本原因。

## 九、推荐 Qwen Code 的最小可行路径

**第 1 阶段（P0，~10 行代码，1 天）**：DEC 1007 alternate scroll
- 启用滚轮 → 方向键翻译
- 让用户能用鼠标滚轮翻历史
- 风险极低（标准 ANSI，所有终端都支持）

**第 2 阶段（P1，~500 行代码，1 周）**：opt-in alt-screen
- 加 `tui.fullscreen` 设置
- 启动时根据设置进 / 不进 alt-screen
- tmux -CC 自动降级（抄 Claude Code）
- 启用 DECSTBM 减少闪烁
- **不做** 虚拟滚动、modal 键（这是 P2）

**第 3 阶段（P2，~5k 行代码，1 月）**：完整 hybrid
- 抄 Codex 模式：自建 ScrollBox + ScrollKeybindingHandler
- 加 sticky prompt header
- 加 modal pager 键
- VirtualMessageList 优化长会话

**第 4 阶段（P3，~30k 行代码，3+ 月）**：评估是否换 OpenTUI
- 与 Gemini CLI 上游分叉成本评估
- snapshot 测试重写
- 是否值得"以代价换上限"

## 证据来源

- Claude Code: `/root/git/claude-code-leaked/utils/fullscreen.ts` (202 LOC), `components/FullscreenLayout.tsx` (636 LOC), `components/VirtualMessageList.tsx` (1081 LOC), `components/ScrollKeybindingHandler.tsx` (1011 LOC), `ink/log-update.ts` (773 LOC), `ink/frame.ts` (124 LOC)
- Codex: `/root/git/codex/codex-rs/tui/src/tui.rs` (660+ LOC), `lib.rs#1397-1657`, `insert_history.rs` (824 LOC)
- OpenCode: `/root/git/opencode/packages/opencode/src/cli/cmd/tui/app.tsx`，依赖 `@opentui/core` 0.1.99
- Qwen Code: `/root/git/qwen-code/packages/cli/src/ui/`（完全无 fullscreen 引用）

> **免责声明**：基于 2026-04-25 各仓库主分支快照。OpenTUI 当前 v0.1.x 仍在快速迭代，alt-screen 行为可能变化。Claude Code v2.1.x 的 `USER_TYPE=ant` 默认值分裂可能在未来对外用户也切默认（基于 2.1.110-2.1.119 的发版节奏判断）。
