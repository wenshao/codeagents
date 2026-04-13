# Qwen Code 改进建议 — Kairos Always-On 自治 Agent 模式 (Always-On Autonomous Agent)

> 核心洞察：交互式 CLI Agent 的下一步演进方向是什么？Claude Code 给出的答案是 **Kairos**——一个编译时特性门控的"Always-On"自治模式。Kairos 让 Agent 不再只是"等人提问→回答→等下一个问题"，而是变成一个持续运行、主动行动、可定时调度的自治助手。它整合了 Cron 任务调度器、Brief 精简通信模式、异步 Agent 派生、Sleep 成本权衡、每日日志追加、Proactive Tick 引擎等多个子系统，构成了从"工具"到"平台"的关键跃迁。Qwen Code 目前没有任何等价机制。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、问题定义：交互式 Agent 的天花板

### 1. 传统交互模型的局限

当前所有主流 CLI Agent（包括 Qwen Code、Gemini CLI、Codex CLI）都遵循同一个交互范式：

```
用户输入 → Agent 思考 → 调用工具 → 输出结果 → 等待下一次输入
```

这个模型对"即时任务"非常有效，但对以下场景无能为力：

| 场景 | 交互式 Agent 的瓶颈 |
|------|-------------------|
| 每天早上自动检查 PR 状态 | 用户必须手动打开终端并输入指令 |
| 监控 CI 构建并在失败时通知 | Agent 只在会话期间存活 |
| 定期清理过期分支 | 无调度能力，依赖外部 crontab |
| 在后台持续分析新提交 | Agent 没有"idle tick"概念 |
| 多任务同时推进时汇报进度 | 同步执行，一次只做一件事 |

### 2. Claude Code 的答案：Kairos 系统

Kairos（希腊语 καιρός，意为"恰当的时机"——不是 chronos 那种机械的时钟时间，而是"该行动的恰当时刻"）是 Claude Code 内部一个完整的自治 Agent 框架。该关键词在泄漏源码中被引用超过 150 次，是整个代码库中引用最密集的未发布特性之一。

它通过编译时特性门控 `feature('KAIROS')` 隔离，目前仅对 Anthropic 内部用户（`USER_TYPE=ant`）开放。Claude Code 创始人 Boris Cherny 已确认 Kairos 正处于"测试中，即将进入生产环境"的状态。

源码: `main.tsx#L78-L81`（条件导入）：
```typescript
// Dead code elimination: conditional import for KAIROS (assistant mode)
const assistantModule = feature('KAIROS')
  ? require('./assistant/index.js') : null;
const kairosGate = feature('KAIROS')
  ? require('./assistant/gate.js') : null;
```

### 3. 行业影响与已发布功能

值得注意的是，虽然完整的 Kairos 系统尚未公开发布，但 Anthropic 已经将其部分子能力以独立功能的形式发布到了生产环境：

| 已发布功能 | 对应 Kairos 子系统 | 发布形态 |
|-----------|-------------------|---------|
| `/loop` 命令 | Cron Scheduler | Cron 风格调度，上限 50 个任务，7 天自动过期 |
| `/schedule` skill | Cron Scheduler (Desktop) | 桌面端持久化任务，跨重启存活 |
| Remote Triggers | Proactive Tick | GitHub Actions 远程唤醒 |
| Background Agents | Async Agent | `run_in_background` 参数 |

这意味着 Kairos 的各个子系统正在以渐进式发布的方式逐步上线，验证了"模块化发布、逐步开放"的可行路径。

## 二、Kairos 架构全景

### 1. 系统组成

Kairos 并非单一功能，而是一个由 7 个子系统协同构成的自治框架：

