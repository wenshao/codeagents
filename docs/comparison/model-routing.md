# 26. 模型路由与自动选择：跨 Agent 深度对比

> 模型路由是 AI 编程代理的核心基础设施——决定每次请求使用哪个模型。从"用户手动切换"到"ML 分类器自动路由"，各工具的实现跨度极大。

## 总览

| Agent | 模型槽位 | 路由方式 | 自动 Fallback | 多提供商 | 复杂度 |
|------|---------|---------|-------------|---------|--------|
| **Gemini CLI** | 1（内部多策略） | **8 策略类自动路由** | ✓（FallbackStrategy） | ✗（仅 Google） | ★★★★★ |
| **Aider** | **3**（主/编辑/弱） | 配置文件 `model-settings.yml` | ✗（手动切换） | ✓（100+ 通过 LiteLLM） | ★★★★☆ |
| **Copilot CLI** | 1 | 手动 `/model` + 配额倍率 | ✗ | ✓（14 模型） | ★★★☆☆ |
| **Claude Code** | 1 | 手动 `/model` + `--fallback-model` | 部分（仅 `--print` 模式） | ✗（仅 Anthropic） | ★★☆☆☆ |
| **Qwen Code** | 1 | 手动 `/model` + 提供商前缀 | ✗ | ✓（6+ 提供商） | ★★☆☆☆ |
| **Kimi CLI** | 1 + thinking 开关 | 手动 `/model` | ✗ | ✓（5+ 提供商） | ★★☆☆☆ |
| **Codex CLI** | 1 | 手动 `/model` + `--oss` 本地 | ✗ | ✓（GPT-5 + 本地） | ★★☆☆☆ |
| **Goose** | 配置驱动 | 模型注册表 | 部分（需手动切换） | ✓（58+ 提供商） | ★★★☆☆ |

---

## 一、Gemini CLI：8 策略类自动路由（最复杂）

> 源码：`packages/core/src/routing/`

### 路由架构

```
用户请求
  │
  ├── OverrideStrategy ──→ 用户/系统显式指定模型？→ 使用指定模型
  │
  ├── FallbackStrategy ──→ 主模型失败？→ 自动切换备用模型
  │
  ├── ApprovalModeStrategy ──→ 当前审批模式影响模型选择
  │                            （Plan 模式 → 可能用 Pro 推理）
  │                            （YOLO 模式 → 可能用 Flash 加速）
  │
  ├── ClassifierStrategy ──→ 通用分类器评估任务复杂度
  │
  ├── GemmaClassifierStrategy ──→ Gemma ML 模型推理分类
  │                               （轻量级，专用于路由决策）
  │
  ├── NumericalClassifierStrategy ──→ 纯算法评分
  │     │  评分因素：输入 token 数、工具数量、
  │     │  交互轮次、是否需要代码生成
  │     └──→ 超过阈值 → Pro；低于阈值 → Flash
  │
  ├── CompositeStrategy ──→ 组合多策略链式决策
  │
  └── DefaultStrategy ──→ 最终默认选择
```

### 路由决策结构

```typescript
interface RoutingDecision {
  model: string;           // 选中的模型 ID
  metadata: {
    source: string;        // 决策来源（哪个策略）
    latencyMs: number;     // 路由决策耗时
    reasoning: string;     // 选择原因（可解释）
    error?: string;        // 可选错误信息
  };
}
```

### Flash vs Pro 自动路由

| 条件 | 选择模型 | 场景 |
|------|---------|------|
| 简单/快速任务 | Gemini Flash | 代码阅读、记忆管理、快速分析 |
| 复杂任务 | Gemini Pro | 代码生成、架构设计、复杂推理 |
| 用户显式指定 | 用户选择 | `/model set gemini-3-pro` |
| 子代理默认 | Flash | codebase_investigator、memory_manager 等 |

### 子代理模型分配

