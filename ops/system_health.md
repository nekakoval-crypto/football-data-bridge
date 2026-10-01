# PBK System Health

Обновлено UTC: 2026-10-01T16:08:08Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 33.31h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.05h | limit 3.0h
- Stage59 user execution: **OK** | age 0.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 6.15h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.64h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 2.05h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 16.59h | limit 8.0h
- Stage71C team totals: **OK** | age 3.30h | limit 8.0h
- Stage71E double chance: **OK** | age 3.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.30h | limit 8.0h
- Stage71G DNB: **OK** | age 3.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.40h | limit 3.0h
- Stage71I settlement: **OK** | age 1.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.11h | limit 1.0h
- Stage73 internal API: **OK** | age 0.25h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.90h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 33.31h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 6.15h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.74h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 16.59h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.40h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.