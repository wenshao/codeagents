# Qwen Code 改进建议 — P3 架构与基础设施深度分析（第三轮）

> 本报告记录**第三轮严格去重扫描**后发现的 4 项真正未覆盖功能。每项都经过 Claude Code 源码逐行验证和 Qwen Code 现状确认。
>
> 验证方法：对照 `qwen-code-improvement-report.md` 总览表、所有 deep-dive 文档、所有 P0-P3 分报告、所有 single-file Agent 文档、之前已提交的 P2 uncovered、P3 features、P3 features v2 报告，确认无重复。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Buddy 伴侣精灵系统（P3）

**做什么**：Claude Code 实现了一个**虚拟伴侣**——一个终端内的 ASCII 精灵（鸭子），有物种、稀有度、属性、帽子、眼睛等自定义外观，会响应用户操作给出动画反馈：

```
    ╲    ╱
     ╲  ╱   ◕‿◕  ← 精灵（鸭子）
      ╱  ╲
    ╱    ╲
   [  🎩  ]  ← 帽子（稀有度决定）
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `buddy/sprites.ts` | 514 | 精灵定义——物种（SPECIES）、稀有度（RARITIES）、权重系统 |
| `buddy/CompanionSprite.tsx` | 370 | 渲染组件——ASCII 精灵显示、动画效果 |
| `buddy/companion.ts` | 133 | 核心逻辑——生成精灵（Mulberry32 PRNG）、属性系统 |
| `buddy/types.ts` | 148 | 类型定义——Companion、Rarity、StatName |
| `buddy/prompt.ts` | 36 | 精灵对话提示词 |
| `buddy/useBuddyNotification.tsx` | 97 | 通知 Hook——精灵弹出提示 |

**总规模**：1298 行

**为什么 Qwen Code 应该学习**：

Qwen Code **完全没有伴侣/精灵系统**。这是一个差异化功能——提升用户情感连接，让终端交互更有趣。

**关键设计细节**：

1. **Mulberry32 PRNG**——轻量级种子随机数生成器，确保每个用户的精灵唯一且可复现
2. **Bun.hash**——如果可用，使用 Bun 的哈希函数生成种子（比 FNV-1a 更快）
3. **稀有度系统**——common(50%)、uncommon(25%)、rare(15%)、epic(8%)、legendary(2%)——权重可配置
4. **属性系统**——5 种属性（快乐、能量、社交、智慧、创造力），稀有度影响属性下限
5. **外观自定义**——帽子（HATS）、眼睛（EYES）根据稀有度解锁
6. **通知系统**——`useBuddyNotification` Hook 触发精灵动画提示

**Qwen Code 现状**：Qwen Code 完全没有伴侣/精灵系统。`QWEN_CODE_COMPANION_EXTENSION_NAME` 是 IDE 插件名称，不是虚拟伴侣。

**Qwen Code 修改方向**：
1. 新建 `buddy/` 模块——精灵定义、类型、渲染
2. 实现 PRNG 精灵生成
3. 新建 `components/BuddySprite.tsx`——ASCII 精灵显示
4. 集成到 REPL 界面

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~800 行
- 开发周期：~5 天（1 人）
- 难点：ASCII 精灵设计、终端渲染兼容性

**意义**：虚拟伴侣提升情感连接——让冷冰冰的终端更有温度。
**缺失后果**：终端交互单调——缺少情感化设计。
**改进收益**：ASCII 精灵陪伴——稀有度系统激发收集欲。

---

<a id="item-2"></a>

### 2. 远程会话管理 + 权限桥接（P3）

**做什么**：Claude Code 的 `remote/` 模块实现了**完整的远程会话管理系统**——本地 CLI 作为客户端，连接 CCR（Claude Code Remote）云端 Agent，实现权限同步、消息转发、会话管理：

```
本地 CLI ←→ WebSocket ←→ CCR 云端 Agent
           SessionsWebSocket    RemoteSessionManager
                     ↓
             remotePermissionBridge
                     ↓
           sdkMessageAdapter (消息格式转换)
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `remote/RemoteSessionManager.ts` | 343 | 远程会话管理——连接、消息路由、权限请求转发 |
| `remote/SessionsWebSocket.ts` | 404 | WebSocket 客户端——重连逻辑、心跳、消息序列化 |
| `remote/sdkMessageAdapter.ts` | 302 | SDK 消息适配器——本地/远程消息格式转换 |
| `remote/remotePermissionBridge.ts` | 78 | 权限桥接——远程权限请求转为本地 ToolUseConfirm |

