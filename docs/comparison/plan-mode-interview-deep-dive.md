# Qwen Code 改进建议 — Plan 模式 Interview 阶段 (Interview-First Planning)

> 核心洞察：很多 Agent 失败并不是因为不会写代码，而是因为“太快开始写代码”。当用户说“重构认证模块”或“优化构建流程”时，真正危险的地方往往在于需求语义并不完整：到底是局部清理、架构迁移、还是流程再设计？Claude Code 在 Plan Mode 上进一步演进出一个 Interview 阶段，让 Agent 先澄清需求、再形成计划、最后请求批准执行；Qwen Code 当前已经有 `exit_plan_mode` 这一条“计划 → 执行”的后半段链路，但缺少“进入计划时先访谈收集约束”的前半段工作流。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、问题定义：Plan 模式不只是“先写计划”，而是“先搞清楚问题”

很多系统都知道“直接动手改代码”风险很高，所以会引入 plan mode。

但仅仅把流程切成：
- 先给一个计划
- 再让用户批准

还不够。

因为在复杂任务中，真正的失败常常发生在计划之前：

| 用户表达 | 潜在歧义 |
|---------|---------|
| “重构认证模块” | 是提取公共函数，还是从 JWT 迁移到 OAuth2？ |
| “优化 CI” | 是缩短构建时间，还是增强缓存、重试、并行？ |
| “加一个 review 流程” | 是本地命令、PR bot、还是 GitHub Action 集成？ |
| “做成企业可用” | 是权限治理、审计、部署、还是合规配置？ |

如果 Agent 在没有澄清这些关键问题之前就开始规划，那么后面的计划再完整，也可能是“精准地做错事”。

因此更成熟的流程应该是：

```text
interview（澄清需求） → plan（形成方案） → approval（用户确认） → execute（执行）
```

这正是 Claude Code 在 Plan Mode 上比 Qwen 更进一步的地方。

---

## 二、Claude Code 的做法：把 Plan Mode 拆成更完整的多阶段工作流

Claude Code 在 plan mode 相关实现中，已经不满足于“只在最后弹一个审批框”，而是把进入规划阶段前后的行为都做成了系统能力。

### 1. `planModeV2.ts`：Interview phase 不是文档概念，而是正式 feature gate

`utils/planModeV2.ts` 里最关键的信号是：

```ts
export function isPlanModeInterviewPhaseEnabled(): boolean
```

这说明 Claude 已经把 “Interview Phase” 当作一个独立可控制的实验/能力开关，而不是零散 prompt 小技巧。

这个函数还体现出明显的平台化特征：
- `USER_TYPE === 'ant'` 时总是启用
- 可通过环境变量显式开关
- 否则通过 GrowthBook gate `tengu_plan_mode_interview_phase` 控制

这意味着 Interview 阶段具备：
- 灰度发布能力
- 用户群分层能力
- kill-switch 能力

也就是说，Claude 不是“偶尔在提示词里建议先问问题”，而是：

> **把“先访谈再规划”升级成一条正式、可实验、可统计、可回滚的产品工作流。**

### 2. 进入 Plan Mode 时，Claude 会根据 Interview 开关改变工具反馈语义

`tools/EnterPlanModeTool/EnterPlanModeTool.ts` 更直观地展示了这一点。

`mapToolResultToToolResultBlockParam()` 中有明确分叉：
- 如果 `isPlanModeInterviewPhaseEnabled()` 为真，就只给出“进入 plan mode，详细流程说明稍后跟进”的结果
- 如果未启用，则给出传统的 read-only exploration/planning 指南

这说明 Claude 的 Plan Mode 不是单一静态模式，而是：
- 普通 plan mode：探索代码、设计实现方案
- interview-first plan mode：先澄清，再规划

这种差异甚至直接反映到 tool_result 层，意味着模型后续收到的系统信号都不同。

### 3. Agent 数量与探索阶段策略也被纳入 Plan Mode V2

同一个 `planModeV2.ts` 还定义了：
- `getPlanModeV2AgentCount()`
- `getPlanModeV2ExploreAgentCount()`

这点很重要，因为它表明 Claude 对 Plan Mode V2 的思考不只停留在“一句 prompt 多问几个问题”，而是进一步把它看成：

> **一个需要单独调配探索资源、规划资源、实验开关的复合工作流。**

换句话说，Interview 阶段不是孤立 UX，而是与更广义的规划系统耦合的。

### 4. `/plan` 命令本身也承担“进入 / 查看 / 编辑计划”的多态入口

`commands/plan/plan.tsx` 展示了 Claude 的另一个产品化细节：
- 不在 plan mode 时，`/plan` 直接帮助用户进入 plan mode
- 已在 plan mode 时，`/plan` 可展示当前 plan
- `/plan open` 可以在外部编辑器中打开计划文件

这让 plan mode 不只是一个隐式状态，而是有可见、可编辑、可恢复的工件（plan file）。

Interview-first workflow 在这样的系统里更有意义，因为：
- 访谈收集的是形成计划前的输入
- 计划最终会沉淀为明确文件
- 用户和 Agent 能围绕同一 plan artifact 协作

