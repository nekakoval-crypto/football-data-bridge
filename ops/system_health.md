# PBK System Health

Обновлено UTC: 2026-10-10T02:08:34Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 19.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 131.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 11.01h | limit 3.0h
- Stage59 user execution: **STALE** | age 19.06h | limit 3.0h
- Stage60 forward performance: **STALE** | age 115.05h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.23h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.67h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.91h | limit 3.0h
- Stage71 challengers: **OK** | age 2.44h | limit 8.0h
- Stage71C team totals: **OK** | age 1.24h | limit 8.0h
- Stage71E double chance: **OK** | age 1.24h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.24h | limit 8.0h
- Stage71G DNB: **OK** | age 1.24h | limit 8.0h
- Stage71H readiness: **OK** | age 1.31h | limit 3.0h
- Stage71I settlement: **OK** | age 1.11h | limit 3.0h
- Stage72 data layer: **OK** | age 0.07h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.88h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.96h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 131.73h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 11.01h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 19.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 115.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.17h > 2.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.06h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.