# Qwen Code 外部贡献者分析

> **数据窗口**：2026-04-01 → 2026-04-28（28 天）· **464 commits** · **48 位贡献者**
>
> 本文区分 Qwen Code 真正的**外部社区贡献者**与 Alibaba 内部团队，分析贡献模式与项目治理特征。

---

## 一句话结论

> **Qwen Code 项目治理 ~89% 由 Alibaba 内部主导，~11% 来自真正外部社区**。外部贡献集中在错误恢复（`euxaristia`）、跨子系统 quick fix（`chinesepowered`）、config refactor（`John London`）三个方向 + i18n 长尾。**核心架构 + niche 子领域均有内部专精团队 owner**，外部贡献空间集中在边角与 i18n。

---

## 速查表（Top 外部贡献者）

| 排名 | 贡献者 | commits | 专精方向 | 代表 PR |
|:---:|---|:---:|---|---|
| 🥇 | **chinesepowered** (John London 🇮🇳) | **21** | 跨子系统 quick fix · sandbox / SDK / channels / weixin / dingtalk | PR#2962-#2981（集中爆发期 ~20 PR） |
| 🥈 | **euxaristia** | **5** | Loop detection / 错误恢复 | PR#3236 stagnation 检测 · PR#3178 validation retry 循环 |
| 🥉 | **John London** ¹ | **4** | Config refactor | PR#3653 dedupe `QWEN_CODE_API_TIMEOUT_MS` |
| 国际化 | Jordi Mas 🇪🇸 / MikeWang0316tw 🇹🇼 / Lassana siby 🌍 | 3 | i18n（Catalan / 繁中 / French） | PR#3643 / PR#3569 / PR#3126 |
| 学术 | YuchenLiang00 🎓 清华 / chaoliang yan 🎓 UNSW | 2 | 单点 niche | `/context detail` / sdk-java env |
| 长尾 | ~22 位单 PR 贡献者 | ~22 | 各种 fix/feat | 见 §4 |

¹ **`chinesepowered` 与 `John London` 显示名相同但**不同人**（不同 email）。

**外部 commit 总量**：~50 / 464 ≈ **11%**

---

## 一、方法论

### 🛑 重要警告：email 域名识别极不可靠

**阿里系工程师常用个人邮箱（gmail / outlook / qq）做 github contribution**。本报告 v1 曾因此误判 2 位内部工程师为外部社区贡献者，已在 v2 修订。

**本报告综合 5 类信号判断**：

| 信号 | 内部 ↑ | 外部 ↑ |
|---|:-:|:-:|
| `@alibaba-inc.com` 邮箱 | ✓ |  |
| 中文显示名（`易良` `顾盼` `思晗`） | ✓ |  |
| 高频跨包改动 + Phase 重构 | ✓ |  |
| revert 决策权 / niche 子系统 owner | ✓ |  |
| 单一专精方向 + 短期爆发 |  | ✓ |
| 国际 i18n 贡献 |  | ✓ |
| 学术机构邮箱（`.edu` / `.edu.cn`） |  | ✓ |
| 单 PR + 边角修复 |  | ✓ |

### 别名合并（同人不同显示名）

| 真名 | 别名 | 共享 email |
|---|---|---|
| `wenshao` | `Shaojin Wen` | `shaojin.wensj@alibaba-inc.com` |
| `易良` | `yiliang114` / `mingholy.lmh` | `1204183885@qq.com` |
| `顾盼` | `LaZzyMan` | `zeusdream7@gmail.com` |

---

## 二、Top 外部贡献者画像

### 🥇 chinesepowered (John London) · 21 commits

```
GitHub:      chinesepowered
Email:       nlai@rediffmail.com  (rediffmail = 印度邮件服务)
显示名:      "John London"
focus:       跨子系统 quick fix
特征:        集中爆发期 — 一周内 PR#2962-#2981 共 ~20 PR 合并
```

**代表 PR**：

- `PR#2981` SDK Stream.return() 防 hang
- `PR#2975` channels 桥接 disconnect handler 重连
- `PR#2970` weixin 4-byte PNG magic signature
- `PR#2962` sandbox latest tag fallback
- `PR#2979` dingtalk reactionContext 内存泄漏

**为什么重要**：少数能在 sandbox / SDK / channels 等**底层基础设施**上做实质修复的外部贡献者。看上去是用户报告 bug 后做了一次集中清扫。