```
KAIROS (Always-On Agent)
│
├─ 1. Activation Gate ─── 编译时 + 运行时双重门控
│     ├─ feature('KAIROS')        编译时 dead code elimination
│     ├─ tengu_kairos             GrowthBook 运行时灰度
│     └─ Directory Trust          需要用户信任当前目录
│
├─ 2. Proactive Tick ─── 心跳决策引擎
│     ├─ scheduleProactiveTick()  定期注入 <tick> prompt
│     ├─ Status Field Routing     'normal' vs 'proactive' 路由
│     └─ 二元决策：行动 or 保持安静
│
├─ 3. Cron Scheduler ─── 定时任务调度器
│     ├─ CronCreate / Delete / List  3 个工具
│     ├─ Durable Tasks              跨会话持久化
│     ├─ Deterministic Jitter       避免 :00 雷群
│     └─ tengu_kairos_cron          运行时熔断开关
│
├─ 4. Brief Mode ─── 精简通信模式
│     ├─ SendUserMessage 工具       非阻塞主动通知
│     ├─ SendUserFile               文件推送
│     ├─ PushNotification           设备推送通知
│     └─ 15 秒阻塞预算              不打扰用户
│
├─ 5. Sleep / Cost Controller ─── 睡眠与成本权衡
│     ├─ Sleep 工具                 控制唤醒节奏
│     ├─ API 调用成本感知           每次唤醒 = 一次 API 调用
│     └─ Prompt Cache 过期权衡      >5min 睡眠 → cache 重建
│
├─ 6. Async Agent ─── 异步 Subagent 派生
│     ├─ Fire-and-forget 执行       不阻塞主线程
│     ├─ isMeta 结果回注            静默合并结果
│     └─ 并行执行多个过期任务       避免串行排队
│
└─ 7. Daily Log ─── 每日追加日志
      ├─ Append-only 日志文件       `~/.claude/projects/<project>/memory/logs/`
      └─ 跨 perpetual session 审计  观察/决策/行动记录
```

### 2. 激活流程

源码: `main.tsx#L1048-L1089`：

```
启动
  │
  ├─ 检查 feature('KAIROS')  ← 编译时门控
  │     ↓ (不通过 → 跳过，dead code elimination)
  │
  ├─ 检查 isAssistantMode()  ← --assistant 标志
  │     ↓
  ├─ 检查 kairosGate.isKairosEnabled()  ← GrowthBook 运行时门控
  │     ↓
  ├─ 检查 Directory Trust  ← 安全要求
  │     ↓
  ├─ setKairosActive(true)  ← 全局状态置位
  ├─ opts.brief = true      ← 强制 Brief 模式
  ├─ 初始化 assistantTeamContext  ← In-process 队友上下文
  └─ 启动 CronScheduler    ← 开始调度循环
```

关键设计：`kairosEnabled` 在启动时计算一次后永不变更（`AppStateStore.ts#L116`），避免运行时状态翻转导致的一致性问题。运行时熔断通过 GrowthBook 的 `tengu_kairos_cron` 门控实现——关闭门控会停止调度器的下一次 tick，但不会影响正在执行的任务。

### 3. 子系统详解

#### 子系统 A：Proactive Tick 心跳引擎

源码: `screens/REPL.tsx#L194`（条件导入 `proactive/index.js`）, `cli/print.ts`（`scheduleProactiveTick`）

> 注：`proactive/` 目录在泄漏构建中因 dead code elimination 被移除，仅通过 `feature('PROACTIVE') || feature('KAIROS')` 保护的条件 `require()` 可知其存在。

这是 Kairos 最核心的创新——将 Agent 从"被动响应"转变为"主动感知"。

通过 `scheduleProactiveTick()` 函数，系统定期向 Agent 的消息队列注入 `<tick>` prompt。每个 tick 携带当前本地时间，告诉 Agent"你醒了——现在想做什么？"Agent 在收到 tick 后做出二元决策：

```
<tick timestamp="2026-04-05T09:00:00+08:00">
  │
  ├─ Agent 评估当前环境
  │     ├─ 文件系统变化
  │     ├─ Git 状态（新提交、PR 更新）
  │     ├─ 待处理消息 / 过期 Cron 任务
  │     └─ 用户是否在终端前（焦点检测）
  │
  ├─ 决策：行动 or 保持安静？
  │     ├─ 行动 → 在 15 秒阻塞预算内执行
  │     │         标记 status: 'proactive'
  │     └─ 安静 → 仅记录日志，不打扰用户
  │
  └─ 追加观察和决策到 Daily Log
```

**Status Field 路由**：Agent 的每个响应都带有 status 字段。`'normal'` 表示对用户消息的回复，`'proactive'` 表示未经请求的主动行为。下游路由系统据此决定通知策略——主动行为通常静默记录，只有在发现重要问题（如 CI 构建失败）时才通过 PushNotification 打扰用户。

#### 子系统 B：Cron 任务调度器

源码: `utils/cronScheduler.ts`, `utils/cronTasks.ts`, `utils/cronJitterConfig.ts`

Agent 可以通过 CronCreate 工具自行创建定时任务：

```typescript
// 工具定义 (tools/ScheduleCronTool/prompt.ts)
CronCreate: {
  description: "Schedule a prompt to run at a specific time",
  parameters: {
    prompt: string,      // 要执行的自然语言指令
    schedule: string,    // Cron 表达式或 ISO 8601 时间
    recurring: boolean,  // 是否循环执行
    label: string        // 人类可读标签
  }
}
```

