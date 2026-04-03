# Qwen Code 改进建议 — P3 详细说明

> 低优先级改进项。每项包含：思路概述、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-37"></a>

### 37. 动态状态栏（P3）

**思路**：`AppState.statusLineText` 允许模型/工具实时更新状态文本（如"正在分析 5 个文件..."），提供执行进度可见性。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `state/AppStateStore.ts` | `statusLineText: string` |
| `components/StatusLine.tsx` | 条件渲染 |

**Qwen Code 修改方向**：`UIStateContext` 新增 `statusText` 状态；工具执行时通过 `setUIState()` 更新；`Footer.tsx` 渲染。

---

<a id="item-38"></a>

### 38. 上下文折叠 History Snip（P3）

**思路**：`feature('HISTORY_SNIP')` 门控。**Claude Code 自身仅 scaffolding**——SnipTool 有 lazy require 占位无完整实现。已有 `collapseReadSearch.ts` 的 UI 级消息折叠（连续 read/search 合并显示）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/collapseReadSearch.ts` | UI 级连续 read/search 折叠 |

**Qwen Code 修改方向**：参考方向——连续工具调用的 UI 折叠显示（不改变 API 发送内容）。

---

<a id="item-39"></a>

### 39. 内存诊断（P3）

**思路**：1.5GB 阈值触发 V8 heap snapshot + Linux smaps_rollup 解析 + 内存增长率分析 → leak 建议。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/heapDumpService.ts` | 阈值触发 + heap snapshot |

**Qwen Code 修改方向**：`process.memoryUsage()` 定期检查；超限时 `v8.writeHeapSnapshot()`。

---

<a id="item-40"></a>

### 40. Feature Gates（P3）

**思路**：GrowthBook 远程特性开关——A/B 测试 + 按事件动态采样。渐进式灰度发布。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/analytics/growthbook.ts` | `initializeGrowthBook()`、`getFeatureValue_CACHED_MAY_BE_STALE()` |

**Qwen Code 修改方向**：集成 GrowthBook SDK 或自建 feature flag 服务。

---

<a id="item-41"></a>

### 41. DXT/MCPB 插件包（P3）

**思路**：`.dxt`/`.mcpb` 单文件打包 MCP 服务器 + 依赖。zip bomb 防护（512MB/文件、1GB 总量、50:1 压缩比）。

**Qwen Code 修改方向**：定义包格式（zip + manifest.json）；安装时验证大小/压缩比。

---

<a id="item-42"></a>

### 42. /security-review（P3）

**思路**：基于 git diff 的安全审查命令，聚焦 OWASP Top 10 漏洞检测。

**Qwen Code 修改方向**：新建 `skills/bundled/security-review/SKILL.md`，prompt 模板聚焦安全。

---

<a id="item-43"></a>

### 43. Ultraplan 远程计划探索（P3）

**思路**：启动远程 CCR 会话，用更强模型深度规划后回传结果。需云端执行基础设施。

**Qwen Code 修改方向**：需先有 Web 版本；`--remote` flag 创建云端 session。

---

<a id="item-44"></a>

### 44. Advisor 顾问模型（P3）

**思路**：`/advisor` 配置副模型（如更强模型）审查主模型输出。`server_tool_use` 方式自动调用。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/advisor.ts` | `isAdvisorEnabled()`、GrowthBook `tengu_sage_compass` |

**Qwen Code 修改方向**：需多模型同时调用能力；response 后追加审查模型调用。

---

<a id="item-45"></a>

### 45. Vim 完整实现（P3）

**思路**：完整 modal editing——motions + operators + text objects + transitions。4 文件结构。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `keybindings/motions.ts` | hjkl/w/b/e/0/$ |
| `keybindings/operators.ts` | d/c/y |
| `keybindings/textObjects.ts` | iw/aw/i"/a" |

**Qwen Code 修改方向**：扩展现有 `vim.ts`——补充 text objects 和 operators。

---

<a id="item-46"></a>

### 46. 语音模式（P3）

**思路**：push-to-talk 语音输入 + 流式 STT 转录。快捷键可通过 `keybindings.json` 重绑。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/voice/` | push-to-talk + STT |
| keybindings: `voice:pushToTalk` | 绑定配置 |

**Qwen Code 修改方向**：需音频捕获 NAPI + STT API（如阿里云 ASR）。

---

<a id="item-47"></a>

### 47. 插件市场（P3）

**思路**：官方 marketplace 安装插件（hooks/commands/agents/MCP），安装状态追踪，自动更新。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/plugins/pluginLoader.ts` | 加载 + marketplace 同步 |
| `utils/plugins/pluginInstaller.ts` | 安装 + 版本管理 |

**Qwen Code 修改方向**：已有 extension 系统；新增 marketplace 发现 + git-based 安装。

**相关文章**：[Hook 与插件扩展](./hook-plugin-extension-deep-dive.md)
