# Qwen Code 改进建议 — P1 命令命名空间治理

> 命令系统改进项：当 built-in commands、文件命令、extension commands、MCP prompt commands 同时存在时，除了“能加载”，还需要解决命名冲突、来源隔离、前缀策略与治理边界。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Slash Command Namespace Governance / 命令命名空间治理（P1）

**思路**：Qwen Code 的 slash command 系统已经进入“平台化”阶段，而不再只是几十个内置命令。当前至少有四类来源会往命令空间里注入名字：

1. built-in commands
2. user / project 文件命令
3. extension commands
4. MCP prompt commands

当来源越来越多时，真正的挑战不再是“怎么加载命令”，而是：

- 谁可以占用顶级命令名？
- 重名时谁覆盖谁？
- extension 是否必须带命名空间前缀？
- MCP prompt 暴露成 slash command 时，是否应默认隔离到 server namespace？
- 用户如何知道某个命令来自 built-in、extension 还是 MCP？
- 团队/企业如何禁用某些来源或保留关键命令名？

Claude Code 在这方面采取的是更保守的合并策略：命令合并时倾向于保持稳定、可预测的名字集合；插件命令则走独立管理路径。Qwen Code 当前虽然有基础冲突处理，但规则仍偏“实现导向”，还没有发展成完整的 namespace governance。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `hooks/useMergedCommands.ts` | `uniqBy([...initialCommands, ...mcpCommands], 'name')`，保持命令名唯一 |
| `services/plugins/pluginCliCommands.ts` | 插件命令走独立 CLI 管理入口（install/uninstall/enable/disable/update） |
| `commands.ts` | 命令总表与内置命令体系 |

**Qwen Code 现状**：`packages/cli/src/services/CommandService.ts` 会并行加载所有 loader 返回的命令，然后统一放入一个 `Map<string, SlashCommand>`。当前冲突规则是：

- 如果是 extension command 且名字冲突，则自动改名为 `extensionName.commandName`，必要时再追加数字后缀；
- 非 extension commands（built-in / user / project / MCP prompt）则按 loader 顺序“后者覆盖前者”；
- `packages/cli/src/services/McpPromptLoader.ts` 会把 MCP prompt 直接暴露为 slash command 名，不默认带 server namespace。

这套策略“能工作”，但存在几个隐患：

1. **顶级命令名竞争**：MCP prompt 与 user/project 命令都可能占用短名字；
2. **来源不透明**：用户看到 `/deploy`，并不知道它来自 project file command、某个 MCP server prompt，还是 extension；
3. **覆盖策略不够显式**：非 extension 冲突靠 loader 顺序决定，行为可预测但不够易理解；
4. **治理能力不足**：缺少 reserved names、per-source enable/disable、source visibility 等平台机制。

**Qwen Code 修改方向**：
1. 为 slash command 引入显式 `source namespace` 概念，例如：
   - built-in: `/model`
   - extension: `/ext.foo.bar`
   - MCP prompt: `/mcp.github.review`
   - file command: `/local.deploy`
2. 对用户常用命令保留短别名，但短别名应由治理层决定，而不是“谁最后加载谁赢”；
3. 在补全列表与帮助界面中显示命令来源（built-in / extension / MCP / local）；
4. 增加 reserved name 策略，防止扩展或 MCP prompt 抢占关键命令；
5. 增加 per-source enable/disable 配置，方便团队/企业限制命令暴露面；
6. 对 MCP prompt 默认使用 `serverName.promptName` 命名，避免直接污染顶级命令空间。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~220 行
- 开发周期：~3 天（1 人）
- 难点：兼容现有短命令习惯，避免破坏已有用户工作流

**改进前后对比**：
- **改进前**：所有来源往同一个命令表注册——extension 有改名兜底，但 user/project/MCP prompt 之间仍可能靠加载顺序决定覆盖关系
- **改进后**：每类命令先进入各自 namespace，再由治理层决定哪些短别名暴露到顶级空间——冲突规则清晰、来源可见、企业可控

**意义**：命令系统一旦可扩展，就必须治理命名空间。
**缺失后果**：命令来源越多，顶级命令空间越混乱——冲突、覆盖、误调用会越来越频繁。
**改进收益**：命令来源透明 + 冲突策略清晰 + 保留字治理，让 slash command 系统从“加载器集合”升级为“可管理的平台能力”。

---

## 为什么这不是现有 slash command / MCP 文档的重复

- 现有 slash command 对比更多回答“有哪些命令”；
- MCP 集成对比更多回答“能否接入 MCP”；
- 本文讨论的是：**当命令来源变多后，命令名如何治理、如何隔离、如何防冲突**。

也就是说，它关注的是 **命令平台治理**，不是命令功能列表。

---

## 可分阶段演进路径

| 阶段 | 能力 | 说明 |
|------|------|------|
| Stage 1 | source 可视化 | 补全列表/帮助页展示命令来源 |
| Stage 2 | MCP / extension 默认命名空间 | 避免顶级命令空间污染 |
| Stage 3 | reserved names + alias policy | 保留关键短命令，统一别名分配 |
| Stage 4 | team policy | 团队/企业按来源禁用命令或限定前缀 |

这样 Qwen Code 的命令系统才能在继续开放扩展的同时保持可预测性。

---

## 相关文章

- [内置命令总览](./slash-commands-deep-dive.md)
- [MCP 集成深度对比](./mcp-integration-deep-dive.md)
- [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)
