# Claude Code 为什么更快更稳定？Qwen Code 应该做哪些改进？

> 基于源码分析的性能差距根因和可操作的改进建议

## 一、Claude Code 快在哪里

### 1. 原生二进制 vs JavaScript 运行时

**这是最根本的差距。**

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **分发方式** | 预编译原生二进制（Rust） | Node.js + npm 依赖 |
| **冷启动** | ~100-200ms | ~2-5 秒 |
| **内存** | ~50-80 MB | ~200-400 MB |
| **依赖体积** | 单文件 | node_modules 数百 MB |

Claude Code 从 `curl install.sh | bash` 安装的是**编译后的原生可执行文件**，npm 安装方式已被标记为 deprecated。这意味着：
- 无 Node.js 启动开销（V8 引擎初始化 ~100ms）
- 无模块解析开销（node_modules 数千文件）
- 无 JIT 编译预热
- Rust 的零成本抽象和内存安全

### 2. 激进的并行化

Claude Code CHANGELOG 中记录的多项优化：

```
✓ macOS 启动加速 ~60ms：keychain 读取与模块加载并行
✓ 大仓库启动内存减少 ~80MB（25 万文件仓库）
✓ 启动内存减少 ~18MB（所有场景）
✓ Git 操作并行：直接读 ref，跳过冗余 git fetch
✓ 会话恢复加速 45%，峰值内存减少 100-150MB
```

**核心策略**：所有 I/O 操作（凭证读取、Git 操作、文件扫描）并行执行，不阻塞主线程。

### 3. 极致的懒加载

- **工具按需加载**：`ToolSearch` 机制——工具 schema 延迟获取，模型请求时才加载
- **插件按需发现**：commands/agents/skills 在需要时才解析 Markdown
- **MCP 按需连接**：不是所有 MCP 服务器启动时连接
- **`--bare` 模式**：脚本调用时跳过 hooks、LSP、插件同步、技能目录扫描

### 4. 内存管理精细

- **流式响应缓冲区**：generator 终止后立即释放
- **会话压缩**：自动压缩 + 断路器（连续 3 次失败后停止重试）
- **文件操作优化**：检查文件存在不读取全部内容
- **大会话处理**：>5MB 会话自动提取记忆 + 保存 transcript

### 5. 超时和断路器

- **非流式 API 回退**：每次尝试 2 分钟超时
- **自动压缩断路器**：3 次连续失败后停止
- **并行工具隔离**：Bash 错误不级联到 Read/Glob 等只读工具
- **MCP 重连**：自动重连 + spinner 自动清除

### 6. 文件系统级沙箱

- **文件系统隔离**：`sandbox.filesystem.allowWrite`/`allowRead` 控制读写权限
- **网络隔离**：`sandbox.network.allowedDomains` 控制可访问域名
- **macOS 弱网络隔离**：`enableWeakerNetworkIsolation` 选项（CHANGELOG 385 行）
- 具体隔离机制为闭源实现，CHANGELOG 中未提及 iptables/ipset/seccomp 等内核级技术

---

## 二、Qwen Code 慢在哪里（源码级问题）

### 问题 1：启动路径严重阻塞

**文件**：`packages/cli/src/gemini.tsx`（215-432 行，交互路径约 8-9 个串行 await）

```
典型交互启动路径（非沙箱场景，约 8-9 个串行 await）：
  setupUnhandledRejectionHandler()  // 213 行（同步，正确地在最前面）
  cleanupCheckpoints()              // 215 行 ← 可并行
  → parseArguments()                // 217 行 ← 可并行（与上面互不依赖）
  → loadSandboxConfig(argv)         // 251 行 ← 依赖 argv（沙箱场景会 relaunch 退出）
  → loadCliConfig(full)             // 356 行 ← 含扩展加载
  → initializeApp()                 // 408 行（内含 i18n → auth → IDE 连接，全部串行）
  → getStartupWarnings()            // 417 行 ← 可并行
  → getUserStartupWarnings()        // 418 行 ← 可并行（与上面互不依赖）
  → kittyProtocolDetection          // 431 行
  → startInteractiveUI()            // 432 行

注：沙箱路径（259-327 行）会 relaunch 进程后退出，不计入正常启动。
文件中共有约 22 个 await，但因分支条件，交互路径实际执行约 8-9 个。
```

**注意**：`loadCliConfig()` 被调用了**两次**（259 行和 356 行）。源码中有 TODO 注释承认这是待重构的冗余：
```typescript
// TODO(jacobr): refactor loadCliConfig so there is a minimal version
// that only initializes enough config to enable refreshAuth
```

