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

# 脱敏拦截：提交前扫描暂存内容，命中敏感信息直接拒绝
cat > "$REPO/hooks/pre-commit" <<'HOOK2'
#!/bin/sh
# 公开仓库脱敏拦截（由 scripts/install-hooks.sh 安装）
ROOT=$(git rev-parse --show-toplevel)
[ -x "$ROOT/scripts/check-secrets.sh" ] || exit 0
STAGED=$(git diff --cached --name-only --diff-filter=ACM)
[ -z "$STAGED" ] && exit 0
cd "$ROOT" && ./scripts/check-secrets.sh $STAGED
HOOK2
chmod +x "$REPO/hooks/pre-commit"

echo "✅ hook 已安装: $REPO/hooks/prepare-commit-msg"
echo "✅ hook 已安装: $REPO/hooks/pre-commit（脱敏拦截）"
