# MDM 企业配置管理 Deep-Dive

> 企业如何集中管控开发者的 AI Agent 配置？本文基于 Claude Code（v2.1.89 源码分析）和 Qwen Code（v0.15.0 开源）的源码分析，对比两者在 MDM（Mobile Device Management）企业策略、配置层级和远程设置管理方面的差异。

---

## 1. 架构总览

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **macOS plist** | ✅ `com.anthropic.claudecode` domain | ❌ |
| **Windows Registry** | ✅ `HKLM\SOFTWARE\Policies\ClaudeCode` | ❌ |
| **Linux 文件策略** | ✅ `/etc/claude-code/managed-settings.json` | ❌ |
| **Drop-in 目录** | ✅ `managed-settings.d/*.json`（systemd 风格） | ❌ |
| **远程策略 API** | ✅ 带 SHA256 校验的 HTTP 缓存 | ❌ |
| **策略优先级** | 5 级（Remote > HKLM > file > drop-in > HKCU） | — |
| **文件级配置** | ✅ settings.json + settings.local.json | ✅ settings.json |

---

## 2. Claude Code：五级策略体系

### 2.1 策略来源优先级（First-Source-Wins）

```
1. Remote Managed Settings    API 远程策略（最高优先级）
       ↓ 未设置时
2. HKLM / plist              管理员 MDM 配置文件
       ↓ 未设置时
3. managed-settings.json      文件策略（需管理员权限）
       ↓ 未设置时
4. managed-settings.d/*.json  Drop-in 目录（字母序合并）
       ↓ 未设置时
5. HKCU                      用户级注册表（最低优先级）
```

**First-Source-Wins 语义**：第一个有内容的来源被使用——来源之间**不合并**。

> 源码: `utils/settings/mdm/settings.ts#L322-L345, L675-L738`

### 2.2 macOS plist 读取

```typescript
// 源码: utils/settings/mdm/constants.ts#L12
// Domain: com.anthropic.claudecode
// Tool: /usr/bin/plutil -convert json -o - --

// 搜索路径（优先级从高到低）:
// 1. /Library/Managed Preferences/{username}/com.anthropic.claudecode.plist  （per-user MDM）
// 2. /Library/Managed Preferences/com.anthropic.claudecode.plist             （device-level MDM）
// 3. ~/Library/Preferences/com.anthropic.claudecode.plist                    （user-writable，ant-only 测试用）

// 超时: 5 秒 (MDM_SUBPROCESS_TIMEOUT_MS)
```

macOS Managed Preferences 由 MDM 服务器（如 Jamf、Kandji）自动分发 plist 配置文件。

### 2.3 Windows Registry 读取

```typescript
// 源码: utils/settings/mdm/constants.ts#L23-L26
// HKLM\SOFTWARE\Policies\ClaudeCode  （管理员策略，最高）
// HKCU\SOFTWARE\Policies\ClaudeCode  （用户级策略，最低）
// 注: SOFTWARE\Policies 在 WOW64 共享——32/64 位无重定向

// 读取方式: reg query <key> /v Settings → 提取 JSON blob
// 源码: settings.ts#L208-L222
```

### 2.4 Drop-in 目录（systemd 风格）

```
macOS:   /Library/Application Support/ClaudeCode/managed-settings.d/
Windows: C:\Program Files\ClaudeCode\managed-settings.d/
Linux:   /etc/claude-code/managed-settings.d/
```

- 基础文件 `managed-settings.json` 先加载
- 目录内 `.json` 文件按**字母序**合并（后者覆盖前者）
- 遵循 systemd/sudoers drop-in 约定

> 源码: `utils/settings/mdm/managedPath.ts#L32`

### 2.5 远程托管设置

```typescript
// 源码: services/remoteManagedSettings/
// 端点: ${BASE_API_URL}/api/claude_code/settings（OAuth API）
// 资格: Console 用户（API Key）+ Enterprise/C4E/Team 订阅者（OAuth）
// 缓存: ~/.claude/remote-settings.json（SHA256 校验）
// 更新策略: HTTP ETag（If-None-Match）减少网络
// 轮询: 长会话每 1 小时刷新
// 降级: API 失败时非阻塞——继续使用已缓存设置
```

### 2.6 启动时序

```
cli.tsx → main.tsx → init()
  ├── startMdmRawRead()           // 并行启动 plutil/reg query 子进程
  ├── startKeychainPrefetch()     // 并行启动 Keychain 读取
  │   ...（其他初始化）
  ├── ensureMdmSettingsLoaded()   // 等待 MDM 子进程完成
  └── loadRemoteManagedSettings() // 异步获取远程策略（不阻塞启动）
```

MDM 读取在启动最早阶段通过子进程并行执行（源码: `rawRead.ts`），避免阻塞主线程 ~100ms。

---

## 3. Qwen Code：文件级配置

### 3.1 配置层级

```
1. ~/.qwen/settings.json           用户全局设置
       ↓
2. .qwen/settings.json             项目级设置
       ↓
3. 环境变量                         运行时覆盖
```

### 3.2 无 MDM 支持

- 无 macOS plist 读取
- 无 Windows Registry 集成
- 无远程策略 API
- 无 drop-in 目录
- 企业策略通过文件分发或环境变量实现

---

## 4. 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 策略分发 | OS-native（plist/Registry/file）+ API | 文件 + 环境变量 |
| 管理员锁定 | ✅ HKLM/plist 用户不可修改 | ❌ 用户可覆盖 |
| 远程策略 | ✅ SHA256 校验 + HTTP ETag | ❌ |
| 启动性能 | 子进程并行读取（~0ms 阻塞） | N/A |
| Drop-in 模块化 | ✅ systemd 风格 | ❌ |
| 策略审计 | 可追溯到来源层级 | 单一文件来源 |

---

## 5. 适用场景

- **企业 IT 管理**：Claude Code 的 MDM 体系允许通过 Jamf/Intune/SCCM 统一下发 AI Agent 策略（如禁用 bypass 模式、限制模型选择、强制遥测）；Qwen Code 需通过配置管理工具（如 Ansible）分发 settings.json
- **安全合规**：Claude Code 的 HKLM 策略用户不可修改，适合 SOC 2 / HIPAA 合规；Qwen Code 的文件配置用户可覆盖
- **个人开发者**：两者的 settings.json 层级对个人使用足够

---

## 6. 关键源码文件

### Claude Code

| 文件 | 职责 |
|------|------|
| `utils/settings/mdm/constants.ts` | 平台常量（plist domain、Registry key、超时） |
| `utils/settings/mdm/rawRead.ts` | 子进程 I/O（plutil/reg query 异步读取） |
| `utils/settings/mdm/settings.ts` | 解析/验证/First-Source-Wins 合并逻辑 |
| `utils/settings/mdm/managedPath.ts` | Drop-in 目录平台路径 |
| `services/remoteManagedSettings/` | 远程策略获取/缓存/轮询 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。
