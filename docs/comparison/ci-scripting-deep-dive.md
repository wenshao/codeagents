# 38. 非交互/CI 模式深度对比

> AI 编程代理从"交互式助手"进入"CI/CD 自动化管道"的关键能力。各工具的脚本化支持从"无"到"完整 JSON 流式协议"。

## 总览

| Agent | 主要标志 | 输出格式 | 结构化输出 | 成本控制 | 无头模式 |
|------|---------|---------|-----------|---------|---------|
| **Claude Code** | `-p / --print` | text/json/**stream-json** | **✓ JSON Schema** | **✓ --max-budget-usd** | ✗（需显式） |
| **Gemini CLI** | `-p` | text | ✗ | ✗ | **✓（TTY 自动检测）** |
| **Codex CLI** | `codex exec` | text | ✗ | ✗ | ✓ |
| **Qwen Code** | `--non-interactive` | text | ✗ | ✗ | ✗ |
| **Qoder CLI** | `-p / --print` | text/json/stream-json | ✗ | ✗ | ✗ |
| **Aider** | `--message` | text | ✗ | ✗ | ✗ |
| **Copilot CLI** | `--full-auto` | text | ✗ | ✗ | ✗ |
| **Goose** | `goose run recipe.yaml` | text | ✗ | ✗ | ✓ |
| **SWE-agent** | `sweagent run-batch` | JSON 轨迹 | ✗ | **✓ $3/实例** | ✓ |
| **OpenHands** | Docker 执行 | EventStream | ✗ | ✗ | **✓（容器）** |

---

## 一、Claude Code：最完整的管道协议

> 来源：`claude --help` v2.1.83

### 基础管道

```bash
# 简单脚本调用
echo "修复 lint 错误" | claude -p

# 带成本控制
claude -p "重构 auth 模块" --max-budget-usd 5.00

# JSON 输出（单次结果）
claude -p "分析代码" --output-format json

# 流式 JSON（实时处理每个 token）
claude -p "修复 Bug" --output-format stream-json

# 结构化输出（JSON Schema 约束）
claude -p "列出所有 TODO" --json-schema '{"type":"array","items":{"type":"string"}}'
```

### `--bare` 最小模式（CI 专用）

```bash
claude --bare -p "运行测试" \
  --system-prompt "你是 CI 助手" \
  --allowed-tools "Bash,Read,Glob" \
  --no-session-persistence
```

**跳过**：hooks、LSP、插件同步、归因、auto-memory、后台预取、keychain 读取、CLAUDE.md 自动发现。
**保留**：Skills 仍可通过 `/skill-name` 使用。
**认证**：仅 `ANTHROPIC_API_KEY` 或 `apiKeyHelper`（OAuth/keychain 不可用）。
**环境变量**：设置 `CLAUDE_CODE_SIMPLE=1`。
**上下文**：必须显式提供 `--system-prompt`、`--add-dir`、`--mcp-config`、`--settings`、`--agents`、`--plugin-dir`。

### 三种输出格式对比

| 格式 | 用途 | 特点 |
|------|------|------|
| `text` | 简单脚本 | 纯文本，直接 grep/awk 处理 |
| `json` | 结构化处理 | 等待完成后输出单个 JSON 对象 |
| `stream-json` | 实时管道 | 逐 token 输出 JSON 行，支持 `--include-partial-messages` |

### 流式 JSON 双向协议

```bash
# 双向流式（stdin → stdout）
claude -p \
  --input-format stream-json \
  --output-format stream-json \
  --replay-user-messages  # 回显用户消息到 stdout（ACK 确认）
```

**`--replay-user-messages`**：仅在 stream-json 双向模式下有效，用于管道中确认消息已接收。

### CI 控制标志完整列表

| 标志 | 用途 | 限制 |
|------|------|------|
| `-p / --print` | 非交互管道模式 | 必须指定 |
| `--bare` | 最小初始化 | 需显式提供上下文 |
| `--output-format` | text/json/stream-json | 仅 `--print` |
| `--input-format` | text/stream-json | 仅 `--print` |
| `--json-schema` | JSON Schema 约束输出 | 仅 `--print` |
| `--max-budget-usd` | 成本上限（USD） | 仅 `--print` |
| `--no-session-persistence` | 禁止保存会话 | 仅 `--print` |
| `--fallback-model` | 模型过载降级 | 仅 `--print` |
| `--include-partial-messages` | 流式输出部分消息 | 仅 stream-json |
| `--replay-user-messages` | 回显确认 | 仅双向 stream-json |
| `--allowed-tools` | 限制可用工具 | — |
| `--disallowed-tools` | 禁止特定工具 | — |

---

## 二、Gemini CLI：TTY 自动检测

> 来源：01-overview.md

```bash
# 非 TTY 环境自动激活无头模式
echo "分析代码" | gemini

# 显式管道模式
gemini -p "检查安全漏洞"
```

**独有特性**：自动检测 `isatty()`，非 TTY 环境（CI/GitHub Actions）自动进入无头模式，无需显式标志。

---

## 三、Codex CLI：5 级审批模式 + Cloud 执行

> 来源：01-overview.md、02-commands.md

### 5 级审批模式（`--ask-for-approval`）

| 模式 | 行为 | CI 适用 |
|------|------|---------|
| `untrusted`（默认） | 每步都询问 | ✗ |
| `on-request` | 模型决定何时询问 | ✓ |
| `never` | 完全自动（无审批） | **✓（CI 最佳）** |
| `on-failure` | 仅失败时询问（已废弃） | ✗ |
| `granular` | 细粒度控制（v0.116.0 未实现） | — |

### 快捷模式

```bash
# 全自动（推荐 CI 模式）
codex --full-auto "修复所有测试"
# 等同于: --ask-for-approval on-request --sandbox workspace-write

# YOLO 模式（跳过所有检查，危险）
codex --dangerously-bypass-approvals-and-sandbox "..."
```

### Cloud 远程执行

```bash
codex cloud exec "fix all failing tests"   # 提交到云端
codex cloud status <TASK_ID>               # 查看状态
codex cloud list                            # 列出任务
codex cloud apply <TASK_ID>                # 将 diff 应用到本地
codex cloud diff <TASK_ID>                 # 查看 diff
```

Cloud 模式支持 best-of-N（1-4 次尝试），选择最佳结果。

---

## 四、Copilot CLI：Autopilot + GitHub Actions

> 来源：02-commands.md、EVIDENCE.md

### Autopilot 模式

```bash
# 自动持续执行
copilot --autopilot "重构 auth 模块"

# 限制自动继续次数
copilot --max-autopilot-continues 10 "..."

# 全权限
copilot --allow-all-tools --allow-all-paths "..."
```

### GitHub Actions 集成

```bash
# CI 中的非交互调用
copilot -p "修复 Issue #123" --allow-all-tools

# 环境变量控制
COPILOT_ALLOW_ALL=true copilot -p "..."
```

---

## 五、SWE-agent：批量评估模式

> 来源：swe-agent.md

```bash
# 单问题解决
sweagent run --issue "https://github.com/org/repo/issues/123"

# 批量 SWE-bench 评估
sweagent run-batch \
  --instances swe-bench:lite \
  --agent.model.name gpt-4o \
  --max-cost 3.00  # $3/实例成本上限
```

**输出**：JSON 轨迹文件 + Web Inspector 可视化。

---

## 四、Goose：Recipe 驱动自动化

```bash
# 执行 YAML 任务模板
goose run recipes/daily-report.yaml

# 定时调度
goose schedule add --recipe daily-report.yaml --cron "0 0 9 * * *"
```

Recipe 是 Goose 的 CI 等价物——参数化 YAML 模板 + Cron 调度。

---

## 五、跨 Agent CI 集成模式

| 模式 | 代表 | 适用场景 |
|------|------|---------|
| **管道协议** | Claude Code（stream-json） | 复杂 CI/CD 管道，需要实时处理 |
| **TTY 自动检测** | Gemini CLI | 简单 CI 脚本，零配置 |
| **批量执行** | SWE-agent（run-batch） | 大规模代码修复评估 |
| **任务模板** | Goose（Recipe） | 定期自动化任务 |
| **容器执行** | OpenHands（Docker） | 完全隔离的 CI 环境 |
| **审批模式** | Codex CLI（never）、Copilot（full-auto） | 无人值守执行 |

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | `claude --help` v2.1.83 | 本地二进制 |
| Gemini CLI | 01-overview.md | 开源 |
| SWE-agent | swe-agent.md | 开源 |
| Goose | goose.md | 开源 |
| Codex CLI | 01-overview.md + 02-commands.md | 二进制 + 官方文档 |
