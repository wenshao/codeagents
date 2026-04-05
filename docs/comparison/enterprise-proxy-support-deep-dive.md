# Qwen Code 改进建议 — 企业代理与证书注入支持 (Enterprise Proxy & CA Cert Support)

> 核心洞察：当我们把视线从个人极客桌面转向大公司的开发机（VDI/DevBox）或 Kubernetes CI/CD 容器时，网络环境往往是极其恶劣的。大公司为了防数据泄露（DLP），通常会实施严格的出口网络封锁，所有的外网 HTTPS 请求必须经过强制的 MITM（中间人攻击式）企业代理服务器，并由企业颁发内部的自签名根证书（Root CA）。如果一个 CLI Agent 不懂这些，它在企业内网中甚至连最基本的 `fetch` 都会抛出 `UNABLE_TO_GET_ISSUER_CERT_LOCALLY` 错误而瞬间罢工。Claude Code 建立了一套极度健壮的底层网络透传与证书加载体系；而 Qwen Code 目前在恶劣的内网代理适配上是一片空白。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么内网环境会让 Agent 寸步难行？

### 1. Qwen Code 现状：理想化网络假设
目前 Qwen Code（以及大部分基于 Node.js `fetch` 或 `axios` 的前端小工具）假设自己运行在一个直接联通公网的环境中。
- **痛点一（代理穿透失败）**：很多企业要求通过 `http://proxy.corp.com:8080` 才能访问外网的大模型 API。Node.js 的原生 `fetch` 并不像 `curl` 那样会自动读取操作系统的 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量。这意味着发向大模型的请求会直接超时死锁。
- **痛点二（证书拦截报错）**：即使网络通了，因为企业代理会解密 HTTPS 流量，它会返回一个由企业 CA 签名的证书。Node.js 底层维护着自己独立、封闭的根证书信任链（不信任操作系统的 Keychain），因此必然报 TLS 握手错误。
- **痛点三（内网资源误伤）**：如果你在这个开发机上用 MCP 连本地的 `http://localhost:3000`，因为配了代理，请求会被错误地发向企业网关，导致 Localhost 环回请求被阻断（缺乏 `NO_PROXY` 隔离机制）。

### 2. Claude Code 解决方案：全天候的代理桥接器
在 Claude Code 的 `entrypoints/init.ts` 和网络基础模块中，专门针对企业网设计了极其厚重的铠甲。

#### 机制一：全局 Node 证书热注入
系统在进程第一秒启动时（早于任何其他模块）：
它会检查用户配置 `settings.json` 中的证书路径或者 `NODE_EXTRA_CA_CERTS` 环境变量。如果在配置中找到了企业 CA 证书路径，它会**直接将该路径硬塞进 `process.env` 中**。
这强迫 Node.js 底层的 C++ TLS 引擎在建立任何一条 HTTPS 连接时，主动把这本企业自签证书加入信任白名单。彻底根治 `CERT_HAS_EXPIRED` 或 `ISSUER_CERT` 报错！

#### 机制二：代理调度器与 `NO_PROXY` 解析
Claude Code 对 `child_process.spawn` 和网络请求进行了一层封装：
它不仅能识别 `HTTP_PROXY` 和 `HTTPS_PROXY`，甚至在创建如 WebSocket 这种需要长连接的子进程时，也会**显式地把这些代理变量下发给子环境**。
更难得的是，它实现了一个小型的 URL Matcher：如果检测到目标 URL 在 `NO_PROXY` 的列表里（比如 `localhost`, `*.internal.net`），它会聪明地绕过代理池，走直连通道，避免本地的 API 被错误地路由到外网代理去。

## 二、Qwen Code 的改进路径 (P2 优先级)

能否进入世界 500 强大公司的内网流水线，代理穿透是“敲门砖”。

### 阶段 1：开发全局 `ProxyDispatcher`
1. 在 `packages/core/src/utils/` 下创建一个全局网络分发模块。
2. 引入 `https-proxy-agent` 等库。
3. 改造项目中所有的大模型 API 调用和文件下载，如果在环境变量中检测到了代理（或者在 `qwen config` 里配置了），则通过 `agent` 选项将所有流量导向代理。

### 阶段 2：支持动态 CA 注入
1. 在 CLI 的 `bin` 入口脚本最顶端：
   ```javascript
   // 必须在任何网络请求模块加载之前运行
   const customCA = readConfigSync('custom_ca_cert_path');
   if (customCA && fs.existsSync(customCA)) {
       process.env.NODE_EXTRA_CA_CERTS = customCA;
   }
   ```

### 阶段 3：提供 `/doctor` 一键排障
因为代理和证书极其容易配错。
必须在现有的 `/doctor` 命令中增加一环：
`[Checking Enterprise Proxy...]` 
尝试通过配置的 Proxy 访问一次外网，如果报错，用人类可读的语言给出明确指导：“你的证书无效，请运行 `qwen config set custom_ca_cert_path <path>`”。

## 三、改进收益评估
- **实现成本**：中等。核心在网络请求底座的统一更换。
- **直接收益**：
  1. **打通企业级市场**：消灭阻碍大型企业内部研发团队使用该工具的最大物理障碍。
  2. **极大的部署稳定性**：不再依赖环境里的黑魔法，在 Docker、K8s Pod 甚至 Github Actions 的 Runner 里拥有了 100% 的网络确定性。