# OpenCode 贡献者页面

> **数据范围**：仓库全历史 → 2026-04-28
> **总计**：~11,875 commits / 924 unique 贡献者
> **Repo**: https://github.com/sst/opencode
> **维护者**: sst（Serverless Stack Toolkit）团队

---

## 速查表

| 类别 | 人数 | commit 占比 | 特征 |
|---|:-:|:-:|---|
| 🏛️ **sst 核心团队** | ~7 | **~75%** | 创始人 Dax 领衔 + 紧密团队 |
| 🤖 **Bot** | 4 | ~12% | GitHub Action · opencode-agent · CI |
| 🌍 **外部社区** | ~900+ | ~13% | 大型开源项目，长尾活跃 |

> OpenCode 是**所有同类项目中外部贡献者总数最多**的（924 人）—— sst 团队的"开放生态"风格。

---

## 一、sst 核心团队

### 项目领导层

| 贡献者 | commits | 别名 | 角色 |
|---|:-:|---|---|
| **Dax Raad** | **1,856** | `dax@anomalyco.com`（推测）| 🌟 **sst 联合创始人 + 项目 Lead** · 主导 `packages/opencode` (2,883) + `sdk` (582) + `tui` (404) |
| **Adam** | **1,280** | `adamdotdevin` / `adamdottv` / `adamelmore` | sst 团队 · UI/Web/App 主力（packages/ui 3,219 + web 2,624 + app 2,251）|
| **Aiden Cline** | 1,159 | `aidenpcline@gmail.com` + `rekram1-node` | sst 团队 · `packages/opencode` (1,537) 主力 |
| **Frank** | 676 | `frank@sst.dev` | sst 团队 · `packages/console` (2,110) + cloud lead |
| **David Hill** | 534 | `iamdavidhill@gmail.com` | sst 团队 · UI/App 设计（packages/app 416 + ui 385）|
| **Kit Langton** | 518 | — | sst 团队 · `packages/opencode` (3,126) 工程主力 |

### Niche 子领域 owner

| 领域 | 主要 owner | 文件路径 |
|---|---|---|
| **Core 引擎** | Dax Raad / Aiden Cline / Kit Langton | `packages/opencode` |
| **UI / Web / App** | Adam | `packages/ui` + `web` + `app` |
| **Console / Cloud** | Frank | `packages/console` + `cloud` |
| **App 设计** | David Hill | `packages/app` UI 设计 |
| **TUI** | Dax Raad | `packages/tui` |
| **SDK** | Dax Raad | `packages/sdk` |

### 其他显著 sst 贡献者

| 贡献者 | commits | 方向 |
|---|:-:|---|
| **Brendan Allan** | 216 | TanStack Query refactor + sync |
| **Luke Parker** | 131 | LSP + experimental tools |
| **Kujtim Hoxha** | 105 | 单系统 |
| **Shoubhit Dash** | 70 | session compaction |
| **James Long** | 54 | TUI editor context（PR#24034）|
| **Sebastian Herrlinger** / **Filip** / **Ariane Emory** | ~50 each | 各专项 |

---

## 二、外部社区贡献者

### 大型开源活跃社区

OpenCode 有 **924 unique authors**（含 bot），是同类项目中外部参与度最高的之一。除 sst 团队外，**~900 位外部贡献者**主要做：

- bug fix（典型 PR <50 行）
- typo / 文档改进
- i18n 翻译
- 平台兼容性（Windows / macOS / Linux 边角）
- 第三方 provider 适配（OpenAI compat / Anthropic / Vertex 等）

### 显著外部贡献者

| 贡献者 | commits | 贡献方向 |
|---|:-:|---|
| **OpeOginni** | 48 | 长期 fix 贡献 |
| **adam jones** | gmail | 单点 |
| **Adam Spiers** | github.com/adamspiers | docs |
| **Cason Adams** / **Connor Adams** | gmail | 各种小修 |
| **Adam Hosker** | hosker.info | 配置 |

### 自动化机器人贡献

| Bot | commits | 作用 |
|---|:-:|---|
| **GitHub Action** | 839 | CI 自动化（generate / sync 等）|
| **opencode-agent[bot]** | 560 | Agent 自动 PR |
| **opencode** | 502 | sst 内部 release bot |
| **Github Action** | 142 | 拼写变体 |

> Bot commits 总和 ~2,043，占总量 ~17% —— **sst 团队大量自动化**生成代码（如 `chore: generate`）

---

## 三、项目治理结构

