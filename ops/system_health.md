# PBK System Health

Обновлено UTC: 2026-10-14T09:13:08Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 18.97h | limit 30.0h
- Stage54 odds/closing: **OK** | age 1.24h | limit 3.0h
- Stage55 context: **OK** | age 1.77h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 2.58h | limit 1.5h
- Stage57 international: **STALE** | age 74.34h | limit 30.0h
- Stage58 daily brief: **STALE** | age 8.47h | limit 3.0h
- Stage59 user execution: **OK** | age 2.48h | limit 3.0h
- Stage60 forward performance: **STALE** | age 65.23h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 8.56h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.66h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.79h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 3.72h | limit 3.0h
- Stage66 attention board: **STALE** | age 8.53h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.43h | limit 3.0h
- Stage71 challengers: **STALE** | age 12.38h | limit 8.0h
- Stage71C team totals: **OK** | age 3.99h | limit 8.0h
- Stage71E double chance: **OK** | age 3.99h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.99h | limit 8.0h
- Stage71G DNB: **OK** | age 3.99h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.14h | limit 3.0h
- Stage71I settlement: **STALE** | age 7.82h | limit 3.0h
- Stage72 data layer: **STALE** | age 1.33h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.20h | limit 1.0h
- Stage68 exposure map: **STALE** | age 9.06h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.01h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage56 weather/XI: age 2.58h > 1.50h
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 74.34h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 8.47h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 65.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 8.56h > 2.00h
- **WARN** `STALE_STAGE` — Stage65 WATCH performance: age 3.72h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 8.53h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.43h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 12.38h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.14h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71I settlement: age 7.82h > 3.00h
- **WARN** `STALE_STAGE` — Stage72 data layer: age 1.33h > 1.00h
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.20h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 9.06h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.