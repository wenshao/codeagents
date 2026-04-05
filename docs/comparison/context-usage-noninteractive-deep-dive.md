# Qwen Code 改进建议 — `/context` 非交互输出与自动化上下文诊断 (Non-Interactive Context Usage)

> 核心洞察：Qwen Code 已经具备很完整的交互式 `/context` 能力，能细分 system prompt、tools、skills、memory、MCP tools 等 token 占用；但它没有像 Claude Code 那样把这套能力暴露到 non-interactive / automation surface。结果是：人可以在 TUI 里看 context，脚本、CI、基准测试和外部控制器却无法稳定获取同一份上下文诊断数据。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、问题定义：Qwen 已有“看板”，但没有“自动化出口”

在日常交互中，`/context` 是非常有价值的诊断命令：
- 当前会话已经消耗多少 tokens？
- 开销主要来自消息历史、system prompt、memory，还是 tools？
- MCP tools 和 skills 是否把上下文窗口挤爆了？
- 自动压缩阈值、buffer 剩余空间是否合理？

这些信息不仅对终端里的单个用户有用，也对以下场景很重要：

| 场景 | 为什么需要非交互 `/context` |
|------|-----------------------------|
| CI / nightly regression | 比较不同版本的 prompt 体积、tool schema 膨胀、上下文策略变化 |
| benchmark / profiling | 批量采集 context usage，验证某次改动是否提升缓存命中或减少 token 开销 |
| IDE / 外部 controller | 在 GUI 面板中展示当前 session 的 context health，而不是要求用户手动输入 `/context` |
| 故障排查 | 复现“为什么这次更容易压缩 / 截断 / 变慢”时，需要结构化输出用于归档 |

Qwen Code 目前的问题不是“没有 `/context`”，而是“`/context` 主要停留在交互式 TUI 命令层”。

---

## 二、Claude Code 的做法：同一套分析能力，同时服务交互和自动化

Claude Code 将 `/context` 拆成两层：

1. **交互式命令实现**：`commands/context/context.tsx`
2. **非交互实现**：`commands/context/context-noninteractive.ts`

这不是简单重复实现，而是把“上下文分析”抽成共享的数据采集路径，然后分别渲染成：
- TUI/ANSI 输出（给终端用户）
- Markdown 表格或结构化文本（给脚本、SDK、外部控制器）

### 1. 共享的数据采集路径

Claude Code 在 `commands/context/context-noninteractive.ts` 中定义了 `collectContextData()`，显式说明它会复用 `/context` 与 SDK `get_context_usage` 的同一条数据采集链路：

```ts
/**
 * Shared data-collection path for `/context` (slash command) and the SDK
 * `get_context_usage` control request.
 */
```

这意味着 Claude 的 context 诊断不是“一个 UI 小功能”，而是**平台能力**：
- 本地 slash command 可调用
- 非交互命令可调用
- SDK / remote control 也能复用

### 2. 输出格式适合自动化消费

`formatContextAsMarkdownTable()` 会把结果整理成稳定的 Markdown 表格，包括：
- 总 tokens / context window / 百分比
- category 分解
- MCP tools 明细
- custom agents / skills / memory files
- system prompt sections（特定构建下）

对于 CLI 自动化来说，这种“稳定表格 + 统一字段名”的输出非常关键，便于：
- 保存基线
- 版本 diff
- 被外部脚本二次解析

### 3. 与控制协议联动

Claude Code 还把同一能力暴露给 SDK 控制请求 `get_context_usage`。这使得 IDE、桥接器、远程控制面板都能复用 context usage，而不用自行模拟 `/context` 命令 UI。

**源码参考**：
- Claude Code：`commands/context/context.tsx`
- Claude Code：`commands/context/context-noninteractive.ts`

---

## 三、Qwen Code 现状：交互分析很细，但 non-interactive 白名单没有放行 `/context`

Qwen Code 的交互式 `/context` 实现其实已经相当完整。

### 1. `/context` 命令本身很强

