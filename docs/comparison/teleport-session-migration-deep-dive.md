# Qwen Code 改进建议 — /teleport 跨端会话迁移 (Session Teleportation)

> 核心洞察：现代开发越来越倾向于混合计算——在 Web 端（如云 IDE、网页版 Claude）进行大架构的系统规划与发散性讨论，而在本地终端（CLI）执行那些需要修改本机文件、运行测试套件的实操任务。Claude Code 开创性地实现了 `/teleport` 功能，允许开发者将云端 Web 会话无缝“传送”到本地终端中，实现跨端状态接力；而 Qwen Code 目前只能各自为战，Web 与 CLI 会话之间存在巨大的信息断层。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、跨终端状态断层的痛点

### 1. Qwen Code 现状：信息孤岛
假设你在手机上或网页版的 Qwen Chat 中，花了一个小时和模型讨论一个极其复杂的重构方案。
- **痛点一（上下文遗失）**：当你回到电脑前打开终端输入 `qwen-code` 准备动手改代码时，本地 Agent 对你刚在网页上讨论的方案一无所知。
- **痛点二（人工搬运低效）**：你不得不将网页上的关键讨论（Prompt、生成的代码片段结构）复制粘贴成一个巨大的 Prompt 再次喂给本地 CLI，浪费极大的 Token 和时间。

### 2. Claude Code 的解决方案：一键时空传送
在 Claude Code 的 `utils/teleport/` 和 `commands/teleport/` 目录中，隐藏着一个强大的会话桥接能力。

当开发者在终端输入 `/teleport` 时，系统会：
1. **身份认证对齐**：使用底层的 OAuth Token 向 Anthropic 云端拉取当前账号在 Web 端（或云环境如 CCR）活跃的 Session 列表。
2. **Git 状态检查**：在迁移前，会严格检查本地的 Git Tree 是否干净（Clean State）。
3. **状态注入与 Git Bundle**：
   - 云端的 Agent 可能会把生成好的代码草稿打包成一个隔离的 git branch 或者 patch。
   - `utils/teleport/gitBundle.ts` 负责在本地终端 `fetch` 并应用这个远程变更。
   - 随后，系统将云端的历史对话（Transcript）完整转换为本地 CLI 支持的 `Message` 格式，瞬间接管本地上下文。
4. 结果：开发者在终端可以直接看到网页上最后一句：“我们规划好了，现在请运行本地测试验证一下方案”，并接着敲回车执行本地命令。

## 二、Qwen Code 的改进路径 (P1 优先级)

如果 Qwen 生态未来提供 Web 端的 Coding UI 或者基于云端环境的 Agent，实现 `/teleport` 是打通生态的关键。

### 阶段 1：开发远程会话发现 API
1. Qwen 服务端需提供类似 `/api/sessions/active` 的接口，允许使用当前 CLI 登录的凭证查询到该用户在网页版（如通义千问 Web）的带有“代码模式”标签的历史会话。
2. 在 `packages/core/src/commands/` 目录下新增 `teleport` 交互式命令，使用类似 `FuzzyPicker` 的 UI 列出云端会话。

### 阶段 2：会话格式转换层 (Transcript Mapper)
1. 下载云端会话的 JSON 历史流。
2. 在本地内存中执行映射逻辑：将网页上的文本对话映射为本地 Agent 识别的 `UserMessage` 和 `AssistantMessage`。
3. 丢弃那些只有云端才支持的特殊内部 Tool Result，注入一条系统标记 `[Session Teleported from Web]`。

### 阶段 3：Git Diff/Patch 协同
如果在云端已经生成了代码草案：
1. 本地 Agent 解析云端下发的 Patch 结构。
2. 强制要求本地通过 `git stash` 保护当前工作区后，应用该 Patch。

## 三、改进收益评估
- **实现成本**：高。需要云端服务台的 API 配合与一致的身份验证。
- **直接收益**：
  1. **全生态融合体验**：打破设备壁垒。在通勤路上用手机与大模型定架构，回到工位一键 Teleport 开始敲代码，体验极其震撼。
  2. **降低本地计算浪费**：复杂架构推理在云平台（算力无限制环境）完成，本地终端仅做轻量的文件读写执行，实现云边协同。