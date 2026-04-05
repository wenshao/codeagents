# Qwen Code 改进建议 — P1 权限决策可解释性

> 权限系统改进项：不仅要“做出 allow / ask / deny 决策”，还要向用户解释“为什么会这样判定、命中了哪条规则、下一步如何调整”。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Permission Decision Trace / 权限决策解释链（P1）

**思路**：Qwen Code 这两版在权限引擎层面其实已经不弱：支持 `allow / ask / deny` 三类规则、session/persistent 两级规则、shell compound command 拆分、shell virtual operations 推导（把 `cat` / `curl` / redirect 等映射为 `read_file` / `web_fetch` / `write_file`），还会用 AST 判断 shell 命令是否只读。这意味着它已经能“算出一个合理决策”。

问题在于，**用户几乎看不到这条决策链**。

当一个工具调用被拒绝或要求确认时，用户真正想知道的是：

- 是哪一条规则命中了？
- 是 shell 规则命中，还是 virtual file/web 规则命中？
- 是 `deny` 规则覆盖了 `allow`，还是没有任何规则命中而回退到默认模式？
- 如果我想放行，应该改 `/permissions` 里的哪条规则？
- 如果是 Hook 导致 ask/block，具体是哪一个 Hook？

Claude Code 在这方面明显更成熟：不仅有权限判定，还有一整套 **decision reason → UI explanation → debug info** 链路。它把“结果”与“原因”一起展示，让权限系统从黑盒变成可调试、可学习的交互系统。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/permissions/PermissionDecisionDebugInfo.tsx` | 展示 decision reason、rule/hook/mode/classifier/sandboxOverride/workingDir 等来源 |
| `components/permissions/PermissionRuleExplanation.tsx` | 把 `decisionReason` 转成用户可读解释，并给出 `/permissions` / `/hooks` 调整提示 |
| `components/permissions/PermissionExplanation.tsx` | 懒加载权限解释，展示 risk level / explanation / reasoning |
| `hooks/toolPermission/PermissionContext.ts` | 权限上下文状态 |
| `hooks/toolPermission/permissionLogging.ts` | 权限日志记录 |
| `tools/BashTool/commandSemantics.ts` | shell 语义分类辅助解释 |

**Qwen Code 现状**：权限判定逻辑很强，但可解释性弱。`packages/core/src/permissions/permission-manager.ts` 负责规则优先级计算（`deny > ask > allow > default`），还会结合 `extractShellOperations()` 做 shell virtual operation 判定；但返回结果主要是最终 decision，没有面向 UI 的“命中链路对象”。`packages/cli/src/ui/components/PermissionsDialog.tsx` 更像规则管理器：列出 allow/ask/deny 规则、支持搜索/增删，却不展示“某次具体决策为何发生”。用户能改规则，却不容易理解当前规则系统到底是怎么工作的。

**Qwen Code 修改方向**：
1. 在 `permission-manager.ts` 中新增 explain 模式：除了最终 decision，还返回 `decisionTrace`，至少包括：
   - 命中的规则（类型、来源、原始 rule 文本）
   - 是否发生 deny/ask 覆盖
   - 是否来自 shell virtual operations
   - 是否走了默认回退
2. 在 shell 场景下，把 `extractShellOperations()` 的推导结果挂入 trace，让用户知道“`cat foo` 为何等价于 `read_file(foo)`”；
3. 在工具确认 UI 中增加“Why?”/“Explain”视图，展示命中链和建议操作；
4. 在 `/permissions` 界面中增加“最近一次命中示例”或 dry-run tester，方便用户调试规则；
5. 后续可与 Hook Runtime 联动：若是 Hook 导致 ask/block，也统一走同一套 decision trace UI。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~250 行
- 开发周期：~3 天（1 人）
- 难点：在不破坏现有权限 API 的前提下为 UI 暴露结构化 trace

**改进前后对比**：
- **改进前**：用户只看到“被拒绝 / 需要确认”——但不知道是哪条规则、哪个层级、哪种语义命中导致的
- **改进后**：用户可看到完整 decision trace——例如“命中 project deny 规则 `WriteFile(/secrets/**)`，同时 shell 语义推导出 `echo > secrets.txt` 属于写文件操作，因此最终为 deny”

**意义**：权限系统越强，越需要 explainability。否则规则一多，用户只能靠试错。
**缺失后果**：权限引擎是黑盒——用户难以调试规则，常见结果是要么过度放权，要么频繁误拦截。
**改进收益**：decision trace 让权限系统可学习、可调试、可审计——特别适合复杂 shell、团队策略和企业治理场景。

---

## 为什么这不是现有“Denial Tracking / 权限对话框文件预览”的重复

- **Denial Tracking** 解决的是“连续拒绝后如何自动回退模式”；
- **权限对话框文件预览** 解决的是“审批时展示将要修改的文件内容”；
- **Permission Decision Trace** 解决的是“这次 allow / ask / deny 到底是怎么推导出来的”。

三者分别是 **回退策略**、**审批信息展示**、**决策可解释性**，层次不同。

---

## 可分阶段落地的演进路径

| 阶段 | 能力 | 说明 |
|------|------|------|
| Stage 1 | 基础 decision trace | 命中 rule、source、default fallback、virtual ops |
| Stage 2 | 确认 UI explain 面板 | 在工具确认框中展示“为什么 ask/deny” |
| Stage 3 | `/permissions test` dry-run | 给一条工具调用/命令，输出命中链与最终结果 |
| Stage 4 | 审计与导出 | 记录最近 N 次权限判定链，便于排障与企业审计 |

这样 Qwen Code 的权限系统才能从“规则引擎”进一步升级为“可调试的权限平台”。

---

## 相关文章

- [Hook Runtime 扩展](./qwen-code-improvement-report-p1-hooks-runtime.md)
- [Hook/插件扩展深度对比](./hook-plugin-extension-deep-dive.md)
- [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)
