# 启动阶段优化深度对比（API Preconnect + Early Input）

> Claude Code 在启动阶段实现了两项关键优化：**API Preconnect**（TCP+TLS 握手与初始化重叠）和 **Early Input Capture**（启动期间键盘输入捕获）。这两项优化均为用户可感知的首次交互延迟改善。本文基于源码分析（`utils/apiPreconnect.ts` 71 行 + `utils/earlyInput.ts` 191 行），覆盖实现原理、跳过条件、Qwen Code 现状和实现方案。

## 1. 问题背景

### 1.1 首次 API 调用的延迟瓶颈

标准 HTTPS 连接建立需要 **TCP 三次握手 + TLS 握手**，耗时约 **100-200ms**。在正常的 CLI 启动流程中，这个延迟阻塞在第一次 API 调用内：

```
正常流程（串行）:

[启动] → [加载配置] → [初始化MCP] → [首次API调用: TCP+TLS 100-200ms + 请求处理]
                                                              ↑
                                                    用户感知到的延迟
```

### 1.2 启动期间的用户输入丢失

用户在终端输入 `claude` 后**立即开始打字**（这是常见行为），但此时 REPL 尚未初始化，这些键盘输入会**直接丢失**，用户需要重新输入。

---

## 2. Claude Code：API Preconnect

### 2.1 优化原理

在配置加载完成后、REPL 初始化之前，发起一个 **fire-and-forget HEAD 请求**到 Anthropic API。这样 TCP+TLS 握手与后续的初始化工作（MCP 加载、action handler 设置等）**并行进行**：

```
优化流程（并行）:

[启动] → [加载配置] → [fire-and-forget HEAD 请求] → [初始化MCP] → [首次API调用: 复用连接]
                           ↓ 100-200ms                 ↑ 与初始化重叠    ↑ 节省 100-200ms
```

**源码**: `utils/apiPreconnect.ts`（71 行）

### 2.2 实现细节

```typescript
// 源码: utils/apiPreconnect.ts#L28-L71
let fired = false

export function preconnectAnthropicApi(): void {
  if (fired) return
  fired = true

  // 跳过云服务商（不同端点+认证）
  if (
    isEnvTruthy(process.env.CLAUDE_CODE_USE_BEDROCK) ||
    isEnvTruthy(process.env.CLAUDE_CODE_USE_VERTEX) ||
    isEnvTruthy(process.env.CLAUDE_CODE_USE_FOUNDRY)
  ) return

  // 跳过 proxy/mTLS/unix（SDK 自定义 dispatcher 不共享连接池）
  if (
    process.env.HTTPS_PROXY || process.env.http_proxy ||
    process.env.ANTHROPIC_UNIX_SOCKET ||
    process.env.CLAUDE_CODE_CLIENT_CERT || process.env.CLAUDE_CODE_CLIENT_KEY
  ) return

  const baseUrl = process.env.ANTHROPIC_BASE_URL || getOauthConfig().BASE_API_URL

  // Fire and forget HEAD 请求，10s 超时
  void fetch(baseUrl, {
    method: 'HEAD',
    signal: AbortSignal.timeout(10_000),
  }).catch(() => {})
}
```

**关键设计决策**：

| 决策 | 说明 |
|------|------|
| **调用时机** | `init.ts#L159` 中 `applyExtraCACertsFromConfig()` + `configureGlobalAgents()` **之后**调用 |
| **TLS 证书顺序** | `applyExtraCACertsFromConfig()` 必须在首次 TLS 握手前完成（Bun/BoringSSL 在启动时缓存证书存储） |
| **请求方法** | `HEAD` — 无响应体，连接到达后即可复用 |
| **超时** | 10 秒 `AbortSignal.timeout()` — 慢网络不阻塞进程 |
| **连接复用** | 依赖 Bun fetch 的全局 keep-alive 连接池（所有 fetch 共享） |

### 2.3 智能跳过机制

Preconnect 在以下情况下**自动跳过**，避免预热错误的连接池：

#### 云服务商跳过

| 环境变量 | 原因 |
|---------|------|
| `CLAUDE_CODE_USE_BEDROCK` | AWS Bedrock 端点 + 签名认证不同 |
| `CLAUDE_CODE_USE_VERTEX` | Google Vertex AI 端点不同 |
| `CLAUDE_CODE_USE_FOUNDRY` | Foundry 端点不同 |

#### 网络配置跳过

| 环境变量 | 原因 |
|---------|------|
| `HTTPS_PROXY` / `http_proxy` | 代理模式下 SDK 使用自定义 dispatcher |
| `ANTHROPIC_UNIX_SOCKET` | Unix socket 不共享全局连接池 |
| `CLAUDE_CODE_CLIENT_CERT` | mTLS 需要客户端证书 |
| `CLAUDE_CODE_CLIENT_KEY` | mTLS 需要客户端私钥 |

