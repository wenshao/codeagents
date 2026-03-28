# 36. 测试/Lint 反射循环深度对比

> "代码写完自动验证"是 AI 编程代理的核心能力差异。从"无任何验证"到"实际编译+运行测试+3 次反射重试"。

## 总览

| Agent | 自动测试 | 自动 Lint | 反射/重试 | 最大次数 | 验证方式 | 独特设计 |
|------|---------|---------|----------|---------|---------|---------|
| **Aider** | **✓** | **✓** | **✓ 3 次反射** | 3 | Lint/测试失败反馈→LLM 重试 | **唯一真正的自动反射循环** |
| **Copilot CLI** | **✓** | **✓** | ✗（隐式） | — | **实际编译+运行测试** | 可执行验证（非 LLM 推理） |
| **Claude Code** | ✗ | ✗ | ✓ 验证代理 | 1/issue | LLM 独立验证 | 80+ 置信度过滤 |
| **Codex CLI** | ✓（沙箱） | ✓（沙箱） | ✓ Guardian | 可配置 | 沙箱隔离执行 | OS 级安全沙箱 |
| **Kimi CLI** | ✗ | ✗ | ✓ 3 次/步 | 100 步×3 | 工具级重试 | tenacity 退避 |
| **Gemini CLI** | ✗ | ✗ | ✗（工具重试） | 100 轮 | 工具失败重试 | 无 Lint/测试特定循环 |
| **Qwen Code** | ✗ | ✗ | ✗ | — | 4 并行审查代理 | 多代理审计 |
| **Goose** | ✗ | ✗ | ✓ RetryManager | 可配置 | MCP 工具执行 | 无原生 Lint/测试 |
| **OpenCode** | ✗ | ✗ | ✓ SQLite 追踪 | — | 工具执行 | DB 持久化结果 |

---

## 一、Aider：3 次反射循环（唯一真正的自动验证）

> 源码：`base_coder.py:101`、`commands.py`

### 完整反射循环（源码：`base_coder.py`）

```
用户输入
  → format_messages()        # 系统提示 + 示例 + 仓库映射 + 文件 + 历史
  → send() → litellm.completion()  # 流式 LLM 调用
  → parse response
  → apply_updates()
  → apply_edits()            # 干运行检查 → 实际修改文件
  → auto_commit()            # Git 提交 + Co-authored-by 归因
  → auto_lint()  ──→ 失败？
  │   ├── clone() 当前 coder 实例  # 创建独立修复器
  │   ├── 错误信息发给 LLM
  │   ├── LLM 生成修复 → apply_edits() → auto_commit()
  │   └── 重新 lint（最多 3 次）
  → auto_test()  ──→ 失败？
  │   ├── add_on_nonzero_exit=True  # 非零退出码自动加入对话
  │   ├── 测试输出作为 LLM 上下文
  │   └── LLM 分析错误 → 修复 → 重新测试
  → reflected_message 检查  # 是否需要反射？
  → 3 次仍失败？→ 停止
```

### /lint 命令实现（源码：`commands.py`，54 行）

```python
# 伪代码（源码分析提取）
def cmd_lint(args):
    # 1. 确定目标文件
    files = args if args else get_dirty_files()  # 指定文件或所有 dirty 文件

    # 2. 执行 lint 检查
    result = run_lint_cmd(files)

    # 3. 发现问题 → 克隆 coder 实例自动修复
    if result.has_errors:
        fix_coder = self.clone()  # 独立修复环境
        fix_coder.run(lint_errors)  # LLM 生成修复
        auto_commit()  # 提交修复
```

### /test 命令实现（源码：`commands.py`，19 行）

```python
def cmd_test(args):
    test_cmd = args or self.test_cmd  # 用户指定或配置默认
    # add_on_nonzero_exit=True: 失败输出自动加入对话上下文
    return cmd_run(test_cmd, add_on_nonzero_exit=True)
    # → 非零退出 → 测试输出进入 LLM → LLM 分析修复 → 闭环
```

### 配置

```yaml
# .aider.conf.yml
auto-test: yes
test-cmd: pytest tests/
auto-commits: yes
lint-cmd: ruff check
```

### 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `max_reflections` | **3** | lint/测试失败后最大反思次数 |
| `auto-test` | 可配置 | 每次编辑后自动运行测试 |
| `auto-lint` | 可配置 | 每次编辑后自动运行 linter |
| `test-cmd` | 用户定义 | 测试命令（如 `pytest`） |
| `lint-cmd` | 用户定义 | lint 命令（如 `ruff check`） |

