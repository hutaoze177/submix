#!/bin/sh
# 安装 git hooks：让每次提交自动追加 Device 行
set -e
cd "$(dirname "$0")/.."
REPO=$(git rev-parse --git-dir)

cat > "$REPO/hooks/prepare-commit-msg" <<'HOOK'
#!/bin/sh
# 自动在提交信息末尾追加 Device 标签（若尚未存在）
MSG_FILE="$1"
REPO_ROOT=$(git rev-parse --show-toplevel)
TAGFILE="$REPO_ROOT/.devtag"

[ -f "$TAGFILE" ] || exit 0
DEVICE=$(grep '^LABEL=' "$TAGFILE" | cut -d= -f2)
[ -z "$DEVICE" ] && exit 0

# 已有 Device 行就不重复追加
if grep -q "^Device: " "$MSG_FILE" 2>/dev/null; then
  exit 0
fi

# 空行分隔后追加
printf '\nDevice: %s\n' "$DEVICE" >> "$MSG_FILE"
HOOK
chmod +x "$REPO/hooks/prepare-commit-msg"
echo "✅ hook 已安装: $REPO/hooks/prepare-commit-msg"
