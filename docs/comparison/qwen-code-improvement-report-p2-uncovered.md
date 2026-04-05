# Qwen Code 改进建议 — P2 未覆盖功能深度分析

> 本文件记录的是**现有改进总览表中完全未提及**的功能模块。每项都经过源码级验证，确保不与已有报告重复。
>
> 验证方法：所有改进点已对照 `qwen-code-improvement-report.md` 总览表、所有 deep-dive 文档、所有 P0-P3 分报告、所有 single-file Agent 文档（`tools/` 目录），确认无重复。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Plugin Marketplace 系统（P2）

**做什么**：Claude Code 的 `/plugin` 命令不仅是启用/禁用管理，还是一个完整的**插件市场客户端**——支持浏览市场、搜索、安装、卸载、信任验证、选项配置全流程：

| 子功能 | 文件 | 行数 | 说明 |
|--------|------|------|------|
| 市场浏览 | `BrowseMarketplace.tsx` | ~200 | 搜索/筛选/浏览可用插件 |
| 发现插件 | `DiscoverPlugins.tsx` | ~150 | 推荐相关插件 |
| 安装管理 | `ManagePlugins.tsx` + `ManageMarketplaces.tsx` | ~400 | 安装/卸载/启用/禁用 |
| 信任验证 | `PluginTrustWarning.tsx` + `ValidatePlugin.tsx` | ~300 | 安装前安全警告和验证 |
| 选项配置 | `PluginOptionsDialog.tsx` + `PluginOptionsFlow.tsx` + `PluginSettings.tsx` | ~400 | 安装后配置用户偏好 |
| 分页/详情 | `usePagination.ts` + `pluginDetailsHelpers.tsx` + `PluginErrors.tsx` | ~200 | UI 辅助 |
| 添加市场源 | `AddMarketplace.tsx` | ~100 | 添加第三方市场 |
| 统一已安装列表 | `UnifiedInstalledCell.tsx` | ~100 | 已安装插件展示 |

**总规模**：17 文件，~7575 行

**为什么 Qwen Code 应该学习**：

Qwen Code 有 Skill 系统（SKILL.md 本地文件），但没有**市场**概念。用户无法浏览、搜索、一键安装社区插件。关键差距：

| 能力 | Claude Code | Qwen Code |
|------|-------------|-----------|
| 浏览市场 | ✓ Marketplace UI | ✗ 无 |
| 搜索插件 | ✓ 按标签/关键词搜索 | ✗ 无 |
| 一键安装 | ✓ 市场内直接安装 | ✗ 手动复制文件 |
| 信任验证 | ✓ 安装前安全审查 | ✗ 无 |
| 选项引导 | ✓ 安装后配置偏好 | ✗ 无 |
| 卸载/禁用 | ✓ UI 管理 | ✗ 手动删除文件 |

**Qwen Code 现状**：Skill 系统是本地文件（`~/.qwen/SKILL.md` 或项目内 `SKILL.md`），没有市场、搜索、安装、信任验证、选项配置等能力。

**Qwen Code 修改方向**：
1. 设计 Plugin Manifest schema（name/version/description/permissions/commands/skills）
2. 实现 `/plugin` 命令（浏览/搜索/安装/卸载/启用/禁用）
3. 添加 Marketplace API 对接（或基于 GitHub 的简单市场）
4. 安装前信任验证（权限声明、文件审查）
5. 安装后选项引导流

**实现成本评估**：
- 涉及文件：~15 个
- 新增代码：~2000 行
- 开发周期：~10 天（1 人）
- 难点：插件沙箱化、权限验证、市场源可信度

**意义**：Skill 系统是本地扩展，Plugin Marketplace 是生态——用户可发现、安装、管理社区插件。
**缺失后果**：用户需手动创建/复制 SKILL.md——无法发现社区扩展。
**改进收益**：Plugin Marketplace = 一键安装 + 安全验证 + 配置引导——生态繁荣。

---

<a id="item-2"></a>

### 2. 上下文 Tips 系统（P2）

> **注意**：`services/tips/tipRegistry.ts` 在 `qwen-code-improvement-report-p2-tools.md#item-19` 中被提及为"上下文 Tips 系统"，但**没有详细源码分析**。本项补充完整的实现细节。