### /lint 和 /test 命令

```bash
/lint             # 运行 lint，发现问题自动创建修复 coder
/test pytest      # 运行测试，非零退出码添加到聊天
```

> **核心优势**：Aider 是唯一将"测试失败 → 反馈给 LLM → 自动修复 → 重新测试"完整自动化的工具。

---

## 二、Copilot CLI：实际编译+运行测试验证

> 来源：03-architecture.md（code-review.agent.yaml）

### code-review 代理的验证步骤

```yaml
tools: ["*"]   # 包括 bash，可以实际执行代码

# Step 3: Verify when possible
# - Can you build the code to check for compile errors?
# - Are there tests you can run to validate your concern?
# - Is the "bug" actually handled elsewhere in the code?
```

**关键区别**：

| 方式 | Copilot CLI | Claude Code |
|------|------------|-----------|
| 验证类型 | **实际编译+运行测试** | LLM 推理验证 |
| 确定性 | 100%（编译错误/测试失败） | 概率性（LLM 判断） |
| Agent | `bash`（构建/测试） | 独立验证代理 |
| 适用 | 客观错误（编译/测试） | 逻辑/安全问题 |

---

## 三、Claude Code：多代理验证流水线

> 来源：05-skills.md（/review 插件）

### 9 步流水线中的验证

```
Step 4: 并行审查（4 代理）
  ├── Sonnet: CLAUDE.md 合规审计
  ├── Opus: Bug 扫描
  └── Opus: 安全/逻辑分析

Step 5: 并行验证
  └── 每个标记问题由独立验证代理确认
      ├── Opus 验证 Bug
      └── Sonnet 验证合规

Step 6: 过滤
  └── 未通过验证的问题被剔除
```

**置信度阈值**：80/100，只有高置信度问题通过。

**假阳性率**：<1%（显式假阳性抑制）。

---

## 四、Codex CLI：沙箱隔离测试

> 来源：03-architecture.md

测试在 OS 级沙箱中执行：

| 平台 | 沙箱技术 | 网络 |
|------|---------|------|
| macOS | Seatbelt | 默认禁止 |
| Linux | Bubblewrap + Landlock + Seccomp | 默认禁止 |
| Windows | 受限令牌 | 防火墙控制 |

测试代码无法逃逸沙箱环境——即使测试中包含恶意代码也无害。

---

## 五、Kimi CLI：per-step 重试

> 源码：`kimisoul.py`、`config.py`

```
_step()
  → 工具调用
  → 失败？→ tenacity 指数退避重试
  → 初始 0.3s → 最大 5s → 抖动 0.5
  → 最多 3 次/步
```

**与 Aider 的区别**：Kimi 的重试是工具级别（API 错误重试），不是 Lint/测试反馈级别（语义修复）。

---

## 六、Gemini CLI：100 轮工具重试（非反射）

> 源码：`client.ts:81`

- `MAX_TURNS = 100` 硬编码
- 工具执行失败触发重试（非 lint/test 反馈级别）
- 重试策略：10 次 API 级退避（5s → 30s）
- 仅重试 429（速率限制）和 5xx（服务器错误）
- **无 lint/test 特定反射循环**

---

## 七、OpenCode：SQLite 追踪 + Tree-sitter 分析

> 源码：03-architecture.md

- **唯一使用 SQLite 数据库**（非 JSON 文件）的工具
- 3 张表（sessions/messages/files）追踪工具执行结果
- Tree-sitter Bash AST 解析：智能判断命令是否安全
- Doom Loop 保护：3 次连续拒绝自动中断

---

## "生成者不应评价自己"原则

