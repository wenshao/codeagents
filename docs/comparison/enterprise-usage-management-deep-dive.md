# Qwen Code 改进建议 — 企业用量管理与费用追踪 (Enterprise Usage Management)

> 核心洞察：当 AI 代码助手从个人免费玩具转变为企业级生产力工具（通常需要绑定企业 API 密钥或者充值额度）时，开发者和技术主管对“成本”和“用量”变得极其敏感。在大模型特别是旗舰模型高昂的 Token 单价下，如果没有及时的用量透视，很容易因为一个死循环的 Agent 任务刷爆信用卡。Claude Code 提供了 `/cost` 与极其详尽的 `/extra-usage` 面板，支持近实时的费用预测与历史消耗查询；而 Qwen Code 目前在企业级配额与用量可视化方面支持较弱。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、API 成本带来的使用焦虑

### 1. Qwen Code 的现状：事后诸葛亮
在当前使用 Qwen Code 的过程中：
- **痛点**：用户无法在终端里直接看到自己的 DashScope（阿里云百炼）账户里还剩多少免费额度，或者这个月已经花掉了多少钱。
- **痛点**：对于一次涉及几百次问答的复杂重构，用户只能在任务全部结束后或者去云控制台里，才能看到后知后觉的账单。这种对成本的“未知恐惧”，会导致很多初级开发者不敢开启并行子任务（Subagents）或者尝试极其吃 Token 的全盘项目审阅。

### 2. Claude Code 解决方案：高能见度的财务账单
在 Claude Code 的 `commands/extra-usage/` 目录下，他们将账单系统做成了终端原生的一环。

#### 机制一：多维度的用量透视 (Usage Dashboard)
通过命令 `/extra-usage` 或 `/cost`，它可以在不跳转浏览器的情况下，通过 API 直接调用账户系统，在终端里渲染出一张排版精美的财务报表。
- 包含当前 Session 的累计消耗（精确到美分）。
- 包含过去 30 天的历史柱状图（通过 ASCII Art 字符画实现简单的趋势图）。
- 区分不同维度的花销：`Input Tokens`, `Output Tokens`, 甚至细分到 `Cache Read Tokens`（命中缓存省了多少钱）这让用户对 Prompt Caching 带来的收益有极其直观的爽感。

#### 机制二：防刷爆的熔断提醒 (Budget Alerts)
在底层的 API 请求层（`services/api/claude.ts`），不仅记录每次请求的增量 Token，还会读取账户的剩余额度。如果余额不足以支撑下一次满额（比如 128K）上下文的发送，它会提前在请求发出前拦截，抛出 `CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE`，让用户去充值，而不是让请求在半路死掉导致数据损坏。

## 二、Qwen Code 的改进路径 (P3 优先级)

打破黑盒，把计费透明化作为对开发者最大的尊重。

### 阶段 1：开发全局 Token 追踪器 (Cost Tracker)
1. 在 `packages/core/src/` 中新增 `costTracker.ts`。
2. 维护内存状态：`sessionInputTokens`, `sessionOutputTokens`, `cachedTokens`。
3. 根据当前使用的具体模型（如 `qwen-max`, `qwen-turbo`）实时换算出 CNY/USD 费用。并在终端的状态栏或者每个交互 Round 结束时，附带一个暗色的 `(¥0.12)` 小尾巴。

### 阶段 2：集成 DashScope 用量查询
1. 新建 `/usage` 交互命令。
2. 调用阿里云大模型平台的 OpenAPI 获取账号/API Key 维度的月度账单和限额。
3. 利用 React Ink 渲染成美观的数据仪表盘。

### 阶段 3：引入硬性阻断阈值 (Hard Budget Limit)
在 `qwen config` 中允许用户设置 `--max-budget-usd 5.00`。
这是给脚本自动化（CI/CD）的定心丸：如果 Agent 意外陷入死循环，只要在这个项目的累计花费到达 5 刀，强制掐断所有网络请求，防范天价账单。

## 三、改进收益评估
- **实现成本**：中等。核心挑战在于接入各个模型提供商（DashScope 等）的账单 API。
- **直接收益**：
  1. **建立信任壁垒**：成本透明是企业采购 AI 工具的第一考量要素，这一步直接提升商业化变现的可能。
  2. **消除开发者焦虑**：看着每一分钱花在哪里，反而会鼓励开发者更有底气地去利用长上下文进行复杂任务。