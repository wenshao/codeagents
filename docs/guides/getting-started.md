# 入门指南

本指南帮助你选择并开始使用 Code Agent CLI 工具。

## 选择合适的工具

### 决策树

```
                    开始
                      │
                      ▼
          ┌───────────────────────┐
          │ 你的优先级是什么？     │
          └───────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌────────┐      ┌─────────┐      ┌──────────┐
│ 隐私    │      │ 速度    │      │ 功能      │
└────┬───┘      └────┬────┘      └────┬─────┘
     │               │                │
     ▼               ▼                ▼
 TabbyML/       Copilot CLI      Claude Code
 本地           Gemini CLI        SWE-agent
     │               │                │
     │               │                │
     └───────────────┴────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  Git 重度使用？  │
            └────────┬────────┘
                     │
           ┌─────────┴─────────┐
           │                   │
          是                   否
           │                   │
           ▼                   ▼
       Aider            Cline/Goose
```

### 快速推荐

| 使用场景 | 推荐 | 替代品 |
|----------|---------------|-------------|
| 日常编码 | Claude Code | Aider |
| Git 重度工作流 | Aider | Claude Code |
| GitHub 生态 | Copilot CLI | Continue |
| 中文开发者 | Qwen Code | Kimi CLI |
| 免费额度高 | Qwen Code | Gemini CLI |
| 学习 | mini-swe-agent | Aider |
| 隐私/自托管 | TabbyML | OpenHands |
| 完全自动化 | OpenHands | SWE-agent |
| 模型灵活性 | Goose | Continue |
| IDE 优先 | Cline | Continue |
| 终端替代品 | Warp | Gemini CLI |

## 安装快速入门

### Claude Code

```bash
# 安装
npm install -g @anthropic-ai/claude-code

# 设置
claude
# 按提示输入 API key

# 首次使用
claude "帮我理解这个代码库"
```

### Aider

```bash
# 安装
pip install aider-chat

# 设置
cd your-project
aider

# 首次使用
aider --message "给 main.py 添加错误处理"
```

### Qwen Code (阿里云)

```bash
# 安装（需要 Node.js 20+）
npm install -g @qwen-code/qwen-code@latest

# 或使用 Homebrew
brew install qwen-code

# 验证安装
qwen --version

# 首次使用
qwen
```

### Kimi CLI (月之暗面)

```bash
# 1. 先安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 安装 Kimi CLI
uv tool install kimi-cli

# 3. 验证安装
kimi --version

# 首次使用（会引导配置）
kimi
```

### GitHub Copilot CLI

```bash
# 安装
brew install copilot-cli

# 设置
copilot-cli auth login

# 首次使用
gh copilot explain "kubectl get pods"
```

### Cline

```bash
# 通过 VS Code 安装
# 1. 打开 VS Code
# 2. Ctrl+Shift+X（扩展）
# 3. 搜索 "Cline"
# 4. 安装

# 首次使用
# 打开命令面板 -> "Cline: Start New Task"
```

### SWE-agent

```bash
# 克隆
git clone https://github.com/princeton-nlp/SWE-agent.git
cd SWE-agent

# 安装
pip install -e .

# 首次使用
python run.py --problem_type princeton-nlp/SWE-agent#0
```

## 安装后的第一步

### 1. 设置 API 密钥

```bash
# Claude (Anthropic)
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Google Gemini
export GOOGLE_API_KEY="..."

# Qwen Code (阿里云)
export QWEN_API_KEY="sk-..."

# Kimi CLI (月之暗面)
export KIMI_API_KEY="sk-..."

# 添加到 ~/.bashrc 或 ~/.zshrc 以持久化
```

### 2. 从简单任务开始

不要从复杂重构开始。尝试：

```bash
# 解释代码
agent "解释这个函数的作用"

# 生成测试
agent "为 auth.py 编写单元测试"

# 修复 bug
agent "修复 user.py 中的空指针异常"

# 添加文档
agent "给这个文件中的所有函数添加文档字符串"
```

### 3. 进阶到复杂任务

熟练后：

```bash
# 多文件编辑
agent "重构认证系统以使用 JWT"

# 功能实现
agent "添加用户首选项的新 API 端点"

# 代码审查
agent "审查上次提交的更改"
```

## 常见工作流

### 工作流 1：使用 Aider 进行测试驱动开发

```bash
# 启动 aider
aider

# 先让它编写测试
"为新用户注册功能编写测试"

# 然后实现
"实现通过这些测试的功能"

# Aider 自动运行测试并修复失败
```

### 工作流 2：使用 Claude Code 进行代码审查

```bash
# 审查 PR
claude "审查 PR #123"

# 获取解释
claude "解释此 PR 中的架构更改"

# 应用建议
claude "应用审查中的建议更改"
```

### 工作流 3：使用 SWE-agent 修复 Bug

```bash
# 给它一个 GitHub issue
python run.py \
  --issue_url https://github.com/user/repo/issues/42 \
  --model claude-sonnet-4

# 它将：
# 1. 分析问题
# 2. 找到相关代码
# 3. 实现修复
# 4. 测试
# 5. 创建 PR
```

### 工作流 4：使用 Cline 进行交互式开发

```bash
# 在 VS Code 中使用 Cline
"Cline，帮我构建任务管理的 REST API"
# Cline 将规划、请求批准、然后实现
```

## 配置技巧

### 优化性能

```yaml
# ~/.aider/config.yml
model: claude-3-5-sonnet  # 比 Opus 快
auto-commit: true
auto-test: false  # 禁用以提高速度
```

### 优化质量

```bash
# Claude Code 使用最佳模型
claude --model claude-opus-4-6
```

### 优化成本

```yaml
# 使用较小模型进行探索
model: claude-haiku-4  # 最便宜
# 切换到 Opus 进行最终实现
```

## 故障排除

### 常见问题

**问题**："找不到 API key"
```bash
# 检查环境变量
echo $ANTHROPIC_API_KEY
# 如果缺失则添加到 shell 配置文件
```

**问题**："上下文窗口超出"
```bash
# 减少上下文范围
# 专注于特定文件而非整个仓库
```

**问题**："权限被拒绝"
```bash
# 检查文件权限
ls -la
# 根据需要调整
chmod +x script.sh
```

## 最佳实践

1. **从小开始**：从简单的单文件任务开始
2. **审查更改**：始终审查代理更改的内容
3. **使用 Git**：让代理进行更改之前提交
4. **具体明确**：清晰的提示获得更好的结果
5. **迭代**：根据结果优化请求
6. **学习模式**：注意什么对你的工作流有效

## 下一步

1. **选择工具**：根据决策树
2. **安装配置**：按照指南
3. **简单任务**：学习工具
4. **复杂工作流**：随着熟练度提高
5. **高级功能**：如 MCP、自定义技能

## 相关资源

- [工具文档](../tools/) - 详细工具指南
- [功能对比](../comparison/features.md) - 横向对比
- [架构解析](../architecture/overview.md) - 代理如何工作
- [基准测试](../benchmarks/) - 性能数据
