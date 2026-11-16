#!/bin/sh
# 带设备标签的 git 提交助手
# 用法: ./scripts/commit.sh "type: 标题" [-m 正文...]
# 会自动在提交信息末尾追加 Device: 行
set -e
cd "$(dirname "$0")/.."

if [ ! -f .devtag ]; then
  echo "缺少 .devtag，请先运行: python3 submix.py --help 或手动创建" >&2
  exit 1
fi
DEVICE=$(grep '^LABEL=' .devtag | cut -d= -f2)
[ -z "$DEVICE" ] && { echo ".devtag 里没有 LABEL" >&2; exit 1; }

if [ $# -eq 0 ]; then
  echo "用法: $0 \"type: 标题\" [-m 正文]" >&2
  exit 1
fi

TITLE="$1"; shift
MSG="$TITLE

$*

Device: $DEVICE"

git commit -F - <<EOF
$MSG
EOF
echo "✅ 已提交（含 Device: $DEVICE）"
git log -1 --format="   %h | %an | %s"
