# Qwen Code 外部贡献者分析

> 基于 `git log --since="2026-04-01"` 的 441 个 commit、48 位贡献者数据。
>
> **目的**：识别**真正来自外部社区**的贡献者及其贡献模式，区别于 Alibaba 内部团队主导开发。这对理解 Qwen Code 的项目治理模式、社区健康度、以及哪些方向上社区参与度高有参考价值。

## 一、内外部分类方法

由于很多核心维护者使用个人邮箱（如 tanzhenxin 用 `gmail.com`，顾盼用 `gmail.com`），单看 email 域名无法准确判断。本分析综合以下信号：

| 信号 | 内部判定权重 | 外部判定权重 |
|---|:-:|:-:|
| `@alibaba-inc.com` / `@aliyun.com` email | 强 | — |
| `@service.alibaba.com`（bot） | 强 | — |
| 中文 commit 显示名（如 `易良` `顾盼` `思晗`）| 中 | — |
| 高频 commits + 跨包架构改动 | 中 | — |
| Phase-N 重构 + revert 把关 | 中 | — |
| 单一专精方向 + 短期爆发期 | — | 强 |
| 国际 i18n 语言贡献 | — | 强 |
| 学术机构邮箱（`.edu` / `.edu.cn`） | — | 强 |
| 深度 niche 修复（终端协议 / OAuth / 沙箱） | — | 中 |

**别名合并**：通过相同 email 识别同一人不同显示名 ——
- `易良` = `yiliang114` = `mingholy.lmh`（同 `1204183885@qq.com`）
- `顾盼` = `LaZzyMan`（同 `zeusdream7@gmail.com`）
- `wenshao` = `Shaojin Wen`（同 `shaojin.wensj@alibaba-inc.com`）
- `chiga0` ≠ `ChiGao`（不同 email：`gary.gao12580@gmail.com` vs `arno.ga0@outlook.com` —— 但提交时间紧邻 + 都做 TUI 改进，可能同一人多设备/多账号）

**⚠️ 方法论局限性提示**（2026-04-27 修订）：本分析早期版本曾把 `chiga0/ChiGao` 与 `Edenman/BZ-D` 误判为外部贡献者，因为他们使用个人 gmail / github noreply 邮箱。**经核实他们均为 Alibaba 内部贡献者**。这反映出：

1. **email 域名识别极不可靠** —— 内部工程师常用个人邮箱做 github contribution，特别是阿里系工程师
2. **正确判定需要直接确认** —— 仅靠 commit metadata 推测内/外部存在系统性误判风险
3. **下文表格已更新** —— chiga0/BZ-D 移出"外部"分类；其他**未确认人员仍标注"推测"**，以避免再次误判

---

## 二、确认外部社区贡献者（2026-04 活跃）

### 🥇 第一梯队 · 高产 / 高影响（3 人）

#### 1. **chinesepowered** (John London) · 21 commits

| 维度 | 信息 |
|---|---|
| **GitHub** | `chinesepowered` |
| **Email** | `nlai@rediffmail.com`（rediffmail = 印度邮件服务） |
| **显示名** | "John London" |
| **focus** | 跨子系统 quick fix · sandbox / SDK / channels / weixin / dingtalk / scripts / integration-tests |
| **代表 PR** | PR#2981 SDK Stream.return() 防 hang · PR#2975 channels 桥接 disconnect handler 重连 · PR#2970 weixin 4-byte PNG magic · PR#2962 sandbox latest tag fallback · PR#2979 dingtalk reactionContext 内存泄漏 |
| **特征** | **集中爆发期**（PR#2962-#2981 同期合并）—— 看上去是了解全栈的资深开发者一次性贡献多个深度修复，可能是用户报告 bug 后做了 ~20 个 PR 集中清理 |
| **重要性** | 是少数能在 sandbox / SDK / channels 等**底层基础设施**上做实质修复的外部贡献者 |

#### 2. **euxaristia** · 5 commits

