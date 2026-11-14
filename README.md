# submix — 链式代理订阅合成工具

把「前置机场」与「落地住宅」两份订阅合成一份 Clash/Mihomo 配置，用真内核校验后推送到
GitHub 私有仓库，供 FlClash / Clash Verge / Clash Party 以订阅链接方式拉取。

```
设备 ──► 前置-机场 (select)
           └─ 前置-自动 (url-test, 32 个机场节点)   ← 默认走这里
                  │  dialer-proxy
                  ▼
         落地-US-ISP (select, 174 个住宅节点)      ← AI / Meta 身份流量走这里
```

一句话分工：**AI 与 Meta 走住宅锁 IP，其余流量走机场省流量要速度。**

---

## 1. 仓库结构

```
submix/
├─ submix.py                 主程序（约 400 行，纯标准库 + pyyaml）
├─ rules/ai-meta.json        规则模板：哪些域名走住宅、哪些走机场
├─ .github/workflows/rebuild.yml   每日自动重建
└─ README.md
```

产物在另一个私有仓库 `hutaoze177/sub`：`sub.yaml`（客户端订阅）+ `README.md`。

---

## 2. 环境准备

```bash
pip install pyyaml

# 可选：mihomo 内核，用于 verify（务必用与客户端同版本）
# https://github.com/MetaCubeX/mihomo/releases  →  mihomo-linux-arm64-v<ver>.gz
gunzip mihomo-linux-arm64-v1.19.34.gz && chmod +x mihomo-linux-arm64-v1.19.34
sudo mv mihomo-linux-arm64-v1.19.34 /tmp/mihomo
/tmp/mihomo -v
```

token 放 `~/.gh_token`（`chmod 600`），需要 classic PAT 的 `repo` + `workflow` 两个 scope。

---

## 3. 三个子命令

`python3 submix.py {build,verify,push} -h` 随时可查。

### 3.1 build —— 合成

```bash
python3 submix.py build \
  --front air.yaml \
  --land  land.yaml \
  --rules rules/ai-meta.json \
  --pin-land "US-静态23" \
  --dns-fallback \
  -o sub.yaml
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--front` | 必填 | 前置订阅，**可重复多次**（多机场混用），接受本地文件或 URL |
| `--land` | 必填 | 落地订阅，**可重复多次**，接受本地文件或 URL |
| `-o/--output` | `sub.yaml` | 输出路径 |
| `--rules` | 无 | 规则模板 JSON；不给就只有 DIRECT/CN/MATCH 这几条兜底 |
| `--front-group` | `前置-机场` | 前置组名 |
| `--auto-group` | `前置-自动` | 自动测速子组名 |
| `--land-group` | `落地-US-ISP` | 落地组名 |
| `--pin-land` | 无 | 把名字**含该子串**的落地节点排到组首（锁出口 IP，可命中多个） |
| `--port` | `7890` | mixed-port |
| `--dns-fallback` | 关 | 给 `nameserver` 追加国内 DoH 兜底并在末尾加 `1.1.1.1#前置组` |
| `--no-dns` | 关 | ⚠️ **当前是空参数**，传了不会删 DNS 段，见第 6 节 |

支持的订阅格式（自动探测，按顺序尝试）：

1. **Clash / Mihomo YAML** —— 有 `proxies` 列表即认定
2. **base64 包裹的链接列表** —— 解出来含 `://` 再逐条解析
3. **明文链接列表** —— `vmess:// ss:// trojan:// vless://`（Clash 不认 `hy2://`，别用）

> 备注：抓订阅用的 UA 是 `submix/1.0`。少数机场按 UA 返回不同内容，
> 拉不到或节点数异常时，先用浏览器/客户端存一份本地 yaml 再走文件路径。

### 3.2 verify —— 用真内核校验（**必做**）

```bash
python3 submix.py verify -f sub.yaml --mihomo /tmp/mihomo
# 或设环境变量：export SUBMIX_MIHOMO=/tmp/mihomo
```

内部就是 `mihomo -t -f <file> -d <临时目录>`，判定条件：退出码为 0 **且** 输出含
`successful`。第一次跑会顺手下载 MMDB（几秒），可忽略那行 `Can't find MMDB`。

### 3.3 push —— 推到产物仓库

