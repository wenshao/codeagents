# Qwen Code 改进建议 — P3 Hook 与组件

> 低优先级 Hook 与组件改进项（32 项）。每项包含：问题场景、现状分析、改进前后对比、实现成本评估、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. useInboxPoller 收件箱轮询（P3）

**问题**：多 Agent（Swarm/Teammate）协作时，Agent 需要定期检查是否有来自其他 Agent 或用户的新消息——但当前没有统一的收件箱轮询机制。

**Claude Code 源码索引**：`hooks/useInboxPoller.ts`

**Qwen Code 现状**：Arena 系统用文件 IPC 但无统一的收件箱轮询 hook。

**Qwen Code 修改方向**：新增 `useInboxPoller` hook——定期检查邮箱文件变更，有新消息时触发回调。

**实现成本评估**：~2 文件，~100 行，~1 天。

**意义**：多 Agent 通信的基础设施——没有轮询就无法及时响应消息。
**缺失后果**：Agent 间消息延迟 → 协作效率低。
**改进收益**：定期轮询 = 及时响应 → 多 Agent 协作流畅。

---

<a id="item-2"></a>

### 2. useRemoteSession 远程会话 Hook（P3）

**Claude Code 源码**：`hooks/useRemoteSession.ts` — Remote Control Bridge 的 React hook 封装，管理远程会话连接/断开/重连状态。

**Qwen Code 现状**：无远程会话 hook。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-3"></a>

### 3. useDiffInIDE IDE 差异查看（P3）

**Claude Code 源码**：`hooks/useDiffInIDE.ts` — 将 Agent 的文件编辑 diff 发送到 IDE（VS Code）中以原生 diff view 打开，比终端内 diff 更易读。

**Qwen Code 现状**：diff 仅在终端显示。**实现成本**：~2 文件，~100 行，~1 天。

---

<a id="item-4"></a>

### 4. useCancelRequest 取消请求 Hook（P3）

**Claude Code 源码**：`hooks/useCancelRequest.ts` — 统一的取消请求处理（Escape 键 / Ctrl+C），区分"取消当前工具"和"取消整个轮次"。

**Qwen Code 现状**：取消处理分散在各处。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-5"></a>

### 5. AgentSummary 代理摘要服务（P3）

**Claude Code 源码**：`services/AgentSummary/agentSummary.ts` — Agent 完成任务后生成结构化摘要（修改了哪些文件、关键决策、遇到的问题）。

**Qwen Code 现状**：无 Agent 完成后的结构化摘要。**实现成本**：~2 文件，~200 行，~2 天。

---

<a id="item-6"></a>

### 6. useBackgroundTaskNavigation 后台任务导航（P3）

**Claude Code 源码**：`components/tasks/BackgroundTasksDialog.tsx` — 在多个后台 Agent 间快速切换，查看各自进度和输出。

**Qwen Code 现状**：后台任务无导航 UI。**实现成本**：~2 文件，~150 行，~1 天。

---

<a id="item-7"></a>

### 7. useTaskListWatcher 任务列表监控（P3）

**Claude Code 源码**：`hooks/useTaskListWatcher.ts` — 监控共享任务文件变更，任务状态变化时自动刷新 UI。

**Qwen Code 现状**：无任务文件监控。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-8"></a>

### 8. useDirectConnect 直连 Hook（P3）

**Claude Code 源码**：`server/createDirectConnectSession.ts`、`server/directConnectManager.ts` — 无需中继服务器的直连模式，适用于本地 IDE 与 CLI 同机通信。

**Qwen Code 现状**：无直连模式。**实现成本**：~3 文件，~200 行，~2 天。

---

<a id="item-9"></a>

### 9. useAssistantHistory 代理历史 Hook（P3）

**Claude Code 源码**：`hooks/useAssistantHistory.ts` — 追踪当前 session 中所有 assistant 消息的历史，支持快速定位和回溯。

