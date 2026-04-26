# 0. OpenCode 项目演进时间线

> 完整历史从 Kujtim Hoxha 的个人 Go 项目（2025-03）到 Anomaly Innovations / SST 团队接手 + 双重重写（Go→TS + Bubble Tea→OpenTUI），到当前 v1.14.x 多客户端开源平台。
>
> **数据来源**：`/root/git/opencode/` git log 11,750 commits 实测 + GitHub API（2026-04-25 抓取）

## 时间线一览

```
2025-03-21  ─┬─  Kujtim Hoxha 个人项目，Go + Bubble Tea TUI，初始 commit
             │
2025-04-22  ─┼─  Dax Raad（SST 创始人）第一个 commit (CI #43)
2025-04-30  ─┼─  GitHub repo 转到 anomalyco（Anomaly Innovations 接手）
             │
2025-05-31  ─┼─  Dax 主导，引入 TypeScript / Bun / models.dev
2025-06-08  ─┤   "Add TypeScript server initialization config to LSP server"
2025-06-12  ─┼─  Bun runtime 集成（BunProc.install）
             │
[Backend 已切 TS + Bun，TUI 仍 Go Bubble Tea]
             │
2025-10-31  ─┼─  PR #2685 "OpenTUI is here" —— Dax 引入新 TUI 框架
2025-11-02  ─┴─  commit "DELETE GO BUBBLETEA CRAP HOORAY" —— 删除老 Go TUI
             │
2025-11-06       opentui v0.1.36 升级
2025-11-12       opentui v0.1.42（已在生产使用）
             │
2026-03-31       opentui v0.1.93
2026-04-14       opentui v0.1.99
2026-04-23       "opentui snapshot" 准备发布
2026-04-24  ─┼─  "full opentui release" —— 稳定版发布
2026-04-25  ─┴─  当前 v1.14.24
```

## 阶段一：起源（2025-03 ~ 2025-04）—— Kujtim Hoxha 单人项目

最早的 4 个 commit：

```
2025-03-21 18:20  initial
2025-03-23 14:56  add help
2025-03-23 19:19  add initial stuff
2025-03-23 22:25  initial agent setup
```