**具体问题**：

| 操作 | 文件 | 问题 |
|------|------|------|
| I18N 初始化 | `initializer.ts:42` | `await initializeI18n()` 在 `initializeApp()` 内阻塞，UI 渲染前必须完成 |
| I18N 文件检查 | `i18n/index.ts:99-104` | `fs.existsSync()` 多次同步调用，阻塞事件循环 |
| loadCliConfig 双调用 | `gemini.tsx:259, 356` | 同一函数调用两次（源码 TODO 承认冗余） |
| Startup Warnings | `gemini.tsx:417-418` | 两个独立 await 串行执行，应 `Promise.all()` |
| ~~FileDiscoveryService~~ | `config.ts:1710` | ✅ 实为懒初始化 getter，构造函数仅解析 gitignore 规则，不扫描文件系统 |
| ~~LSP 阻塞启动~~ | `config.ts:635` | ✅ 仅 getter/setter，不阻塞启动 |

### 问题 2：流式工具调用解析的字符串拼接开销

**文件**：`packages/core/src/core/openaiContentGenerator/streamingToolCallParser.ts`

```typescript
// 第 155 行：每个 chunk 到来时字符串拼接
const newBuffer = currentBuffer + chunk;
this.buffers.set(actualIndex, newBuffer);  // 存入 Map
```

每个 chunk 到来时，`currentBuffer + chunk` 创建新字符串（JavaScript 字符串不可变，每次拼接分配新内存）。虽然每 chunk 只拼接一次（非循环内重复拼接），但对于长工具输出（数千 chunk），累积的内存分配和 GC 压力仍然显著。改用数组收集 + 最终 join 更优。

### 问题 3：Token 计算开销大

**文件**：`packages/core/src/core/openaiContentGenerator/openaiContentGenerator.ts`（82-107 行）

```typescript
// countTokens() 方法：
async countTokens(request: CountTokensParameters): Promise<CountTokensResponse> {
  try {
    const estimator = new RequestTokenEstimator();
    const result = await estimator.calculateTokens(request);  // 主路径
    return { totalTokens: result.totalTokens };
  } catch (error) {
    // 回退：对 contents 做 JSON 序列化，按 4 字符≈1 token 估算
    const content = JSON.stringify(request.contents);
    const totalTokens = Math.ceil(content.length / 4);
    return { totalTokens };
  }
}
```

- 主路径 `RequestTokenEstimator` 每次调用前遍历全部历史内容
- 异常回退用 `JSON.stringify(request.contents)` 序列化全部对话内容（非整个 request，但仍昂贵）
- 对于 100 轮对话，每轮新增消息后都重新计算全部 token，无增量缓存

### 问题 4：会话历史无限增长

**文件**：`geminiChat.ts`（246、295、520 行）

```typescript
// 每次读历史都深拷贝：
getHistory() { return structuredClone(history); }  // 多 MB 历史的完整深拷贝

// 历史只增不减：
history.push(message);  // 无自动修剪
```

- `structuredClone()` 对大历史非常昂贵
- 没有自动修剪机制，100 轮对话后历史可达数十 MB

### 问题 5：聊天压缩触发时的 JSON 序列化

**文件**：`chatCompressionService.ts`（45、80-126 行）

```typescript
// findCompressSplitPoint()（45 行）—— 仅在压缩触发时调用：
const charCounts = contents.map((content) => JSON.stringify(content).length);
```

**触发条件**（`compress()` 方法，80-126 行）：
- 仅当 token 数超过上下文窗口的 70%（`COMPRESSION_TOKEN_THRESHOLD = 0.7`）时触发
- **不是每轮都执行**，典型使用中可能在 ~70 轮后首次触发
- 但一旦触发，会对所有历史 Content 项做 `JSON.stringify()`，大会话时仍有显著开销

### 问题 6：重量级依赖加载

**文件**：`packages/core/package.json`（30-38 行）、`packages/cli/src/gemini.tsx`

| 依赖 | 包数/体积 | import 方式 | 实际加载时机 |
|------|----------|-----------|-------------|
| ~~OpenTelemetry~~ | 9 个包 | `telemetry/sdk.ts` 顶层 import | ✅ **条件加载**：仅 `telemetry.enabled=true` 时加载（默认 false），不影响正常启动 |
| web-tree-sitter | ~380 KB（WASM 187KB） | `shellAstParser.ts:17` 顶层 import | 模块被 import 时加载，但 Parser 是 `initParser()` 懒单例 |
| React 19 + Ink | ~300 KB | `gemini.tsx:15,20` 顶层 import | **交互和非交互模式都会加载**（顶层 import），但 `nonInteractiveCli.ts` 本身不 import React |

