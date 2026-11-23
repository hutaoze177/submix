# sub — 链式代理订阅（私有仓库）

> 📌 **本文件是模板，位于公开仓库 `hutaoze177/submix/docs/`。**
> 其中的 `<PIN_LAND_IP>` 是占位符，部署到私有产物仓库时替换为实际的锁定 IP。
> **公开仓库内任何文件都不得写入真实住宅 IP、上游域名、账号 ID 或 token。**

> ⚠️ **接手前必读：本仓库有两个订阅文件，不是重复、不是备份、不是新旧版本。**
> 选错会直接导致「流量费暴涨」或「视频卡顿」。详见下面第 1 节。

「机场前置 + 住宅落地」的链式代理配置，由 [`hutaoze177/submix`](https://github.com/hutaoze177/submix)
（公开仓库，只放代码和脱敏后的规则模板）**自动重建**后推送到本仓库。

---

## 1. 两个订阅文件（最重要）

| 文件 | `MATCH` 兜底 | 用途 | 流量成本 |
|---|---|---|---|
| **`sub.yaml`** | `前置-机场` | **日常主用**。只有 AI / Meta 走住宅，其余走机场 | 低 ✅ |
| **`sub-all-landing.yaml`** | `落地-US-ISP` | **应急备用**。所有国外流量都走美国住宅 | **极高 ⚠️** |

### 两者的差别：只有一行

```diff
- MATCH,前置-机场        # sub.yaml
+ MATCH,落地-US-ISP      # sub-all-landing.yaml
```

除最后一行外**逐字节相同** —— 节点、组结构、其余全部规则完全一致。
所以：

- ❌ 不要以为 `sub-all-landing.yaml` 是旧版本或废弃文件 —— 它是**刻意维护的并列变体**
- ❌ 不要把它们合并、改名、或删掉其中任何一个
- ❌ 不要把 `sub-all-landing.yaml` 设成默认，除非用户明确要求
- ✅ 两者都由 CI 同时构建、同时推送，缺一不可

### 什么时候用哪个

```
日常所有场景            → sub.yaml
需要绝对干净的出口 IP   → sub-all-landing.yaml（临时切换，用完切回）
```

`sub-all-landing.yaml` 下刷 1 小时 4K 视频就能烧掉几十美元住宅流量，
**不要让它长期处于启用状态**。

### 两份共同点

| 项 | 说明 |
|---|---|
| 国内流量 | **都是 DIRECT**（不绕美国），由 `GEOSITE cn` / `GEOIP CN` 保证 |
| 默认落地 | `US-静态09「纽约」<PIN_LAND_IP>`（按 IP 锁定，见第 4 节） |
| 节点数 | 285 个（32 机场 + 253 住宅） |
| 规则数 | 131 条 |

---

## 2. 禁止手改本仓库

```
本仓库的 sub.yaml / sub-all-landing.yaml / README.md
全部由 CI 自动生成或维护，手动修改会在下次重建时被覆盖。
```

**要改配置，请改公开仓库 `hutaoze177/submix`**：

| 想改什么 | 改哪里 |
|---|---|
| 规则（哪些域名走住宅/机场/直连） | `rules/ai-meta.json` 的 `air` / `land` / `direct` / `raw` 段 |
| 构建流程、调度时间、产物名称 | `.github/workflows/rebuild.yml` |
| 工具逻辑、新参数 | `submix.py` |
| 落地锁定 IP、上游订阅地址 | 仓库 Secrets：`PIN_LAND` / `FRONT_URL` / `LAND_URL` |

> ⚠️ `hutaoze177/submix` 是**公开仓库**，提交前必须确认不含：
> token、住宅 IP、上游订阅域名、节点账号 ID。
> 提交前跑：`./scripts/check-secrets.sh`（pre-commit hook 也会自动拦截）

---

## 3. 架构

```
设备 ──► 前置-机场 (select)
           └─ 前置-自动 (url-test, 32 个机场节点)   ← 默认
                  │  dialer-proxy
                  ▼
         落地-US-ISP (select, 253 个住宅节点)
```

| 组 | 类型 | 作用 |
|---|---|---|
| `前置-机场` | select | 主出口选择器，默认选 `前置-自动` |
| `前置-自动` | url-test | 32 个机场节点每 300s 测速，自动选最快的 |
| `落地-US-ISP` | select | 住宅落地，**永不自动切换** |

分流策略（`sub.yaml`）：

- **AI / Meta 身份流量** → 住宅落地（锁 IP，避免账号风控）
- **其余国外流量** → 机场（省住宅流量、要速度）
- **国内** → DIRECT

具体哪些域名走住宅：见 `hutaoze177/submix` 仓库的 `rules/ai-meta.json` 的 `land` 段（约 81 条）。

---

## 4. 落地 IP 锁定

**这是账号安全的核心，改动前必须想清楚。**

- 默认首位固定为 `US-静态09「纽约」<PIN_LAND_IP>`（早期叫 `US-静态23`）
- 出口 IP 由 BrightData 账号里的 `-ip-x.x.x.x` 决定，**节点名会随上游重编号而变化，但 IP 不变**
- 因此 CI 用 **IP 锁定**（`secrets.PIN_LAND = <PIN_LAND_IP>`）而不是节点名
- `落地-US-ISP` 是 select 组，不会自动切换
- `profile.store-selected: true`：选过的节点重启后保留

> **不要随便改 `PIN_LAND`** —— 用户所有 AI 账号的出口 IP 都依赖它，
> 换 IP 可能触发账号异地风控。要换必须先问用户。

---

## 5. 客户端接入

Clash Verge / Clash Party / FlClash 均可。

**方式 A：内嵌 token 的订阅链接（推荐）**

```
https://<TOKEN>@raw.githubusercontent.com/hutaoze177/sub/main/sub.yaml
https://<TOKEN>@raw.githubusercontent.com/hutaoze177/sub/main/sub-all-landing.yaml
```

**方式 B：header 认证**

```
URL:    https://api.github.com/repos/hutaoze177/sub/contents/sub.yaml
Header: Authorization: Bearer <TOKEN>
        Accept: application/vnd.github.raw
```

**方式 C：本地文件导入** —— 下载 yaml 存到手机，客户端「从文件导入」。

> - 国内直连 `raw.githubusercontent.com` 不通，**更新订阅需在 TUN / 系统代理已运行的状态下**
> - 裸链（不带 token）返回 `404` 是私有性正常的标志，不是故障
> - **不要把带 token 的完整链接贴进聊天、文档或公开仓库**

---

## 6. 自动重建

```
仓库: hutaoze177/submix → .github/workflows/rebuild.yml
调度: UTC 03:17 和 15:17（北京时间 11:17 / 23:17）
流程: 构建 sub.yaml → 构建 sub-all-landing.yaml → 分别推送
```

GitHub 免费额度的 schedule 有 **5–8 小时延迟**，双调度就是为了保证每天至少执行一次。
手动触发：GitHub → Actions → rebuild → Run workflow。

---

## 7. 快速排查

| 现象 | 先查什么 |
|---|---|
| 订阅拉不动 | 是否开着代理；token 是否有效；`raw` 域名国内直连本来就不通 |
| 节点全部超时 | `proxy-server-nameserver` 是否被换成公共 DNS（会让 anytls/hysteria2 全挂） |
| 出口 IP 变了 | `落地-US-ISP` 首位是不是被换了；`PIN_LAND` 是否被改 |
| 流量消耗异常 | 客户端是不是切到了 `sub-all-landing.yaml` |
| 只有一份产物更新 | CI 的两个 push 步骤是否都成功 |

详见公开仓库的 `CONTRIBUTING.md` 与 `README.md`（含 8 个历史踩坑记录）。
