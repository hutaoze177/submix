#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
submix —— 链式代理订阅合成工具

把「前置机场」与「落地节点」两份订阅合成一份 Clash/Mihomo 配置：
  设备 → 前置机场(url-test) → 落地节点(dialer-proxy) → 目标

固化了踩过的坑：
  1. DNS 必须沿用前置订阅的 nameserver-policy（换公共 DNS 会让 anytls/hysteria2 全挂）
  2. 落地节点自动注入 dialer-proxy，指向前置组
  3. 同一 App 的 API 与 CDN 必须走同一条链路（否则 IP 分叉，比全走机场更显眼）
  4. 输出前用真 mihomo 内核校验

用法：
  python3 submix.py build --front air.yaml --land land.yaml -o sub.yaml
  python3 submix.py build --front https://机场订阅 --land ./落地.yaml --rules rules/ai-meta.json -o sub.yaml
  python3 submix.py push  -f sub.yaml --repo user/repo --token-file ~/.gh_token
  python3 submix.py verify -f sub.yaml --mihomo /tmp/mihomo
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

try:
    import yaml
except ImportError:
    sys.exit("缺少依赖：pip install pyyaml")


# ---------------------------------------------------------------- 订阅载入

def _fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "submix/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _parse_links(text):
    """把 vmess/ss/trojan/vless 链接解析成 Clash proxy 字典。"""
    out = []
    for raw in re.findall(r"(?:vmess|ss|trojan|vless)://[^\s]+", text):
        try:
            scheme, body = raw.split("://", 1)
            if scheme == "vmess":
                j = json.loads(base64.b64decode(body + "=" * (-len(body) % 4)))
                name = j.get("ps") or f"vmess-{j.get('add')}"
                p = {"name": name, "type": "vmess", "server": j["add"], "port": int(j["port"]),
                     "uuid": j["id"], "alterId": int(j.get("aid", 0)),
                     "cipher": j.get("scy") or "auto", "udp": True}
                if j.get("tls") == "tls":
                    p["tls"] = True
                    if j.get("sni") or j.get("host"):
                        p["servername"] = j.get("sni") or j.get("host")
                net = j.get("net")
                if net in ("ws", "grpc", "h2"):
                    p["network"] = net
                    if net == "ws":
                        p["ws-opts"] = {"path": j.get("path") or "/", "headers": {}}
                        if j.get("host"):
                            p["ws-opts"]["headers"]["Host"] = j["host"]
                out.append(p)
            elif scheme == "ss":
                main, _, tail = body.partition("#")
                name = urllib.parse.unquote(tail) if tail else None
                if "@" in main:
                    userinfo, hostport = main.rsplit("@", 1)
                    try:
                        dec = base64.b64decode(userinfo + "=" * (-len(userinfo) % 4)).decode()
                    except Exception:
                        dec = urllib.parse.unquote(userinfo)
                    method, _, password = dec.partition(":")
                else:
                    dec = base64.b64decode(main + "=" * (-len(main) % 4)).decode()
                    method, _, rest = dec.partition(":")
                    password, _, hostport = rest.rpartition("@")
                host, _, port = hostport.partition(":")
                out.append({"name": name or f"ss-{host}", "type": "ss", "server": host,
                            "port": int(port), "cipher": method, "password": password, "udp": True})
            elif scheme == "trojan":
                main, _, tail = body.partition("#")
                name = urllib.parse.unquote(tail) if tail else None
                pemain, _, hostport = main.partition("@")
                hostport = hostport.split("?")[0]
                host, _, port = hostport.partition(":")
                out.append({"name": name or f"trojan-{host}", "type": "trojan", "server": host,
                            "port": int(port), "password": pemain, "udp": True,
                            "skip-cert-verify": True})
            elif scheme == "vless":
                main, _, tail = body.partition("#")
                name = urllib.parse.unquote(tail) if tail else None
                pemain, _, rest = main.partition("@")
                hostport, _, query = rest.partition("?")
                q = dict(urllib.parse.parse_qsl(query))
                host, _, port = hostport.partition(":")
                p = {"name": name or f"vless-{host}", "type": "vless", "server": host,
                     "port": int(port), "uuid": pemain, "udp": True}
                if q.get("security") == "tls":
                    p["tls"] = True
                    if q.get("sni"):
                        p["servername"] = q["sni"]
                if q.get("type") in ("ws", "grpc"):
                    p["network"] = q["type"]
                out.append(p)
        except Exception:
            continue
    return out