**Qwen Code 现状**：无独立的 assistant 历史追踪 hook。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-10"></a>

### 10. useSSHSession SSH 会话 Hook（P3）

**Claude Code 源码**：`hooks/useSSHSession.ts` — SSH 连接会话管理，支持本地 terminal 通过 SSH 连接到远程机器上的 Agent。

**Qwen Code 现状**：无 SSH 会话支持。**实现成本**：~2 文件，~150 行，~2 天。

---

<a id="item-11"></a>

### 11. useSwarmPermissionPoller Swarm 权限轮询（P3）

**Claude Code 源码**：`hooks/useSwarmPermissionPoller.ts` — 多 Agent Swarm 模式下定期检查是否有来自 Teammate 的权限请求需要 Leader 审批。

**Qwen Code 现状**：无 Swarm 权限轮询。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-12"></a>

### 12. useTasksV2 任务 V2 Hook（P3）

**Claude Code 源码**：`hooks/useTasksV2.ts` — Task 框架的 React hook 封装，提供任务增删改查 + 实时刷新。

**Qwen Code 现状**：无 Task hook。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-13"></a>

### 13. useArrowKeyHistory 箭头键历史导航（P3）

**Claude Code 源码**：`hooks/useArrowKeyHistory.ts` — 用 ↑/↓ 箭头键浏览之前的输入命令（类似 shell history），无需重新输入。

**Qwen Code 现状**：无命令历史导航。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-14"></a>

### 14. useCanUseTool 工具可用性 Hook（P3）

**Claude Code 源码**：`hooks/useCanUseTool.ts` — 检查指定工具在当前权限模式下是否可用，用于 UI 条件渲染（灰显不可用工具）。

**Qwen Code 现状**：权限检查在工具执行时才做，无预检 hook。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-15"></a>

### 15. useSearchInput 输入搜索 Hook（P3）

**Claude Code 源码**：`hooks/useSearchInput.ts` — Transcript Search 的输入层 hook，处理搜索框激活/去激活、关键词状态、匹配导航。

**Qwen Code 现状**：无搜索输入 hook。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-16"></a>

### 16. usePasteHandler 粘贴处理 Hook（P3）

**Claude Code 源码**：`hooks/usePasteHandler.ts` — 统一的粘贴事件处理——检测粘贴内容类型（文本/图片/文件路径），图片自动转为 base64 附件，文件路径转为 @引用。

**Qwen Code 现状**：有图片粘贴支持但处理逻辑分散。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-17"></a>

### 17. useScheduledTasks 定时任务 Hook（P3）

**Claude Code 源码**：`hooks/useScheduledTasks.ts` — Cron 定时任务的 React hook 封装，提供任务列表渲染 + 状态更新 + 到期检测。

**Qwen Code 现状**：有 CronScheduler 但无 UI hook。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-18"></a>

### 18. useVimInput Vim 输入 Hook（P3）

**Claude Code 源码**：`hooks/useVimInput.ts` — Vim 模式的输入处理 hook，管理 normal/insert/visual 模式切换和按键映射。

**Qwen Code 现状**：有基础 vim.ts 但无独立 hook。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-19"></a>

### 19. useLspPluginRecommendation LSP 插件推荐（P3）

**Claude Code 源码**：`hooks/useLspPluginRecommendation.tsx` — 根据项目语言自动推荐安装对应 LSP 插件（如检测到 .py 推荐 Python LSP）。

**Qwen Code 现状**：无 LSP 插件推荐。**实现成本**：~1 文件，~80 行，~1 天。

---

<a id="item-20"></a>

### 20. unifiedSuggestions 统一建议服务（P3）

**Claude Code 源码**：`utils/suggestions/unifiedSuggestions.ts` — 合并 command/path/history 三层补全建议为统一排序列表。

**Qwen Code 现状**：补全建议分散在各处。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-21"></a>

