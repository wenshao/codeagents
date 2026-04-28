# Qwen Code 贡献者页面

> **数据范围**：2025-10-23（fork from Gemini CLI v0.8.2）→ 2026-04-28
> **总计**：~2,400+ commits / 60+ 贡献者
>
> 本页是 Qwen Code 项目治理总览，按角色分类介绍核心维护团队、活跃贡献者、社区参与者，以及如何参与贡献。

---

## 速查表

| 类别 | 人数 | 特征 | commit 占比 |
|---|:-:|---|:-:|
| 🏛️ **Alibaba 内部团队**（按 `@alibaba-inc.com` 确认） | 13+ | 项目治理 + 架构决策 + niche owner | ~75% |
| 🔧 **核心活跃贡献者**（推测内部 / 紧密合作） | ~10 | 高频跨包改动 + 中文显示名 + 个人邮箱 | ~14% |
| 🌍 **外部社区**（确认非 Alibaba） | ~30+ | 单点 / 集中爆发 / i18n / 学生 | ~11% |
| 📜 **Gemini CLI 上游遗产** | 30+ | fork 前贡献，post-fork 不活跃 | 历史 ~5% |

---

## 一、Alibaba 内部团队（核心维护者）

### 项目领导层

| 贡献者 | 邮箱 | 角色推测 |
|---|---|---|
| **Binyuan Hui** (`binyuan.hby@`) | alibaba-inc.com | 🌟 **Tongyi/Qwen 团队相关 lead**（推测项目 sponsor） |
| **zeyu cui** (`zeyu.czy@`) | alibaba-inc.com | 推测 Qwen 团队成员 |

### 主力维护者（按 commit 量）

| 贡献者 | 别名 | 邮箱 | 焦点领域 | post-fork commits |
|---|---|---|---|:-:|
| **tanzhenxin** | — | `tanzhenxing1987@gmail.com`（个人邮箱）| **Lead Maintainer** · 跨包重构 · revert 决策权 · 配置 / OpenAI converter | **517** |
| **yiliang114 / 易良 / mingholy.lmh / Mingholy** | 4 别名 | `mingholy.lmh@alibaba-inc.com` + qq 个人邮箱 | **VSCode IDE companion + Webui** owner | 333 + 213 + 33 + 12 |
| **顾盼 / LaZzyMan** | 2 别名 | `zeusdream7@gmail.com`（个人邮箱）| **Phase-N 重构 lead**（Phase 2 slash command 多模式） · Permission / RipGrep | 191 + 11 |
| **wenshao / Shaojin Wen / 高铁** | 3 别名 | `shaojin.wensj@alibaba-inc.com` | **Performance + Architecture** · 度量驱动重构 · Memory 系统 · `/review` 改进 | 166 + 54 |
| **DennisYu07 / 宇溯** | 2 别名 | `yusu.cjy@alibaba-inc.com` | **Hooks 系统奠基者** · ACP hooks · 文件互锁 | 157 + 15 |

### Niche 子领域 owner（专精团队）

| 贡献者 | 邮箱 | 专精方向 | 代表 PR |
|---|---|---|---|
| **chiga0 / ChiGao** | `gary.gao12580@gmail.com` + `arno.ga0@outlook.com` | 🎨 **TUI 渲染** · Compact 模式 | PR#3013 SlicingMaxSizedBox · PR#3591 flicker foundation · PR#3352 dual-output sidecar · PR#3100 compact mode UX |
| **Edenman / BZ-D** | github noreply | 🖥️ **终端协议 + MCP OAuth** | PR#3460 OSC 11 主题检测 · PR#3489 OAuth URL 可点击 · PR#3442 mcp add OAuth flag · PR#3393 OSC 52 复制热键 |
| **思晗** | `housihan.hsh@alibaba-inc.com` | CLI 核心 | — |
| **胡玮文** | `huweiwen.hww@alibaba-inc.com` | 单 commit 内部协作 | — |
| **xuewenjie / xwj02155382** | `xwj02155382@alibaba-inc.com` | 内部专项 | 37 + 27 commits |

### 其他 Alibaba 内部贡献者

| 贡献者 | 邮箱 |
|---|---|
| **skyfire / 乾离** | `gengwei.gw@alibaba-inc.com` |
| **SunDapeng** | `dapeng.sdp@alibaba-inc.com` |
| **家娃** | `guanjing.pangj@alibaba-inc.com` |
| **沐目** | `xiangy.zhangxy@alibaba-inc.com` |
| **秦奇** | `gary.gq@alibaba-inc.com` |

