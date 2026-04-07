# 18. 文件索引与模糊搜索——开发者参考

> Claude Code 使用 native Rust/NAPI 模块实现 fzf 风格的模糊文件搜索，支持异步增量索引。这是 Agent 在大型代码库（10 万+ 文件）中快速定位目标文件的关键。
>
> **Qwen Code 对标**：Qwen Code 依赖 `glob` + `rg` 组合搜索文件。Claude Code 的 native 文件索引（Rust NAPI）在大仓库中快 10-100 倍。

## 一、为什么需要专用文件索引

### 问题定义

| 场景 | glob/rg | 专用文件索引 |
|------|---------|------------|
| "找到 auth 相关的文件" | `glob("**/auth*")` — 精确匹配，找不到 `authentication.ts` | 模糊搜索 "auth" → 匹配 `auth.ts`、`authentication.ts`、`AuthProvider.tsx` |
| 10 万文件的 monorepo | 每次搜索扫描文件系统 2-5 秒 | 索引后 <10ms |
| 用户输入时实时补全 | 每个按键触发新搜索 → 延迟 | 增量索引 + 内存查询 → 即时 |

### Claude Code 的实现

源码: `native-ts/file-index/`（Rust NAPI 模块）

```
启动时
  │
  ├─ 异步扫描项目文件树
  │   └─ 排除 .gitignore、node_modules 等
  │
  ├─ 构建内存索引（Rust 实现）
  │
  └─ 提供查询 API
        ├─ 模糊匹配（fzf 算法）
        ├─ 路径权重（src/ 下的文件优先）
        └─ 增量更新（文件变化时）
```

### 竞品对比

| Agent | 文件搜索 | 索引 | 模糊匹配 | 性能 |
|-------|---------|------|---------|------|
| **Claude Code** | Rust NAPI 模块 | ✓ 异步增量 | ✓ fzf 风格 | <10ms（10 万文件） |
| **Gemini CLI** | glob + rg | — | — | 100ms-2s |
| **Qwen Code** | glob + rg | — | — | 100ms-2s |
| **Cursor** | VS Code 文件搜索 | ✓ | ✓ | 快（VS Code 优化） |

## 二、与 ToolSearch 的关系

文件索引和 ToolSearch 是两个不同层面的"搜索"：

| 维度 | 文件索引 | ToolSearch |
|------|---------|-----------|
| 搜索对象 | 项目中的文件路径 | Claude Code 的延迟加载工具 |
| 使用者 | Agent 的 Read/Edit/Write 工具 | Agent 需要激活不常用工具时 |
| 实现 | Rust NAPI 模块 | TypeScript 字符串匹配 |

## 三、Qwen Code 改进建议

### P2：文件索引优化

当前 Qwen Code 每次 `glob` 都扫描文件系统。建议：
1. 启动时异步构建文件列表缓存
2. 通过 `fs.watch` 监听文件变化增量更新
3. 模糊匹配可以用 `fzf-for-js` 等纯 JS 库，不需要 Rust NAPI

### P3：路径补全优化

Qwen Code 的 PR#2879（路径补全）已实现 LRU 缓存。可以在此基础上接入文件索引，从"目录扫描 + 缓存"升级为"全量索引 + 增量更新"。