| 维度 | 信息 |
|---|---|
| **GitHub** | `euxaristia` |
| **focus** | Loop detection / 错误恢复 / build infra |
| **代表 PR** | **PR#3236 enhanced loop detection with stagnation + validation-retry checks** · **PR#3178 detect tool validation retry loops + inject stop directive** · PR#2857 shell output 宽度约束 · PR#3237 build 用 `node --import tsx` 替代 npx |
| **特征** | **错误恢复机制核心改进者**——loop 检测是 agentic 系统稳定性关键 |
| **重要性** | 命中 codeagents item-27（错误恢复分类路由）的相关方向 |

#### 3. **John London** · 4 commits（与 chinesepowered 显示名相同但**不同人**）

| 维度 | 信息 |
|---|---|
| **GitHub** | `benevolentjoker@gmail.com` |
| **focus** | Config refactor |
| **代表 PR** | **PR#3653 refactor(config): dedupe QWEN_CODE_API_TIMEOUT_MS env override**（PR#3629 follow-up cleanup）+ 几个其他 refactor |
| **注意** | **与 `chinesepowered`（也叫 John London）邮箱不同** —— 这是另一个独立贡献者，不是同一人 |

---

### 📌 已纠正分类（原误判为外部）

下列贡献者**经确认为 Alibaba 内部团队成员**，使用个人邮箱做 github contribution（这是阿里系工程师常见做法）。从外部分类移到内部团队：

| 贡献者 | commits | 误判依据 | 实际身份 | 重要贡献 |
|---|:-:|---|---|---|
| **chiga0 / ChiGao** | 6 | gmail/outlook 个人邮箱 | **内部 TUI 渲染负责人** | PR#3013 SlicingMaxSizedBox + PR#3591 flicker foundation + PR#3352 dual-output sidecar + PR#3100 compact mode UX |
| **Edenman / BZ-D** | 5 | github noreply 邮箱 | **内部终端协议 + MCP OAuth 负责人** | PR#3460 OSC 11 主题检测 + PR#3489 OAuth URL 可点击 + PR#3442 mcp add OAuth flag + PR#3393 OSC 52 复制热键 |

**这是该方向 Alibaba 内部分工的关键信号**：TUI 渲染（chiga0/ChiGao）和终端协议（Edenman/BZ-D）是被分配给**特定专精工程师**而非通用维护者，反映 Phase-N 重构里这些子领域有专门 owner。

---

### 🥈 第二梯队 · i18n 国际化贡献者（3 人）

显示项目国际化吸引力 —— 这些 PR 都很小但代表非中文用户的实际投入：

| 贡献者 | 国家/地区 | 贡献 |
|---|---|---|
| **Jordi Mas** (jmas@softcatala.org) | 🇪🇸 Catalonia | **PR#3643 Adds Catalan language support** —— softcatala.org 是加泰罗尼亚开源本地化组织 |
| **MikeWang0316tw** (br70316@gmail.com) | 🇹🇼 Taiwan | **PR#3569 Traditional Chinese (zh-TW)** —— `tw` 后缀 + 繁中需求 |
| **Lassana siby** | 🌍 非洲（推测） | PR#3126 French (fr-FR) locale support |

---

### 🥉 第三梯队 · 单点贡献者（聚焦 1-2 项功能）

#### 重要单点贡献

