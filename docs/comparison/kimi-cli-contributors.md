# Kimi-CLI 贡献者页面

> **数据范围**：仓库全历史 → 2026-04-28
> **总计**：~155 commits / 23 unique 贡献者
> **维护者**: Moonshot AI（月之暗面）
> **当前版本**: v1.39.0

---

## 速查表

| 类别 | 人数 | commit 占比 | 特征 |
|---|:-:|:-:|---|
| 🏛️ **Moonshot AI 内部团队** | ~3-5 | **~80%** | 单人主导（Kai 60%）+ 紧密小团队 |
| 🌍 **外部社区** | ~18+ | ~20% | 多为单 PR 贡献 |

> Kimi-CLI 是**最年轻的 AI Code Agent**项目（仅 155 commits），处于早期发展阶段，治理高度集中。

---

## 一、Moonshot AI 核心团队

### 项目领导层

| 贡献者 | commits | 别名 / Email | 角色 |
|---|:-:|---|---|
| **Kai / Kaiyi** | **94 + 2 = 96** | `me@kaiyi.cool` | 🌟 **项目 Lead** · 主导 release / skills / kosong 模型集成 / Kimi 适配 · 占总 commits **62%** |
| **Yi Yang** | 3 | `yangyi@msh.team` + `ahyangyi@gmail.com` | Moonshot 团队（`@msh.team` = Moonshot）· Soul agent + diff 渲染 + 文档 |
| **Arthur** | — | `wangshuyi@moonshot.cn` | Moonshot 内部（仅 1 commit）|

### 主要贡献者（推测内部 / 紧密合作）

| 贡献者 | commits | 焦点领域 | 代表 PR |
|---|:-:|---|---|
| **Zoee** (`n-WN`) | 14 | Tools + Auth + Shell session | PR#1843 MCP tool output truncate · PR#1827 list_directory cap · PR#1822 cross-process token refresh lock |
| **qer** | 10 | Approval + Shell + Auth | PR#2087 approval scope to turn lifecycle · PR#2078 /usage display · PR#2060 OAuth recovery |
| **Tempura** | 9 | Hooks + Build | PR#1561 lifecycle hooks system · PR#1651 hooks docs · PR#1831 PyInstaller fix |
| **Will (liruifengv)** | 7 | Web UI + Config | PR#2088 max_steps 500→1000 · PR#1921 markdown spacing · PR#1920 web UI buttons |

### 其他贡献者

| 贡献者 | commits | 来源 |
|---|:-:|---|
| **_Kerman** (`kermanx@qq.com`) | 2 | shell + install |
| **Kaiyi** (alias of Kai) | 2 | Anthropic thinking effort |
| **bigeagle** | 2 | — |
| **Yi Yang** (gmail) | 1 | 同 yangyi@msh.team（Moonshot）|

---

## 二、外部社区（单 PR 贡献者）

| 贡献者 | Email | 贡献 |
|---|---|---|
| **zq.deer** | qq.com | 单 PR |
| **Yousa** | gmail | 单 PR |
| **Yongteng Lei** | outlook.com | 单 PR |
| **qszhu** | gmail | 单 PR |
| **Nyx** | gmail | 单 PR |
| **Louis** | github noreply | 单 PR |
| **KOMATA** | github noreply | 单 PR |
| **Jesse** | gmail | 单 PR |
| **Howard Peng** | gmail | 单 PR |
| **elis132** | github noreply | 单 PR |
| **drunkpiano** | gmail | 单 PR |
| **ayokaa** | github noreply | 单 PR |

**外部贡献特征**：仍以早期反馈期的零星贡献为主，无显著长期外部贡献者。

---

## 三、项目治理结构

```
┌─ Moonshot AI 团队 ──────────────────────────────────┐
│ 项目 Lead：Kai / Kaiyi (kaiyi.cool, 96 commits 62%) │
│ Soul Agent：Yi Yang (yangyi@msh.team)                │
│ Internal：Arthur (wangshuyi@moonshot.cn)             │
└────────────────┬─────────────────────────────────────┘
                 │
┌─ 紧密合作贡献者（推测内部或长期合作）─────────────┐
│ Zoee（Tools 14）· qer（Approval 10）·               │
│ Tempura（Hooks 9）· Will/liruifengv（Web 7）         │
└────────────────┬─────────────────────────────────────┘
                 │
┌─ 早期社区（~18+ 单 PR 贡献者）─────────────────────┐
│ 中文社区为主（多 qq.com / gmail 中国地区）           │
│ 单 PR / 单点 fix 模式                                 │
└──────────────────────────────────────────────────────┘
```

