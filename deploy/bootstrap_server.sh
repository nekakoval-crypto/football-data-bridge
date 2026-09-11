#!/usr/bin/env bash
set -Eeuo pipefail

# PBK production bootstrap for a fresh Ubuntu/Debian VPS.
# Run as root from an interactive terminal. Secrets are entered locally and are
# never committed to GitHub.

REPO_URL="${PBK_REPO_URL:-https://github.com/nekakoval-crypto/football-data-bridge.git}"
PBK_ROOT="/opt/pbk"
REPO="$PBK_ROOT/repo"
DATA="$PBK_ROOT/data"
ENV_DIR="/etc/pbk"
ENV_FILE="$ENV_DIR/pbk.env"

fail(){ echo "ERROR: $*" >&2; exit 1; }
info(){ printf '\n==> %s\n' "$*"; }

[ "$(id -u)" -eq 0 ] || fail "Run this script as root."
[ -t 0 ] || fail "Run from an interactive terminal (do not pipe curl directly into bash)."

if [ -z "${PBK_HOST:-}" ]; then
  read -r -p "PBK domain (recommended) or public IPv4 for temporary HTTP test: " PBK_HOST
fi
[ -n "$PBK_HOST" ] || fail "PBK_HOST cannot be empty."

if [ -z "${PBK_USER:-}" ]; then
  read -r -p "PBK login name [pbk]: " PBK_USER
  PBK_USER="${PBK_USER:-pbk}"
fi
[[ "$PBK_USER" =~ ^[A-Za-z0-9._-]+$ ]] || fail "PBK login contains unsupported characters."

if python3 - "$PBK_HOST" >/dev/null 2>&1 <<'PY'
import ipaddress,sys
ipaddress.ip_address(sys.argv[1])
PY
then
  PBK_SITE="http://$PBK_HOST"
  TEMP_HTTP=1
else
  PBK_SITE="$PBK_HOST"
  TEMP_HTTP=0
fi

info "Installing base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git gpg python3 sqlite3 debian-keyring debian-archive-keyring apt-transport-https

if ! command -v caddy >/dev/null 2>&1; then
  info "Installing Caddy from its official stable repository"
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg /etc/apt/sources.list.d/caddy-stable.list
  apt-get update
  apt-get install -y caddy
fi

info "Creating restricted PBK service account"
if ! id pbk >/dev/null 2>&1; then useradd --system --home-dir "$PBK_ROOT" --create-home --shell /usr/sbin/nologin pbk; fi
install -d -o pbk -g pbk -m 0755 "$PBK_ROOT" "$REPO"
install -d -o pbk -g pbk -m 0750 "$DATA"

info "Installing/updating PBK repository"
if [ -d "$REPO/.git" ]; then
  runuser -u pbk -- git -C "$REPO" fetch --quiet origin main
  runuser -u pbk -- git -C "$REPO" reset --hard origin/main >/dev/null
else
  rm -rf "$REPO"
  install -d -o pbk -g pbk -m 0755 "$REPO"
  runuser -u pbk -- git clone --depth 1 --branch main "$REPO_URL" "$REPO"
fi

info "Creating private application password"
while :; do
  read -r -s -p "New PBK web password (minimum 12 characters): " PBK_PASSWORD; echo
  [ "${#PBK_PASSWORD}" -ge 12 ] || { echo "Password is too short." >&2; continue; }
  read -r -s -p "Repeat password: " PBK_PASSWORD_2; echo
  [ "$PBK_PASSWORD" = "$PBK_PASSWORD_2" ] || { echo "Passwords do not match." >&2; continue; }
  break
done
PBK_PASSWORD_HASH="$(printf '%s\n' "$PBK_PASSWORD" | caddy hash-password)"
unset PBK_PASSWORD PBK_PASSWORD_2

info "Writing Caddy configuration and secret environment"
install -d -m 0700 "$ENV_DIR"
cat > "$ENV_FILE" <<EOF
PBK_HOST="$PBK_SITE"
PBK_USER="$PBK_USER"
PBK_PASSWORD_HASH="$PBK_PASSWORD_HASH"
EOF
chmod 0600 "$ENV_FILE"
install -m 0644 "$REPO/deploy/Caddyfile" /etc/caddy/Caddyfile
install -d -m 0755 /etc/systemd/system/caddy.service.d
cat > /etc/systemd/system/caddy.service.d/pbk.conf <<EOF
[Service]
EnvironmentFile=$ENV_FILE
EOF

info "Installing PBK systemd units"
for f in pbk-api.service pbk-sync.service pbk-sync.timer pbk-release.service pbk-release.timer; do
  install -m 0644 "$REPO/deploy/$f" "/etc/systemd/system/$f"
done
systemctl daemon-reload

info "Building the initial verified Stage72 database"
runuser -u pbk -- /bin/bash "$REPO/deploy/sync_data.sh"
[ -s "$DATA/pbk_unified.sqlite" ] || fail "Initial SQLite database was not created."

info "Validating Caddy and starting PBK services"
caddy validate --config /etc/caddy/Caddyfile --envfile "$ENV_FILE"
systemctl enable --now pbk-api.service
systemctl enable --now pbk-sync.timer
systemctl enable --now pbk-release.timer
systemctl restart caddy

info "Running local health checks"
for _ in $(seq 1 15); do
  if curl -fsS http://127.0.0.1:8787/v1/health >/tmp/pbk-health.json; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8787/v1/health >/tmp/pbk-health.json || {
  journalctl -u pbk-api.service -n 50 --no-pager >&2 || true
  fail "PBK API health check failed."
}
python3 -m json.tool /tmp/pbk-health.json || cat /tmp/pbk-health.json
systemctl is-active --quiet pbk-api.service || fail "pbk-api.service is not active."
systemctl is-active --quiet pbk-sync.timer || fail "pbk-sync.timer is not active."
systemctl is-active --quiet pbk-release.timer || fail "pbk-release.timer is not active."
systemctl is-active --quiet caddy || fail "caddy.service is not active."

REV="$(runuser -u pbk -- git -C "$REPO" rev-parse HEAD)"
printf '%s\n' "$REV" > "$DATA/release_commit"
chown pbk:pbk "$DATA/release_commit"
chmod 0640 "$DATA/release_commit"

printf '\nPBK SERVER BOOTSTRAP: SUCCESS\n'
printf 'Site: %s\n' "$PBK_SITE"
printf 'Login: %s\n' "$PBK_USER"
printf 'API: local-only 127.0.0.1:8787\n'
printf 'Data refresh: every 5 minutes with SQLite integrity check + atomic replace\n'
printf 'Production release check: every 15 minutes with API restart + health check\n'
if [ "$TEMP_HTTP" -eq 1 ]; then
  cat <<'EOF'

IMPORTANT: this is temporary HTTP-by-IP mode only.
Do NOT use the Basic Auth password over an untrusted network.
For the real PC/Android PWA, point a domain/subdomain to this server and rerun
this bootstrap with PBK_HOST=your.domain.example to activate public HTTPS.
EOF
else
  cat <<'EOF'

HTTPS mode requested. Make sure this hostname's A/AAAA DNS record points to the
server and that inbound TCP 80/443 are open; Caddy will obtain/renew TLS.
EOF
fi
