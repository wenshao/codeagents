# Qwen Code 改进建议 — P3 详细说明

> 低优先级改进项的详细说明。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

<a id="item-37"></a>

### 37. 动态状态栏（P3）

**Claude Code**：`AppState.statusLineText` 允许模型/工具实时更新状态文本（如"正在分析 5 个文件..."）。

**Qwen Code**：仅静态 Footer。

**改进收益**：用户实时了解 Agent 当前在做什么——减少等待焦虑。

---

<a id="item-38"></a>

### 38. 上下文折叠 History Snip（P3）

**Claude Code**：`feature('HISTORY_SNIP')` 门控，目前仅 scaffolding（SnipTool 有 lazy require 占位，无完整实现）。已有 `collapseReadSearch.ts` 的 UI 级消息折叠。

**Qwen Code**：缺失。

**说明**：Claude Code 自身未完整实现，列为参考方向。

---

<a id="item-39"></a>

### 39. 内存诊断（P3）

**Claude Code**：`utils/heapDumpService.ts` 在 1.5GB 阈值触发 V8 heap snapshot，解析 Linux smaps_rollup，分析内存增长率并给出 leak 建议。

**Qwen Code**：缺失。

**改进收益**：长会话内存泄漏自动检测和诊断——帮助开发者定位 Agent 的内存问题。

---

<a id="item-40"></a>

### 40. Feature Gates（P3）

**Claude Code**：`services/analytics/growthbook.ts` 集成 GrowthBook 远程特性开关 + A/B 测试 + 按事件动态采样率。

**Qwen Code**：缺失。

**改进收益**：新功能渐进式灰度发布——降低全量上线风险。

---

<a id="item-41"></a>

### 41. DXT/MCPB 插件包格式（P3）

**Claude Code**：支持 `.dxt`/`.mcpb` 打包格式，含 zip bomb 防护（512MB/文件、1GB 总量、50:1 压缩比限制）。

**Qwen Code**：缺失。

**改进收益**：安全的插件分发——单文件安装 MCP 服务器 + 依赖。

---

<a id="item-42"></a>

### 42. /security-review 安全审查（P3）

**Claude Code**：基于 frontmatter 模板的安全审查命令，聚焦 git diff 中的漏洞检测。

**Qwen Code**：缺失。

**改进收益**：代码提交前自动安全扫描——减少安全漏洞。

---

<a id="item-43"></a>

### 43. Ultraplan 远程计划探索（P3）

**Claude Code**：`/ultraplan` 启动远程 CCR 会话，使用更强模型进行深度规划后回传结果。

**Qwen Code**：缺失。依赖远程执行基础设施。

---

<a id="item-44"></a>

### 44. Advisor 顾问模型（P3）

**Claude Code**：`/advisor` 配置副模型（如 Opus）审查主模型（如 Sonnet）输出。`server_tool_use` 方式，Backend 确定审查模型。

**Qwen Code**：缺失。需多模型同时调用能力。

---

<a id="item-45"></a>

### 45. Vim 完整实现（P3）

**Claude Code**：`keybindings/` 含 `motions.ts`、`operators.ts`、`textObjects.ts`、`transitions.ts` 完整 Vim 键绑定系统。

**Qwen Code**：有基础 `vim.ts` 实现。

**改进收益**：Vim 用户获得完整的 modal editing 体验。

---

<a id="item-46"></a>

### 46. 语音模式（P3）

**Claude Code**：`commands/voice/` + push-to-talk 快捷键 + 流式 STT 转录。快捷键可通过 `keybindings.json` 重绑。

**Qwen Code**：缺失。需音频捕获 + STT 基础设施。

---

<a id="item-47"></a>

### 47. 插件市场（P3）

**Claude Code**：支持从官方 marketplace 安装插件（hooks/commands/agents/output styles/MCP），自动更新。含安装状态追踪（pending → installing → installed/failed）。

**Qwen Code**：缺失。需插件发现、安装、版本管理基础设施。

**相关文章**：[Hook 与插件扩展](./hook-plugin-extension-deep-dive.md)

---