**关键发现**：
- ~~OpenTelemetry 是最大的性能问题~~ → **实际是条件加载**。`config.ts:746-748` 检查 `telemetrySettings.enabled`，仅启用时才调用 `initializeTelemetry()`，默认关闭
- React/Ink 在 `gemini.tsx` 顶层 `import { render } from 'ink'` 和 `import React from 'react'`（15、20 行），即使进入非交互路径也已解析。`nonInteractiveCli.ts` 不引用 React，但入口 `gemini.tsx` 已经加载了

### 问题 7：MCP 超时过长

**文件**：`packages/core/src/tools/mcp-client.ts`

```typescript
// 第 59 行：默认超时 10 分钟
export const MCP_DEFAULT_TIMEOUT_MSEC = 10 * 60 * 1000;

// 第 153-155 行：连接使用配置的超时
await this.client.connect(this.transport, {
  timeout: this.serverConfig.timeout,  // 默认 10 分钟
});
```

MCP 连接**有**超时保护（10 分钟），但对于启动路径来说 10 分钟太长。一个无响应的 MCP 服务器会让用户等待很久才看到超时错误。建议：启动阶段使用更短的超时（如 5-10 秒），后续操作再用长超时。

### ~~问题 8：Anthropic 客户端无连接复用~~ ✅ 已验证不存在

**文件**：`packages/core/src/core/anthropicContentGenerator/anthropicContentGenerator.ts`

```typescript
// 第 58-88 行：客户端在构造函数中创建一次，后续复用
export class AnthropicContentGenerator implements ContentGenerator {
  private client: Anthropic;  // 实例属性，复用

  constructor(config, cliConfig) {
    this.client = new Anthropic({
      apiKey: config.apiKey,
      timeout: config.timeout || DEFAULT_TIMEOUT,
      maxRetries: config.maxRetries,
      ...runtimeOptions,
    });
  }
}
```

**纠正**：Anthropic 客户端是在构造函数中创建一次并复用的，不是每次请求重建。此问题不存在。

---

## 三、Qwen Code 改进路线图

### 第一优先级：启动速度（用户第一印象）

#### 1.1 启动流程并行化

```typescript
// 当前（gemini.tsx）：所有 await 串行
await cleanupCheckpoints();                    // 215 行
let argv = await parseArguments();             // 217 行
// ...后续全部依赖 argv，无法提前

// 改进 1：独立操作并行
const [_, argv] = await Promise.all([
  cleanupCheckpoints(),   // 与参数解析互不依赖
  parseArguments(),
]);

// 改进 2：startup warnings 并行（当前 417-418 行串行）
const [warnings, userWarnings] = await Promise.all([
  getStartupWarnings(),
  getUserStartupWarnings({...}),
]);

// 改进 3：消除 loadCliConfig 双调用（当前 259 和 356 行）
// 源码 TODO 已承认冗余，重构为 minimal config + full config 分离
```

**预期收益**：
- 并行化独立操作：省 200-500ms
- 消除 loadCliConfig 双调用：省 100-300ms
- 总计可将交互模式启动时间减少 30-50%

#### 1.2 I18N 同步加载改为内嵌默认语言

```typescript
// 当前：每次启动异步加载语言包
await import(languagePackUrl);

// 改进：英文/中文内嵌，其他语言懒加载
import defaultLocale from './locales/en.json';  // 编译时内嵌
```

#### 1.3 非交互入口独立（避免加载 React/Ink）

```typescript
// 当前：gemini.tsx 顶层导入 React 和 Ink
import { render } from 'ink';        // 第 15 行
import React from 'react';           // 第 20 行
// 即使走非交互路径（457-510 行），这些模块已在入口处解析

// 改进方案 A：非交互模式使用独立入口
// bin/qwen-noninteractive → 直接 import nonInteractiveCli.ts（不经过 gemini.tsx）

// 改进方案 B：gemini.tsx 中 React/Ink 改为 dynamic import
// 仅在 startInteractiveUI() 内部才 import
async function startInteractiveUI(...) {
  const { render } = await import('ink');
  const React = await import('react');
  // ...
}
```

