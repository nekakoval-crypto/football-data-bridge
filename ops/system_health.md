# PBK System Health

Обновлено UTC: 2026-10-07T09:10:00Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 2.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **STALE** | age 66.75h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 50.07h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.60h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.64h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.69h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.27h | limit 3.0h
- Stage66 attention board: **STALE** | age 6.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.96h | limit 3.0h
- Stage71 challengers: **OK** | age 1.46h | limit 8.0h
- Stage71C team totals: **OK** | age 2.33h | limit 8.0h
- Stage71E double chance: **OK** | age 2.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.33h | limit 8.0h
- Stage71G DNB: **OK** | age 2.33h | limit 8.0h
- Stage71H readiness: **OK** | age 2.42h | limit 3.0h
- Stage71I settlement: **OK** | age 0.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.09h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.99h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 66.75h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 50.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.60h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.69h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 6.10h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.99h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.