| 贡献者 | 主要 PR | 影响 |
|---|---|---|
| **Yan Shen** (shenyankm@gmail.com) | **PR#3507 sticky todo panel** + PR#3270 Tab 输入忽略 | sticky todo 是重要 UI 功能，对标 Claude Code |
| **dreamWB** | PR#3477 vscode 原生 context menu copy | VSCode UX |
| **Dragon (DragonnZhang)** | PR#3593 `argument-hint` for slash commands | slash UX |
| **gin-lsl** | PR#2734 WebFetch Markdown for Agents | WebFetch 改进 |
| **Gordon Lam** | PR#3458 OpenAI samplingParams verbatim | provider 兼容 |
| **Fu Yuchen** | PR#3590 reasoning_content 在 resume + active session 保留（GH#3579）| Thinking 块修复，关联 item-22 |
| **apophis** | PR#2942 CJK 词分割 with Intl.Segmenter | 中日韩文本处理 |
| **harsh** (Ojhaharsh) 🇮🇳 | PR#3481 qwenOAuth2 错误处理 + PR#1675 xdg-open graceful 降级 | 错误处理 |
| **Sharvil Saxena** (sharziki) 🇮🇳 | PR#3431 `/clear` 取消 `/btw` 对话 | UX 边角 |
| **Pedro Ribeiro Mendes Júnior** 🇧🇷 | PR#3358 `M-d` Emacs 风格绑定 | 键盘快捷键 |
| **Viktor Szépe** (viktor@szepe.net) 🇭🇺 | PR#2189 typo fix | typo |
| **YuchenLiang00** (清华学生) | `/context detail` 子命令 | context 工具增强 |
| **chaoliang yan** (UNSW Australia) | PR#3543 sdk-java 自定义 env 传递 | Java SDK |
| **lamb** (gy1016) | PR#3303 macOS Zed 编辑器检测（CLI 不在 PATH）| 编辑器集成 |
| **joeytoday** | PR#3325 docs OAuth discontinuation | docs |
| **ihubanov** | PR#3445 `slashCommands.disabled` 设置 | 配置 |
| **克竟** | PR#3051 防止 Shift+Tab 接受 prompt placeholder | 键位修复 |
| **pikachu** (pic4xiu) | PR#3046/#3321 update notifications 推迟到 model response 后 | UX 时序 |
| **Richard Luo** | PR#3252 Windows install 命令兼容 CMD/PowerShell | docs |
| **YingchaoX** | vim normal mode `?` shortcut 恢复 | vim |
| **feyclaw** | PR#3150 Telegram 适配器语音消息支持 | channels |
| **evan70** | PR#2865 normalize-package-data 升 7.0.1 | dep upgrade |

---

## 三、统计数据

### 内外部 commit 占比

```
总 commit (2026-04):         441
内部 (alibaba-inc.com 邮箱):    4 人
推测内部/紧密合作（中文显示名 + gmail/qq）:  ~10 人
外部社区贡献者:               ~30+ 人
```

### 真正外部贡献者总 commit 量

```
chinesepowered:    21
euxaristia:         5
John London:        4
其他单点贡献:    ~20+
小计:           ~50+ commits（约占总量 11%）

[勘误] 原版本误把 chiga0/ChiGao (6) + Edenman/BZ-D (5) 计入外部，
经确认这两位是 Alibaba 内部贡献者，故从外部分类移除。
```

### 国际化覆盖

| 语言 | 状态 | 贡献者 |
|---|---|---|
| 简体中文 | 内置 | Alibaba 团队 |
| 英文 | 内置 | Alibaba 团队 |
| **繁体中文** | ✓ PR#3569 | MikeWang0316tw 🇹🇼 |
| **加泰罗尼亚语** | ✓ PR#3643 | Jordi Mas 🇪🇸 |
| **法语** | ✓ PR#3126 | Lassana siby 🌍 |
| 日语 / 韩语 / 西语 / 葡语 / 德语 / 俄语 | 待 | — |

---

## 四、外部贡献者贡献模式分析

### 模式 1：niche 协议专家（如 Fu Yuchen 单点 / harsh）

**特征**：在某个**狭窄技术域**（OAuth flow / TLS / sandboxing / 错误处理）做深度修复或新功能。

**为什么重要**：内部团队往往不会专注到这种 niche，但用户实际使用时这些 niche 经常爆雷。

**代表 PR**：Fu Yuchen 的 PR#3590（reasoning_content resume 修复）/ harsh 的 PR#3481（qwenOAuth2 错误处理）

> **注**：Qwen Code 内部其实有专门的 niche 协议负责人（如 chiga0/ChiGao 负责 TUI 渲染、Edenman/BZ-D 负责终端协议 + MCP OAuth）—— 这与 Claude Code 这类有专精团队的项目类似。外部 niche 协议专家相对稀少。

