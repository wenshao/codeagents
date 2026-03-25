# 19. Qwen Code vs Gemini CLI vs Kimi CLI：源码级深度对比

> 三个有渊源关系的 CLI 编程代理：Gemini CLI（上游）→ Qwen Code（分叉增强）↔ Kimi CLI（独立实现）

## 项目谱系

```
Google Gemini CLI (上游, TypeScript)
    │
    ├── 分叉 ──→ Qwen Code (阿里云, TypeScript)
    │              增加: 多提供商、Arena、子代理、国际化
    │
    └── 独立参考 ──→ Kimi CLI (月之暗面, Python)
                       独立: 双模式交互、Wire 协议、Moonshot 服务
```

## 概览对比

| 维度 | Gemini CLI | Qwen Code | Kimi CLI |
|------|-----------|-----------|----------|
| **开发者** | Google | 阿里云 | 月之暗面 |
| **语言** | TypeScript | TypeScript | Python (68.8%) |
| **代码量** | ~191k 行 | ~191k 行（分叉） | ~20k 行 |
| **上游关系** | 原创 | Gemini CLI 分叉 | 独立实现 |
| **许可证** | Apache-2.0 | Apache-2.0 | 开源 |
| **CLI 框架** | Ink + React 19 | Ink + React 19 | Typer + Rich |
| **运行时** | Node.js | Node.js 20+ | Python 3.12+ |

---

## 1. 代理循环

### Gemini CLI

```typescript
// packages/core/src/core/client.ts
class GeminiClient {
  MAX_TURNS = 100;

  async *sendMessageStream(request, signal, promptId, turns, isRetry, displayContent) {
    // Turn 对象包装每轮迭代
    // 流式 yield 事件
    // retryWithBackoff() 处理无效流
    // 自动 "please continue" 检测
  }
}
```

- **100 轮上限**，通过 `Turn` 对象管理每轮状态
- **流式生成器**模式（`async *`），逐步 yield 事件
- **模型粘性**：`currentSequenceModel` 跨轮保持同一模型
- **重试策略**：`retryWithBackoff()` 处理 Gemini 2 的无效流
- **Hook 系统**：回调式 before/after agent hook

### Qwen Code（继承 + 增强）

```typescript
// packages/core/src/core/client.ts
class GeminiClient {  // 保留类名
  MAX_TURNS = 100;    // 相同

  // 新增: 消息类型枚举
  enum SendMessageType { UserQuery, ToolResult, Retry, Hook }

  // 新增: Token 限制检查
  if (config.getSessionTokenLimit()) { ... }

  // 新增: Arena 控制信号
  if (arenaClient) { checkArenaControl(); }

  // 新增: 子代理系统提醒
  systemReminders.push(subagentReminder, planModeReminder);
}
```

**Qwen Code 在 Gemini CLI 基础上增加了**：

| 增强 | 说明 |
|------|------|
| `SendMessageType` 枚举 | 区分 UserQuery/ToolResult/Retry/Hook 四种消息 |
| Session Token 限制 | 硬性 token 预算上限 + 遥测 |
| Arena 集成 | 控制信号、状态上报、错误处理 |
| 子代理管理 | `getSubagentManager()` 委托工作 |
| 系统提醒 | 动态注入子代理/Plan 模式/Arena 上下文 |
| MessageBus Hook | 事件驱动的 Hook 系统（替代回调式） |
| 会话录制 | `ChatRecordingService` 持久化 |
| IDE 上下文格式 | 纯文本（Gemini 用 JSON） |

### Kimi CLI（独立 Python 实现）

```python
# src/kimi_cli/app.py
class KimiCLI:
    @classmethod
    def create(cls, config: Config) -> 'KimiCLI':
        # 工厂模式创建
        # 加载配置、OAuth 认证、插件初始化

    async def run_shell(self):
        # TUI 交互模式（主要模式）
        # Ctrl-X 切换到 Shell 模式

    async def run_acp(self):
        # IDE 集成（ACP 协议）
```

- **Python 异步**：`async/await` + Pydantic 类型安全
- **多执行模式**：`run_shell()`、`run_print()`、`run_acp()`、`run_wire_stdio()`
- **双模式交互**：Agent ↔ Shell（Ctrl-X 切换），Wire 协议保持上下文
- **配置驱动**：`agent_loop.max_steps = 20`（远少于 Gemini/Qwen 的 100）
- **自动压缩**：80% 容量时触发上下文压缩

**关键差异**：
- Gemini/Qwen 的循环是**流式生成器**模式；Kimi 是**传统异步**模式
- Gemini/Qwen 100 轮上限；Kimi 默认 20 步
- Kimi 的双模式交互在 Gemini/Qwen 中没有对应概念

