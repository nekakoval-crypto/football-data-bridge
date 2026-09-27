# PBK System Health

Обновлено UTC: 2026-09-27T19:05:36Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 12.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.78h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.10h | limit 1.5h
- Stage57 international: **OK** | age 12.32h | limit 30.0h
- Stage58 daily brief: **STALE** | age 7.03h | limit 3.0h
- Stage59 user execution: **OK** | age 0.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 6.15h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.62h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.73h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **OK** | age 1.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.92h | limit 3.0h
- Stage71 challengers: **OK** | age 3.55h | limit 8.0h
- Stage71C team totals: **OK** | age 6.35h | limit 8.0h
- Stage71E double chance: **OK** | age 6.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 6.35h | limit 8.0h
- Stage71G DNB: **OK** | age 6.35h | limit 8.0h
- Stage71H readiness: **OK** | age 0.49h | limit 3.0h
- Stage71I settlement: **OK** | age 0.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.02h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 7.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 6.15h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.62h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.73h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.84h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.