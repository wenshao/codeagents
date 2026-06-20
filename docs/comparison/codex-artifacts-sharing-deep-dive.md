# Codex 会话产物、分享与发布 Deep-Dive（对标 Claude artifacts）

> 承接 [Claude Code Artifacts Deep-Dive](./artifacts-deep-dive.md)：OpenAI **Codex**（`codex` CLI + Codex Cloud/Web）有没有"把会话产出变成可分享 / 可发布产物"的对应功能？本文以本地 Rust 源码（`/root/git/codex`，2026-06-19 `64bdeed9f7`）+ 官方文档 + 反编译二进制 feature-flag 转储三方核验。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md) · [Deep-Dive 索引](./deep-dive-index.md)

> **一句话结论**：Codex **没有** Claude artifacts 的直接对标（没有"一键把会话产出快照成托管可分享网页"的命令）。相关能力分散在几条彼此独立的路径上——一个**休眠占位**的 `artifact` feature flag（原 PPTX 工具已移除）、本地 markdown 复制、**仅云端可分享**的会话、以及 **Codex Sites**（部署 web app 到 workspace URL）。终端 CLI 会话**完全不能**按 URL 分享。

---

## 一、`artifact` feature flag：休眠的占位符（核心发现）

Codex 的 feature 注册表里**确有**一个 `artifact` flag，但它是**休眠态**——定义在册、无实现、且被显式排除在配置 schema 之外。

```rust
// 源码: codex-rs/features/src/lib.rs:1257-1262（2026-06-19）
FeatureSpec {
    id: Feature::Artifact,
    key: "artifact",
    stage: Stage::UnderDevelopment,   // 开发中
    default_enabled: false,            // 默认关闭
},
```

```rust
// 源码: codex-rs/config/src/schema.rs:25-27 —— 生成配置 schema 时跳过 artifact
for feature in FEATURES {
    if feature.id == codex_features::Feature::Artifact {
        continue;   // ← 不暴露为可配置 TOML 项
    }
    ...
}
```

doc 注释为 `/// Enable native artifact tools.`（`features.rs:225`），但**当前源码里找不到任何 artifact 工具 handler / 模板**（`core/templates/tools/` 无 artifact 模板；`core/src/tools/handlers/` 无 `artifacts.rs`；core 内 grep `pptx|presentation_artifact|PptxGen` 0 命中）。即：**enum 占位还在，工具实现已空**。

### 时间线（三方交叉）

| 时间 | 状态 | 证据 |
|------|------|------|
| ≤2026-03-25（v0.116.0 二进制）| `artifact` flag = `under development / false` | 本仓库 [codex-cli EVIDENCE.md](../tools/codex-cli/EVIDENCE.md) feature-flag 转储 |
| 2026-03-26 | 原 artifact **工具**被移除 | web 研究指向 `PR #15851 "drop artifact tool and feature"`（commit `bb95cc5`）；本地核实当前 core 无 pptx 残留 ✓ |
| 2026-06-19（当前源码）| flag 占位保留：`UnderDevelopment / false / schema 排除 / 无 handler` | `codex-rs/features/src/lib.rs:1258` ✓ |

