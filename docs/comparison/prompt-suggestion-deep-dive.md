# Qwen Code 改进建议 — Prompt Suggestion / Next-step Suggestion（下一步输入建议）

> 核心洞察：当一次对话刚结束、用户还没开始输入下一句时，Agent 最有机会做的一件事，不是继续解释自己刚做了什么，而是轻量预测“用户下一步大概率会输入什么”。Claude Code 把这个能力产品化为 Prompt Suggestion：基于上下文预测下一条自然输入，配套启用策略、过滤规则、接受/忽略遥测，以及终端内的轻量展示。Qwen Code 其实已经有相当扎实的基础实现：core 中有 `suggestionGenerator.ts`，CLI/WebUI 也都接入了 followup controller；但从源码对比看，Claude 在启用治理、抑制策略、过滤成熟度、以及 suggestion 生命周期的精细度上仍更完整。也就是说，Qwen 已经“做出来了”，但还有机会继续把它打磨成更成熟的交互子系统。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么“下一步输入建议”值得单独讨论

传统 CLI Agent 的交互循环通常是：
- 用户输入问题
- 模型给出回答
- 用户自己想下一步干什么

但真实使用中，很多场景的“下一步”其实高度可预测：

| 当前对话状态 | 用户下一步常见输入 |
|-------------|------------------|
| bug 刚修完 | `run the tests` |
| 改动刚完成 | `commit this` |
| 模型问是否继续 | `yes` / `go ahead` |
| 输出了一组方案 | 用户通常会选其中一个 |
| 错误修复后 | `try it out` |

如果系统能在用户还没输入前，轻量给出一个高概率建议，就会带来几个收益：

1. **减少一次思考开销**：用户不必重新组织语言
2. **降低交互摩擦**：尤其在重复工作流中很明显
3. **让 Agent 更像协作伙伴**：不是只会等输入，而是在预测下一步
4. **为后续 speculation / prefetch 创造条件**：一旦猜对，系统甚至可以提前准备下一轮

所以这不是一个“花哨 UI 小功能”，而是一个典型的交互效率增强能力。

---

## 二、Claude Code 的做法：Prompt Suggestion 是一条完整的产品链路

Claude Code 在这一能力上最有价值的地方，不只是“能生成建议”，而是它把 suggestion 当成一个完整的系统能力来做。

### 1. `promptSuggestion.ts`：明确的启用条件与抑制逻辑

`services/PromptSuggestion/promptSuggestion.ts` 展示了 Claude 对这项能力的谨慎态度。

首先，`shouldEnablePromptSuggestion()` 并不是简单返回 true，而是依次考虑：
- 环境变量覆盖
- GrowthBook gate（`tengu_chomp_inflection`）
- non-interactive session 禁用
- swarm teammate 禁用
- settings 中的 `promptSuggestionEnabled`

这说明 Claude 非常明确地知道：

> **Prompt Suggestion 不是在所有场景下都应该打开。**

尤其这几点很关键：
- **非交互模式禁用**：print mode、piped input、SDK 不展示 suggestion
- **swarm teammate 禁用**：多代理环境中只让 leader 展示 suggestion
- **feature gate + setting 并存**：既能灰度，又能给用户显式开关

这是一种非常成熟的启用治理模型。

### 2. 抑制条件不只看“开关”，还看当前对话状态

Claude 在 `getSuggestionSuppressReason()` 和 `tryGenerateSuggestion()` 中又加了一层运行时抑制：
- `pending_permission`
- `elicitation_active`
- `plan_mode`
- `rate_limit`
- `early_conversation`
- `last_response_error`
- `cache_cold`
- `empty`
- `aborted`

这意味着 suggestion 不是“只要开着就无脑生成”，而是：

> **只有在当前交互状态足够稳定、足够适合时才会生成。**

这类抑制规则的价值很大，因为建议本身很容易在错误时机变成噪音：
- 用户正在审批权限时，不该弹建议
- plan mode 中，不该把 focus 拉回“随手下一句”
- 上一轮是错误响应时，建议往往不可靠
- 上下文缓存冷、成本高时，也未必值得生成

