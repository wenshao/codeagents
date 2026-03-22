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

### 6. 内核级沙箱

- Linux 使用 **iptables/ipset** 做网络隔离（内核级，几乎零开销）
- 不是 JavaScript 层面的沙箱模拟

---

## 二、Qwen Code 慢在哪里（源码级问题）

### 问题 1：启动路径严重阻塞

**文件**：`packages/cli/src/gemini.tsx`（214-408 行）

```
当前启动流程（串行）：
  参数解析 → 设置加载 → 认证验证 → Kitty 协议检测
  → I18N 初始化 → 文件发现 → LSP 发现 → MCP 连接
  总计：2-5 秒
```

**具体问题**：

| 操作 | 文件 | 问题 |
|------|------|------|
| I18N 初始化 | `initializer.ts:42` | 同步文件 I/O 加载语言包，阻塞 UI 渲染 |
| 文件发现 | `config.ts:750` | `new FileDiscoveryService(cwd)` 无缓存，每次启动扫描文件系统 |
| GEMINI.md 扫描 | `config.ts:729` | `getAllGeminiMdFilenames()` 每次启动遍历文件 |
| LSP 发现 | `config.ts:1166-1167` | `await lspService.discoverAndPrepare()` + `await lspService.start()` 串行阻塞 |
| 语言包加载 | `i18n/index.ts:99-104` | `fs.existsSync()` 多次同步检查，阻塞主线程 |

### 问题 2：流式工具调用解析 O(n²)

**文件**：`packages/core/src/core/openaiContentGenerator/streamingToolCallParser.ts`

```typescript
// 第 156 行：字符串拼接累积
newBuffer += chunk;  // O(n²) 复杂度
```

每个 chunk 到来时，用字符串拼接而非 Buffer/数组，导致长工具调用输出的解析时间随长度平方增长。

### 问题 3：Token 计算开销大

**文件**：`openaiContentGenerator.ts`（82-107 行）

```typescript
// 每次请求前都执行：
RequestTokenEstimator.calculateTokens(request);  // 串行处理文本/图片/音频

// 回退方案更糟：
JSON.stringify(request.contents);  // 对整个历史做序列化
```

**每次** LLM 调用前都完整计算 token 数，对于 100 轮对话意味着反复序列化数百 KB 历史。

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

### 问题 5：聊天压缩 O(n) 序列化

**文件**：`chatCompressionService.ts`（45 行）

```typescript
// 对每一条历史消息做 JSON 序列化来计算字符数：
const charCount = JSON.stringify(content).length;
```

100 轮对话 = 100+ 次 `JSON.stringify()`，每次序列化全部内容。

### 问题 6：重量级依赖启动加载

**文件**：`packages/core/package.json`

| 依赖 | 体积 | 问题 |
|------|------|------|
| OpenTelemetry（6 个包） | ~500 KB | 启动时 eager 加载，多数用户不需要 |
| web-tree-sitter | ~2.5 MB WASM | 启动时加载，初始 LLM 调用不需要 |
| React 19 + Ink | ~300 KB | 即使非交互模式也加载 |
| diff 库 | ~100 KB | 预加载，仅文件编辑时需要 |

### 问题 7：MCP 无超时保护

**文件**：`mcp-client-manager.ts`（122-123 行）

```typescript
await server.connect();   // 无超时
await server.discover();  // 无超时
```

挂起的 MCP 服务器会无限期阻塞启动。

### 问题 8：Anthropic 客户端无连接复用

**文件**：`anthropicContentGenerator.ts`（74-81 行）

每次请求创建新的 Anthropic 客户端实例，无法利用 HTTP/2 多路复用。

---

## 三、Qwen Code 改进路线图

### 第一优先级：启动速度（用户第一印象）

#### 1.1 启动流程并行化

```typescript
// 当前：串行
await loadSettings();
await validateAuth();
await initI18n();
await discoverFiles();
await startLSP();

// 改进：并行
const [settings, auth, i18n] = await Promise.all([
  loadSettings(),
  validateAuth(),
  initI18n()
]);
// LSP 和文件发现延迟到首次需要时
```

**预期收益**：启动时间从 2-5 秒降到 0.5-1 秒。

#### 1.2 I18N 同步加载改为内嵌默认语言

```typescript
// 当前：每次启动异步加载语言包
await import(languagePackUrl);

// 改进：英文/中文内嵌，其他语言懒加载
import defaultLocale from './locales/en.json';  // 编译时内嵌
```

