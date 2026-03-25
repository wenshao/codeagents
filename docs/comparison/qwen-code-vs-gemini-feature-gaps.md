# 24. Qwen Code 功能补全建议：对标上游 Gemini CLI

> Qwen Code 是 Gemini CLI 的分叉。本文识别分叉后未移植或上游新增的功能。

## 功能全景对比

| 功能 | Gemini CLI（上游） | Qwen Code（分叉） | 状态 |
|------|-------------------|-------------------|------|
| **核心代理循环** | ✅ | ✅ | 对等 |
| 工具系统（声明式） | ✅ | ✅ | 对等 |
| 事件驱动调度器 | ✅ Scheduler | ✅ CoreToolScheduler | 对等（实现不同） |
| Hook 系统 | ✅ 11 事件（BeforeTool/AfterTool 等） | ✅ 12 事件（PreToolUse/PostToolUse 等） | 近似对等（Qwen 多 1 个事件，事件命名不同） |
| MCP 集成 | ✅ Stdio/SSE/HTTP | ✅ Stdio/SSE/HTTP（`StreamableHTTPClientTransport`） | 对等 |
| 会话管理 | ✅ | ✅ + `chatRecordingService`（JSONL 持久化） | 对等 |
| Ink + React TUI | ✅ | ✅ | 对等 |
| 审批模式（4 种） | ✅ DEFAULT/AUTO_EDIT/YOLO/PLAN | ✅ 同 4 种 | 对等 |
| Memory 工具 | ✅ 全局 + 扩展 + 项目 + 子目录 | ✅ 继承同一多层体系 | 对等 |
| 多提供商 | ❌ 仅 Gemini | ✅ 6+ 提供商 | **Qwen 独有** |
| 免费 OAuth | ❌ | ✅ 1000 次/天 | **Qwen 独有** |
| 6 语言 UI | ❌ | ✅ | **Qwen 独有** |
| Arena 多代理 | ❌ | ✅ | **Qwen 独有** |
| 子代理管理 | ✅ 5 内置子代理 + /agents 命令（v0.12.0+） | ✅ SubagentManager + Arena 竞争模式 | 对等（Qwen 额外有 Arena） |
| 扩展格式转换 | ❌ | ✅ Claude/Gemini | **Qwen 独有** |
| **模型路由器** | ✅ 8 种路由策略类（7 种用户策略） | ❌ | **需补全** |
| **外挂安全检查器** | ✅ CheckerRunner | ❌ | **需补全** |
| **TOML 策略文件** | ✅ 9 个预定义策略 | ❌ | **需补全** |
| **A2A 协议服务器** | ✅ | ❌ | **需补全** |
| **工具链式调用** | ✅ TailToolCall | ❌ | **需补全** |
| **模型粘性** | ✅ currentSequenceModel | ❌ | **需补全** |
| **录制回放调试** | ✅ RecordingContentGenerator | ❌ | **需补全** |
| **Code Assist 服务器** | ✅ 企业级 | ❌ | **需补全** |
| **CONSECA 策略系统** | ✅ | ❌ | **需补全** |
| 请求队列批量调度 | ✅ 高级 | ✅ 基础 | Qwen 较简单 |

---

## 内置命令对比（Gemini CLI 39 vs Qwen Code 40）

> Qwen Code 继承了 Gemini CLI 大部分命令，同时新增了独有命令。以下对比关注差异。

### Gemini CLI 有而 Qwen Code 没有的命令

| Gemini CLI 命令 | 功能 | Qwen Code 对应 |
|----------------|------|----------------|
| `/rewind` | 回退到之前的对话状态（含影响分析 UI） | `/restore`（功能类似但无 /rewind） |
| `/policies` | 策略管理（list） | ❌ 无（Qwen 用 JSON 权限，无 TOML 策略） |
| `/shortcuts` | 显示键盘快捷键 | ❌ 无 |
| `/privacy` | 打开隐私设置 | ❌ 无（通过 `/settings` 间接管理） |
| `/footer` | 配置状态栏（别名 `statusline`） | ❌ 无 |
| `/shells` | 列出活跃 Shell 进程（别名 `bashes`） | ❌ 无 |
| `/commands` | 命令管理（reload） | ❌ 无 |
| `/profile` | 性能分析（开发模式） | ❌ 无 |
| `/corgi` | 彩蛋 | ❌ 无 |

### Qwen Code 有而 Gemini CLI 没有的命令

| Qwen Code 命令 | 功能 | Gemini CLI 对应 |
|---------------|------|----------------|
| `/arena` | **多模型并行 worktree 竞争** | ❌ 无 |
| `/language` | **切换 UI 语言**（6 种） | ❌ 无（仅英文） |
| `/insight` | **代码分析生成报告** | ❌ 无 |
| `/btw` | **快速旁问**（不中断主对话） | ❌ 无（Gemini CLI 仓库搜索 0 匹配） |
| `/review` | **代码审查**（Skill，4 代理并行） | ❌ 无（需安装扩展 `/code-review`） |
| `/summary` | **生成对话摘要**（独立于 /compress 压缩） | ❌ 无（`/compress` 是压缩，非导出摘要） |
| `/extensions` | 扩展管理（兼容 Claude + Gemini 格式） | Gemini CLI 有自己的扩展系统 |

### 命名差异但功能等价的命令

