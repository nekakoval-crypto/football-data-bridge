# PBK System Health

Обновлено UTC: 2026-09-30T18:09:02Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **OK** | age 11.33h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 25.19h | limit 3.0h
- Stage60 forward performance: **STALE** | age 20.23h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.18h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.71h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.16h | limit 3.0h
- Stage66 attention board: **OK** | age 0.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.98h | limit 3.0h
- Stage71 challengers: **STALE** | age 18.62h | limit 8.0h
- Stage71C team totals: **OK** | age 5.30h | limit 8.0h
- Stage71E double chance: **OK** | age 5.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.30h | limit 8.0h
- Stage71G DNB: **OK** | age 5.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.39h | limit 3.0h
- Stage71I settlement: **OK** | age 1.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.19h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 25.19h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 20.23h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.72h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 18.62h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.39h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.