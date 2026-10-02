# PBK System Health

Обновлено UTC: 2026-10-02T20:07:04Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.28h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **OK** | age 13.27h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.02h | limit 3.0h
- Stage59 user execution: **STALE** | age 24.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 34.13h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.13h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.24h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.75h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.91h | limit 3.0h
- Stage71 challengers: **OK** | age 4.33h | limit 8.0h
- Stage71C team totals: **OK** | age 7.30h | limit 8.0h
- Stage71E double chance: **OK** | age 7.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 7.30h | limit 8.0h
- Stage71G DNB: **OK** | age 7.30h | limit 8.0h
- Stage71H readiness: **OK** | age 1.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.09h | limit 1.0h
- Stage68 exposure map: **STALE** | age 12.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 24.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 34.13h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.13h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.24h > 2.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 12.92h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.