**总规模**：1127 行

**为什么 Qwen Code 应该学习**：

Qwen Code **完全没有远程会话管理功能**。所有操作都在本地完成，无法连接到云端 Agent。

**关键设计细节**：

1. **SessionsWebSocket**——
   - 重连逻辑：`MAX_RECONNECT_ATTEMPTS = 5`，`RECONNECT_DELAY_MS = 2000`
   - 心跳：`PING_INTERVAL_MS = 30000`
   - 4001 错误处理：session not found 重试 3 次（压缩期间可能短暂失效）
   - 永久关闭码：4003 (unauthorized) 立即停止重连
2. **RemoteSessionManager**——
   - `viewerOnly` 模式：纯查看者不发送中断信号
   - 权限请求转发：`onPermissionRequest` 回调到本地 UI
   - 初始 prompt 标记：`hasInitialPrompt` 跟踪首次处理状态
3. **SDK Message Adapter**——
   - 本地/远程消息格式转换
   - 工具名称映射
   - 错误码标准化
4. **Remote Permission Bridge**——
   - 创建合成 AssistantMessage（远程工具使用无本地消息）
   - 创建 Tool stub（远程 MCP 工具本地无定义）
   - 权限请求路由到 FallbackPermissionRequest

**Qwen Code 现状**：Qwen Code 的 channels 支持 dingtalk/telegram/weixin，但**没有 CCR 式远程会话管理**。SDK 有基础权限控制，但没有远程权限桥接。

**Qwen Code 修改方向**：
1. 新建 `remote/` 模块
2. 实现 WebSocket 客户端（重连、心跳）
3. 实现 RemoteSessionManager
4. 实现权限桥接（合成消息、Tool stub）

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~800 行
- 开发周期：~5 天（1 人）
- 难点：需要云端 CCR 平台支持

**意义**：远程会话管理是"本地 CLI + 云端重算力"的核心桥梁。
**缺失后果**：无法连接云端 Agent——受限于本地算力。
**改进收益**：远程会话管理——本地 CLI 连接云端——算力无限制。

---

<a id="item-3"></a>

### 3. 完整快捷键系统（P3）

**做什么**：Claude Code 实现了一套**完整的快捷键系统**——解析、验证、加载用户自定义快捷键、冲突检测、多 chord 序列：

