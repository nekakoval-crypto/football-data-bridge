# PBK System Health

Обновлено UTC: 2026-10-05T22:08:20Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.42h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.24h | limit 3.0h
- Stage55 context: **OK** | age 0.55h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.29h | limit 1.5h
- Stage57 international: **STALE** | age 31.72h | limit 30.0h
- Stage58 daily brief: **STALE** | age 14.95h | limit 3.0h
- Stage59 user execution: **STALE** | age 4.16h | limit 3.0h
- Stage60 forward performance: **STALE** | age 15.04h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 5.65h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 15.68h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.05h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 10.94h | limit 3.0h
- Stage71 challengers: **STALE** | age 25.33h | limit 8.0h
- Stage71C team totals: **OK** | age 3.30h | limit 8.0h
- Stage71E double chance: **OK** | age 3.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.30h | limit 8.0h
- Stage71G DNB: **OK** | age 3.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.40h | limit 3.0h
- Stage71I settlement: **STALE** | age 5.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.10h | limit 1.0h
- Stage68 exposure map: **STALE** | age 15.85h | limit 3.0h
- Stage69 promotion gate: **STALE** | age 3.99h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 31.72h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 14.95h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 4.16h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 15.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 5.65h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 15.68h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 10.94h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 25.33h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.40h > 3.00h
- **WARN** `STALE_STAGE` — Stage71I settlement: age 5.22h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 15.85h > 3.00h
- **WARN** `STALE_STAGE` — Stage69 promotion gate: age 3.99h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.