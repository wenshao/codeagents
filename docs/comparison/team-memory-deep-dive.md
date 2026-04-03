# Team Memory 组织级记忆同步 Deep-Dive

> 团队成员如何共享 AI Agent 学到的项目知识？本文基于 Claude Code（v2.1.89 源码分析）的源码分析，介绍其 Team Memory 组织级记忆同步架构：API 同步、Delta 上传、gitleaks 密钥扫描和冲突解决。Qwen Code 目前无此功能。

---

## 1. 架构总览

```
用户 A 编辑 team/MEMORY.md
  ↓ fs.watch（2s debounce）
本地 SHA256 哈希 → 与 serverChecksums 对比 → Delta 上传
  ↓ PUT /api/claude_code/team_memory
Anthropic Server（per-repo 存储）
  ↓ GET（ETag 条件请求）
用户 B 启动新 session → Pull → 注入系统提示
```

| 维度 | Team Memory | Auto Memory |
|------|-----------|------------|
| **作用域** | 组织级（同 repo 所有成员共享） | 用户私有 |
| **同步** | API pull/push（startup + fs.watch） | 无（仅本地） |
| **存储路径** | `~/.claude/projects/.../memory/team/` | `~/.claude/projects/.../memory/` |
| **认证** | First-party OAuth（必须） | 无 |
| **密钥扫描** | ✅ 29 条 gitleaks 规则 | 无 |
| **冲突处理** | 412 → refresh checksums → retry | N/A |
| **大小限制** | 250KB/entry，总数由服务端控制 | 无限制 |
| **特性门控** | `feature('TEAMMEM')` + GrowthBook `tengu_herring_clock` | `CLAUDE_CODE_DISABLE_AUTO_MEMORY` |

---

## 2. API 同步协议

**端点**：`/api/claude_code/team_memory?repo={owner/repo}`

| 方法 | 用途 | 说明 |
|------|------|------|
| **GET** | 拉取全量记忆 + 每 key SHA256 校验和 | ETag 条件请求（304 = 未变化） |
| **GET ?view=hashes** | 仅拉取校验和元数据 | 冲突恢复时轻量探测 |
| **PUT** | Delta 上传变更条目 | 仅上传哈希不同的 key |

**状态码**：

| 码 | 含义 |
|:--:|------|
| 200 | 成功 |
| 304 | 未变化（ETag 匹配，跳过 pull） |
| 404 | 新 repo，无数据 |
| 412 | ETag 不匹配（冲突） |
| 413 | 条目数超限（返回 `max_entries`） |

> 源码: `services/teamMemorySync/types.ts`

---

## 3. Delta 同步算法

```
1. 读取本地 team/ 目录所有文件
2. 计算每个文件 SHA256 哈希
3. 与 serverChecksums Map 对比
4. 仅上传哈希不同的 key（delta）
5. 分批: MAX_PUT_BODY_BYTES = 200KB（贪心装箱）
6. 每批独立 PUT，部分失败不影响已提交批次
```

**冲突解决（412）**：

```
PUT → 412 (ETag mismatch)
  → GET ?view=hashes（刷新 serverChecksums）
  → 重新计算 delta
  → 重试 PUT（新 ETag）
  → 最多 2 次重试
```

**状态追踪**（`SyncState`）：

```typescript
// 源码: services/teamMemorySync/index.ts
{
  lastKnownChecksum: string | null,        // ETag
  serverChecksums: Map<string, string>,     // per-key sha256
  serverMaxEntries: number | null,          // 从 413 学习
}
```

---

## 4. 文件监视与推送

```typescript
// 源码: services/teamMemorySync/watcher.ts
// fs.watch 监视 team/ 目录
// 2 秒 debounce（避免编辑中频繁推送）
// 变更触发: 重新计算 delta → PUT
```

---

## 5. Gitleaks 密钥扫描

**扫描时机**：**上传前**——密钥不会离开本地机器。

**29 条规则覆盖**（源码: `services/teamMemorySync/secretScanner.ts`）：

| 类别 | 规则 |
|------|------|
| 云平台 | AWS Access Key、GCP API Key、Azure |
| AI 平台 | OpenAI API Key、Anthropic API Key、HuggingFace Token |
| 代码托管 | GitHub PAT（regular/fine-grained/app/refresh）、GitLab Token |
| 通信 | Slack Token、Twilio API Key、SendGrid |
| 包管理 | NPM Token、PyPI Token |
| 基础设施 | Databricks、Hashicorp Vault、Pulumi |
| 支付 | Stripe API Key、Shopify Token |
| 密钥 | RSA/DSA/EC Private Key |

**命中行为**：
- 整个文件跳过（不上传）
- 收集到 `skippedSecrets` 数组（含规则 ID + 人类可读标签）
- 密钥值**永不**记录或显示

---

## 6. 系统提示注入

```typescript
// 源码: memdir/teamMemPrompts.ts
// 启用 Team Memory 时，系统提示包含:

"You have a persistent, file-based memory system with two directories:
  - private: ~/.claude/projects/.../memory/ (user-scoped)
  - team: ~/.claude/projects/.../memory/team/ (org-scoped, synced)

Memory scope:
  - private: persistent per-user, unshared
  - team: shared with all authenticated org members, synced on session start"
```

**MEMORY.md 索引**：private 和 team 各有独立的 `MEMORY.md`，均注入系统提示（200 行 / 25KB 截断）。

---

## 7. 路径安全

```typescript
// 源码: memdir/teamMemPaths.ts
// Symlink 安全（PSR M22186）：
// - 解析 symlink 目标
// - 验证目标在 team/ 目录内
// - 防止 symlink 越狱读取系统文件
```

---

## 8. Qwen Code 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 团队记忆 | ✅ API 同步（per-repo） | ❌ |
| 密钥扫描 | ✅ 29 条 gitleaks 规则 | ❌ |
| 文件监视 | ✅ fs.watch + 2s debounce | ❌ |
| 冲突处理 | ✅ ETag + 412 重试 | ❌ |
| 记忆类型 | 4 种（user/feedback/project/reference），可选 private/team 作用域 | 仅简单笔记 |

---

## 9. 关键源码文件

| 文件 | 职责 |
|------|------|
| `services/teamMemorySync/index.ts` | 同步编排、Delta 上传、批处理 |
| `services/teamMemorySync/types.ts` | API Schema（Zod）、状态类型 |
| `services/teamMemorySync/watcher.ts` | 文件监视 + 2s debounce 推送 |
| `services/teamMemorySync/secretScanner.ts` | 29 条 gitleaks 规则密钥扫描 |
| `memdir/teamMemPaths.ts` | 路径验证 + symlink 安全 |
| `memdir/teamMemPrompts.ts` | 系统提示构建（private + team） |
| `memdir/memdir.ts` | Feature gating + 记忆加载 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。Team Memory 需 First-party OAuth 认证。