```bash
GH_TOKEN=ghp_xxx python3 submix.py push \
  -f sub.yaml --repo hutaoze177/sub --path sub.yaml
# 或用文件：--token-file ~/.gh_token   （默认就是这个路径）
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `-f` | 必填 | 要推的文件 |
| `--repo` | 必填 | `owner/repo` |
| `--path` | `sub.yaml` | 仓库内路径 |
| `--branch` | `main` | 分支 |
| `--token-file` | `~/.gh_token` | 仅当没设 `GH_TOKEN` 环境变量时才读 |
| `--message` | `update subscription via submix` | commit message |

实现走 Contents API：`GET` 拿旧 `sha` → `PUT` 带 `sha` 覆盖。**不带 `sha` 会 409/422**，
所以新文件第一次推也先 GET 一次（404 就跳过 sha）。

---

## 4. 规则模板 `rules/ai-meta.json`

```json
{
  "_comment": "元信息，程序忽略",
  "air":   ["cdn.oculus.com"],           // → DOMAIN-SUFFIX,...,<前置组>
  "land":  ["claude.ai", "fbcdn.net"],   // → DOMAIN-SUFFIX,...,<落地组>
  "raw":   ["DOMAIN,sub.your-sub-provider.example,DIRECT"],  // 原样追加
  "match": "前置-机场"                   // MATCH 兜底的组名
}
```

**展开顺序就是匹配顺序（先匹配先生效）**：

```
1. air[*]   → 前置组     ← 纯下载 CDN 放这里，压过 land
2. land[*]  → 落地组     ← AI / Meta 身份与内容 CDN
3. raw[*]   → 原样
4. GEOSITE,private,DIRECT
5. GEOIP,LAN,DIRECT,no-resolve
6. GEOSITE,cn,DIRECT
7. GEOIP,CN,DIRECT
8. MATCH,<match>
```

所以 `oculus.com` 可以在 `land` 里（走住宅），而 `cdn.oculus.com` 放 `air` 里（走机场下载），
靠 `air` 排在前面的顺序实现「同域不同子域分流」。

### 两条硬规矩

1. **同一个 App 的 API 和内容 CDN 必须同链路。** Meta 的 `meta.ai` 走住宅而
   `fbcdn.net` 走机场，会出现「API 美国 IP、图片日本 IP」，比全走机场更容易被风控。
   身份域名、Graph API、`fbcdn.net` / `cdninstagram.com` / `fbsbx.com` 一律进 `land`。
2. **`raw` 里的组名是硬编码字符串**（`前置-机场` / `落地-US-ISP`）。
   一旦用 `--front-group` / `--land-group` 改名，`raw` 里这些也要同步改，否则规则指向不存在的组，
   `mihomo -t` 会报 `proxy group [...] not found`。

维护时只改这个 JSON，然后 build + verify + push，不要手改产物 `sub.yaml`。

---

## 5. 产物长什么样

以下是实测数字（前置 32 + 落地 174 = **206 节点 / 86 规则 / ≈70 KB**）：

```
proxies
├─ 32 个前置节点   anytls 23 / hysteria2 7 / vless 2      （无 dialer-proxy）
└─ 174 个落地节点  http 174（BrightData 住宅）            （全部 dialer-proxy: 前置-机场）

proxy-groups
├─ 前置-机场  select   [前置-自动, <32 个节点按 pin 后的顺序>]
├─ 前置-自动  url-test [32 个节点]  url=gstatic generate_204, interval=300, tolerance=50, lazy
└─ 落地-US-ISP select  [<174 个节点，--pin-land 命中的在最前>]