---

## 二、核心活跃贡献者（推测内部 / 紧密合作）

> 高频提交 + 中文显示名 + 用个人邮箱 —— 行为模式更像内部团队，但未通过 `@alibaba-inc.com` 邮箱直接确认。

| 贡献者 | post-fork commits | 焦点领域 | 代表 PR |
|---|:-:|---|---|
| **pomelo-nwu** | 90 | 单系统专项 | — |
| **DragonnZhang** | 73 | 跨子系统 | PR#3593 argument-hint slash commands |
| **qqqys** | 35 | UX + Session picker | PR#3093 `/rename` · PR#3605 `/resume` Space-preview · PR#3329 实时 token 显示 |
| **joeytoday** | 31 | 文档 | PR#3325 OAuth discontinuation docs |
| **jinye / DJY1989418** | 19 | SDK + Recovery | PR#3441 `/rewind` · PR#3494 Python SDK · PR#3318 API preconnect |
| **Reid / reidliu41** | 12 | Arena + Swarm | PR#3433 dynamic swarm worker · PR#3614 arena 测试 |
| **zhangxy-zju** | 11 | ACP + Retry | PR#3080 persistent retry · PR#3463 ACP 并发 |
| **Weaxs** | 9 | 单系统 | — |
| **liqoingyu** | 17 | 单系统 | — |
| **刘伟光** | 20 | 单系统 | — |
| **Tu Shaokun** | 8 | 单系统 | — |

---

## 三、外部社区贡献者

> 详细分析见 [Qwen Code 外部贡献者分析](./qwen-code-external-contributors.md)

### 第一梯队 · 高产外部

| 贡献者 | 国家 | commits（2026-04） | 方向 |
|---|---|:-:|---|
| **chinesepowered** (John London) | 🇮🇳 印度（推测）| 21 | 跨子系统 quick fix（集中爆发期）|
| **euxaristia** | — | 5 | Loop detection / 错误恢复 |
| **John London** ¹ | — | 4 | Config refactor |

¹ **与 chinesepowered 显示名相同但不同人**（不同 email）

### i18n 国际化贡献者

| 贡献者 | 国家 | 语言 | PR |
|---|---|---|---|
| **Jordi Mas** | 🇪🇸 Catalonia | Catalan | PR#3643 |
| **MikeWang0316tw** | 🇹🇼 Taiwan | Traditional Chinese | PR#3569 |
| **Lassana siby** | 🌍 | French | PR#3126 |

### 学术机构贡献者

| 贡献者 | 机构 | 贡献 |
|---|---|---|
| **YuchenLiang00** | 🎓 清华 (`@mails.tsinghua.edu.cn`) | `/context detail` 子命令 |
| **chaoliang yan** | 🎓 UNSW Australia (`@ad.unsw.edu.au`) | PR#3543 sdk-java 自定义 env |

### 国际多元社区

| 贡献者 | 国家 | PR |
|---|---|---|
| **harsh** (Ojhaharsh) | 🇮🇳 印度 | PR#3481 qwenOAuth2 错误处理 |
| **Sharvil Saxena** (sharziki) | 🇮🇳 印度 | PR#3431 `/clear` 取消 `/btw` |
| **Pedro Ribeiro Mendes Júnior** | 🇧🇷 巴西 | PR#3358 `M-d` Emacs 风格 |
| **Viktor Szépe** | 🇭🇺 匈牙利 | PR#2189 typo fix |

### 其他单点贡献者

`Yan Shen` (sticky todo panel) · `Fu Yuchen` (reasoning_content fix) · `Dragon` (argument-hint) · `gin-lsl` (WebFetch markdown) · `Gordon Lam` (samplingParams) · `apophis` (CJK 词分割) · `dreamWB` (vscode context menu) · `ihubanov` (slashCommands disable) · `lamb` (macOS Zed 检测) · `克竟` (Shift+Tab placeholder) · `pikachu` (update 通知时序) · `Richard Luo` (Windows 安装 docs) · `YingchaoX` (vim shortcut) · `feyclaw` (Telegram 语音) · `evan70` (DEP0169)

---

## 四、Gemini CLI 上游遗产（fork 前贡献，post-fork 不活跃）