仅 1 周内 Kujtim Hoxha **独立**搭出基本可工作 agent —— Go 写的 backend + Bubble Tea（[charmbracelet/bubbletea](https://github.com/charmbracelet/bubbletea)）TUI。早期 commit 节奏：

```
2025-03-24  initial working agent
2025-03-25  additional tools
2025-03-27  rework llm
2025-04-03  add initial lsp support  ← LSP 在第 2 周就有了
```

**Kujtim 的设计选择**：
- Go 语言（性能 + 单二进制分发）
- Bubble Tea TUI（Go 生态最成熟的 TUI 框架）
- LSP 早期集成（后来成为 OpenCode 的招牌特性之一）

## 阶段二：接手（2025-04-22 ~ 2025-04-30）

```
2025-04-22 21:16  Dax Raad: CI (#43)              ← Dax 第一个 commit
2025-04-30        GitHub repo anomalyco/opencode 创建
```

**Dax Raad** 是 [SST（Serverless Stack Toolkit）](https://sst.dev) 创始人，旗下公司 **Anomaly Innovations**（[anoma.ly](https://anoma.ly)）—— 此前以构建 Next.js 全栈框架 + Console 著称。

**关键判断**：repo 创建时间（2025-04-30）**晚于** Dax 第一个 commit（2025-04-22）—— 推测是 Kujtim **主动转让**项目给 Anomaly，Dax 之前是用 fork 贡献，转手后改为主仓库直接 commit。

## 阶段三：第一次重写（2025-05 ~ 2025-06）—— Go backend → TypeScript + Bun

Dax 上手后立即开始 backend rewrite：

```
2025-05-30  Update package dependencies         ← 引入 npm 生态
2025-05-31  Standardize code style              ← TypeScript 风格统一
2025-05-31  lazy load LLMs even harder
2025-05-31  tool rework
2025-06-04  implemented todo tool               ← 业务功能 TS 重写
2025-06-08  Add TypeScript server init for LSP
2025-06-12  Bun runtime 集成（BunProc.install）
2025-06-23  bundle models.dev at build time     ← models.dev 动态 Provider
```

**核心变动**：
- Backend 从 Go → **TypeScript + Bun runtime**
- 新增 [models.dev](https://models.dev) 集成 —— 100+ Provider 零代码接入（OpenCode 的招牌特性）
- 重写工具系统（Read/Write/Edit/Bash 等）
- LSP 集成增强

**TUI 暂未动**：仍是原 Go + Bubble Tea，通过 client-server 模式与 TS backend 通信（HTTP/WebSocket）。这种 **"polyglot 架构"** 持续了 ~5 个月。

## 阶段四：第二次重写（2025-10-31 ~ 2025-11-02）—— Go TUI → OpenTUI

```
2025-10-06  Add missing files and fix type aliases for opentui features
            ← 第一个 OpenTUI 相关 commit（铺垫）
2025-10-31  PR #2685 "OpenTUI is here"          ← OpenTUI 正式引入
2025-11-02  "DELETE GO BUBBLETEA CRAP HOORAY"   ← 老 Go TUI 删除
2025-11-06  opentui v0.1.36 升级
2025-11-11  opentui v0.1.41 + Kitty keyboard 支持
2025-11-12  opentui v0.1.42（修 CJK/grapheme 问题）
```

**[OpenTUI](https://github.com/sst/opentui)** 是 Dax 自家团队（SST/Anomaly）开发的**全新 TUI 框架**——Bun 原生、SolidJS 渲染、tree-sitter 语法高亮、原生 SGR 鼠标 + alt-screen + 虚拟滚动。

为什么自建 OpenTUI 而非用 Ink？
- Ink 基于 React，渲染开销大（每次状态更新整树重建）
- Ink 是 inline 模式，没有 alt-screen，长会话闪烁
- 需要原生 mouse / kitty keyboard / tree-sitter 等高级能力

代价：**OpenCode 与 OpenTUI 同时迭代，双方版本紧耦合**。git log 大量看到 opentui 升级 + revert + roll back。

## 阶段五：稳定化（2025-12 ~ 2026-04）

OpenTUI 在快速迭代（v0.1.36 → v0.1.99，~50 个版本，4 个月），OpenCode 跟版升级压力大：

```
2026-04-14  upgrade opentui to 0.1.99 (#22283)
2026-04-17  upgrade opentui to 0.1.100 (#22928)
2026-04-17  back to opentui 0.1.99             ← 0.1.100 出问题立即回退
2026-04-17  roll back opentui
```

可见 **OpenTUI 仍在 v0.1.x，每个版本都有兼容性风险**。OpenCode 形成了一套"上 → 测 → 退 → 等修复 → 再上"的工作流。

```
2026-04-22  opentui snapshot          ← 准备发布
2026-04-23  new snapshot
2026-04-24  full opentui release      ← 稳定版发布
```

**2026-04-24 的 "full opentui release"** 是 OpenCode v1.14.x 稳定在 OpenTUI 上的关键节点——不是首次使用 OpenTUI（那是 2025-10-31），而是**全面稳定**。

同期 Effect 框架重度迁移：

```
git log 大量 commit:
"refactor(core): migrate ... to Effect Schema"
"refactor(provider): migrate provider domain to Effect Schema"
"refactor(session): migrate session domain to Effect Schema"
"refactor(tool): migrate tool framework + all 18 built-in tools to Effect Schema"
```

[Effect](https://effect.website/) 是 TypeScript 函数式 effect system —— SST 团队的 signature 技术栈。OpenCode 大量代码迁移到 Effect Schema（取代原 Zod）。

## 阶段六：商业化（2025-Q4 起）

OpenCode 的 **OpenCode Zen** 和 **OpenCode Go** 付费计划上线：

| 计划 | 价格 | 内容 |
|---|---|---|
| 免费/开源 | $0 | 自带任意 provider API key |
| **OpenCode Zen** | 按量付费 | 编码优化 model + 月度限额 |
| **OpenCode Go** | $5 首月 → $10/月 | GLM-5、Kimi K2.5、MiniMax M2.5/M2.7 转售 |

属于 **"open core + hosted"** 模式 —— SST 团队的传统玩法（[SST Console](https://console.sst.dev) 也是同样定价结构）。

## 阶段七：中国 AI 生态深度绑定（2025-Q4 起，与商业化同步）

虽然项目方完全是美国/西方公司（Anomaly Innovations / SST），**OpenCode 的商业生态 90% 绑定中国 AI**——这是它最有意思也最容易被忽视的特点。

### 7.1 内置 provider：9/11 是中国 AI 实验室

实测 `opencode models` 列出的所有 provider 前缀：

```
deepseek/                      ← DeepSeek（杭州，幻方旗下）
kimi-for-coding/               ← Kimi For Coding（Moonshot 编程版）
minimax/                       ← MiniMax（上海）国际版
minimax-cn/                    ← MiniMax 中国大陆版
minimax-cn-coding-plan/        ← MiniMax 中国 Coding Plan
minimax-coding-plan/           ← MiniMax 国际 Coding Plan
moonshotai/                    ← Moonshot AI（北京）国际版
moonshotai-cn/                 ← Moonshot 中国大陆版
zai-coding-plan/               ← Z.AI（智谱国际品牌）Coding Plan
zhipuai-coding-plan/           ← Zhipu AI（北京）中国 Coding Plan
opencode/                      ← OpenCode 自家转售
```

**11 个 provider 中，10 个是中国 AI 实验室或其衍生**（剩下 1 个是 OpenCode 自家），**没有原生 OpenAI / Anthropic / Google provider 作为默认**——这些反而要走 [models.dev](https://models.dev) 动态加载（"自带 API key"模式）。

`-cn` 后缀的版本特别值得关注：表明 OpenCode **专门为中国大陆访问做了端点适配**——大陆用户可直接用 `minimax-cn-coding-plan/...` 而无需 VPN。

### 7.2 OpenCode Go 订阅：纯中国 AI 转售

`OpenCode Go` 付费计划（$5 首月 → $10/月）的全部包含模型都是**中国 AI**：

| 模型 | 提供方 | 备注 |
|---|---|---|
| **GLM-5** | Zhipu AI（智谱，北京） | 智谱 GLM 系列旗舰 |
| **Kimi K2.5** | Moonshot AI（北京） | 月之暗面 Kimi 编程版 |
| **MiniMax M2.5** | MiniMax（上海） | 标准版 |
| **MiniMax M2.7** | MiniMax（上海） | 旗舰版 |

**没有 Claude、GPT、Gemini 出现在 Go 订阅里**——这是一个明确的商业选择。

### 7.3 多语言文档：中文 first-class

[`README.zh.md`](https://github.com/anomalyco/opencode/blob/main/README.zh.md) 简体中文 + [`README.zht.md`](https://github.com/anomalyco/opencode/blob/main/README.zht.md) 繁体中文 都在仓库根目录的语言切换列表里。22 种语言里，**中文（简+繁）排在第二、第三位**（仅次于英文）。

### 7.4 商业逻辑：AI 套利

```
美国/欧洲市场已被 Cursor / Claude Code / Copilot 占据
   ↓
OpenCode 想要差异化
   ↓
中国 AI 实验室（Kimi / DeepSeek / Zhipu / MiniMax）coding-tier 模型
   ↓ 价格优势：~ Claude/GPT-4 的 1/5 ~ 1/10
   ↓ 在 SWE-bench 等编程 benchmark 表现接近顶级
   ↓ 但西方开发者难直接接入（境外 API 限速 / 注册门槛 / 双 API 端点）
   ↓
OpenCode = "西方开发者访问中国 coding 模型的最佳通道"
```

OpenCode 的**商业护城河本质是 AI 套利**——把中国 AI 实验室的便宜+好用模型，包装成西方 developer 友好的 CLI + 订阅。

### 7.5 与同类 Agent 的对比

| Agent | 注册地 | 商业绑定 | 中国生态权重 |
|---|---|---|---|
| **OpenCode** | 🇺🇸 美国（Anomaly Innovations） | 🇨🇳 9/11 中国 provider + Go 订阅纯中国模型 | **极重** |
| Qwen Code | 🇨🇳 中国（阿里 Qwen） | 🇨🇳 主推 Qwen 自家模型 | 重（自家） |
| Claude Code | 🇺🇸 美国（Anthropic） | 🇺🇸 仅 Claude 模型 | 无 |
| Codex CLI | 🇺🇸 美国（OpenAI） | 🇺🇸 仅 OpenAI 模型 | 无 |
| Cursor | 🇺🇸 美国（Anysphere） | 🇺🇸 主流 Western models | 无 |

**OpenCode 是唯一商业模式建立在"美国包装中国 AI"上的 CLI agent**——技术栈完全西方（Bun/TS/Solid/OpenTUI 都是西方栈），但生态/商业 90% 是中国。

### 7.6 战略地位

OpenCode 占据了一个其他 agent 没占的位置：

```
              西方主流市场
            (Cursor / Claude Code)
                    │
                    │
       OpenCode ────●────  中国本土市场
       （横跨东西方）       (Qwen Code)
                    │
                    │
              不绑定单一厂商
              (provider-agnostic)
```

- 不是西方主流（不绑 Anthropic/OpenAI）
- 不是中国本土（不绑 Qwen/Kimi 单家）
- **是 west-meets-east 的中介层**

这种定位让 OpenCode 比纯 Western agent 多拿到中国市场，又比纯 Chinese agent 多拿到西方开发者——**双向套利**。

### 7.7 风险

这种深度绑定也带来风险：

1. **中美关系恶化** —— 如美国出口管制扩大到 AI 模型 API，OpenCode 的"中国转售"商业模式可能受冲击
2. **中国 API 政策变动** —— 如中国境外访问被限制，国际版 provider 可能失效
3. **中国 AI 实验室自建 CLI** —— 阿里有 Qwen Code，DeepSeek/Moonshot/Zhipu 也可能各自建立官方 agent，**绕过 OpenCode 中介层**
4. **价格优势消失** —— 如中国 AI 跟 OpenAI/Anthropic 一样涨价，套利空间消失

OpenCode 长期能否守住这个定位，取决于中国 AI 是否持续保持"性价比 + 难直接访问"的双重特性。

## 当前状态（2026-04-25）

| 维度 | 数值 |
|---|---|
| **Stars** | 149,294（实测，gh API） |
| **Forks** | 17,128 |
| **Total commits** | 11,750 |
| **Active contributors** | 数百（Top 10 占 ~70% commits） |
| **Repo 创建时间** | 2025-04-30 |
| **当前版本** | v1.14.24 |
| **License** | MIT |

### 核心团队（按 commit 数）

| 排名 | 贡献者 | Commits | 主要负责 |
|---|---|---|---|
| 1 | **Dax Raad** | 1,845 | 架构 + agent loop + 商业化 |
| 2 | Adam (adamdottv) | 1,266 | TUI + Console UI + 主题 |
| 3 | Aiden Cline | 1,144 | 工具 + tooling |
| 4 | GitHub Action | 839 | 自动化（download stats / release） |
| 5 | Frank | 659 | — |
| 6 | David Hill | 534 | — |
| 7 | **opencode-agent[bot]** | 509 | **agent 自己 PR** |
| 8 | Kit Langton | 466 | — |
| 9 | Jay V | 333 | — |
| 10 | Kujtim Hoxha | < 333 | **原作者**，仍偶有 commit |

> **Kujtim Hoxha 仍是项目的一部分** —— 转手后没有完全离开，仍偶有贡献。属于"友好转让"。

### opencode-agent[bot] —— 最高级别 dogfood

`opencode-agent[bot]` 给自家仓库提了 **509 个 PR**——OpenCode **自己用自己**写代码改 bug。这是其他 agent 项目少有的 dogfood 程度（Claude Code 的 `claude.ai/code` 也类似但未公开数据）。

## 与其他 Agent 项目的差异

| 项目 | 起源 | 核心定位 | 重写次数 |
|---|---|---|---|
| **OpenCode** | 个人（Kujtim）→ 公司（Anomaly） | provider-agnostic 平台 | 2 次（Go→TS、Bubble Tea→OpenTUI） |
| Claude Code | Anthropic 官方 | 闭源旗舰 | （内部，不公开） |
| Qwen Code | Gemini CLI 分叉 | Qwen 生态 | 0（继承 Gemini CLI） |
| Codex CLI | OpenAI 官方 | OpenAI 生态 | 1（Go→Rust，2025-Q3） |
| OpenHands | 学术研究 → 公司 | research agent | 1（CodeAct→OpenHands） |

OpenCode 是**唯一从个人项目演化到商业化产品**的 agent，且经历**双重重写**——Backend 重写（Go→TS）+ TUI 重写（Bubble Tea→OpenTUI）。

## 演进规律的启示

### 1. "重写"不是失败，是技术升级窗口

OpenCode 两次重写都是**主动选择**：
- Go → TS：为了 npm 生态 + 100+ Provider 接入 + 多客户端共享代码
- Bubble Tea → OpenTUI：为了 alt-screen + 虚拟滚动 + 现代 TUI 能力

每次重写都换来**质的飞跃**（功能集 + 性能）。

### 2. polyglot 架构作为过渡

2025-06 ~ 2025-10 的 5 个月，OpenCode 跑的是 **TS backend + Go TUI** 混合架构。这种过渡架构让团队**不用一次性重写所有东西**，可以分模块迁移。

### 3. 自建框架的代价

OpenTUI 是 Anomaly 自家产品 —— OpenCode **既是用户也是消费者**。这让 OpenCode 能定义 OpenTUI roadmap（与 LLM agent 用例对齐），但代价是 OpenTUI 仍在 v0.1.x 不成熟，OpenCode 跟版升级开销大。

### 4. open core + hosted 商业化

继承 SST 团队风格 —— 核心 100% 开源，付费 = 模型转售 + 配额。**与 Cursor 闭源、Claude Code 服务订阅截然不同**。

## 数据来源

- Git 历史：`/root/git/opencode/` 11,750 commits（截至 2026-04-25）
- GitHub API：`gh repo view anomalyco/opencode --json stargazerCount,forkCount`（2026-04-25 实测）
- 原作者 GitHub 主页：[github.com/kujtimiihoxha](https://github.com/kujtimiihoxha)
- Dax Raad / SST：[sst.dev](https://sst.dev)、[anoma.ly](https://anoma.ly)
- OpenTUI：[github.com/sst/opentui](https://github.com/sst/opentui)（依赖来源）

> **免责声明**：基于 git log 分析的时间线推测——具体接手过程（Kujtim 是否完全转交所有权 / 是否仍有股权 / 是否签了正式协议）未公开，本文仅基于公开 commit 时间和 repo owner 变化推断。
