# Qwen Code 改进建议 — SSRF 防护 (Server-Side Request Forgery Prevention)

> 核心洞察：当 AI Agent 的能力从“本机代码修改”扩展到“调用外部 HTTP Hooks”或者“通过 WebFetch 抓取外网信息”时，安全风险将呈指数级上升。如果不加限制，恶意用户（或被污染的代码上下文）可以通过 Prompt Injection 诱导大模型向内网发送恶意的 HTTP 请求（例如访问 AWS 的 `169.254.169.254` 窃取凭证，或扫描内网 Jenkins 端口），造成严重的 SSRF 漏洞。Claude Code 拥有极其硬核的 `ssrfGuard.ts` 防护墙，涵盖了 IPv4 映射、IPv6 本地链路以及最难防范的 DNS Rebinding 攻击；而 Qwen Code 目前的网络请求校验机制过于薄弱。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、脆弱的网络请求与内网渗透风险

### 1. Qwen Code 现状：基础或缺失的校验
在执行网络相关操作（比如以后如果加入了 HTTP Hook 或增强了 Fetch 工具）时，如果代码仅仅做一次 `isPrivateIp(url)` 的正则判断，是远远不够的。
- **痛点一（IP 变形绕过）**：攻击者可以不使用 `127.0.0.1`，而是使用 IPv4-mapped IPv6 地址（如 `::ffff:127.0.0.1` 或 `::ffff:7f00:1`），普通的正则拦截会直接放行，最终底层的 `fetch` 还是会打到本机的服务上。
- **痛点二（DNS Rebinding 攻击）**：更高级的攻击是，黑客提供一个看似合法的域名 `http://safe.com`，这在第一遍验证时解析到了外部 IP（例如 8.8.8.8，验证通过）；但在大模型底层真正发起 TCP 连接时，该域名的 DNS TTL 刚好过期，黑客将其重新解析到了内部 IP（例如 `192.168.1.100`）。这就完美绕过了 URL 层面的检测，将恶意 payload 打入企业内网。

### 2. Claude Code 解决方案：滴水不漏的 SSRF 防火墙
在 Claude Code 的 `utils/hooks/ssrfGuard.ts` 中，开发者为了彻底封死大模型作恶的可能，实现了一套金融级安全网关：

#### 机制一：全量私有地址段屏蔽
拦截所有的：
- 本地环回 (Loopback): `127.0.0.0/8`, `::1`
- 局域网私有 (RFC 1918): `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- 链路本地 (Link-Local): `169.254.0.0/16` (极度危险，常用于云厂商 Metadata API 获取 Root 权限)
- 对应的所有 IPv6 变体和映射。

#### 机制二：DNS 解析结果的二次拦截 (防 DNS Rebinding)
它不会直接把用户输入的 URL 丢给 Node.js 的 `fetch()`！
相反，它的执行流程是：
1. 手动提取 URL 的 Hostname。
2. 使用 `dns.promises.lookup` 在应用层手动解析该域名，得到最终的真实 IP 地址。
3. 对这个**真实 IP**进行是否为私有段的校验（这样彻底废掉了 DNS 变形或重绑定的伎俩）。
4. 校验通过后，使用底层网络库把请求**强制定向到刚才解析出的那个安全 IP 上**（并在 Header 里把 Host 伪装回原来的域名），杜绝了底层 `fetch` 自己再去查一次 DNS 的时间差漏洞。

## 二、Qwen Code 的改进路径 (P2 优先级)

对于一款定位于“企业级研发流程”的 Agent，安全性决定了它能否进入大公司的内网白名单。

### 阶段 1：引入强力的 IP 校验库
1. 在 `packages/core/src/utils/` 下创建 `ssrfGuard.ts`。
2. 使用 `ipaddr.js` 等成熟的库来解析和比对 IP。
3. 穷举阻断 `169.254.169.254` 等云服务敏感端点。

### 阶段 2：重写 Web 请求底层
1. 查找项目中所有的外网请求点（例如未来的 HTTP Hook 执行器，或者拉取外部插件的模块）。
2. 在发起请求前，必须先经过 `validateSafeUrl(targetUrl)`。
3. 实现 DNS Lookup 校验逻辑，将校验后的 IP 作为底层 Socket 的直连地址。

### 阶段 3：建立例外名单 (Allowlist)
在某些场景下（比如企业内网专用的 Jira Hook），用户确实需要请求内网 IP。
允许通过配置文件或环境变量 `QWEN_CODE_ALLOWED_INTERNAL_HOSTS="jira.corp.local"` 来显式开洞，但必须由人类开发者主动授权，默认一律阻断。

## 三、改进收益评估
- **实现成本**：中等。核心在底层网络请求的劫持，难点在于要保证 HTTP 代理环境（HTTP Proxy）下的兼容性。代码量在 200 行左右。
- **直接收益**：
  1. **零日漏洞防护**：使得 Qwen Code 天生免疫各种利用大模型发起的进阶 SSRF 渗透攻击。
  2. **合规性达标**：满足大型企业和金融客户的 SecOps 审计红线，为推广铺平道路。