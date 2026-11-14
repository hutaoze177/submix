# submix — 链式代理订阅合成工具

把「前置机场」与「落地节点」两份订阅合成一份 Clash/Mihomo 配置，并推送到 GitHub 私有仓库。

```
设备 → 前置机场(url-test) → 落地节点(dialer-proxy) → 目标
```

## 固化的四个坑

1. **DNS 沿用前置订阅**：机场域名必须用它自己的私有 DoH 解析，换成公共 DNS 会让
   anytls / hysteria2 全部 TLS 握手失败（曾从 26/32 掉到 1/32）。
2. **落地节点自动注入 `dialer-proxy`**，统一指向前置组。
3. **自动排除落地订阅自带的前置候选节点**，避免 `dialer-proxy` 自己指自己。
4. **输出前用真 mihomo 内核校验**。

## 用法

### 合成

```bash
python3 submix.py build \
  --front air.yaml \                 # 前置订阅：本地文件或 URL，可多次
  --land land.yaml \                 # 落地订阅：本地文件或 URL，可多次
  --rules rules/ai-meta.json \       # 规则模板
  --pin-land "US-静态23" \           # 锁定出口节点（排到组首）
  --dns-fallback \                   # 前置 DNS 缺 nameserver 时补兜底
  -o sub.yaml
```

支持三种订阅格式：Clash/Mihomo YAML、base64 编码的链接列表、明文 `vmess:// ss:// trojan:// vless://`。

### 校验

```bash
python3 submix.py verify -f sub.yaml --mihomo /tmp/mihomo
```

### 推送

```bash
GH_TOKEN=ghp_xxx python3 submix.py push \
  -f sub.yaml --repo hutaoze177/sub --path sub.yaml
# 或 --token-file ~/.gh_token
```

## 规则模板

`rules/ai-meta.json`：

```json
{
  "air":   ["cdn.oculus.com", "dl.oculus.com"],   // 走机场（纯下载 CDN）
  "land":  ["claude.ai", "meta.ai", "fbcdn.net"], // 走住宅
  "raw":   ["DOMAIN,sub.your-sub-provider.example,DIRECT"],    // 原样追加
  "match": "前置-机场"                             // MATCH 兜底
}
```

**关键原则**：同一个 App 的 API 和内容 CDN 必须走同一条链路。Meta 的 `fbcdn.net`
如果不跟 `meta.ai` 一起走住宅，就会出现"API 用美国 IP、图片用日本 IP"，比全走机场更显眼。

## 依赖

- Python 3.9+、`pyyaml`
- 可选：mihomo 二进制（校验用），`--mihomo` 指定或设 `SUBMIX_MIHOMO`

## 实测背景

用 32 节点机场 + 172 节点 BrightData 住宅池验证：26/32 机场节点可用，
`api.anthropic.com` 返回 405（链路可达、IP 未被封），生成配置过 `mihomo -t`。
