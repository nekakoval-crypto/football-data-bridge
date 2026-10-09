# PBK System Health

Обновлено UTC: 2026-10-09T20:07:21Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.45h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **STALE** | age 125.71h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.99h | limit 3.0h
- Stage59 user execution: **STALE** | age 13.04h | limit 3.0h
- Stage60 forward performance: **STALE** | age 109.03h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.53h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.65h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 27.75h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **OK** | age 1.04h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.92h | limit 3.0h
- Stage71 challengers: **OK** | age 4.36h | limit 8.0h
- Stage71C team totals: **OK** | age 1.31h | limit 8.0h
- Stage71E double chance: **OK** | age 1.31h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.31h | limit 8.0h
- Stage71G DNB: **OK** | age 1.31h | limit 8.0h
- Stage71H readiness: **OK** | age 1.42h | limit 3.0h
- Stage71I settlement: **OK** | age 1.17h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.06h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.01h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 125.71h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.99h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 13.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 109.03h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.53h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.65h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 27.75h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.