`packages/cli/src/ui/commands/contextCommand.ts` 展示出 Qwen 已经做了很多细粒度统计：
- `system prompt` tokens
- 全部 tool declarations tokens
- built-in tools / MCP tools 明细
- `memory` 文件解析与估算
- skills listing + loaded body tokens
- autocompact buffer
- API 实测 prompt tokens / cached content tokens

从实现深度上看，Qwen 的 `/context` 已经不是“只显示一个总 token 数字”的轻量功能，而是一套完整的上下文成本分析器。

### 2. 但 non-interactive mode 有显式白名单

问题出在 `packages/cli/src/nonInteractiveCliCommands.ts`。

该文件定义了 `ALLOWED_BUILTIN_COMMANDS_NON_INTERACTIVE`：

```ts
export const ALLOWED_BUILTIN_COMMANDS_NON_INTERACTIVE = [
  'init',
  'summary',
  'compress',
  'btw',
  'bug',
] as const;
```

这意味着：
- `/context` 虽然是 built-in command
- 但在 non-interactive mode / ACP non-interactive 路径中，它不会被加入允许列表
- `filterCommandsForNonInteractive()` 只会保留白名单中的 built-in commands

也就是说，Qwen 当前的设计实际上把 `/context` 限定在交互式 TUI 里。

### 3. 文档层也强化了这个现状

`docs/users/features/commands.md` 确实把 `/context` 列为常规 slash command，但文档并未说明它可用于 non-interactive automation；同一页对 `/btw` 则明确列出了：
- Interactive
- Non-interactive
- ACP

这说明 Qwen 在产品定义上已经区分“哪些命令可自动化调用”，而 `/context` 还没有进入这一级能力面。

**源码参考**：
- Qwen Code：`packages/cli/src/ui/commands/contextCommand.ts`
- Qwen Code：`packages/cli/src/nonInteractiveCliCommands.ts`
- Qwen Code：`docs/users/features/commands.md`

---

## 四、差距本质：不是缺功能，而是缺“平台级复用出口”

这个差距非常典型，也很有代表性。

| 维度 | Claude Code | Qwen Code |
|------|-------------|-----------|
| 交互式 `/context` | 有 | 有 |
| 非交互 `/context` | 有 | 无 |
| 共享分析数据路径 | 有 | 部分有，但主要绑定在 slash command UI 层 |
| 对外控制协议复用 | 有 `get_context_usage` | 暂无同等级 evidence |
| 自动化友好输出 | Markdown 表格 / 控制请求 | 交互式展示为主 |

所以问题不是“Qwen 缺少 context 诊断”，而是：

> **Qwen 已经实现了 context 分析引擎，但还没有把它产品化为脚本、CI、ACP controller 可消费的接口。**

这类差距往往比“从 0 到 1 新增功能”更值得优先补齐，因为：
- 底层分析能力已经存在
- 风险相对较低
- 收益可直接覆盖文档、测试、性能分析、外部集成多条产品线

---

## 五、Qwen Code 的改进路径

### 阶段 1：放开 non-interactive 白名单（最低成本版本）

最直接的路径，是先把 `/context` 加入 `ALLOWED_BUILTIN_COMMANDS_NON_INTERACTIVE`：

```ts
export const ALLOWED_BUILTIN_COMMANDS_NON_INTERACTIVE = [
  'init',
  'summary',
  'compress',
  'btw',
  'bug',
  'context',
] as const;
```

然后让 `/context` 在 non-interactive 模式下返回：
- 单次 `message`
- 或稳定的 `stream_messages`
- 最好支持表格 / JSON 两种输出

这样最短路径就能覆盖：
- `qwen --prompt "/context"`
- ACP 非交互场景
- 文档/脚本采集

### 阶段 2：抽取共享 `collectContextUsage()` 服务

更合理的工程化做法，是把 `contextCommand.ts` 中的数据收集逻辑再进一步下沉：
- CLI slash command 负责展示
- non-interactive command 负责结构化输出
- IDE / ACP / 未来 remote control 直接复用同一个 service

建议抽象为：

