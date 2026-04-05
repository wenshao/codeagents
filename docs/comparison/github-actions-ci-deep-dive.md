# Qwen Code 改进建议 — GitHub Actions CI (Automated Workflow)

> 核心洞察：现代 AI 代码助手必须无缝融入研发流程。将 Agent 限制在开发者的本地终端中，只能解决“编写代码”的痛点。而将 Agent 集成到 GitHub Actions 等 CI/CD 系统中，通过 Issue/PR 的 `@mention` 自动触发响应，并支持结构化的 `--json-schema` 输出，能真正实现“无人值守的自动化研发闭环”。Claude Code 提供了高度集成的 `/install-github-app` 命令，一键打通从鉴权到 CI YAML 的全流程；而 Qwen Code 目前缺少这一桥梁。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、集成现状与痛点分析

### 1. Qwen Code 现状：仍停留在“本地玩具”阶段
尽管 Qwen Code 已经有了基础的 CLI 执行能力，甚至社区或实验分支中也有类似 `.github/workflows/qwen-code-pr-review.yml` 的尝试，但它的集成门槛极高：
- **无自动化配置**：开发者必须自己去查文档，复制 YAML 模板，手动进入 GitHub 设置页生成并配置 API Key 等 Secrets。
- **缺乏自然交互**：不支持通过在 Issue 或 PR 的评论里 `@qwen` 来直接召唤 Agent 进行自动修改或代码审查。
- **CI 环境安全性未知**：如果 Agent 在 CI 环境下运行不受限的 Shell 命令，很容易泄露像 `GITHUB_TOKEN` 等关键环境变量。

### 2. Claude Code 解决方案：极致的一键集成
Claude Code 提供了一套惊艳的 `/install-github-app` 全自动向导体验。开发者只需在本地运行这个命令：
1. **自动权限校验**：CLI 会利用开发者当前的 Auth Token 验证对当前 Git Remote 仓库是否有写入权限。
2. **生成 YAML 模板**：自动生成包含 `@claude` mention 触发器和 Code Review 自动化审查流程的 Workflow 文件。
3. **静默拉取与 PR 提交**：自动在后台 checkout 一个新的 branch，并通过 `gh api` 甚至原生 API 配置好所需的 Secrets，直接打开一个准备好的 PR 让开发者合并。

#### CI / Headless 运行时的底层支持
为了支撑 CI 运行，Claude Code 在其 `-p / --print` 无头模式（Headless Mode）中埋入了大量优化：
- `--output-format json`：支持输出机器可读格式，便于 CI 脚本链式调用后续步骤。
- `--permission-mode dontAsk`：在 CI 里没人能按 Y 回车。任何超出预设白名单的敏感操作直接默认拒绝。
- **CI 环境脱敏** (`utils/subprocessEnv.ts`)：一旦检测到在 CI 运行，会拦截并清洗所有包含 `SSH_SIGNING_KEY` 或 `ACTIONS_RUNTIME_*` 等敏感环境变量，防止模型利用 Bash 工具泄露云端凭证。

## 二、Qwen Code 改进路径 (P1 优先级)

为了将 Qwen Code 从“单机工具”升级为“研发流程基础设施”，我们需要构建强大的平台集成系统。

### 阶段 1：开发 Headless/CI 模式基础设施
在现有的命令支持之上，增强 `qwen-code` 的非交互模式选项：
- 支持 `--permission-mode auto-deny`（无人值守时拒绝危险操作）。
- 添加 `--json-schema <path>` 参数，确保模型在退出时的总结输出必须符合外部 CI 脚本所需的 JSON 格式，不合规则自动重试。
- 加入环境变量净化器：在 Spawn shell 工具前，剥离敏感变量。

### 阶段 2：开发官方 GitHub Action 模板
创建 `QwenLM/qwen-code-action` 仓库。
编写两个核心 Workflow 模板：
1. **Mention 触发器**：监听 `issue_comment.created` 等事件。当识别到评论正文中包含 `@qwen-code` 时，将评论内容作为 Prompt 传给 Agent 并在对应 PR 的工作区内运行。
2. **Code Review 触发器**：在 `pull_request` 更新时自动拉起审查。

### 阶段 3：实现在 CLI 中一键安装 (Install Command)
实现 `/install-github-app` （或更泛用的 `/install-ci`）命令：
```typescript
// 伪代码
export async function installGitHubActions() {
    await checkRepoPermissions();
    await generateWorkflowYAML();
    await setGitHubSecrets(apiKey); // 通过 GitHub API 或 gh cli
    await createPullRequest("Setup Qwen Code Actions");
}
```

## 三、改进收益评估
- **实现成本**：中。需要集成 GitHub API，编写 Action 容器镜像，以及完善 CLI 参数。
- **直接收益**：
  1. **指数级提高传播率**：一键安装带来极低的上手门槛，吸引更多企业用户尝试自动化。
  2. **从助手走向自动机**：研发团队可以在下班前在 Issue 中 `@qwen-code please fix this bug`，第二天直接查看生成的 PR。