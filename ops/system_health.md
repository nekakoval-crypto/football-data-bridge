# PBK System Health

Обновлено UTC: 2026-10-10T09:07:17Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 2.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **OK** | age 2.26h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.15h | limit 3.0h
- Stage60 forward performance: **STALE** | age 122.03h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.60h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **STALE** | age 6.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 1.41h | limit 8.0h
- Stage71C team totals: **OK** | age 2.29h | limit 8.0h
- Stage71E double chance: **OK** | age 2.29h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.29h | limit 8.0h
- Stage71G DNB: **OK** | age 2.29h | limit 8.0h
- Stage71H readiness: **OK** | age 2.39h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.10h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.90h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.02h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.15h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 122.03h > 3.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.60h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 6.06h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.