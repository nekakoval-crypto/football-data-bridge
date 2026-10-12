# PBK System Health

Обновлено UTC: 2026-10-12T06:51:48Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 24.24h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 5.17h | limit 3.0h
- Stage55 context: **STALE** | age 4.63h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.79h | limit 1.5h
- Stage57 international: **OK** | age 23.98h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.94h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.04h | limit 3.0h
- Stage60 forward performance: **STALE** | age 14.87h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.89h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 6.34h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.32h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.56h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.97h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 6.65h | limit 3.0h
- Stage71 challengers: **OK** | age 4.27h | limit 8.0h
- Stage71C team totals: **OK** | age 0.52h | limit 8.0h
- Stage71E double chance: **OK** | age 0.52h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.52h | limit 8.0h
- Stage71G DNB: **OK** | age 0.52h | limit 8.0h
- Stage71H readiness: **OK** | age 0.66h | limit 3.0h
- Stage71I settlement: **OK** | age 0.36h | limit 3.0h
- Stage72 data layer: **OK** | age 0.27h | limit 1.0h
- Stage73 internal API: **STALE** | age 4.05h | limit 1.0h
- Stage68 exposure map: **STALE** | age 20.16h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.07h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage54 odds/closing: age 5.18h > 3.00h
- **WARN** `STALE_STAGE` — Stage55 context: age 4.63h > 3.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.94h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 14.87h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.89h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 6.34h > 2.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.97h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 6.65h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 4.05h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 20.16h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.