# PBK System Health

Обновлено UTC: 2026-10-03T18:18:41Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 12

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.56h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 3.50h | limit 3.0h
- Stage55 context: **STALE** | age 4.88h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 3.64h | limit 1.5h
- Stage57 international: **STALE** | age 35.46h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.43h | limit 3.0h
- Stage59 user execution: **STALE** | age 12.28h | limit 3.0h
- Stage60 forward performance: **STALE** | age 11.20h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.48h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.28h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 4.64h | limit 3.0h
- Stage66 attention board: **STALE** | age 8.28h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 5.56h | limit 3.0h
- Stage71 challengers: **STALE** | age 18.74h | limit 8.0h
- Stage71C team totals: **OK** | age 1.79h | limit 8.0h
- Stage71E double chance: **OK** | age 1.79h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.79h | limit 8.0h
- Stage71G DNB: **OK** | age 1.79h | limit 8.0h
- Stage71H readiness: **OK** | age 2.12h | limit 3.0h
- Stage71I settlement: **OK** | age 1.19h | limit 3.0h
- Stage72 data layer: **STALE** | age 1.45h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.36h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.47h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.07h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage54 odds/closing: age 3.50h > 3.00h
- **WARN** `STALE_STAGE` — Stage55 context: age 4.88h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage56 weather/XI: age 3.64h > 1.50h
- **WARN** `STALE_STAGE` — Stage57 international: age 35.46h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.43h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 12.28h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 11.20h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.48h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.67h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.28h > 3.00h
- **WARN** `STALE_STAGE` — Stage65 WATCH performance: age 4.64h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 8.28h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 5.56h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 18.74h > 8.00h
- **WARN** `STALE_STAGE` — Stage72 data layer: age 1.45h > 1.00h
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.36h > 1.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.47h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.