# 9. /loop 与定时执行功能深度分析

> 循环执行和远程调度是 AI 编程代理从"一次性助手"进化为"持续自动化"的关键能力。

## 功能覆盖

| Agent | 本地循环 | 远程调度 | 类似功能 |
|------|---------|---------|---------|
| **Claude Code** | ✓ `/loop` | ✓ `/schedule`（CCR 云端） | — |
| **Copilot CLI** | ✗ | ✗ | Autopilot（持续执行但非循环） |
| **Codex CLI** | ✗ | ✓ `codex cloud`（实验性） | — |
| **Aider** | ✗ | ✗ | `--watch-files` 文件监视（AI 注释触发，非循环命令） |
| **Goose** | ✗ | **✓** `goose schedule`（本地 cron） | Recipe + 定时调度 |
| **Gemini CLI** | ✗ | ✗ | — |
| **Qwen Code** | ✗ | ✗ | — |
| **Kimi CLI** | ✗ | ✗ | — |

> **关键发现：** Claude Code 同时拥有本地循环（`/loop`）和远程调度（`/schedule`）；Goose 拥有本地 cron 调度（`goose schedule`）；Codex CLI 拥有一次性远程执行（`codex cloud`）。

---

## Claude Code `/loop`（本地循环执行）

### 源码定义（v2.1.81 二进制反编译提取）

```javascript
d4({
  name: "loop",
  description: "Run a prompt or slash command on a recurring interval
    (e.g. /loop 5m /foo, defaults to 10m)",
  whenToUse: 'When the user wants to set up a recurring task, poll for status,
    or run something repeatedly on an interval (e.g. "check the deploy every
    5 minutes", "keep running /babysit-prs"). Do NOT invoke for one-off tasks.',
  argumentHint: "[interval] <prompt>",
  userInvocable: true,
  isEnabled: Kh,  // 条件启用
})
```

### 参数格式

```
/loop [间隔] <提示或命令>
```

| 参数 | 格式 | 说明 |
|------|------|------|
| 间隔 | `Ns`、`Nm`、`Nh`、`Nd` | 秒/分/时/天，最小粒度 1 分钟 |
| 默认间隔 | `10m` | 源码常量 `OeH = "10m"` |
| 提示 | 任意文本或 `/命令` | 每次循环重新发送 |

### 使用示例

```bash
# 每 5 分钟检查 PR 状态
/loop 5m /babysit-prs

# 每 30 分钟检查部署
/loop 30m check the deploy

# 每小时执行 standup
/loop 1h /standup 1

# 默认 10 分钟间隔
/loop check the deploy

# 自然语言指定间隔
/loop check the deploy every 20m
```

### 内部机制

1. **解析阶段**：从参数中提取间隔（如 `5m`）和目标命令
2. **循环阶段**：按间隔重复将目标命令作为新的用户输入发送给代理
3. **管理**：通过 `/tasks` 命令查看和管理运行中的循环任务
4. **停止**：`Ctrl+C` 或通过 `/tasks` 取消

### 适用场景

| 场景 | 示例 | 间隔建议 |
|------|------|---------|
| CI/CD 监控 | `/loop 5m check the deploy status` | 5-10 分钟 |
| PR 巡检 | `/loop 10m /babysit-prs` | 10-30 分钟 |
| 持续审查 | `/loop 30m /review` | 30-60 分钟 |
| 状态轮询 | `/loop 2m check if tests passed` | 2-5 分钟 |
| 定期提交 | `/loop 1h /commit` | 30-60 分钟 |

### 与 `/schedule` 的区别

| 维度 | `/loop`（本地） | `/schedule`（远程） |
|------|---------------|-------------------|
| 执行位置 | 当前终端会话 | Anthropic 云端（CCR） |
| 生命周期 | 终端关闭即停止 | 独立于本地会话 |
| 上下文 | 共享当前会话 | 独立 Git checkout + 工具集 |
| 定时格式 | `Ns/Nm/Nh/Nd` | **cron 表达式** |
| MCP 支持 | 使用当前 MCP 配置 | 连接 claude.ai MCP Connectors |
| 适用 | 短期监控、实时反馈 | 长期自动化、CI/CD 集成 |

---

## Claude Code `/schedule`（远程云端调度）

### 架构（CCR = Claude Code Remote）

```
/schedule create
  │
  ├── 用户交互（AskUserQuestion 工具）
  │     └── 选择操作: 创建 / 列出 / 更新 / 执行
  │
  ├── RemoteTrigger 工具 ──→ claude.ai CCR API
  │     ├── POST /v1/code/triggers (创建)
  │     ├── GET  /v1/code/triggers (列出)
  │     ├── GET  /v1/code/triggers/{id} (获取)
  │     ├── POST /v1/code/triggers/{id} (更新)
  │     └── POST /v1/code/triggers/{id}/run (执行)
  │
  └── CCR 云端执行
        ├── 隔离的 Git checkout
        ├── 独立的工具集（Bash/Read/Write/Edit/Glob/Grep）
        ├── 可选 MCP Connectors（从 claude.ai 配置）
        └── 模型: claude-sonnet-4-6
```

