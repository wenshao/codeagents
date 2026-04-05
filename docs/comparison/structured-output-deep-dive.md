# Qwen Code 改进建议 — Structured Output (--json-schema)

> 核心洞察：当大模型 Agent 作为一个子组件被集成到更大的企业级自动化流水线中时（比如用于给遗留代码自动生成带类型的 `d.ts` 文件，或用于进行漏洞扫描并输出报告），纯文本的自然语言输出是毫无用处的。下游的解析脚本无法处理不确定的 markdown。Claude Code 设计了巧妙的“结构化输出伪工具 (Synthetic Output Tool)”并结合运行时 Schema 校验机制，完美确保了模型在完成推理后吐出格式 100% 严谨的 JSON 串；而 Qwen Code 目前仅能依靠 Prompt 提示来“碰运气”。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么 Prompt 约束总是失败？

### 1. Qwen Code 现状：基于自然语言的弱约束
如果要在现有的 Qwen Code 中强制让模型输出 JSON：
```bash
qwen-code "请总结当前目录的文件列表，只输出 JSON，不要输出任何解释，格式为 { files: string[] }"
```
- **痛点一 (格式泄露)**：大模型有着强烈的“聊天欲望”。即使加上了“只输出 JSON”的限制，它仍然极大概率会在开头加上一句 `Here is the JSON you requested:`，或者在结尾附上一段解释，直接导致下游的 `JSON.parse()` 崩溃挂起整个 CI 流水线。
- **痛点二 (格式漂移)**：大模型可能漏掉某个关键字段，或者把应该输出的 `Array` 变成了单个 `String`。
- **痛点三 (无自愈机制)**：一旦输出错了，流程直接失败，没有任何“告诉它错了并重新生成”的自动重试层。

### 2. Claude Code 的解决方案：Synthetic Output Tool
在 Claude Code 中（见 `tools/SyntheticOutputTool/SyntheticOutputTool.ts`），它通过一个极其精妙的假工具（Synthetic Tool）来接管最终的话语权。

当你运行：
```bash
claude -p "分析漏洞" --json-schema schema.json
```
1. 引擎在检测到非交互模式 (`isNonInteractiveSession`) 且存在 `--json-schema` 时，会在 Agent 的工具池里动态挂载一个专门的 `StructuredOutput` 工具。
2. 它在系统提示词中强制附加一条核心指令：“当你完成你的思考和所有探索后，你**必须且只能**调用 `StructuredOutput` 工具来返回最终结果，不要直接输出文字响应。”
3. **运行时 Ajv 强校验**：当模型真的调用了这个工具时，工具内部会使用 `ajv` 库对传入的 JSON arguments 进行极其严苛的模式验证。
4. **验证失败即重试**：如果 `ajv` 报错“缺少 required 字段 `severity`”，引擎不会抛错，而是直接将这个校验错误作为 `tool_error` 返回给模型：“你的输出不符合 JSON Schema：[错误信息]”。模型收到后会自动修正拼写并再次调用该工具，直到 Schema 完全契合为止。

这实现了 100% 确定的、无边角的完美机器可读输出！

## 二、Qwen Code 的改进路径 (P1 优先级)

为了让 Qwen Code 能够在 CI 脚本中稳定地充当“确定性处理节点”，这一特性是刚需。

### 阶段 1：开发 StructuredOutput 工具
1. 新增 `packages/core/src/tools/structuredOutput.ts`。
2. 该工具被定义为“终端节点（Terminal Tool）”。一旦被调用并且校验成功，直接标记当前推理循环 `runReasoningLoop` 结束（`AgentTerminateMode.SUCCESS`）。

### 阶段 2：引入 JSON Schema 验证器
1. 引入 `ajv` 等高性能的 Schema 验证库。
2. 在工具的 `execute` 逻辑中，把用户传入的 `--json-schema` 文件（或者内联字符串）编译为验证函数。

### 阶段 3：CLI 无头模式支持
1. 在 `packages/core/src/cli/nonInteractiveCli.ts` 中增加 `--json-schema <path>` 参数。
2. 如果存在该参数，在组装 System Prompt 时：
   - 禁用任何默认的自然语言结尾提示。
   - 注入强制使用结构化工具指令。
3. 捕获最终的 `ToolResult`，直接通过 `process.stdout` 原样输出 JSON 字符串，不上色，不带任何其他前缀。

## 三、改进收益评估
- **实现成本**：小。核心是新增一个虚拟工具并串联起大模型的循环终止逻辑，代码量大约 100-150 行。
- **直接收益**：
  1. **解锁机器间通信**：使得 Qwen Code 的输出可以被 `jq` 无缝解析，直接喂给下一个 Bash 脚本或者 API 请求。
  2. **模型结果高可靠性**：不再依赖脆弱的正则提取，把自然语言输出带来的语法错误率降为 0。