rules  86 条
├─ 落地-US-ISP  46（45 个 land 域名 + raw 里 1 条 nodebuf.com）
├─ 前置-机场    34 + MATCH 兜底 1
├─ DIRECT       4（sub.your-sub-provider.example、private、cn、CN）
└─ no-resolve   1（GEOIP,LAN）
```

固定写死的顶层项：

```yaml
mixed-port: 7890        allow-lan: false      mode: rule
ipv6: true              log-level: warning    unified-delay: true
tcp-concurrent: true    find-process-mode: off
profile: { store-selected: true, store-fake-ip: true }
```

`store-selected: true` 很关键：客户端里手动选过的节点会持久化，重启不被冲掉。

### 输出不稳定是正常的

`hysteria2` 节点的 `hop-interval` 每次 build 都随机（订阅源给的），所以**两次构建的产物字节不同**，
diff 时只看到 `hop-interval` 差异就是没变。要判断「内容是否真的变了」，比较节点数 / 规则数 /
`proxy-groups` 顺序，而不是 md5。

---

## 6. 踩过的坑（改成条件反射）

### 坑 1：DNS 不能换成公共 DNS ⚠️ 最致命

机场节点域名（`*.tls.node.example.com`、`*.quic.node2.example.com`）必须用机场自己的私有 DoH 解析：

```
https://<机场私有 DoH 入口 1>/dns-query/<uuid>
https://<机场私有 DoH 入口 2>/dns-query/<uuid>
https://[<IPv6 入口>]/dns-query/<uuid>
```

（真实值在 `dns.proxy-server-nameserver` 里，两个 IPv4 + 一个 IPv6 入口，此处不落明文。）

换成 `223.5.5.5` 后域名会解析到 Cloudflare 中转 IP，anytls / hysteria2 **TLS 握手全挂**，
实测可用率从 26/32 掉到 **1/32**。

程序的保护：`build` 默认**整段沿用前置订阅的 `dns`**（含 `proxy-server-nameserver` 里那组私有 DoH）。
动 DNS 相关代码前先想清楚这一条。

### 坑 2：`nameserver` 全塞代理 DNS 会成环

试过只留 `https://1.1.1.1/dns-query#前置-机场`，节点全挂 —— 解析代理服务器自己的地址也要 DNS，
形成循环依赖。正确做法是保留国内 DoH 兜底：

```yaml
nameserver: ['https://223.5.5.5/dns-query', 'https://doh.pub/dns-query', 'https://1.1.1.1/dns-query#前置-机场']
```

这就是 `--dns-fallback` 干的事，别手写。

### 坑 3：落地订阅自带「前置候选」组，不能给它挂 `dialer-proxy`

虾蹬订阅里有个叫「前置-机场」的组（50 多个意大利/荷兰免费节点）。这些节点若被当落地再注入
`dialer-proxy: 前置-机场`，就是**自己指自己**（循环引用）。

程序的做法：凡组名含「前置」的组成员，从落地池里排除；`type` 为 `direct` / `reject` 的也排除。
本仓库实测会排掉 54 个。

### 坑 4：同一 App 的 API 和 CDN 必须同链路 ⚠️

抓过 `com.facebook.aura` 同一进程：`hatch-api.meta.ai` → 美国住宅，`scontent-phl2-1.xx.fbcdn.net` → 日本机场。
**这比全走机场更显眼。** 见第 4 节两条硬规矩。

### 坑 5：workflow 文件里不能有中文注释

`.github/workflows/rebuild.yml` 的 `on:` 块里带中文注释，GitHub 会**静默半残**：
网页能看到 workflow（state=active），但 dispatch 返回
`422 Workflow does not have 'workflow_dispatch' trigger`，run 记录 failure 且不产生任何 job。

现在的文件是**纯 ASCII、无注释、无 `permissions` 块**，一次通过。改这个文件时保持这样。

### 坑 6：`198.18.0.x` 是 fake-ip，不是真实地址

FlClash 重启 / 切配置后 fake-ip 映射表清空，App 还攥着旧假 IP 发包 → mihomo 查不到域名 →
所有 `DOMAIN-SUFFIX` 不命中 → 掉进 `MATCH` 走错链路。

判断方法看连接详情的上下行：

- `↑400B / ↓0B` —— 只有 TLS ClientHello，会话没建立，**无风险，可无视**
- `↑50KB / ↓800KB` —— 业务数据真的走错了，**才要处理**

试过用 `sniffer`（从 TLS SNI 还原域名）治本，用户要求回退（commit `eb16f76`，原实现在 `84d067b`）。
**除非用户主动提，不要重新启用。**

### 坑 7：`--no-dns` 是空参数（已知缺陷，待修）

`submix.py` 里：

```python
if args.no_dns and "dns" in dns:
    pass          # ← 什么都不做
```

传了不会删 `dns` 段。需要「完全不输出 DNS」时，目前只能手工在产物里删，或改这行代码。
**不要照 README 旧版的描述以为它能用。**

