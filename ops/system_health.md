# PBK System Health

Обновлено UTC: 2026-09-30T19:09:30Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 12.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **OK** | age 12.33h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 26.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 21.24h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.18h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.72h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.73h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 1.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **STALE** | age 19.62h | limit 8.0h
- Stage71C team totals: **OK** | age 6.31h | limit 8.0h
- Stage71E double chance: **OK** | age 6.31h | limit 8.0h
- Stage71F European handicap: **OK** | age 6.31h | limit 8.0h
- Stage71G DNB: **OK** | age 6.31h | limit 8.0h
- Stage71H readiness: **OK** | age 0.50h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.13h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 26.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 21.24h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.18h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.73h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 19.62h > 8.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.92h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.