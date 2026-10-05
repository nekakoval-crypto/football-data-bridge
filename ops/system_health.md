# PBK System Health

Обновлено UTC: 2026-10-05T03:08:45Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.46h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **OK** | age 12.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 16.17h | limit 3.0h
- Stage59 user execution: **STALE** | age 9.00h | limit 3.0h
- Stage60 forward performance: **STALE** | age 32.40h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.20h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.22h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.69h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.99h | limit 3.0h
- Stage71 challengers: **OK** | age 6.34h | limit 8.0h
- Stage71C team totals: **OK** | age 2.28h | limit 8.0h
- Stage71E double chance: **OK** | age 2.28h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.28h | limit 8.0h
- Stage71G DNB: **OK** | age 2.28h | limit 8.0h
- Stage71H readiness: **OK** | age 2.35h | limit 3.0h
- Stage71I settlement: **OK** | age 0.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.15h | limit 1.0h
- Stage73 internal API: **OK** | age 0.05h | limit 1.0h
- Stage68 exposure map: **STALE** | age 16.13h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 16.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 9.00h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 32.40h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.20h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 16.13h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.