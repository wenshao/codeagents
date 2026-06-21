# MCP 支持完整性对比 Deep-Dive（Codex / Claude Code / Qwen Code / OpenCode / Qoder CLI）

> 五家 Code Agent 对 **MCP（Model Context Protocol）** 的支持，谁更完整？本文对照 MCP spec **v2025-06-18** 的能力面，逐项核验——Qwen/Codex/OpenCode 本地源码直接钉死，Claude Code 以官方文档为准，Qoder 闭源以反编译二进制 EVIDENCE 为准。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md) · [Deep-Dive 索引](./deep-dive-index.md) · 相关 [MCP 集成对比](./mcp-integration-deep-dive.md) / [Codex MCP Server](./codex-mcp-server-deep-dive.md) / [MCP 自动重连](./mcp-auto-reconnect-deep-dive.md)

> **一句话结论 + 排名**：**Claude Code > Codex ≈ Qwen Code > OpenCode > Qoder CLI**。三条分水岭：① **Sampling**（server 反向借用 client 的 LLM）只有 Claude Code 支持；② **自身作 MCP server**（被别的 LLM 当工具调用）Claude/Codex/Qwen 有，**OpenCode/Qoder 仅客户端**；③ **WebSocket** 传输仅 Claude Code。其余 client 能力（tools/resources/prompts/roots/OAuth）五家大体齐全，差异在 **elicitation**（OpenCode 显式禁用）。

---

## 一、评估维度：MCP 能力面

MCP 不只是"调用外部工具"。完整性看四组能力：

| 组 | 能力 | 含义 |
|----|------|------|
| **传输** | stdio / SSE / Streamable HTTP / WebSocket | 与 MCP server 通信的通道 |
| **Server features**（client 消费）| tools / resources / prompts（+ `*_list_changed` 通知）| 工具调用、资源读取、prompt 取用 |
| **Client features**（server→client 回调）| **sampling** / **elicitation** / **roots** / logging | server 反向借 client 的 LLM / 请求用户输入 / 拿 workspace 根 / 日志 |
| **鉴权 & 形态** | OAuth 2.x / 自身作 MCP server | 远程 server 鉴权 / 把自己暴露成 MCP 工具 |

> Client features 是"完整性"最容易缺的一档——很多 Agent 只做 client→server 的工具调用，不实现 server→client 的 sampling/elicitation/roots。

---

## 二、完整性矩阵

| 能力 | **Claude Code** | **Codex** | **Qwen Code** | **OpenCode** | **Qoder CLI** |
|------|:--:|:--:|:--:|:--:|:--:|
| 传输 stdio | ✓ | ✓ | ✓ | ✓ | ✓ |
| 传输 SSE（legacy）| ✓ | ✓ | ✓ | ✓ | 🟡¹ |
| 传输 Streamable HTTP | ✓ | ✓ | ✓ | ✓ | 🟡¹ |
| 传输 **WebSocket** | ✓ | ✗ | ✗ | ✗ | ✗ |
| Tools（list/call/list_changed）| ✓ | ✓ | ✓ | ✓ | ✓ |
| Resources（list/read）| ✓ | ✓ | ✓ | ✓ | 🟡¹ |
| Prompts（list/get → slash）| ✓ | ✓ | ✓ | ✓ | 🟡¹ |
| **Sampling**（server→client LLM）| **✓** | ✗ | ✗ | ✗² | ✗ |
| **Elicitation**（server 请求用户输入）| ✓ | ✓³ | ✓⁴ | ✗² | ? |
| **Roots**（暴露 workspace 给 server）| ✓ | ✓ | ✓ | ✓ | ? |
| Logging / 通知消费 | ✓ | ✓ | ✓ | 🟡 | ? |
| **OAuth 2.x** 远程鉴权 | ✓✓⁵ | ✓ | ✓⁶ | ✓ | ✓⁷ |
| **自身作 MCP server** | ✓ `claude mcp serve` | **✓✓** `mcp-server`+`app-server` | ✓ `qwen mcp serve` | **✗ 仅客户端** | **✗ 仅客户端** |
| 独家能力 | sampling · WebSocket · **channels** 推送 | **双 server 形态** | `claudeMcpImport` + 运行时启停 | Effect-TS + HTTP API 远程管理 MCP | gemini 血统 + `McpAuthTool` |

**脚注**：
1. Qoder 闭源，传输/resources/prompts 按其 **gemini-cli 血统**推断，未逐一二进制核验。
2. **OpenCode 显式禁用** sampling + elicitation——`packages/opencode/src/mcp/index.ts:43,45` 把 `// sampling: {}` / `// elicitation: {}` **注释掉**，client capabilities 仅声明 `roots: {}`（line 47）。
3. Codex 有 `mcp_elicitations_auto_deny` 开关（`codex-rs/core/src/codex_thread.rs:331`）。
4. Qwen elicitation 经 hook 路由（`packages/core/src/hooks/types.ts`），非 mcp-client 内联实现。
5. Claude OAuth 最全：DCR（RFC 6749）+ RFC 9728 自动发现 + 预配置 `--client-id/secret` + `oauth.scopes` + `headersHelper` 动态头。
6. Qwen 有 token 存储多模式（`oauth-token-storage` / `file-token-storage` / `sa-impersonation-provider`）。
7. Qoder `McpAuthTool` + `qoder mcp auth`，细节闭源不可考。

