#!/usr/bin/env bash
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run as root" >&2; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ufw fail2ban unattended-upgrades

# Small VPS safety: add 1 GiB swap only when no swap exists.
if ! swapon --show=NAME --noheadings | grep -q .; then
  fallocate -l 1G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1024
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Firewall: keep the current SSH path open before enabling the firewall.
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw --force enable >/dev/null

cat > /etc/fail2ban/jail.d/pbk-sshd.conf <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

echo 'PBK SERVER HARDENING: OK'
echo 'Firewall: SSH + 80/tcp + 443/tcp only'
echo 'Fail2ban: sshd enabled'
echo 'Swap:'
swapon --show
echo 'UFW:'
ufw status
