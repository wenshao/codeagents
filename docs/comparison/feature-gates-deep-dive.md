# Qwen Code 改进建议 — Feature Gates 与动态灰度发布 (Feature Flags & A/B Testing)

> 核心洞察：当我们为 AI Agent 开发极具风险的底层重构（如全新的 Markdown 解析器、更激进的 Context 压缩算法）时，直接发版全量上线无异于走钢丝。如果某些边缘 Case 导致用户的代码库被毁，回滚整个 NPM 包将是一场灾难。现代工程化要求“代码发布与功能上线解耦”。Claude Code 内置了企业级的 `GrowthBook` 远程特性开关引擎，支持按百分比灰度、热更新开关以及 A/B 测试；而 Qwen Code 目前的新功能上线属于“一锤子买卖”。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么纯靠“发版”来控制功能是不够的？

### 1. Qwen Code 的现状：硬编码的演进
在 Qwen Code 中，如果想上线一个实验性的“技能预取 (Skill Prefetch)”功能，一般的做法是用常量或简单的环境变量包裹：
```typescript
const EXPERIMENTAL_SKILL_SEARCH = process.env.ENABLE_SKILL_SEARCH === 'true';
```
- **痛点一（灰度验证难）**：要测试这个功能，你只能让内测用户手动加上冗长的环境变量去跑。你无法做到“随机挑选 5% 的活跃用户体验新版，如果没有爆出错误再逐渐放量到 100%”。
- **痛点二（紧急熔断慢）**：如果该功能上线后发现严重的内存泄漏，你唯一的手段就是紧急发一个 NPM 补丁版，然后祈祷用户赶紧去升级。在此期间，旧版用户将持续受难。

### 2. Claude Code 解决方案：GrowthBook 远程遥控
Claude Code 在 `services/analytics/growthbook.ts` 中接入了开源的 Feature Flag 平台 `GrowthBook`。

#### 机制一：无感知的远程下发与缓存
Agent 在后台（通常通过异步的 Prefetch 或在非关键路径）静默拉取线上的 Feature 开关 JSON 配置，并缓存在本地。
在代码中，控制功能的开启极其优雅：
```typescript
if (getFeatureValue_CACHED_MAY_BE_STALE('EXPERIMENTAL_SKILL_SEARCH')) {
    // 执行新版高速预取逻辑
} else {
    // 老的保守逻辑
}
```

#### 机制二：细粒度的采样与 A/B 测试
有了这套系统，产品和工程团队可以在远端面板上做到：
1. **流量分片 (Traffic Splitting)**：让用户标识 ID 为奇数的人使用模型 A，偶数的人使用模型 B，收集 Telemetry 遥测数据对比两者的 Token 消耗速率。
2. **事件动态采样 (Dynamic Sampling)**：如果某项遥测数据（如 `mouse_tracking`）发得太频繁导致打点服务器过载，可以在远端将它的上传采样率（Sampling Rate）从 100% 瞬间下调到 1%，无需发版。

#### 机制三：紧急熔断 (Kill Switch)
如果在黑客马拉松中加入的新特性 `AUTO_DREAM` 被发现会在某些电脑上把 CPU 跑满。运维人员只需在 GrowthBook 后台点击一下 Toggle，全球所有 Claude Code 客户端在下一次心跳周期获取到更新后，这个功能就会立刻被“封印”，彻底终结灾难。

## 二、Qwen Code 的改进路径 (P3 优先级)

引入特性门控机制，是让 Qwen Code 能够稳健迭代复杂功能的定海神针。

### 阶段 1：开发基础版 Feature Gates 拦截器
1. 新建 `packages/core/src/config/featureFlags.ts`。
2. 提供一个极简的封装接口，例如 `isFeatureEnabled(featureName)`。
3. 初始阶段，可以只依赖本地的 `.qwen/features.json` 或者环境变量。

### 阶段 2：引入远程配置下发机制
1. 选择一个轻量的配置分发中心（或者直接通过阿里云的对象存储 OSS 挂载一个公共的可读 JSON）。
2. 在 Qwen Code 启动的 `startDeferredPrefetches` 阶段（不阻塞首屏），异步拉取这个 JSON 覆盖本地缓存。

### 阶段 3：推行灰度理念重构核心功能
对于未来要加入的 `MCP Parallel Connection` 或 `FileStateCache`，不要直接抹除旧代码，而是使用 `if (isFeatureEnabled('NEW_MCP_ENGINE'))` 进行流量切割。
等版本稳定后，再移除开关和旧代码，实现软着陆。

## 三、改进收益评估
- **实现成本**：中等。核心在于建立一套可信赖且不阻塞启动的远端拉取与缓存系统。
- **直接收益**：
  1. **彻底解放发版压力**：研发团队敢于将未完全测试的“牛逼功能”合入主干（合并隐藏在开关后），加快研发节奏。
  2. **止损于微毫**：拥有了分钟级的一键紧急止血（Kill Switch）能力。