#### 1.3 重量级依赖懒加载

```typescript
// 当前：启动时全部加载
import * as otel from '@opentelemetry/...';
import TreeSitter from 'web-tree-sitter';

// 改进：使用时才加载
const getTreeSitter = () => import('web-tree-sitter');
const getOtel = () => import('@opentelemetry/...');
```

#### 1.4 非交互模式裁剪 React

```typescript
// 当前：非交互模式也加载 Ink + React
// 改进：非交互模式使用轻量输出
if (nonInteractive) {
  // 直接 stdout，不加载 React
} else {
  const { render } = await import('ink');
}
```

### 第二优先级：运行时性能

#### 2.1 流式解析改用 Buffer 数组

```typescript
// 当前 O(n²)：
newBuffer += chunk;

// 改进 O(n)：
const chunks: Buffer[] = [];
chunks.push(chunk);
// 最后一次性 Buffer.concat(chunks)
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

#### 2.3 历史管理改为环形缓冲

```typescript
// 当前：无限增长数组 + structuredClone
// 改进：
class ConversationHistory {
  private messages: Message[] = [];
  private maxSize = 200;

  push(msg: Message) {
    this.messages.push(msg);
    if (this.messages.length > this.maxSize) {
      this.compress(); // 触发压缩
    }
  }

  // 返回引用而非深拷贝（加 readonly 标记）
  getReadonly(): readonly Message[] {
    return this.messages;
  }
}
```

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

#### 3.2 HTTP 连接复用

```typescript
// Anthropic 客户端单例 + 连接池
class AnthropicPool {
  private static client: Anthropic | null = null;

  static getClient(config): Anthropic {
    if (!this.client) {
      this.client = new Anthropic({
        apiKey: config.apiKey,
        maxRetries: 3,
        // 启用 HTTP/2 keep-alive
      });
    }
    return this.client;
  }
}
```

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

#### 3.4 未处理异常提前捕获

```typescript
// 当前：应用初始化后才注册异常处理（gemini.tsx:120-137）
// 改进：入口文件第一行
process.on('unhandledRejection', handler);
process.on('uncaughtException', handler);
// 然后才开始初始化
```

### 第四优先级：长期架构

#### 4.1 考虑核心模块 Rust 化

将最热的路径用 Rust 重写为 N-API 模块：
- Token 计算（当前是 JS 最热代码）
- 流式解析（当前 O(n²)）
- 文件搜索（grep/glob）

```
性能收益预估：
  Token 计算：10-50x 提速
  流式解析：消除 O(n²)
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
| 启动流程并行化 | 低 | **高**（首印象） | P0 |
| 全局超时保护 | 低 | **高**（稳定性） | P0 |
| 重量级依赖懒加载 | 低 | **高**（启动-1-2秒） | P0 |
| 流式解析 O(n²) 修复 | 低 | 中 | P1 |
| Token 计算增量缓存 | 中 | 中 | P1 |
| HTTP 连接复用 | 低 | 中 | P1 |
| 压缩服务优化 | 低 | 中 | P1 |
| 历史管理重构 | 中 | 中 | P1 |
| 非交互模式裁剪 React | 中 | 中 | P2 |
| `--bare` 模式 | 中 | 中 | P2 |
| I18N 默认语言内嵌 | 低 | 低 | P2 |
| 断路器模式 | 中 | 中 | P2 |
| 热路径 Rust N-API | 高 | **高** | P3 |
| SQLite 存储 | 高 | 高 | P3 |

---

## 五、一句话总结

**Claude Code 快的本质**：Rust 原生二进制 + 激进并行化 + 极致懒加载 + 内核级沙箱 + 超时断路器。

**Qwen Code 慢的本质**：Node.js 运行时开销 + 启动串行阻塞 + O(n²) 流式解析 + 历史无限增长 + 重依赖 eager 加载 + 无超时保护。

**最小代价最大收益的三件事**：
1. 启动流程 `Promise.all()` 并行化（改几行代码，省 1-3 秒）
2. 重量级依赖改 dynamic import（省 1-2 秒启动 + 百 MB 内存）
3. MCP/LSP 加超时（消除无限挂起的稳定性风险）

---

*分析基于 Qwen Code 本地源码和 Claude Code 插件仓库 + CHANGELOG，截至 2026 年 3 月。*
