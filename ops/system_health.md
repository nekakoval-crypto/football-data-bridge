# PBK System Health

Обновлено UTC: 2026-10-07T14:10:01Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 7.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 71.75h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 11.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 55.07h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.45h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.57h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 13.69h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.07h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.96h | limit 3.0h
- Stage71 challengers: **OK** | age 6.46h | limit 8.0h
- Stage71C team totals: **OK** | age 1.29h | limit 8.0h
- Stage71E double chance: **OK** | age 1.29h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.29h | limit 8.0h
- Stage71G DNB: **OK** | age 1.29h | limit 8.0h
- Stage71H readiness: **OK** | age 1.38h | limit 3.0h
- Stage71I settlement: **OK** | age 1.15h | limit 3.0h
- Stage72 data layer: **OK** | age 0.19h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **STALE** | age 15.99h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.96h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 71.75h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 11.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 55.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 13.69h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.96h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 15.99h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.