# Qwen Code 改进建议 — Conditional Hooks 条件过滤系统 (Conditional Hooks)

> 核心洞察：生命周期钩子（Hooks）是 Agent 生态的重要扩展点，允许在事件（如 `PreToolUse` 或 `PostCommit`）发生时执行外部逻辑。但在企业级开发中，如果不区分场景就盲目触发所有钩子（例如：开发者配置了每次修改文件就跑代码格式化，结果 Agent 只是用 `Bash` 跑了个简单的 `ls` 命令，也白白触发了笨重的格式化 Hook），将导致巨大的时间浪费与逻辑污染。Claude Code 在 Hook 引擎中内建了类似防火墙规则的 `if` 表达式系统；而 Qwen Code 目前的 Hook 是绝对无条件全量触发的。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、无条件 Hook 带来的效率灾难

### 1. Qwen Code 现状：只要挂载，全局执行
目前的 `Hook` 系统在匹配到指定 `event` 时，无论上下文是什么都会被调用。
- **痛点一（无效算力浪费）**：假设你绑定了 `PreToolUse` 来执行安全敏感词扫描。当 Agent 调用无害的 `FileReadTool` 时，这个笨重的安全扫描脚本也会跑一遍。
- **痛点二（逻辑交叉污染）**：如果你想实现“只要 Agent 用 Shell 执行了带有 `git` 的命令，就先发一条钉钉消息”，在现在的配置下你完全做不到，因为 Shell 的参数是在运行期才决定的。

### 2. Claude Code 的解决方案：精确的条件路由
Claude Code 在其 `types/hooks.ts` Schema 中为所有类型的 Hook（不管是 `command` 还是 `http`）暴露了一个可选字段：`if`。

它直接复用了 `Permission Manager`（权限管理器）中的通配符与规则验证器语法，例如：
```yaml
# Claude Code 挂载钩子配置示例
hooks:
  - type: command
    events: ["PreToolUse"]
    if: "Bash(git:*)"
    command: "./scripts/check_git_status.sh"
    
  - type: http
    events: ["PreToolUse"]
    if: "FileWrite(*.ts,*.tsx)"
    url: "http://linter-service/validate"
```

在这套强大的前置判定（`hookRunner.ts`）系统下：
只有当大模型准备使用 `Bash` 并且前缀匹配了 `git`，或者准备编辑带有 `.ts`/`.tsx` 后缀的文件时，对应的钩子才会被挂起执行。其它所有日常搜索和阅读操作直接光速旁路（Bypass）。

## 二、Qwen Code 的改进路径 (P2 优先级)

赋予 Hook 系统以“逻辑脑”，避免大水漫灌。

### 阶段 1：Schema 增加表达式字段
在 `HookConfig` 定义中，增加可选的字符串字段 `if`（或者 `condition`）。
```typescript
export interface HookConfig {
  name: string;
  events: AgentEventType[];
  if?: string; // 类似 "ToolName(ArgPattern)" 的模式
  // ... 其他执行配置
}
```

### 阶段 2：复用 Permission Matcher 引擎
Qwen Code 内部本身应该具备对 Tool 参数进行鉴权的验证器引擎（用于判断用户配置的哪些命令可以被允许）。
- 在 `hookRunner.ts` 分发执行前，拦截所有的 `PreToolUse` 和 `PostToolUse` 事件。
- 获取当前事件上下文中挂载的 `toolName` 和 `toolArgs` 序列化字符串。
- 将 `hook.if` 的表达式传给匹配器进行求值。如果返回 `false`，则在 debug logger 中打一条 `Hook [x] skipped due to condition mismatch` 并直接 `return` 结束。

### 阶段 3：特殊事件的高级判定（进阶）
除了 Tool 参数过滤外，未来还可以扩展对内部状态机的判定（例如 `if: "ContextTokens > 150000"`，在临界溢出前去清理垃圾数据等特殊应急 Hook）。

## 三、改进收益评估
- **实现成本**：极低。本身复用了权限模块已有的验证轮子，只需新增几十行控制流分支。
- **直接收益**：
  1. **消灭垃圾耗时**：精确过滤让无害的工具调用速度大幅回归，消除 Hook 带来的宏观性能下降感。
  2. **高频定制能力**：允许企业级客户编写高度“领域驱动（Domain Driven）”的外挂拦截流，让 Qwen Code 的生态可玩性产生质变。