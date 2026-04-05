# Deep-Dive 文章索引（133 篇）

> 按主题分类的深度分析文章，每篇聚焦一个具体技术机制的 Claude Code vs Qwen Code 对比。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

## 核心架构（18 篇）

| 文章 | 主题 |
|------|------|
| [架构总览](./architecture-deep-dive.md) | 整体架构对比 |
| [上下文压缩](./context-compression-deep-dive.md) | 5 层压缩策略 |
| [上下文折叠](./context-collapse-deep-dive.md) | History Snip |
| [Token 估算](./token-estimation-deep-dive.md) | API 计数 + 3 层回退 |
| [Token Budget 续行](./token-budget-continuation-deep-dive.md) | 90% 续行 + 递减检测 |
| [Prompt Cache 优化](./prompt-cache-optimization-deep-dive.md) | 分段缓存 + schema 锁定 |
| [系统提示](./system-prompt-deep-dive.md) | 模块化系统提示 |
| [系统提示内容指导](./system-prompt-content-guidelines-deep-dive.md) | OWASP + 代码风格 |
| [附件协议与预算](./attachment-protocol-budget-deep-dive.md) | 40+ 类型 + per-type 预算 |
| [记忆系统](./memory-system-deep-dive.md) | Session Memory + Auto Dream |
| [记忆 Prefetch](./memory-prefetch-deep-dive.md) | 异步预取 |
| [嵌套记忆 @include](./nested-memory-include-deep-dive.md) | @path 递归引用 |
| [指令加载](./instruction-loading-deep-dive.md) | CLAUDE.md 层级加载 |
| [消息规范化](./message-normalization-deep-dive.md) | 配对修复 + 媒体裁剪 |
| [输出 Token 自适应](./output-token-adaptive-upgrade-deep-dive.md) | 8K→64K 升级 |
| [Thinking 块保留](./thinking-block-retention-deep-dive.md) | 跨轮保留 + 空闲清理 |
| [反应式压缩](./reactive-compression-deep-dive.md) | prompt_too_long 恢复 |
| [命令队列编排](./command-queue-orchestration-deep-dive.md) | 统一队列 + 优先级调度 |

## 工具与命令（16 篇）

| 文章 | 主题 |
|------|------|
| [斜杠命令](./slash-commands-deep-dive.md) | 命令体系总览 |
| [关键命令](./key-commands-deep-dive.md) | /compact /plan /init |
| [工具并行](./tool-parallelism-deep-dive.md) | 智能批处理 |
| [工具搜索](./tool-search-deep-dive.md) | ToolSearch 延迟加载 |
| [流式工具执行](./streaming-tool-execution-deep-dive.md) | 流水线执行 |
| [输入队列](./input-queue-deep-dive.md) | Mid-Turn Queue Drain |
| [Hook 与插件](./hook-plugin-extension-deep-dive.md) | Hook 系统 + 插件 |
| [HTTP Hooks](./http-hooks-deep-dive.md) | 原生 HTTP Hook |
| [Conditional Hooks](./conditional-hooks-deep-dive.md) | 条件过滤 |
| [MCP 集成](./mcp-integration-deep-dive.md) | MCP 服务器管理 |
| [MCP 并行连接](./mcp-parallel-connection-deep-dive.md) | 动态插槽调度 |
| [MCP 自动重连](./mcp-auto-reconnect-deep-dive.md) | 断线恢复 |
| [Bash File Watcher](./file-watcher-stale-edit-deep-dive.md) | stale-edit 防护 |
| [Ripgrep 回退](./ripgrep-fallback-deep-dive.md) | 三级回退 |
| [Notebook Edit](./notebook-edit-deep-dive.md) | Jupyter cell 编辑 |
| [批量并行](./batch-parallel-execution-deep-dive.md) | /batch 多 Agent 并行 |

## 性能优化（16 篇）

