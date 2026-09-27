# PBK System Health

Обновлено UTC: 2026-09-27T18:07:23Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.57h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.40h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.16h | limit 1.5h
- Stage57 international: **OK** | age 11.35h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.06h | limit 3.0h
- Stage59 user execution: **OK** | age 0.25h | limit 3.0h
- Stage60 forward performance: **STALE** | age 5.18h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.65h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.76h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.87h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.99h | limit 3.0h
- Stage71 challengers: **OK** | age 2.58h | limit 8.0h
- Stage71C team totals: **OK** | age 5.38h | limit 8.0h
- Stage71E double chance: **OK** | age 5.38h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.38h | limit 8.0h
- Stage71G DNB: **OK** | age 5.38h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.49h | limit 3.0h
- Stage71I settlement: **OK** | age 1.32h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.14h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.06h > 3.00h
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 5.18h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.65h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.76h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.87h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.49h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.