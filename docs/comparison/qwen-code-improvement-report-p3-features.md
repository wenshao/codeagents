# Qwen Code 改进建议 — P3 功能特性深度分析

> 本报告记录 Claude Code 中**现有改进总览表完全未提及**的 7 项功能特性。每项都经过源码级验证，确保不与已有报告重复。
>
> 验证方法：所有改进点已对照 `qwen-code-improvement-report.md` 总览表、所有 deep-dive 文档、所有 P0-P3 分报告、所有 single-file Agent 文档（`tools/claude-code/` 目录），确认无重复。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. 沙箱排除命令 excludedCommands（P3）

**做什么**：Claude Code 允许用户配置一组命令模式，这些命令将**不被沙箱执行**——直接在宿主机运行。这对于需要直接访问宿主机资源的命令（如 Docker、Bazel）非常有用：

```json
// .claude/settings.local.json
{
  "sandbox": {
    "excludedCommands": [
      "docker:*",
      "npm run test:*",
      "bazel:*"
    ]
  }
}
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/sandbox-toggle/sandbox-toggle.tsx` | 132 | `/sandbox` 命令入口 + `exclude` 子命令 |
| `commands/sandbox-toggle/index.ts` | 12 | 命令注册 |
| `components/sandbox/SandboxSettings.tsx` | 295 | 沙箱设置 UI（3 种模式：auto-allow/regular/disabled） |
| `components/sandbox/SandboxConfigTab.tsx` | 44 | 沙箱配置标签页 |
| `components/sandbox/SandboxDependenciesTab.tsx` | 119 | 沙箱依赖检查标签页 |
| `components/sandbox/SandboxOverridesTab.tsx` | 192 | 沙箱覆盖标签页（显示 excludedCommands） |
| `components/sandbox/SandboxDoctorSection.tsx` | 45 | 沙箱诊断信息展示 |
| `utils/sandbox/sandbox-adapter.ts` | ~900 | 沙箱管理器 + `addToExcludedCommands()` 函数 |
| `tools/BashTool/shouldUseSandbox.ts` | ~100 | 判断命令是否应使用沙箱（含 excludedCommands 匹配逻辑） |

**总规模**：~1700 行（命令 + 组件 + 工具函数）

**为什么 Qwen Code 应该学习**：

Qwen Code 有基础沙箱支持（`sandbox.ts` 984 行），但**没有 excludedCommands 功能**。用户无法排除特定命令从沙箱执行——所有沙箱命令都被同等对待。

**关键设计细节**：

1. **命令模式匹配**：支持通配符（`docker:*`、`npm run test:*`），不仅匹配命令前缀，还匹配完整命令模式
2. **复合命令拆分**：`docker ps && curl evil.com` 会被拆分为 `docker ps` 和 `curl evil.com`，分别检查是否排除
3. **环境变量剥离**：`FOO=bar bazel ...` 和 `timeout 30 bazel ...` 也能正确匹配 `bazel:*` 模式
4. **交互式 UI**：`/sandbox` 命令提供交互式设置界面，用户可选择沙箱模式（auto-allow/regular/disabled）并管理 excludedCommands

**Qwen Code 现状**：Qwen Code 的 `sandbox.ts`（984 行）支持 docker/podman/sandbox-exec 三种沙箱后端，但没有 excludedCommands 功能，也没有交互式沙箱设置 UI。

**Qwen Code 修改方向**：
1. 在 `settingsSchema.ts` 的 sandbox 配置中添加 `excludedCommands` 字段
2. 新建 `utils/sandbox/excludedCommands.ts`——命令模式匹配逻辑
3. 修改 `shouldUseSandbox()` 逻辑——检查命令是否匹配 excludedCommands
4. 扩展 `/sandbox` 或 `/settings` 命令——添加 excludedCommands 管理 UI

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：命令模式匹配（通配符 + 环境变量剥离 + 复合命令拆分）

---

<a id="item-2"></a>

### 2. 交互式隐私设置对话框 /privacy-settings（P3）

**做什么**：Claude Code 的 `/privacy-settings` 命令提供一个**交互式对话框**，让用户切换 "Help improve Claude" 设置（是否允许使用聊天记录训练模型）：

```
Data Privacy
━━━━━━━━━━━━
Review and manage your privacy settings at https://claude.ai/settings/data-privacy-controls

Help improve Claude          true/false  ← 可按 Enter/Tab/Space 切换
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/privacy-settings/privacy-settings.tsx` | 71 | `/privacy-settings` 命令入口 + Grove 资格检查 |
| `commands/privacy-settings/index.ts` | 12 | 命令注册 |
| `components/grove/Grove.tsx` | 462 | `GroveDialog` + `PrivacySettingsDialog` 组件 |
| `services/api/grove.ts` | 348 | Grove API 服务——`getGroveSettings()`、`updateGroveSettings()`、`isQualifiedForGrove()` |

