# PBK System Health

Обновлено UTC: 2026-10-03T08:07:03Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 1.37h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **OK** | age 25.27h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.96h | limit 3.0h
- Stage59 user execution: **OK** | age 2.09h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.00h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.22h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 7.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.90h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.97h | limit 3.0h
- Stage71 challengers: **STALE** | age 8.55h | limit 8.0h
- Stage71C team totals: **OK** | age 1.15h | limit 8.0h
- Stage71E double chance: **OK** | age 1.15h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.15h | limit 8.0h
- Stage71G DNB: **OK** | age 1.15h | limit 8.0h
- Stage71H readiness: **OK** | age 1.27h | limit 3.0h
- Stage71I settlement: **OK** | age 1.05h | limit 3.0h
- Stage72 data layer: **OK** | age 0.11h | limit 1.0h
- Stage73 internal API: **OK** | age 0.19h | limit 1.0h
- Stage68 exposure map: **STALE** | age 7.88h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.96h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 7.73h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.90h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 8.55h > 8.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 7.88h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.