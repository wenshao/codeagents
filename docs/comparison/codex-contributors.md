# Codex CLI 贡献者页面

> **数据范围**：仓库全历史 → 2026-04-28
> **总计**：~5,890 commits / 444 unique 贡献者
> **Repo**: https://github.com/openai/codex

---

## 速查表

| 类别 | 人数 | commit 占比 | 特征 |
|---|:-:|:-:|---|
| 🏛️ **OpenAI 内部团队**（`@openai.com` / `-oai` suffix） | ~70+ | **~92%** | 项目治理几乎全部内部主导 |
| 🌍 **外部社区** | ~370+ | ~7% | 大量低 commit 量贡献者 |
| 🤖 **Bot** | 2 | ~1% | dependabot · github-actions |

> Codex 是**所有同类项目中外部贡献占比最低**的（除 Claude Code 完全闭源外）—— 典型的"开放源码 + 内部治理"模式。

---

## 一、OpenAI 内部主力维护者

> OpenAI 内部贡献者通过 `@openai.com` 邮箱或 `-oai` / `-openai` GitHub username 后缀识别。

### Top 10（all-time commits）

| 贡献者 | commits | 2026 commits | 焦点领域 |
|---|:-:|:-:|---|
| **Michael Bolin** | 865 | 360 | `codex-rs/core` (1762 files) + `app-server-protocol` (948) + `tui` (331) |
| **jif-oai** | 788 | **579** | `codex-rs/core` (1525) + `tui` (226) + `state` (220) — **2026 第一名** |
| **Ahmed Ibrahim** (`aibrahim@`) | 465 | 273 | `codex-rs/core` (985) + `tui` (312) + `app-server-protocol` (176) |
| **pakrym-oai** | 411 | 197 | core + ghost snapshots cleanup |
| **Eric Traut** | 322 | 256 | 🎨 **TUI 主力** — `tui` (2151) + `tui_app_server` (1459) |
| **Jeremy Rose** | 199 | 11 | non-interactive resume + 历史核心贡献 |
| **Dylan Hurd** | 150 | 113 | plugin / MCP fixture tests |
| **Owen Lin** | 121 | 74 | analytics + guardian review |
| **viyatb-oai** | 100 | — | — |
| **iceweasel-oai** | 98 | — | — |

### Niche 子领域 owner（推测）

| 领域 | 主要 owner | 信号 |
|---|---|---|
| **Core 语义引擎** | Michael Bolin / jif-oai / Ahmed Ibrahim | 三人 codex-rs/core commits 总和 ~4,272 |
| **TUI 渲染** | Eric Traut | tui + tui_app_server 共 3,610 commits（断崖领先）|
| **MCP / Plugin** | Dylan Hurd / Ahmed Ibrahim | MCP fixture tests + Split MCP modules |
| **App-Server / Protocol** | Michael Bolin | app-server-protocol 948 commits |
| **State 管理** | jif-oai | state 220 commits |
| **Analytics** | Owen Lin | guardian review event schema |

### 大量 OpenAI 内部贡献者列表

```
@openai.com 邮箱（部分）：
aaronl-openai · acrognale-oai · ae · Akshay Nathan · Alex Daley ·
alexsong-oai · Alex Zamoshchin · amjith · Andi Liu · Andrei Eternal ·
Andrew Ambrosino · Andrey Mishchenko · Anton Panasenko ·
arnavdugar-openai · baumann-oai · blevy-oai · Charley Cunningham ·
colby-oai · Eric Traut · Fouad Matin · Gabriel Peal · Owen Lin ·
pakrym-oai · viyatb-oai · sayan-oai · gt-oai · xl-openai ...
```

总计 70+ 个 `@openai.com` 邮箱用户，加上 `-oai` / `-openai` 后缀的另 30+ 用户。

---

## 二、外部社区贡献者

### 显著外部贡献者（无 `@openai.com` 邮箱）

由于 444 - 70+ = ~370 位非 OpenAI 邮箱贡献者，但**绝大多数是单 PR 长尾**。代表性的：

