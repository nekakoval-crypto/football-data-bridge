# PBK System Health

Обновлено UTC: 2026-10-01T19:08:02Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 12.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.28h | limit 3.0h
- Stage55 context: **OK** | age 0.75h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **STALE** | age 36.31h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 9.15h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.25h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.24h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 19.59h | limit 8.0h
- Stage71C team totals: **OK** | age 6.30h | limit 8.0h
- Stage71E double chance: **OK** | age 6.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 6.30h | limit 8.0h
- Stage71G DNB: **OK** | age 6.30h | limit 8.0h
- Stage71H readiness: **OK** | age 0.43h | limit 3.0h
- Stage71I settlement: **OK** | age 0.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.47h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.90h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 36.31h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 9.15h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.14h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.25h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.74h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.95h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 19.59h > 8.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.90h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.