```ts
interface ContextUsageSnapshot {
  model: string;
  totalTokens: number;
  contextWindowSize: number;
  categories: Array<{ name: string; tokens: number }>;
  builtinTools: Array<{ name: string; tokens: number }>;
  mcpTools: Array<{ name: string; tokens: number }>;
  skills: Array<{ name: string; tokens: number; loaded: boolean }>;
  memoryFiles: Array<{ path: string; tokens: number }>;
  autocompactBuffer: number;
}
```

这会让 `/context` 从“命令”升级为“可嵌入的诊断 API”。

### 阶段 3：补充 JSON 输出，服务基准测试与外部面板

Markdown 表格适合人读，但真正的自动化往往更需要 JSON。

建议新增：
- `/context --json`
- 非交互 `--output-format json`
- 或 ACP control request：`get_context_usage`

这样可以直接支持：
- CI 基线快照
- 回归趋势图
- IDE 状态面板
- benchmark harness 自动采集

### 阶段 4：把 context health 与告警系统打通

一旦 `/context` 可自动化输出，Qwen 就能很自然地追加：
- 超过 80% 时发 warning
- 某 MCP server 突然引入 20k tokens 时提示“tool schema 膨胀”
- 某次扩展安装导致 skill/tool/memory 开销异常增大时，自动生成诊断建议

这会把 `/context` 从“查询命令”升级为“context observability 基础设施”。

---

## 六、实现成本与优先级判断

### 实现成本

这个改动的成本大概率是 **小到中**：

1. **最低可用版本**：只放开白名单并适配返回类型，成本很低。
2. **工程化版本**：抽取共享 service + JSON 输出，中等成本。
3. **平台化版本**：再接 IDE / ACP / controller，成本继续上升。

但无论哪一层，门槛都明显低于：
- 新做一个远程控制系统
- 新做 worktree 工作流
- 新做浏览器集成

因为 Qwen 已经有了最关键的“上下文分析逻辑”。

### 优先级建议

建议列为 **P2**：
- 不属于阻塞主流程的 P0/P1
- 但它对基准测试、自动化、集成生态都非常有价值
- 而且实现收益比高，适合做成一项“低风险、高复用”的质量型改进

---

## 七、对用户的直接收益

如果 Qwen Code 补齐 non-interactive `/context`，用户可立即获得以下收益：

1. **CI 可观测性增强**  
   每次发版都能自动记录 context usage，及时发现 prompt/tool schema 膨胀。

2. **性能回归更容易定位**  
   当用户抱怨“为什么这版更慢 / 更容易压缩”时，可以直接用脚本抓 context snapshot 做前后对比。

3. **IDE / GUI 集成更自然**  
   未来无论是 VS Code companion、ACP 客户端还是 web dashboard，都不需要重新发明一套 context 统计逻辑。

4. **文档与教程更可验证**  
   本仓库这类源码对比文档可以直接引用自动化输出，而不是依赖手工截图或交互录屏。

---

## 八、结论

Qwen Code 在 `/context` 上已经完成了“分析能力”这一步，但还没有完成“自动化出口”这一步。

Claude Code 的启发不在于它把 `/context` 做得更花哨，而在于它把同一套上下文诊断能力同时暴露给：
- 交互式命令
- 非交互命令
- SDK / 控制协议

对 Qwen Code 来说，这是一类非常典型、非常值得优先补齐的产品化差距：

> **已有强分析引擎，但缺少 non-interactive / controller-friendly 的统一导出层。**

一旦补上，Qwen 的 `/context` 就不再只是给终端用户临时查看的命令，而会成为整个 Qwen CLI / IDE / ACP 生态的基础诊断接口。

---

## 关键源码索引

### Claude Code
- `commands/context/context.tsx`
- `commands/context/context-noninteractive.ts`

### Qwen Code
- `packages/cli/src/ui/commands/contextCommand.ts`
- `packages/cli/src/nonInteractiveCliCommands.ts`
- `docs/users/features/commands.md`

> **免责声明**：以上结论基于 2026-04 本地源码对比，后续版本可能已变更。