---

## 2. 工具调度器

### Gemini CLI：事件驱动状态机

```
Scheduler 类
  ├── requestQueue（请求队列，支持并发批次）
  ├── SchedulerStateManager（状态管理）
  ├── 生命周期: Validating → Scheduled → Executing → Success/Error
  ├── checkPolicy() → PolicyEngine
  ├── resolveConfirmation() → 用户确认
  └── tailToolCallRequest → 工具链式调用
```

- **请求队列**：支持并发批次调度
- **状态机**：每个工具调用有完整生命周期
- **尾调用**：`tailToolCallRequest` 支持工具链式执行
- **策略集成**：内联 `PolicyEngine` 检查

### Qwen Code：Hook 驱动调度器

```
CoreToolScheduler
  ├── 无请求队列（更简单的同步调度）
  ├── 生命周期: validating → awaiting_approval → executing → success/error
  ├── buildPermissionRules() → PermissionManager
  ├── toolHookTriggers（Pre/Post 工具 Hook）
  ├── modifyWithEditor()（交互式编辑）
  ├── Levenshtein 距离（工具名模糊匹配）
  └── outputUpdateHandler（实时输出流）
```

**Qwen 增加的调度能力**：

| 特性 | Gemini CLI | Qwen Code |
|------|-----------|-----------|
| 请求队列 | ✓（并发批次） | ✗（更简单） |
| 工具链式调用 | ✓（tailToolCall） | ✗ |
| Pre/Post Hook | ✗ | ✓（toolHookTriggers） |
| 交互式编辑 | ✗ | ✓（modifyWithEditor） |
| 模糊匹配 | ✗ | ✓（Levenshtein） |
| 实时输出流 | 通过状态更新 | ✓（outputUpdateHandler） |
| 截断检测 | ✗ | ✓（引导信息） |

### Kimi CLI：Python 工具执行器

```python
# src/kimi_cli/tools/ 目录
tools/
├── file/          # read/write/edit
├── shell/         # AST 安全分析
├── web/           # Moonshot Search/Fetch
├── think/         # 推理
├── plan/          # 规划
├── multiagent/    # 多代理
├── background/    # 后台任务
└── todo/          # 任务管理
```

- **直接函数调用**：无状态机，工具是普通异步函数
- **AST 命令分析**：Shell 工具解析命令 AST 判断安全性
- **后台任务**：`background/` 支持异步长时间运行
- **多代理**：`multiagent/` 通过 Channel 通信

**关键差异**：Gemini 有最复杂的调度器（状态机 + 队列 + 尾调用），Qwen 简化但加了 Hook，Kimi 最简单（直接调用）。

---

## 3. 权限/策略系统

### Gemini CLI：TOML 策略引擎

```typescript
// packages/core/src/policy/policy-engine.ts
class PolicyEngine {
  // 规则类型: PolicyRule | SafetyCheckerRule | HookCheckerRule
  // 决策: DENY | ASK_USER | ALLOW
  // 审批模式: DEFAULT | AUTO_EDIT | YOLO

  check(toolCall, serverName, toolAnnotations): CheckResult {
    // 通配符: *, server__*, *__tool
    // 正则参数匹配
    // 递归 Shell 命令验证（重定向检测）
    // 外挂安全检查器进程
  }
}
```

### Qwen Code：配置驱动权限管理

```typescript
// packages/core/src/permissions/permission-manager.ts
class PermissionManager {
  // 规则集: persistentRules（持久）+ sessionRules（会话级）
  // 优先级: deny(3) > ask(2) > default(1) > allow(0)

  evaluate(ctx: PermissionCheckContext): PermissionDecision {
    // Shell 虚拟操作提取（文件/网络）
    // 复合命令拆分 splitCompoundCommand()
    // 相对路径解析
    // Legacy coreTools 白名单兼容
  }
}
```

### Kimi CLI：规则优先级权限

```python
# src/kimi_cli/config.py
permissions:
  shell: "ask"           # ask/allow/deny
  file:
    read: "allow"
    write: "ask"
  dangerous_patterns: ["rm -rf", "sudo"]  # deny 列表
```

### 三者对比

| 特性 | Gemini CLI | Qwen Code | Kimi CLI |
|------|-----------|-----------|----------|
| **格式** | TOML 策略文件 | JSON 设置 | TOML 配置 |
| **通配符** | ✓（`*`, `server__*`） | ✗ | ✗ |
| **正则匹配** | ✓ | 模式匹配 | 模式匹配 |
| **外挂安全检查** | ✓（进程级） | ✗ | ✗ |
| **Shell 分析** | 递归验证 + 重定向检测 | 虚拟操作提取 | AST 解析 |
| **持久/会话分离** | ✗ | ✓ | ✓ |
| **审批模式** | DEFAULT/AUTO_EDIT/YOLO | 分离管理 | yolo_mode 布尔 |
| **工具注解** | ✓（元数据规则） | ✗ | ✗ |
| **Hook 集成** | ✓（HookCheckerRule） | 通过 Hook 系统 | ✗ |