```
~/.claude/keybindings.json
{
  "ctrl+k ctrl+s": "openSettings",   // multi-chord
  "ctrl+c": "cancel",                 // reserved (不可重绑)
  "ctrl+l": { "command": "clear", "when": "inputFocused" }  // 条件绑定
}
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `keybindings/defaultBindings.ts` | 340 | 默认快捷键定义 |
| `keybindings/loadUserBindings.ts` | 472 | 加载用户自定义快捷键 |
| `keybindings/parser.ts` | 203 | 快捷键字符串解析（"ctrl+k ctrl+s" → Chord 结构） |
| `keybindings/resolver.ts` | 244 | 快捷键解析——按键 → 命令 |
| `keybindings/schema.ts` | 236 | JSON Schema 定义（验证 keybindings.json） |
| `keybindings/validate.ts` | 498 | 验证逻辑——冲突检测、格式检查 |
| `keybindings/match.ts` | 120 | 快捷键匹配 |
| `keybindings/reservedShortcuts.ts` | 127 | 保留快捷键（Ctrl+C/D 不可重绑） |
| `keybindings/shortcutFormat.ts` | 63 | 快捷键显示格式化 |
| `keybindings/template.ts` | 52 | 快捷键模板 |
| `keybindings/useKeybinding.ts` | 196 | React Hook——快捷键注册 |
| `keybindings/useShortcutDisplay.ts` | 59 | 快捷键显示 Hook |
| `keybindings/KeybindingContext.tsx` | 242 | Context 提供者 |
| `keybindings/KeybindingProviderSetup.tsx` | 307 | Provider 初始化 |

**总规模**：3159 行

**为什么 Qwen Code 应该学习**：

Qwen Code 有**基础快捷键系统**（`keyBindings.ts` 186 行 + `keyMatchers.ts` 105 行 = **291 行**），但**缺少完整的快捷键架构**：

| 能力 | Claude Code | Qwen Code |
|------|-------------|-----------|
| 用户自定义快捷键 | ✓ `~/.claude/keybindings.json` | ✗ 无 |
| 多 chord 序列 | ✓ `ctrl+k ctrl+s` | ✗ 无 |
| 冲突检测 | ✓ 498 行验证逻辑 | ✗ 无 |
| JSON Schema 验证 | ✓ 236 行 | ✗ 无 |
| 保留快捷键 | ✓ 127 行（Ctrl+C/D 不可重绑） | ✗ 无 |
| 快捷键 Provider | ✓ Context + Provider | ✗ 无 |

**关键设计细节**：

1. **Parser**——`parser.ts` (203 行) 解析快捷键字符串：`"ctrl+k ctrl+s"` → `{chords: [{key: "k", ctrl: true}, {key: "s", ctrl: true}]}`
2. **Resolver**——`resolver.ts` (244 行) 多 chord 状态机——第一个键按下后等待第二个键
3. **Validate**——`validate.ts` (498 行) 冲突检测——防止用户重绑保留快捷键
4. **Schema**——`schema.ts` (236 行) JSON Schema 定义——IDE 自动补全 keybindings.json
5. **Provider**——`KeybindingProviderSetup.tsx` (307 行) 加载默认 + 用户快捷键

**Qwen Code 现状**：Qwen Code 的 `keyBindings.ts` (186 行) 定义了基础快捷键枚举和默认绑定，`keyMatchers.ts` (105 行) 提供基础匹配逻辑。**没有用户自定义快捷键、没有 multi-chord、没有冲突检测、没有 JSON Schema。**

**Qwen Code 修改方向**：
1. 新建 `keybindings/parser.ts`——快捷键字符串解析
2. 新建 `keybindings/resolver.ts`——多 chord 状态机
3. 新建 `keybindings/validate.ts`——冲突检测
4. 新建 `keybindings/schema.ts`——JSON Schema
5. 支持 `~/.qwen/keybindings.json` 加载

**实现成本评估**：
- 涉及文件：~10 个
- 新增代码：~1500 行
- 开发周期：~8 天（1 人）
- 难点：multi-chord 状态机超时处理

**意义**：用户自定义快捷键——符合个人习惯，提高工作效率。
**缺失后果**：快捷键硬编码——无法自定义——用户需适应工具而非工具适应用户。
**改进收益**：自定义快捷键——multi-chord + 冲突检测 + 保留键保护——完整快捷键系统。

---

<a id="item-4"></a>

### 4. useMoreRight 右面板扩展（P3）

**做什么**：Claude Code 的 `useMoreRight` Hook 管理右侧面板的扩展显示——当信息超出当前面板容量时，自动扩展到右侧新面板：

```
┌─────────────┬──────────────┐
│ 主面板      │ 右面板        │
│ 对话历史    │ 工具结果      │
│             │ 更多 → 新右面板│
└─────────────┴──────────────┘
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `moreright/useMoreRight.tsx` | 25 | 核心 Hook——右面板状态管理 |

**总规模**：25 行

**为什么 Qwen Code 应该学习**：

Qwen Code **没有右面板扩展功能**。当信息过多时，只能滚动查看，无法分屏显示。

**Qwen Code 现状**：Qwen Code 使用单面板布局。

**Qwen Code 修改方向**：
1. 新建 `moreright/useMoreRight.tsx`
2. 集成到布局系统

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~30 行
- 开发周期：~0.5 天（1 人）

---

## 总结

本文件涵盖 4 项**现有改进总览表完全未提及**的功能：

| # | 改进点 | 源码规模 | 开发周期 | 意义 |
|---|--------|:--------:|:--------:|------|
| 1 | [Buddy 伴侣精灵](#item-1) | 1298 行 | ~5 天 | 情感化设计 |
| 2 | [远程会话管理 + 权限桥接](#item-2) | 1127 行 | ~5 天 | 云端算力连接 |
| 3 | [完整快捷键系统](#item-3) | 3159 行 vs Qwen 291 行 | ~8 天 | 自定义快捷键 |
| 4 | [useMoreRight 右面板](#item-4) | 25 行 | ~0.5 天 | 多面板布局 |

**总计**：~18.5 天（1 人）

> **验证声明**：本文件所有改进点已对照以下文档确认无重复：
> - `qwen-code-improvement-report.md` 总览表（全部 P0-P3 条目）
> - 所有 deep-dive 文档（33 个文件）
> - 所有 P0-P3 分报告（p0-p1-core/engine/platform、p2-core/perf/stability/tools、p3）
> - 所有 single-file Agent 文档（`tools/claude-code/` 目录下 10 个文件）
> - 之前已提交的 P2 uncovered、P3 features、P3 features v2 报告