**持久化机制**：当 `tengu_kairos_cron_durable` 门控开启时，任务持久化到 `~/.claude/scheduled_tasks.json`，跨会话存活。关闭时仅在当前会话内有效。已发布的 `/loop` 命令限制上限为 50 个任务。

**Jitter 防雷群**：`cronJitterConfig.ts` 从 GrowthBook 的 `tengu_kairos_cron_config` 读取抖动配置，对每个任务的触发时间添加确定性偏移，避免大量用户的 Cron 任务在 `:00` 整点同时击穿 API：

```typescript
// cronJitterConfig.ts#L56-L69
// 从 GrowthBook 获取配置，5 分钟刷新间隔
const config = getGrowthBookFeatureValue(
  'tengu_kairos_cron_config',
  DEFAULT_JITTER_CONFIG
);
```

**执行调度**：任务在 REPL 空闲时触发（不在用户输入过程中中断），通过 `'later'` 优先级入队，在轮次间隙排空。

**运营熔断**：在事故期间，运维团队可以通过 GrowthBook 推送新的 `tengu_kairos_cron_config` 配置，例如将所有定时任务的最小间隔从 5 分钟提高到 60 分钟，或直接关闭 `tengu_kairos_cron` 门控停止整个调度器。

**自动过期**：循环任务默认 7 天后自动过期（通过 GrowthBook 可配置），防止遗忘的任务无限运行。

#### 子系统 C：Brief 精简通信模式

源码: `tools/BriefTool/BriefTool.ts`

> 注：BriefTool 的异步消息机制已在 [BriefTool 深度文章](./brieftool-async-user-messages-deep-dive.md) 中详细分析。这里聚焦它在 Kairos 系统中的角色。

在 Kairos 模式下，Brief 不是可选项而是**强制启用**的。系统提示明确告知 Agent：`SendUserMessage` 是回复的唯一通道，工具调用之外的文本输出"仅在用户展开详情时可见——Agent 应假设它不会被阅读"。这从根本上改变了 Agent 的输出行为：从长文本回复变为高信号的短消息检查点。

Kairos 独占工具：

| 工具 | 用途 | 源码位置 |
|------|------|---------|
| SendUserMessage | 非阻塞状态消息推送 | `tools/BriefTool/BriefTool.ts` |
| SendUserFile | 文件/截图/日志推送给用户 | `tools/BriefTool/` |
| PushNotification | 向用户设备发推送通知（超越终端边界） | `tools/BriefTool/` |
| SubscribePR | 订阅并监控 PR 活动（变更、合并、冲突） | Webhook 集成 |

**15 秒阻塞预算**：任何主动行动如果会阻塞用户工作流超过 15 秒，必须延迟执行。这是"有帮助但不烦人"的核心约束。类比：一个好的专业助手只在有价值的信息时才开口，而不是不断汇报"我还在工作"。

#### 子系统 D：Sleep 工具与成本权衡

源码: `tools/SleepTool/prompt.ts`

这是一个从纯源码分析中容易忽略的精妙设计。Sleep 工具的 prompt 明确告知 Agent 成本权衡规则（源码原文："Each wake-up costs an API call, but the prompt cache expires after 5 minutes of inactivity — balance accordingly."）：

- **每次唤醒 = 一次 API 调用**：Agent 每次从 sleep 中醒来都需要一次完整的 API 请求，消耗 token 配额
- **Prompt Cache 过期窗口**：如果 Agent 睡眠超过 ~5 分钟，prompt cache 会过期，下次唤醒需要从零重建整个上下文（成本显著增加）
- **权衡策略**：系统提示告知 Agent 需要平衡"频繁唤醒的高 API 成本"与"过长睡眠导致 cache 失效的重建成本"

```
Sleep 决策矩阵：
┌──────────────┬──────────────────┬────────────────────┐
│ 睡眠时长      │ API 调用成本      │ Cache 状态          │
├──────────────┼──────────────────┼────────────────────┤
│ < 30s        │ 高（频繁调用）     │ ✅ 热 cache         │
│ 30s - 5min   │ 中（合理间隔）     │ ✅ 热 cache         │
│ > 5min       │ 低（调用次数少）   │ ❌ cache 过期重建   │
└──────────────┴──────────────────┴────────────────────┘
```