**设计哲学差异**：
- Gemini：**策略引擎**——复杂、可插拔、企业级
- Qwen：**权限管理器**——简化、配置驱动、兼容 Legacy
- Kimi：**规则配置**——直觉式、最简单

---

## 4. LLM 提供商抽象

### Gemini CLI：单提供商，深度集成

```typescript
// ContentGenerator 接口
interface ContentGenerator {
  generateContent(request): Promise<Response>
  generateContentStream(request): AsyncGenerator<Response>
  countTokens(request): Promise<TokenCount>
  embedContent(request): Promise<EmbedResult>
  userTier, paidTier  // 用户层级追踪
}

// 唯一实现: @google/genai SDK
// AuthType: LOGIN_WITH_GOOGLE | USE_GEMINI | USE_VERTEX_AI | COMPUTE_ADC
```

### Qwen Code：多提供商，扩展配置

```typescript
// ContentGenerator 接口（扩展）
interface ContentGenerator {
  // 继承 Gemini 所有方法
  useSummarizedThinking(): boolean  // 新增: 思维链摘要
  // 移除: userTier 字段
}

// 5 种实现:
// - GeminiContentGenerator (Google)
// - OpenAiContentGenerator (DashScope, OpenAI 兼容)
// - AnthropicContentGenerator (Claude)
// + Qwen OAuth (浏览器认证, 1000 次/天)
// + Vertex AI

// 扩展配置:
ContentGeneratorConfig {
  timeout, maxRetries, retryErrorCodes,
  enableCacheControl,                    // DashScope 缓存
  samplingParams: { top_p, top_k, penalties, temperature, max_tokens },
  reasoning: { effort },                 // 推理强度
  schemaCompliance,                      // OpenAPI 3.0
  modalities: [image, pdf, audio, video], // 多模态
  extra_body                             // 自定义参数
}
```

### Kimi CLI：Python 工厂模式

```python
# src/kimi_cli/llm.py
def create_llm(provider: str, model: str, config: Config) -> LLM:
    match provider:
        case "kimi":      return KimiLLM(...)       # Moonshot API
        case "openai":    return OpenAILLM(...)      # OpenAI
        case "anthropic": return AnthropicLLM(...)   # Claude
        case "google":    return GoogleLLM(...)      # Gemini
        case "_echo":     return EchoLLM(...)        # 测试
```

### 提供商支持矩阵

| 提供商 | Gemini CLI | Qwen Code | Kimi CLI |
|--------|-----------|-----------|----------|
| Google Gemini | ✓（原生） | ✓（继承） | ✓ |
| Vertex AI | ✓（原生） | ✓（继承） | ✗ |
| OpenAI/DashScope | ✗ | ✓（新增） | ✓ |
| Anthropic | ✗ | ✓（新增） | ✓ |
| Qwen OAuth（免费） | ✗ | ✓（新增） | ✗ |
| Kimi/Moonshot | ✗ | ✗ | ✓（原生） |
| 本地模型 | ✗ | ✗ | ✗ |
| **总计** | **2** | **5** | **4** |

---

## 5. 配置系统

| 维度 | Gemini CLI | Qwen Code | Kimi CLI |
|------|-----------|-----------|----------|
| **格式** | TOML（设置 + 策略） | JSON（settings.json） | TOML（config.toml） |
| **项目级** | `.gemini/` | `.qwen/` | 无 |
| **全局** | `~/.gemini/` | `~/.qwen/` | `~/.config/kimi-cli/` |
| **自定义提示** | `GEMINI.md` | `system.md` | 代理 TOML |
| **技能** | `.gemini/skills/` | `.qwen/skills/` | `.agents/skills/` |
| **会话存储** | `.gemini/sessions/` | `.qwen/tmp/<hash>/chats/` | Wire 格式文件 |
| **类型校验** | 运行时 | Zod + 运行时 | Pydantic 2 |
| **热重载** | 部分 | 部分 | ✗ |

---

## 6. 独有特性对比

### 仅 Gemini CLI 有