Qwen Code 于 **2025-10-23** 从 [Gemini CLI v0.8.2](https://github.com/google-gemini/gemini-cli) fork。这些上游 Google 团队成员的贡献仍可见于 `git log`，但 fork 后不再活跃：

| 贡献者 | 历史 commits | 来源 |
|---|:-:|---|
| **Olcan** | 166 | Google Gemini CLI |
| **Taylor Mullen / N. Taylor Mullen** | 125 + 87 | Google |
| **Tommaso Sciortino** | 114 | Google |
| **Brandon Keiji** | 103 | Google |
| **Jacob Richman** | 78 | Google |
| **Allen Hutchison** | 75 | Google |
| **Shreya Keshive** | 64 | Google |
| **Alexander Farber** | 63 | Google |
| **christine betts** | 55 | Google |
| **Seth Troisi** | 54 | Google |
| **Sandy Tao** | 52 | Google |
| **Abhi** | 52 | Google |
| **Jerop Kipruto** | 51 | Google |
| **matt korwel** | 49 | Google |

**fork 后状态**：Qwen Code 独立演进，不再 sync 上游。详情见 [Gemini CLI backport 报告](./qwen-code-gemini-upstream-report.md)（追踪 61 项可 backport 改进）。

---

## 五、项目治理结构

### 决策层级

```
┌─ 战略方向 ─────────────────────────┐
│ Binyuan Hui + Tongyi/Qwen 团队     │  Alibaba 内部
│ (@alibaba-inc.com)                 │
└────────────────┬───────────────────┘
                 │
┌─ 架构 / Phase 重构 ────────────────┐
│ tanzhenxin (lead)                  │  517 commits
│ 顾盼 (LaZzyMan, Phase-N)           │  191 commits
└────────────────┬───────────────────┘
                 │
┌─ Niche 子领域 owner ──────────────────────────────────┐
│ 易良 (yiliang114)    → VSCode + Webui   333 commits   │
│ chiga0/ChiGao        → TUI 渲染          6 commits    │
│ Edenman/BZ-D         → 终端协议+OAuth    5 commits    │
│ DennisYu07           → Hooks 系统       157 commits   │
│ wenshao              → Performance      166 commits   │
└────────────────┬─────────────────────────────────────┘
                 │
┌─ 活跃功能贡献者（推测内部）─────────────────────────┐
│ pomelo-nwu / DragonnZhang / qqqys / joeytoday /      │
│ jinye / Reid / zhangxy-zju / Weaxs / Tu Shaokun ...  │
└────────────────┬─────────────────────────────────────┘
                 │
┌─ 外部社区 ────────────────────────────────────────────┐
│ chinesepowered (集中爆发) · euxaristia (loop detect)  │
│ Jordi Mas / MikeWang0316tw / Lassana siby (i18n)      │
│ ~22 位单点贡献者                                       │
└──────────────────────────────────────────────────────┘
```

### 治理特征

1. **内部主导，社区开放**：~89% commits 来自 Alibaba 内部团队 + 紧密合作者，~11% 来自纯外部社区
2. **Niche 子领域有专精 owner**：TUI 渲染 / 终端协议 / Hooks 等核心 niche 都有内部专属负责人，不是通用维护者
3. **revert 决策内部把关**：tanzhenxin 等 lead 把 revert / 大重构作为内部决策，PR#3433 → PR#3468 revert / PR#3567 → PR#3633 revert 都是内部决策
4. **Phase 化重构模式**：顾盼推动的 Phase 2 slash command 多模式重构是典型，往往跨多个 PR 分阶段完成
5. **国际 i18n 长尾依赖外部**：内部不可能维护所有语言，i18n 长尾贡献者是项目国际化的唯一可持续路径

### 与同类项目治理对比

| 项目 | 治理模式 | 外部贡献占比 | 公开维护者列表 |
|---|---|:-:|:-:|
| **Claude Code** | Anthropic 内部封闭，仅闭源 binary | 0% | ❌ |
| **Codex** | OpenAI 内部主导，外部 PR 少 | ~10% | ❌ |
| **Qwen Code** | Alibaba 主导 + 国际 i18n | **~11%** | ❌（**本页面是首次梳理**）|
| **OpenCode** | sst（Dax）+ 紧密小团队 | ~20% | ✓ |
| **Gemini CLI** | Google 主导 + Apache-2.0 + 大量外部 | ~30% | ✓ |

---

## 六、如何参与贡献

> 详见 [Qwen Code 外部贡献者分析](./qwen-code-external-contributors.md#九给外部贡献者的建议)

### 推荐方向

| 想做什么 | 难度 | 参考模式 |
|---|:-:|---|
| Loop detection / 错误恢复 | ★★★ | `euxaristia` —— 度量驱动 + 系统化方案 |
| 跨子系统 quick fix | ★★ | `chinesepowered` —— 集中扫荡 |
| Config refactor | ★★ | `John London` —— 找现存 dup logic dedupe |
| i18n 翻译 | ★ | `Jordi Mas` —— 单 PR 加一种语言 |
| 学习/学生项目 | ★ | `YuchenLiang00` —— 选小型 `/<command>` 子功能 |
| 单点 niche fix | ★ | `harsh` `Pedro` —— 修一个具体 bug |

### ⚠️ 避开的方向（已有内部 owner）

| 方向 | 原因 | 内部 owner |
|---|---|---|
| TUI 渲染 / Compact 模式 | 已有专属 owner | `chiga0/ChiGao` |
| 终端协议 / MCP OAuth | 已有专属 owner | `Edenman/BZ-D` |
| Hooks 系统 | 已有专属 owner | `DennisYu07` |
| Phase-N 大型重构 | 内部领地 | `顾盼` / `tanzhenxin` |
| revert 已合并的 PR | 内部决策权 | `tanzhenxin` |

### 资源

- **GitHub**: https://github.com/QwenLM/qwen-code
- **PR 列表**: https://github.com/QwenLM/qwen-code/pulls
- **Issues**: https://github.com/QwenLM/qwen-code/issues
- **Roadmap**: https://github.com/QwenLM/qwen-code/issues/2516（智能工具并行 等）
- **CONTRIBUTING.md**: 项目根目录

---

## 七、附录

### A. 数据采集方法

```bash
# 总 commit / 作者数（post-fork）
cd /root/git/qwen-code
git log --no-merges --since="2025-10-23" --pretty=format:"%H" | wc -l    # → 2,406
git log --no-merges --since="2025-10-23" --pretty=format:"%an|%ae" | sort -u | wc -l  # → 60+

# 按贡献者排名
git log --no-merges --since="2025-10-23" --pretty=format:"%an" | sort | uniq -c | sort -rn | head -30

# Alibaba 内部识别
git log --no-merges --pretty=format:"%an %ae" | grep -i "alibaba-inc.com" | sort -u

# 单一作者历史
git log --no-merges --since="2025-10-23" --author="<NAME>" --pretty=format:"%cs %s" | head -20
```

### B. 数据局限性

1. **email 域名识别不可靠** —— 阿里系工程师常用个人邮箱（gmail / qq / outlook）做 github contribution。本页 v1 / `external-contributors` v1 都曾因此误判。
2. **同人多别名** —— `wenshao = Shaojin Wen = 高铁`、`mingholy.lmh = Mingholy = 易良 = yiliang114`、`顾盼 = LaZzyMan` 等。已尽可能合并。
3. **核心活跃贡献者推测**：`pomelo-nwu` / `qqqys` / `Reid` 等无法从邮箱直接确认内/外，按行为模式（高频跨包改动 + 中文显示名）归为 "推测内部 / 紧密合作"。

### C. 相关文档

- [Qwen Code 外部贡献者深度分析](./qwen-code-external-contributors.md) —— 外部社区贡献者画像 + 6 种贡献模式
- [Qwen Code 改进报告](./qwen-code-improvement-report.md) —— 275 项改进 + 101 PR 追踪
- [Qwen Code Gemini CLI backport 报告](./qwen-code-gemini-upstream-report.md) —— 上游可 backport 改进
- [Qwen Code Codex 对标](./qwen-code-codex-improvements.md) —— 28 项 Codex CLI 对标
- [Qwen Code OpenCode 对标](./qwen-code-opencode-improvements.md) —— 29 项 OpenCode 对标

---

**最后更新**：2026-04-28
**数据窗口**：post-fork（2025-10-23 → 2026-04-28，~6 个月）
**贡献者总数**：~60+（含 Alibaba 内部 13+ + 推测内部/紧密合作 ~10 + 外部 ~30+）