| 贡献者 | Email/Source | 贡献方向 |
|---|---|---|
| **Akshay Nathan** | gmail（个人）+ `@openai.com`（双账号）| 双重身份，从外部转内部 |
| **dependabot[bot]** | bot | ~126 自动 PR |
| **Felipe Coury** / **Devon Rifkin** | gmail | 单点功能 |
| **David Gilbertson** | gmail | docs/typo |
| **Helmut Januschka** | januschka.com | docs |
| **Ivan Murashko** / **Eugene Brevdo** / **Alex Kwiatkowski** | github noreply | 各种 fix |
| **Beehive Innovations** | guidedways | 单点 |

### 国际化 / 外部专项

Codex 的外部贡献几乎全是 **bug fix / typo / docs** 类长尾，**很少架构级 PR**。原因：

- OpenAI 内部决策权高度集中
- Rust 代码库门槛高，外部贡献者难深入
- 关键架构改动经常在内部 stack 中完成

---

## 三、项目治理结构

```
┌─ OpenAI Codex 团队 ──────────────────────────────────┐
│ Lead 工程师：Michael Bolin / jif-oai / Eric Traut    │
│ TUI 专精：Eric Traut（断崖领先）                     │
│ Core 语义：Michael Bolin + jif-oai + Ahmed Ibrahim  │
│ 70+ OpenAI 工程师参与（@openai.com）                 │
└────────────────┬─────────────────────────────────────┘
                 │
┌─ 外部社区（~370+ 贡献者，单 PR 长尾为主）────────────┐
│ • bug fix / typo / docs                              │
│ • dependabot 自动依赖更新                            │
│ • 极少架构级提议                                     │
└──────────────────────────────────────────────────────┘
```

### 治理特征

1. **完全内部主导** —— ~92% commits 来自 OpenAI 内部，比 Qwen Code (~89%) / OpenCode (~80%) / Gemini CLI (~70%) 都更内部主导
2. **Rust 门槛保护** —— 用 Rust 编写让外部贡献门槛比 TypeScript 项目高
3. **明确的 niche 专属** —— Eric Traut 几乎独家掌握 TUI / Michael Bolin 主导 protocol
4. **revert 决策严格** —— 大量内部 stack（`stack/...` 命名 PR）反映 OpenAI 内部 review 流程
5. **外部 PR 多为 fix/docs** —— 架构级提议极少 merge

---

## 四、与同类项目对比

| 项目 | 治理模式 | 总 commits | 总贡献者 | 内部占比 |
|---|---|:-:|:-:|:-:|
| **Claude Code** | Anthropic 完全闭源 | N/A | 0 公开 | 100% |
| **Codex** | **OpenAI 主导 + 高门槛 Rust** | 5,890 | 444 | **~92%** |
| **Qwen Code** | Alibaba 主导 + 中文社区 + 国际 i18n | ~2,400 (post-fork) | 60+ (recent) | ~89% |
| **OpenCode** | sst 创始人 Dax 主导 + 中等社区 | 11,875 | 924 | ~80%? |
| **Gemini CLI** | Google 主导 + Apache-2.0 + 大量外部 | ~3,000 | 多 | ~70% |

**Codex 的位置**：**最封闭的开源 AI Code Agent**（除 Claude Code 完全闭源外）。

---

## 五、相关数据采集

```bash
cd /root/git/codex

# 总数
git log --no-merges --pretty=format:"%H" | wc -l                           # → 5,890
git log --no-merges --pretty=format:"%an|%ae" | sort -u | wc -l            # → 444

# 内部识别
git log --no-merges --pretty=format:"%an %ae" | grep -iE "openai\.com|-oai$" | sort -u  # → 70+

# Top 贡献者
git log --no-merges --pretty=format:"%an" | sort | uniq -c | sort -rn | head -20

# 2026 活动
git log --since="2026-01-01" --no-merges --author="<NAME>" --pretty=format:"%cs %s" | head -10
```

---

## 相关文档

- [Codex CLI 对标改进报告（28 项）](./qwen-code-codex-improvements.md)
- [Qwen Code 贡献者页面](./qwen-code-contributors.md)
- [OpenCode 贡献者页面](./opencode-contributors.md)
- [Kimi-CLI 贡献者页面](./kimi-cli-contributors.md)

---

**最后更新**：2026-04-28
**数据窗口**：仓库全历史