**总规模**：~893 行

**为什么 Qwen Code 应该学习**：

Qwen Code 有 `privacy` 配置 schema（`settingsSchema.ts` 中的 `usageStatisticsEnabled` 字段），但**没有交互式对话框**。用户只能通过编辑 JSON 配置文件来切换设置，体验较差。

**关键设计细节**：

1. **Grove 资格检查**：`isQualifiedForGrove()` 检查用户是否是 Consumer Subscriber（付费用户），只有付费用户才能看到隐私设置对话框
2. **缓存机制**：Grove 配置缓存 24 小时，冷启动时后台获取，不阻塞 UI
3. **OAuth 401 重试**：`updateGroveSettings()` 使用 OAuth 401 重试机制，确保 token 过期时也能成功更新
4. **交互设计**：支持 Enter/Tab/Space 切换，Esc 取消，带二次确认（pending 状态）

**Qwen Code 现状**：Qwen Code 的 `/settings` 命令打开设置对话框，但隐私设置只是其中的一个配置项，没有专门的隐私设置对话框，也没有 Grove 式的交互式切换 UI。

**Qwen Code 修改方向**：
1. 新建 `commands/privacy-settings/` 目录
2. 新建 `components/PrivacySettingsDialog.tsx`——交互式隐私设置对话框
3. 修改 `/settings` 命令——添加隐私设置快捷入口
4. （可选）添加 API 服务——如果 DashScope 支持远程隐私设置

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~1.5 天（1 人）
- 难点：无（纯 UI 功能）

---

<a id="item-3"></a>

### 3. 自动发布说明 /release-notes（P3）

**做什么**：Claude Code 的 `/release-notes` 命令自动从 GitHub 获取并格式化显示发布说明：

```
Version 2.0.53:
· Fixed: Shell command timeout issue
· Added: New /review command
· Improved: Tool execution speed by 30%

Version 2.0.52:
· Fixed: Memory leak in sandbox mode
· Added: Support for new MCP servers
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/release-notes/release-notes.ts` | 61 | `/release-notes` 命令入口 |
| `commands/release-notes/index.ts` | 12 | 命令注册 |
| `utils/releaseNotes.ts` | 370 | 发布说明核心逻辑——获取、解析、缓存、显示 |

**总规模**：~443 行

**为什么 Qwen Code 应该学习**：

Qwen Code **没有 release notes 功能**。用户无法在终端内查看新版本的变化——只能去 GitHub 查看 CHANGELOG。

**关键设计细节**：

1. **自动获取**：`fetchAndStoreChangelog()` 从 GitHub raw content URL 获取 CHANGELOG.md
2. **文件缓存**：存储在 `~/.claude/cache/changelog.md`，不依赖配置文件
3. **超时保护**：获取时设置 500ms 超时，不阻塞 UI
4. **版本比较**：使用 `semver` 库比较版本号，只显示比上次更新的版本更新的内容
5. **最近 N 条**：`MAX_RELEASE_NOTES_SHOWN = 5`，只显示最近 5 条发布说明
6. **解析 Markdown**：`parseChangelog()` 解析 Markdown 格式的 CHANGELOG，提取版本号和变更列表
7. **非交互式模式跳过**：`getIsNonInteractiveSession()` 检查，非交互式模式不获取 changelog

**Qwen Code 现状**：Qwen Code 有 `/status`（别名 `/about`）命令显示版本信息，但没有 release notes 功能。

**Qwen Code 修改方向**：
1. 新建 `utils/releaseNotes.ts`——发布说明核心逻辑
2. 新建 `commands/releaseNotesCommand.ts`——`/release-notes` 命令
3. 在启动时后台获取 changelog（类似 Claude Code 的 `checkForReleaseNotes()`）
4. 解析 GitHub CHANGELOG.md 或 Qwen Code 的 CHANGELOG.md

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：CHANGELOG 格式解析（Qwen Code 的 CHANGELOG 格式可能与 Claude Code 不同）

---

<a id="item-4"></a>

### 4. 企业用量管理 /extra-usage（P3）

**做什么**：Claude Code 的 `/extra-usage` 命令让企业/团队用户管理额外 API 用量——检查当前用量、向管理员申请增加用量、或登录新账号：

