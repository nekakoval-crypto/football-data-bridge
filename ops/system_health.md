# PBK System Health

Обновлено UTC: 2026-10-10T13:09:16Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 6.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.26h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.27h | limit 1.5h
- Stage57 international: **OK** | age 6.29h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.07h | limit 3.0h
- Stage59 user execution: **OK** | age 2.22h | limit 3.0h
- Stage60 forward performance: **STALE** | age 126.06h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.62h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.25h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 3.00h | limit 3.0h
- Stage71 challengers: **OK** | age 5.44h | limit 8.0h
- Stage71C team totals: **OK** | age 0.32h | limit 8.0h
- Stage71E double chance: **OK** | age 0.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.32h | limit 8.0h
- Stage71G DNB: **OK** | age 0.32h | limit 8.0h
- Stage71H readiness: **OK** | age 0.43h | limit 3.0h
- Stage71I settlement: **OK** | age 0.20h | limit 3.0h
- Stage72 data layer: **OK** | age 0.26h | limit 1.0h
- Stage73 internal API: **OK** | age 0.55h | limit 1.0h
- Stage68 exposure map: **STALE** | age 6.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.07h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 126.06h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.62h > 2.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.11h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 6.93h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.