---

## 三、关键差异（逐项）

### 1. Sampling 是完整性分水岭 —— 只有 Claude Code

`sampling/createMessage` 让 MCP server **反向借用 client 的 LLM** 做补全（server 内部需一次 LLM 调用，不必自带 API key）。

- **Claude Code**：✓ 支持，server 请求需用户批准（human-in-the-loop）。
- **Codex / Qwen / OpenCode**：源码确认**无** sampling（Codex `codex-rs` grep 0；Qwen `packages/` grep `sampling/createMessage` 0；**OpenCode 在 `mcp/index.ts` 把 sampling capability 注释掉了**）。
- **Qoder**：闭源不可考，其 gemini-cli 血统亦无。

> 五家里唯一的"硬"能力缺口——四家都不做 sampling，Claude Code 独有。

### 2. 自身作 MCP server —— OpenCode 与 Qoder 是"纯客户端"

| Agent | 形态 | 命令/证据 |
|---|---|---|
| Codex | **双 server**：标准 `mcp-server`（MCP 2 tools）+ `app-server`（MCP-like 私有协议，多 transport）| `codex-rs/mcp-server` + `codex-rs/app-server*`（详 [Codex MCP Server Deep-Dive](./codex-mcp-server-deep-dive.md)）|
| Claude Code | `claude mcp serve` 暴露 Read/Edit/LS/Bash 给其他 MCP 客户端 | 官方文档 |
| Qwen Code | `qwen mcp serve` + `sdkMcpController` | `packages/cli/src/nonInteractive/control/controllers/sdkMcpController.ts` |
| **OpenCode** | **✗ 仅客户端**（`Client({name:"opencode"})`，无 self-as-MCP-server；HTTP API 是管理 client 侧 MCP server 配置）| `packages/opencode/src/mcp/index.ts:88` |
| **Qoder CLI** | **✗ 无 serve** | EVIDENCE：`qoder mcp` 仅 add/add-json/get/list/remove/auth |

> 注：OpenCode/Qoder 都有自己的服务端架构（OpenCode 的 `opencode serve` HTTP API、Qoder 的云远程），但都**不是 MCP server 形态**——不能被别的 MCP 客户端当工具调用。

### 3. WebSocket 传输 —— 仅 Claude Code