| 功能 | Gemini CLI | Qwen Code | 说明 |
|------|-----------|-----------|------|
| 审批模式 | 集成在 `/plan` + `Shift+Tab` | `/approval-mode` | Qwen 独立为命令 |
| 上下文压缩 | `/compress`（别名 `compact`） | `/compress`（别名 `compact`） | 完全一致 |
| 信任管理 | `/permissions trust`（子命令） | `/trust`（顶级命令） | 功能等价，命令层级不同 |

### 命令差距总结

| 维度 | Gemini CLI | Qwen Code |
|------|-----------|-----------|
| 总命令数 | **39** | **40** |
| Gemini 独有（无对应） | **~8 个** | — |
| Qwen 独有（无对应） | — | **~6 个**（/arena, /language, /insight, /btw, /review, /summary） |
| 继承命令 | — | ~35 个 |

> **核心发现：** 命令数量几乎对等（39 vs 40）。Gemini CLI 独有的命令主要是管理类（/policies、/shortcuts、/shells），Qwen Code 独有的命令是高价值功能（/arena、/btw、/review）——**质量上 Qwen 的独有命令价值更高**。

---

## 一、高优先级（核心能力差距）

### 1. 模型路由器（8 种策略类 / 7 种用户策略）

**Gemini CLI 实现**（`packages/core/src/routing/`）：
- `modelRouterService.ts`：完整的模型路由服务
- **8 种可插拔路由策略类**（源码 TypeScript 实现）：
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

**Qwen Code 缺失影响**：Gemini CLI 的模型粘性用于内部模型路由（如 Fallback 切换后保持新模型）。Qwen Code 的模型由用户显式选择，通常不会自动切换。**如果实现模型路由器（第 1 项），则需要此功能保持路由后的模型一致性**。

**工作量**：极低（半天），加一个实例变量。**依赖模型路由器，独立价值较低**。

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
- **9 个预定义策略文件**（源码：`packages/core/src/policy/policies/`）：
  - `read-only.toml` — 只读模式
  - `write.toml` — 写入权限
  - `yolo.toml` — 全自动模式
  - `plan.toml` — 规划模式
  - `discovered.toml` — 发现的工具
  - `conseca.toml` — CONSECA 策略
  - `memory-manager.toml` — 记忆管理器策略
  - `sandbox-default.toml` — 沙箱默认策略
  - `tracker.toml` — 追踪器策略
- `integrity.ts`：策略完整性校验

**Qwen Code 现状**：使用 JSON settings 的 permission 规则（`deny > ask > allow`），功能等价但格式不同。

**评估**：TOML 策略更适合团队共享和版本控制（可读性好），但 Qwen 的 JSON 规则也能工作。**非阻塞性缺口**，可按需补全。

**工作量**：中（3-5 天）

---

### 6. LLM 响应录制回放（RecordingContentGenerator）

**Gemini CLI 实现**（`core/recordingContentGenerator.ts`）：
- 记录 LLM **原始响应**，供后续 `--fake-responses` 回放
- 用于自动化测试和调试——无需实际调用 LLM

**Qwen Code 现状**：有 `chatRecordingService.ts`（会话历史 JSONL 持久化），但这是**对话记录**，不是 LLM 响应录制回放。Qwen Code **缺少无需 LLM 的离线回放调试能力**。

**工作量**：中（2-3 天）

---

## 三、低优先级（企业/实验性）

### 7. A2A 协议服务器

**Gemini CLI 实现**（`packages/a2a-server/`，[PR #3079](https://github.com/google-gemini/gemini-cli/pull/3079)）：
- 完整的 Agent-to-Agent 通信服务器，基于 `@a2a-js/sdk`
- v0.33.0（2026-03-11）引入 HTTP 认证 + 已认证 Agent Card 发现
- `@a2a` 工具允许模型向其他 Agent 发送消息
- 远程子代理通过 `.well-known/agent.json` 服务发现
- 远程子代理定义为 Markdown 文件（YAML frontmatter），放在项目级或用户级目录

**评估**：A2A 协议已升级到 v0.3（支持 gRPC、安全签名），但生态仍在建设中。Qwen Code 有 Arena 和子代理作为替代方案。

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
| 模型粘性（currentSequenceModel） | 极低（半天） | 中（依赖模型路由器） | P1（与路由器捆绑） |
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
| **多提供商** | Qwen OAuth + DashScope + ModelScope + Anthropic + Google + 自定义（6+） | 仅 Gemini |
| **免费 OAuth** | 每天 1000 次 | 无 |
| **6 语言 UI** | 中/英/日/德/俄/葡 | 仅英文 |
| **Arena 模式** | 多模型并行竞争 | 无 |
| **Arena 多终端后端** | Arena 模式支持 iTerm/Tmux/InProcess 后端 | 无 Arena 模式 |
| **扩展格式转换** | Claude/Gemini 扩展自动转换 | 无 |

---

## 六、一句话总结

**3 个需要投入的 P1**：工具链式调用（减少 LLM 轮次）+ 模型路由器 Fallback（API 容错）+ 模型粘性（与路由器捆绑）

**1 个开发者体验 P1**：LLM 响应录制回放（`--fake-responses` 离线测试）

**Qwen Code 作为分叉已大幅超越上游**——6+ 提供商、免费 OAuth、Arena、6 语言 UI 是独有竞争力。上游的模型路由器（8 策略类）和安全检查器值得借鉴，但 A2A 和 Code Assist 是 Google 专属功能，无需复制。

---

*分析基于 Gemini CLI 开源代码、Qwen Code 开源代码及官方文档，截至 2026 年 3 月。*