---

### 🥈 euxaristia · 5 commits

```
GitHub:      euxaristia
focus:       Loop detection / 错误恢复 / build infra
```

**代表 PR**：

- `PR#3236` enhanced loop detection with **stagnation + validation-retry checks**
- `PR#3178` detect tool validation retry loops + inject stop directive
- `PR#2857` shell output 宽度约束防 box 溢出
- `PR#3237` build 用 `node --import tsx` 替代 npx

**为什么重要**：**agentic 系统稳定性核心路径**改进者。命中 codeagents item-27（错误恢复分类路由）方向。

---

### 🥉 John London · 4 commits

```
GitHub:      benevolentjoker@gmail.com
注意:        与 chinesepowered 显示名相同但不同人（不同 email）
focus:       Config refactor
```

**代表 PR**：

- `PR#3653` refactor(config): dedupe `QWEN_CODE_API_TIMEOUT_MS` env override（PR#3629 follow-up）
- 几个其他小 refactor

---

## 三、i18n 国际化贡献

3 位单 PR i18n 贡献者，是项目国际化**唯一可持续路径**：

| 贡献者 | 国家 | PR | 语言 |
|---|---|---|---|
| **Jordi Mas** (jmas@softcatala.org) | 🇪🇸 Catalonia | PR#3643 | Catalan（softcatala.org 是加泰罗尼亚开源本地化组织） |
| **MikeWang0316tw** | 🇹🇼 Taiwan | PR#3569 | Traditional Chinese (zh-TW) |
| **Lassana siby** | 🌍 非洲（推测） | PR#3126 | French (fr-FR) |

**长尾断层**：日 / 韩 / 西 / 葡 / 德 / 俄 等大语种均缺贡献者。

---

## 四、单点贡献者（~22 位）

### 影响较大的单点贡献

| 贡献者 | PR | 说明 |
|---|---|---|
| **Yan Shen** | PR#3507 sticky todo panel | 重要 UI 功能，对标 Claude Code |
| **Fu Yuchen** | PR#3590 reasoning_content resume preserve | 命中 item-22 Thinking 块修复 |
| **Dragon (DragonnZhang)** | PR#3593 argument-hint for slash commands | slash 命令 UX |
| **gin-lsl** | PR#2734 WebFetch Markdown for Agents | WebFetch 改进 |
| **Gordon Lam** | PR#3458 OpenAI samplingParams verbatim | provider 兼容 |
| **apophis** | PR#2942 CJK 词分割 (Intl.Segmenter) | 中日韩文本处理 |
| **dreamWB** | PR#3477 vscode 原生 context menu copy | VSCode UX |
| **ihubanov** | PR#3445 `slashCommands.disabled` 设置 | 配置 |

### 学生 / 研究者贡献

| 贡献者 | 机构 | 贡献 |
|---|---|---|
| **YuchenLiang00** | 🎓 清华 (`@mails.tsinghua.edu.cn`) | `/context detail` 子命令 |
| **chaoliang yan** | 🎓 UNSW Australia (`@ad.unsw.edu.au`) | PR#3543 sdk-java 自定义 env 传递 |

### 国际多元贡献

| 贡献者 | 国家 | PR |
|---|---|---|
| **harsh** (Ojhaharsh) | 🇮🇳 印度 | PR#3481 qwenOAuth2 错误处理 + PR#1675 xdg-open graceful |
| **Sharvil Saxena** (sharziki) | 🇮🇳 印度 | PR#3431 `/clear` 取消 `/btw` 对话 |
| **Pedro Ribeiro Mendes Júnior** | 🇧🇷 巴西 | PR#3358 `M-d` Emacs 风格绑定 |
| **Viktor Szépe** | 🇭🇺 匈牙利 | PR#2189 typo fix |

### 其他单点贡献

`lamb` macOS Zed 检测 · `joeytoday` auth docs · `克竟` 防止 Shift+Tab placeholder · `pikachu` update 通知时序 · `Richard Luo` Windows 安装 docs · `YingchaoX` vim shortcut · `feyclaw` Telegram 语音 · `evan70` DEP0169 dep upgrade

---

## 📌 已纠正分类（原误判为外部）

> ⚠️ **本报告 v1 曾误判这 2 位为外部，v2 已修订**