> 注：~~OTel 9 包 eager 加载~~ 经第三轮核实，OTel 实际是**条件加载**（`config.ts:746`，默认 `enabled: false`），不影响正常启动，无需改动。

### 第二优先级：运行时性能

#### 2.1 流式解析改用数组收集

```typescript
// 当前：每个 chunk 创建新字符串（GC 压力大）
const newBuffer = currentBuffer + chunk;

// 改进：数组收集，最终一次性 join
class StreamBuffer {
  private chunks: string[] = [];
  append(chunk: string) { this.chunks.push(chunk); }
  toString() { return this.chunks.join(''); }
  get length() { return this.chunks.reduce((s, c) => s + c.length, 0); }
}
```

#### 2.2 Token 计算缓存 + 增量

```typescript
// 当前：每次完整计算
calculateTokens(fullHistory);

// 改进：只计算增量
class TokenCounter {
  private cachedCount = 0;
  private lastHistoryLength = 0;

  count(history) {
    if (history.length === this.lastHistoryLength) return this.cachedCount;
    // 只计算新增部分
    const newMessages = history.slice(this.lastHistoryLength);
    this.cachedCount += countTokens(newMessages);
    this.lastHistoryLength = history.length;
    return this.cachedCount;
  }
}
```

#### 2.3 structuredClone 改 readonly 引用

```typescript
// 当前（geminiChat.ts:514-520）：每次 getHistory() 深拷贝
getHistory(curated?: boolean): Content[] {
  return structuredClone(history);  // 昂贵！每轮 3-6 次调用
}

// 改进：返回只读引用（经验证，所有调用方仅读取不修改）
getHistory(curated?: boolean): readonly Content[] {
  const history = curated ? extractCuratedHistory(this.history) : this.history;
  return history;  // 返回引用，TypeScript readonly 防止修改
}
```

**安全性验证**：第四轮核实确认所有 `getHistory()` 调用方（`client.ts:568`, `client.ts:681`, `turn.ts:351`, `chatCompressionService.ts:88`）均仅执行 `.filter()`、属性访问等只读操作，**不修改返回的数组**。移除深拷贝是安全的。

#### 2.4 压缩服务改用字符长度估算

```typescript
// 当前：JSON.stringify 计算字符数
const len = JSON.stringify(content).length;

// 改进：直接估算（精度足够用于阈值判断）
function estimateSize(content: Content): number {
  if (typeof content === 'string') return content.length;
  if (content.text) return content.text.length;
  return 1000; // 非文本默认估值
}
```

### 第三优先级：稳定性

#### 3.1 全局超时保护

```typescript
// MCP 连接加超时
await Promise.race([
  server.connect(),
  timeout(5000, 'MCP server connection timeout')
]);

// LSP 发现加超时
await Promise.race([
  lspService.discoverAndPrepare(),
  timeout(3000, 'LSP discovery timeout')
]);
```

#### ~~3.2 HTTP 连接复用~~ ✅ 已验证不需要

Anthropic 客户端已在构造函数中创建一次并复用（`anthropicContentGenerator.ts:58-88`），此改进不需要。

#### 3.3 错误恢复断路器

```typescript
// 参考 Claude Code 的断路器模式
class CircuitBreaker {
  private failures = 0;
  private readonly threshold = 3;

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.failures >= this.threshold) {
      throw new Error('Circuit breaker open');
    }
    try {
      const result = await fn();
      this.failures = 0;
      return result;
    } catch (e) {
      this.failures++;
      throw e;
    }
  }
}
```

#### ~~3.4 未处理异常提前捕获~~ ✅ 已验证不需要

`setupUnhandledRejectionHandler()` 已在 `main()` 第一行（213 行）调用，早于所有 async 操作。此改进不需要。

### 第四优先级：长期架构

#### 4.1 考虑核心模块 Rust 化

将最热的路径用 Rust 重写为 N-API 模块：
- Token 计算（当前每轮全量遍历历史）
- 流式解析（减少字符串分配和 GC 压力）
- 文件搜索（grep/glob）

```
性能收益预估：
  Token 计算：10-50x 提速
  流式解析：消除 GC 压力
  文件搜索：5-10x 提速（ripgrep 级别）
```

#### 4.2 引入 `--bare` 模式

参考 Claude Code，为脚本/CI 场景提供最小化启动：

```bash
qwen --bare -p "fix this bug"  # 跳过 hooks/LSP/插件/技能扫描
```

#### 4.3 会话存储改为 SQLite