| 子代理 | 默认模型 | 回退模型 |
|--------|---------|---------|
| generalist | 继承主模型 | — |
| codebase_investigator | gemini-3-flash-preview | gemini-2.5-pro |
| memory_manager | gemini-3-flash-preview | — |
| cli_help | gemini-3-flash-preview | — |
| browser | gemini-3-flash-preview | gemini-2.5-flash |

### 两种分类器对比

| 维度 | GemmaClassifier（ML） | NumericalClassifier（算法） |
|------|----------------------|---------------------------|
| 推理方式 | ML 模型推理 | 纯数值评分 |
| 速度 | 较慢（需推理） | 快速（纯计算） |
| 准确性 | 更高（语义理解） | 中等（启发式规则） |
| 可解释性 | 较低 | **高**（分数可追溯） |
| 依赖 | 需加载 Gemma 模型 | 无外部依赖 |

> **设计理念：** 用低成本的路由决策（Gemma Flash 推理或纯算法评分）来节省高成本的 Pro 调用。路由本身的开销远小于选错模型的代价。

---

## 二、Aider：三槽位模型架构（最灵活的手动路由）

> 源码：`aider/coders/base_coder.py`、`aider/models.py`

### 三槽位设计

```
用户任务
  │
  ├── [主模型] ──→ 代码理解 + 推理 + 生成方案
  │     配置: /model claude-sonnet-4
  │
  ├── [编辑器模型] ──→ 根据方案执行代码修改（diff 生成）
  │     配置: /editor-model claude-haiku-4.5
  │     特点: map_tokens=0（不重复加载仓库地图）
  │
  └── [弱模型] ──→ 提交消息、历史摘要、lint 修复
        配置: /weak-model gpt-4o-mini
        特点: 低成本操作，不需要强推理
```

### 模型配置映射（`model-settings.yml`）

```yaml
# 每个模型有最优配置
- name: claude-sonnet-4
  edit_format: diff           # 最适合的编辑格式
  weak_model: claude-haiku-4.5
  use_repo_map: true
  send_undo_reply: true

- name: gpt-4o
  edit_format: udiff
  weak_model: gpt-4o-mini
  use_repo_map: true

- name: deepseek/deepseek-chat
  edit_format: diff
  weak_model: deepseek/deepseek-chat
  use_repo_map: true
```

### Architect 模式的双模型流水线

```
用户请求 → [架构师模型（主模型）] → 生成实现方案（自然语言）
                    ↓
             [编辑器模型] → 根据方案修改代码（diff）
```

- `ArchitectCoder` 继承自 `AskCoder`（只读，不直接编辑）
- `reply_completed()` 时将输出传给编辑器模型
- 编辑器 Coder 创建时 `map_tokens=0`（不重复加载仓库地图）

### 为什么三槽位？

| 操作 | 需要的能力 | 最优模型 | 成本 |
|------|-----------|---------|------|
| 代码理解/推理 | 强推理 | Opus/Sonnet | 高 |
| 应用代码修改 | 格式遵循 | Haiku/Flash | 低 |
| 提交消息 | 文本摘要 | Mini/Haiku | 极低 |
| 历史压缩 | 摘要能力 | Mini/Flash | 极低 |

> **设计理念：** 不同任务用不同强度的模型——强模型思考，弱模型执行，最弱模型做杂活。成本可降低 ~60-80%（基于模型定价差异估算）。

---

## 三、Claude Code：单模型 + 有限 Fallback

> 来源：`claude --help` v2.1.83、二进制分析

### 模型选择

```bash
# 交互式切换
/model                    # 选择 Sonnet 4.6 / Opus 4.6 / Haiku 4.5

# CLI 参数
claude --model opus       # 指定模型别名
claude --model claude-sonnet-4-6  # 完整模型 ID
```

### Fallback 机制

```bash
# 仅在 --print（非交互）模式下有效
claude -p "fix the bug" --fallback-model haiku

# 当默认模型过载时，自动切换到 fallback 模型
```