| 文章 | 主题 |
|------|------|
| [启动优化](./startup-optimization-deep-dive.md) | Preconnect + Early Input |
| [文件读取缓存](./file-read-cache-deep-dive.md) | LRU + 批量并行 I/O |
| [Memoize TTL 缓存](./memoize-ttl-cache-deep-dive.md) | write-through + 后台刷新 |
| [同步 I/O 异步化](./sync-io-async-deep-dive.md) | 事件循环解阻塞 |
| [Bun 原生 API](./bun-native-api-optimization-deep-dive.md) | stringWidth + JSONL |
| [工具输出限高防闪烁](./tool-output-height-limiting-deep-dive.md) | SlicingMaxSizedBox + 15 行硬上限 |
| [终端渲染池化](./terminal-rendering-string-pooling-deep-dive.md) | CharPool/StylePool |
| [增量文件索引](./incremental-file-index-deep-dive.md) | FNV-1a 签名检测 |
| [文件模糊搜索](./file-index-fuzzy-search-deep-dive.md) | fzf 风格搜索 |
| [Shell 输出直写](./shell-output-fd-bypass-deep-dive.md) | fd 绕过 JS |
| [环形缓冲区](./circular-buffer-disk-spill-deep-dive.md) | CircularBuffer + 磁盘溢出 |
| [图片压缩](./image-compression-pipeline-deep-dive.md) | 多策略流水线 |
| [Git 上下文注入](./git-context-auto-injection-deep-dive.md) | 自动注入 |
| [LSP 并行启动](./lsp-parallel-startup-deep-dive.md) | Promise.all |
| [Prompt Suggestion](./prompt-suggestion-deep-dive.md) | 建议产品化 |
| [Speculation 启用](./speculation-default-enable-deep-dive.md) | 默认启用 |
| [成本与 Fast Mode](./cost-fastmode-deep-dive.md) | 费用追踪 |

## 稳定性与安全（18 篇）

| 文章 | 主题 |
|------|------|
| [崩溃恢复](./crash-recovery-deep-dive.md) | 中断检测 + 合成续行 |
| [API 退避重试](./api-retry-fallback-deep-dive.md) | 指数退避 + 模型降级 |
| [持久化重试](./persistent-retry-deep-dive.md) | CI 无限重试 |
| [优雅关闭](./graceful-shutdown-deep-dive.md) | 信号处理 + failsafe |
| [原子文件写入](./atomic-file-write-deep-dive.md) | temp+rename |
| [自动检查点](./automatic-checkpoint-restore-deep-dive.md) | 文件快照恢复 |
| [Shell 安全](./shell-security-deep-dive.md) | AST + 25 检查 |
| [Sandbox 安全](./sandbox-security-deep-dive.md) | 沙箱模型 |
| [Sandbox 排除](./sandbox-excluded-commands-deep-dive.md) | excludedCommands |
| [安全审查](./security-review-command-deep-dive.md) | /security-review |
| [隐私/遥测](./telemetry-privacy-deep-dive.md) | 隐私监控 |
| [遥测架构](./telemetry-architecture-deep-dive.md) | 遥测系统 |
| [隐私设置](./privacy-settings-dialog-deep-dive.md) | 交互式隐私 |
| [MDM 企业配置](./mdm-enterprise-deep-dive.md) | 企业策略 |
| [企业代理](./enterprise-proxy-support-deep-dive.md) | CONNECT relay |
| [内存诊断](./memory-diagnostics-deep-dive.md) | V8 heap dump |
| [Feature Gates](./feature-gates-deep-dive.md) | GrowthBook A/B |
| [Zip Bomb 防护](./zip-bomb-protection-deep-dive.md) | DXT/MCPB 插件包 |

## 多 Agent 与编排（13 篇）

| 文章 | 主题 |
|------|------|
| [Kairos Always-On](./kairos-always-on-agent-deep-dive.md) | 自治 Agent + Cron 调度 |
| [Fork Subagent](./fork-subagent-deep-dive.md) | 上下文继承 + cache 共享 |
| [多 Agent](./multi-agent-deep-dive.md) | Swarm 系统 |
| [Coordinator/Swarm](./coordinator-swarm-orchestration-deep-dive.md) | Leader/Worker 编排 |
| [Agent 工具控制](./agent-tool-access-control-deep-dive.md) | 3 层 allowlist/denylist |
| [InProcess 隔离](./in-process-agent-isolation-deep-dive.md) | AsyncLocalStorage |
| [Agent 记忆持久化](./agent-memory-persistence-deep-dive.md) | 3 级记忆 |
| [Agent 恢复续行](./agent-resume-continuation-deep-dive.md) | SendMessage 续行 |
| [Agent 权限冒泡](./agent-permission-bubble-deep-dive.md) | bubble 模式 |
| [Agent 创建向导](./interactive-agent-creation-deep-dive.md) | 11 步向导 |
| [Task Management](./task-management-deep-dive.md) | 任务协同 |
| [Team Memory](./team-memory-deep-dive.md) | 组织级记忆 |
| [SDK 双向控制](./sdk-bidirectional-control-deep-dive.md) | 控制协议 |

## 平台集成（14 篇）