| 贡献者 | commits | 实际身份 | 重要贡献 |
|---|:-:|---|---|
| **chiga0 / ChiGao** | 6 | **内部 TUI 渲染负责人** | PR#3013 SlicingMaxSizedBox · PR#3591 flicker foundation · PR#3352 dual-output sidecar · PR#3100 compact mode UX |
| **Edenman / BZ-D** | 5 | **内部终端协议 + MCP OAuth 负责人** | PR#3460 OSC 11 主题检测 · PR#3489 OAuth URL 可点击 · PR#3442 mcp add OAuth flag · PR#3393 OSC 52 复制热键 |

**这是 Alibaba 内部分工成熟度的关键信号** —— niche 子领域有专精 owner，不是通用维护者。

---

## 五、统计概览

### Commit 分布（462 commits / 28 天）

```
Alibaba 内部确认           ████░░░░░░░░░░░░░░░░░  ~50%（4 人，含 wenshao 199）
推测内部 / 紧密合作        █████░░░░░░░░░░░░░░░░  ~35%（~10 人，含 tanzhenxin 76）
真正外部社区               █████░░░░░░░░░░░░░░░░  ~11%（~30+ 人）
未分类                     █░░░░░░░░░░░░░░░░░░░░  ~4%
```

### 外部贡献者细分

```
chinesepowered (集中爆发):  ██████░░░░  21 commits
euxaristia / John London:   ██░░░░░░░░  ~9 commits
单点贡献 (~22 人):          █████░░░░░  ~20 commits
i18n (3 人):                █░░░░░░░░░  3 commits
─────────────────────────  ──────────
小计:                       ~50+ commits（占总量 11%）
```

---

## 六、贡献模式（5 种）

### ① 补丁集中爆发期 · `chinesepowered` 模式

短时间（几天到一周）集中提交 10+ PR，覆盖多个不相关子系统。**推测原因**：公司内部使用 Qwen Code 时遇到一系列 bug，攒批一次性贡献。

### ② 度量驱动重构 · `euxaristia` 模式

发现性能/正确性 bug → 写复现 → 写修复 → 带 benchmark/度量数据 → PR。质量高，常超出内部团队优先级。

### ③ niche 协议专家（外部稀少）

某狭窄技术域（OAuth flow / TLS / sandboxing）做深度修复或新功能。

> **注**：Qwen Code 内部已有 niche 协议负责人（`chiga0/ChiGao` TUI 渲染、`Edenman/BZ-D` 终端协议 + MCP OAuth）。**外部 niche 协议专家相对稀缺**。

### ④ i18n 长尾贡献

单 PR 加一个语言文件，几乎不与代码逻辑交互。**项目国际化的唯一可持续路径** —— 内部团队不可能维护所有语言。

### ⑤ 双向 spec/impl 闭环 · `wenshao` 个人模式

同一人**同时维护 codeagents spec 仓库 + 在 qwen-code 实现 spec**。例如 item-28 Skill 装载性能优化 spec → PR#3604 实现（PR body 显式引用 spec）。

> **稀有但极有价值** —— 形成"提案 → 设计 → 实现"快速反馈循环，但这种贡献者目前是孤例。

---

## 七、健康/风险信号

### ✅ 健康信号

1. **核心 niche 由内部专精团队覆盖** —— TUI 渲染 / 终端协议 / MCP OAuth 都有专属 owner，反映团队成熟度
2. **错误恢复路径有外部参与** —— `euxaristia` 在 agentic 稳定性核心做实质改进
3. **多元国家 / 地区** —— 印度、巴西、匈牙利、加泰、台湾、澳洲、中国大陆都有贡献
4. **学术机构开始参与** —— 清华、UNSW 学生贡献，对教育市场有吸引力

### ⚠️ 风险信号

