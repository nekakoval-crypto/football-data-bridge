# PBK System Health

Обновлено UTC: 2026-10-07T10:10:08Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 3.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 67.75h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 51.07h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.23h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 9.69h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.96h | limit 3.0h
- Stage71 challengers: **OK** | age 2.46h | limit 8.0h
- Stage71C team totals: **OK** | age 3.33h | limit 8.0h
- Stage71E double chance: **OK** | age 3.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.33h | limit 8.0h
- Stage71G DNB: **OK** | age 3.33h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.42h | limit 3.0h
- Stage71I settlement: **OK** | age 1.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.06h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **STALE** | age 11.99h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 67.75h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 51.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 9.69h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.96h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.42h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 11.99h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.