```bash
/extra-usage    # 检查用量状态
                # 如果未启用：打开浏览器登录
                # 如果已启用：显示当前用量
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/extra-usage/extra-usage.tsx` | 45 | `/extra-usage` 命令入口 + 登录流程 |
| `commands/extra-usage/extra-usage-core.ts` | 118 | 用量管理核心逻辑——检查资格、申请、状态显示 |
| `commands/extra-usage/extra-usage-noninteractive.ts` | 12 | 非交互式模式支持 |
| `commands/extra-usage/index.ts` | 12 | 命令注册 |
| `services/api/adminRequests.ts` | ~150 | Admin Request API——检查资格、创建请求、查询状态 |
| `services/api/usage.ts` | ~100 | Usage API——获取用量统计、利用率 |
| `services/api/overageCreditGrant.ts` | ~50 | Overage Credit Grant API——信用额度管理 |

**总规模**：~487 行

**为什么 Qwen Code 应该学习**：

Qwen Code **没有用量管理功能**。企业/团队用户无法在终端内检查或申请额外用量——只能去 Web 控制台操作。

**关键设计细节**：

1. **Admin Request 流程**：
   - `checkAdminRequestEligibility('limit_increase')`——检查用户是否有资格申请
   - `createAdminRequest({ request_type: 'limit_increase' })`——创建申请
   - `getMyAdminRequests('limit_increase', ['pending', 'dismissed'])`——查询已有申请
2. **登录流程**：如果用户未登录，自动启动登录流程（`<Login>` 组件）
3. **缓存失效**：`invalidateOverageCreditGrantCache()`——确保获取最新状态
4. **团队/企业区分**：根据 `subscriptionType`（team/enterprise/max）显示不同的用量管理界面
5. **非交互式模式**：支持 `--non-interactive` 标志，输出 JSON 格式用量信息

**Qwen Code 现状**：Qwen Code 的 `/stats` 命令显示会话级统计（时长、token 用量），但没有企业用量管理功能。

**Qwen Code 修改方向**：
1. 新建 `commands/extra-usage/` 目录
2. 新建 `services/api/usage.ts`——用量 API 服务
3. 实现 `/extra-usage` 命令——检查用量、申请增加
4. （需要后端支持）DashScope Admin Request API

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：需要 DashScope 后端支持 Admin Request API

---

<a id="item-5"></a>

### 5. 交互式限速选项菜单 /rate-limit-options（P3）

**做什么**：Claude Code 的 `/rate-limit-options` 命令提供交互式菜单，帮助用户在遇到限速时选择操作：

```
Rate Limit Options
━━━━━━━━━━━━━━━━━━
You've reached your rate limit. Choose an action:

[ ] Add funds to continue with extra usage
[ ] Upgrade your plan
[ ] Stop and wait for limit to reset
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/rate-limit-options/rate-limit-options.tsx` | 209 | 限速选项菜单 UI + 操作路由 |
| `commands/rate-limit-options/index.ts` | 12 | 命令注册 |

**总规模**：~221 行

**为什么 Qwen Code 应该学习**：

Qwen Code **没有交互式限速选项菜单**。用户遇到限速时只能等待或手动切换账号——没有引导式的操作选择。

**关键设计细节**：

1. **动态菜单**：根据用户订阅类型、限速状态、extra-usage 启用状态动态显示不同选项
2. **GrowthBook 门控**：`getFeatureValue_CACHED_MAY_BE_STALE("tengu_jade_anvil_4", false)` 控制菜单项顺序
3. **操作路由**：选择后路由到对应命令（`/extra-usage`、`/upgrade`）
4. **限速状态感知**：使用 `useClaudeAiLimits()` hook 获取当前限速状态

**Qwen Code 现状**：Qwen Code 的 API 客户端有重试逻辑（`api.ts`），但没有用户交互式的限速选项菜单。

**Qwen Code 修改方向**：
1. 新建 `commands/rateLimitOptionsCommand.tsx`——限速选项菜单
2. 集成到限速错误处理流程——检测到 429 时显示菜单
3. （可选）添加 `useDashScopeLimits()` hook——获取 DashScope 限速状态

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）
- 难点：需要 DashScope 限速 API 支持

---

<a id="item-6"></a>

### 6. CCR 远程环境设置 /remote-setup（P3）

**做什么**：Claude Code 的 `/remote-setup` 命令帮助用户设置 CCR（Claude Code Remote）远程环境——将本地 GitHub 凭据导入到远程环境，并创建默认环境：

