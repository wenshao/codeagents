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

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Aider | 03-architecture.md + 02-commands.md | 开源 |
| Copilot CLI | 03-architecture.md（code-review.agent.yaml） | SEA 反编译 |
| Claude Code | 05-skills.md（/review 插件） | 二进制分析 |
| Codex CLI | 03-architecture.md（沙箱） | Rust 源码 + 官方文档 |
| Kimi CLI | 03-architecture.md + config.py | 开源 |
