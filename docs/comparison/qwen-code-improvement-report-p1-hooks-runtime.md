# Qwen Code 改进建议 — P1 Hook Runtime 扩展

> Hook 运行时改进项：从 shell command-only 扩展到多后端执行模型，支持 Prompt Hook、异步 Hook 编排与更强的语义策略能力。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Prompt Hooks / LLM 语义 Hook（P1）

**思路**：当前 Qwen Code 的 Hook 已有较完整的事件总线（`PreToolUse`、`PostToolUse`、`Notification`、`SessionStart` 等），但执行器本质上仍只有 `type: "command"`——所有 Hook 都必须落到 shell 命令。这样虽然足够通用，却不适合“语义判断”类场景：例如“这次 `git push` 是否违反团队发布策略？”、“本次工具调用是否与当前任务目标冲突？”、“这段用户输入是否包含敏感数据，应该先二次确认？”。

Claude Code 在 shell / HTTP 之外，还支持 **Prompt Hook**：把 Hook prompt 连同当前上下文交给一个小模型执行，要求模型返回严格 JSON（`{ok:true}` 或 `{ok:false, reason:"..."}`）。这使 Hook 从“脚本式规则”扩展为“语义策略判断器”。适合 shell/regex 难以表达的治理场景。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/hooks/execPromptHook.ts` | `execPromptHook()`，调用小模型执行 Hook prompt，强制 `json_schema` 输出 |
| `types/hooks.ts` | Hook 类型体系、sync/async JSON 响应协议、Prompt/Callback Hook 类型定义 |
| `utils/hooks/AsyncHookRegistry.ts` | 异步 Hook 注册、进度轮询、stdout JSON 响应解析 |

**Qwen Code 现状**：Hook 类型仍是单一 `command`。`packages/core/src/hooks/types.ts` 中 `HookType` 仅有 `Command`，`HookConfig = CommandHookConfig`；`packages/core/src/hooks/hookRunner.ts` 也只实现 `executeCommandHook()`。这意味着即使事件体系很丰富，运行时仍局限于 shell 脚本 + stdin/stdout JSON。

**Qwen Code 修改方向**：
1. `packages/core/src/hooks/types.ts` 扩展 `HookType`：在 `command` 之外新增 `prompt`（后续也可继续扩展 `http`、`callback`）；
2. 新建 `packages/core/src/hooks/execPromptHook.ts`：复用现有模型调用栈，采用小模型执行 Hook prompt；
3. 要求 Prompt Hook 输出严格 JSON Schema，避免自由文本导致的不确定性；
4. 在 `hookRunner.ts` 增加分发逻辑：`type === 'prompt'` 时走 LLM Hook 分支；
5. 在 `hooksCommand.ts` / Hook UI 中展示 Hook 类型、模型、超时与阻断原因。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~250 行
- 开发周期：~3 天（1 人）
- 难点：Hook prompt 的安全边界与超时控制

**改进前后对比**：
- **改进前**：Hook 只能执行 shell 命令——复杂语义检查需要开发者自己写脚本、调用外部模型、再拼 JSON 返回
- **改进后**：`type: "prompt"` 直接把语义判断下沉到 Hook Runtime——可用小模型做轻量审批、策略校验、提示增强

**意义**：很多治理策略本质是语义问题，而不是字符串匹配问题。
**缺失后果**：复杂 Hook 只能壳套壳——shell 调脚本，脚本再调模型，配置脆弱且调试困难。
**改进收益**：Prompt Hook 让 Hook 成为一等语义策略层——更适合审批、安全、规范、上下文增强。

---

## 为什么这不是现有“HTTP Hooks / Conditional Hooks”的重复

- **Conditional Hooks** 解决的是“哪些 Hook 应该触发”；
- **HTTP Hooks** 解决的是“Hook 是否可以直接请求远程服务”；
- **Prompt Hooks / Hook Runtime 扩展** 解决的是“Hook Runtime 本身是否支持多执行后端，尤其是 LLM 语义执行”。

三者分别对应 **触发条件**、**传输通道**、**执行模型**，不是同一个层次的问题。

---

## 进一步演进方向

如果后续继续向 Claude Code 靠拢，Qwen Code 的 Hook Runtime 可以按下面路径递进演化：

| 阶段 | 能力 | 说明 |
|------|------|------|
| Stage 1 | `command` + `prompt` | 本地脚本与 LLM 语义判断双后端 |
| Stage 2 | 统一 async registry | 所有 Hook 类型共享异步调度、超时、进度与结果回传 |
| Stage 3 | typed hook backends | `http` / `callback` / `remote-policy` 等可插拔执行器 |
| Stage 4 | explainability | 展示“哪个 Hook 阻断了继续执行、原因是什么、来自哪层策略” |

这样 Hook 系统才能从“事件很多的 shell 执行器”升级为“可扩展的策略运行时”。

---

## 相关文章

- [Hook/插件扩展深度对比](./hook-plugin-extension-deep-dive.md)
- [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)