1. **核心架构基本全由 Alibaba 内部主导** —— Phase 重构、revert 决策、niche 子领域 owner 全在内部
2. **外部贡献集中在 fix/ 而非 feat/** —— 除 `chinesepowered` 集中爆发期外，多数是 bug fix
3. **Top 外部贡献者匿名度高** —— `chinesepowered` 显示名 "John London" 但 email 是印度邮件服务，真实身份不透明
4. **i18n 长尾断层** —— 日韩西葡德俄等大语种均缺贡献者
5. **email-based 识别不可靠** —— 项目对外**缺少正式贡献者身份标记**（CODEOWNERS / 维护者列表 / 头衔徽章），导致外部观察者易系统性误判
6. **"双重身份" 贡献者罕见** —— `wenshao` 是孤例，spec/impl 闭环知识传播路径单一

---

## 八、与同类项目治理对比

| 项目 | 治理模式 | 外部贡献占比（commit 估算） |
|---|---|---|
| **Claude Code** | Anthropic 内部封闭，无外部 commit（仅闭源 binary） | 0% |
| **Codex** | OpenAI 内部主导，外部 PR 少 | ~10% |
| **Qwen Code** | **Alibaba 主导 + 比 Codex 更开放 + 国际 i18n** | **~11%** |
| **OpenCode** | sst（创始人 Dax）+ 紧密小团队 + 中等外部 | ~20% |
| **Gemini CLI** | Google 主导 + Apache-2.0 + 大量外部贡献 | ~30% |

**Qwen Code 位置**：开放程度介于 OpenCode（开放但小）和 Gemini CLI（高度开放）之间。**比 Codex / Claude Code 更外向**。

---

## 九、给外部贡献者的建议

> 想给 Qwen Code 贡献？参考已有外部贡献者的成功模式，避开内部专精团队领地。

### 推荐方向

| 想做什么 | 参考模式 | 难度 |
|---|---|---|
| Loop detection / 错误恢复 | `euxaristia` —— 发现真实问题 + 系统化方案 | ★★★ |
| 跨子系统 quick fix | `chinesepowered` —— 集中扫荡多个 bug 一次性 PR | ★★ |
| Config refactor | `John London` —— 找现存 dup logic 做 dedupe | ★★ |
| i18n | `Jordi Mas` —— 单 PR 加一个语言文件 | ★ |
| 学习/学生项目 | `YuchenLiang00` —— 选一个 `/<command>` 的小子功能 | ★ |
| 单点 niche fix | `harsh` `Pedro` —— 修一个具体 bug | ★ |

### ⚠️ 避开的方向

| 方向 | 原因 |
|---|---|
| TUI 渲染 / Compact 模式 | 已有内部 owner（`chiga0/ChiGao`），外部 PR 易被抢先 |
| 终端协议 / MCP OAuth | 已有内部 owner（`Edenman/BZ-D`） |
| Phase-N 大型重构 | 内部团队领地（`顾盼` / `tanzhenxin`） |
| revert 已合并的 PR | 内部决策权 |
| 大型架构提议 | 不会被 review |

---

## 附录

### A. 数据采集方法

```bash
# 总 commit 与作者数
cd /root/git/qwen-code
git log --since="2026-04-01" --no-merges --pretty=format:"%an|%ae" | sort -u | wc -l   # → 48
git log --since="2026-04-01" --no-merges --pretty=format:"%H" | wc -l                  # → 464

# 每位贡献者 commit 数
git log --since="2026-04-01" --no-merges --pretty=format:"%an" | sort | uniq -c | sort -rn

# 单一作者所有 PR
git log --since="2026-04-01" --no-merges --author="<NAME>" --pretty=format:"%s"
```

### B. 修订历史

- **v3 (2026-04-28)** · 改进可读性
  - 新增 TL;DR 一句话结论 + 速查表
  - 引入视觉条形图（commit 分布）
  - 简化方法论部分（从 verbose 表格改为信号清单）
  - 合并贡献模式（6→5），删除重复段落
  - 单点贡献者用 4 类小表格替代长列表
  - 数据更新到 2026-04-28（commits 441→464）

- **v2 (2026-04-27)** · 用户反馈勘误
  - `chiga0/ChiGao`、`Edenman/BZ-D` 从外部移到内部专精团队
  - 外部 commit 占比 14% → 11%
  - 加 email-based 识别局限性警告

- **v1 (2026-04-27)** · 初版

### C. 相关文档

- [Qwen Code 改进报告](./qwen-code-improvement-report.md)
- [Qwen Code OpenCode 对标](./qwen-code-opencode-improvements.md)
- [Qwen Code Gemini upstream backport](./qwen-code-gemini-upstream-report.md)

---

**最后更新**：2026-04-28 · **数据窗口**：2026-04-01 → 2026-04-28
