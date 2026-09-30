# PBK System Health

Обновлено UTC: 2026-09-30T01:08:30Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 18.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.25h | limit 3.0h
- Stage55 context: **OK** | age 0.71h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.28h | limit 1.5h
- Stage57 international: **OK** | age 18.32h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.08h | limit 3.0h
- Stage59 user execution: **STALE** | age 8.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 3.22h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.12h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.58h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.09h | limit 3.0h
- Stage66 attention board: **OK** | age 0.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.92h | limit 3.0h
- Stage71 challengers: **OK** | age 1.61h | limit 8.0h
- Stage71C team totals: **OK** | age 0.33h | limit 8.0h
- Stage71E double chance: **OK** | age 0.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.33h | limit 8.0h
- Stage71G DNB: **OK** | age 0.33h | limit 8.0h
- Stage71H readiness: **OK** | age 0.41h | limit 3.0h
- Stage71I settlement: **OK** | age 0.20h | limit 3.0h
- Stage72 data layer: **OK** | age 0.53h | limit 1.0h
- Stage73 internal API: **OK** | age 0.45h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 8.18h > 3.00h
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 3.22h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.