> **本地源码修正 web 视图**：单看 GitHub 历史会以为 "artifact 已被删干净"。但本地 HEAD 核实——**Feature 枚举条目仍在**（随 `codex-features` crate 拆分 [PR #15253] 保留），只是无实现、schema 排除。准确表述是"**工具已移除、flag 占位休眠**"，而非"完全删除"。

### 原 artifact 工具是什么（已移除）

据 web 研究，它**不是** Claude 那种"发布网页"，而是**线程内创建/编辑 PowerPoint（.pptx）的 stateful model-tool**——动作为 `create / import_pptx / export_pptx / add_slide / add_chart / set_theme` 等，`artifact_id` 在线程内持久。即概念上对标 Claude 的 **PPTX/文档类 artifact**，与"可分享网页 artifact"无关。

---

## 二、幻灯片 / PPTX 生成的现状

工具移除后，幻灯片生成在官方文档里以 **use-case** 形式存在（`PptxGenJS` JS 库 + `imagegen` skill 渲染每页 PNG 做 QA）：
- https://developers.openai.com/codex/use-cases/generate-slide-decks

> **本地源码精度**：当前 bundled sample skills 仅 `imagegen / openai-docs / plugin-creator / skill-creator / skill-installer`（`codex-rs/skills/src/assets/samples/`）——**无**专门的 "slides" bundled skill。所以 PPTX 生成是**文档化的使用模式**（靠库 + 技能），不是开箱即用的 shipped 功能。输出为本地 `.pptx` 文件，**非可分享 URL**。

---

## 三、会话分享：CLI 本地、仅云端可分享

| 表面 | 会话能否按 URL 分享 | 机制 |
|------|------------------|------|
| **Codex CLI（终端）** | ❌ 不能 | 会话存为**本地 JSONL rollout**（`$CODEX_HOME/sessions/YYYY/MM/DD/rollout-*.jsonl`）；`codex resume` / `fork` / `archive` 仅复用本地 |
| **Codex Cloud / Web**（chatgpt.com/codex）| ✅ 可以 | 云端任务有服务端状态，可按链接分享（唯一分享表面）|

OpenAI maintainer 在 [discussion #13251](https://github.com/openai/codex/discussions/13251) 明确：

> "Local conversations are stored locally to the machine where you run the CLI, extension or app. They are not stored in the cloud."

即**分享只在 Codex Web/Cloud 存在，CLI 与编辑器扩展不支持**；把 CLI transcript 上传云端共享仍是未实现的 open feature request。

> **不确定项**：官方可达文档未给出云端任务分享 URL 的确切格式（Help Center 11369540 对自动抓取返回 403）；但"云端可分享 / CLI 不可分享"的事实由 maintainer 陈述确证。

---

## 四、Codex Sites：最接近的"可分享可视产物"（但是部署，不是快照）

[Codex Sites](https://developers.openai.com/codex/sites) 让 Codex "create, save, deploy, and inspect websites, web apps, and games hosted by OpenAI"——**部署一个运行中的 web app 到 workspace 范围的 production URL**：

- **触发**：主要在 **Codex app**（线程内 `@Sites` 插件 / Sites 侧栏），**非 CLI 命令**
- **流程**：save a version（绑定源 git commit）→ deploy a version → 部署成功后"reports the production URL"
- **可分享 URL**：有——每个 Sites 部署 URL 都是 production 部署
- **受众门控**（非公开默认）：分享前须设 audience —— `admins_only` / `workspace_all` / `custom`

> **与 Claude artifacts 的本质区别**：Codex Sites 发布的是**部署的 app/网站到 workspace URL**（一条部署管道）；Claude artifacts 是把会话刚产出的自包含 HTML/报告**即时快照**成可分享页。Codex **没有**"把刚写的报告/可视化一键快照成可分享 artifact 页"的能力。

---

## 五、Cloud task 的产物 = PR / diff

云端任务完成后，结果以"**回答 + diff + Pull Request**"呈现（https://developers.openai.com/codex/cloud/environments）：

> "When the agent finishes, it shows its answer and a diff of any files it changed. You can open a PR or ask follow-up questions."

配套：GitHub 上 `@codex` 触发任务并直接提 PR；IDE→云端 handoff；`codex apply`（把最近一次 cloud task 的 diff 应用到本地）；`codex cloud`（交互式选取云任务）。**云任务的"可分享产物"实质是 PR / branch / diff**，不是发布的文档页。

---

## 六、Slash 命令与本地导出

```text
# 源码: codex-rs/tui/src/slash_command.rs（2026-06-19）
/copy   →  "copy last response as markdown"                         （:98）
/raw    →  "toggle raw scrollback mode for copy-friendly ... selection"（:99）
/diff   →  "show git diff (including untracked files)"               （:100）
```

- **有**：`/copy`（把上条回答复制为 markdown）、`/diff`、`/raw`——轻量、本地、剪贴板级
- **无**：`/share`、`/export`、`/artifact`、`/publish`、`/transcript`（本地源码 grep 均无；官方 [slash-commands 清单](https://developers.openai.com/codex/cli/slash-commands) 亦无）
- HTML/markdown transcript 导出为**社区工具**（如 `codex-transcript-viewer` 渲染 rollout JSONL），非官方功能

---

## 七、对比表：Codex vs Claude Code artifacts

| 能力（以 Claude artifacts 为镜）| Codex CLI | Codex Cloud/Web | Claude Code |
|------|------|------|------|
| 名为 "artifact" 的功能 | flag **休眠占位**（原 PPTX 工具已移除）| — | ✅ Artifacts（发布网页）|
| 会话产出→**自包含交互页** | ❌ | ❌ | ✅ 一键快照 + CSP 沙箱 |
| **托管私有 URL + 组织分享** | ❌ | 🟡 仅会话/任务可分享链接 | ✅ claude.ai/code/artifact + version + RBAC |
| 部署 web app 到 URL | ❌ | ✅ **Codex Sites**（workspace 门控；部署非快照）| ✗（artifacts 是静态页非部署）|
| PPTX / 幻灯片 | 🟡 文档化 use-case（PptxGenJS，非 bundled skill）| 同 | ✅ 文档类 artifact |
| `/share` 命令 | ❌ | — | ✗（artifacts 无 slash，自动/自然语言）|
| 导出 transcript（HTML/MD）| 🟡 `/copy` markdown；本地 JSONL rollout | — | — |
| 一次运行的"产物" | git diff（`codex apply`）| **PR** + diff + 回答 | 发布的 artifact 页 |
| 报告 / dashboard 生成器 | ❌ | ❌ | ✅（artifact 典型场景）|

**结论**：Codex 把"产物"绑在 **PR/diff（云）** 与 **Sites 部署（云/app）** 两条工程化路径上；Claude artifacts 则是**会话内一键快照成可分享页**。二者哲学不同——Codex 偏"把改动落成可合并的 PR / 可部署的 app"，Claude 偏"把会话表达力可视化并轻量分享"。Codex CLI **本地终端**这一层，对标 artifacts 的能力基本为空（仅 `/copy` markdown）。

---

## 八、源码验证说明

> 本项目要求闭源/半闭源声明须有 EVIDENCE（二进制/源码）或官方文档 URL 支撑。本文 Codex 部分以**本地 Rust 源码可直接钉死**，云端/Sites/分享以官方文档为准。

- **本地源码钉死**（`/root/git/codex` @ `64bdeed9f7` 2026-06-19）：`Feature::Artifact` 占位休眠（`features/src/lib.rs:1258`）+ schema 排除（`config/src/schema.rs:26`）+ 无 artifact tool handler/模板 + core 无 pptx 残留；`/copy /diff /raw` 存在、`/share /export /artifact` 不存在（`tui/src/slash_command.rs`）；bundled skills 无 slides。
- **二进制转储佐证**：[codex-cli EVIDENCE.md](../tools/codex-cli/EVIDENCE.md)（v0.116.0，2026-03-25）feature-flag 转储 `artifact  under development  false`。
- **官方文档**（云端/Sites/分享/PPTX use-case）：见正文各处 URL。
- **web 研究但本地不可直接复核**：PR #15851（artifact 工具移除，2026-03-26）——本地仅能核实"当前 core 无 pptx 残留"这一结果，PR# 本身以 web 研究为准。
- **本地源码修正 web 两处**：① `artifact` flag 非"已删除"而是"休眠占位"；② 无 bundled "slides" skill（仅文档化 use-case）。

---

## 九、启示

1. **"产物分享"的两种范式**：Claude = 会话产出**即时快照→轻量分享页**；Codex = 改动**落成 PR / 部署成 Sites**。前者重"看与分享"，后者重"合并与上线"。做 fork/对标时应明确取哪一侧——多数终端编码场景，Claude 的"零基础设施本地+轻分享"更贴近日常 review，Codex 的 Sites 更适合"把 demo 一键上线"。
2. **`artifact` flag 休眠的信号**：Codex 保留 `artifact` enum 占位但移除实现、schema 排除——可能为未来某种 artifact 能力预留槽位，但**当前不可用**，不应据 flag 存在而声称"Codex 有 artifact 功能"。
3. **对 Qwen Code**：Codex CLI 这层与 Qwen 同样"本地无托管分享"；若 Qwen 要补"会话产物可视化"，参照 [Claude artifacts 启示](./artifacts-deep-dive.md#十对-qwen-code-的启示)——复用 `qwen serve` web-shell 做本地 viewer，比走 Codex 的云部署路径更契合本地优先取向。

---

## 证据来源

| 来源 | 类型 | 获取方式 |
|------|------|---------|
| `/root/git/codex` @ `64bdeed9f7`（2026-06-19）| Rust 源码（flag/schema/slash/skills 直接钉死）| 本地 grep + Read |
| [codex-cli EVIDENCE.md](../tools/codex-cli/EVIDENCE.md) | v0.116.0 二进制 feature-flag 转储 | 本仓库二进制分析 |
| [developers.openai.com/codex/sites](https://developers.openai.com/codex/sites) | 官方文档（Sites 部署/受众）| WebFetch |
| [developers.openai.com/codex/cloud](https://developers.openai.com/codex/cloud) · [/environments](https://developers.openai.com/codex/cloud/environments) | 官方文档（云任务产物/PR）| WebFetch |
| [developers.openai.com/codex/cli/slash-commands](https://developers.openai.com/codex/cli/slash-commands) | 官方 slash 清单（无 /share /export）| WebFetch |
| [developers.openai.com/codex/use-cases/generate-slide-decks](https://developers.openai.com/codex/use-cases/generate-slide-decks) | 官方（PPTX use-case）| WebFetch |
| [github.com/openai/codex/discussions/13251](https://github.com/openai/codex/discussions/13251) | maintainer 陈述（CLI 不可分享）| WebFetch |
| `PR #15851`（artifact 工具移除）| web 研究（本地仅核实结果）| GitHub |

> **免责声明**：Codex 云端/Sites/分享功能演进快，本文官方文档部分截至 2026-06-20；`artifact` flag 现状以本地源码 `64bdeed9f7` 为准，后续版本可能变更。