Claude 在这方面明显做了大量产品经验沉淀。

### 3. 建议生成本身是独立子流程，甚至能与 speculation 联动

在 `tryGenerateSuggestion()` / `executePromptSuggestion()` 中，Claude 会：
- 使用 forked agent / cache-safe params 生成 suggestion
- 记录 `promptId`、`generationRequestId`
- 将 suggestion 写回 appState
- 如果 speculation 开启，还会 `startSpeculation()`

这说明 Claude 并没有把 suggestion 当作一个死的 UI placeholder，而是把它当作：

> **后续 speculative execution / cache reuse 的前置步骤。**

也就是说，suggestion 和性能优化、预取策略其实有内在关联。

### 4. `SUGGESTION_PROMPT` + `shouldFilterSuggestion()`：规则非常细

Claude 的 `SUGGESTION_PROMPT` 已经很完整，但更体现成熟度的是后续过滤：
- evaluative（如 “looks good”, “thanks”）
- questions
- Claude-voice（“Let me...”, “I'll...”）
- new ideas they didn’t ask about
- `cache_cold`
- `meta_text`
- `meta_wrapped`
- `too_few_words`
- 以及大量更细的 rule-based suppress/filter

这里反映出一个很重要的经验：

> **预测用户下一句并不难，难的是别在错误时刻给出错误风格的建议。**

从产品上看，Claude 真正强的不是“生成”，而是“只留下高信号 suggestion”。

### 5. `usePromptSuggestion.ts`：遥测与交互生命周期很完整

`hooks/usePromptSuggestion.ts` 展示了 Claude 在 suggestion 生命周期上的精细设计：
- `shownAt`
- `acceptedAt`
- `firstKeystrokeAt`
- `wasFocusedWhenShown`
- `acceptMethod`（tab / enter）
- `timeToAcceptMs`
- `timeToIgnoreMs`
- `timeToFirstKeystrokeMs`
- `similarity`

这意味着 Claude 不只是知道 suggestion 有无被点，而是能深入分析：
- 用户是否在 suggestion 显示时聚焦终端
- 是立即接受，还是输入几个字后忽略
- 用户输入与 suggestion 的相似度如何
- 哪种 accept method 更常见

这已经是非常成熟的 UX telemetry 思维。

### 6. 终端内也有专门的建议展示组件

Claude 的 suggestion 不是纯后端能力，还有专门 UI，如：
- `components/PromptInput/PromptInputFooterSuggestions.tsx`

说明它已经是一个完整端到端产品，而不是试验性 API。

**Claude Code 关键源码**：
- `services/PromptSuggestion/promptSuggestion.ts`
- `hooks/usePromptSuggestion.ts`
- `components/PromptInput/PromptInputFooterSuggestions.tsx`

---

## 三、Qwen Code 现状：已经具备基础实现，但治理与成熟度仍可继续加强

这次对比里，Qwen 与很多“完全缺失”的改进点不同。Qwen 在 Prompt Suggestion 上其实已经走得不浅。

### 1. `suggestionGenerator.ts`：Qwen 已经有核心生成器

`packages/core/src/followup/suggestionGenerator.ts` 非常关键，它已经清楚定义：
- `SUGGESTION_PROMPT`
- `SUGGESTION_SCHEMA`
- `MIN_ASSISTANT_TURNS`
- `generatePromptSuggestion()`
- `generateViaForkedQuery()` / `generateViaBaseLlm()`
- `getFilterReason()`

这意味着 Qwen 不只是“想到要做这个功能”，而是已经有一个独立、可复用的 core 层 suggestion engine。

而且从 prompt 文本上看，Qwen 与 Claude 的方向高度一致：
- 预测用户自然会输入什么
- 避免 AI-voice
- 避免新点子
- 2-12 words
- 支持在无明显下一步时保持沉默

