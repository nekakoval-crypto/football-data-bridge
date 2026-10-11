# PBK System Health

Обновлено UTC: 2026-10-11T20:45:12Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.13h | limit 30.0h
- Stage54 odds/closing: **OK** | age 2.34h | limit 3.0h
- Stage55 context: **OK** | age 1.99h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.09h | limit 1.5h
- Stage57 international: **OK** | age 13.87h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.21h | limit 3.0h
- Stage59 user execution: **OK** | age 2.26h | limit 3.0h
- Stage60 forward performance: **STALE** | age 4.76h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 6.64h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 15.06h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.20h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 2.95h | limit 3.0h
- Stage66 attention board: **STALE** | age 14.17h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.20h | limit 3.0h
- Stage71 challengers: **OK** | age 1.03h | limit 8.0h
- Stage71C team totals: **OK** | age 7.46h | limit 8.0h
- Stage71E double chance: **OK** | age 7.46h | limit 8.0h
- Stage71F European handicap: **OK** | age 7.46h | limit 8.0h
- Stage71G DNB: **OK** | age 7.46h | limit 8.0h
- Stage71H readiness: **STALE** | age 7.63h | limit 3.0h
- Stage71I settlement: **OK** | age 0.18h | limit 3.0h
- Stage72 data layer: **OK** | age 0.25h | limit 1.0h
- Stage73 internal API: **OK** | age 0.15h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.05h | limit 3.0h
- Stage69 promotion gate: **STALE** | age 4.67h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 4.76h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 6.64h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 15.06h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 14.17h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71H readiness: age 7.63h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage69 promotion gate: age 4.67h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.