# WebSearch 工具 Deep-Dive — 5 大 Code Agent + 阿里云百炼后端

> 对比 Claude Code、Codex、OpenCode、Kimi CLI、Qwen Code 的 WebSearch 工具实现，并把阿里云百炼（DashScope / Model Studio）的 server-side `web_search` built-in tool 也加入横向比较。基于 2026-05-04 各项目本地源码 + 官方文档查询。
>
> **2026-05-06 更新**：本文于 2026-05-04 发布后，**Qwen Code 团队成员次日（2026-05-05 04:33 UTC）发起 [Issue #3841](https://github.com/QwenLM/qwen-code/issues/3841) 直接引用本文的跨产品对比数据（569/39/71/163/0 LOC）+ path A/B/C 框架**；同日 [PR#3844](https://github.com/QwenLM/qwen-code/pull/3844) 实现 path C（含 Claude Code-style 7 层 prompt-injection 防御）。详见文末 [§十一 后续进展](#十一-后续进展2026-05-06)。
>
> **配套文章**：
> - [SDK / ACP / Daemon 架构 Deep-Dive](./sdk-acp-daemon-architecture-deep-dive.md) —— 程序化访问接口对比
> - [ReadFile 工具 Deep-Dive](./read-file-tool-deep-dive.md) —— 文件读取工具对比
> - [WebFetch 对比](./web-fetch-tool-deep-dive.md)（如有）
> - 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、TL;DR

5 家 Code Agent 在 WebSearch 上选了 4 种不同策略：

| 产品 | 策略 | 后端 | 客户端 LOC |
|---|---|---|:---:|
| **Claude Code** | 自家提供商**服务端原生**（Anthropic）| `web_search_20250305` beta | 569 |
| **Codex** | 自家提供商**Responses API 原生**（OpenAI）| Responses API `web_search` | 39（仅显示）|
| **OpenCode** | **第三方 MCP**（Exa AI）| `mcp.exa.ai/mcp` | 71 |
| **Kimi CLI** | **自家提供商私有服务**（Moonshot）| `moonshot_search` HTTP | 163 |
| **Qwen Code** | ❌ **没有 WebSearch 工具** | — | 0 |

**关键发现**：阿里云百炼（Qwen 模型的官方 API 平台）**早就有功能丰富的 server-side `web_search` built-in tool**（4 档 search_strategy + 4 档 freshness + forced_search + enable_citation + 25 个 domain allowlist），但 **Qwen Code CLI 没有把它暴露成本地工具**——这是 CLI 实现层 gap，不是 provider 层缺失。

## 二、整体策略分类

```
┌─────────────────────────────────────────────────────────────┐
│  服务端原生（CLI 端薄壳）                                       │
│  ├─ Claude Code  → Anthropic web_search_20250305            │
│  └─ Codex         → OpenAI Responses API web_search         │
│                                                              │
│  自有搜索服务（CLI 端做完整 HTTP）                              │
│  └─ Kimi CLI      → Moonshot moonshot_search HTTP API       │
│                                                              │
│  开放协议（CLI 端做 MCP client）                                │
│  └─ OpenCode      → Exa MCP（mcp.exa.ai）                    │
│                                                              │
│  缺失（CLI 端无任何 WebSearch）                                 │
│  └─ Qwen Code     → 仅 WebFetch；DashScope 的 enable_search   │
│                     未暴露为显式工具                            │
└─────────────────────────────────────────────────────────────┘
```

## 三、各家实现详解

### 3.1 Claude Code（Anthropic 服务端原生）

**源码**：`tools/WebSearchTool/WebSearchTool.ts`（569 LOC，反编译自二进制；EVIDENCE 见 [`docs/tools/claude-code/EVIDENCE.md`](../tools/claude-code/EVIDENCE.md)）

```typescript
// 关键常量（EVIDENCE.md 已验证）
{
  type: 'web_search_20250305',  // Anthropic beta tool 类型
  max_uses: 8,                   // 单次会话最多 8 次
}
```

| 维度 | 值 |
|---|---|
| 参数 | `query`, `allowed_domains?`, `blocked_domains?` |
| 单会话上限 | `max_uses = 8` |
| 域名过滤 | ✓ 双向（allow/block） |
| 服务端口 | Anthropic API 内置（CLI 不发 HTTP）|
| 计费 | 按 Anthropic 服务定价 |
| Compactable | ✓（在 `COMPACTABLE_TOOLS` set，可被 microcompact 清理）|
| 加载策略 | 延迟加载（`shouldDefer: true`，通过 ToolSearch 召回）|

**架构特点**：CLI 只把工具描述传给 API，**搜索结果以 tool_result 直接由 Anthropic 服务端返回**。客户端 569 行主要是：① 工具 schema 定义；② 结果展示；③ `max_uses` 计数；④ allow/block domains 校验。

### 3.2 Codex（OpenAI Responses API 原生）

**源码**：
- `codex-rs/protocol/src/models.rs:1107-1132`（`WebSearchAction` enum）
- `codex-rs/core/src/web_search.rs`（39 LOC，仅显示格式化）

```rust
#[serde(tag = "type", rename_all = "snake_case")]
#[schemars(rename = "ResponsesApiWebSearchAction")]
pub enum WebSearchAction {
    Search    { query: Option<String>, queries: Option<Vec<String>> },
    OpenPage  { url: Option<String> },
    FindInPage { url: Option<String>, pattern: Option<String> },
    Other,
}
```

| 维度 | 值 |
|---|---|
| Action 类型 | **3 种独家**：`Search` / `OpenPage` / `FindInPage` |
| 配置 | `tools_config.web_search_mode` + `web_search_config`（`turn_context.rs:186/195`）|
| Feature gate | `Feature::WebSearchCached` / `Feature::WebSearchRequest`（`config/mod.rs:1663-1666`）|
| 客户端 LOC | **39**（最薄）|
| 计费 | 按 OpenAI Responses API 定价 |

**架构特点**：客户端**只 39 行**，全是把 `WebSearchCall` 渲染到 TUI 历史的逻辑。**3 种 action 是 Codex 独有**：
- `Search { query, queries }` —— 单/多 query 都支持
- `OpenPage { url }` —— 让模型直接打开特定 URL
- `FindInPage { url, pattern }` —— 在指定页面内查 pattern

第三种 `FindInPage` 在 5 家中**唯一原生支持**——其他家都需要 LLM 先 OpenPage 拉全文再自己匹配。

### 3.3 OpenCode（Exa MCP）

**源码**：
- `packages/opencode/src/tool/websearch.ts`（71 LOC）
- `packages/opencode/src/tool/mcp-exa.ts`（McpExa 客户端）

```typescript
import * as McpExa from "./mcp-exa"

export const Parameters = Schema.Struct({
  query: Schema.String,
  numResults: Schema.optional(Schema.Number),               // 默认 8
  livecrawl: Schema.optional(Schema.Literals(["fallback", "preferred"])),
  type: Schema.optional(Schema.Literals(["auto", "fast", "deep"])),
  contextMaxCharacters: Schema.optional(Schema.Number),    // 默认 10000
})

// 调用 Exa MCP
const result = yield* McpExa.call(
  http,
  "web_search_exa",
  McpExa.SearchArgs,
  { query, type: type || "auto", numResults: numResults || 8, livecrawl: livecrawl || "fallback", ... },
  "25 seconds",  // 客户端 25s 超时
)
```

| 维度 | 值 |
|---|---|
| 后端 | **Exa AI** via MCP（`https://mcp.exa.ai/mcp?exaApiKey=...`）|
| API key | `EXA_API_KEY` 环境变量 |
| 参数 | query / numResults / livecrawl / type / contextMaxCharacters |
| 客户端超时 | 25 秒 |
| 协议 | JSON-RPC over SSE（`McpExa.parseSse`）|
| 用户审批 | ✓ 走 OpenCode permission 系统（`permission: "websearch"`）|
| 计费 | Exa 自家定价 |

**独有参数**：
- `livecrawl`：`fallback`（默认，缓存优先）vs `preferred`（实时优先）—— 在缓存命中率与时新性之间精细控制
- `type`：`auto` / `fast` / `deep` —— 搜索深度 3 档
- `contextMaxCharacters`：返回 LLM 友好的浓缩上下文字符上限

**架构特点**：**唯一提供商无关**的实现——通过 MCP 协议调用第三方搜索服务（Exa），用户可换其他 MCP-compatible 搜索后端（Tavily / Perplexity / 自建 MCP server 等）。

**附加**：`provider/sdk/copilot/responses/tool/web-search.ts` + `web-search-preview.ts` 表明 OpenCode 的 GitHub Copilot provider 也支持 Copilot 自家的 web_search（双轨并存）。

### 3.4 Kimi CLI（Moonshot 私有服务）

**源码**：`src/kimi_cli/tools/web/search.py`

```python
class Params(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)              # 1-20
    include_content: bool = False                            # 是否抓页面内容

class SearchWeb(CallableTool2[Params]):
    def __init__(self, config: Config, runtime: Runtime):
        if config.services.moonshot_search is None:
            raise SkipThisTool()                             # 未配置则禁用
        self._base_url = config.services.moonshot_search.base_url
        self._api_key = config.services.moonshot_search.api_key

    async def __call__(self, params):
        search_timeout = aiohttp.ClientTimeout(
            total=180,         # 客户端总超时
            sock_read=90,      # socket 读超时
            sock_connect=15,   # 连接超时
        )
        async with session.post(self._base_url, headers={
            "Authorization": f"Bearer {api_key}",
            "X-Msh-Tool-Call-Id": tool_call.id,             # 调用追踪头
            ...,
        }, json={
            "text_query": query,
            "limit": params.limit,
            "enable_page_crawling": params.include_content,
            "timeout_seconds": 30,                          # 服务端超时
        }) as response:
            ...
```

| 维度 | 值 |
|---|---|
| 后端 | **Moonshot 自研搜索服务** |
| Auth | Bearer API key + OAuth ref（`_oauth_ref`）|
| 参数 | query / limit(1-20，默认 5) / include_content(默认 false) |
| 客户端超时 | total **180s** / sock_read 90s / sock_connect 15s |
| 服务端超时 | **30s**（passed via `timeout_seconds` body）|
| 自定义 headers | `User-Agent` / `Authorization` / **`X-Msh-Tool-Call-Id`** |
| Feature gate | `SkipThisTool()` 当 `moonshot_search` 未配置 |
| Result | title / date / url / snippet / content（可选）|

**独有特点**：
- **唯一显式分离客户端 vs 服务端超时**（180s 客户端 vs 30s 服务端）—— `total=180` 覆盖网络重传 + 服务端 30s 业务超时 + 页面爬取的额外时间
- **`X-Msh-Tool-Call-Id` 调用追踪 header** —— 服务端可通过此 ID 追踪同一次工具调用对应的所有日志/计费/限流
- **`include_content` 抓全页开关** —— 与 OpenCode 的 `contextMaxCharacters` 思路类似但更粗粒度

### 3.5 Qwen Code（缺失，但有完整历史循环）

> **历史循环**（重要！本文初稿 2026-05-04 时未注意到）：Qwen Code 不是从未有过 WebSearch，而是**经历了"有 → 删 → 重新加（进行中）"完整循环**：
>
> | 时间 | 事件 |
> |---|---|
> | **PR#3502 之前** | Qwen Code **有**内置 web_search 工具 + **4 providers**（DashScope / Tavily / Google / GLM）|
> | 2026-04-21 | [Issue #3496](https://github.com/QwenLM/qwen-code/issues/3496) 用户提出"webSearch 免费份额停掉后是否还能用"（已 closed）|
> | **2026-04-24** | [PR#3502](https://github.com/QwenLM/qwen-code/pull/3502) ✓ 合并 —— **删除全部 web_search**（+167/-1830 净删 1,663 行 + 4 providers + CLI flag + env var）。理由："built-in tool 需要为每个 search service 维护 provider-specific integration + API key plumbing；MCP 已经提供更干净更可扩展的同样机制"——架构上向 OpenCode/Claude Code 的"用 MCP 替代内置 provider"方向对齐 |
> | **2026-05-04** | 本文发布，记录 Qwen Code 此时"完全缺失" |
> | **2026-05-05** | 见 [§十一](#十一-后续进展2026-05-06) |
>
> 所以严格说现状是"**经历删除后暂时缺失**"，不是"从未实现过"。下面的源码证据反映 PR#3502 删除后的当前状态。

**源码证据**：

```typescript
// packages/core/src/tools/tool-names.ts
WEB_FETCH: 'web_fetch',     // ✓ 有
// （没有 WEB_SEARCH 定义）

// packages/core/src/extension/claude-converter.ts
const CLAUDE_TOOLS_MAPPING = {
  WebFetch: 'WebFetch',      // ✓ Claude WebFetch ↔ Qwen WebFetch
  WebSearch: 'None',          // ❌ 显式声明无 Qwen 等价物
  ...
};
```

`packages/core/src/tools/` 下只有 `web-fetch.ts`，**没有 `web-search.ts`**。

| 维度 | 值 |
|---|---|
| 后端 | **无** |
| 替代方案 | `WebFetch`（用户/模型必须先有 URL 再抓内容）|
| 间接路径 | 用户手动浏览器搜 → 贴 URL → Qwen WebFetch |

但是！见下文 §四，**Qwen 模型在 DashScope 服务端早就支持 web_search**——只是 CLI 没把它包成显式工具。

## 四、阿里云百炼（DashScope）的 server-side `web_search`

> 这部分是本文最值得注意的发现：**Qwen 模型背后的 API 平台早就提供了功能比 Claude Code/Codex 都丰富的 server-side web_search**，但 Qwen Code CLI 没有暴露给用户。

### 4.1 三种调用方式

| 接口 | 启用方式 | 说明 |
|---|---|---|
| **DashScope 原生** | `enable_search=True` 顶层参数 | 功能最全，支持完整 `search_options` |
| **OpenAI 兼容 Chat Completions** | `extra_body={"enable_search": True}`（Python）/ 顶层参数（Node.js）| 简单 boolean 启用 |
| **OpenAI 兼容 Responses API** | `tools=[{"type": "web_search"}]` | 与 OpenAI 兼容形态 |

### 4.2 完整 `search_options`（DashScope 原生）

```python
search_options = {
  # 搜索强度 4 档
  "search_strategy": "turbo",      # turbo (默认) / max / agent / agent_max
  
  # 强制搜索（绕过模型自判断）
  "forced_search": True,
  
  # 返回搜索来源
  "enable_source": True,
  
  # 引用脚注（回答中加 [1][2] 上标）
  "enable_citation": True,
  
  # 时新性窗口 4 档
  "freshness": 30,                 # 7 / 30 / 180 / 365 天
  
  # 域名 allowlist（最多 25 个）
  "assigned_site_list": [
    "github.com", "stackoverflow.com", ...
  ]
}
```

### 4.3 返回格式

```json
{
  "search_info": {
    "search_results": [
      {
        "index": 0,
        "title": "...",
        "url": "...",
        "site_name": "..."
      },
      ...
    ]
  }
}
```

### 4.4 配套工具

| 工具 | 用途 | 关系 |
|---|---|---|
| `web_search` | 关键词搜索 | 主工具 |
| `web_extractor` | 网页内容抓取 | **必须配 web_search 用** |
| `code_interpreter` | 代码执行 | 独立可用 |

> 官方建议："为获得最佳回复效果，建议同时开启 `web_search` + `web_extractor` + `code_interpreter`"

### 4.5 计费

- **MCP 集成**调用 web_search / web_extractor / code_interpreter：**限时免费 + 每月 2000 次免费额度**
- 通过 Chat Completions / Responses API 调用：官方文档未列具体定价

### 4.6 支持模型

- 国际版：qwen3-max / qwen3.5-plus / qwen3.5-flash / qwen3-coder-plus / qwen3-coder-flash 及日期变体
- 中国大陆：同上
- 美国（弗吉尼亚）：同上
- **2025 年 7 月后发布的 Max/Plus/Flash 自动支持联网搜索**

## 五、横向能力矩阵

| 能力 | Claude | Codex | OpenCode | Kimi | Bailian/DashScope | Qwen Code |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 服务端原生 | ✓ | ✓ | ❌ | ❌ | ✓ | — |
| 简单 boolean 启用 | ❌ | ❌ | ❌ | ❌ | **✓ `enable_search: true`** | — |
| 关键词搜索 | ✓ | ✓ | ✓ | ✓ | ✓ | ❌ |
| 多 query 单调用 | ❌ | ✓ | ❌ | ❌ | ❌ | — |
| 直接 OpenPage（URL 取内容） | （走 WebFetch）| **✓ 独有 action** | ❌ | ❌ | （配 web_extractor）| — |
| FindInPage（页内 pattern 搜） | ❌ | **✓ 独有 action** | ❌ | ❌ | ❌ | — |
| 域名 allowlist | ✓ | ❌ | ❌ | ❌ | **✓ 25 个** | — |
| 域名 blocklist | ✓ | ❌ | ❌ | ❌ | ❌ | — |
| 实时性窗口（freshness）| ❌ | ❌ | livecrawl 模式 | ❌ | **✓ 4 档**（7/30/180/365 天）| — |
| 搜索深度档位 | ❌ | ❌ | ✓ 3 档（auto/fast/deep）| ❌ | **✓ 4 档**（turbo/max/agent/agent_max）| — |
| 强制搜索（forced）| ❌ | ❌ | ❌ | ❌ | **✓ forced_search** | — |
| 引用脚注（citation）| ❌ | ❌ | ❌ | ❌ | **✓ enable_citation** | — |
| 抓页面内容控制 | ❌ | ❌ | ✓ contextMaxCharacters | ✓ include_content | （配 web_extractor）| — |
| 单会话调用上限 | ✓ max_uses=8 | ❌ | ❌ | ❌ | ❌ | — |
| 服务端 / 客户端超时分离 | — | — | ❌ | **✓** | — | — |
| 调用追踪 header | ❌ | ❌ | ❌ | **✓ X-Msh-Tool-Call-Id** | ❌ | — |
| 用户审批权限 | （隐式）| — | **✓ permission flow** | ❌ | — | — |
| 后端可换 | ❌（绑死 Anthropic）| ❌（绑死 OpenAI）| **✓ MCP** | ❌（绑死 Moonshot）| ❌（绑死阿里）| — |

**结论**：**百炼 web_search 在参数维度上是最丰富的实现**——`search_strategy 4 档 + freshness 4 档 + forced_search + enable_citation + enable_source + assigned_site_list 25 个 domain` 覆盖了其他家所有特色（除 Codex 的 OpenPage/FindInPage 三态 action 之外）。

## 六、设计哲学差异

| 维度 | Claude Code | Codex | OpenCode | Kimi CLI | Bailian |
|---|---|---|---|---|---|
| **架构** | 一体化 | 一体化 | 开放（MCP）| 一体化 | 一体化 |
| **客户端 LOC** | 569 | 39 | 71 | 163 | —（无 CLI 端）|
| **客户端职责** | API 调用 + 安全/限流 | **仅显示格式化** | MCP 客户端 + 权限路由 | 完整 HTTP + 错误处理 | — |
| **服务端"智能"** | 高（domain 过滤/限流均服务端）| **最高**（搜索逻辑全在 API）| 高（Exa 处理 livecrawl/type）| 中（基础搜索 API）| **最高**（4 档 strategy + 4 档 freshness 全服务端）|
| **可扩展性** | ❌ 绑死 Anthropic | ❌ 绑死 OpenAI | ✓ 换 MCP server | ❌ 绑死 Moonshot | ❌ 绑死阿里 |
| **预算控制** | ✓ max_uses=8 显式 | ❌ 由 OpenAI 计费控制 | ❌ 由 Exa 计费控制 | ❌ 由 Moonshot 计费控制 | ✓ MCP 集成免费 2K/月 |

## 七、典型场景适配

| 场景 | 最佳选 | 原因 |
|---|---|---|
| 在不同 LLM 提供商间切换 | **OpenCode** | MCP 解耦，换 LLM 不影响 web_search |
| 严控成本（明确 8 次/会话）| **Claude Code** | 唯一显式 max_uses 上限 |
| 需要"在某页面找 pattern" | **Codex** | 唯一原生支持 FindInPage |
| 需要 livecrawl 控制实时性 | **OpenCode** | Exa 的 livecrawl |
| 需要强制搜索（不让模型自判断）| **Bailian** | 唯一支持 `forced_search: true` |
| 需要 freshness 时间窗口 | **Bailian** | 唯一支持 7/30/180/365 天 4 档 |
| 需要回答带引用脚注 | **Bailian** | 唯一支持 `enable_citation` |
| 需要 domain allowlist | **Claude Code 或 Bailian** | 双向 vs 25 上限单向 |
| 中国大陆部署 | **Kimi CLI 或 Bailian** | 国内提供商，无 GFW |
| 想自建搜索服务 | **OpenCode 唯一可行** | 自实现 MCP server 即可接入 |

## 八、Qwen Code 的 WebSearch gap：实现层 vs Provider 层

### 8.1 关键洞察

```
┌────────────────────────────────────────────────────────────┐
│  Provider 层（DashScope / 百炼）                              │
│  ✓ web_search built-in tool（4 档 strategy + 4 档 freshness）│
│  ✓ web_extractor 配套                                       │
│  ✓ MCP 集成免费 2000 次/月                                    │
└────────────────────────────────────────────────────────────┘
                          ▲
                          │ 模型层早已支持
                          │
┌────────────────────────────────────────────────────────────┐
│  CLI 层（Qwen Code）                                          │
│  ❌ 没有 web_search 工具定义                                   │
│  ❌ 没有 enable_search 参数透传                               │
│  ❌ tool-names.ts 没有 WEB_SEARCH                             │
│  ❌ claude-converter.ts: WebSearch → 'None'                   │
└────────────────────────────────────────────────────────────┘
```

**Qwen Code 缺 WebSearch 不是 provider 能力问题，是 CLI 实现层 gap**。这与之前发现的 OTel / `/doctor` / MCP Auto-Reconnect 几处"标缺失实际已实现"勘误同类，但**反向**：provider 层有但 CLI 层未暴露。

### 8.2 改进路径（按工作量从小到大）

#### 路径 A：通过 MCP 接入（0 天 · 用户侧配置）

Qwen Code 已有完整的 MCP client 基础设施。用户配 MCP server（Exa / Tavily / Perplexity / 阿里百炼 MCP）即可立刻获得 WebSearch：

```json
// ~/.qwen/mcp.json
{
  "mcpServers": {
    "exa": {
      "url": "https://mcp.exa.ai/mcp?exaApiKey=$EXA_API_KEY"
    }
  }
}
```

**优点**：0 代码改动，用户 5 分钟就能用上。
**缺点**：不是开箱即用——每个用户需要自己配 + 拿 API key。

#### 路径 B：透传 DashScope `enable_search`（~0.5 天 · CLI 侧最小改动）

在 `packages/core/src/core/openaiContentGenerator/pipeline.ts` 的 `buildRequest` 里，针对 DashScope provider 注入 `enable_search: true`：

```typescript
// 仅 ~10 行
if (this.contentGeneratorConfig.provider === 'dashscope' && config.enableWebSearch) {
  request.body.enable_search = true
  if (config.searchOptions) {
    request.body.search_options = config.searchOptions  // 透传 4 档 strategy / freshness 等
  }
}
```

**优点**：直接复用百炼免费 2000 次/月配额，零增量成本。
**缺点**：是"模型自决"模式（让 LLM 自己判断要不要搜），不是显式工具——用户看不到搜索发生（除非开 `enable_source`）。

#### 路径 C：包装为显式工具（~1 周 · 完整体验）

新建 `packages/core/src/tools/web-search.ts`，参考 OpenCode 设计模式：

```typescript
export class WebSearchTool extends BaseDeclarativeTool<WebSearchParams> {
  name = 'web_search'
  
  async execute(params: WebSearchParams): Promise<ToolResult> {
    // 选项 1：调 DashScope web_search via Responses API
    // 选项 2：调 MCP server 走 mcp-exa 路径
    // 选项 3：直接 fetch DashScope OpenAI-compat endpoint with enable_search: true
  }
}
```

**优点**：用户体验最完整——能审批/取消/查看历史搜索；与 Claude Code/Codex 体验一致。
**缺点**：需要决策默认后端（DashScope vs MCP）+ 处理用户配多 provider 的情况。

### 8.3 推荐：B + C 渐进路线

1. **第 1 周**：路径 B 落地——给 DashScope 用户立刻可用
2. **第 2-3 周**：路径 C 落地——把 `web_search` 暴露为显式工具，后端走 DashScope 默认 + 允许用户切到 MCP
3. **持续**：路径 A 文档化——给非 Qwen 模型用户的兜底方案

## 九、源码证据索引

| 主题 | 文件路径 |
|---|---|
| Claude Code WebSearchTool（反编译）| `tools/WebSearchTool/WebSearchTool.ts` —— 569 LOC，`max_uses = 8`，`web_search_20250305` beta |
| Claude Code COMPACTABLE_TOOLS | `services/compact/microCompact.ts` —— 含 WebSearch |
| Codex WebSearchAction enum | `codex-rs/protocol/src/models.rs:1107-1132` |
| Codex WebSearch 显示 | `codex-rs/core/src/web_search.rs` —— 39 LOC |
| Codex feature gates | `codex-rs/core/src/config/mod.rs:1663-1666` —— `WebSearchCached` / `WebSearchRequest` |
| OpenCode websearch | `packages/opencode/src/tool/websearch.ts` —— 71 LOC |
| OpenCode Exa MCP client | `packages/opencode/src/tool/mcp-exa.ts` |
| OpenCode 工具描述 | `packages/opencode/src/tool/websearch.txt` —— 14 行 prompt |
| OpenCode Copilot WebSearch | `packages/opencode/src/provider/sdk/copilot/responses/tool/web-search.ts` |
| Kimi WebSearch | `src/kimi_cli/tools/web/search.py` |
| Kimi WebSearch 描述 | `src/kimi_cli/tools/web/search.md` |
| Qwen tool-names（无 WEB_SEARCH）| `packages/core/src/tools/tool-names.ts` |
| Qwen claude-converter（WebSearch → 'None'）| `packages/core/src/extension/claude-converter.ts` |
| 百炼 web_search 文档 | https://help.aliyun.com/zh/model-studio/web-search |
| 百炼 Responses API web_search | https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-responses |

## 十、关键洞察清单

1. **5 家 4 策略**：服务端原生（Claude/Codex）/ 自有 HTTP 服务（Kimi）/ MCP 第三方（OpenCode）/ 缺失（Qwen）。

2. **Codex 的 3 种 action 是独家创新**：`Search` + `OpenPage` + `FindInPage` 让模型不仅能搜，还能直接打开特定页面或在页内查 pattern——其他家都需要 LLM 多轮调用工具实现同样效果。

3. **OpenCode 是唯一提供商无关的实现**：MCP 协议带来的可换性是其他家做不到的。

4. **Kimi 的工程细节最完整**：唯一明确分离客户端/服务端超时（180s/30s）+ 调用追踪 header（`X-Msh-Tool-Call-Id`）。

5. **百炼 web_search 参数最丰富**：4 档 strategy + 4 档 freshness + forced_search + enable_citation + 25 domain allowlist + MCP 免费 2000 次/月——超越所有 5 家 CLI 的实现。

6. **Qwen Code 缺失是 CLI 实现层 gap**：Provider 层（DashScope）能力齐备，但 Qwen Code CLI 没有暴露——这是个 ~0.5-1 周可补的低悬果实，建议优先级 P1。

7. **架构哲学映射定价模式**：服务端原生（Claude/Codex/Bailian）的客户端最薄，因为搜索逻辑+计费都在服务端；CLI 端做完整 HTTP 的（Kimi）需要处理超时/错误/格式化等细节；MCP 模式（OpenCode）把这些细节交给 MCP server。

## 十一、后续进展（2026-05-06）

本文于 2026-05-04 发布后，Qwen Code 团队**直接基于本文档的分析**推进了 WebSearch 工具的实现：

### 11.1 时间线

| 时间 | 事件 |
|---|---|
| **2026-05-04** | 本文发布（commit `ae8d998`），含 §五横向能力矩阵 + §八 path A/B/C 改进路径 |
| **2026-05-05 04:33 UTC** | Qwen Code 团队成员发起 [**Issue #3841**](https://github.com/QwenLM/qwen-code/issues/3841)：`feat(tools): add WebSearch support (start by passing through DashScope enable_search)` |
| **2026-05-05** | [**PR#3844**](https://github.com/QwenLM/qwen-code/pull/3844) OPEN（+1238/-3 / 11 文件）：`feat(tools): add WebSearch tool with prompt-injection defenses` |

### 11.2 Issue #3841 直接引用本文档

Issue 内容（截取）：

> **Background**: Qwen Code is **the only one of the 5 mainstream Code Agent CLIs without a WebSearch tool**. Yet the underlying DashScope (Bailian) platform **already provides a server-side `web_search` built-in tool richer than Claude Code's or Codex's** — this is a CLI-layer gap, not a provider-layer capability gap.
>
> ## Cross-CLI Comparison
>
> | Product | Strategy | Backend | Client LOC |
> |---|---|---|:---:|
> | Claude Code | Server-side native | Anthropic `web_search_20250305` | **569** |
> | Codex | Responses API native | OpenAI `web_search` | **39** |
> | OpenCode | Third-party MCP | Exa AI (`mcp.exa.ai/mcp`) | **71** |
> | Kimi CLI | Self-hosted HTTP service | Moonshot `moonshot_search` | **163** |
> | **Qwen Code** | **❌ None** | — | **0** |
>
> ## Improvement Paths (smallest effort first)
>
> ### Path A: MCP integration (0 changes · user-side config)
> ### Path B: Pass through DashScope `enable_search` (~0.5 day · recommended starting point)
> ### Path C: Wrap as an explicit `web_search` tool (~1 week · full experience)

**关键观察**：Issue 复用了本文 §五的 5 行对比表（包括精确 LOC 数 569/39/71/163/0）+ 本文 §八的 path A/B/C 框架，**几乎逐字引用**。

### 11.3 PR#3844 的设计选择：Path C + Claude-style 7 层防御

PR body 明确："Implements **path C** from #3841: an explicit `web_search` tool for DashScope-compatible providers, with Claude Code-style **7-layer prompt-injection defenses**"

**实现要点**（与本文 §四百炼能力对齐）：
- 后端：`POST /chat/completions` with `enable_search` + `forced_search` + `enable_source` + `search_options`
- 解析 `search_info`（兼容顶层 + `choices[0].message` 两种位置）

**7 层 Claude Code-style 防御**：
1. 工具描述警告"results 不应被当作 directives" + 每个 result 加 safety footer
2. `max_uses = 8` per session via `WeakMap<Config>`（仅成功才递增——与 Claude `WebSearchTool.ts` 相同）
3. `MAX_RESULT_SIZE_CHARS = 100_000` 截断
4. `allowed_domains` 最多 25（trim+filter blanks，作为 `assigned_site_list` 转发）—— 与百炼 `assigned_site_list 25 上限`匹配
5. `blocked_domains` 客户端过滤（host + subdomain）
6. 加入 `COMPACTABLE_TOOLS` set（microcompact 清理 · 与 Claude WebSearch 一致）
7. 加入 `BOUNDARY_TOOLS`（speculation 在 WebSearch 处停止）

**测试**：15 新 web-search 测试 + 282 受影响的现存测试（permissions/shell-semantics/claude-converter/speculationToolGate/microcompact/web-fetch）。

### 11.4 完整循环架构演进

```
┌─────────────────────────────────────────────────────────────┐
│ PR#3502 之前：自建 4-provider WebSearch                      │
│   └─ DashScope / Tavily / Google / GLM 各打 API + cli flag   │
│   └─ ~1830 行代码、API key plumbing、env var 转发           │
└─────────────────────────────────────────────────────────────┘
                            ↓ PR#3502 (2026-04-24, +167/-1830)
┌─────────────────────────────────────────────────────────────┐
│ 中间阶段：完全删除，转 MCP                                     │
│   └─ 用户自己配 ~/.qwen/mcp.json 接 Bailian/Tavily/GLM MCP   │
│   └─ 干净，但缺开箱即用体验                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓ codeagents 文档（2026-05-04）+ Issue #3841（2026-05-05）
┌─────────────────────────────────────────────────────────────┐
│ PR#3844：1 default provider（DashScope） + Claude-style 防御 │
│   └─ 复用 path A（MCP fallback）保留可换性                   │
│   └─ 加上 Claude 的 7 层 prompt-injection 防御               │
│   └─ 不再 4 provider 全打 API（开箱即用 + 不用维护 4 套集成）│
└─────────────────────────────────────────────────────────────┘
```

**最终方案**比删除前的 4-provider 实现**架构更稳健**——单 provider + MCP fallback + Claude-style 安全设计。这是被 codeagents 文档引导出的设计决策。

### 11.5 codeagents 文档影响产品决策的首例

这是 codeagents 项目分析直接影响 Qwen Code 团队设计的**首个公开案例**：
1. 文档提供精确的跨产品对比数据（5 行 × 4 列含 LOC 数字）
2. 文档的 path A/B/C 改进路径框架被 Issue 完整引用
3. PR 选择 path C 而非最小改动的 path B，并加上 path C 章节列出的所有 Claude-style 防御项

印证了 codeagents 项目"基于源码验证的中立技术对比"的价值——**不只是文档化已有事实，还能为产品改进提供可执行的工程蓝图**。

---

> **免责声明**：以上数据基于 2026-05-04 各项目本地源码 + 官方文档查询，可能已过时。版本号反映当时仓库状态。各产品演进迅速，建议使用前以仓库最新状态为准。