这说明两边在能力定位上非常接近。

### 2. Qwen 也已经考虑了 forked query 与 cache-aware 路径

Qwen 的 `generatePromptSuggestion()` 并不是硬编码单一路径，而是支持：
- cache-aware `runForkedQuery()`
- 直接 `generateContent()` 的 base LLM 路径

这与 Claude 的思路是相通的：suggestion 不一定必须走主会话完整生成链路，而可以通过更轻的分叉请求来完成。

### 3. CLI 与 WebUI 都已接入共享 controller

Qwen 这块还有一个很好的设计：
- CLI：`packages/cli/src/ui/hooks/useFollowupSuggestions.tsx`
- WebUI：`packages/webui/src/hooks/useFollowupSuggestions.ts`

二者都基于共享的 controller：
- `INITIAL_FOLLOWUP_STATE`
- `createFollowupController()`

这说明 Qwen 没有把 suggestion 绑死在某个前端，而是已经做成：

> **core 生成 + shared controller + 多前端接入**

这在架构上是很健康的。

### 4. Composer 也已经接入 promptSuggestion

`packages/cli/src/ui/components/Composer.tsx` 中，`InputPrompt` 已经接收：
- `promptSuggestion`
- `onPromptSuggestionDismiss`

说明这个能力已经不只是底层代码，还进入了实际终端输入体验。

### 5. 但与 Claude 相比，Qwen 仍有几个明显可继续补强的点

虽然 Qwen 已有实现，但与 Claude 对比后，还能看到几个方向：

#### (1) 启用治理还不够细

Claude 的启用规则覆盖：
- env override
- growthbook gate
- non-interactive
- swarm teammate
- settings

Qwen 当前实现里，更明显的是生成器与前端 controller，但从这次读到的路径看，还没有看到 Claude 那么完整的“运行前启用决策矩阵”。

也就是说，Qwen 更像：
- 已能生成 suggestion
- 已能展示 suggestion

但 Claude 更像：
- 明确知道**什么时候绝对不要生成**
- 明确知道**谁该看 suggestion，谁不该看**

#### (2) 过滤规则虽然有，但产品化抑制策略仍可更强

Qwen 的 `getFilterReason()` 已经有不少过滤逻辑，这是好事。

但 Claude 的系统还额外关注：
- pending permission
- elicitation active
- plan mode
- rate limit
- last response error
- cache cold

这些偏“运行时产品状态”的 suppress reason，比单纯文本过滤更贴近真实交互质量。

#### (3) 遥测粒度还可以更丰富

Qwen 的 CLI hook 里已有：
- outcome telemetry
- time-to-accept / ignore
- suggestion length
- focus state

这已经不错。

但 Claude 还进一步记录：
- first keystroke timing
- similarity
- generation request id
- shownAt / acceptedAt 与 suggestion state 的强绑定
- 某些内部用户群的 suggestion / userInput 对照

对后续调优来说，这种数据会非常有价值。

#### (4) Suggestion 与更大交互体系的联动仍可加强

Claude 的 suggestion 与 speculation、cache safety、permission state、plan mode 都有联动。

Qwen 当前更像“一个独立增强点”，而 Claude 更像“嵌在整个交互状态机中的一个节点”。

---

## 四、差距本质：Qwen 缺的不是功能存在性，而是系统成熟度

这篇最重要的结论，不是“Qwen 没有 Prompt Suggestion”。

恰恰相反，Qwen **已经有了**：
- suggestion prompt
- 独立生成器
- forked query 路径
- shared controller
- CLI/WebUI 双接入
- 基本 telemetry

所以更准确的表述应该是：

> **Qwen 已经实现了 Prompt Suggestion 的基础闭环，但相较 Claude，仍可继续强化启用治理、运行时抑制、Suggestion 过滤成熟度，以及与整个交互状态机的联动。**

这类差距很适合写成独立 deep-dive，因为它体现的是：
- 不是“有/无”
- 而是“从可用到成熟”的差距