### 坑 8：组名改名要全链路同步

`--front-group` / `--land-group` 只改组定义，`rules/ai-meta.json` 的 `raw` 里仍写死旧名。
改名后 `mihomo -t` 报 `proxy group [xxx] not found`，客户端则表现为规则全失效。

---

## 7. GitHub Actions 自动重建

`.github/workflows/rebuild.yml`：

```yaml
name: rebuild
on:
  workflow_dispatch:
  schedule:
    - cron: "17 3 * * *"        # UTC 03:17 = 北京 11:17
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install pyyaml
      - run: python3 submix.py build --front "$FRONT" --land "$LAND" \
               --rules rules/ai-meta.json --pin-land "US-静态23" --dns-fallback -o out/sub.yaml
        env: { FRONT: "${{ secrets.FRONT_URL }}", LAND: "${{ secrets.LAND_URL }}" }
      - run: python3 submix.py push -f out/sub.yaml --repo hutaoze177/sub --path sub.yaml
        env: { GH_TOKEN: "${{ secrets.SUB_TOKEN }}" }
```

需要的 secrets（**只存名字，值不进代码**）：

| Secret | 内容 |
|---|---|
| `FRONT_URL` | 机场订阅地址 |
| `LAND_URL` | 虾蹬订阅地址 |
| `SUB_TOKEN` | 有 `hutaoze177/sub` 写权限的 PAT |

注意事项：

- 私有仓库新建后 Actions 可能默认关闭，要确认 `enabled: true`
- 手动触发：网页 → Actions → rebuild → Run workflow，或
  `gh workflow run rebuild.yml -R hutaoze177/submix`
- 云端 runner 在国外，拉两个机场订阅没问题（已验证 run #4 全绿）
- 定时任务在仓库 60 天无提交后会被 GitHub 自动暂停，届时去 Actions 页点一下 Enable

---

## 8. 验证链路是否真的通

```bash
# 单个节点延迟（mihomo 外部控制接口需开启 external-controller）
curl -s "http://127.0.0.1:9090/proxies/<组名>/delay?url=https://www.gstatic.com/generate_204&timeout=5000"

# 直接测出口 IP 有没有被目标站封
curl -x http://127.0.0.1:7890 -o /dev/null -w "%{http_code}\n" https://api.anthropic.com
```

判读 `api.anthropic.com` 的返回码：

| 码 | 含义 |
|---|---|
| `401` / `405` | ✅ 链路通，IP 未被封 |
| `403` | ⚠️ 链路通但被 Cloudflare 拦（IP 进了黑名单） |
| `000` | ❌ 链路断（节点死 / DNS 错 / 握手失败） |

住宅池里的账号有死活之分（`407 Account is suspended` 就是账号被封），**按账号判断，不按 zone**：
实测同是 `isp_proxy1`，有的活有的死。死节点要么排到组末，要么从 `land.yaml` 删掉。

---

## 9. 日常维护清单

| 要做的事 | 动作 |
|---|---|
| 新增漏网域名 | 改 `rules/ai-meta.json` 的 `land`/`air` → build → verify → push |
| 换默认落地 IP | 改 `--pin-land` 关键字；**先跟用户确认**，换 IP 会让 AI 账号看到变更 |
| 精简死节点 | 按第 8 节测完，从落地快照 `land.yaml` 删掉再 build |
| 降权 token | 换 fine-grained PAT，只授 `hutaoze177/sub` 的 `Contents: Read and write` |
| 升级内核 | 换 `/tmp/mihomo` 并重跑 verify，产物格式以客户端版本为准 |

---

## 10. 安全与敏感信息

- 产物 `sub.yaml` 含住宅代理的账号密码、机场节点凭据，**仓库必须 private**
- token 只走环境变量 / `~/.gh_token`（600），**绝不写进代码、README、commit**
- 订阅链接建议内嵌 token 形式分发（`https://<TOKEN>@raw.githubusercontent.com/...`），
  裸链应返回 `404` —— 这是私有性正常的标志，不是故障
- 国内直连 `raw.githubusercontent.com` 不通；更新订阅要在 TUN / 系统代理下进行。
  备用：`api.github.com` + `Authorization: Bearer` + `Accept: application/vnd.github.raw`
- `workflow` scope 必需，否则推 `.github/workflows/` 会被拒
