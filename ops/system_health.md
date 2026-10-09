# PBK System Health

Обновлено UTC: 2026-10-09T22:09:14Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.48h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.34h | limit 1.5h
- Stage57 international: **STALE** | age 127.74h | limit 30.0h
- Stage58 daily brief: **STALE** | age 7.02h | limit 3.0h
- Stage59 user execution: **STALE** | age 15.07h | limit 3.0h
- Stage60 forward performance: **STALE** | age 111.06h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.56h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 5.68h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 29.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 1.07h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.95h | limit 3.0h
- Stage71 challengers: **OK** | age 6.40h | limit 8.0h
- Stage71C team totals: **OK** | age 3.34h | limit 8.0h
- Stage71E double chance: **OK** | age 3.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.34h | limit 8.0h
- Stage71G DNB: **OK** | age 3.34h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.45h | limit 3.0h
- Stage71I settlement: **OK** | age 1.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.15h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 127.74h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 7.02h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 15.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 111.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.56h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 5.68h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 29.79h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.95h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.45h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.96h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.