# Qwen Code 改进建议 — Advisor 顾问模型 (Advisor Model & Multi-Model Collaboration)

> 核心洞察：当我们使用大模型执行高风险操作（例如：编写一条复杂的数据库迁移 SQL，或者生成一段混淆过的正则表达式）时，即使是最强的旗舰模型也偶尔会产生“自信的幻觉”。如果这段代码被 Agent 直接静默执行，后果不堪设想。Claude Code 通过内置的 `/advisor` 命令首创了“主副模型协作审查”机制（Advisor Model）。当主模型输出代码后，无需用户介入，系统会在后台自动唤起一个独立的副模型对其结果进行背对背的交叉验证与挑刺；而 Qwen Code 目前完全是单模型闭环架构，缺乏自我纠错的“第二双眼睛”。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、单模型架构在安全场景的局限性

### 1. Qwen Code 现状：直接信任
在当前的执行链路中，Qwen Code 的大模型是唯一的决策者。
- **痛点一（盲目执行）**：如果用户开启了 `auto-edit` 或 `yolo` 模式，大模型一旦生成了一条删除目录的 Shell 命令或者修改了鉴权中间件的逻辑，系统会直接予以放行。
- **痛点二（同质化盲区）**：哪怕在生成的过程中我们让它“三思而后行 (Think Step-by-Step)”，同一个模型对自己的错误往往存在“思维惯性（Echo Chamber）”，很难发现自己刚刚写错的空指针异常。

### 2. Claude Code 的解决方案：主副对弈 (Adversarial Review)
在 Claude Code 的 `utils/advisor.ts` 以及底层的 `commands/advisor.ts` 中，作者引入了一个被称为“顾问 (Advisor)”的全新角色。

#### 机制一：灵活的副模型挂载
用户可以通过 `/advisor opus` 等命令，随时为一个处于“快速模式（Haiku/Sonnet）”的主干 Agent，挂载一个“重型旗舰模型（Opus）”作为技术顾问。这完美平衡了速度和质量：
平时翻找文件和写 CRUD 由又快又便宜的小模型负责；一到高难度技术决策，背后的大佬就会睁眼。

#### 机制二：`server_tool_use` 系统级拦截
这种审查**不是**通过向当前对话数组简单追加文字来实现的。
在 Claude API 的底层协议中，系统利用了一种类似隐形工具调用的机制（`AdvisorServerToolUseBlock`）：
1. 主模型在生成了一段敏感代码或计划后，返回结果前。
2. 调度引擎会自动拦截这波输出，并将其封装在一个特殊的系统级上下文中，发送给 Advisor 模型。
3. Advisor 模型独立审视这段逻辑，给出“通过（Approved）”或者尖锐的改进意见（“这段代码存在 SQL 注入风险，应该改用参数化查询”）。
4. 引擎将 Advisor 的挑刺结果，以 `advisor_tool_result` 的形式注入回原会话中，强制主模型重新生成并修正代码。

整个主副博弈的过程发生在瞬间的后台，用户只会看到终端里主模型“恍然大悟”地改进了自己的代码，体验极其安全且充满科技感。

## 二、Qwen Code 的改进路径 (P3 优先级)

让大模型之间产生对齐与对抗，是通往 AGI 高可靠性的必经之路。

### 阶段 1：开发 `/advisor` 注册逻辑
1. 修改 `config/settings.ts`，加入 `advisorModel` 字段。
2. 新增命令 `/advisor <model_name>`，允许用户指定 `qwen-max` 等大模型作为评审官。

### 阶段 2：拦截推理执行流
1. 修改 `agent-core.ts` 中的 `processModelResponse` 阶段。
2. 当发现大模型输出了带有高危权限的 `functionCalls`（例如 `shell`, `write_file`），如果开启了 Advisor 模式，则**先挂起（Suspend）这些工具的执行**。
3. 把这些即将执行的命令或代码，组装成一段 Prompt 发送给 Advisor 模型：
   > "You are an expert Security and Logic Reviewer. The primary agent is about to execute the following code/command. Point out any severe bugs, security flaws, or confirm if it's safe."

### 阶段 3：结果融合与强制返工
1. 如果 Advisor 返回 “无明显错误 (No critical issues)”，则原封不动地放行挂起的工具。
2. 如果 Advisor 返回了漏洞报告，则取消本次工具执行。将报告作为一条 `user` (或伪装的 `system`) 消息抛给主模型：“The Advisor model has reviewed your proposed action and found the following issues: ... Please fix them before proceeding.”。

## 三、改进收益评估
- **实现成本**：中等。核心在执行流的挂起与子 Agent 的无缝调用，代码约 200 - 300 行。
- **直接收益**：
  1. **指数级提升代码可靠性**：双模型交叉验证几乎能将大模型的幻觉和初级错误率压至极低，让企业敢于在生产环境使用 `yolo` 模式。
  2. **成本与质量的最优解**：主流程采用 Qwen-Turbo（极速省钱），安全评审采用 Qwen-Max（稳健兜底），是目前业界公认的最佳商业落地方案。