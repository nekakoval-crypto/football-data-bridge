# PBK System Health

Обновлено UTC: 2026-09-29T20:07:44Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.12h | limit 1.5h
- Stage57 international: **OK** | age 13.30h | limit 30.0h
- Stage58 daily brief: **STALE** | age 17.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 22.21h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.12h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.65h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **OK** | age 1.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.92h | limit 3.0h
- Stage71 challengers: **STALE** | age 20.58h | limit 8.0h
- Stage71C team totals: **OK** | age 7.14h | limit 8.0h
- Stage71E double chance: **OK** | age 7.14h | limit 8.0h
- Stage71F European handicap: **OK** | age 7.14h | limit 8.0h
- Stage71G DNB: **OK** | age 7.14h | limit 8.0h
- Stage71H readiness: **OK** | age 1.46h | limit 3.0h
- Stage71I settlement: **OK** | age 1.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.17h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 17.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 22.21h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.12h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.65h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.82h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 20.58h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.