def load_source(src):
    """载入一份订阅，返回 (clash_dict, kind)。支持本地文件 / URL / base64 / 链接列表。"""
    if re.match(r"^https?://", src):
        data = _fetch(src)
        origin = src
    else:
        if not os.path.exists(src):
            sys.exit(f"订阅文件不存在：{src}")
        data = open(src, "rb").read()
        origin = src

    text = data.decode("utf-8", "replace")

    # 1) Clash / Mihomo YAML
    try:
        d = yaml.safe_load(text)
        if isinstance(d, dict) and isinstance(d.get("proxies"), list):
            return d, "clash"
    except Exception:
        pass

    # 2) base64 包裹的链接列表
    s = re.sub(r"\s+", "", text)
    if re.fullmatch(r"[A-Za-z0-9+/=_-]{32,}", s):
        try:
            dec = base64.b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", "replace")
            if "://" in dec:
                nodes = _parse_links(dec)
                if nodes:
                    return {"proxies": nodes}, "base64-links"
        except Exception:
            pass

    # 3) 明文链接列表
    nodes = _parse_links(text)
    if nodes:
        return {"proxies": nodes}, "links"

    sys.exit(f"无法识别订阅格式：{origin}")


# ---------------------------------------------------------------- 合成

def _uniq(nodes):
    seen, out = set(), []
    for n in nodes:
        name = n.get("name")
        if not name:
            continue
        base, i = name, 2
        while name in seen:
            name = f"{base} #{i}"
            i += 1
        n = dict(n, name=name)
        seen.add(name)
        out.append(n)
    return out


def build(args):
    front_nodes, land_nodes = [], []
    front_dns = None
    for src in args.front:
        d, kind = load_source(src)
        px = d.get("proxies") or []
        front_nodes += px
        if front_dns is None and isinstance(d.get("dns"), dict):
            front_dns = d["dns"]
        print(f"  前置 {src} ({kind}) → {len(px)} 个节点")
    for src in args.land:
        d, kind = load_source(src)
        # 落地订阅常自带一组"前置候补"节点，它们不能再挂 dialer-proxy（否则自己指自己）
        excluded = set()
        for g in (d.get("proxy-groups") or []):
            if "前置" in str(g.get("name", "")):
                excluded.update(g.get("proxies") or [])
        raw = [p for p in (d.get("proxies") or [])
               if p.get("type") not in ("direct", "reject")]
        px = [p for p in raw if p.get("name") not in excluded]
        land_nodes += px
        skip = len(raw) - len(px)
        print(f"  落地 {src} ({kind}) → {len(px)} 个节点"
              + (f"（已排除 {skip} 个自带前置）" if skip else ""))

    if not front_nodes:
        sys.exit("前置订阅里没有节点")
    if not land_nodes:
        sys.exit("落地订阅里没有节点")

    # 落地节点统一注入 dialer-proxy；如落地源自带的组引用了它自己，这里直接覆盖
    land_clean = []
    for p in land_nodes:
        q = {k: v for k, v in p.items() if k != "dialer-proxy"}
        q["dialer-proxy"] = args.front_group
        land_clean.append(q)

    front_nodes = _uniq(front_nodes)
    land_clean = _uniq(land_clean)
    proxies = front_nodes + land_clean
    fnames = [p["name"] for p in front_nodes]
    lnames = [p["name"] for p in land_clean]

    if args.pin_land:
        hit = [n for n in lnames if args.pin_land in n]
        if hit:
            for n in hit:
                lnames.remove(n)
            lnames = hit + lnames
            print(f"  落地置顶：{hit[0]}")

    # DNS：默认沿用前置订阅（这是 anytls/hysteria2 能连上的前提）
    dns = dict(front_dns or {})
    if args.dns_fallback:
        ns = list(dns.get("nameserver") or [])
        for s in ("https://223.5.5.5/dns-query", "https://doh.pub/dns-query"):
            if s not in ns:
                ns.append(s)
        # 干净的 DoH 放最后、经前置出网
        ns.append(f"https://1.1.1.1/dns-query#{args.front_group}")
        dns["nameserver"] = ns
    if args.no_dns and "dns" in dns:
        pass

    cfg = {
        "mixed-port": args.port,
        "allow-lan": False,
        "mode": "rule",
        "ipv6": True,
        "log-level": "warning",
        "unified-delay": True,
        "tcp-concurrent": True,
        "find-process-mode": "off",
        "profile": {"store-selected": True, "store-fake-ip": True},
    }
    if dns:
        cfg["dns"] = dns

    # 域名嗅探：App 拿着 fake-ip / 纯 IP 发起连接时，从 TLS SNI 或 HTTP Host
    # 还原出真实域名，再按 DOMAIN-SUFFIX 规则匹配。
    # 没有这个，fake-ip 映射表一旦丢失就会退化到 MATCH 兜底（走错链路）。
    cfg["sniffer"] = {
        "enable": True,
        "parse-pure-ip": True,
        "override-destination": False,
        "sniff": {
            "HTTP": {"ports": [80, "8080-8880"], "override-destination": True},
            "TLS": {"ports": [443, 8443]},
            "QUIC": {"ports": [443, 8443]},
        },
        "skip-domain": ["+.push.apple.com", "+.apple.com", "Mijia Cloud"],
    }

    cfg["proxies"] = proxies
    cfg["proxy-groups"] = [
        {"name": args.front_group, "type": "select", "proxies": [args.auto_group] + fnames},
        {"name": args.auto_group, "type": "url-test",
         "url": "https://www.gstatic.com/generate_204", "interval": 300,
         "tolerance": 50, "lazy": True, "proxies": fnames},
        {"name": args.land_group, "type": "select", "proxies": lnames},
    ]
    cfg["rules"] = make_rules(args)

    out = args.output
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, width=4096)
    print(f"\n  输出 {out}：{os.path.getsize(out)} 字节 | 节点 {len(proxies)} | 规则 {len(cfg['rules'])}")
    return cfg


