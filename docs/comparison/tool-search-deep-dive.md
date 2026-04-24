# 工具动态发现与延迟加载 Deep-Dive

> 39+ 个工具的 schema 全部注入系统提示会浪费大量 token。本文基于 Claude Code（v2.1.89 源码分析）的源码分析，介绍其 ToolSearchTool 延迟加载机制——仅加载核心工具，其余按需搜索。

> **🟡 进度追踪（2026-04-24）**：[**PR#3589**](https://github.com/QwenLM/qwen-code/pull/3589) OPEN —— `feat(tools): add ToolSearch for on-demand loading of deferred tool schemas` 直接实现本文描述的方向。度量：典型 39-tool setup 节省 **~15K tokens/request**。
>
> **实现要点**：
> - `DeclarativeTool` 新增 `shouldDefer` / `alwaysLoad` / `searchHint` 三个标志
> - 默认 deferred：MCP 工具 + `lsp` / `cron_*` / `ask_user_question` / `exit_plan_mode`
> - `ToolSearch` 双模式：`select:Name1,Name2` 精确匹配 + 关键词搜索（支持 `+must-word` 必需词）
> - 评分对齐 Claude Code spec：built-in **10/5/4/2**（name/substring/hint/desc），MCP **12/6**（偏向 MCP 以鼓励发现）
> - **Resume 支持**：`startChat` 扫描历史 function calls 重新 reveal 之前用过的 deferred 工具
> - **Compaction 保留**：`/clear` 清 revealed，压缩路径（`startChat(newHistory)`）保留
> - Subagent wildcard `['*']` 通过 `includeDeferred: true` 保持向后兼容
> - 21 文件 / +1051/-11 行 / 20 个新测试 case
>
> 合并后本项目可升级为 ✓ **已实现**。

---

## 1. 问题与方案

| 方案 | 系统提示 Token | 工具可用性 |
|------|:---:|:---:|
| **全量加载** | ~15,000+（39 工具 schema） | 全部可用 |
| **延迟加载**（Claude Code） | ~5,000（~10 核心工具） | 核心始终可用，其余按需 |

Claude Code 通过 `ToolSearchTool` 实现第二种方案——核心工具始终在系统提示中，其余工具的 schema 仅在模型调用 ToolSearch 时注入。

---

## 2. 延迟加载分类

```typescript
// 源码: tools/ToolSearchTool/prompt.ts#L62-L108
// 分类逻辑:
```

| 类别 | 条件 | 示例 |
|------|------|------|
| **始终加载** | `alwaysLoad: true` 或特殊角色 | ToolSearch 自身、Agent（FORK_SUBAGENT 启用时）、BriefTool、SendUserFileTool |
| **延迟加载** | `shouldDefer: true` 或 MCP 工具 | WebFetch、WebSearch、NotebookEdit、CronCreate、TaskCreate 等 |
| **MCP 工具** | 始终延迟 | 所有 `mcp__*` 前缀工具 |

---

## 3. 搜索模式

### 3.1 Select 模式（直接选择）

```
ToolSearch(query: "select:WebFetch,NotebookEdit")
→ 精确匹配工具名（大小写不敏感）
→ 返回匹配工具的完整 schema
→ 已加载工具也会返回（无害的 no-op）
```

> 源码: `tools/ToolSearchTool/ToolSearchTool.ts#L363-L405`

### 3.2 Keyword 模式（模糊搜索）

```
ToolSearch(query: "notebook jupyter")
ToolSearch(query: "+slack send")       ← + 前缀 = 必须匹配
```

**评分算法**（源码: `ToolSearchTool.ts#L186-L302`）：

| 匹配类型 | MCP 工具 | 普通工具 |
|----------|:--------:|:--------:|
| 工具名精确部分匹配 | 12 分 | 10 分 |
| 工具名部分匹配 | 6 分 | 5 分 |
| `searchHint` 匹配 | 4 分 | 4 分 |
| 描述匹配（词边界） | 2 分 | 2 分 |
| 全名回退 | 3 分 | 3 分 |

**MCP 工具评分略高**——因为 MCP 工具始终延迟，搜索是唯一发现路径。

### 3.3 Schema

```typescript
// 输入:
{ query: string, max_results?: number }  // max_results 默认 5

// 输出:
{
  matches: [{ name, description, schema }],
  query: string,
  total_deferred_tools: number,
  pending_mcp_servers?: string[]  // 仍在连接中的 MCP 服务器
}
```

---

## 4. 缓存策略

```typescript
// 源码: ToolSearchTool.ts#L66-L100
// 工具描述缓存:
getToolDescriptionMemoized(toolName)
  → 首次调用: 生成描述 + schema
  → 后续调用: 返回缓存
  → 延迟工具集变化时: maybeInvalidateCache() 清除

// Schema 延迟加载:
lazySchema()  → 仅在 ToolSearch 被调用时加载 schema
```

---

## 5. 系统提示中的呈现

当 ToolSearch 启用时，系统提示中不列出延迟工具的完整 schema，而是一段引导文本：

```
The following deferred tools are available via ToolSearch:
AskUserQuestion, CronCreate, CronDelete, CronList, ...
```

模型看到这段文本后，知道可以通过 `ToolSearch(query: "select:AskUserQuestion")` 获取完整 schema。

---

## 6. Qwen Code 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 工具加载 | 核心始终 + 其余延迟 | 全部始终加载 |
| 搜索工具 | ToolSearchTool（keyword + select） | 无 |
| MCP 工具 | 始终延迟 | 始终加载 |
| 系统提示 Token | ~5,000（核心） | ~15,000+（全部） |
| 缓存 | 描述缓存 + 变更失效 | N/A |

---

## 7. 关键源码文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `tools/ToolSearchTool/ToolSearchTool.ts` | 472 | 搜索引擎（keyword/select/评分/缓存） |
| `tools/ToolSearchTool/prompt.ts` | 122 | 延迟分类逻辑 + 系统提示文本 |
| `tools/ToolSearchTool/constants.ts` | 1 | 常量 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。
