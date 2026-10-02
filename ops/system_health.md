# PBK System Health

Обновлено UTC: 2026-10-02T06:09:13Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 23.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.12h | limit 1.5h
- Stage57 international: **STALE** | age 47.33h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 10.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 20.17h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.26h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 1.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.99h | limit 3.0h
- Stage71 challengers: **OK** | age 6.59h | limit 8.0h
- Stage71C team totals: **OK** | age 5.36h | limit 8.0h
- Stage71E double chance: **OK** | age 5.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.36h | limit 8.0h
- Stage71G DNB: **OK** | age 5.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.43h | limit 3.0h
- Stage71I settlement: **OK** | age 1.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.11h | limit 1.0h
- Stage73 internal API: **OK** | age 0.02h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 47.33h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 10.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 20.17h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.74h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.43h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.