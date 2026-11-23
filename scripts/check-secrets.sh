#!/bin/sh
# 公开仓库脱敏检查（强制）
# 用法: ./scripts/check-secrets.sh [文件...]    不带参数则扫描整个工作区
# 退出码: 0 = 干净，1 = 发现敏感信息
set -u
cd "$(dirname "$0")/.."

TARGETS="$*"
if [ -z "$TARGETS" ]; then
  # 已跟踪 + 未跟踪（不含 .gitignore 忽略项），确保新增文件也会被检查
  TARGETS=$(git ls-files; git ls-files --others --exclude-standard)
  SCAN_ALL=1
else
  SCAN_ALL=0
fi

FAIL=0
report() {
  printf '  ❌ %s:%s\n     %s\n' "$1" "$2" "$3"
  FAIL=1
}

# --- 1) 凭据类（关键字直配）---
KEYPAT='ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|brd-customer|hl_[0-9a-f]{8,}'

# --- 2) 上游订阅 / 机场基础设施域名 ---
DOMPAT='teleapi\.top|yytls\.top|yydzx\.xyz'

for f in $TARGETS; do
  [ -f "$f" ] || continue
  case "$f" in
    scripts/check-secrets.sh) continue ;;   # 本脚本自身含检测规则
  esac

  # 凭据
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    no=$(printf '%s' "$line" | cut -d: -f1)
    txt=$(printf '%s' "$line" | cut -d: -f2-)
    report "$f" "$no" "$txt"
  done <<EOF
$(grep -nIE "$KEYPAT" "$f" 2>/dev/null | head -5)
EOF

  # 域名
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    no=$(printf '%s' "$line" | cut -d: -f1)
    txt=$(printf '%s' "$line" | cut -d: -f2-)
    report "$f" "$no" "$txt"
  done <<EOF
$(grep -nIE "$DOMPAT" "$f" 2>/dev/null | head -5)
EOF

  # --- 3) 真实 IPv4：白名单之外的公网地址 ---
  while IFS= read -r ip; do
    [ -z "$ip" ] && continue
    case "$ip" in
      127.*|0.*|255.*|10.*|192.168.*|198.18.*|198.19.*) continue ;;
      1.1.1.1|1.0.0.1|223.5.5.5|223.6.6.6|8.8.8.8|8.8.4.4|9.9.9.9) continue ;;
      172.1[6-9].*|172.2[0-9].*|172.3[01].*) continue ;;
      192.0.2.*|198.51.100.*|203.0.113.*) continue ;;   # RFC5737 文档示例段
    esac
    no=$(grep -nF "$ip" "$f" 2>/dev/null | head -1 | cut -d: -f1)
    report "$f" "$no" "疑似真实 IP: $ip"
  done <<EOF
$(grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' "$f" 2>/dev/null | sort -u | head -20)
EOF
done

if [ "$FAIL" -eq 0 ]; then
  [ "$SCAN_ALL" -eq 1 ] && echo "✅ 脱敏检查通过：工作区无敏感信息" || echo "✅ 脱敏检查通过"
  exit 0
fi
echo
echo "🚫 检测到敏感信息，禁止提交。请改为占位符："
echo "   <PIN_LAND_IP> / <TOKEN> / <UPSTREAM_DOMAIN> / <ACCOUNT_ID>"
echo "   规则说明见 CONTRIBUTING.md「公开仓库脱敏（强制）」"
exit 1
