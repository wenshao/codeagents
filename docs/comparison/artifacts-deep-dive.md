# Artifacts 会话产物发布 Deep-Dive

> AI 编程代理能否把一次会话的产出，从终端文本变成一个**可分享、可交互、随会话原地更新的网页**？本文介绍 Claude Code 于 2026-06 推出的 **Artifacts**（会话产物发布）功能，并与各家 Agent 的"会话产物可视化"路径对比。Qwen Code 目前无完全对标功能（最接近的是本地 `/export HTML`）。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md) · [Deep-Dive 索引](./deep-dive-index.md)

> **证据基础**：本功能为 2026-06 新增（beta），**晚于**本仓库反编译的 `claude-code-leaked`（v2.1.x）二进制——该二进制内 grep 不到任何 `*ARTIFACT*` 发布符号（仅有一个早期相关 feature flag `REVIEW_ARTIFACT`，见 [§九](#九源码验证说明)）。因此本文技术声明以**官方文档**为准：[code.claude.com/docs/en/artifacts](https://code.claude.com/docs/en/artifacts.md)（已全文核验）+ 发布博客 [claude.com/blog/artifacts-in-claude-code](https://claude.com/blog/artifacts-in-claude-code)。功能仍在 beta，后续可能变更。

---

## 一、是什么

Artifact 是 Claude Code 从当前会话**发布到 claude.ai 上一个私有 URL**（`https://claude.ai/code/artifact/<uuid>`）的一个**自包含、可交互网页**：在浏览器打开后，随会话继续**原地更新**，并可在组织内分享。

定位是"**把不适合用终端文本表达的产出，换成更适合看 / 交互的页面**"——例如带注解的 PR diff 走查、从会话数据生成的 dashboard、多个实现方案并排对比、长任务的进度时间线。

### 与 claude.ai 网页版 Artifacts 的区别（关键澄清）

二者**不是同一个东西**，容易混淆：

| 维度 | claude.ai 网页 Artifacts | **Claude Code Artifacts** |
|------|------------------------|--------------------------|
| 位置 | 聊天界面内联侧边栏渲染 | 终端 / 桌面 app 发布到独立私有 URL |
| 内容 | 聊天里的独立 code/HTML/React/SVG/markdown | 一个自包含 HTML 页面（claude.ai 托管）|
| 分享 | 局限于该聊天上下文 | 组织内分享 + 作者署名 + gallery |
| 持久 | 会话级 | 跨会话持久 + 每次 republish 一个 version |

> Claude Code CLI 里**没有**网页版那种内联 Artifacts；它是终端原生、发布到独立 viewer 的另一套机制。

### 它不是什么

> 官方原文："An artifact is a capture of work, not an application."

Artifact 是**产物的快照，不是应用**——单个自包含页面、无后端，不能存表单输入、不能在浏览时调 API、不能多路由。需要带后端的内部工具，应自行部署。

---

## 二、创建 / 更新 / 分享流程

### 创建

两种触发，**均无 slash 命令**：

1. **自动**：Claude 判断输出"更适合页面"时自主发布
2. **显式自然语言请求**：

```text
Make an artifact that walks through this PR with the diff annotated inline.
```

```text
Build a dashboard artifact of last week's deploy failures by service and keep it updated as you investigate.
```

流程：Claude 先把页面写成项目目录里的 **`.html` / `.htm` / `.md`** 文件 → 首次发布前弹权限确认（`Claude wants to publish "…" (deploy-failures.html) to a private page on claude.ai`）→ 选 Yes → 打印 URL + 自动开浏览器。标题与 tab emoji 由 Claude 选定。

| 操作 | 方式 |
|------|------|
| 重开最近 artifact | `Ctrl+]` |
| 禁止自动开浏览器 | 环境变量 `CLAUDE_CODE_ARTIFACT_AUTO_OPEN=0` |
| 跨会话更新某 artifact | 把其 URL 给 Claude（无 URL 则新会话总是新建，不更新）|

### 更新

让 Claude 改页面、或长任务自行 republish；Claude 编辑底层文件并**发布到同一 URL**，已打开页面者原地看到更新。每次发布成一个 version，可在页头 **Share** 控件选给查看者展示哪个 version。

### 分享

新 artifact 仅作者可见 → 页头 **Share** 授权给组织内指定人 / 全体。**分享止于组织边界**：查看者必须以同组织成员身份登录 claude.ai，无组织外可见选项；要给外部人，让 Claude 给出 HTML 文件直接发文件。Artifact **只读不可协同编辑**（作者是唯一 writer）。gallery 在 [claude.ai/code/artifacts](https://claude.ai/code/artifacts)。

---

## 三、能做什么（prompting patterns）

单个 HTML 页面，凡 HTML+CSS+内联 JS 能表达皆可。官方列出 5 类高频模式：

| 模式 | 用途 |
|------|------|
| **走查变更** | 渲染 diff / 设计改动 + 行边注解，审查者读"为什么"而非自行重建 |
| **方案对比** | 一页并排多变体（布局 / 文案 / API 形状 / 实现计划）逐一权衡 |
| **可交互调参** | slider / toggle / 输入框绑定到所调对象，直接试值（如动画 easing 实时预览）|
| **结果带回会话** | 页内 "Copy as prompt" 导出按钮 → 把页面交互结果粘回终端（如 triage 看板拖卡后导出最终排序）|
| **进度追踪** | 长任务跑时持续刷新 checklist artifact，有链接者无需读终端即可跟进 |

---

## 四、技术约束（强 CSP 沙箱）

每个 artifact 是单个自包含页面，被 Claude Code 包进 HTML 文档外壳，并施加严格 Content Security Policy：

| 约束 | 效果 |
|------|------|
| **无外部请求** | CSP 封死跨 host 的 script/css/font/img + `fetch`/XHR/WebSocket → CSS/JS 内联、图片转 data URI |
| **无后端** | 纯静态页：不存表单、不在浏览时认证查看者、不调 API |
| **单页** | 相对链接不解析；多段内容用页内锚点而非分文件 |
| **文件类型** | 发布文件须 `.html` / `.htm` / `.md`（md 渲染成带样式 HTML）|
| **渲染体积** | 渲染页 ≤ **16 MiB**（超限多因内嵌大图）|

> **token 成本**：生成 artifact 像普通响应一样耗 output token，带样式页比同内容的终端文本更贵（内联 CSS、交互 JS、尤其 data-URI 图片是主因）。官方建议：图表优先 SVG / HTML-CSS 而非位图、省去不必要的交互、大数据集让页面汇总而非全量内联。

---

## 五、设计系统集成

Claude 构建 artifact 时套用内置 **design skill**（自动给出 palette / typography / layout）；该 skill 会**先在项目里找已有设计系统**再用自己的。要让 artifact 贴合产品品牌，把 design tokens 记在 Claude 能找到的地方（如 [CLAUDE.md](../tools/claude-code/13-system-prompt.md) 或仓库 theme 文件）：

```markdown
## Design system
- Colors: primary #1a4d8f, accent #f59e0b, surface #f8fafc
- Typography: Inter for body, JetBrains Mono for code
- Spacing: 8px scale, 6px border radius
```

优先级：**用户 prompt > 用户设计系统 > Claude 默认**。

---

## 六、可用性与门控

> 任一条件不满足时，Claude 改为写一个本地 HTML 文件、或直接说无法发布。

| 要求 | 满足条件 |
|------|---------|
| **Plan** | Team / Enterprise（Team 默认开；Enterprise 需 admin 在 claude.ai 后台开）|
| **认证** | 已用 `/login` 登录 claude.ai。**API key / gateway token / 云厂商凭据不可发布** |
| **Provider** | Anthropic API。**Bedrock / Vertex AI / Microsoft Foundry 不支持** |
| **组织策略** | 未启用 CMEK / HIPAA / Zero Data Retention |
| **Surface** | Claude Code CLI，或 Claude 桌面 app ≥ `1.13576.0`。**Agent SDK / GitHub Action / MCP-server 上下文默认关**；`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` 也关 |

### 自行关闭（不论组织设置）

| 方式 | 设置 |
|------|------|
| settings 文件 | `"disableArtifact": true` |
| 环境变量 | `CLAUDE_CODE_DISABLE_ARTIFACT=1` |
| 权限规则 | `permissions.deny` 加 `Artifact` |

> **Agent SDK 无编程 API**：TS/Python SDK 的消息类型与工具集里**均无** artifact 相关项——artifact 是 Claude 在 CLI 上下文里的自主行为，SDK 无法触发或控制。

---

## 七、企业管理

artifact 内容存于 Anthropic 托管基础设施，仅发布组织的已认证成员可见。admin（Team/Enterprise）在 [claude.ai 后台](https://claude.ai/admin-settings/claude-code)管控：

- **开关**：Settings > Claude Code > Capabilities 的 **Artifacts** toggle；Enterprise 可按 RBAC role 限定（Settings > Roles）
- **保留策略**：Settings > Data & privacy controls，对"私有未分享"与"已分享"分设 TTL 自动删除
- **审计日志**：发布 / 分享 / 删除均记 `claude_artifact_*` 事件（与 claude.ai 对话内 artifact 同族）
- **域名白名单**：viewer 从沙箱化 `*.claudeusercontent.com` 源加载，受限出网组织需加白
- **Compliance API**（组织级清单 / 取回 / 删除）：

| Method | Endpoint |
|--------|----------|
| `GET` | `/v1/compliance/code/artifacts` |
| `GET` | `/v1/compliance/code/artifacts/{artifact_id}/versions/{version_id}` |
| `DELETE` | `/v1/compliance/code/artifacts/{artifact_id}` |

---

## 八、横向对比：各 Agent 的"会话产物可视化"

> "把会话产出变成可视 / 可分享产物"这一能力，各家路径差异大。下表区分**本地产物**（生成文件 / 本地预览）与**托管发布**（上传到云端可分享 URL）。

| Agent | 会话产物可视化 | 托管发布 + 分享 | 版本/组织治理 | 备注 |
|-------|-------------|---------------|-------------|------|
| **Claude Code** | ✅ Artifacts（自包含交互页）| ✅ claude.ai 私有 URL + 组织分享 | ✅ version + RBAC + 审计 + 保留策略 + Compliance API | 本文主题；Team/Enterprise beta |
| **Qwen Code** | 🟡 `/export HTML`（本地 HTML 导出，`exportCommand.ts`，含 light theme，[PR#3908](https://github.com/QwenLM/qwen-code/pull/3908)）+ `qwen serve` web-shell（`packages/web-shell`，本地托管 web UI）| ✗ 无云端发布/分享 URL | ✗ | 最接近的对标是**本地导出**，非托管发布 |
| **Gemini CLI** | 🟡 会话可导出 | ✗ | ✗ | 无托管 artifact 发布 |
| **Codex CLI** | 🟡 thread 导出 | ✗ | ✗ | 无托管 artifact 发布 |
| **Copilot CLI** | 🟡 infinite sessions / checkpoint | ✗ | ✗ | 无托管 artifact 发布 |

**结论**：把会话产出**自动判定→生成自包含交互页→发布到托管私有 URL→组织内版本化分享→admin 治理**这条完整链路，目前为 Claude Code **独有**。其余 Agent 多止步于"本地导出 / 本地预览"。

---

## 九、源码验证说明

> 本仓库强调闭源功能须有 EVIDENCE（二进制分析）或官方文档 URL 支撑。Artifacts 因发布时间（2026-06）晚于反编译二进制，故无二进制证据，仅以官方文档钉死。

- **`claude-code-leaked`（v2.1.x）无发布符号**：grep `CLAUDE_CODE_DISABLE_ARTIFACT` / `CLAUDE_CODE_ARTIFACT_AUTO_OPEN` / `disableArtifact` / `publishArtifact` / `claude.ai/code/artifact` / `claudeusercontent` / `claude_artifact_` 均无命中。
- **唯一相关痕迹**：feature-flag 清单（[`15-telemetry-feature-flags.md`](../tools/claude-code/15-telemetry-feature-flags.md)）含 `REVIEW_ARTIFACT` gate——疑似早期/相关门控（artifacts 的典型场景之一即 PR review 走查），但非完整发布功能，不应据此声称该二进制已具备本功能。
- **qwen-code 无对标**：grep `claudeusercontent` / `/code/artifact` / `publishArtifact` 均无；最接近的是 `/export` 本地 HTML 导出 + web-shell。

---

## 十、对 Qwen Code 的启示

Artifacts 的"托管发布"部分**强绑定 Anthropic 自有基础设施（claude.ai）**，第三方 fork 无法直接复制。但**本地 artifact 概念可借鉴**：

1. **自包含交互页生成**：让模型在合适场景（PR 走查 / dashboard / 方案对比）直接产出**带 CSP 约束的单文件交互 HTML**，而非纯文本——qwen 已有 `/export HTML` + design 能力底座，可扩展为"按场景生成 artifact 风格页"。
2. **复用已有 web-shell 托管**：qwen 的 `qwen serve` / `packages/web-shell` 已能本地托管 web UI，可作为"本地 viewer"承载 artifact 风格页面（原地刷新 + 局域网分享），形成"无云依赖"的等价体验——契合本项目 [本地 TUI 优先](./qwen-code-improvement-report.md) 的取向。
3. **治理面**：若未来做托管分享，需配套 version / 组织可见性 / 保留策略 / 审计——Claude 的 Compliance API + RBAC 模型可作设计参照。

---

## 证据来源

| 来源 | 类型 | 获取方式 |
|------|------|---------|
| [code.claude.com/docs/en/artifacts](https://code.claude.com/docs/en/artifacts.md) | 官方文档（功能/约束/设置/可用性/企业管理全量）| WebFetch 全文核验 |
| [claude.com/blog/artifacts-in-claude-code](https://claude.com/blog/artifacts-in-claude-code) | 发布博客（发布时间 / 路线图）| 官方博客 |
| [docs.claude.com/en/api/compliance](https://docs.claude.com/en/api/compliance) | Compliance API 参考 | 官方文档 |
| `claude-code-leaked`（v2.1.x）| 反编译二进制（**无**发布符号，证伪用）| 本地 grep |
| `qwen-code` `exportCommand.ts` / `packages/web-shell` | 开源源码（对标分析）| 本地源码 |

> **免责声明**：Artifacts 处于 beta（2026-06 推出，Team/Enterprise）。以上基于官方文档与本仓库源码比对，后续版本可能变更；exact 发布日期以官方博客为准。