**原因**：这些场景下 SDK 会传递自定义 `dispatcher`/`agent`，不共享 Bun 的全局连接池，preconnect 预热的连接不会被复用。

### 2.4 调用时机演进

Claude Code 曾有两个调用点，后来删除了一个：

| 版本 | 调用点 | 问题 |
|------|--------|------|
| 早期 | `cli.tsx` 入口处 | settings.json 未加载，`ANTHROPIC_BASE_URL`/proxy/mTLS 不可见 |
| 当前 | `init.ts` 配置加载后 | ✅ settings.json 已应用，环境变量已生效 |

源码注释明确说明：
> "The early cli.tsx call site was removed — it ran before settings.json loaded, so ANTHROPIC_BASE_URL/proxy/mTLS in settings would be invisible and preconnect would warm the wrong pool."

---

## 3. Claude Code：Early Input Capture

### 3.1 优化原理

在 CLI 入口处**最早启动 raw mode 监听 stdin**，捕获用户在 REPL 初始化前的输入。REPL 就绪后将缓冲内容注入输入框。

**源码**: `utils/earlyInput.ts`（191 行）

### 3.2 调用点

| 函数 | 调用位置 | 源码 |
|------|---------|------|
| `startCapturingEarlyInput()` | `entrypoints/cli.tsx#L291` — CLI 入口最早期 | 用户输入 `claude` 后立即启动 |
| `consumeEarlyInput()` | `screens/REPL.tsx#L1331` — REPL 组件的 `useState` 初始化 | REPL 渲染时消费缓冲内容 |

### 3.3 架构总览

```
启动早期 → startCapturingEarlyInput()
  ├─ process.stdin.setRawMode(true)     # 原始模式 (Raw Mode)
  ├─ 监听 'readable' 事件               # 逐字符捕获
  └─ processChunk() 逐字符处理:
      ├─ Ctrl+C (code 3) → process.exit(130)
      ├─ Ctrl+D (code 4) → 停止捕获
      ├─ Backspace (8/127) → 删除最后一个 grapheme cluster
      ├─ ESC (27) → 跳过转义序列 (Escape Sequence)（方向键/功能键）
      ├─ CR (13) → 转换为 \n
      └─ 可打印字符 → 加入 earlyInputBuffer

REPL 就绪 → consumeEarlyInput()
  ├─ stopCapturingEarlyInput()          # 清理监听器
  ├─ 返回 trimmed buffer                 # 预填充到输入框
  └─ 不清零 stdin 状态（REPL 的 Ink App 自行管理）
```

### 3.4 逐字符处理逻辑

`processChunk()` 是核心函数，逐字节扫描输入流：

| 字符/序列 | 处理 | 原因 |
|-----------|------|------|
| `Ctrl+C` (0x03) | 立即 `process.exit(130)` | 此时 shutdown 机制未初始化 |
| `Ctrl+D` (0x04) | 停止捕获 | EOF 信号 |
| `Backspace` (0x08/0x7F) | 删除最后一个 **grapheme cluster** | 支持 emoji 等组合字符 |
| `ESC` (0x1B) | 跳过整个转义序列 | 方向键/功能键不进入 buffer |
| `CR` (0x0D) | 转换为 `\n` | 统一换行符 |
| `Tab` (0x09) | 加入 buffer | 保留 tab 字符 |
| 其他 < 0x20 | 跳过 | 控制字符不可打印 |
| 可打印字符 | 加入 `earlyInputBuffer` | 正常累积 |

### 3.5 关键设计细节

#### Grapheme-aware Backspace

使用 `lastGrapheme()` 工具函数处理 Unicode 组合字符：

```typescript
// 源码: utils/earlyInput.ts#L94-L99
if (code === 127 || code === 8) {
  if (earlyInputBuffer.length > 0) {
    const last = lastGrapheme(earlyInputBuffer)
    earlyInputBuffer = earlyInputBuffer.slice(0, -(last.length || 1))
  }
}
```

这确保了 emoji（如 👨‍👩‍👧‍👦 由多个 code point 组成）按**视觉字符**为单位删除，而非按 code point。

#### 转义序列 (Escape Sequence) 跳过

```typescript
// 源码: utils/earlyInput.ts#L103-L112
if (code === 27) {
  i++ // 跳过 ESC
  // 跳过直到终止字节 (@ ~ 范围 0x40-0x7E)
  while (i < str.length && !(str.charCodeAt(i) >= 64 && str.charCodeAt(i) <= 126)) {
    i++
  }
  if (i < str.length) i++ // 跳过终止字节
  continue
}
```

ANSI 转义序列格式：`ESC [ ... 终止字节`。这段代码完整跳过整个序列，避免方向键等功能键污染输入 buffer。

#### 不干扰 REPL

```typescript
// 源码: utils/earlyInput.ts#L154
// Don't reset stdin state - the REPL's Ink App will manage stdin state.
```

`stopCapturingEarlyInput()` **仅移除监听器**，不调用 `setRawMode(false)`。REPL 的 Ink 框架会自行管理 stdin 状态。