这种对比比单纯的 feature gap 更有价值。

---

## 五、Qwen Code 的改进路径

### 阶段 1：补齐更明确的启用/禁用决策层

建议把 suggestion 是否启用拆成一个独立决策函数，统一考虑：
- interactive / non-interactive
- plan mode
- 权限审批中
- 多 agent / teammate / arena 场景
- 用户 settings
- feature gate

这样能避免 suggestion 在错误时机出现。

### 阶段 2：把“文本过滤”升级为“状态抑制 + 文本过滤”双层模型

当前已有 `getFilterReason()`，下一步可以补一层：
- `getSuppressReason(appState)`

先看当前交互状态适不适合生成 suggestion，再进入文本过滤。

### 阶段 3：补 suggestion 生命周期遥测

可进一步记录：
- shownAt
- acceptedAt
- firstKeystrokeAt
- suggestion similarity
- generationRequestId
- suggestion source（cli/webui/sdk）

这样后续调优会更有依据。

### 阶段 4：与 speculation / prefetch / cache reuse 联动

如果 Qwen 后续继续加强 speculation 或预取策略，那么 Prompt Suggestion 会是天然的前置信号。

一旦 suggestion 高置信生成成功，可以进一步：
- 预热 cache
- 预取相关上下文
- 甚至先做轻量 speculative analysis

### 阶段 5：明确产品定位，避免与 ghost text 混淆

Qwen 已经有输入层体验增强能力，建议把这类能力边界说清楚：
- ghost text：输入时补全
- prompt suggestion：回复结束后预测下一句
- file index / fuzzy search：定位资源

这样用户与开发者都更容易理解各自价值。

---

## 六、为什么这个改进点值得现在写

### 1. 它是一个“Qwen 已有基础、还能继续打磨”的优质选题

这类题目很有价值，因为它不是空想需求，而是：
- 已有实现
- 已有用户可感知入口
- 已能通过对比提炼出下一步优化方向

### 2. 它能自然连接输入体验体系

当前仓库已经有：
- `ghost-text-completion-deep-dive.md`
- `file-index-fuzzy-search-deep-dive.md`

Prompt Suggestion 可以成为“输入体验与下一步交互”的又一个关键环节，构成更完整的交互链路图谱。

### 3. 对用户价值直观，且不容易与现有 deep-dive 重复

它不像某些底层性能点那样需要大量背景知识；用户几乎立刻能理解：
- 系统是不是在恰当时机给出恰当建议
- 建议是不是经常“像我正准备输入的那句”

---

## 七、结论

Claude Code 与 Qwen Code 在 Prompt Suggestion 上的差距，不应被理解为“有和没有”的差距。

Qwen 已经具备：
- 核心 suggestion generator
- 过滤逻辑
- CLI/WebUI 共享 controller
- 实际输入组件接入

Claude 更领先的地方在于：
- 更细的启用治理
- 更成熟的运行时 suppress 规则
- 更精细的过滤与遥测
- 与 speculation / 状态机更深的联动

因此这个改进点最准确的表述是：

> **把 Qwen 的 Prompt Suggestion 从“已经可用的交互增强功能”，继续打磨成一个有更强策略治理与更高信号质量的成熟交互子系统。**

这会让它不只是“偶尔有用的建议气泡”，而是成为真正可靠的下一步协作能力。

---

## 关键源码索引

### Claude Code
- `services/PromptSuggestion/promptSuggestion.ts`
- `hooks/usePromptSuggestion.ts`
- `components/PromptInput/PromptInputFooterSuggestions.tsx`

### Qwen Code
- `packages/core/src/followup/suggestionGenerator.ts`
- `packages/cli/src/ui/hooks/useFollowupSuggestions.tsx`
- `packages/webui/src/hooks/useFollowupSuggestions.ts`
- `packages/cli/src/ui/components/Composer.tsx`

> **免责声明**：以上结论基于 2026-04 本地源码与当前仓库文档对比，后续版本可能已变更。