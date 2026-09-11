# Stage74 — выбранная архитектура приложения ПБК

## Зафиксированные решения

- Название: **ПБК**.
- Язык: русский.
- Тема: тёмная.
- Доступ: приватный, один владелец, публичной регистрации нет.
- Клиент: один responsive **PWA** для ПК и Android.
- Android APK/native wrapper: позже, поверх того же backend/API.
- Backend: существующий Stage73 read-only HTTP API.
- Data layer: Stage72 SQLite, пересобираемая из operational ledgers.
- Production host: **Hetzner Cloud, Germany, CX23-class**.
- Reverse proxy / TLS / access gate: Caddy.
- Клиент никогда не получает API-Football secret.

## Production layout

```text
GitHub Actions / operational ledgers
             |
             v
      public/private git repo
             |
      pbk-sync.timer (5 min)
             |
             v
 /opt/pbk/data/pbk_unified.sqlite
             |
       Stage73 API :8787
             |
        Caddy / HTTPS
          /api/*  +  /
             |
             v
        PBK responsive PWA
         PC + Android
```

## Why a VPS

PBK is not a static dashboard. It needs a persistent API, SQLite projection, background refresh, later bookmaker adapters, backups and push/notification workers. A small VPS keeps those pieces under one operational model and avoids serverless/runtime limits.

## Files

- `app/` — PWA frontend.
- `deploy/Caddyfile` — HTTPS/static frontend/reverse proxy/private access.
- `deploy/pbk-api.service` — Stage73 long-running service.
- `deploy/pbk-sync.service` + `.timer` — atomic data refresh every 5 minutes.
- `deploy/sync_data.sh` — fetch main, rebuild Stage72 into a temporary DB, run SQLite integrity check, then atomically promote the DB.

## Initial access model

Caddy HTTP Basic Auth is the bootstrap owner-only gate. It protects both UI and API. A custom in-app session/login can replace it later without changing Stage72/73.

## DNS / HTTPS

Before phone installation, use a real HTTPS hostname. A domain is not needed while developing the repository, but will be acquired/configured before production PWA install. Caddy then manages TLS automatically.

## Server bootstrap checklist

1. Create Ubuntu LTS Hetzner CX23-class server in Germany.
2. Add SSH key; disable password SSH login after validation.
3. Create non-root `pbk` user.
4. Install `git`, `python3`, `sqlite3`, `caddy`.
5. Clone repo to `/opt/pbk/repo` and create `/opt/pbk/data`.
6. Generate Caddy password hash and configure `PBK_HOST`, `PBK_USER`, `PBK_PASSWORD_HASH` in a root-owned environment file.
7. Copy systemd units from `deploy/`, enable `pbk-api.service` and `pbk-sync.timer`.
8. Install Caddyfile, expose only SSH/HTTP/HTTPS via firewall.
9. Point DNS to server; validate HTTPS.
10. Open the PWA on PC and Android and install from browser.

## Security invariants

- `API_FOOTBALL_KEY` is never sent to browser/PWA.
- Stage73 remains read-only.
- UI cannot change R eligibility, thresholds, exposure or settlement.
- Working SQLite is read-only for the API process and replaced atomically by the sync job.
- No public registration in v1.

## First UI scope

`Сегодня`, `R1/R2/R3`, `WATCH`, `Матчи`, `Health` are implemented first. The source for the Today screen is Stage66 via `/api/v1/attention`, preserving RED/ORANGE/BLUE/GRAY semantics and `market_cards` as MARKET VIEW ONLY.

Next UI increments: match drill-down, context, lifecycle timeline, results/performance, statistics, filters, notifications.
