# PBK System Health

Обновлено UTC: 2026-10-09T17:09:24Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 10.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **STALE** | age 122.74h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.02h | limit 3.0h
- Stage59 user execution: **STALE** | age 10.08h | limit 3.0h
- Stage60 forward performance: **STALE** | age 106.06h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.56h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.68h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 24.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.25h | limit 3.0h
- Stage66 attention board: **STALE** | age 6.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **OK** | age 1.40h | limit 8.0h
- Stage71C team totals: **OK** | age 4.30h | limit 8.0h
- Stage71E double chance: **OK** | age 4.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.30h | limit 8.0h
- Stage71G DNB: **OK** | age 4.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.40h | limit 3.0h
- Stage71I settlement: **OK** | age 0.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.21h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **STALE** | age 24.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.01h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 122.74h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 10.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 106.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 24.79h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 6.09h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.40h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 24.91h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.