# Qwen Code 改进建议 — Speculation 投机预测执行默认启用 (Speculative Execution)

> 核心洞察：大语言模型的推理速度（Tokens per Second）是目前的硬瓶颈，而在多步自动化任务中，网络延迟（TTFT）加上模型推理时间，常常让开发者在两次确认之间等待数秒。为了掩盖这种物理延迟，让用户产生“无缝响应”的错觉，现代 AI 架构引入了极其前沿的 `Speculation（投机/预测执行）` 机制。即：在等待人类敲击回车（或 Tab 接受建议）的间隙，后台已经偷偷把大模型请求发出去甚至把命令跑完了。Claude Code 和 Qwen Code 虽然在底层都实现了这套机制，但 Claude Code 将其视为默认的核心提速引擎；而 Qwen Code 目前受限于安全性评估，此功能仍是默认关闭且场景受限的隐藏选项。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么“等模型思考”极其破坏心流？

### 1. Qwen Code 现状：串行阻塞交互
在目前的标准交互模式下：
1. Agent 跑完一个脚本后，觉得应该跑一下单元测试，于是在屏幕上打出建议：`Would you like to run 'npm test'? [Press Tab to accept]`
2. 此时，Agent 的后台引擎进入休眠，静静等待。
3. 用户看了一秒钟，按下了 `Tab` 和 `Enter`。
4. Agent 这才开始将刚才的意图组装成 Prompt 发往大模型 API（耗时 2-5 秒）。
5. 模型返回 JSON 调用 `BashTool`。
6. `BashTool` 启动跑完测试。
**痛点**：对于这句用户 99% 会同意的“废话式交互”，用户在按下回车后，被强行要求盯着屏幕的 Spinner 干等好几秒，这种“打断感”是连续沉浸式编程的致命伤。

### 2. Claude Code 解决方案：时间旅行般的“零延迟”
在 Claude Code 的 `services/PromptSuggestion/speculation.ts` 源码中，作者实现了一套极其激进的“偷跑”架构。

#### 机制一：后台静默抢跑 (Background Speculation)
当终端刚打出 `[Press Tab to accept]` 提示的瞬间，大模型后台并没有闲着。它假设用户**一定会按 Tab**，所以它不仅把提示发给了 UI，同时还立刻在后台发起了一次针对这个选项的 API 推理调用，甚至在内存的虚拟文件系统（Overlay FS）沙盒里把工具给跑了。

#### 机制二：瞬间的未来兑现 (Instant Materialization)
当用户思考了 3 秒钟后按下 `Tab` 接受时，后台的那个 API 请求刚好跑完或者快跑完了。系统会立刻从 `Speculation Task` 中把已经计算好的未来结果提取出来瞬间刷入终端！
给用户的震撼体验是：**刚按下确认，结果瞬间弹出来了！延迟被降维打击到了 0 毫秒。**

#### 机制三：投机废弃与并行流水线 (Pipeline Abandonment)
如果用户没有按 `Tab` 而是自己输入了别的字母，系统就会像没事人一样，立刻 `abort` 杀掉后台那个预测请求，这仅仅浪费了一点极小的 Token 费用，却换来了 90% 场景下巨大的时间节约。

## 二、Qwen Code 的改进路径 (P1 优先级)

Qwen Code 已经在底层包含了 Overlay 文件系统，现在的关键是将这把“法拉利钥匙”交给用户。

### 阶段 1：开启全局 Flag
1. 在 `packages/core/src/config/` 等核心配置中，将 `enableSpeculation` 参数默认设置为 `true`。
2. 确保在首屏或者 `/settings` 菜单中增加一个开关 `[x] 启用预测加速`，方便极少部分对 Token 费用极其敏感的用户将其关闭。

### 阶段 2：扩大 Safe Tools 白名单
投机执行最大的风险在于“副作用（Side Effects）”。如果模型偷偷去执行了 `rm -rf`，这是不能接受的。
1. 审查现有的 `speculationToolGate` 拦截器。
2. 将所有纯“读取（Read-only）”的工具全量加入白名单（如 `read_file`, `grep`, `ls`, `cat` 等）。
3. 甚至可以引入基于 AST 分析的只读验证，在确保绝对没有文件修改风险的前提下，允许更多的复杂探索命令进入后台预测池。

### 阶段 3：配合流水线级联预测 (Pipelined Speculation)
一旦用户同意了当前的猜测（比如允许跑测试），此时测试可能还要跑两秒。在此期间，再利用闲置算力，提前请求大模型的**下下一轮建议**（比如“是否将报错提交修复”），让快感产生连击。

## 三、改进收益评估
- **实现成本**：极低。由于 Qwen Code 的历史贡献者已经把最难的 Overlay FS 沙盒做完了，现在只是进行业务层的解锁与配置重写，代码量几十行。
- **直接收益**：
  1. **碾压级的交互响应速度**：让 Qwen Code 的日常“闲聊+确认”操作彻底告别 Spinner 等待，手感瞬间丝滑 5 倍以上。
  2. **掩盖 API 延迟劣势**：即便模型提供商在晚高峰响应很慢，只要有了 Speculation 垫底，用户根本察觉不到网络卡顿。