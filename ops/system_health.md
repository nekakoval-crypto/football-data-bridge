# PBK System Health

Обновлено UTC: 2026-10-01T11:08:27Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 4.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.35h | limit 1.5h
- Stage57 international: **OK** | age 28.32h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 42.18h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.16h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.16h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.68h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.25h | limit 3.0h
- Stage66 attention board: **OK** | age 2.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **STALE** | age 11.60h | limit 8.0h
- Stage71C team totals: **OK** | age 4.32h | limit 8.0h
- Stage71E double chance: **OK** | age 4.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.32h | limit 8.0h
- Stage71G DNB: **OK** | age 4.32h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.41h | limit 3.0h
- Stage71I settlement: **OK** | age 0.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.02h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.01h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 42.18h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 11.60h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.41h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.