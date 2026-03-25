# 38. 非交互/CI 模式深度对比

> AI 编程代理从"交互式助手"进入"CI/CD 自动化管道"的关键能力。各工具的脚本化支持从"无"到"完整 JSON 流式协议"。

## 总览

| 工具 | 主要标志 | 输出格式 | 结构化输出 | 成本控制 | 无头模式 |
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

# JSON 输出
claude -p "分析代码" --output-format json

# 流式 JSON（实时处理）
claude -p "修复 Bug" --output-format stream-json

# 结构化输出（JSON Schema 约束）
claude -p "列出所有 TODO" --json-schema '{"type":"array","items":{"type":"string"}}'
```

### `--bare` 最小模式

```bash
# CI/CD 专用：跳过所有非必要初始化
claude --bare -p "运行测试" \
  --system-prompt "你是 CI 助手" \
  --allowed-tools "Bash,Read,Glob"
```

跳过：hooks、LSP、插件同步、归因、auto-memory、后台预取、keychain、CLAUDE.md 自动发现。

### 流式 JSON 双向协议

```bash
# 双向流式（stdin → stdout）
claude -p \
  --input-format stream-json \
  --output-format stream-json \
  --replay-user-messages  # 回显确认
```

### 会话控制

| 标志 | 用途 |
|------|------|
| `--no-session-persistence` | 禁止保存会话（CI 场景） |
| `--fallback-model haiku` | 模型过载自动降级 |
| `--max-budget-usd 10` | 成本上限 |
| `--include-partial-messages` | 流式输出部分消息 |

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

## 三、SWE-agent：批量评估模式

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

## 五、跨工具 CI 集成模式

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

| 工具 | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | `claude --help` v2.1.83 | 本地二进制 |
| Gemini CLI | 01-overview.md | 开源 |
| SWE-agent | swe-agent.md | 开源 |
| Goose | goose.md | 开源 |
| Codex CLI | 01-overview.md + 02-commands.md | 二进制 + 官方文档 |