| 特性 | 说明 |
|------|------|
| **TOML 策略引擎** | 企业级策略文件，通配符 + 正则 + 安全检查器 |
| **外挂安全检查器** | 可加载外部进程做安全验证，5 秒超时 |
| **工具尾调用** | `tailToolCallRequest` 链式工具执行 |
| **并发请求队列** | 批量调度并行工具调用 |
| **工具注解规则** | 基于元数据的策略匹配 |
| **A2A 协议** | 实验性 Agent-to-Agent 通信 |
| **用户层级追踪** | `userTier`, `paidTier` 字段 |
| **模型路由器** | Fallback/Override/Classifier 等可插拔路由策略 |

### 仅 Qwen Code 有

| 特性 | 说明 |
|------|------|
| **免费 OAuth** | 通义账号每天 1000 次免费 |
| **6+ 提供商支持** | OpenAI + Anthropic + Gemini + Vertex + Qwen OAuth |
| **Arena 模式** | 多代理竞争/协作框架 |
| **子代理管理** | 委托工作给专用子代理 |
| **6 语言 UI** | 中/英/日/德/俄/葡 |
| **MessageBus Hook** | 事件驱动的 Hook 系统 |
| **Session Token 限制** | 硬性 Token 预算 |
| **交互式编辑** | `modifyWithEditor()` 中间编辑 |
| **配置源追踪** | 调试每个配置值的来源 |
| **多模态输入** | image/pdf/audio/video 声明 |
| **Claude/Gemini 扩展转换** | 可转换其他工具的扩展格式 |

### 仅 Kimi CLI 有

| 特性 | 说明 |
|------|------|
| **双模式交互** | Agent ↔ Shell（Ctrl-X），Wire 协议保持上下文 |
| **Wire 协议** | 统一多客户端通信（TUI/Web/IDE/IPC） |
| **ACP 协议** | Agent Client Protocol，IDE 原生集成 |
| **Moonshot 服务** | 原生 Search 和 Fetch API |
| **扩展思维模式** | `thinking_mode = "enabled"` 深度推理 |
| **后台任务** | 异步长时间运行 + 心跳检测 |
| **Python 生态** | Pydantic 类型安全 + FastAPI 服务器 |
| **Zsh 插件** | 终端无缝集成 |

---

## 7. 代码分叉分析：Qwen Code 改了什么

通过对比同名文件，Qwen Code 在 Gemini CLI 基础上的改动可归纳为：

### 核心引擎改动

| 文件 | Gemini CLI | Qwen Code 改动 |
|------|-----------|----------------|
| `client.ts` | 纯 Gemini 代理循环 | +SendMessageType 枚举, +Arena 集成, +子代理, +Token 限制, +MessageBus Hook |
| `contentGenerator.ts` | 单提供商接口 | +6+ 提供商, +采样参数, +模态声明, +配置源追踪, +summarizedThinking |
| `scheduler.ts` → `coreToolScheduler.ts` | 事件驱动状态机 | 简化为 Hook 驱动, +交互式编辑, +Levenshtein 匹配, +截断检测 |
| `policy-engine.ts` → `permission-manager.ts` | TOML 策略引擎 | 简化为配置驱动, +持久/会话规则分离, +虚拟操作提取, +Legacy 兼容 |

### 新增模块

| 模块 | 说明 |
|------|------|
| `i18n/` | 6 语言国际化 |
| `agents/arena/` | 多代理 Arena 框架 |
| `agents/backends/` | Tmux/iTerm2/进程内 后端 |
| `subagents/` | 子代理配置和管理 |
| `extensions/` | 扩展系统 + 格式转换 |

### 保留不变

| 模块 | 说明 |
|------|------|
| Ink + React UI 框架 | 终端渲染 |
| MCP 集成 | 协议层 |
| 基本工具定义模式 | DeclarativeTool 抽象 |
| 会话管理基础 | Session ID + 历史 |

---

## 8. 适用场景总结

| 场景 | 最佳选择 | 原因 |
|------|---------|------|
| **Google 生态** | Gemini CLI | 原生集成，策略引擎最强 |
| **多模型切换** | Qwen Code | 6+ 提供商 + 免费 OAuth |
| **中文开发** | Qwen Code / Kimi CLI | 国际化 / Moonshot 优化 |
| **双模式终端** | Kimi CLI | Ctrl-X 无缝 Agent↔Shell |
| **企业安全** | Gemini CLI | TOML 策略 + 外挂安全检查 |
| **免费使用** | Qwen Code | 每天 1000 次免费 |
| **IDE 集成** | Kimi CLI | ACP 协议原生 |
| **多代理** | Qwen Code | Arena + 子代理 + Tmux |
| **Python 生态** | Kimi CLI | Pydantic + FastAPI |
| **CI/CD** | Gemini CLI | 最成熟的策略框架 |

---

*分析基于本地源码仓库，截至 2026 年 3 月。*
