# Qwen Code 改进建议 — 启动优化 (API Preconnect & Early Input)

> 核心洞察：作为高频使用的 CLI 工具，开发者对“从按下回车到能敲下第一个字母”的微小延迟极其敏感。传统 Node.js 应用启动慢（加载模块、初始化 UI）、大模型首次 API 请求慢（建立底层的 TLS 与网络握手）往往会让用户感觉“工具很笨重”。Claude Code 在这方面通过两个不显眼但极具技术深度的底层优化：`TCP Preconnect`（提前预热网络隧道）和 `Early Input Capture`（启动期盲打拦截），硬生生把用户的“体感延迟”抹到了负数；而 Qwen Code 目前在冷启动阶段完全是阻塞干等状态。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、冷启动期间的两大“体感断层”

### 1. Qwen Code 的现状
当开发者在终端中敲下 `qwen-code` 并按下回车时，主要发生两件事：
- **痛点一（启动期键盘敲击丢失）**：程序需要 500ms 左右去加载巨大的 AST 库、读取各种本地配置文件、初始化 Ink UI 组件。这段时间如果用户打字，终端的回显（Echo）是错乱的，且当 UI 真正渲染出来时，用户刚刚敲的字全没了，只能被迫删掉重打。
- **痛点二（首个 Prompt 响应奇慢）**：UI 出来后，用户输入了第一句话并发送。此时底层的 Axios/Fetch 才慢吞吞地发起 DNS 解析 -> TCP 三次握手 -> TLS 证书交换 -> SSL 握手。这个纯网络底层的初始化至少需要 200-500ms 额外的时间，导致第一句话的回复比后续的对话慢得多。

### 2. Claude Code 解决方案：榨干每一毫秒的间隙
Claude Code 在其核心架构中（`services/api/claude.ts` 以及 `utils/earlyInput.ts`）运用了操作系统级别的极客优化。

#### 机制一：TCP Preconnect (预先建立隧道)
在 CLI 的最外层入口（`entrypoints/cli.tsx` 的前几行代码中），系统甚至还没开始去读取复杂的配置文件，就直接调用了一个 `preconnect()` 函数。
```typescript
// 伪代码思路
fetch("https://api.anthropic.com/", { method: "HEAD" }).catch(() => {});
```
这个极其廉价的 HTTP HEAD 请求不关注响应，它的唯一作用是逼迫操作系统的网络栈提前把通向大模型 API 网关的 TCP 和 TLS 隧道搭好。
当 1 秒后用户真正按下回车发送复杂的 Payload 时，底层复用了这个已经握手成功的 Socket，首 Token 延迟瞬间降低几百毫秒。

#### 机制二：Early Input Capture (早鸟按键捕获)
为了解决 Node.js 加载庞大模块导致的 500ms “打字盲区”，Claude Code 引入了 `startEarlyInputCapture()`。
1. 在进程刚诞生的最初 10 毫秒，它立刻通过原生的系统调用，强行把 `process.stdin` 切入 `raw mode`，并挂上极轻量级的事件监听器。
2. 此时主线程在拼命解析臃肿的 TypeScript / React Ink 库。
3. 任何用户的键盘敲击（即使包括回删 Backspace 等控制字符）都会被这个轻量拦截器录制下来存进缓冲数组。
4. 500ms 后，React Ink 组件 `PromptInput` 终于加载并挂载完毕。它会调用 `useEarlyInput()` 一口吞下刚才缓冲的所有字符，瞬间预填充到输入框内。

**效果**：用户敲下命令，立刻开始盲打输入问题，哪怕前 0.5 秒屏幕什么都没刷出来，等画面一亮，自己敲的字已经完美躺在输入框里！这种“人不用等机器”的体验极其超前。

## 二、Qwen Code 的改进路径 (P1 优先级)

天下武功唯快不破，优化冷启动是建立技术口碑的最快途径。

### 阶段 1：实现 API 预热 (Preconnect)
1. 在 `packages/core/src/cli.ts` 顶层，提取模型配置 Endpoint URL。
2. 只要探测到非单纯的打印帮助 (`-h`) 模式，立刻 `fire-and-forget` 抛出一个空的探活请求（或 Socket 建连）。由于 Qwen API 通常在国内，这能消除建立连接的 50ms-150ms 开销。

### 阶段 2：开发 `earlyInput.ts`
1. 编写一个无外部依赖的 `earlyInput.ts`。暴露 `startCapture()` 和 `consumeBuffer()`。
2. 在 `bin/qwen-code` 最开头直接加载并运行 `startCapture()`。利用 `readline.emitKeypressEvents` 缓冲按键。

### 阶段 3：与 React UI 对接
1. 修改 UI 层的 `InputComponent`。
2. 在 `useEffect` 挂载完成的那一刻，消费 `earlyInput` 的缓冲区，并在状态机中把它设为当前的初始值 `setInputValue(buffer)`。
3. 记得消费完后交还终端控制权并关闭 `raw mode` 的早鸟拦截，平滑过渡给标准的 Ink 终端控制。

## 三、改进收益评估
- **实现成本**：低到中等。代码量在 200 行以内，但在处理跨平台终端事件（尤其是 Windows 的 Command Prompt）时需要非常仔细的测试。
- **直接收益**：
  1. **断崖式提升“顺滑感”**：消除由于前端运行时臃肿带来的负面体验，实现打字“零等待”。
  2. **消除网络握手时延**：使用户对大模型首个问题的响应速度感观大幅加快。