# PBK System Health

Обновлено UTC: 2026-09-30T00:09:13Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.41h | limit 3.0h
- Stage55 context: **OK** | age 0.89h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.22h | limit 1.5h
- Stage57 international: **OK** | age 17.33h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.09h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.19h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.23h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 9.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 8.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 9.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.23h | limit 3.0h
- Stage66 attention board: **OK** | age 1.13h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.01h | limit 3.0h
- Stage71 challengers: **OK** | age 0.62h | limit 8.0h
- Stage71C team totals: **STALE** | age 11.16h | limit 8.0h
- Stage71E double chance: **STALE** | age 11.16h | limit 8.0h
- Stage71F European handicap: **STALE** | age 11.16h | limit 8.0h
- Stage71G DNB: **STALE** | age 11.16h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.49h | limit 3.0h
- Stage71I settlement: **OK** | age 1.34h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.13h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.19h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 9.15h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 8.67h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 9.84h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 11.16h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 11.16h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 11.16h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 11.16h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.49h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.98h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.