def make_rules(args):
    """规则模板 + 兜底。"""
    rules = []
    spec = None
    if args.rules:
        with open(args.rules, encoding="utf-8") as f:
            spec = json.load(f)

    if spec:
        # 机场优先的纯下载 CDN 放最前（先匹配先生效）
        for d in spec.get("air", []):
            rules.append(f"DOMAIN-SUFFIX,{d},{args.front_group}")
        for d in spec.get("land", []):
            rules.append(f"DOMAIN-SUFFIX,{d},{args.land_group}")
        for r in spec.get("raw", []):
            rules.append(r)
        match = spec.get("match", args.front_group)
    else:
        match = args.front_group

    rules.append("GEOSITE,private,DIRECT")
    rules.append("GEOIP,LAN,DIRECT,no-resolve")
    rules.append("GEOSITE,cn,DIRECT")
    rules.append("GEOIP,CN,DIRECT")
    rules.append(f"MATCH,{match}")
    return rules


# ---------------------------------------------------------------- 校验

def verify(args):
    mihomo = args.mihomo or os.environ.get("SUBMIX_MIHOMO", "mihomo")
    workdir = tempfile.mkdtemp(prefix="submix-")
    try:
        r = subprocess.run([mihomo, "-t", "-f", args.file, "-d", workdir],
                           capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        sys.exit(f"找不到 mihomo 内核：{mihomo}（用 --mihomo 指定或设置 SUBMIX_MIHOMO）")
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    for line in tail:
        print("  " + line)
    ok = r.returncode == 0 and "successful" in (r.stdout + r.stderr)
    print("  " + ("✅ 校验通过" if ok else "❌ 校验失败"))
    return 0 if ok else 1


# ---------------------------------------------------------------- 推送

def push(args):
    token = os.environ.get("GH_TOKEN")
    if not token and args.token_file:
        token = open(os.path.expanduser(args.token_file)).read().strip()
    if not token:
        sys.exit("缺少 token：设置 GH_TOKEN 或用 --token-file")

    repo, branch = args.repo, args.branch
    path = args.path
    content = open(args.file, "rb").read()
    api = f"https://api.github.com/repos/{repo}/contents/{path}"
    hdr = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
           "User-Agent": "submix/1.0"}

    def call(method, url, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=hdr, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    status, meta = call("GET", f"{api}?ref={branch}")
    payload = {"message": args.message, "content": base64.b64encode(content).decode(),
               "branch": branch}
    if status == 200:
        payload["sha"] = meta["sha"]
    code, res = call("PUT", api, payload)
    if code in (200, 201):
        print(f"  ✅ 已推送 {repo}:{path} @ {branch}")
        return 0
    print(f"  ❌ 推送失败 {code}: {json.dumps(res, ensure_ascii=False)[:200]}")
    return 1


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(prog="submix", description="链式代理订阅合成工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="合成配置")
    b.add_argument("--front", action="append", required=True, help="前置订阅（文件/URL，可多次）")
    b.add_argument("--land", action="append", required=True, help="落地订阅（文件/URL，可多次）")
    b.add_argument("-o", "--output", default="sub.yaml")
    b.add_argument("--rules", help="规则模板 JSON")
    b.add_argument("--front-group", default="前置-机场")
    b.add_argument("--auto-group", default="前置-自动")
    b.add_argument("--land-group", default="落地-US-ISP")
    b.add_argument("--pin-land", help="把名字含该字符串的落地节点置顶（锁定出口 IP）")
    b.add_argument("--port", type=int, default=7890)
    b.add_argument("--dns-fallback", action="store_true",
                   help="给 nameserver 追加国内 DoH 兜底（前置 DNS 缺 nameserver 时用）")
    b.add_argument("--no-dns", action="store_true")

    v = sub.add_parser("verify", help="用 mihomo 内核校验")
    v.add_argument("-f", "--file", required=True)
    v.add_argument("--mihomo")

    p = sub.add_parser("push", help="推送到 GitHub 仓库")
    p.add_argument("-f", "--file", required=True)
    p.add_argument("--repo", required=True, help="owner/repo")
    p.add_argument("--path", default="sub.yaml")
    p.add_argument("--branch", default="main")
    p.add_argument("--token-file", default="~/.gh_token")
    p.add_argument("--message", default="update subscription via submix")

    args = ap.parse_args()
    if args.cmd == "build":
        build(args)
        return 0
    if args.cmd == "verify":
        return verify(args)
    if args.cmd == "push":
        return push(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
