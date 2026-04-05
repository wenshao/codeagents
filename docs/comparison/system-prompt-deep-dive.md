# Qwen Code 改进建议 — 系统提示模块化组装 (System Prompt Modular Assembly)

> 核心洞察：现代大语言模型代理的每一次呼吸（API 调用），都扛着一个极其沉重的包袱——系统提示词（System Prompt）。在这个长达上万字的提示词中，不仅包含了极其复杂的“行为准则（Do's and Don'ts）”，还塞满了针对当前工具库的详细使用说明（Tool Definitions）。随着 API 厂商推出了能省下 80% 费用的“Prompt Cache（提示词缓存）”技术，如何让这些提示词尽可能地保持静态成为了降低成本的关键。然而，系统提示中往往还夹杂着像“当前目录”、“当前日期”这样随时在变动的短变量。Claude Code 设计了极其精湛的 **系统提示分段与动态边界（Dynamic Boundary）** 算法，把静态内容死死锁在了缓存里；而 Qwen Code 的全局混合拼接会导致极其惨重的缓存击穿。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、微小变动击穿万字缓存的悲剧

### 1. Qwen Code 现状：单一字符串的组装陷阱
目前在构建发送给大模型的 `system` 字段时，很多开源 Agent 会采用简单粗暴的字符串模板（String Interpolation）拼接：
```typescript
const systemPrompt = `
You are Qwen Code, a helpful coding assistant...
[...省略 10000 字的冗长底层准则...]

## 当前环境信息
当前日期：${new Date().toISOString()}
工作目录：${process.cwd()}
当前 Git 分支：${gitBranch}
`;
```
- **痛点一（Token 成本爆炸）**：如果开发者在终端里执行了一个最基础的 `cd src/components` 命令切换了工作目录。`process.cwd()` 这个变量立刻改变！哪怕这几万字的系统提示只变了短短十几个字母，但在云端大模型看来，这就是一段全新的、从来没见过的前缀。缓存（Prompt Cache）瞬间失效（Miss）！你需要为这重新发送的 10000 多个 Token 支付昂贵的“冷启动”全额费用。
- **痛点二（极高的首字延迟）**：缓存失效意味着模型必须重新阅读这几万字的核心规则才能开口说话。在原本应该秒回的普通操作中，会突然出现长达 2-3 秒的意外卡顿（TTFT 飙升）。

### 2. Claude Code 解决方案：物理隔离的界碑
在 Claude Code 的 `utils/systemPrompt.ts` 等底层拼装模块中，工程师们为了死保缓存命中率，把大模型提示词工程做到了极其苛刻的微操地步。

#### 机制一：独立切片的 Section (Modular Sections)
系统提示被彻底拆解成了一个个独立的“切片（Sections）”。
- **静态切片**：包含绝对不会变的东西，如“永远不要暴露密码”、“如何使用 Bash 工具”、“如何输出代码块”。这些占据了内容的 **97%**。
- **动态切片**：那些每过一秒、每敲一个命令都可能在变的东西，被单独抽离封装在了名叫 `DANGEROUS_uncachedSystemPromptSection(reason)` 的特殊函数里（作者刻意加了 `DANGEROUS` 前缀以警告其他开发者：不要随便往这里塞东西，因为会破缓存！）。

#### 机制二：不可逾越的动态边界 (Dynamic Boundary)
在最终拼装发送给大模型的结构数组时，它设立了一个强硬的分界线：`SYSTEM_PROMPT_DYNAMIC_BOUNDARY`。
在这个界碑之上的所有大部头，会被附加上 `cache_control: { type: "ephemeral" }` 标记，告知服务端对这部分长文本进行极速缓存驻留（Global Scope Caching）。
在这个界碑之下的、排在整个请求最最末尾的（比如当前所处的目录、最新的日期），则被标注为 `uncached` 动态内容。
**结果是惊人的**：无论用户怎么频繁地 `cd` 切换目录，因为前面的 97% 内容一字不差，缓存永远命中！仅有尾部那微不足道的 3% 的 Token 会产生冷读取。极大压制了 API 的账单，保证了全流程“零延迟”的手感。

## 二、Qwen Code 的改进路径 (P1 优先级)

想要让用户感觉 Agent 越用越便宜、越用越快，模块化的组装逻辑是底层必修课。

### 阶段 1：重构大一统的 `SystemPrompt` 生成器
1. 在 `packages/core/src/prompts/`（或对应负责系统提示的目录）中，废弃原本那张庞大的一体化长文本拼接字符串。
2. 拆分出返回静态字符串的函数：`getCoreRules()`, `getSecurityGuidelines()`, `getToolUsages()`。

### 阶段 2：设立严格的缓存阻断边界
1. 在大模型 API 请求层（例如向阿里云百炼发送的请求构造阶段），明确区分“可缓存前缀（Cached Prefix）”和“易变后缀（Volatile Suffix）”。
2. 将所有与**用户运行状态密切相关**的探测函数（比如 `getCurrentGitStatus()`, `getCurrentTime()`, `getCWD()`）返回的内容，统一放在提示词列表的最末端。
3. 按照各大平台（如 Anthropic, 阿里云等）对 Prompt Cache API 的具体语法要求，在静态块的末尾严格打上缓存断点（Breakpoint）标签。

### 阶段 3：建立防劣化探针
在本地调试模式开启时，每次发送网络请求，都在终端或日志文件里打出一行日志：
`[Cache Diagnostics] Static Prefix: 14500 tokens. Volatile Tail: 350 tokens.`
如果在后续开发新功能时，某个写得糟糕的代码导致 Volatile 部分异常庞大，甚至污染了静态块，能够立刻被拦截和优化。

## 三、改进收益评估
- **实现成本**：中等。核心不在于写代码，而在于深刻理解大模型底座缓存协议的切分点规则，并在项目中重构文本组装顺序。代码量在 200 行左右。
- **直接收益**：
  1. **极度恐怖的费用缩减**：据统计，一个 8 小时的正常编码会话，优秀的缓存能为用户节约掉高达 80% 到 90% 的 Input Token 成本。
  2. **消除环境变动带来的延迟尖刺**：每次状态变动（换目录、Git 提交了一次代码导致状态机更新）后的第一次提问，Agent 响应速度能由之前的 3 秒陡降至不到 0.5 秒。