### 治理特征

1. **极度集中** —— Kai 一人占 62% commits，比任何其他 AI Code Agent 项目都集中
2. **早期阶段** —— 仅 155 commits / 23 贡献者（vs Codex 5,890 / Qwen 2,400 post-fork）
3. **快速迭代** —— Apr 2026 一月内多次 release（v1.38.0 / v1.39.0），平均 5-7 天一版
4. **kosong 模型层** —— Kimi-CLI 有独立的 `kosong` 模型抽象层（version 0.52.0），与 CLI 同步发布
5. **Hooks 系统** —— Tempura 主导 PR#1561 lifecycle hooks（Wire 1.7），是少数 Kimi 独有的扩展点
6. **中文社区主导** —— 外部贡献者多为中国地区开发者（qq.com / 中文 ID）

---

## 四、与同类项目对比

| 项目 | 维护者 | 总 commits | 总贡献者 | 内部占比 | 项目年龄 |
|---|---|:-:|:-:|:-:|:-:|
| **Claude Code** | Anthropic | N/A | 0 公开 | 100% | ~1.5 年 |
| **Codex** | OpenAI | 5,890 | 444 | ~92% | ~1 年 |
| **Qwen Code** | Alibaba | ~2,400 | 60+ | ~89% | 6 个月 (post-fork) |
| **OpenCode** | sst | 11,875 | 924 | ~75-80% | ~1 年 |
| **Kimi-CLI** | **Moonshot AI** | **155** | **23** | **~80%** | **<6 个月** |
| **Gemini CLI** | Google | ~3,000 | 多 | ~70% | ~1.5 年 |

**Kimi-CLI 的位置**：**最年轻 + 最集中**的 AI Code Agent。处于"创始人主导早期"阶段。

---

## 五、值得关注的 Kai 个人技术决策

由于 Kai 一人决定了 62% 的代码方向，几个有特色的选择：

### 1. kosong 抽象层

Kai 把模型层抽出独立 package `kosong`（每次 CLI release 同时发布 kosong 新版）。这种**模型层与 CLI 解耦**的设计在其他项目中较少见 —— 让 Kimi-CLI 能在不破坏 CLI API 的前提下快速适配新模型（DeepSeek / OpenAI compat / Anthropic 等）。

### 2. KIMI_MODEL_THINKING_KEEP 环境变量

PR#2029 加 `KIMI_MODEL_THINKING_KEEP` 环境变量来控制 thinking 块的保留 —— 类似 Qwen 的 `QWEN_DISABLE_AUTO_TITLE` 风格，**通过环境变量做 feature 开关**而非 config 文件。

### 3. fix(kimi): default openai_legacy reasoning_key for DeepSeek 400

Kai 关注**第三方 provider 兼容性**（DeepSeek / OpenAI legacy），这与 Qwen Code / OpenCode 的多 provider 路线一致。

### 4. Soul Agent

Yi Yang 主导的 `soul` agent 概念（PR#2003 yolo reminder 在 compaction 后重新注入）—— 是 Kimi 特有的**长期人格保持**机制。

---

## 六、相关数据采集

```bash
cd /root/git/kimi-cli

# 总数
git log --no-merges --pretty=format:"%H" | wc -l                           # → 155
git log --no-merges --pretty=format:"%an|%ae" | sort -u | wc -l            # → 23

# Moonshot 邮箱识别
git log --no-merges --pretty=format:"%an %ae" | grep -iE "@moonshot\.cn|@msh\.team" | sort -u

# Top 贡献者
git log --no-merges --pretty=format:"%an" | sort | uniq -c | sort -rn

# Kai 历史
git log --no-merges --author="Kai" --pretty=format:"%cs %s" | head -20
```

---

## 相关文档

- [Qwen Code 贡献者页面](./qwen-code-contributors.md)
- [Codex 贡献者页面](./codex-contributors.md)
- [OpenCode 贡献者页面](./opencode-contributors.md)
- [Kimi-CLI 工具文档](../tools/kimi-cli/) （tools 目录单独项）

---

**最后更新**：2026-04-28
**数据窗口**：仓库全历史
**注意**：Kimi-CLI 是早期项目，数据规模较小，治理模式可能随项目成熟而演化。
