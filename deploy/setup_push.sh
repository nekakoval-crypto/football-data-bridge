#!/usr/bin/env bash
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run as root" >&2; exit 1; }

REPO=/opt/pbk/repo
ROOT=/opt/pbk
DATA=/opt/pbk/data
VENV=/opt/pbk/venv
REQ="$REPO/deploy/requirements-push.txt"
REQ_HASH="$DATA/push_requirements.sha256"
PRIVATE="$DATA/vapid_private.pem"
PUBLIC="$DATA/vapid_public.txt"

[ -f "$REQ" ] || { echo "Push requirements file missing" >&2; exit 1; }

if ! command -v openssl >/dev/null 2>&1 || [ ! -x "$VENV/bin/python" ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update >/dev/null
  apt-get install -y python3-venv openssl >/dev/null
fi

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi

NEW_HASH="$(sha256sum "$REQ" | awk '{print $1}')"
OLD_HASH="$(cat "$REQ_HASH" 2>/dev/null || true)"
if [ "$NEW_HASH" != "$OLD_HASH" ] || ! "$VENV/bin/python" -c 'import pywebpush' >/dev/null 2>&1; then
  "$VENV/bin/pip" install --disable-pip-version-check --no-cache-dir -r "$REQ" >/dev/null
  printf '%s\n' "$NEW_HASH" > "$REQ_HASH"
fi

if [ ! -s "$PRIVATE" ]; then
  umask 077
  openssl ecparam -name prime256v1 -genkey -noout -out "$PRIVATE"
fi

if [ ! -s "$PUBLIC" ]; then
  "$VENV/bin/python" - "$PRIVATE" > "$PUBLIC" <<'PY'
import base64,sys
from cryptography.hazmat.primitives.serialization import load_pem_private_key
p=sys.argv[1]
with open(p,'rb') as f:
    key=load_pem_private_key(f.read(),password=None)
n=key.public_key().public_numbers()
raw=b'\x04'+n.x.to_bytes(32,'big')+n.y.to_bytes(32,'big')
print(base64.urlsafe_b64encode(raw).rstrip(b'=').decode())
PY
fi

install -d -o pbk -g pbk -m 0750 "$DATA"
chown pbk:pbk "$PRIVATE" "$PUBLIC" "$REQ_HASH"
chmod 0600 "$PRIVATE"
chmod 0640 "$PUBLIC" "$REQ_HASH"

echo "PBK PUSH SETUP: OK"
echo "Public VAPID key: $(cat "$PUBLIC")"
