#!/usr/bin/env bash
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run as root" >&2; exit 1; }
REPO=/opt/pbk/repo
[ -d "$REPO/.git" ] || { echo "PBK repository missing" >&2; exit 1; }
runuser -u pbk -- git -C "$REPO" fetch --quiet origin main
runuser -u pbk -- git -C "$REPO" reset --hard origin/main >/dev/null
/bin/bash "$REPO/deploy/apply_release.sh"
echo "PBK production auto-release enabled."
