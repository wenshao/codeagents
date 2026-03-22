# Qwen Code 功能补全建议：对标上游 Gemini CLI

> Qwen Code 是 Gemini CLI 的分叉。本文识别分叉后未移植或上游新增的功能。

## 功能全景对比

| 功能 | Gemini CLI（上游） | Qwen Code（分叉） | 状态 |
|------|-------------------|-------------------|------|
| **核心代理循环** | ✅ | ✅ | 对等 |
| 工具系统（声明式） | ✅ | ✅ | 对等 |
| 事件驱动调度器 | ✅ Scheduler | ✅ CoreToolScheduler | 对等（实现不同） |
| Hook 系统 | ✅ | ✅ 12 事件 | 对等 |
| MCP 集成 | ✅ Stdio/SSE/HTTP | ✅ Stdio/SSE | Qwen 少 HTTP |
| 会话管理 | ✅ | ✅ + 录制 | 对等 |
| Ink + React TUI | ✅ | ✅ | 对等 |
| 审批模式（4 种） | ✅ DEFAULT/AUTO_EDIT/YOLO/PLAN | ✅ 同 4 种 | 对等 |
| Memory 工具 | ✅ 仅项目级 | ✅ 全局 + 项目级 | **Qwen 更强** |
| 多提供商 | ❌ 仅 Gemini | ✅ 5 提供商 | **Qwen 独有** |
| 免费 OAuth | ❌ | ✅ 1000 次/天 | **Qwen 独有** |
| 6 语言 UI | ❌ | ✅ | **Qwen 独有** |
| Arena 多代理 | ❌ | ✅ | **Qwen 独有** |
| 子代理管理 | ❌ | ✅ | **Qwen 独有** |
| 扩展格式转换 | ❌ | ✅ Claude/Gemini | **Qwen 独有** |
| **模型路由器** | ✅ 8 种路由策略 | ❌ | **需补全** |
| **外挂安全检查器** | ✅ CheckerRunner | ❌ | **需补全** |
| **TOML 策略文件** | ✅ 6 个预定义策略 | ❌ | **需补全** |
| **A2A 协议服务器** | ✅ | ❌ | **需补全** |
| **工具链式调用** | ✅ TailToolCall | ❌ | **需补全** |
| **模型粘性** | ✅ currentSequenceModel | ❌ | **需补全** |
| **录制回放调试** | ✅ RecordingContentGenerator | ❌ | **需补全** |
| **Code Assist 服务器** | ✅ 企业级 | ❌ | **需补全** |
| **CONSECA 策略系统** | ✅ | ❌ | **需补全** |
| 请求队列批量调度 | ✅ 高级 | ✅ 基础 | Qwen 较简单 |

---

## 一、高优先级（核心能力差距）

### 1. 模型路由器（8 种策略）

**Gemini CLI 实现**（`packages/core/src/routing/`）：
- `modelRouterService.ts`：完整的模型路由服务
- **8 种可插拔路由策略**：
  - `fallbackStrategy.ts` — 主模型失败自动切换备用
  - `overrideStrategy.ts` — 强制覆盖模型选择
  - `approvalModeStrategy.ts` — 按审批模式选择模型
  - `classifierStrategy.ts` — 通用分类器路由
  - `gemmaClassifierStrategy.ts` — ML 模型分类路由
  - `numericalClassifierStrategy.ts` — 数值分类路由
  - `compositeStrategy.ts` — 组合策略
  - `defaultStrategy.ts` — 默认回退

**Qwen Code 缺失影响**：无法自动 fallback 到备用模型，API 错误/配额耗尽时直接失败。

**建议实现**：优先实现 `FallbackStrategy`（最高 ROI）：
```typescript
// packages/core/src/routing/fallbackStrategy.ts
class FallbackRouter {
  private models: string[];  // 按优先级排列

  async selectModel(request): Promise<string> {
    for (const model of this.models) {
      if (await this.isAvailable(model)) return model;
    }
    throw new Error('All models unavailable');
  }
}
```

**工作量**：中（3-5 天实现 Fallback，完整 8 策略需 2-3 周）

---

### 2. 工具链式调用（Tail Tool Calls）

**Gemini CLI 实现**（`scheduler.ts:676-707`）：
- `TailToolCallRequest` 接口
- 工具执行后可直接触发下一个工具，无需模型介入
- 减少 LLM 轮次，加速多步操作

**Qwen Code 缺失影响**：每个工具调用都需要模型决策，多步操作（如"读文件→编辑→测试"）多耗 2-3 轮 LLM 调用。

**建议实现**：
```typescript
// 工具执行结果中可包含下一步调用请求：
interface ToolResult {
  llmContent: PartListUnion;
  tailToolCallRequest?: {
    toolName: string;
    params: Record<string, unknown>;
  };
}
```

**工作量**：中（2-3 天）

---

### 3. 模型粘性（Model Stickiness）

**Gemini CLI 实现**（`client.ts:91`）：
- `private currentSequenceModel: string | null = null`
- 一次对话序列中保持使用同一模型
- 避免多轮对话中模型切换导致的上下文不一致

**Qwen Code 缺失影响**：多提供商场景下，连续轮次可能切换模型，导致风格/能力不一致。

**工作量**：极低（半天），加一个实例变量

---

## 二、中优先级（安全与调试）

