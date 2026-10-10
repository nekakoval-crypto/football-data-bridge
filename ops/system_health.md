# PBK System Health

Обновлено UTC: 2026-10-10T15:07:11Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 8.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.10h | limit 1.5h
- Stage57 international: **OK** | age 8.25h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 4.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 128.02h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.59h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.70h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.77h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.94h | limit 3.0h
- Stage71 challengers: **OK** | age 7.41h | limit 8.0h
- Stage71C team totals: **OK** | age 2.29h | limit 8.0h
- Stage71E double chance: **OK** | age 2.29h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.29h | limit 8.0h
- Stage71G DNB: **OK** | age 2.29h | limit 8.0h
- Stage71H readiness: **OK** | age 2.40h | limit 3.0h
- Stage71I settlement: **OK** | age 0.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.10h | limit 1.0h
- Stage68 exposure map: **STALE** | age 8.90h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage59 user execution: age 4.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 128.02h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 8.90h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.