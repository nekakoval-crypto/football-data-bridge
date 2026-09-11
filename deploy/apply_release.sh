#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/opt/pbk/repo
DATA=/opt/pbk/data
ENV_FILE=/etc/pbk/pbk.env
STATE="$DATA/release_commit"

[ "$(id -u)" -eq 0 ] || { echo "Run as root" >&2; exit 1; }
[ -d "$REPO/.git" ] || { echo "PBK repository missing" >&2; exit 1; }

ensure_sync(){ systemctl enable --now pbk-sync.timer >/dev/null 2>&1 || true; }
trap ensure_sync EXIT

runuser -u pbk -- git -C "$REPO" fetch --quiet origin main
TARGET="$(runuser -u pbk -- git -C "$REPO" rev-parse origin/main)"
CURRENT="$(cat "$STATE" 2>/dev/null || true)"
if [ "$TARGET" = "$CURRENT" ]; then
  echo "PBK release already applied: $TARGET"
  exit 0
fi

echo "Applying PBK release $TARGET"
systemctl stop pbk-sync.timer || true
systemctl stop pbk-sync.service || true
runuser -u pbk -- git -C "$REPO" reset --hard origin/main >/dev/null

# Build and verify the new SQLite projection before restarting services.
runuser -u pbk -- env PBK_SKIP_FETCH=1 /bin/bash "$REPO/deploy/sync_data.sh"

# Validate the candidate Caddy configuration before installing it.
caddy validate --config "$REPO/deploy/Caddyfile" --envfile "$ENV_FILE" >/dev/null

# Push delivery is optional for core PBK availability. A provisioning failure must not
# take down the read-only analytical application.
PUSH_READY=0
if [ -f "$REPO/deploy/setup_push.sh" ]; then
  if /bin/bash "$REPO/deploy/setup_push.sh"; then
    PUSH_READY=1
  else
    echo "WARNING: PBK Web Push provisioning failed; core application release continues." >&2
  fi
fi

install -m 0644 "$REPO/deploy/Caddyfile" /etc/caddy/Caddyfile
install -m 0644 "$REPO/deploy/pbk-api.service" /etc/systemd/system/pbk-api.service
install -m 0644 "$REPO/deploy/pbk-sync.service" /etc/systemd/system/pbk-sync.service
install -m 0644 "$REPO/deploy/pbk-sync.timer" /etc/systemd/system/pbk-sync.timer
install -m 0644 "$REPO/deploy/pbk-release.service" /etc/systemd/system/pbk-release.service
install -m 0644 "$REPO/deploy/pbk-release.timer" /etc/systemd/system/pbk-release.timer
if [ -f "$REPO/deploy/pbk-push.service" ]; then install -m 0644 "$REPO/deploy/pbk-push.service" /etc/systemd/system/pbk-push.service; fi
if [ -f "$REPO/deploy/pbk-push.timer" ]; then install -m 0644 "$REPO/deploy/pbk-push.timer" /etc/systemd/system/pbk-push.timer; fi
systemctl daemon-reload
systemctl restart pbk-api.service
systemctl reload caddy.service
systemctl enable --now pbk-release.timer >/dev/null
ensure_sync
if [ "$PUSH_READY" -eq 1 ]; then
  systemctl enable --now pbk-push.timer >/dev/null
else
  systemctl disable --now pbk-push.timer >/dev/null 2>&1 || true
fi

for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8787/v1/health >/tmp/pbk-release-health.json; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8787/v1/health >/tmp/pbk-release-health.json
python3 - <<'PY'
import json
p=json.load(open('/tmp/pbk-release-health.json'))
if p.get('status')!='OK':
    raise SystemExit('PBK API health is not OK after release')
print('PBK release health: OK')
PY

if [ "$PUSH_READY" -eq 1 ]; then
  curl -fsS http://127.0.0.1:8787/v1/push/status >/tmp/pbk-push-status.json
  python3 - <<'PY'
import json
p=json.load(open('/tmp/pbk-push-status.json'))
if not p.get('enabled'):
    raise SystemExit('PBK push key was provisioned but API does not report push enabled')
print('PBK push status: READY')
PY
fi

printf '%s\n' "$TARGET" > "$STATE"
chown pbk:pbk "$STATE"
chmod 0640 "$STATE"
echo "PBK release applied: $TARGET"