```
Connect Claude on the web to GitHub?

Your local credentials are used to authenticate with GitHub

[Continue]  [Cancel]
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/remote-setup/remote-setup.tsx` | 186 | 远程设置 UI + 状态机 |
| `commands/remote-setup/api.ts` | 182 | 远程环境 API——导入 GitHub Token、创建默认环境、获取 Web URL |
| `commands/remote-setup/index.ts` | 20 | 命令注册 |

**总规模**：~388 行

**为什么 Qwen Code 应该学习**：

Qwen Code **没有远程执行能力**，所有操作都在本地完成。但未来如果支持远程执行（如阿里云 ECS 上运行 Agent），这个功能将非常有用。

**关键设计细节**：

1. **登录状态检查**：
   - `isSignedIn()`——检查是否登录 Claude
   - `getGhAuthStatus()`——检查 GitHub CLI 认证状态
   - `gh auth token`——读取 GitHub Token
2. **Token 导入**：`importGithubToken(token)`——将本地 GitHub Token 导入到远程环境
3. **环境创建**：`createDefaultEnvironment()`——在远程环境创建默认项目
4. **浏览器跳转**：`openBrowser(url)`——打开 Claude Code Web 界面
5. **错误处理**：4 种错误类型（not_signed_in、invalid_token、server、network）各有专用错误信息

**Qwen Code 现状**：Qwen Code 的 `setupGithubCommand` 提供基础 GitHub 设置，但没有远程环境设置能力。

**Qwen Code 修改方向**：
1. （远期）如果支持远程执行，新建 `commands/remote-setup/` 目录
2. 实现远程环境 API 对接
3. 引导用户完成远程环境初始化设置

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：需要远程执行平台支持

---

<a id="item-7"></a>

### 7. Thinkback 动画回放 /thinkback-play（P3）

**做什么**：Claude Code 的 `/thinkback-play` 命令播放 Thinkback 动画——一个终端内的 ASCII 动画，展示 "回忆" 过程：

```
 _____________
 |          \  \
 | NEW TERMS \__\
 |              |
 |  ----------  |
 |  ----------  |
 |  ----------  |
 |  ----------  |
 |  ----------  |
 |              |
 |______________|
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/thinkback-play/thinkback-play.ts` | 36 | `/thinkback-play` 命令——查找 skill 目录并播放动画 |
| `commands/thinkback-play/index.ts` | 12 | 命令注册 |
| `commands/thinkback/thinkback.ts` | ~530 | Thinkback 核心逻辑——动画播放 |

**总规模**：~578 行

**为什么 Qwen Code 应该学习**：

这是一个**趣味性功能**，不是核心功能。但它展示了 Claude Code 的 "个性化体验" 设计理念——通过小细节提升用户体验。

**Qwen Code 现状**：Qwen Code 没有 thinkback 功能。

**Qwen Code 修改方向**：
1. （低优先级）新建 `commands/thinkbackPlayCommand.ts`
2. 实现简单的 ASCII 动画播放
3. 可选：添加更多终端动画（如加载动画、完成庆祝等）

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~0.5 天（1 人）
- 难点：无（纯 UI/动画功能）

---

## 总结

本文件涵盖 7 项**现有改进总览表完全未提及**的功能：

| # | 改进点 | 源码规模 | 开发周期 | 意义 |
|---|--------|:--------:|:--------:|------|
| 1 | [沙箱排除命令](#item-1) | ~1700 行 | ~2 天 | 沙箱灵活性 |
| 2 | [交互式隐私设置](#item-2) | ~893 行 | ~1.5 天 | 隐私体验 |
| 3 | [自动发布说明](#item-3) | ~443 行 | ~2 天 | 版本感知 |
| 4 | [企业用量管理](#item-4) | ~487 行 | ~2 天 | 企业功能 |
| 5 | [限速选项菜单](#item-5) | ~221 行 | ~1 天 | 用户体验 |
| 6 | [CCR 远程设置](#item-6) | ~388 行 | ~2 天 | 远程执行 |
| 7 | [Thinkback 动画](#item-7) | ~578 行 | ~0.5 天 | 个性化体验 |

**总计**：~10.5 天（1 人）

> **验证声明**：本文件所有改进点已对照以下文档确认无重复：
> - `qwen-code-improvement-report.md` 总览表（全部 P0-P3 条目）
> - 所有 deep-dive 文档（33 个文件）
> - 所有 P0-P3 分报告（p0-p1-core/engine/platform、p2-core/perf/stability/tools、p3）
> - 所有 single-file Agent 文档（`tools/claude-code/` 目录下 10 个文件）
>
> 注意：`/terminalSetup` 已在 Qwen Code 中有类似功能（`terminalSetupCommand`），已从本文件移除。