### 4. 外挂安全检查器（Safety Checkers）

**Gemini CLI 实现**（`packages/core/src/safety/`）：
- `checker-runner.ts`：外部进程安全检查执行器
- 支持超时控制
- `protocol.ts`：IPC 通信协议
- `registry.ts`：检查器注册表
- **CONSECA 策略系统**：`conseca/policy-enforcer.ts` + `policy-generator.ts`

**Qwen Code 缺失影响**：无法加载第三方安全检查器，安全审计能力有限。

**工作量**：高（1-2 周）

---

### 5. TOML 策略文件

**Gemini CLI 实现**（`packages/core/src/policy/`）：
- `toml-loader.ts`：TOML 文件解析
- **6 个预定义策略文件**：
  - `read-only.toml` — 只读模式
  - `write.toml` — 写入权限
  - `yolo.toml` — 全自动模式
  - `plan.toml` — 规划模式
  - `discovered.toml` — 发现的工具
  - `conseca.toml` — CONSECA 策略
- `integrity.ts`：策略完整性校验

**Qwen Code 现状**：使用 JSON settings 的 permission 规则（`deny > ask > allow`），功能等价但格式不同。

**评估**：TOML 策略更适合团队共享和版本控制（可读性好），但 Qwen 的 JSON 规则也能工作。**非阻塞性缺口**，可按需补全。

**工作量**：中（3-5 天）

---

### 6. 录制回放调试（RecordingContentGenerator）

**Gemini CLI 实现**（`core/recordingContentGenerator.ts`）：
- 记录 LLM 响应，供后续调试和回放
- `--fake-responses` CLI 标志激活
- 捕获"有趣"的响应片段

**Qwen Code 缺失影响**：无法离线重放对话调试，排查问题需要重新执行。

**工作量**：中（2-3 天）

---

## 三、低优先级（企业/实验性）

### 7. A2A 协议服务器

**Gemini CLI 实现**（`packages/a2a-server/`）：
- 完整的 Agent-to-Agent 通信服务器
- 基于 `@a2a-js/sdk`
- Express.js HTTP 实现
- 支持分层记忆和扩展加载

**评估**：A2A 是实验性协议，生态尚不成熟。Qwen Code 有 Arena 和子代理作为替代方案。

**工作量**：高（2-3 周）

---

### 8. Code Assist 服务器（企业）

**Gemini CLI 实现**（`packages/core/src/code_assist/`）：
- OAuth2 认证 + 用户层级（UserTierId）
- 管理员控制 + 实验特性
- 企业级代码辅助服务

**评估**：面向 Google Cloud 企业客户，Qwen Code 有自己的阿里云集成路线。

**工作量**：高（3-4 周）

---

## 四、优先级矩阵

| 功能 | 工作量 | 用户价值 | 优先级 |
|------|--------|---------|--------|
| 模型粘性（currentSequenceModel） | 极低（半天） | **高**（多提供商一致性） | **P0** |
| 工具链式调用（Tail Tool Calls） | 中（2-3 天） | **高**（减少 LLM 轮次） | **P1** |
| 模型路由器（Fallback 优先） | 中（3-5 天） | **高**（API 容错） | **P1** |
| 录制回放调试 | 中（2-3 天） | 中（开发者体验） | **P1** |
| TOML 策略文件 | 中（3-5 天） | 中（团队共享） | P2 |
| 外挂安全检查器 | 高（1-2 周） | 中（企业安全） | P2 |
| A2A 协议服务器 | 高（2-3 周） | 低（实验性） | P3 |
| Code Assist 服务器 | 高（3-4 周） | 低（Google 专属） | P3 |
| CONSECA 策略系统 | 高（1-2 周） | 低（Google 专属） | P3 |

---

## 五、Qwen Code 的分叉增强（无需对标）

| 功能 | Qwen Code 增强 | Gemini CLI 缺失 |
|------|---------------|----------------|
| **多提供商** | OpenAI + Anthropic + Gemini + Vertex + Qwen OAuth | 仅 Gemini |
| **免费 OAuth** | 每天 1000 次 | 无 |
| **6 语言 UI** | 中/英/日/德/俄/葡 | 仅英文 |
| **Arena 模式** | 多模型并行竞争 | 无 |
| **子代理管理** | SubagentManager + 多终端后端 | 无 |
| **扩展格式转换** | Claude/Gemini 扩展自动转换 | 无 |
| **Memory 双作用域** | 全局 `~/.qwen/QWEN.md` + 项目级 | 仅项目级 |
| **Session Token 限制** | 硬性 Token 预算 | 无 |
| **MessageBus Hook** | 事件驱动 Hook | 回调式 Hook |

---

## 六、一句话总结

**1 个半天可完成的 P0**：模型粘性（多提供商场景下保持连续轮次使用同一模型）

**3 个需要投入的 P1**：工具链式调用 + 模型路由器（Fallback）+ 录制回放调试

**Qwen Code 作为分叉已大幅超越上游**——多提供商、免费 OAuth、Arena、6 语言 UI 是独有竞争力。上游的模型路由器和安全检查器值得借鉴，但 A2A 和 Code Assist 是 Google 专属功能，无需复制。

---

*分析基于 Gemini CLI 和 Qwen Code 本地源码，截至 2026 年 3 月。*
