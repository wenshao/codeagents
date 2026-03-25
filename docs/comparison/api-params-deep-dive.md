# 40. API 参数与重试策略深度对比

> API 参数配置直接影响代码生成质量、成本和可靠性。从 temperature=0 的确定性输出到 7 种生成配置，各工具的 LLM 调用策略差异显著。

## 总览

| 工具 | 默认温度 | 重试策略 | 循环上限 | 流式输出 | LLM SDK | Prompt 缓存 |
|------|---------|---------|---------|---------|---------|-----------|
| **Claude Code** | 0/1（模式相关） | 指数退避 | 可配置 maxTurns | ✓ | 原生 Anthropic | **✓ cache_control** |
| **Gemini CLI** | 0(base)/1(chat) | 10 次，5-30s | **100 轮** | ✓ | @google/genai | ✓ cachedContent |
| **Aider** | **0** | 0.125s→60s | 3 次反射 | ✓（默认） | **LiteLLM** | ✓ Anthropic 缓存 |
| **Kimi CLI** | 环境变量控制 | tenacity 0.3-5s×3 | **100 步/轮** | ✓ | kosong（自研） | ✗ |
| **Goose** | None（环境变量） | 可配置 RetryManager | 无固定上限 | Provider 决定 | **Provider trait** | ✗ |
| **Codex CLI** | 可配置 | — | 可配置 | ✓ | 原生 OpenAI | ✓ 服务端 |
| **Copilot CLI** | 0/1（场景相关） | — | 可配置 | ✓ | 原生 GitHub | ✗ |
| **Qwen Code** | 继承 Gemini | 继承 Gemini | **100 轮** | ✓ | @google/genai | ✓（DashScope） |

---

## 一、温度策略

### 跨 Agent 温度对比

| 场景 | Claude Code | Gemini CLI | Aider | Kimi CLI |
|------|------------|-----------|-------|---------|
| **代码生成** | ~0 | 0（base） | **0** | 环境变量 |
| **对话交互** | ~1 | **1**（chat） | 0 | 环境变量 |
| **分类/安全** | 0 | 0（classifier） | — | — |
| **辅助任务** | — | 0.2-0.3 | — | — |
| **推理模型** | — | — | **禁用** | — |

### Gemini CLI 7 种生成配置（源码：`defaultModelConfigs.ts`）

| 配置 | temperature | topP | topK | thinkingConfig |
|------|-------------|------|------|----------------|
| `base` | **0** | 1 | — | — |
| `chat-base` | **1** | 0.95 | 64 | `includeThoughts: true` |
| `chat-base-2.5` | 继承 | 继承 | 继承 | `thinkingBudget: DEFAULT` |
| `chat-base-3` | 继承 | 继承 | 继承 | `thinkingLevel: HIGH` |
| `classifier` | 0 | 1 | — | `thinkingBudget: 512, maxOutputTokens: 1024` |
| `prompt-completion` | **0.3** | 继承 | — | `thinkingBudget: 0, maxOutputTokens: 16000` |
| `fast-ack-helper` | **0.2** | 继承 | — | `thinkingBudget: 0, maxOutputTokens: 120` |

### Aider 推理模型温度禁用

```python
# models.py — 以下模型自动禁用温度
use_temperature = False  # DeepSeek R1, o1/o3/o4, GPT-5

# Aider 实际 LLM 调用（models.py:1020）
response = litellm.completion(
    model=self.model_name,
    messages=messages,
    temperature=0 if self.use_temperature else None,
    stream=True,
    timeout=600,  # 10 分钟超时
    **extra_kwargs
)
```

### Claude Code API 调用示例（二进制提取）

```javascript
// Anthropic API 调用（cache_control 优化）
{
  model: "claude-sonnet-4-6",
  max_tokens: 16384,
  system: [
    { type: "text", text: systemPrompt, cache_control: { type: "ephemeral" } }
  ],
  tools: toolDefinitions.map(t => ({
    ...t, cache_control: { type: "ephemeral" }
  })),
  messages: conversationHistory
}
```

### Gemini CLI 生成配置（源码：`defaultModelConfigs.ts`）

```typescript
// chat-base 配置（对话模式默认）
{
  temperature: 1,
  topP: 0.95,
  topK: 64,
  generationConfig: {
    thinkingConfig: { includeThoughts: true }
  }
}

// classifier 配置（模型路由分类器）
{
  temperature: 0,
  topP: 1,
  generationConfig: {
    thinkingConfig: { thinkingBudget: 512 },
    maxOutputTokens: 1024
  }
}
```

---

## 二、重试策略

### 跨 Agent 重试对比

| 工具 | 初始延迟 | 最大延迟 | 最大次数 | 重试条件 | 抖动 |
|------|---------|---------|---------|---------|------|
| **Aider** | 0.125s | 60s | — | LiteLLM 可重试错误 | ✗ |
| **Gemini CLI** | **5s** | **30s** | **10** | 429 + 5xx | ✗ |
| **Kimi CLI** | 0.3s | 5s | 3/步 | 通用错误 | **✓（0.5）** |
| **Goose** | — | 300s（超时） | 用户配置 | — | ✗ |
| **Claude Code** | — | — | 指数退避 | API 错误 | ✗ |

### Kimi CLI tenacity 配置（源码：`kimisoul.py:687-691`）

```python
@retry(
    wait=wait_exponential_jitter(initial=0.3, max=5, jitter=0.5),
    stop=stop_after_attempt(3),
)
async def _step(self):
    ...
```

### Gemini CLI 重试条件（源码：`retry.ts:150`）

