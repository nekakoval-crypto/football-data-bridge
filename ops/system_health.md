# PBK System Health

Обновлено UTC: 2026-10-04T21:08:43Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 7.46h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 3.06h | limit 3.0h
- Stage55 context: **OK** | age 2.86h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 3.24h | limit 1.5h
- Stage57 international: **OK** | age 6.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 10.17h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.00h | limit 3.0h
- Stage60 forward performance: **STALE** | age 26.40h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.38h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.14h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.86h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 3.20h | limit 3.0h
- Stage66 attention board: **OK** | age 0.03h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 32.39h | limit 3.0h
- Stage71 challengers: **OK** | age 0.34h | limit 8.0h
- Stage71C team totals: **OK** | age 6.93h | limit 8.0h
- Stage71E double chance: **OK** | age 6.93h | limit 8.0h
- Stage71F European handicap: **OK** | age 6.93h | limit 8.0h
- Stage71G DNB: **OK** | age 6.93h | limit 8.0h
- Stage71H readiness: **STALE** | age 7.28h | limit 3.0h
- Stage71I settlement: **OK** | age 2.80h | limit 3.0h
- Stage72 data layer: **OK** | age 0.48h | limit 1.0h
- Stage73 internal API: **OK** | age 0.39h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.13h | limit 3.0h
- Stage69 promotion gate: **OK** | age 2.96h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage54 odds/closing: age 3.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage56 weather/XI: age 3.24h > 1.50h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 10.17h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.00h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 26.40h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.38h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.14h > 2.00h
- **WARN** `STALE_STAGE` — Stage65 WATCH performance: age 3.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 32.39h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71H readiness: age 7.28h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.13h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.