# Qwen Code 改进建议 — P3 详细说明

> 低优先级改进项。每项包含：思路概述、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-152"></a>

### 152. 动态状态栏（P3）

**思路**：`AppState.statusLineText` 允许模型/工具实时更新状态文本（如"正在分析 5 个文件..."），提供执行进度可见性。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `state/AppStateStore.ts` | `statusLineText: string` |
| `components/StatusLine.tsx` | 条件渲染 |

**Qwen Code 修改方向**：`UIStateContext` 新增 `statusText` 状态；工具执行时通过 `setUIState()` 更新；`Footer.tsx` 渲染。

**意义**：用户不知道 Agent 当前在做什么——长时间执行时焦虑等待。
**缺失后果**：仅有 spinner 无具体信息——'还要等多久？在做什么？'
**改进收益**：动态状态文本——'正在分析 5 个文件...'——减少等待焦虑。

---

<a id="item-153"></a>

### 153. 上下文折叠 History Snip（P3）

**思路**：`feature('HISTORY_SNIP')` 门控。**Claude Code 自身仅 scaffolding**——SnipTool 有 lazy require 占位无完整实现。已有 `collapseReadSearch.ts` 的 UI 级消息折叠（连续 read/search 合并显示）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/collapseReadSearch.ts` | UI 级连续 read/search 折叠 |

**Qwen Code 修改方向**：参考方向——连续工具调用的 UI 折叠显示（不改变 API 发送内容）。

**意义**：早期对话占满上下文但内容已过时——比全量压缩更精细的方案。
**缺失后果**：注意：Claude Code 自身仅 scaffolding，无完整实现。参考方向。
**改进收益**：UI 级折叠——连续 read/search 合并显示，减少视觉噪音。

---

<a id="item-154"></a>

### 154. 内存诊断（P3）

**思路**：1.5GB 阈值触发 V8 heap snapshot + Linux smaps_rollup 解析 + 内存增长率分析 → leak 建议。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/heapDumpService.ts` | 阈值触发 + heap snapshot |

**Qwen Code 修改方向**：`process.memoryUsage()` 定期检查；超限时 `v8.writeHeapSnapshot()`。

**意义**：长会话可能内存泄漏——Agent 进程 OOM 导致 session 丢失。
**缺失后果**：无内存监控——OOM 时直接崩溃，无诊断信息。
**改进收益**：1.5GB 阈值预警 + heap snapshot——提前发现并诊断泄漏。

---

<a id="item-155"></a>

### 155. Feature Gates（P3）

**思路**：GrowthBook 远程特性开关——A/B 测试 + 按事件动态采样。渐进式灰度发布。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/analytics/growthbook.ts` | `initializeGrowthBook()`、`getFeatureValue_CACHED_MAY_BE_STALE()` |

**Qwen Code 修改方向**：集成 GrowthBook SDK 或自建 feature flag 服务。

**意义**：新功能灰度发布降低全量上线风险——A/B 测试数据驱动决策。
**缺失后果**：新功能只能全量发布——出问题影响所有用户。
**改进收益**：渐进式灰度——先 1% 用户验证，确认无问题后全量。

---

<a id="item-156"></a>

### 156. DXT/MCPB 插件包（P3）

**思路**：`.dxt`/`.mcpb` 单文件打包 MCP 服务器 + 依赖。zip bomb 防护（512MB/文件、1GB 总量、50:1 压缩比）。

**Qwen Code 修改方向**：定义包格式（zip + manifest.json）；安装时验证大小/压缩比。

**意义**：MCP 插件分发需要打包依赖——避免安装环境不一致。
**缺失后果**：松散文件分发——依赖缺失导致安装失败。
**改进收益**：单文件安装 + zip bomb 防护——安全可靠的插件分发。

---

<a id="item-157"></a>

### 157. /security-review（P3）

**思路**：基于 git diff 的安全审查命令，聚焦 OWASP Top 10 漏洞检测。

**Qwen Code 修改方向**：新建 `skills/bundled/security-review/SKILL.md`，prompt 模板聚焦安全。

**意义**：代码提交前的安全扫描是 DevSecOps 的基本要求。
**缺失后果**：无内置安全审查——安全漏洞可能被合并到代码库。
**改进收益**：基于 diff 的安全审查——聚焦新增代码的 OWASP Top 10。

---

<a id="item-158"></a>

### 158. Ultraplan 远程计划探索（P3）

**思路**：启动远程 CCR 会话，用更强模型深度规划后回传结果。需云端执行基础设施。

**Qwen Code 修改方向**：需先有 Web 版本；`--remote` flag 创建云端 session。

**意义**：复杂项目规划需要更强模型的深度推理——本地模型可能不够。
**缺失后果**：规划仅能用当前模型——深度思考能力受限。
**改进收益**：远程调用更强模型规划——结果回传到本地执行。

---

<a id="item-159"></a>

### 159. Advisor 顾问模型（P3）

**思路**：`/advisor` 配置副模型（如更强模型）审查主模型输出。`server_tool_use` 方式自动调用。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/advisor.ts` | `isAdvisorEnabled()`、GrowthBook `tengu_sage_compass` |

**Qwen Code 修改方向**：需多模型同时调用能力；response 后追加审查模型调用。

**意义**：主模型输出质量不稳定——副模型审查可提升可靠性。
**缺失后果**：无审查机制——错误输出可能被直接执行。
**改进收益**：副模型自动审查——发现主模型遗漏的问题。

---

<a id="item-160"></a>

### 160. Vim 完整实现（P3）

**思路**：完整 modal editing——motions + operators + text objects + transitions。4 文件结构。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `keybindings/motions.ts` | hjkl/w/b/e/0/$ |
| `keybindings/operators.ts` | d/c/y |
| `keybindings/textObjects.ts` | iw/aw/i"/a" |

**Qwen Code 修改方向**：扩展现有 `vim.ts`——补充 text objects 和 operators。

**意义**：Vim 用户群体庞大——完整 modal editing 是差异化竞争力。
**缺失后果**：基础 vim 模式缺少 text objects 和 operators——Vim 用户体验不完整。
**改进收益**：完整 Vim 体验——motions + operators + text objects 全覆盖。

---

<a id="item-161"></a>

### 161. 语音模式（P3）

**思路**：push-to-talk 语音输入 + 流式 STT 转录。快捷键可通过 `keybindings.json` 重绑。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/voice/` | push-to-talk + STT |
| keybindings: `voice:pushToTalk` | 绑定配置 |

**Qwen Code 修改方向**：需音频捕获 NAPI + STT API（如阿里云 ASR）。

**意义**：语音输入解放双手——适合代码审查讨论、快速口述需求。
**缺失后果**：只能键盘输入——手不方便时无法使用。
**改进收益**：push-to-talk 语音输入——说完自动转文字。

---

<a id="item-162"></a>

### 162. 插件市场（P3）

**思路**：官方 marketplace 安装插件（hooks/commands/agents/MCP），安装状态追踪，自动更新。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/plugins/pluginLoader.ts` | 加载 + marketplace 同步 |
| `utils/plugins/pluginInstaller.ts` | 安装 + 版本管理 |

**Qwen Code 修改方向**：已有 extension 系统；新增 marketplace 发现 + git-based 安装。

**意义**：插件生态是工具平台化的关键——用户和社区可扩展功能。
**缺失后果**：功能扩展依赖官方开发——社区无法贡献。
**改进收益**：插件市场——社区可发布和发现插件，生态自增长。

**相关文章**：[Hook 与插件扩展](./hook-plugin-extension-deep-dive.md)