### 5. `ExitPlanModeV2Tool.ts`：计划审批不是简单 yes/no，而是 workflow junction

`tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts` 显示，Claude 的“退出 plan mode”已经是一个很强的 workflow junction：
- 读取并持有 plan 文件
- 支持 allowed prompts 这类语义级权限请求
- 在 teammate 场景中走 mailbox / leader approval 逻辑
- 根据不同上下文决定是否真的需要本地用户交互
- 把 plan approval 请求变成结构化消息与 requestId

这意味着 Claude 的 plan mode 链路至少包含：
- 进入
- 访谈/探索
- 形成计划文件
- 审批
- 多代理/团队中的转发与响应

而不是一个轻量“弹框确认”而已。

### 6. UI 层也明确存在 Plan Approval 的消息组件

`components/messages/PlanApprovalMessage.tsx` 进一步证明，Claude 把计划审批视为一类一等交互对象：
- 请求态有专门展示
- 批准与拒绝分别有不同边框/颜色/反馈
- 拒绝时带 revision guidance
- 还支持与 teammate mailbox 的结构化消息体系结合

这意味着 Interview → Plan → Approval 不是纯后端状态切换，而是完整的人机交互流。

**Claude Code 关键源码**：
- `utils/planModeV2.ts`
- `tools/EnterPlanModeTool/EnterPlanModeTool.ts`
- `commands/plan/plan.tsx`
- `tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts`
- `components/messages/PlanApprovalMessage.tsx`

---

## 三、Qwen Code 现状：已有“计划审批”，但缺少“先访谈再规划”的显式阶段

Qwen Code 在 Plan 模式上并不是空白，相反，它已经有一条清晰的后半段能力链路。

### 1. `exitPlanMode.ts`：Qwen 已经解决了“计划 → 用户批准 → 开始执行”

`packages/core/src/tools/exitPlanMode.ts` 清楚说明：
- 模型生成 `plan`
- 工具向用户展示计划并请求批准
- 用户可 `Proceed Once` / `Proceed Always` / `Cancel`
- 根据选择切换 approval mode

这说明 Qwen 已经拥有：
- 显式的 plan approval 工具
- 清楚的 plan confirmation UI 协议
- 计划通过后切换到可编码状态的机制

这一步本身已经比很多纯“口头计划”系统成熟。

### 2. 开发者文档也明确把 `exit_plan_mode` 定义为 planning workflow 的一部分

`docs/developers/tools/exit-plan-mode.md` 的描述与实现一致：
- 它强调先设计实现方案
- 再通过 `exit_plan_mode` 请求批准
- 最终进入 implementation phase

这意味着 Qwen 已经形成了很明确的“先计划、后执行”意识。

### 3. `PlanSummaryDisplay.tsx`：Qwen 已有计划摘要展示 UI

`packages/cli/src/ui/components/PlanSummaryDisplay.tsx` 说明 Qwen 不只是把结果简单输出为文本，而是专门有一个 plan summary 的展示组件。

从产品角度讲，这代表 Qwen 已经有：
- 计划作为单独 display type 的概念
- 计划批准/拒绝后的专门展示界面

### 4. 但缺少的是“进入 plan mode 之前的 structured interview phase”

与 Claude 相比，Qwen 当前最明显的缺口在于：
- 有 exit，没有对应的 enter/interview phase protocol
- 有 plan approval，没有 interview-first state machine
- 有计划摘要展示，但没有“先问再计划”的显式产品语义

更直白地说，Qwen 当前更像：

```text
explore → 写计划 → 请求批准 → 执行
```

而 Claude 已经在探索：

```text
interview → explore → 写计划 → 请求批准 → 执行
```

这多出来的一步，恰恰是减少方向性返工的关键。

---

## 四、差距本质：Qwen 缺的不是“Plan 模式”，而是“需求澄清阶段”

| 维度 | Claude Code | Qwen Code |
|------|-------------|-----------|
| 显式 plan approval | 有 | 有 |
| 计划展示 UI | 有 | 有 |
| Plan Mode 入口工具/命令 | 有 | 后半段更完整 |
| Interview-first phase | 有 feature gate 与行为分叉 | 未见独立阶段 |
| 多阶段 planning workflow | 更完整 | 主要覆盖计划确认 |
| 团队/高级工作流中的 plan approval | 有 | 未见同等级集成 |

因此这里真正的差距不应被表述为：
- Qwen 没有 Plan Mode
- Qwen 不支持计划批准

而应该更准确地说：

> **Qwen 已经实现了 planning workflow 的“收尾阶段”，但尚未把“先澄清需求再形成计划”产品化成一个独立阶段。**

这类差距特别值得单独成文，因为它直接影响复杂任务的第一步是否走对方向。

---

## 五、为什么 Interview 阶段很重要

### 1. 它降低“高成本返工”概率

在复杂任务里，最贵的错误不是代码写错，而是：
- 改对了代码，改错了方向
- 按错误假设输出了一整套计划
- 用户批准前没发现歧义，批准后还得全部重来