### 模式 2：度量驱动重构（如 euxaristia）

**特征**：发现**性能/正确性 bug** → 写复现 → 写修复 → 带 benchmark/度量数据 → PR

**为什么重要**：这种贡献质量高，往往超出内部团队的优先级排序。

**代表 PR**：euxaristia 的 PR#3236（loop detection stagnation 检测）+ PR#3178（validation retry 循环检测）

### 模式 3：补丁集中爆发期（如 chinesepowered）

**特征**：某个开发者**短时间内**（几天到一周）集中提交 10+ PR，覆盖多个不相关子系统。

**推测原因**：
- 公司内部使用 Qwen Code 时遇到一系列 bug，攒批一次性贡献
- 个人项目踩坑后做了一次集中清扫

**代表**：chinesepowered 的 PR#2962-#2981 集群

### 模式 4：i18n 长尾贡献

**特征**：单 PR 只加一个语言文件，几乎不与代码逻辑交互

**重要性**：这是项目国际化的**唯一可持续路径** —— 内部团队不可能维护所有语言。

### 模式 5：学生 / 研究者贡献（如 YuchenLiang00 清华, chaoliang yan UNSW）

**特征**：学术机构邮箱 + 单 PR 贡献，方向偏 niche 功能（detail subcommand / sdk-java）

**重要性**：低 commit 量但显示项目对学术圈有吸引力，长期可能演化为更深参与

### 模式 6：双向 spec/impl 闭环（如 wenshao 个人）

**特征**：同一人既维护 codeagents spec 仓库，又在 qwen-code 仓库实现 spec 中的项

**例子**：item-28 Skill 装载性能优化 spec → PR#3604 实现（PR body 显式引用）

**重要性**：稀有但极有价值——形成"提案 → 设计 → 实现"的快速反馈循环。

---

## 五、关键观察

### ✅ 健康信号

1. **核心功能 niche 由内部专精团队覆盖**：TUI 渲染（chiga0/ChiGao）、终端协议（Edenman/BZ-D）等关键路径是内部专精工程师而非通用维护者负责，反映团队成熟度
2. **外部 loop 检测 / 错误恢复有持续参与**：euxaristia 等外部贡献者在 agentic 系统稳定性核心路径有实质改进（PR#3236 / PR#3178）
3. **多元国家/地区参与**：印度、巴西、匈牙利、加泰罗尼亚、台湾、澳大利亚、中国大陆都有贡献者
4. **学术机构参与**：清华、UNSW 学生开始贡献 —— 项目对教育市场有吸引力

### ⚠️ 风险信号

