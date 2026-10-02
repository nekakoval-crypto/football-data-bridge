# PBK System Health

Обновлено UTC: 2026-10-02T21:07:23Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **OK** | age 14.27h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 25.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 35.14h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.13h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.25h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.75h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.92h | limit 3.0h
- Stage71 challengers: **OK** | age 5.33h | limit 8.0h
- Stage71C team totals: **STALE** | age 8.31h | limit 8.0h
- Stage71E double chance: **STALE** | age 8.30h | limit 8.0h
- Stage71F European handicap: **STALE** | age 8.30h | limit 8.0h
- Stage71G DNB: **STALE** | age 8.30h | limit 8.0h
- Stage71H readiness: **OK** | age 2.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.09h | limit 1.0h
- Stage68 exposure map: **STALE** | age 13.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 25.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 35.14h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.13h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.25h > 2.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 8.31h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 8.31h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 8.31h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 8.31h > 8.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 13.92h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.