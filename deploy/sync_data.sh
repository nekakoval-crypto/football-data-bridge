#!/usr/bin/env bash
set -euo pipefail

REPO=/opt/pbk/repo
DATA=/opt/pbk/data
TMP="$DATA/pbk_unified.next.sqlite"
LIVE="$DATA/pbk_unified.sqlite"

cd "$REPO"
git fetch --quiet origin main
git reset --hard origin/main >/dev/null

mkdir -p "$DATA"
rm -f "$TMP"
OPS_DIR="$REPO/ops" STAGE72_DB_PATH="$TMP" python3 "$REPO/scripts/stage72_build_data_layer.py" >/tmp/pbk-stage72-build.log

check=$(python3 - "$TMP" <<'PY'
import sqlite3,sys
p=sys.argv[1]
with sqlite3.connect(p) as c:
    print(c.execute('PRAGMA integrity_check').fetchone()[0])
PY
)

if [ "$check" != "ok" ]; then
  echo "Stage72 integrity check failed: $check" >&2
  exit 1
fi

mv -f "$TMP" "$LIVE"
chmod 640 "$LIVE"

echo "PBK data synced: $(date -Is)"