#### 启动条件检查

```typescript
// 源码: utils/earlyInput.ts#L33-L39
if (
  !process.stdin.isTTY ||          // 仅 TTY 模式
  isCapturing ||                   // 避免重复启动
  process.argv.includes('-p') ||   // print 模式跳过
  process.argv.includes('--print')
) {
  return
}
```

**`-p` 模式跳过的原因**：raw mode 会禁用 ISIG（终端 Ctrl+C → SIGINT），导致 `-p` 模式下 Ctrl+C 无法中断进程。

#### Seed 能力

```typescript
// 源码: utils/earlyInput.ts#L182
export function seedEarlyInput(text: string): void {
  earlyInputBuffer = text
}
```

支持程序化预设输入内容，可用于自动化测试或特定场景的预填充。

---

## 4. Qwen Code 现状

### 4.1 API Preconnect：完全缺失

搜索 `packages/cli/src/gemini.tsx` 和 `packages/core/src/utils/` 均无 preconnect 相关代码。

Qwen Code 的启动流程（`gemini.tsx` 527 行分析）：

```
[加载 settings] → [加载配置] → [初始化 App] → [渲染 (Rendering) REPL] → [首次API调用: 完整握手]
                                                              ↑
                                                    首次延迟无优化
```

### 4.2 Early Input Capture：完全缺失

Qwen Code **完全没有**对应机制：
- 无 `setRawMode` 早期调用
- 无 stdin 缓冲区
- 用户在 REPL 渲染 (Rendering) 前的打字**全部丢失**

现有 `packages/cli/src/utils/readStdin.ts` 仅处理 **pipe 模式**的 stdin 读取，不处理 TTY 早期输入。

### 4.3 启动阶段对比

| 指标 | Claude Code | Qwen Code |
|------|-------------|-----------|
| API Preconnect（预连接 (Preconnect)） | ✅ `init.ts` 中 fire-and-forget HEAD | ❌ 无 |
| Early Input（早期输入捕获 (Early Input Capture)） | ✅ 启动时 raw mode 捕获 | ❌ 无 |
| 首次 API 延迟 | ~0ms（复用预连接 (Preconnect)） | 100-200ms（完整握手） |
| 启动期间打字 | ✅ 捕获并预填充 | ❌ 全部丢失 |

---

## 5. Qwen Code 实现方案

### 5.1 API Preconnect（~40 行）

**建议文件**: `packages/core/src/utils/apiPreconnect.ts`

```typescript
let fired = false

export function preconnectApi(baseUrl: string): void {
  if (fired) return
  fired = true

  // 跳过 proxy/mTLS
  if (
    process.env.HTTPS_PROXY ||
    process.env.http_proxy ||
    process.env.ANTHROPIC_UNIX_SOCKET
  ) {
    return
  }

  // Fire and forget HEAD 请求
  void fetch(baseUrl, {
    method: 'HEAD',
    signal: AbortSignal.timeout(10_000),
  }).catch(() => {})
}
```

**集成点**: `packages/cli/src/gemini.tsx` 中 `loadSettings()` 后、`initializeApp()` 前：

```typescript
// gemini.tsx 中的集成位置示意
const settings = loadSettings()
const config = loadCliConfig(settings)

// ← 在此处插入
preconnectApi(config.apiBaseUrl)

await initializeApp(config)
```

### 5.2 Early Input Capture（~120 行）

**建议文件**: `packages/cli/src/utils/earlyInput.ts`

核心实现与 Claude Code 类似，需注意：
1. 复用 Qwen Code 已有的 Unicode 工具函数（如 grapheme 分割）
2. 与 Ink 框架的 stdin 管理协调（不调用 `setRawMode(false)`）
3. `-p` / `--print` 模式下跳过

**集成点**:
1. `gemini.tsx` 入口处**最早**调用 `startCapturingEarlyInput()`
2. REPL 渲染前调用 `consumeEarlyInput()` 获取缓冲内容，预填充到输入框

---

## 6. 收益评估

| 指标 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| 首次 API 延迟 | 100-200ms（完整握手） | ~0ms（复用连接） | **~150ms** |
| 用户输入丢失 | 启动期间打字全部丢失 | 捕获并预填充 | **交互流畅度显著提升** |
| 实现成本 | — | ~160 行代码 | **低投入高回报** |

## 7. 参考

| 项目 | 源码路径 |
|------|---------|
| Claude Code Preconnect | `utils/apiPreconnect.ts` (71 行) |
| Claude Code Early Input | `utils/earlyInput.ts` (191 行) |
| Qwen Code CLI 入口 | `packages/cli/src/gemini.tsx` (527 行) |
| Qwen Code Stdin 读取 | `packages/cli/src/utils/readStdin.ts` |

> **免责声明**: 以上分析基于 Claude Code leaked 源码和 Qwen Code 开源源码。Qwen Code 实现方案为建议，非官方实现。
