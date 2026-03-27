# 8. 故障排查指南

## 简介

本指南汇总了主流 AI 编程 CLI 工具在日常使用中最常遇到的问题及其解决方案。涵盖 Claude Code、Aider、Cursor、Codex CLI 和 Copilot CLI 等工具。

每个问题按 **症状 -> 原因 -> 解决方案** 的格式组织，并附带实际的错误信息和修复命令，方便快速定位和解决。

建议先阅读「通用问题」部分，因为许多工具共享相同的底层问题（如 API Key 配置、网络代理等）。如果通用部分未能解决你的问题，再查阅对应工具的专项章节。

---

## 目录

1. [通用问题](#通用问题)
2. [Claude Code 常见问题](#claude-code-常见问题)
3. [Aider 常见问题](#aider-常见问题)
4. [Cursor 常见问题](#cursor-常见问题)
5. [Codex CLI 常见问题](#codex-cli-常见问题)
6. [Copilot CLI 常见问题](#copilot-cli-常见问题)
7. [性能优化建议](#性能优化建议)

---

## 通用问题

### API Key 配置错误

**症状：**

```
Error: Invalid API key provided
Error: Authentication failed. Please check your API key.
401 Unauthorized
```

**原因：**

- 环境变量未设置或拼写错误
- API Key 已过期或被撤销
- 使用了错误平台的 Key（例如将 OpenAI Key 用于 Anthropic 接口）

**解决方案：**

1. 确认环境变量已正确导出：

```bash
# Anthropic
echo $ANTHROPIC_API_KEY

# OpenAI
echo $OPENAI_API_KEY

# Google
echo $GEMINI_API_KEY
```

2. 如果为空，在 shell 配置文件中添加：

```bash
# ~/.bashrc 或 ~/.zshrc
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

3. 重新加载配置：

```bash
source ~/.bashrc
```

4. 前往对应平台的控制台验证 Key 是否仍然有效。

---

### 网络代理/VPN 问题

**症状：**

```
Error: connect ETIMEDOUT
Error: unable to verify the first certificate
RequestError: self-signed certificate in certificate chain
```

**原因：**

- 企业代理或 VPN 拦截了 HTTPS 请求
- 代理环境变量未正确设置
- 自签名证书未被信任

**解决方案：**

1. 设置代理环境变量：

```bash
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1"
```

2. 如果遇到证书问题，临时禁用严格验证（仅限调试）：

```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
```

3. 更推荐的做法是将企业 CA 证书添加到系统信任链：

```bash
# Linux
sudo cp company-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# macOS
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain company-ca.crt
```

---

### 模型速率限制

**症状：**

```
Error: 429 Too Many Requests
Rate limit exceeded. Please retry after X seconds.
You have exceeded your current quota.
```

**原因：**

- 短时间内发送了过多请求
- 账户的 API 用量已达到配额上限
- 使用了高需求模型而账户层级不足

**解决方案：**

1. 等待错误信息中提示的冷却时间后重试。
2. 检查账户用量面板，确认是否需要升级计划。
3. 在脚本中实现指数退避重试：

```bash
# 大多数工具内置了重试逻辑，但如果手动调用 API：
for i in 1 2 4 8 16; do
  curl -s https://api.anthropic.com/... && break
  echo "速率限制，等待 ${i} 秒..."
  sleep $i
done
```

4. 考虑切换到用量较低的模型（如 claude-sonnet 替代 claude-opus）。

---

### 上下文窗口超限

**症状：**

```
Error: This model's maximum context length is exceeded
Error: prompt is too long
Token count exceeds the model's context window
```

**原因：**

- 会话历史累积的 token 数量超过模型上限
- 一次性添加了过多文件到上下文
- 系统提示词本身占用了大量 token

**解决方案：**

1. 开启新会话，清除历史上下文。
2. 减少同时加载到上下文中的文件数量。
3. 使用 `.gitignore` 或工具专属的忽略配置排除不必要的文件：

```bash
# Claude Code: .claudeignore
# Aider: .aiderignore
node_modules/
dist/
*.min.js
```

4. 对大型文件，只引用需要修改的部分而不是整个文件。

---

### 权限被拒

**症状：**

```
Error: EACCES: permission denied
Permission denied (publickey)
sudo: a terminal is required to read the password
```

**原因：**

- 当前用户对目标目录没有写入权限
- 全局安装 npm 包时需要提升权限
- Git SSH 密钥未配置

**解决方案：**

1. 文件系统权限问题：

```bash
# 检查当前目录权限
ls -la

# 修复所有权
sudo chown -R $(whoami) /path/to/directory
```

2. npm 全局安装权限：

```bash
# 推荐：使用 nvm 管理 Node.js，避免 sudo
nvm install --lts
nvm use --lts

# 或者修改 npm 全局目录
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH
```

3. Git SSH 权限：

```bash
ssh-keygen -t ed25519 -C "your@email.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

---

## Claude Code 常见问题

### 安装失败（Node.js 版本、npm 权限）

**症状：**

```
npm error engine Unsupported engine
npm error notsup Required: {"node":">=18.0.0"}
npm ERR! code EACCES
```

**原因：**

- Node.js 版本低于 18.0.0
- 使用 `sudo npm install -g` 导致权限混乱
- npm 缓存损坏

**解决方案：**

1. 确认 Node.js 版本：

```bash
node --version
# 需要 v18.0.0 或更高
```

2. 使用 nvm 升级：

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
nvm use 22
```

3. 清除 npm 缓存后重新安装：

```bash
npm cache clean --force
npm install -g @anthropic-ai/claude-code
```

---

### 沙箱限制（macOS sandbox-exec 错误）

**症状：**

```
sandbox-exec: pattern serialization length exceeds maximum
Error: Command failed with signal SIGKILL
deny(1) file-read-data /path/to/file
```

**原因：**

- macOS 沙箱配置文件中的规则条目过多
- 项目目录路径包含特殊字符
- 沙箱配置与系统版本不兼容

**解决方案：**

1. 减少 `.claudeignore` 中不必要的否定规则来降低沙箱规则数量。
2. 将项目移到路径较短且不含特殊字符的目录：

```bash
# 避免
/Users/名前/Projects/我的项目/

# 推荐
/Users/username/projects/my-project/
```

3. 如果问题持续，尝试禁用沙箱（仅限受信任的项目）：

```bash
claude --dangerously-skip-permissions
```

---

### MCP 服务器连接失败

**症状：**

```
Error: MCP connection failed
Error: spawn <command> ENOENT
MCP server exited with code 1
```

**原因：**

- MCP 服务器的可执行文件路径不正确
- 配置文件语法错误
- 服务器依赖未安装

**解决方案：**

1. 检查 MCP 配置文件的正确性：

```bash
# 查看 Claude Code MCP 配置
cat ~/.claude/claude_desktop_config.json
```

2. 确认服务器可执行文件存在：

```bash
which mcp-server-filesystem
# 如果未找到，重新安装
npm install -g @anthropic-ai/mcp-server-filesystem
```

3. 验证配置格式：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-filesystem", "/path/to/dir"]
    }
  }
}
```

4. 手动启动服务器查看详细错误日志：

```bash
npx -y @anthropic-ai/mcp-server-filesystem /path/to/dir
```

---

### 会话恢复失败

**症状：**

```
Error: Session not found
Error: Failed to resume conversation
Could not load previous session
```

**原因：**

- 会话文件已损坏或被删除
- Claude Code 版本升级导致会话格式不兼容
- 磁盘空间不足

**解决方案：**

1. 检查磁盘空间：

```bash
df -h ~
```

2. 列出已有会话：

```bash
claude --resume
```

3. 如果无法恢复，开启新会话并通过 `--continue` 标志继续最近的对话：

```bash
claude --continue
```

4. 清理旧会话数据：

```bash
ls -la ~/.claude/projects/
# 可安全删除过旧的会话目录
```

---

### Token 消耗过高

**症状：**

- 账单金额远超预期
- 简单任务却消耗大量 token
- API 用量面板显示异常高的输入 token 数

**原因：**

- 每次对话都会发送完整的会话历史
- 大型文件被完整包含在上下文中
- 未配置忽略规则，导致无关文件被读取

**解决方案：**

1. 创建 `.claudeignore` 文件排除不需要的文件：

```
node_modules/
.git/
dist/
build/
*.lock
*.log
```

2. 定期开启新会话避免历史累积：

```bash
# 而不是在同一会话中进行数十轮对话
claude
```

3. 使用更具针对性的指令，避免模糊的开放式问题。
4. 在 Claude Code 设置中配置费用上限。

---

## Aider 常见问题

### Git 仓库未初始化

**症状：**

```
Error: No git repo found
git repo not found in /path/to/directory or any parent directory
```

**原因：**

- 当前目录不是 Git 仓库
- Aider 要求在 Git 仓库中运行以追踪文件变更

**解决方案：**

1. 初始化 Git 仓库：

```bash
cd /path/to/project
git init
git add .
git commit -m "Initial commit"
```

2. 如果不想使用 Git 追踪，可以用 `--no-git` 参数：

```bash
aider --no-git
```

---

### 模型不支持的编辑格式

**症状：**

```
Error: Model does not support the selected edit format
Model X does not support whole edit format
Falling back to diff edit format
```

**原因：**

- 不同模型对编辑格式（whole、diff、udiff）的支持能力不同
- 使用了小参数模型但选择了高级编辑格式

**解决方案：**

1. 让 Aider 自动选择最佳格式（默认行为）。
2. 手动指定兼容的编辑格式：

```bash
# 对能力较强的模型
aider --edit-format diff

# 对能力较弱的模型
aider --edit-format whole
```

3. 在 `.aider.conf.yml` 中持久化配置：

```yaml
edit-format: diff
```

---

### repo-map 生成慢

**症状：**

- Aider 启动时在 "Building repo map..." 步骤卡住很久
- 大型仓库中首次启动需要数分钟

**原因：**

- 仓库文件数量庞大
- tree-sitter 解析大量源文件耗时
- 未配置 `.aiderignore` 排除无关目录

**解决方案：**

1. 创建 `.aiderignore` 排除不需要的目录：

```
node_modules/
vendor/
.venv/
dist/
build/
__pycache__/
```

2. 降低 repo-map 的 token 预算：

```bash
aider --map-tokens 1024
```

3. 完全禁用 repo-map（会降低 Aider 对仓库的全局理解）：

```bash
aider --map-tokens 0
```

---

### LiteLLM 兼容性

**症状：**

```
litellm.exceptions.BadRequestError
NotFoundError: model "xxx" not found
litellm.APIConnectionError
```

**原因：**

- Aider 通过 LiteLLM 连接非原生支持的 API 提供商
- 模型名称格式不正确
- LiteLLM 版本与 Aider 不兼容

**解决方案：**

1. 确保模型名称使用正确的前缀格式：

```bash
# OpenAI 兼容 API
aider --model openai/my-model --openai-api-base http://localhost:8000/v1

# Ollama
aider --model ollama/codellama

# Azure
aider --model azure/my-deployment
```

2. 更新 LiteLLM 到兼容版本：

```bash
pip install --upgrade litellm
```

3. 设置自定义 API Base URL：

```bash
export OPENAI_API_BASE="http://localhost:11434/v1"
aider --model openai/codellama
```

---

## Cursor 常见问题

### CLI 命令未找到

**症状：**

```
bash: cursor: command not found
zsh: command not found: cursor
```

**原因：**

- Cursor 的 CLI 路径未添加到系统 PATH
- 未在 Cursor 内运行 "Install 'cursor' command" 操作

**解决方案：**

1. 在 Cursor 编辑器内安装 CLI 命令：
   - 打开 Cursor
   - 按 `Cmd+Shift+P`（macOS）或 `Ctrl+Shift+P`（Linux）
   - 搜索并运行 "Install 'cursor' command in PATH"

2. 手动添加到 PATH：

```bash
# macOS
export PATH="/Applications/Cursor.app/Contents/Resources/app/bin:$PATH"

# Linux
export PATH="/usr/share/cursor/bin:$PATH"
```

3. 将上述 export 添加到 `~/.bashrc` 或 `~/.zshrc` 中使其永久生效。

---

### Background Agent 不可用

**症状：**

- Background Agent 选项灰色不可选
- 提示 "Background Agent is not available for your account"
- 任务提交后无响应

**原因：**

- 账户计划不支持 Background Agent 功能
- Cursor 版本过旧
- 网络环境阻止了与后端服务的连接

**解决方案：**

1. 确认账户为 Pro 或 Business 计划。
2. 更新 Cursor 到最新版本：
   - 打开 Cursor -> Help -> Check for Updates
3. 检查是否有防火墙或代理阻止了 WebSocket 连接。
4. 尝试退出登录后重新登录 Cursor 账户。

---

### 扩展冲突

**症状：**

- AI 自动补全不工作或异常
- 编辑器变得极慢
- 功能行为不符合预期

**原因：**

- 同时安装了多个 AI 补全扩展（如 Copilot + Cursor 内置 AI）
- 扩展版本与 Cursor 版本不兼容
- 扩展配置互相覆盖

**解决方案：**

1. 禁用冲突的 AI 扩展：

```
# 在 Cursor 中通常不需要安装 GitHub Copilot 扩展
# Cursor 自带 AI 功能，两者会冲突
```

2. 通过 CLI 列出已安装的扩展：

```bash
cursor --list-extensions
```

3. 禁用或卸载有冲突的扩展：

```bash
cursor --disable-extension GitHub.copilot
```

4. 如果问题持续，重置扩展目录：

```bash
mv ~/.cursor/extensions ~/.cursor/extensions.bak
# 重启 Cursor 后重新安装需要的扩展
```

---

## Codex CLI 常见问题

### 沙箱启动失败

**症状：**

```
Error: Failed to create sandbox
Error: Container runtime not available
sandbox creation failed: permission denied
```

**原因：**

- 系统缺少容器运行时（Docker）
- 当前用户不在 docker 用户组中
- 内核不支持所需的沙箱特性

**解决方案：**

1. 确认 Docker 已安装且运行中：

```bash
docker --version
docker ps
```

2. 将当前用户添加到 docker 组：

```bash
sudo usermod -aG docker $USER
# 需要重新登录使其生效
newgrp docker
```

3. 使用降级的沙箱模式：

```bash
codex --full-auto
# 或指定网络访问策略
codex --full-auto --net
```

---

### Docker 未安装

**症状：**

```
Error: docker: command not found
Cannot connect to the Docker daemon
Is the docker daemon running?
```

**原因：**

- Docker 未安装
- Docker 服务未启动
- Docker Desktop（macOS/Windows）未运行

**解决方案：**

1. 安装 Docker：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker

# macOS
brew install --cask docker
# 然后启动 Docker Desktop 应用
```

2. 启动已安装但未运行的 Docker 服务：

```bash
sudo systemctl start docker
sudo systemctl status docker
```

3. 如果不想使用 Docker，Codex CLI 在某些模式下可以不依赖 Docker 运行，但安全隔离能力会降低。

---

## Copilot CLI 常见问题

### 认证失败

**症状：**

```
Error: Not authenticated
Error: GitHub token is invalid or expired
You must be logged in to use GitHub Copilot
```

**原因：**

- 未登录 GitHub 账户
- OAuth token 已过期
- GitHub Copilot 订阅未激活

**解决方案：**

1. 重新进行身份认证：

```bash
gh auth login
gh auth status
```

2. 确认 Copilot CLI 已安装：

```bash
copilot --version
# 如未安装，重新安装：
brew install copilot-cli
# 或
curl -fsSL https://gh.io/copilot-install | bash
```

3. 检查 Copilot 订阅状态：
   - 前往 https://github.com/settings/copilot 确认订阅处于活跃状态。

4. 刷新认证 token：

```bash
gh auth refresh -s copilot
```

---

### Premium request 用尽

**症状：**

```
You've used all your premium requests for this period
Premium model not available, falling back to default
```

**原因：**

- 当月的 premium 模型请求配额已用完
- 使用了高级模型（如 Claude Opus、GPT-4o）消耗了额外配额
- 团队/组织的共享配额已耗尽

**解决方案：**

1. 查看当前用量：
   - 前往 https://github.com/settings/copilot 查看用量详情。

2. 切换到非 premium 模型继续使用：

```bash
# 在 Copilot Chat 中手动选择 GPT-4o-mini 等基础模型
```

3. 等待下个计费周期配额重置。
4. 如果经常用尽配额，考虑升级到更高级别的计划或购买额外配额。

---

## 性能优化建议

### 减少 token 消耗

以下策略适用于所有基于 API 的 AI 编程工具：

1. **精确描述需求**：避免模糊的提示词，直接说明要修改哪个文件的哪个函数。

2. **配置忽略文件**：

```bash
# .claudeignore / .aiderignore / .cursorignore
node_modules/
.git/
dist/
build/
coverage/
*.min.js
*.map
package-lock.json
yarn.lock
```

3. **分割大任务**：将复杂的重构拆分为多个小步骤，每步只关注一个文件或一个函数。

4. **及时开启新会话**：当对话上下文变得很长时，新开一个会话比在旧会话中继续更省 token。

5. **使用适当的模型**：
   - 简单任务（格式化、重命名）：使用 Sonnet 或 Haiku 等轻量模型
   - 复杂任务（架构设计、疑难调试）：使用 Opus 等高级模型

---

### 加速响应

1. **选择就近的 API 端点**：如果提供商支持多区域，选择延迟最低的区域。

2. **启用流式输出**：大多数工具默认启用，确保未被禁用。

```bash
# Aider 确保流式输出开启
aider --stream
```

3. **减少上下文大小**：上下文越小，首 token 响应时间越快。

4. **使用本地模型进行简单任务**：

```bash
# 使用 Ollama 运行本地模型
ollama pull codellama
aider --model ollama/codellama
```

5. **避免高峰时段**：API 服务在工作日的工作时间（美国时区）通常负载更高。

---

### 上下文管理技巧

1. **只添加必要的文件**：

```bash
# Aider：只添加需要修改的文件
aider src/main.py src/utils.py
# 而不是
aider src/*.py
```

2. **善用项目级说明文件**：

```bash
# Claude Code: CLAUDE.md
# Aider: .aider.conf.yml
# 在项目根目录放置项目说明，避免每次对话重复解释
```

3. **使用引用而非粘贴**：指示工具去读取某个文件，而不是在对话中粘贴大段代码。

4. **定期总结上下文**：对于长时间的调试会话，每隔几轮要求工具总结当前进展，然后在新会话中引用总结继续。

5. **分层管理配置**：

```
# Claude Code 配置优先级（从高到低）：
# 1. 系统级设置（管理员策略）
# 2. 工作区级设置（项目 .claude/ 目录）
# 3. 用户级设置（~/.claude/）
```

---

## 快速诊断流程

遇到问题时，按以下顺序排查：

```
1. 检查工具版本是否为最新
   $ claude --version / aider --version / cursor --version

2. 检查 API Key 是否有效
   $ echo $ANTHROPIC_API_KEY

3. 检查网络连通性
   $ curl -s https://api.anthropic.com/v1/messages -o /dev/null -w "%{http_code}"

4. 检查磁盘空间和权限
   $ df -h ~ && ls -la .

5. 查看工具日志
   $ 各工具的日志位置不同，参见对应工具的文档

6. 搜索 GitHub Issues
   $ gh search issues "你的错误信息" --repo=<tool-repo>
```

如果以上步骤均未解决问题，建议在对应工具的 GitHub 仓库中提交 issue，并附上：
- 操作系统和版本
- 工具版本
- 完整的错误日志
- 复现步骤

## 相关资源

- [入门指南](./getting-started.md) — 安装、认证、首次使用
- [配置示例](./config-examples.md) — 各 Agent 配置格式对比
- [系统要求对比](../comparison/system-requirements.md) — 运行时版本 + 二进制大小
- [迁移指南](./migration.md) — Agent 间迁移步骤
- [上下文管理](./context-management.md) — 压缩阈值 + Token 管理
