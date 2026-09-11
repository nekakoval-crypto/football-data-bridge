# Stage74F — PBK production server bootstrap

Status: **READY FOR OWNER SERVER CREATION**.

This is the first Stage74 point that requires an external resource owned by the project owner: a permanent public Linux VPS. Everything before this point can run from GitHub Actions/local CI without owner intervention.

## Target server

Recommended initial production shape:

- Provider: Hetzner Cloud, Germany.
- Server class: CX23 or current equivalent small shared x86 plan.
- OS: Ubuntu 24.04 LTS or newer supported Ubuntu LTS.
- Public networking: IPv4 + IPv6.
- No extra volume is required initially.
- Server name: `pbk-prod`.
- Inbound firewall: TCP 22, 80 and 443. API port 8787 must **not** be exposed publicly.

The server can be resized later without changing PBK architecture.

## Security boundary

Never send the server root password, PBK web password, API keys, SSH private key or other secrets into chat/GitHub.

Safe information to share for guided setup:

- public server IPv4/IPv6;
- server hostname/domain;
- screenshots of non-secret provider settings;
- command output with secrets removed.

The PBK web password is entered directly on the VPS during bootstrap and only its hash is written to `/etc/pbk/pbk.env`.

## First install

From the fresh server's root shell:

```bash
curl -fsSLo /root/pbk-bootstrap.sh https://raw.githubusercontent.com/nekakoval-crypto/football-data-bridge/main/deploy/bootstrap_server.sh
chmod 700 /root/pbk-bootstrap.sh
less /root/pbk-bootstrap.sh
/root/pbk-bootstrap.sh
```

Do not use `curl | bash`; the bootstrap intentionally requires an interactive terminal so credentials are entered locally.

The script:

1. installs Git/Python/SQLite and the official stable Caddy package;
2. creates a restricted `pbk` service account;
3. clones/updates the PBK repository;
4. asks locally for the private web login/password and stores only the password hash;
5. installs Caddy + systemd configuration;
6. builds the Stage72 SQLite database into a temporary file;
7. runs SQLite `integrity_check` and only then atomically promotes the DB to live;
8. starts the read-only Stage74 API bound only to `127.0.0.1:8787`;
9. enables five-minute data refresh;
10. runs local health checks before declaring success.

## Domain / HTTPS

For the real PC/Android PWA, use a public domain or subdomain whose A/AAAA records point to the VPS. Caddy will then provision and renew HTTPS automatically when TCP 80/443 are reachable.

A raw public IP can be supplied to the bootstrap only for temporary server-side/connectivity testing. The script converts a raw IP to explicit HTTP mode and warns that Basic Auth must not be used over an untrusted plain-HTTP connection. Do not install/use the production PWA that way.

## Expected services

- `pbk-api.service` — read-only app API on `127.0.0.1:8787`.
- `pbk-sync.timer` — refreshes repository/data every five minutes.
- `caddy.service` — private web access, HTTPS and reverse proxy `/api/*`.

Useful checks:

```bash
systemctl status pbk-api.service --no-pager
systemctl status pbk-sync.timer --no-pager
systemctl status caddy --no-pager
curl -fsS http://127.0.0.1:8787/v1/health | python3 -m json.tool
```

## Recovery rule

The server is disposable infrastructure, not the source of truth. Operational source files remain in GitHub; the live SQLite database is rebuilt from them. If the VPS is lost, create a clean server and rerun the bootstrap instead of trying to reconstruct PBK manually.