```
┌─ sst 核心团队 ────────────────────────────────────────┐
│ 创始人 Lead：Dax Raad (1,856 commits)                 │
│ Web/UI Lead：Adam (1,280)                              │
│ Engine：Aiden Cline (1,159) + Kit Langton (518)        │
│ Cloud：Frank (676, console + cloud)                    │
│ Design：David Hill (534)                               │
└────────────────┬─────────────────────────────────────┘
                 │
┌─ 自动化生成层（bot, ~2,043 commits）─────────────────┐
│ GitHub Action / opencode-agent / opencode release    │
└────────────────┬─────────────────────────────────────┘
                 │
┌─ 外部社区（~900+ 贡献者）─────────────────────────────┐
│ • bug fix / typo / docs                              │
│ • i18n / 平台兼容                                    │
│ • 第三方 provider 适配                               │
│ • 单点 niche 修复                                    │
└──────────────────────────────────────────────────────┘
```

### 治理特征

1. **创始人驱动 + 紧密团队** —— Dax Raad 1,856 commits 远超第二名，典型创业型项目治理
2. **垂直分工清晰** —— UI/Web (Adam) vs Cloud (Frank) vs Engine (Dax+Aiden+Kit) vs Design (David) 边界明确
3. **大量自动化** —— bot 占 17% 反映 sst 团队对工具链投入很重
4. **外部参与门槛低** —— TypeScript + 文件结构清晰，新贡献者易上手
5. **Apache-2.0 开放**

---

## 四、与同类项目对比

| 项目 | 治理模式 | 总 commits | 总贡献者 | 内部占比 |
|---|---|:-:|:-:|:-:|
| **Claude Code** | Anthropic 完全闭源 | N/A | 0 公开 | 100% |
| **Codex** | OpenAI 主导 + 高门槛 Rust | 5,890 | 444 | ~92% |
| **Qwen Code** | Alibaba 主导 + 国际 i18n | ~2,400 (post-fork) | 60+ (recent) | ~89% |
| **OpenCode** | **sst 创始人 Dax 主导 + 大型开放社区** | **11,875** | **924** | **~75-80%** |
| **Gemini CLI** | Google 主导 + Apache-2.0 + 大量外部 | ~3,000 | 多 | ~70% |

**OpenCode 的位置**：**外部参与度最高的"创业型"AI Code Agent**。比 Codex / Qwen 开放，但比 Gemini 略集中。

---

## 五、有趣发现

### Adam 的 4 个邮箱别名

```
Adam   → 2363879+adamdotdevin@users.noreply.github.com
Adam   → 2363879+adamdottv@users.noreply.github.com  ← github user adamdottv
adamdotdevin → 2363879+adamdottv@users.noreply.github.com
adamdottv    → 2363879+adamdottv@users.noreply.github.com
adamelmore   → 2363879+adamdottv@users.noreply.github.com  ← 同 GitHub ID
Adam (gmail) → Acorpstein8234@gmail.com  ← 不同人（不同 ID）
```

合并后 Adam（sst）的总 commits ≈ 1,280 + 169 + 96 = **~1,545**。

### 极高 bot commits 占比

OpenCode 17% commits 来自自动化（GitHub Action / opencode-agent / opencode release）。这反映 sst 团队的**自动化文化**：

- `chore: generate` 类 PR 由 `GitHub Action` 自动产出
- `opencode-agent[bot]` 用 OpenCode 自己 dogfood 生成代码
- 大量 `sync` / `chore: update` 自动 commit

---

## 六、相关数据采集

```bash
cd /root/git/opencode

# 总数
git log --no-merges --pretty=format:"%H" | wc -l                           # → 11,875
git log --no-merges --pretty=format:"%an|%ae" | sort -u | wc -l            # → 924

# Top 贡献者
git log --no-merges --pretty=format:"%an" | sort | uniq -c | sort -rn | head -25

# sst 邮箱
git log --no-merges --pretty=format:"%an %ae" | grep -iE "@sst\.dev|@anomalyco" | sort -u

# Adam 别名合并
git log --no-merges --pretty=format:"%an %ae" | grep -i "adam"
```

---

## 相关文档

- [OpenCode 对标改进报告（29 项）](./qwen-code-opencode-improvements.md)
- [Qwen Code 贡献者页面](./qwen-code-contributors.md)
- [Codex 贡献者页面](./codex-contributors.md)
- [Kimi-CLI 贡献者页面](./kimi-cli-contributors.md)

---

**最后更新**：2026-04-28
**数据窗口**：仓库全历史
