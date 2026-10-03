# PBK System Health

Обновлено UTC: 2026-10-03T00:09:21Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.41h | limit 3.0h
- Stage55 context: **OK** | age 0.91h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.19h | limit 1.5h
- Stage57 international: **OK** | age 17.30h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 28.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 38.17h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 6.28h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.21h | limit 3.0h
- Stage66 attention board: **OK** | age 0.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.99h | limit 3.0h
- Stage71 challengers: **OK** | age 0.59h | limit 8.0h
- Stage71C team totals: **STALE** | age 11.34h | limit 8.0h
- Stage71E double chance: **STALE** | age 11.34h | limit 8.0h
- Stage71F European handicap: **STALE** | age 11.34h | limit 8.0h
- Stage71G DNB: **STALE** | age 11.34h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.47h | limit 3.0h
- Stage71I settlement: **OK** | age 1.30h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.07h | limit 1.0h
- Stage68 exposure map: **STALE** | age 16.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 28.24h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 38.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.17h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 6.28h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.78h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 11.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 11.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 11.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 11.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.47h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 16.96h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.