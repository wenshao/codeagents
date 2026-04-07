# 6. Provider 与模型动态加载——开发者参考

> OpenCode 通过 [models.dev](https://models.dev) API 动态加载 100+ LLM Provider，实现零代码接入新模型。这是目前 Code Agent 中 Provider 支持最广的实现——Qwen Code 需要手动配置每个 Provider，Claude Code 只支持 Claude 模型。
>
> **Qwen Code 对标**：Qwen Code 支持 10+ Provider（手动配置 baseUrl/apiKey）。OpenCode 的 models.dev 动态发现 + 构建时快照 + 5 分钟 TTL 缓存是主要参考。

## 一、为什么动态 Provider 加载有价值

| 方式 | 新 Provider 接入成本 | 模型信息更新 | 离线支持 |
|------|-------------------|------------|---------|
| 硬编码（Claude Code） | 改代码 + 发版 | 改代码 + 发版 | ✓ |
| 手动配置（Qwen Code） | 用户写 settings.json | 用户手动更新 | ✓ |
| **动态加载（OpenCode）** | **零成本**（自动发现） | **自动更新**（5 分钟 TTL） | ✓（构建时快照） |

## 二、实现架构

源码: `packages/opencode/src/provider/models.ts`

```
启动时
  │
  ├─ 1. 尝试加载内存缓存
  │
  ├─ 2. 缓存过期（>5 分钟）？
  │     ├─ 是 → fetch https://models.dev/api.json
  │     │        ├─ 成功 → 更新内存 + 磁盘缓存
  │     │        └─ 失败 → 回退到磁盘缓存
  │     └─ 否 → 使用内存缓存
  │
  ├─ 3. 磁盘缓存也不可用？
  │     └─ 回退到构建时快照（models-snapshot.js）
  │
  └─ 4. 后台每 60 分钟刷新
```

### 三层回退

| 层 | 数据源 | TTL | 用途 |
|---|--------|-----|------|
| 1 | 内存缓存 | 5 分钟 | 最快访问 |
| 2 | 磁盘缓存 `~/.cache/opencode/models.json` | 持久 | 网络不可用时 |
| 3 | 构建时快照 `models-snapshot.js` | 永久 | 完全离线 |

### 模型数据结构

```typescript
{
  id: "claude-sonnet-4-6",
  name: "Claude Sonnet 4.6",
  family: "claude",
  provider: "anthropic",
  cost: {
    input: 3,        // $/M tokens
    output: 15,
    cache_read: 0.3,
    cache_write: 3.75,
    context_over_200k: { input: 6, output: 30 }
  },
  limit: {
    context: 200000,
    input: 200000,
    output: 8192
  },
  modalities: {
    input: ["text", "image"],
    output: ["text"]
  },
  reasoning: true,
  tool_call: true,
  status: "stable"
}
```

### 20 个内置 Provider

Anthropic、OpenAI、Google（Generative AI + Vertex AI）、Amazon Bedrock、Azure、OpenRouter、Mistral、GitHub Copilot、GitLab、xAI、Groq、Cohere、DeepInfra、Cerebras、Together AI、Perplexity、Cloudflare（Workers AI + AI Gateway）、SAP AI Core、自定义 OpenAI 兼容。

## 三、Qwen Code 改进建议

### P2：接入 models.dev

Qwen Code 当前需要用户手动配置每个 Provider 的 baseUrl 和 apiKey。可以：
1. 接入 models.dev API 获取模型元数据（名称、定价、上下文窗口、能力）
2. 构建时生成快照供离线使用
3. 用户只需配置 apiKey，模型信息自动填充

### P3：Provider 自动发现

通过 `provider` Hook 允许插件动态注册新 Provider——不需要改核心代码。