这种"让 Agent 自己权衡成本"的设计是自治 Agent 的重要特征——Agent 需要理解自己的运行成本，而不是盲目地无限循环。

#### 子系统 E：异步 Agent 派生

源码: `tools/AgentTool/AgentTool.tsx#L566`

```typescript
const assistantForceAsync = feature('KAIROS')
  ? appState.kairosEnabled : false;
```

当 Kairos 活跃时，Agent 工具切换到 fire-and-forget 模式。这解决了一个实际问题：如果 3 个过期的 Cron 任务同时触发，同步执行意味着用户要等第一个完成才能处理第二个。异步派生允许它们并行执行，结果通过 `isMeta` 标记的 prompt 静默回注到主对话流中（对用户不可见，仅供 Agent 理解状态）。

#### 子系统 F：每日日志与审计

源码: `memdir/memdir.ts#L319`, `assistant/sessionHistory.ts`

Kairos 维护 **append-only** 的每日日志文件（``~/.claude/projects/<project>/memory/logs/``），记录观察、决策和行动。这不仅是调试工具，更是自治 Agent 的审计基础设施——当一个 Agent 在用户不在场时执行了操作，事后审计能力至关重要。

这与 autoDream（记忆整合系统）互斥——Kairos 模式使用自己的 disk-skill dream 机制，不走标准的 autoDream 路径：

```typescript
// services/autoDream/autoDream.ts#L96
if (getKairosActive()) return false // KAIROS mode uses disk-skill dream
```

### 4. 遥测与可观测性

Kairos 模式下的所有事件都会被打上 `kairosActive: true` 标签（`services/analytics/metadata.ts#L493`），让 Anthropic 团队可以区分自治模式和交互模式的行为数据：

```typescript
// metadata.ts#L735-736
...(feature('KAIROS') && getKairosActive()
  ? { kairosActive: true as const }
  : {})
```

Cron 任务执行时附带 `cc_workload=cron` 的 billing header（源码: `utils/workloadContext.ts`），供 API 端进行 QoS 路由。这使 Anthropic 的后端可以区分自治任务和用户交互式请求，在高负载时优先保障交互式体验。

### 5. Feature Gate 层级

Kairos 使用了多层 Feature Gate，体现了精细化的功能控制设计：

| Gate | 类型 | 控制范围 | 刷新间隔 |
|------|------|---------|---------|
| `feature('KAIROS')` | 编译时 | 整个 Kairos 系统的 dead code elimination | — |
| `feature('KAIROS_BRIEF')` | 编译时 | Brief 工具独立发布（不依赖完整 Kairos） | — |
| `feature('KAIROS_CHANNELS')` | 编译时 | 通道通信能力 | — |
| `feature('KAIROS_GITHUB_WEBHOOKS')` | 编译时 | GitHub Webhook 订阅 | — |
| `feature('KAIROS_PUSH_NOTIFICATION')` | 编译时 | 设备推送通知 | — |
| `feature('KAIROS_DREAM')` | 编译时 | Dream 记忆整合 skill | — |
| `feature('PROACTIVE')` | 编译时 | 主动行为引擎 | — |
| `tengu_kairos` | 运行时 (GrowthBook) | 用户级开关 | ~5 分钟 |
| `tengu_kairos_cron` | 运行时 (GrowthBook) | Cron 调度器熔断 | 每 tick 检查 |
| `tengu_kairos_cron_durable` | 运行时 (GrowthBook) | 持久化任务存储 | ~5 分钟 |
| `tengu_kairos_cron_config` | 运行时 (GrowthBook) | Jitter 调优参数 | ~5 分钟 |
| `tengu_kairos_brief` | 运行时 (GrowthBook) | Brief 工具熔断 | 5 分钟 TTL |

这种编译时 + 运行时的双层设计值得关注：编译时门控确保外部构建完全不包含 Kairos 代码（zero footprint），运行时门控提供事故期间的即时熔断能力。子特性的独立编译门控（如 `KAIROS_BRIEF`、`KAIROS_PUSH_NOTIFICATION`）允许逐步发布，不必等待整个系统就绪。

## 三、Conway：Kairos 的产品化演进

值得关注的是，Anthropic 正在测试一个名为 **Conway** 的持久化 Agent 平台，它被认为是 Kairos 概念的产品化演进。Conway 提供：

- 专用 Web 界面（Search / Chat / System 三区域布局）
- Webhook 唤醒机制（不依赖 CLI 会话存活）
- Chrome 浏览器交互能力
- 推送通知
- `.cnw.zip` 格式的扩展生态