> 来源：[Anthropic Engineering Blog](https://www.anthropic.com/engineering/harness-design-long-running-apps)（2026-03-24）

Anthropic 在长任务 harness 开发中发现了一个关键问题：**当 Agent 被要求评价自己产出的作品时，它会自信地夸赞——即使质量平庸**。

这解释了为什么各工具的验证架构都倾向于**分离生成和评估**：

| 工具 | 生成者 | 评估者 | 分离程度 |
|------|--------|--------|---------|
| **Claude Code /review** | Sonnet（变更摘要） | **独立 Opus 代理**（Bug 扫描 + 安全分析） | 完全分离 |
| **Copilot CLI /review** | Agent | **实际编译 + 运行测试**（非 LLM） | 完全分离（确定性验证） |
| **Aider 反射循环** | 主模型 | **lint/test 工具**（非 LLM） | 完全分离（确定性验证） |
| **Anthropic Harness** | Generator | **独立 Evaluator**（Playwright 测试） | 完全分离 |
| **Qwen Code Arena** | 多个 Generator | **用户**选优 | 生成分离，评估靠人 |

> **Anthropic 原文**："Tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work."（调校独立评估者比让生成者自我批评**容易得多**。）

**实践建议**：如果你在构建 Agent 验证流程，**永远不要让 Agent 评价自己的输出**。用独立代理、确定性工具（编译/测试）、或人类评审。

---

## 理想验证架构（未来方向）

目前没有任何工具同时实现：

```
AI 编辑 → 实际编译（Copilot） → 测试失败 → 反馈给 LLM（Aider） → 自动修复 → 重新测试 → 沙箱隔离（Codex） → 多代理审查（Claude Code）
```

| 组件 | 最佳实现者 | 其他工具缺失 |
|------|-----------|------------|
| 实际编译验证 | Copilot CLI | 大多数只做 LLM 推理 |
| 反射循环 | Aider（3 次） | 无自动 lint→fix 循环 |
| 沙箱隔离 | Codex CLI | 无 OS 级隔离 |
| 多代理审查 | Claude Code | 单代理验证 |

---

## Agent 评估方法论（来源：[Anthropic Engineering Blog](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)，2026-01-09）

Anthropic 总结的 Agent 评估最佳实践，直接影响测试反射循环的设计：

### 评估结果而非路径

> "There is a common instinct to check that agents followed very specific steps like a sequence of tool calls in the right order. We've found this approach too rigid and results in overly brittle tests, as agents regularly find valid approaches that eval designers didn't anticipate."

**对测试反射循环的启示**：Aider 的反射循环评估**测试是否通过**（结果），而非**修复步骤是否正确**（路径）——这与 Anthropic 的建议一致。

### Eval-Driven Development

> "Build evals to define planned capabilities before agents can fulfill them, then iterate until the agent performs well."

### 0% 通过率 = 任务有 Bug

> "With frontier models, a 0% pass rate across many trials (i.e. 0% pass@100) is most often a signal of a broken task, not an incapable agent."

### 真实案例：评估 Bug 导致 42% → 95% 的跳跃

> "Opus 4.5 initially scored 42% on CORE-Bench, until an Anthropic researcher found multiple issues: rigid grading that penalized '96.12' when expecting '96.124991...', ambiguous task specs, and stochastic tasks that were impossible to reproduce exactly. After fixing bugs...Opus 4.5's score jumped to 95%."

---

## 基础设施噪声：基准分数波动 6 个百分点（来源：[Anthropic Engineering Blog](https://www.anthropic.com/engineering/infrastructure-noise)，2026-02-03）

> "Infrastructure configuration can swing agentic coding benchmarks by several percentage points—sometimes more than the leaderboard gap between top models."

> "In internal experiments, the gap between the most- and least-resourced setups on Terminal-Bench 2.0 was 6 percentage points (p < 0.01)."

**对排行榜的启示**：

> "Until resource methodology is standardized, our data suggests that leaderboard differences below 3 percentage points deserve skepticism until the eval configuration is documented and matched."

> "A few-point lead might signal a real capability gap—or it might just be a bigger VM."

---

## Think Tool：复杂推理中的暂停思考（来源：[Anthropic Engineering Blog](https://www.anthropic.com/engineering/claude-think-tool)，2025-03-20）

Think Tool 让 Claude 在工具调用链中**暂停推理**，对测试验证场景有直接价值：

> "Extended thinking is all about what Claude does before it starts generating a response...The 'think' tool is for Claude, once it starts generating a response, to add a step to stop and think about whether it has all the information it needs to move forward."

| 场景 | 基线准确率 | Think Tool 准确率 | 提升 |
|------|-----------|-----------------|------|
| 航空客服（Tau-Bench） | 0.370 | 0.570 | **+54%** |
| SWE-bench | 基线 | +1.6% | p < .001 |

> "The 'think' tool is better suited for when Claude needs to...analyze tool outputs carefully in long chains of tool calls, navigate policy-heavy environments...or make sequential decisions where each step builds on previous ones and mistakes are costly."

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Aider | 03-architecture.md + 02-commands.md | 开源 |
| Copilot CLI | 03-architecture.md（code-review.agent.yaml） | SEA 反编译 |
| Claude Code | 05-skills.md（/review 插件） | 二进制分析 |
| Codex CLI | 03-architecture.md（沙箱） | Rust 源码 + 官方文档 |
| Kimi CLI | 03-architecture.md + config.py | 开源 |