- **触发条件**：默认模型 API 过载（overloaded）
- **遥测事件**：`tengu_api_opus_fallback_triggered`
- **限制**：仅 `--print` 模式，交互模式无自动 Fallback
- **锁定生态**：仅 Anthropic 模型，无法切换到 OpenAI/Google

### 内部模型路由

Claude Code 的 Skill 系统有隐式模型选择：
- `/review` 插件：Haiku（前置检查）→ Sonnet（变更摘要/合规审计）→ Opus（Bug 扫描/安全分析）
- 子代理（Agent 工具）：可指定 `model: "haiku"` 或 `"sonnet"` 或 `"opus"`
- 但这是**插件级别的硬编码**，非通用路由系统

---

## 四、Copilot CLI：多提供商 + 配额路由

> 来源：官方文档、二进制分析

### 模型选择

```bash
/model                    # 交互式选择
# 可用模型（14 个）：
# Claude: Sonnet 4, Haiku 3.5
# GPT: 4.1（免费）, 4.1-mini, gpt-5-mini（免费）, o3, o4-mini
# Gemini: 2.5 Pro, 2.5 Flash
```

### 配额倍率系统

> 来源：[GitHub Copilot 官方文档](https://docs.github.com/en/copilot)，倍率因版本/计划而异。

| 模型 | 配额倍率 | 说明 |
|------|---------|------|
| GPT-4.1 | ~1x | 基准（部分计划免费） |
| GPT-4.1-mini | ~0.25x | 低成本 |
| o3 | ~1.5x | 高推理 |
| Gemini 2.5 Pro | ~0.5x | 中等 |
| Claude Sonnet 4 | ~1x | 基准 |
| Claude Opus 4.5 | ~3x | 高倍率 |

> **隐式路由：** 虽然无自动 Fallback，但配额系统引导用户选择性价比最优的模型。

---

## 五、Qwen Code：多提供商前缀路由（无自动 Fallback）

> 来源：Qwen Code 开源代码

### 提供商前缀语法

```bash
/model dashscope/qwen3-coder      # DashScope
/model modelscope/qwen3           # ModelScope
/model anthropic/claude-sonnet-4  # Anthropic
/model google/gemini-2.5-pro      # Google
/model openai-compatible/custom   # 自定义端点
```

### 缺失：无模型路由器

作为 Gemini CLI 分叉，Qwen Code **没有移植上游的 ModelRouterService**。影响：
- API 错误/配额耗尽时直接失败（无自动 Fallback）
- 所有模型选择都是手动的
- 无法根据任务复杂度自动选择轻量/重量模型

> 已识别为 **P1 优先级** 功能缺口（见 [Qwen Code vs Gemini CLI 功能差距](./qwen-code-vs-gemini-feature-gaps.md#1-模型路由器8-种策略类--7-种用户策略)）。

---

## 六、Kimi CLI：单模型 + Thinking 模式

> 源码：`soul/slash.py`、`config.py`

```bash
/model kimi-k2.5            # 切换模型
/model --thinking            # 开启深度推理显示
/model --no-thinking         # 关闭推理显示
```

- 模型切换触发 `Reload` 异常（重新初始化 Shell 上下文）
- 支持 5+ 提供商：Kimi（默认）、OpenAI、Anthropic、Google Gemini、Vertex AI
- **无自动路由**：完全手动选择

---

## 七、Codex CLI：云端 + 本地双轨

> 来源：`codex --help`、官方文档

```bash
# 云端模型
codex --model gpt-5.2-codex

# 本地模型（通过 Ollama/vLLM）
codex --oss --model qwen3:32b
```

- **双轨架构**：云端（GPT-5 系列）或本地（`--oss` 标志）
- **事件系统**：`model/rerouted` 事件存在但未公开文档
- **无自动路由**：手动选择

---

## 八、Goose：注册表驱动 + 快速 Fallback

> 来源：[Goose 文档](https://block.github.io/goose/docs/)、开源代码

```yaml
# ~/.config/goose/config.yaml
provider: anthropic
model: claude-sonnet-4
```

```bash
goose --model claude-opus-4     # 启动时指定
```

- **58+ 提供商**：通过模型注册表支持（Anthropic、OpenAI、Google、AWS、Azure、Groq 等）
- **无自动 Fallback**：模型不可用时需手动修改配置切换（注册表支持快速查找替代）
- **无斜杠命令 `/model`**：通过配置文件或启动参数选择
- **MCP 驱动**：模型能力可从扩展推断

---

## 设计模式对比

### 模式 1：自动路由 vs 手动选择

| 方案 | 代表 | 优势 | 劣势 |
|------|------|------|------|
| **ML 分类器自动路由** | Gemini CLI | 零用户干预，成本最优 | 复杂，路由决策本身有延迟 |
| **三槽位手动分配** | Aider | 最大灵活性，用户完全控制 | 需要用户理解模型特性 |
| **单模型 + Fallback** | Claude Code | 简单可靠 | 无成本优化 |
| **注册表 + 手动切换** | Goose | 提供商最多 | 无智能路由，无自动 Fallback |

### 模式 2：成本优化策略

| 策略 | 工具 | 实现 | 节省比例 |
|------|------|------|---------|
| **任务分类路由** | Gemini CLI | Flash(简单) / Pro(复杂) | ~50-70%（估算） |
| **三槽位分离** | Aider | 主(强) / 编辑(中) / 弱(低) | ~60-80%（估算） |
| **配额倍率引导** | Copilot CLI | 低倍率模型更"便宜" | 用户自选 |
| **子代理模型指定** | Claude Code | Haiku(前置) → Sonnet(主) → Opus(核心) | ~40-60%（估算） |

### 模式 3：容错与可用性

| Agent | Fallback 方式 | 触发条件 | 用户感知 |
|------|-------------|---------|---------|
| **Gemini CLI** | FallbackStrategy 自动 | API 错误/超时 | 透明（日志记录决策来源） |
| **Claude Code** | `--fallback-model` | 模型过载 | 仅 `--print` 模式 |
| **Goose** | 手动切换配置 | 模型不可用 | 需修改配置 |
| **其他** | 无 | — | 直接报错 |

---

## 未来趋势

1. **更多工具将引入自动路由** — Gemini CLI 证明了 ML 分类器路由的可行性，其他工具（尤其多提供商工具如 Qwen Code、Kimi CLI）有强烈动机实现类似功能
2. **成本优化将成为核心竞争力** — Aider 的三槽位设计表明，合理的模型分配可节省 60-80% 成本
3. **Fallback 将成为标配** — 随着 AI 编程代理用于生产环境，API 容错能力不再是可选项
4. **路由决策可解释性** — Gemini CLI 的 `reasoning` 字段是正确方向，用户需要理解为什么选了某个模型

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Gemini CLI 路由 | `packages/core/src/routing/*.ts` | GitHub 源码 |
| Aider 三槽位 | `aider/models.py` + `aider/coders/architect_coder.py` | GitHub 源码 |
| Claude Code Fallback | `claude --help` v2.1.83 + 二进制 strings | 本地二进制 |
| Copilot CLI 配额 | 官方文档 + 二进制分析 | 官方文档 + SEA 反编译 |
| Qwen Code 提供商 | `packages/core/src/providers/` | GitHub 源码 |
| Kimi CLI 模型 | `src/kimi_cli/soul/slash.py` | GitHub 源码 |
| Codex CLI 双轨 | `codex --help` + 官方文档 | 本地二进制 + 官方文档 |
| Goose 注册表 | [官方文档](https://block.github.io/goose/docs/) | 官方文档 |