仅重试：
- **429** — 速率限制（Rate Limit Exceeded）
- **5xx** — 服务器错误（Internal Server Error）

不重试：4xx 客户端错误（除 429）。

---

## 三、代理循环控制

### 循环上限

| 工具 | 上限 | 源码位置 | 说明 |
|------|------|---------|------|
| **Gemini CLI** | **100 轮** | `client.ts:81` MAX_TURNS | 硬编码 |
| **Kimi CLI** | **100 步/轮** | `config.py:71-72` max_steps_per_turn | 可配置 |
| **Qwen Code** | **100 轮** | 继承 Gemini | 硬编码 |
| **Aider** | 3 次反射 | `base_coder.py:101` | lint/test 专用 |
| **Claude Code** | 可配置 | maxTurns（74 refs） | 动态 |
| **Goose** | 无固定上限 | — | 直到模型停止 |

### 停止条件

| 工具 | 停止方式 |
|------|---------|
| Claude Code | `end_turn` / `stop_sequence` / 用户中断 |
| Gemini CLI | 轮次耗尽 / 模型停止 / 用户中断 |
| Aider | 模型不再调用工具 / 3 次反射失败 |
| Kimi CLI | 步数耗尽 / `stop_reason` / 用户中断 |
| Goose | 模型决定 / 用户中断 |

---

## 四、上下文窗口与压缩阈值

| 工具 | 最大上下文 | 压缩阈值 | 预留空间 |
|------|-----------|---------|---------|
| **Claude Code** | 100 万 token（Opus 4.6[1m]） | ~95% | — |
| **Gemini CLI** | ~100 万 | **50%** | — |
| **Kimi CLI** | 模型依赖 | **85%** | **50K tokens** |
| **Goose** | 模型依赖 | **80%** | — |
| **Aider** | 模型依赖 | `done_messages > 1024 tokens` | — |
| **Qwen Code** | ~100 万 | 50%（继承） | — |

---

## 五、Prompt 缓存

| 工具 | 缓存机制 | 效果 |
|------|---------|------|
| **Claude Code** | Anthropic `cache_control: ephemeral` | 系统提示和工具定义缓存，减少重复 token |
| **Aider** | Anthropic prompt caching（通过 LiteLLM） | 后台保活 ping 维持缓存 |
| **Gemini CLI** | Google `cachedContent` API | 长上下文缓存 |
| **Codex CLI** | OpenAI 服务端缓存 | `enable_request_compression` |
| **Qwen Code** | DashScope 缓存（`enableCacheControl`） | 继承 |

---

## 六、工具调用策略

| 工具 | 并行调用 | 工具选择 | 特殊机制 |
|------|---------|---------|---------|
| **Claude Code** | ✓（Agent 子代理） | 模型自选 | ToolSearch 延迟加载 |
| **Gemini CLI** | ✓ | 模型自选 | TailToolCall 链式调用 |
| **Copilot CLI** | ✓（`multi_tool_use.parallel`） | 模型自选 | 模型特定 apply-patch |
| **Aider** | ✗（串行） | 编辑格式决定 | 14 种格式按模型选择 |
| **Kimi CLI** | ✗（串行+后台任务） | 模型自选 | max_steps_per_turn=100 |
| **Goose** | ✓ | 模型自选 | toolshim 兼容层 |

### Goose toolshim（独有）

```rust
pub struct ModelConfig {
    pub toolshim: bool,           // 为不支持工具调用的模型启用 shim
    pub toolshim_model: Option<String>,  // 代理工具调用的模型
}
```

对不支持原生工具调用的模型（如部分本地模型），Goose 通过 toolshim 用另一个模型代理工具调用决策。

---

## 七、Goose toolshim：无原生工具调用的模型兼容层

> 源码：`model.rs:48`

```rust
pub struct ModelConfig {
    pub toolshim: bool,              // 启用工具调用 shim
    pub toolshim_model: Option<String>, // 代理决策的模型
}
```

对不支持原生 function calling 的模型（如部分本地 Ollama 模型），Goose 通过 `toolshim` 用另一个模型代理工具调用决策。例如：主模型为 `llama3:8b`（无工具调用），`toolshim_model` 设为 `gpt-4o-mini`（代理工具选择）。

---

## 八、LLM SDK 生态

| SDK | 使用者 | 提供商覆盖 |
|-----|--------|-----------|
| **LiteLLM** | Aider, SWE-agent, OpenHands | 100+（统一 Python 接口） |
| **@google/genai** | Gemini CLI, Qwen Code | Google 模型 |
| **原生 Anthropic** | Claude Code | Anthropic 模型 |
| **原生 OpenAI** | Codex CLI | OpenAI 模型 |
| **Provider trait** | Goose（rmcp Rust） | 58+（Rust trait 抽象） |
| **Handler 工厂** | Cline | 48+（per-provider Handler） |
| **kosong** | Kimi CLI | 5+（自研 Python 抽象） |
| **Vercel AI SDK** | OpenCode | 100+（TypeScript） |

---

## 证据来源

| 工具 | 源码文件 | 获取方式 |
|------|---------|---------|
| Aider | `models.py:988`（temp）, `history.py`（压缩）| GitHub 源码 |
| Gemini CLI | `defaultModelConfigs.ts`, `retry.ts`, `client.ts:81` | GitHub 源码 |
| Kimi CLI | `config.py:71-85`, `kimisoul.py:687-691` | GitHub 源码 |
| Goose | `model.rs:48-158`, `context_mgmt/mod.rs` | GitHub 源码 |
| Claude Code | `claude --help` + 二进制分析 | 本地二进制 |
| Codex CLI | `codex --help` + config schema | 二进制 + 官方文档 |