1. **核心架构基本全由 Alibaba 内部主导**：Phase 重构（顾盼）、revert 决策（tanzhenxin）、TUI 渲染（chiga0/ChiGao）、终端协议（Edenman/BZ-D）、内部团队（思晗 / 胡玮文 等）—— 几乎所有架构方向都由内部决定
2. **外部贡献集中在 fix/ 而非 feat/**：除 chinesepowered 集中爆发期外，多数外部贡献是 bug fix 或小功能，缺架构级提议
3. **Top 外部贡献者匿名度高**：chinesepowered 显示名 "John London" 但 email 是印度邮件服务，真实身份不透明 —— 不利于社区信任建立
4. **i18n 长尾断层**：日韩西葡德俄等大语种均缺贡献者，繁中也只有一个 PR
5. **"双重身份" 贡献者罕见**：wenshao 是孤例 —— 同时熟悉 spec 与 impl 的贡献者稀缺，影响项目知识传播
6. **email-based 内/外部识别不可靠**：本报告早期版本曾误把 chiga0/BZ-D 等内部工程师识别为外部，反映项目对外缺少**正式贡献者身份标记机制**（如 CODEOWNERS / 维护者列表 / 头衔徽章）

### 与 Claude Code / Codex / OpenCode 比较

| 项目 | 治理模式 | 外部贡献占比（估算） |
|---|---|---|
| **Claude Code** | Anthropic 内部封闭，无外部 commit（仅闭源 binary）| 0% |
| **Codex** | OpenAI 内部主导，外部 PR 少 | ~10% |
| **Gemini CLI** | Google 主导 + Apache-2.0 + 大量外部贡献 | ~30%? |
| **OpenCode** | sst（创始人 Dax）+ 紧密小团队 + 中等外部 | ~20% |
| **Qwen Code** | Alibaba 主导 + 比 Codex 更开放 + 国际 i18n | ~14% commit / ~60% 贡献者数 |

**Qwen Code 的位置**：开放程度介于 OpenCode（开放但小）和 Gemini CLI（高度开放）之间。比 Codex / Claude Code 更外向。

---

## 六、对外部贡献者的建议（从外部视角看 Qwen Code）

如果你是想给 Qwen Code 贡献的外部开发者，参考已有外部贡献模式：

| 想做什么 | 建议参考 |
|---|---|
| 终端协议 / OAuth / sandboxing 等 niche | ⚠️ **此方向已有内部专精团队**（chiga0/ChiGao 做 TUI 渲染、Edenman/BZ-D 做终端协议 + MCP OAuth），外部贡献需找他们未覆盖的边角，否则容易被内部 PR 抢先 |
| TUI 性能 / 渲染 | ⚠️ **同上**，建议避开此方向，转向更专精的子领域（如某个特定终端的兼容性修复）|
| 错误恢复 / loop 检测 | euxaristia 模式 —— 发现现实问题 + 系统化方案 |
| i18n | Jordi Mas 模式 —— 单 PR 加一个语言文件 |
| 学习/学生项目 | YuchenLiang00 模式 —— 选一个 `/<command>` 的小子功能 |
| 跨子系统 quick fix | chinesepowered 模式 —— 集中扫荡多个 bug 一次性 PR |

避免：
- ❌ 大型架构提议（不会被 review）
- ❌ Phase 级重构（属于内部团队领地）
- ❌ revert 已合并的内部 PR（除非你能 100% 论证为 bug）

---

## 七、数据来源与方法论

```bash
# 总 commit 与作者数
cd /root/git/qwen-code
git log --since="2026-04-01" --no-merges --pretty=format:"%an|%ae" | sort -u | wc -l   # → 48
git log --since="2026-04-01" --no-merges --pretty=format:"%H" | wc -l                  # → 441

# 内部判定：alibaba-inc.com / service.alibaba.com email
# 同别名合并：按 email 分组识别 wenshao=Shaojin Wen / 易良=yiliang114=mingholy.lmh / 顾盼=LaZzyMan

# 外部贡献者每人 commit 数
for author in <list>; do git log --since="2026-04-01" --author="$author" --oneline | wc -l; done
```

---

**最后更新**：2026-04-27（修订：chiga0/ChiGao + Edenman/BZ-D 从外部分类移到内部团队）
**数据窗口**：2026-04-01 → 2026-04-27（27 天）
**相关文档**：[Qwen Code 改进报告](./qwen-code-improvement-report.md) · [Qwen Code 维护者画像（参见近期对话记录）]

## 修订历史

- **2026-04-27 v2**：用户反馈纠正 —— `chiga0/ChiGao`（TUI 渲染负责人）和 `Edenman/BZ-D`（终端协议 + MCP OAuth 负责人）实际为 Alibaba 内部贡献者，非外部社区。本次修订：
  1. 第二章移除这两位的 Tier 1 条目，新增"已纠正分类"区块说明
  2. 第三章统计数据：外部 commit 数从 ~60+（14%）下调至 ~50+（11%）
  3. 第四章贡献模式：移除"chiga0/ChiGao + BZ-D = niche 协议专家"误导引用
  4. 第五章健康/风险信号：增加"email-based 识别不可靠"作为新风险信号
  5. 第六章对外部贡献者建议：标注 TUI 渲染 + 终端协议方向**已有内部专精团队**，外部需避开
  6. 第一章方法论增加局限性提示
- **2026-04-27 v1**：初版基于 git log 数据创建