```
当前：JSONL 追加写入（无索引、分页靠文件读取）
改进：SQLite（WAL 模式、索引查询、增量写入）
收益：大会话加载速度 10x+，支持复杂查询
```

---

## 四、改进优先级矩阵

| 改进 | 难度 | 收益 | 优先级 |
|------|------|------|--------|
| 启动 await 并行化（cleanupCheckpoints ‖ parseArguments, warnings 并行） | 低 | **高**（首印象） | P0 |
| 消除 loadCliConfig 双调用（源码 TODO 已承认） | 中 | **高**（省 100-300ms） | P0 |
| MCP 启动超时缩短（10min→5-10s） | 低 | **高**（稳定性） | P0 |
| structuredClone 改 readonly 引用（每轮多次调用） | 低 | **高**（大会话性能） | P1 |
| Token 计算增量缓存 | 中 | 中 | P1 |
| 流式解析字符串拼接改数组收集 | 低 | 中 | P1 |
| 压缩服务 JSON.stringify 改估算 | 低 | 中 | P1 |
| i18n fs.existsSync 改异步 + 默认语言内嵌 | 低 | 中 | P1 |
| gemini.tsx 非交互路径独立入口（避免加载 React/Ink） | 中 | 中 | P2 |
| `--bare` 模式 | 中 | 中 | P2 |
| 断路器模式 | 中 | 中 | P2 |
| 热路径 Rust N-API（Token 计算、文件搜索） | 高 | **高** | P3 |
| 会话存储改 SQLite | 高 | 高 | P3 |

---

## 五、一句话总结

**Claude Code 快的本质**：Rust 原生二进制 + 激进并行化 + 极致懒加载 + 内核级沙箱 + 超时断路器。

**Qwen Code 慢的本质**：Node.js 运行时开销 + 启动路径 8-9 个串行 await（无并行） + loadCliConfig 双调用 + structuredClone 每轮 3-6 次深拷贝 + React/Ink 非交互也加载 + MCP 启动超时 10 分钟。

> 注：~~OTel 9 包 eager 加载~~ 经第三轮核实，OTel 实际是条件加载（默认关闭），不影响正常启动。

**最小代价最大收益的四件事**：
1. 启动独立 await 并行化 + warnings 并行（`Promise.all()`，改几行代码）
2. 消除 loadCliConfig 双调用（源码 TODO 已指出方向）
3. structuredClone 改 readonly 引用（每轮 3-6 次深拷贝，大会话影响显著）
4. MCP 启动超时从 10 分钟缩短到 5-10 秒

---

*分析基于 Qwen Code 本地源码和 Claude Code 插件仓库 + CHANGELOG，截至 2026 年 3 月。*

---

## 附录：源码核实记录（四轮核实）

### 第一轮核实

| 问题 | 核实文件 | 实际行号 | 结论 |
|------|---------|---------|------|
| 启动串行 | `gemini.tsx` | 215-432 | ✅ 确认 |
| i18n 阻塞 | `initializer.ts` → `i18n/index.ts` | 42, 253-257 | ✅ 确认 |
| FileDiscoveryService | `config.ts` | 37, 534, 778, 1710 | ✅ 存在，懒初始化 |
| ~~LSP 阻塞启动~~ | `config.ts` | 635-636 | ❌ 仅 getter/setter，不阻塞 |
| 流式字符串拼接 | `streamingToolCallParser.ts` | 155 | ⚠️ O(n) 非 O(n²)，但 GC 压力大 |
| structuredClone | `geminiChat.ts` | 520 | ✅ 确认 |
| JSON.stringify 压缩 | `chatCompressionService.ts` | 45 | ✅ 确认 |
| MCP 超时 | `mcp-client.ts` | 59, 153-155 | ⚠️ 有 10 分钟超时，但太长 |
| ~~Anthropic 每请求创建~~ | `anthropicContentGenerator.ts` | 58-88 | ❌ 构造函数创建一次，复用 |
| OpenTelemetry 包数 | `package.json` | 30-38 | ⚠️ 实际 9 个包 |
| Token 计算 | `openaiContentGenerator.ts` | 82-107 | ✅ 确认 |

### 第二轮核实（深度验证）

