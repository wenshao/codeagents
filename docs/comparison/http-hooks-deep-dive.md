# Qwen Code 改进建议 — HTTP Hooks 原生网络集成 (Native HTTP Hooks)

> 核心洞察：现代开发流程高度依赖外部系统（如 Jira 状态同步、Slack 消息通知、Jenkins 触发、安全审批网关）。目前大多 CLI Agent 的 Hook 机制仅仅支持运行一段本地的 Shell 脚本（Command Hook）。如果要把 Agent 和外部系统打通，开发者只能被迫写一堆脆弱的 `curl` 脚本，自己处理转义、超时和 JSON 解析。Claude Code 支持了原生的 `type: "http"` Hook，允许在生命周期事件触发时直接向指定 URL 发送结构化 JSON，并解析响应，这极大提升了扩展能力和系统集成度；而 Qwen Code 目前仅支持 Shell Hook。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、集成外系统的痛点

### 1. Qwen Code 现状：脆弱的 Shell 脚本中转
假设我们在 Qwen Code 中配置了一个 `PostToolUse` 的 Hook，希望在每次大模型修改完代码后，向内部的审计 API 发送一条记录。
在仅有 Command Hook 的情况下，配置大概长这样：
```json
{
  "events": ["PostToolUse"],
  "type": "command",
  "command": "curl -X POST https://audit.corp/api -H 'Content-Type: application/json' -d '{\"tool\": \"'$TOOL_NAME'\"}'"
}
```
**痛点**：
- **极易失败的字符转义**：如果 `$TOOL_ARGS` 里含有单引号或换行符，整个 `curl` 拼接就会语法错误甚至导致命令注入（Command Injection）。
- **极难解析的响应**：如果服务端返回了一段带有审批意见的 JSON 响应，用 Bash 的 `jq` 或 `grep` 提取异常繁琐，很难将其优雅地返回给 Agent 作为下一步操作的提示。
- **跨平台兼容性差**：`curl` 在 Windows 上可能不可用或语法不同。

### 2. Claude Code 解决方案：原生 HTTP 协议驱动
Claude Code 在其 Hook 系统 (`utils/hooks/hookRunner.ts` 和 `types/hooks.ts`) 中，原生支持了 `http` 类型的 Hook：

```json
{
  "events": ["PreToolUse"],
  "type": "http",
  "url": "https://approval-gateway.corp/check",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer ${ENV:APPROVAL_TOKEN}"
  }
}
```

当该 Hook 触发时，Claude Code 的引擎会：
1. **自动序列化**：把当前生命周期的上下文（如 `tool_name`, `args`, `session_id`）构建为一个完整的 JSON Object，并通过底层的 HTTP Client (如 `fetch`) 安全地 POST 给目标 URL，彻底免去了 Shell 字符转义的烦恼。
2. **结构化响应解析**：服务端可以返回一个 JSON 包含 `{"approved": true, "message": "Proceed"}`。引擎会直接将这些返回字段无缝注入到下一轮大模型的 System Context 中。
3. **安全阻断与 SSRF 防护**：内建了网络超时控制；对于某些环境甚至能配合代理限制私有 IP 访问。

## 二、Qwen Code 的改进路径 (P1 优先级)

为了将 Qwen Code 从“单机脚本运行器”进化为“微服务架构的一环”，扩展 Hook 系统的协议支持是性价比极高的改动。

### 阶段 1：扩展 Hook 配置 Schema
在 `packages/core/src/types/hookTypes.ts`（或对应的配置文件声明）中，扩展 `HookConfig` 的定义：
```typescript
type HookType = 'command' | 'http';

interface HttpHookConfig extends BaseHookConfig {
    type: 'http';
    url: string;
    method?: 'POST' | 'GET' | 'PUT';
    headers?: Record<string, string>;
    timeoutMs?: number;
}
```

### 阶段 2：实现 HTTP Runner
在 `hookRunner.ts` 的执行分发逻辑中增加 HTTP 分支：
1. 当解析到 `type === 'http'` 时，收集当前事件上下文 (`HookInputContext`)。
2. 将上下文 `JSON.stringify()` 作为 Body。
3. 解析配置中的 `headers`（支持环境变量替换，如 `${QWEN_HOOK_TOKEN}`）。
4. 执行原生的 `fetch()` 或 `axios` 调用。

### 阶段 3：响应集成与反馈流
如果 Hook 是前置拦截型的（比如 `PreToolUse`），它应该能够阻塞执行。
解析 HTTP 响应返回的 JSON：
- 约定一套简单的标准，如响应如果包含 `"error"` 或 HTTP 状态码 `>= 400`，则阻断当前操作，并将服务端的错误信息作为 `tool_error` 喂给模型。
- 如果返回成功的文本或 JSON，则附加到执行流日志中供模型理解。

## 三、改进收益评估
- **实现成本**：低。无需引入新的大型依赖，只需新增几十行 HTTP Fetch 的包裹代码和错误处理逻辑。
- **直接收益**：
  1. **解放 DevOps 集成**：极其轻松地对接企微/飞书机器人、Jenkins Pipeline 或者 Jira 状态机，无需开发者编写和维护脆弱的 Bash 胶水脚本。
  2. **安全与跨平台**：完全绕开不同 OS 下 Shell 转义和执行环境的差异，保证跨 Windows/Linux/macOS 的一致性。