### 21. useInputBuffer 输入缓冲 Hook（P3）

**Claude Code 源码**：`hooks/useInputBuffer.ts` — 管理用户输入的缓冲区（多行编辑、composition 事件、粘贴合并），防止快速输入丢字。

**Qwen Code 现状**：输入直接处理无缓冲。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-22"></a>

### 22. useIssueFlagBanner 问题标志 Banner（P3）

**Claude Code 源码**：`hooks/useIssueFlagBanner.ts` — 检测已知问题（如 API 降级、版本过旧）并在终端顶部显示 banner 通知。

**Qwen Code 现状**：无问题 banner 机制。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-23"></a>

### 23. useDiffData 差异数据 Hook（P3）

**Claude Code 源码**：`hooks/useDiffData.ts` — 文件编辑的 diff 数据管理 hook，提供 before/after 内容对比 + 行级差异计算。

**Qwen Code 现状**：diff 计算在组件内部。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-24"></a>

### 24. toolUseSummary 工具使用摘要（P3）

**Claude Code 源码**：`services/toolUseSummary/` — 每轮对话结束后生成工具使用摘要（调用了哪些工具、结果如何、耗时多久）。

**Qwen Code 现状**：无工具使用摘要。**实现成本**：~2 文件，~150 行，~1 天。

---

<a id="item-25"></a>

### 25. useAwaySummary 离开摘要 Hook（P3）

**Claude Code 源码**：`hooks/useAwaySummary.ts` — 用户离开后返回时，自动生成"你离开期间发生了什么"的摘要。

**Qwen Code 现状**：无离开摘要。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-26"></a>

### 26. useCommandKeybindings 命令快捷键 Hook（P3）

**Claude Code 源码**：`hooks/useCommandKeybindings.tsx` — 将 slash command 与快捷键绑定的 React hook。

**Qwen Code 现状**：快捷键与命令分离管理。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-27"></a>

### 27. usePluginRecommendationBase 插件推荐基础 Hook（P3）

**Claude Code 源码**：`hooks/usePluginRecommendationBase.tsx` — 插件推荐的基础逻辑（检测项目类型→匹配可用插件→展示推荐）。

**Qwen Code 现状**：无插件推荐。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-28"></a>

### 28. useSkillImprovementSurvey 技能改进调查 Hook（P3）

**Claude Code 源码**：`hooks/useSkillImprovementSurvey.ts` — 在用户使用 skill 后收集"这个 skill 好用吗"的反馈。

**Qwen Code 现状**：无 skill 反馈收集。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-29"></a>

### 29. usePrStatus PR 状态 Hook（P3）

**Claude Code 源码**：`hooks/usePrStatus.ts` — 追踪当前 session 关联的 PR 状态（open/merged/closed/CI status）。

**Qwen Code 现状**：无 PR 状态追踪。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-30"></a>

### 30. useLogMessages 日志消息 Hook（P3）

**Claude Code 源码**：`hooks/useLogMessages.ts` — 统一的日志消息管理 hook，收集各组件的调试/信息/警告消息用于诊断。

**Qwen Code 现状**：日志分散在各处。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-31"></a>

### 31. useClaudeCodeHintRecommendation 提示推荐 Hook（P3）

**Claude Code 源码**：`hooks/useClaudeCodeHintRecommendation.tsx` — 根据用户操作上下文推荐功能提示（"试试 /plan"、"用 Tab 接受建议"等）。

**Qwen Code 现状**：无上下文感知的功能推荐。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-32"></a>

### 32. /sandbox-toggle sandbox 切换命令（P3）

**Claude Code 源码**：`commands/sandbox-toggle/sandbox-toggle.tsx` — 运行时切换 sandbox 开关，无需修改配置文件重启。

**Qwen Code 现状**：sandbox 需在配置中设置，运行时不可切换。**实现成本**：~2 文件，~80 行，~0.5 天。