Conway 的出现意味着 Kairos 的设计思想正在从 CLI 内嵌模式向独立平台方向演进。对于 Qwen Code 来说，这提供了两种可能的实现路径：一是在 CLI 内部集成（Kairos 模式），二是作为独立服务运行（Conway 模式）。

## 四、Qwen Code 的改进路径

### 阶段 0：评估战略定位（P3 优先级）

Kairos 代表的是"CLI Agent → 自治平台"的范式转换。在决定是否实现之前，需要回答几个战略问题：

1. **用户需求验证**：开发者是否真的需要一个"始终在线"的代码 Agent？还是足够快的交互式响应就够了？
2. **基础设施依赖**：Kairos 的价值很大程度上来自 Anthropic 自身的 API 和推送基础设施，第三方实现的体验是否能达到相同水平？
3. **安全风险**：一个不需要用户确认就能主动执行代码的 Agent，安全模型需要重新设计。
4. **成本模型**：持续运行意味着持续消耗 token 配额。Agent 需要内置成本感知能力（如 Sleep 工具的权衡逻辑），而不是盲目运行。

### 阶段 1：Cron 调度器（最高 ROI 子系统）

Cron 调度器是最独立、最高价值的子系统，Claude Code 已经以 `/loop` 命令的形式验证了其可行性：

```typescript
// 建议的最小实现
interface ScheduledTask {
  id: string;
  prompt: string;
  schedule: string;         // Cron 表达式
  recurring: boolean;
  createdAt: string;        // ISO 8601
  expiresAt?: string;       // 自动过期（建议默认 7 天）
  lastRun?: string;
  maxTasks?: number;        // 上限（建议 50）
}

// 持久化到 ~/.qwen/scheduled_tasks.json
// REPL 空闲时检查待执行任务
// 执行时派生 Subagent 处理
```

**关键设计决策**：
- 任务在 REPL 空闲时触发，不在用户输入过程中中断
- 循环任务需要自动过期机制，防止遗忘的任务无限运行
- 需要 Jitter 机制避免雷群效应（如果用户量增长）

### 阶段 2：Brief 通信集成

参考 [BriefTool 深度文章](./brieftool-async-user-messages-deep-dive.md) 的改进路径，为 Qwen Code 增加非阻塞消息通道。这是自治模式的通信基础。

### 阶段 3：Proactive Tick 引擎

实现 idle tick 机制：当用户没有输入时，定期给 Agent 一个"心跳"，让它决定是否需要主动行动。需要配合：
- 15 秒阻塞预算，确保不打扰用户的正常工作流
- Status field 路由，区分主动行为和被动响应
- 成本感知 Sleep 工具，平衡唤醒频率和 API 成本

### 阶段 4：审计日志

实现 append-only 的每日日志系统。对于自治 Agent，事后审计能力不是可选的——用户需要知道"Agent 在我不在的时候都做了什么"。

## 五、改进收益评估

- **实现成本**：极高。Kairos 不是一个功能，而是一个完整的自治框架。完整实现需要 Cron 调度器、Brief 通信模式、异步 Agent 派生、Sleep 成本控制器、安全 sandbox 升级、Feature Gate 系统等多个模块协同。估计 5000+ 行代码。但可以分阶段发布——Claude Code 已经验证了这种渐进式路径。
- **战略价值**：
  1. **差异化竞争**：目前没有任何开源 CLI Agent 实现了类似的自治模式，率先推出将形成显著的产品差异化。
  2. **平台化基础**：Kairos 是将 CLI Agent 从"工具"升级为"平台"的关键基础设施，为 PR 监控、CI 集成、定时维护等高价值场景打开大门。
  3. **生态拉动**：自治模式天然需要更多的 Hook、Skill、MCP 服务器来发挥价值，会强力拉动插件生态发展。
  4. **已验证的发布路径**：`/loop` → `/schedule` → Kairos → Conway 的渐进式路径已经被 Anthropic 验证，降低了实施风险。
- **风险**：
  1. 安全模型复杂度显著增加——自治 Agent 的权限边界远比交互式 Agent 难以定义。
  2. API 成本可能成为用户痛点——持续运行意味着持续消耗 token 配额。需要像 Sleep 工具那样内置成本感知。
  3. 调试难度大幅上升——异步、定时、主动行为的组合让问题追踪变得困难。审计日志是必须的。

## 六、与现有深度文章的关系