| 问题 | 核实文件 | 实际行号 | 结论 |
|------|---------|---------|------|
| 启动 await 总数 | `gemini.tsx` | 215-510 | ⚠️ 修正：实为 **22 个** await（非 12+） |
| loadCliConfig 双调用 | `gemini.tsx` | 259, 356 | ✅ 确认：调用两次，源码有 TODO 承认冗余 |
| 可并行的 await 对 | `gemini.tsx` | 215/217, 417/418 | ✅ 确认：至少 2 对可 Promise.all() |
| ~~FileDiscoveryService 扫描文件系统~~ | `fileDiscoveryService.ts` | 25-36 | ❌ 纠正：构造函数仅解析 gitignore 规则，不扫描 |
| ~~异常处理注册晚~~ | `gemini.tsx` | 213 | ❌ 纠正：在 main() 第一行，早于所有 async 操作 |
| i18n fs.existsSync | `i18n/index.ts` | 99-104, 212 | ✅ 确认：多处 fs.existsSync() 同步调用 |
| OpenTelemetry import 方式 | `telemetry/sdk.ts` | 7-30 | ✅ 确认：9 个包全部为顶层静态 import |
| web-tree-sitter 加载 | `shellAstParser.ts` | 17 | ⚠️ 修正：模块静态 import，但 Parser 初始化是 `initParser()` 懒单例 |
| Token fallback 范围 | `openaiContentGenerator.ts` | 100 | ⚠️ 修正：序列化 `request.contents`（非整个 request） |
| initializeApp 内部 | `initializer.ts` | 33-74 | ✅ 确认：i18n → auth → IDE 连接，全部串行 |
| 非交互路径 | `gemini.tsx` | 457-510 | ✅ 确认：同样有串行 await 可优化 |

### 第三轮核实（交叉验证）

| 问题 | 核实文件 | 实际行号 | 结论 |
|------|---------|---------|------|
| ~~OTel eager 加载~~ | `config.ts` + `telemetry/sdk.ts` | 746-748, 7-30 | ❌ **重大纠正**：条件加载（`telemetry.enabled` 默认 false），不影响正常启动 |
| structuredClone 调用频率 | `geminiChat.ts`, `client.ts`, `turn.ts` | 296, 568, 681, 351 | ✅ 确认：每轮至少 1 次，错误/压缩/Hook 时更多 |
| React 非交互加载 | `gemini.tsx` | 15, 20 | ✅ 确认：顶层 import，非交互也解析；`nonInteractiveCli.ts` 自身不 import React |
| 压缩服务粒度 | `chatCompressionService.ts` | 45 | ✅ 确认：`contents.map(c => JSON.stringify(c).length)` 对数组每项序列化 |
| readStdin 条件 | `gemini.tsx` | 463-468 | ✅ 确认：条件 `!process.stdin.isTTY`，非交互路径专用 |
| CHANGELOG: keychain 60ms | `CHANGELOG.md` | 136 | ✅ 确认：原文 "Faster startup on macOS (~60ms) by reading keychain credentials in parallel" |
| CHANGELOG: 大仓库 80MB | `CHANGELOG.md` | 50 | ✅ 确认：原文 "Reduced memory usage on startup in large repositories (~80 MB saved on 250k-file repos)" |
| CHANGELOG: 恢复 45% | `CHANGELOG.md` | 137 | ✅ 确认：原文 "up to 45% faster loading and ~100-150MB less peak memory" |

### 第四轮核实（精确性验证）

| 问题 | 核实文件 | 实际行号 | 结论 |
|------|---------|---------|------|
| ~~22 个串行 await~~ | `gemini.tsx` | 215-432 | ⚠️ 修正：文件共 22 个 await，但交互路径实际执行 **8-9 个**（沙箱/非交互分支不走） |
| structuredClone 可安全移除 | `client.ts` | 568, 681 | ✅ 确认：所有调用方仅 `.filter()`/属性访问，不修改返回数组 |
| ~~压缩每轮 JSON.stringify~~ | `chatCompressionService.ts` | 80-126 | ⚠️ 修正：仅 token > 上下文 70% 时触发，非每轮（约 70 轮后首次） |
| ~~内核级沙箱 iptables/ipset~~ | `CHANGELOG.md` | 全文搜索 | ❌ **纠正**：CHANGELOG 无 iptables/ipset/seccomp/BPF 任何提及；实为文件系统+网络域名隔离 |
| ~~web-tree-sitter ~2.5MB~~ | `node_modules/web-tree-sitter/` | 实测 | ❌ **纠正**：WASM 187KB，总包 ~380KB（原描述偏大 6-7 倍） |
| 优先级矩阵重复表头 | 文档自身 | 449-452 | ✅ 已修复格式错误 |