| 文章 | 主题 |
|------|------|
| [GitHub Actions CI](./github-actions-ci-deep-dive.md) | CI 自动化 |
| [GitHub Code Review](./github-code-review-deep-dive.md) | 多 Agent 审查 |
| [GitLab CI/CD](./gitlab-ci-cd-deep-dive.md) | GitLab 集成 |
| [Agent SDK Python](./agent-sdk-python-deep-dive.md) | Python SDK |
| [CI 脚本](./ci-scripting-deep-dive.md) | headless 模式 |
| [CI 环境检测](./ci-environment-detection-deep-dive.md) | 平台检测 |
| [Bare Mode](./bare-mode-deep-dive.md) | --bare 快速启动 |
| [Structured Output](./structured-output-deep-dive.md) | --json-schema |
| [Remote Control Bridge](./remote-control-bridge-deep-dive.md) | 远程控制 |
| [Teleport 迁移](./teleport-session-migration-deep-dive.md) | 跨端迁移 |
| [PR Webhook](./pr-webhook-event-subscription-deep-dive.md) | PR 事件订阅 |
| [UltraReview](./ultrareview-remote-deep-review-deep-dive.md) | 远程深度审查 |
| [Ultraplan](./ultraplan-remote-planning-deep-dive.md) | 远程规划 |
| [Session Ingress Auth](./session-ingress-auth-deep-dive.md) | 远程认证 |

## 用户体验（21 篇）

| 文章 | 主题 |
|------|------|
| [Ghost Text 补全](./ghost-text-completion-deep-dive.md) | 输入灰字建议 |
| [终端 UI](./terminal-ui-deep-dive.md) | 终端界面 |
| [紧凑状态栏](./compact-status-bar-deep-dive.md) | 固定高度 Footer |
| [动态状态栏](./dynamic-status-bar-deep-dive.md) | 实时更新文本 |
| [自定义快捷键](./custom-keybindings-deep-dive.md) | keybindings.json |
| [Vim 模拟](./vim-emulation-deep-dive.md) | modal editing |
| [语音模式](./voice-mode-deep-dive.md) | push-to-talk |
| [Buddy 伴侣](./buddy-companion-deep-dive.md) | 精灵系统 |
| [右面板](./right-panel-ui-deep-dive.md) | useMoreRight |
| [Logo V2](./logov2-brand-identity-deep-dive.md) | 品牌标识 |
| [Virtual Scrolling](./virtual-scrolling-deep-dive.md) | 虚拟滚动 |
| [Feedback Survey](./feedback-survey-deep-dive.md) | 用户反馈 |
| [Turn Diffs](./turn-diffs-deep-dive.md) | 轮次差异 |
| [Transcript Search](./transcript-search-navigation-deep-dive.md) | 会话搜索 |
| [会话标签](./session-tags-search-deep-dive.md) | /tag 搜索 |
| [会话后台化](./session-backgrounding-deep-dive.md) | Ctrl+B 后台 |
| [Plan 模式](./plan-mode-interview-deep-dive.md) | Interview 访谈 |
| [BriefTool](./brieftool-async-user-messages-deep-dive.md) | 异步消息 |
| [/context 非交互](./context-usage-noninteractive-deep-dive.md) | 自动化诊断 |
| [上下文 Tips](./context-tips-system-deep-dive.md) | 提示系统 |
| [权限对话框预览](./permission-dialog-file-preview-deep-dive.md) | 文件预览 |

## 其他（16 篇）

| 文章 | 主题 |
|------|------|
| [API 参数](./api-params-deep-dive.md) | API 参数对比 |
| [Git 集成](./git-integration-deep-dive.md) | Git 操作 |
| [Git 工作流](./git-workflow-session-deep-dive.md) | 工作流管理 |
| [Computer Use](./computer-use-deep-dive.md) | 桌面自动化 |
| [Deep Link](./deep-link-protocol-deep-dive.md) | URI 协议 |
| [Chrome 调试](./chrome-extension-debugging-deep-dive.md) | 浏览器调试 |
| [Config 工具](./config-tool-dynamic-settings-deep-dive.md) | 动态设置 |
| [终端主题检测](./terminal-theme-detection-deep-dive.md) | dark/light |
| [远程 CCR 设置](./remote-ccr-setup-deep-dive.md) | 远程环境 |
| [企业用量](./enterprise-usage-management-deep-dive.md) | /extra-usage |
| [限速选项](./rate-limit-options-deep-dive.md) | 限速菜单 |
| [插件市场](./plugin-marketplace-deep-dive.md) | 分发机制 |
| [插件生命周期](./plugin-marketplace-lifecycle-deep-dive.md) | 生命周期管理 |
| [Skill 系统](./skill-system-deep-dive.md) | Skill 设计 |
| [Advisor 模型](./advisor-model-deep-dive.md) | 副模型审查 |
| [测试反射](./test-reflection-deep-dive.md) | 测试策略 |
