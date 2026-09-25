# PBK System Health

Обновлено UTC: 2026-09-25T18:06:45Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 190 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.16h | limit 1.5h
- Stage57 international: **OK** | age 11.32h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.20h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.27h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.19h | limit 3.0h
- Stage66 attention board: **OK** | age 0.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.98h | limit 3.0h
- Stage71 challengers: **STALE** | age 10.54h | limit 8.0h
- Stage71C team totals: **OK** | age 5.36h | limit 8.0h
- Stage71E double chance: **OK** | age 5.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.36h | limit 8.0h
- Stage71G DNB: **OK** | age 5.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.46h | limit 3.0h
- Stage71I settlement: **OK** | age 1.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.13h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.22h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 10.54h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.46h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.