### 创建 Trigger 的 body 结构（源码提取）

```json
{
  "name": "每天审查 PR",
  "cron_expression": "0 9 * * 1-5",
  "enabled": true,
  "job_config": {
    "ccr": {
      "environment_id": "ENVIRONMENT_ID",
      "session_context": {
        "model": "claude-sonnet-4-6",
        "sources": [
          {"git_repository": {"url": "https://github.com/ORG/REPO"}}
        ],
        "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
      },
      "events": [{
        "data": {
          "uuid": "<v4-uuid>",
          "type": "user",
          "content": [{"type": "text", "text": "审查所有未合并的 PR"}]
        }
      }]
    }
  }
}
```

### MCP Connector 系统

远程 Trigger 可以连接 claude.ai 上配置的 MCP 服务器：
- Connector UUID 编码为 `mcpsrv_` + Base58 编码
- 通过 `G7_()` 函数解码 Base58 → 十六进制 → UUID 格式
- 认证通过 OAuth in-process 处理（token 不暴露到 shell）

### 使用示例

```bash
# 交互式创建
/schedule

# 列出所有定时任务
/schedule list

# 立即执行一个 trigger
/schedule run <trigger_id>

# 注意：不能删除——需到 https://claude.ai/code/scheduled 网页操作
```

---

## Codex CLI `codex cloud`（实验性远程执行）

### 与 Claude Code `/schedule` 的对比

| 维度 | Claude Code `/schedule` | Codex CLI `codex cloud` |
|------|------------------------|------------------------|
| 状态 | 正式功能 | **实验性** |
| 定时 | cron 表达式（重复执行） | **一次性提交** |
| 执行 | CCR 云端 | OpenAI 云端 |
| Best-of-N | ✗ | **✓（1-4 次尝试）** |
| Diff 拉回 | ✗（直接在远程 Git 操作） | **✓（`codex cloud apply`）** |
| 子命令 | list/get/create/update/run | exec/status/list/apply/diff |

```bash
# Codex Cloud 使用
codex cloud exec "fix all failing tests"     # 提交一次性任务
codex cloud status <TASK_ID>                 # 查看状态
codex cloud list                              # 列出任务
codex cloud apply <TASK_ID>                  # 将 diff 应用到本地
codex cloud diff <TASK_ID>                   # 查看 diff
```

### 关键差异

**Claude Code `/schedule`** = **持续自动化**（cron 定时循环）
**Codex CLI `codex cloud`** = **一次性远程执行**（提交任务→等待完成→拉回结果）

---

## Goose `goose schedule`（本地 cron 调度）