Claude Code 支持 stdio/SSE/Streamable-HTTP/**WebSocket** 四传输；Codex/Qwen/OpenCode/Qoder 均为 stdio/SSE/HTTP 三传输（无 WS）。

### 4. Elicitation —— Claude/Codex/Qwen 有，OpenCode 显式禁用

- **有**：Claude（经 hook 自动应答）、Codex（带 `mcp_elicitations_auto_deny` 开关）、Qwen（经 hook）。
- **无**：OpenCode——`mcp/index.ts` 把 elicitation capability **注释禁用**，仅保留 `roots`；这是 OpenCode client-features 比 Codex/Qwen 少一档的关键。
- Qoder 闭源不可考。

### 5. Channels 推送 —— Claude 独有的 MCP 扩展

Claude Code 的 `claude/channel` 让 MCP server **主动推消息进 session**（`--channels`）。其余四家无此 MCP 扩展。

---

## 四、逐家小结

**Claude Code（最完整）**：四传输（含 WebSocket）+ 全 client features（**唯一 sampling** + elicitation + roots + logging）+ 最全 OAuth（DCR/RFC9728/scopes/headersHelper）+ `claude mcp serve` + **channels** 推送 + MCP tool-search（按需加载省 token）+ `MAX_MCP_OUTPUT_TOKENS` 输出限额。少数 spec 可选项（resource templates / `resources/subscribe` / completion / cancellation）官方文档未明，标"不确定"。

**Codex（很完整，差 sampling/WS）**：stdio/SSE/HTTP + tools/resources/prompts（`get_prompt`/`list_prompts`/`resources/read`）+ roots + elicitation（带 auto-deny）+ OAuth；**双 MCP server 形态**（`mcp-server` + `app-server`）是其独家强项——5 家里把"自己当工具给别的 LLM 调"做得最彻底。缺 sampling、WebSocket。

**Qwen Code（很完整，差 sampling/WS）**：stdio/SSE/HTTP + tools/resources/prompts + roots + elicitation（hook）+ list_changed 通知 + OAuth（token 存储多模式）+ `qwen mcp serve`；独家 `claudeMcpImport`（直接导入 Claude 的 MCP 配置）+ 运行时启停 MCP server。缺 sampling、WebSocket。

**OpenCode（开源可核验，但 client-features 最简）**：stdio/SSE/HTTP + tools/resources/prompts（`McpCatalog` 分页 `listTools/Prompts/Resources` cursor）+ roots（`ListRootsRequestSchema` 返回 workspace 目录，`mcp/index.ts:89`）+ OAuth（`oauth-provider`/`oauth-callback`）+ HTTP API 远程管理 MCP（Effect-TS）。**短板**：`mcp/index.ts:43,45` **显式注释禁用** sampling + elicitation（client capabilities 仅 `roots`）；**无 server 形态**（`Client({name:"opencode"})` 纯客户端）。开源、能力清晰可核验，但 client-features 比 Codex/Qwen 少 elicitation 一档。

**Qoder CLI（最弱/最不可考）**：gemini-cli 血统的 MCP 客户端——`qoder mcp` add/get/list/remove/auth + `McpAuthTool`（OAuth）+ `DiscoveredMCPTool` + `mcp-config` bundled skill + `--strict-mcp-config`/`--experimental-mcp-load` flag。**关键短板：仅客户端、无 `serve`**。sampling/elicitation/roots 因闭源不可核验，按 gemini 血统大概率无 sampling。

---

## 五、证据等级与不确定项

| Agent | 证据 | 强度 |
|---|---|---|
| Qwen Code | 本地 TS 源码 `packages/core/src/{tools/mcp-client,mcp/*}` + `cli/.../sdkMcpController` | **强** |
| Codex | 本地 Rust 源码 `codex-rs/{mcp-types,rmcp-client,mcp-server,app-server*,core}` | **强** |
| OpenCode | 本地 TS 源码 `packages/opencode/src/mcp/{index,catalog,oauth-*}` | **强** |
| Claude Code | 官方文档 [code.claude.com/docs/en/mcp](https://code.claude.com/docs/en/mcp)（部分 spec 可选项为文档推断）| 中-强 |
| Qoder CLI | 反编译二进制 EVIDENCE（client-only 已钉死；细粒度能力按 gemini 血统推断）| 弱-中 |

**不确定项**：① Claude resource templates / `resources/subscribe` / completion / cancellation 官方未明；② Qoder elicitation/roots/sampling 闭源不可考；③ 各家 `*_list_changed` 通知消费完整度未逐一压测；④ OpenCode logging 消费未确认（标 🟡）。

---

## 六、与现有文档的关系 + 对 Qwen 启示

- 项目既有 [MCP 集成对比](./mcp-integration-deep-dive.md) 是**传输/命名/策略/OAuth** 矩阵（含 8 家，但无 Codex/Qoder、无 client-features 完整性）；本文是其**能力完整性**正交补充，聚焦用户点名的 5 家。
- **对 Qwen Code 的启示**：
  1. **Sampling 是唯一真缺口**——若要对齐 Claude，可加 `sampling/createMessage` client handler（让 MCP server 反向借 Qwen 的 LLM，带审批）。投入小，补齐"全 client features"，且能反超 Codex/OpenCode（它们都无 sampling）。
  2. **WebSocket 传输**可选补（Claude 独有，但 stdio/HTTP 已覆盖绝大多数场景，优先级低）。
  3. Qwen 的 `qwen mcp serve` + `claudeMcpImport` + 运行时启停 + elicitation 已是强项，**server 形态 + client-features 完整度**领先 OpenCode/Qoder、与 Claude/Codex 同档——只差 sampling 一项即可登顶。

---

## 证据来源

| 来源 | 类型 | 获取 |
|------|------|------|
| `/root/git/qwen-code` `origin/main` | TS 源码（mcp-client / mcp / sdkMcpController 钉死）| 本地 grep |
| `/root/git/codex` @ `6f5dd7b` | Rust 源码（mcp-types/rmcp-client/mcp-server/app-server/core）| 本地 grep |
| `/root/git/opencode` @ `355a0bcf5` | TS 源码（mcp/index·catalog·oauth-provider 钉死）| 本地 grep |
| [code.claude.com/docs/en/mcp](https://code.claude.com/docs/en/mcp) | 官方文档（传输/sampling/elicitation/roots/OAuth/serve/channels）| WebFetch |
| [modelcontextprotocol.io spec v2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18) | MCP 规范（能力面基线）| WebFetch |
| [Qoder CLI EVIDENCE.md](../tools/qoder-cli/EVIDENCE.md) | 反编译二进制（client-only 钉死）| 本仓库二进制分析 |

> **免责声明**：MCP 规范与各家实现演进快，本文截至 2026-06-22；Qwen/Codex/OpenCode 以本地源码、Claude 以官方文档、Qoder 以二进制 EVIDENCE 为准，闭源项标注不确定。
