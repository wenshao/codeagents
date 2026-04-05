# Qwen Code 改进建议 — SDK 双向控制协议 (SDK Bi-directional Control Protocol)

> 核心洞察：当我们把视线拔高，试图将 CLI Agent 包装为一个个底层的可被 IDE（比如 VS Code 插件）或其他大语言模型流水线调用的 SDK 节点时，普通的“单向文本输入/输出”就显得极其捉襟见肘了。外部消费者（SDK Consumer）往往需要精细控制这个内部引擎：比如强行塞给它一个初始缓存状态，或者在运行中途拦截它的危险操作并注入审批结果。Claude Code 在其 `entrypoints/sdk/` 下设计了一套庞大、完备且基于事件驱动的“双向 NDJSON 控制协议（Bi-directional Control Protocol）”；而 Qwen Code 目前在作为 SDK 时缺乏足够的掌控感。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、把 Agent 降级为组件时的“提线困境”

### 1. Qwen Code 现状：松散与不可控的暴露面
在很多开源项目的早期架构中，如果你想在自己的代码里通过 `import { Agent } from 'qwen-code'` 来使用它：
- **痛点一（权限无法外包）**：如果在 IDE 插件里跑 Agent，Agent 想改文件，它默认会在标准输出（stdout）打印 `[Y/n]`。但 IDE 没有终端！如果你想在 IDE 里弹出一个精美的原生 UI `YES/NO` 按钮来接管这个控制权，Agent 底层并没有暴露出这样的双向桥接回调。
- **痛点二（硬状态缺乏干预）**：如果你想从外部直接打断（Interrupt）它的长考，或者在运行前通过某种协议提前将刚才用户在 IDE 里打开的文件列表注入（Seed Context）进去，现有的单向 API 是无能为力的。

### 2. Claude Code 的极客解法：NDJSON 双向控制总线
Claude Code 为了完美适配自家各种网页版产品和极客调用，设计了超过 20 种强类型控制结构（定义在 `entrypoints/sdk/controlSchemas.ts` 等文件）。

#### 机制一：CLI 到 SDK 的权限反转回调 (`can_use_tool`)
当作为 SDK 包被包裹在另一层 UI 里（比如通过 IPC/Stdio 通信的 IDE 插件）执行时，如果大模型触发了危险动作：
1. 引擎内部（CLI 端）挂起，并通过事件总线向外面的宿主（SDK 端）喷出一条特殊的 JSON 控制事件：
   `{"type": "control_request", "action": "can_use_tool", "tool": "bash", "args": "rm -rf"}`
2. 引擎在这里静默 `await`。
3. 外面的 IDE 收到 JSON 后，弹出了精美的按钮。用户点击拒绝。
4. IDE 通过相同的控制总线，向引擎内喷入响应：
   `{"type": "control_response", "id": "123", "decision": "deny"}`
5. 引擎内部收到响应，瞬间唤醒，对大模型抛错继续。实现了权限的完美外包！

#### 机制二：SDK 到 CLI 的上帝模式干预 (God Mode Interventions)
外部的宿主拥有像“上帝”一样的控制权。宿主可以随时向下抛送以下指令：
- `{"type": "set_model", "model": "haiku"}`：运行中途强行把引擎底层模型替换。
- `{"type": "seed_read_state", "files": [...]}`：利用外部手段极速把某些状态压入到引擎的 `fileReadCache` 里，消除重复读取时间。
- `{"type": "interrupt"}`：从外部注入系统级的致命中断，直接熔断底层的 AbortController 停止耗钱的大模型 API。

## 二、Qwen Code 的改进路径 (P2 优先级)

让工具从“一个只能手点的玩具”变成“可被无缝编排的终极武器”。

### 阶段 1：重构 `agent-events.ts` 提升为控制协议
1. 将目前系统内部散落的事件通知，统一抽象收拢。
2. 建立两套明确的 Schema（如利用 `zod` 校验）：
   - `AgentToHostEvent`：包含运行状态更新、需要宿主解决的权限审批（`PermissionRequest`）、中间结果。
   - `HostToAgentCommand`：包含中断（`Interrupt`）、权限批准（`PermissionResponse`）、参数热更（`SetVariable`）。

### 阶段 2：开发挂起与回调代理 (Bridging Promise)
1. 在 `packages/core/src/core/` 实现一个 `ControlBus` 模块。
2. 当内部运行到类似 `ask_user` 或需要沙盒审查的节点时：
   将传统调用 `inquirer.prompt` 或 Ink 输入框的逻辑，通过一层 `Adapter` 包装。如果处于 SDK 模式，直接把请求包装成 `AgentToHostEvent` 发射出去，并生成一个悬而未决的 Promise 等待对应 ID 的 `HostToAgentCommand` 降临来 `resolve`。

### 阶段 3：对外暴露标准化 SDK 接口
对于引入 NPM 包的二次开发者，提供如下丝滑体验：
```typescript
const qwen = new QwenCodeAgent({ mode: 'controlled' });

// 接管所有的危险工具审批
qwen.on('permission_request', async (req, resolve) => {
    const isSafe = await myCustomUIPrompt(req.toolName);
    resolve(isSafe ? 'allow' : 'deny');
});

// 在外部按钮按下时强制中断
document.getElementById('stop').onclick = () => qwen.interrupt();

qwen.run("帮我改下全栈的代码");
```

## 三、改进收益评估
- **实现成本**：高。不仅需要重构底层的大量控制反转（Inversion of Control），更要保证所有的异步锁（Locks / Promises）不发生内存泄漏或永久死锁。
- **直接收益**：
  1. **IDE 生态的绝对基础**：没有这个强控制协议，就几乎不可能开发出一个交互良好的 VS Code 或 JetBrains 的 GUI 插件版本。
  2. **解锁 CI 深度编排**：使得其他系统可以利用这些 JSON 流，将几十个不同的 Qwen Code 实例像 Kubernetes 编排 Pod 一样精准调遣。