| 相关文章 | 关联点 |
|---------|-------|
| [BriefTool 异步消息](./brieftool-async-user-messages-deep-dive.md) | Kairos 的通信子系统 |
| [Feature Gates](./feature-gates-deep-dive.md) | Kairos 的门控基础设施 |
| [会话后台化](./session-backgrounding-deep-dive.md) | 后台运行能力 |
| [Fork Subagent](./fork-subagent-deep-dive.md) | 异步 Agent 派生机制 |
| [命令队列编排](./command-queue-orchestration-deep-dive.md) | 任务排队与优先级 |
| [记忆系统](./memory-system-deep-dive.md) | Daily Log 与 autoDream 的互斥关系 |
| [远程控制 Bridge](./remote-control-bridge-deep-dive.md) | Kairos 启用时自动激活 Bridge |
| [PR Webhook 事件订阅](./pr-webhook-event-subscription-deep-dive.md) | SubscribePR 工具的底层机制 |
| [成本与 Fast Mode](./cost-fastmode-deep-dive.md) | cc_workload=cron 的 QoS 分级 |

### 替代模式：Multica Daemon

[Multica](https://github.com/multica-ai/multica)（`server/internal/daemon/`，~5,600 行 Go，含 execenv/repocache/usage 子模块）采用了不同于 Kairos 的自治 Agent 模式：

| 维度 | Kairos（Claude Code） | Multica Daemon |
|------|---------------------|---------------|
| 触发方式 | Cron 定时 + PR 事件 | 后台轮询服务器任务队列 |
| 任务来源 | 自主发现（PR、Issue、定时维护） | 平台分配（Issue Board 上人类指派） |
| Agent 编排 | 单 Agent + 异步派生 | 多 Agent 统一 Backend（Claude/Codex/OpenClaw/OpenCode） |
| 状态管理 | Brief 模式（通知 + 睡眠） | 数据库任务状态机（enqueue→claim→start→complete/fail） |
| 安全 | sandbox + 权限升级 | Secret Redaction（输出脱敏） |
| 适用场景 | 个人开发者自治 | 团队协作管理（"AI 版 Linear"） |

对 Qwen Code 的启发：如果目标是**团队场景**（多人 + 多 Agent 协作），Multica 的 Daemon 轮询模式比 Kairos 的 Cron 模式更合适；如果目标是**个人自治**，Kairos 的事件驱动模式更轻量。

### 替代模式：Hermes Agent 的闭环学习 + 后台 Review 子代理

[Hermes Agent](../tools/hermes-agent/)（Nous Research，Python 369K 行）采用了第三种"Always-On" 范式：**基于双计数器 Nudge 的后台学习 review 子代理**。它不是 Kairos 那样的"按时/按事件触发"的独立 Agent，也不是 Multica 那样的"轮询任务队列"的 daemon，而是**会话内触发的 post-response review 后台子代理**。

| 维度 | Kairos（Claude Code） | Multica Daemon | Hermes Review 子代理 |
|------|---------------------|---------------|---------------------|
| 触发方式 | Cron 定时 + PR 事件 | 后台轮询服务器任务队列 | **双计数器**（用户回合数 ≥10 / 工具调用数 ≥10） |
| 任务来源 | 自主发现（PR、Issue、定时维护） | 平台分配 | 会话本身（学习闭环） |
| 运行时机 | 独立周期性 | 独立轮询 | **主响应送出后异步**（不抢主任务注意力） |
| 状态管理 | Brief 模式 | 数据库任务状态机 | 共享 memory_store + `nudge_interval=0` 防递归 |
| 运行时长上限 | 无（长任务） | 无 | **`max_iterations=8`**（严格短任务） |
| 用户可见性 | 通知 + 睡眠 | 任务状态面板 | 一行 `💾 Skill 'xxx' created` |
| 适用场景 | 个人开发者长期自治 | 团队 AI-Linear | **会话内持续学习** |

**三种范式的互补性**：
- Kairos = **"做事"**的自治（定时维护、PR 审查、issue 分类）
- Multica = **"分派"**的自治（任务队列 → 多 Agent Backend）
- Hermes Review 子代理 = **"学习"**的自治（从对话中沉淀 memory/skill）

这三者可以**同时存在**：qwen-code 若要实现完整的自治能力，应参考三者不同的设计原则——Kairos 的事件触发、Multica 的任务分派、Hermes 的会话内学习。详见 [闭环学习系统深度对比](./closed-learning-loop-deep-dive.md) 和 [Hermes Agent 闭环学习实现](../tools/hermes-agent/03-closed-learning-loop.md)。