**做什么**：Claude Code 内建一个提示（tips）系统——在用户等待期间（如 API 调用中、工具执行时），显示上下文相关的使用技巧：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/tips/tipRegistry.ts` | 686 | 注册表——数百条预设 tips，按标签/场景分类 |
| `services/tips/tipScheduler.ts` | 58 | 调度器——根据等待时间/场景选择展示哪条 tip |
| `services/tips/tipHistory.ts` | 17 | 历史记录——防止重复展示同一条 tip |

**Tip 分类**（基于 `tipRegistry.ts` 686 行分析）：
- **通用技巧**："按 Escape 取消当前操作"
- **命令提示**："试试 `/review` 审查 PR"
- **功能发现**："你可以用 `/model` 切换模型"
- **高级用法**："在 CLAUDE.md 中定义项目规范"
- **上下文相关**：如果检测到用户在用 MCP，展示 "试试 `/mcp` 管理服务器"

**调度策略**：
- 等待 >3 秒时展示（避免打断快速操作）
- 每条 tip 有冷却时间（不重复展示）
- 按场景标签过滤（MCP/Agent/Git 等）

**为什么 Qwen Code 应该学习**：

Qwen Code 有 `/tips` 命令（手动查看技巧），但没有**自动展示**机制。用户在等待 API 响应时的空白时间没有被利用来教育用户。

**Qwen Code 现状**：Tips 需要用户手动 `/tips` 查看——没有自动调度、没有上下文感知、没有防重复机制。

**Qwen Code 修改方向**：
1. 新建 `services/tips/tipRegistry.ts`——预设 tips 库（按场景分类）
2. 新建 `services/tips/tipScheduler.ts`——等待期间自动展示
3. 新建 `services/tips/tipHistory.ts`——防重复
4. 在 `useGeminiStream.ts` 的等待状态中集成 tip 展示

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~500 行
- 开发周期：~3 天（1 人）
- 难点：编写数百条高质量 tips 并按场景分类

---

<a id="item-3"></a>

### 3. /clear 清屏与会话重置（P2）

**做什么**：Claude Code 的 `/clear` 不只是清屏——它提供多种清除模式：

| 模式 | 命令 | 说明 |
|------|------|------|
| 清屏 | `/clear` | 清除终端显示，保留对话历史 |
| 清对话 | `/clear --history` | 清除对话历史，保留系统提示 |
| 全新开始 | `/clear --all` | 清除一切，如同新 session |

**关键设计**：
- 清屏时保持 scrollback buffer 可选择（不清空终端历史）
- 清对话后保留 memory/attachments 等上下文
- 清一切后重新初始化系统提示和工具注册
- 交互确认（防止误操作）

**为什么 Qwen Code 应该学习**：

Qwen Code 有 `/clear` 命令，但只有清屏功能——没有清除对话历史或完全重置的能力。用户在想"重新开始"但保留当前 session（不重启）时没有选项。

**Qwen Code 修改方向**：
1. 扩展 `/clear` 命令支持 `--history` 和 `--all` 标志
2. `--history`：清空 messages 数组，保留 system prompt + memory
3. `--all`：完全重置，重新初始化
4. 交互确认

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~0.5 天（1 人）

---

<a id="item-4"></a>

### 4. Thinkback 回忆功能（P2）

**做什么**：`/thinkback` 让 Agent 回顾整个会话的历程——从开始到现在的关键决策、修改的文件、解决的问题：

```
/thinkback                      # 回顾整个 session
/thinkback --from "30 min ago"  # 回顾最近 30 分钟
/thinkback --topic "auth"       # 回顾认证相关的讨论
```

**实现方式**：
- 分析完整 transcript（JSONL）
- 提取关键决策点（模型调用、文件修改、错误修复）
- 生成结构化的回顾报告
- 可选按时间范围或主题过滤

**为什么 Qwen Code 应该学习**：

长会话（50+ 轮）后，用户经常想不起来刚才做了什么。`/thinkback` 提供结构化的回顾——"你在 10:30 重构了 auth middleware，在 11:00 修复了 3 个测试失败"。

Qwen Code 有 `/summary` 命令，但它是即时摘要（总结当前状态），不是回顾（时间线式的关键事件列表）。

**Qwen Code 修改方向**：
1. 新建 `/thinkback` 命令
2. 分析 transcript 提取关键事件（文件修改、错误修复、决策点）
3. 按时间线排序
4. 支持 `--from` 和 `--topic` 过滤

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：从 transcript 中识别关键事件

---

## 总结

本文件涵盖 4 项**现有改进总览表完全未提及**的功能：

| # | 改进点 | 源码规模 | 开发周期 | 意义 |
|---|--------|:--------:|:--------:|------|
| 1 | [Plugin Marketplace](#item-1) | 17 文件, 7575 行 | ~10 天 | 生态扩展 |
| 2 | [上下文 Tips 系统](#item-2) | 3 文件, 761 行 | ~3 天 | 功能发现 |
| 3 | [/clear 增强](#item-3) | 已有基础 | ~0.5 天 | 会话管理 |
| 4 | [Thinkback 回忆](#item-4) | 2 文件, 566 行 | ~2 天 | 长会话回顾 |

**总计**：~15.5 天（1 人）

> **验证声明**：本文件所有改进点已对照以下文档确认无重复：
> - `qwen-code-improvement-report.md` 总览表（全部 P0-P3 条目）
> - 所有 deep-dive 文档（33 个文件）
> - 所有 P0-P3 分报告（p0-p1-core/engine/platform、p2-core/perf/stability/tools、p3）
> - 所有 single-file Agent 文档（`tools/claude-code/` 目录下 10 个文件）
>
> 注意：`install-github-app` 和 `add-dir` 已在其他报告中覆盖，已从本文件移除。