Interview 阶段的价值就是在最便宜的时候暴露歧义。

### 2. 它把“问问题”从临场发挥变成系统机制

如果没有 Interview phase，模型仍然可能通过 `ask_user_question` 自发提问。

但两者差别很大：
- 自发提问：取决于模型是否想到要问
- Interview phase：系统明确要求“先问关键问题，再规划”

也就是说，Interview phase 把“澄清需求”从一种可能行为，提升为一种默认 workflow。

### 3. 它尤其适合高歧义任务

例如：
- 重构
- 迁移
- 平台化改造
- 企业级增强
- 新 feature 设计

这些任务通常不是“少查一个文件”的问题，而是“少确认一个约束就整盘偏掉”。

---

## 六、Qwen Code 的改进路径

### 阶段 1：新增 `enter_plan_mode` 或等价入口工具

Qwen 当前已有 `exit_plan_mode`，下一步最自然的是补上显式入口：
- 进入 plan mode
- 记录当前是否处于 interview phase
- 在进入时切换工作流约束

这样能把 planning workflow 从“只在结束时出现”扩展到“从开始就有阶段意识”。

### 阶段 2：引入 Interview phase 状态

最小版本不一定要复杂，可以先有：
- `interview`
- `planning`
- `execution`

模型在 `interview` 阶段应被明确要求：
- 不做代码修改
- 先问关键澄清问题
- 收集目标、边界、约束、成功标准
- 满足条件后再进入 planning

### 阶段 3：与 `ask_user_question` 深度联动

Qwen 已经有 `ask_user_question`，这是非常好的基础。

Interview phase 的关键不是新做一套提问 UI，而是：
- 给 `ask_user_question` 明确的 workflow 上下文
- 规定何时必须用它
- 规定收集完哪些信息后才可出 plan

也就是说，Qwen 已有工具层基础，缺的是状态机与产品语义层。

### 阶段 4：把计划工件与访谈输入关联起来

Claude 的 plan mode 之所以更完整，一个原因是 plan file / approval / message UI 都是成套的。

Qwen 若继续演进，建议让计划摘要里能够体现：
- 已确认的目标
- 明确的假设
- 尚未覆盖的风险
- 用户已批准的边界

这样计划不再只是步骤列表，而是带来源可追溯的决策产物。

### 阶段 5：后续再考虑 feature gate 与 agent-count 策略

Qwen 初期可以先做一个朴素版本；等成熟后，再考虑像 Claude 那样加入：
- feature gate
- 不同用户分层
- 更复杂的 explore/planning 资源配置

---

## 七、为什么这个改进点值得优先补齐

### 1. 它会显著提升复杂任务成功率

复杂任务最需要的不是更快开始，而是更少返工。

Interview-first workflow 的价值恰恰体现在：
- 把错误暴露在动手前
- 把问题解决在计划前
- 把歧义消除在批准前

### 2. Qwen 已有后半段能力，补齐成本相对可控

Qwen 并不是从零做 Planning：
- 已有 `exit_plan_mode`
- 已有 plan approval
- 已有 plan summary display
- 已有 `ask_user_question`

所以这不是新发明一个系统，而是把已有能力补成完整闭环。

### 3. 对文档/代码类复杂任务尤其有意义

这个仓库的工作模式正是高歧义、高上下文的例子：
- 要读多个仓库
- 要比对实现差异
- 要选择合适主题
- 要避免与已有 deep-dive 重复

这类任务非常适合 Interview-first workflow，因为“先对齐目标”本身就能减少误判。

---

## 八、结论

Claude Code 在 Plan Mode 上最值得借鉴的，不是“有计划审批”，而是：

> **它把规划工作流继续前移了一步：在真正写计划之前，先把需求访谈本身产品化。**

Qwen Code 当前已经拥有不错的 planning 后半段：
- 计划展示
- 用户批准
- 执行切换

但还缺少一个正式的、可感知的 Interview 阶段，去确保 Agent 在规划之前先理解正确的问题。

因此这个改进点最准确的描述不是：
- 再优化一下 Plan 模式
- 再加一点提问 prompt
- 再做一个审批弹窗

而是：

> **把 Qwen 的 Plan 模式从“先写计划再批准”升级为“先访谈、再规划、再批准、再执行”的完整工作流。**

这会比单纯优化计划展示，更实质地降低复杂任务中的方向性错误。

---

## 关键源码索引

### Claude Code
- `utils/planModeV2.ts`
- `tools/EnterPlanModeTool/EnterPlanModeTool.ts`
- `commands/plan/plan.tsx`
- `tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts`
- `components/messages/PlanApprovalMessage.tsx`

### Qwen Code
- `packages/core/src/tools/exitPlanMode.ts`
- `docs/developers/tools/exit-plan-mode.md`
- `packages/cli/src/ui/components/PlanSummaryDisplay.tsx`
- `packages/core/src/tools/askUserQuestion.ts`

> **免责声明**：以上结论基于 2026-04 本地源码与当前仓库文档对比，后续版本可能已变更。