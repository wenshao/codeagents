# Qwen Code 改进建议 — ConfigTool 动态配置读写 (Dynamic ConfigTool)

> 核心洞察：几乎所有的 CLI Agent 都有一个 `config` 命令，让人类去修改底层的行为模式。但是当你的 Agent 面对极其复杂的跨阶段任务时——比如，你要求它“先分析这 10 万行代码（需要拥有大上下文的旗舰模型），然后再根据分析给我批量生成 500 个 Mock 数据 JSON 文件（需要便宜且飞快的小模型），最后再仔细 Review 一遍生成的有没有越界（需要切回强推理的旗舰模型）”——如果完全指望用户在每个阶段去人工敲命令切换，这绝不是智能体，这叫脚本。Claude Code 构建了专门给大模型使用的 `ConfigTool`；而 Qwen Code 目前所有的配置调整必须由人类在控制台发起。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、配置必须靠人工切换的尴尬

### 1. Qwen Code 现状：无法自主思考的环境
在目前的框架中，配置存储在类似 `.qwen/config.json` 的全局单例里。
- **痛点**：只有人类开发者有权限通过类似 `qwen config set model qwen-max` 这样的系统命令去触及底层的运转模式。
- **导致的结果**：当 Qwen Code 在执行一整个复杂工作流中遇到障碍时（比如连续请求都被 API 的 429 频率限制挡在门外），它只能像只无头苍蝇一样原地撞墙报错，无法说出一句：“我发现主模型被限流了，我要不要在配置里把模型临时改成备用小模型试试看？”。

### 2. Claude Code 的极客脑洞：让模型获得方向盘
在 Claude Code 中（见 `tools/ConfigTool/ConfigTool.ts` 源码），他们将改变系统配置的能力“武器化”，并暴露给了大模型自己。

#### 机制一：赋予大模型修改引擎参数的 Tool
系统内置了一个叫 `ConfigTool` 的虚拟工具。大模型一旦觉得目前的配置阻碍了自己，它可以在推理循环中调用这个工具。
比如大模型可以自己决定执行：
```json
{
  "tool_name": "config_tool",
  "args": {
    "action": "set",
    "key": "theme",
    "value": "light"
  }
}
```
它能自己读取当前用户启用了哪些配置（`action: get`），甚至自己动手修改外观！

#### 机制二：基于 Schema 的防爆验证
把“操作底层配置文件”的权力交给 AI 是极其危险的（它可能不小心把超时时间配成 `-1` 导致系统崩溃）。
因此，`ConfigTool` 内部挂载了一套比钢铁还硬的 JSON Schema 验证器（基于 Zod 或 Ajv）。模型如果提交了非法的键名或者类型不对的值，工具会直接阻断底层写入，并抛出 `Tool Error` 勒令模型修正。

#### 机制三：高级自我调节案例
Claude 模型通过 `ConfigTool`，甚至可以做到：
当它发现自己每次输出一大段代码时终端滚得太快，它会先调用工具把 `statusLineText` 相关配置调低刷新率，或者干脆提醒用户如果终端是白色背景看不清代码的话，它主动把终端的 `theme` 从 `dark` 切为 `light`。这种破窗而出的智能化体验是颠覆性的！

## 二、Qwen Code 的改进路径 (P2 优先级)

让大模型可以自己“系鞋带”和“换轮胎”，是向 Autonomous Agent（完全自主智能体）进化的分水岭。

### 阶段 1：开放特定的沙盒配置选项
1. 在 Qwen Code 底层抽象出 `DynamicConfigKeys` 列表（绝对不能把涉及到本地文件路径的危险配置暴露出去）。
2. 只暴露像 `model`、`theme`、`verbosity_level` 这种对系统运行无害的安全调节选项。

### 阶段 2：开发并装载 ConfigTool
1. 在 `packages/core/src/tools/` 下新建 `configMutation.ts`。
2. 内部暴露两个动作：`get` 获取当前设定，`set` 更新设定。
3. 把这个工具下发给带有高权限（非后台只读）的主 Agent。大模型在其系统提示中被明确告知：“You can use ConfigTool to change the active model or UI theme if strictly necessary to complete your multi-step objective.”

### 阶段 3：配合权限弹窗双重保险
如果模型试图调用这个工具去切换 API 模型（可能涉及到资费变化）：
它必须触发我们在前几轮探讨过的 `Agent Permission Bubble`！在终端屏幕上高亮弹出：
> “The agent wants to change the active model to **qwen-max** to perform complex reasoning. Approve? (Y/n)”
让人类把好最后一关。

## 三、改进收益评估
- **实现成本**：小到中等。实现工具本身只要几十行，麻烦的是如何在运行时把修改后的新配置瞬间热重载（Hot-reload）到大模型的 HTTP Client 实例里。
- **直接收益**：
  1. **自动化工作流的质变**：用户只需要给出一个粗略的宏观目标，Agent 可以像人类一样“看菜下饭”，自己根据难度切换适合的算力模型，榨干成本效益比。
  2. **令人惊呼的产品体验**：当开发者看着大模型由于任务失败而主动去修改自身的设置进行“自我救赎”时，会极大地增强“它是一个真正聪明的同事”的心理投射。