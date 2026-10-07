# PBK System Health

Обновлено UTC: 2026-10-07T08:11:01Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 1.56h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.36h | limit 1.5h
- Stage57 international: **STALE** | age 65.77h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.09h | limit 3.0h
- Stage59 user execution: **STALE** | age 5.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 49.09h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 6.62h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.26h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 7.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.17h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.98h | limit 3.0h
- Stage71 challengers: **OK** | age 0.47h | limit 8.0h
- Stage71C team totals: **OK** | age 1.35h | limit 8.0h
- Stage71E double chance: **OK** | age 1.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.35h | limit 8.0h
- Stage71G DNB: **OK** | age 1.35h | limit 8.0h
- Stage71H readiness: **OK** | age 1.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.20h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.14h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.01h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 65.77h > 30.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 5.21h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 49.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 6.62h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 7.70h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.12h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.01h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.