> 来源：[Goose CLI Commands](https://block.github.io/goose/docs/guides/goose-cli-commands/)，[GitHub Discussions #4389](https://github.com/block/goose/discussions/4389)

### 与 Claude Code `/schedule` 的对比

| 维度 | Claude Code `/schedule` | Goose `goose schedule` |
|------|------------------------|----------------------|
| 执行位置 | Anthropic 云端（CCR） | **本地守护进程 (Daemon)** |
| 定时 | cron 表达式 | cron 表达式（6 位，含秒） |
| 任务来源 | 自然语言提示 | **Recipe（YAML 任务模板）** |
| 管理命令 | create/list/update/run | add/list/sessions/run-now/remove |
| 删除 | 需在 claude.ai 网页操作 | `goose schedule remove` |
| 依赖 | 云端基础设施 + OAuth | 本地运行，无需云端 |

### 使用示例

```bash
# 添加定时任务（每天 9 点执行日报 Recipe）
goose schedule add --schedule-id daily-report \
  --cron "0 0 9 * * *" \
  --recipe-source ./recipes/daily-report.yaml

# 列出所有定时任务
goose schedule list

# 查看某任务的执行历史
goose schedule sessions --schedule-id daily-report -l 10

# 立即执行一次
goose schedule run-now --schedule-id daily-report

# 删除定时任务
goose schedule remove --schedule-id daily-report
```

### Recipe 系统

Goose 的调度只能执行 Recipe（YAML/JSON 定义的可复用任务模板）。Recipe 定义任务的提示词、所需扩展和参数，通过 deeplink 或 YAML 文件导入。

---

## Aider `--watch-files`（文件监视 + AI 注释触发）

> 来源：[Aider Watch Docs](https://aider.chat/docs/usage/watch.html)

Aider 的 `--watch-files` 不是循环命令，而是**基于文件变更的 AI 触发机制**：

```bash
# 启动文件监视模式
aider --watch-files

# 在 IDE 中添加 AI 注释触发操作：
# AI! — 触发 aider 修改代码
# AI? — 触发 aider 回答问题
```

**工作原理：**
1. 监视仓库中所有文件变更
2. 扫描文件中以 `AI` 开头或结尾的单行注释（`# ...AI!`、`// ...AI?`）
3. `AI!`（感叹号）触发代码修改，`AI?`（问号）触发问答
4. 收集所有 AI 注释作为指令，调用 aider 执行
5. 跳过 >1MB 的大文件，忽略 .svg/.pdf 等非代码文件

| 维度 | Claude Code `/loop` | Aider `--watch-files` |
|------|-------------------|---------------------|
| 触发方式 | 定时间隔 | 文件变更 |
| 指令来源 | 命令行参数 | 文件内 AI 注释 |
| 执行方式 | 重复发送相同命令 | 收集注释作为新指令 |
| IDE 集成 | 无（终端内） | **✓（任何 IDE/编辑器）** |
| 适用场景 | 监控/轮询 | IDE 内无缝 AI 编程 |

---

## Copilot CLI Autopilot（持续执行但非循环）

Copilot CLI 的 Autopilot 模式不是循环执行，而是**持续执行直到任务完成**：

```
Shift+Tab 切换到 Autopilot 模式
  └── 代理持续工作，不暂停等待输入
      └── 直到任务完成或 --max-autopilot-continues 次数用尽
```

| 维度 | Claude Code `/loop` | Copilot Autopilot |
|------|-------------------|-------------------|
| 重复执行 | ✓（按间隔循环） | ✗（持续但不循环） |
| 任务类型 | 监控/轮询/定期审查 | 复杂任务持续执行 |
| 停止条件 | 手动停止 | 任务完成或次数限制 |
| 间隔控制 | 用户指定 | 无间隔（连续） |

---

## 面向开发者的设计洞察

### 1. 本地循环 vs 远程调度的架构选择

| 方案 | 适用场景 | 技术限制 |
|------|---------|---------|
| **本地循环**（Claude Code `/loop`） | 开发时的实时监控 | 依赖终端保持打开 |
| **远程调度**（Claude Code `/schedule`） | CI/CD、夜间任务 | 需要云端基础设施 |
| **本地 cron 调度**（Goose `schedule`） | 定期本地任务 | 依赖本地守护进程 (Daemon) |
| **一次性远程**（Codex `cloud exec`） | 计算密集型任务 | 无持续自动化 |
| **文件监视**（Aider `--watch-files`） | IDE 内 AI 编程 | 需文件内 AI 注释 |
| **持续执行**（Copilot Autopilot） | 复杂单次任务 | 非循环 |

### 2. 为什么大部分工具没有 /loop？

`/loop` 需要解决几个技术挑战：
1. **任务管理**：如何追踪/列出/取消运行中的循环任务
2. **上下文隔离**：循环执行是否共享或隔离上下文
3. **错误处理**：某次执行失败是否停止整个循环
4. **资源控制**：防止用户设置过短间隔耗尽 API 配额

Claude Code 通过 `/tasks` 命令管理循环任务，复用了其 Task 工具系统（TaskCreate/TaskGet/TaskList/TaskUpdate），这是其他工具缺乏的基础设施。

### 3. `/schedule` 的技术门槛

实现远程调度需要：
- 云端执行环境（CCR）
- OAuth 令牌 (Token) 管理（in-process，不暴露到 shell）
- MCP Connector 远程桥接 (Bridge)
- Cron 表达式解析和调度引擎
- API 端点（`/v1/code/triggers/*`）

这需要整个云端基础设施的支持，解释了为什么只有 Anthropic（Claude Code）和 OpenAI（Codex CLI）提供了云端远程执行能力。Goose 采用了不同路径——本地 cron 调度，无需云端基础设施，但依赖本地守护进程 (Daemon) 运行。

---

## 证据来源

| Agent | 源码 | 获取方式 |
|------|------|---------|
| Claude Code `/loop` | `d4({name:"loop",...})` 注册 + `j7_` usage 字符串 + `OeH="10m"` | 二进制 strings 提取 |
| Claude Code `/schedule` | `vAH="RemoteTrigger"` + API 端点 + CCR 提示词 | 二进制 strings 提取 |
| Codex CLI `cloud` | `codex cloud --help` | 本地 --help |
| Copilot CLI Autopilot | `AUTOPILOT_MODE` feature flag + README | 二进制 + 官方文档 |
| Goose `schedule` | `goose schedule add --help` | [官方文档](https://block.github.io/goose/docs/guides/goose-cli-commands/) |
| Aider `--watch-files` | `aider/watch.py` | [官方文档](https://aider.chat/docs/usage/watch.html) |
