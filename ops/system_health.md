# PBK System Health

Обновлено UTC: 2026-10-01T20:08:51Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.15h | limit 1.5h
- Stage57 international: **STALE** | age 37.32h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.06h | limit 3.0h
- Stage59 user execution: **OK** | age 0.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 10.16h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.16h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.26h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 7.75h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.17h | limit 3.0h
- Stage66 attention board: **OK** | age 1.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **STALE** | age 20.60h | limit 8.0h
- Stage71C team totals: **OK** | age 7.32h | limit 8.0h
- Stage71E double chance: **OK** | age 7.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 7.32h | limit 8.0h
- Stage71G DNB: **OK** | age 7.32h | limit 8.0h
- Stage71H readiness: **OK** | age 1.45h | limit 3.0h
- Stage71I settlement: **OK** | age 1.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.20h | limit 1.0h
- Stage68 exposure map: **STALE** | age 6.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 37.32h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 10.16h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.15h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.26h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 7.75h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 20.60h > 8.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 6.91h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.