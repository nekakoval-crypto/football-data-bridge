# PBK System Health

Обновлено UTC: 2026-10-08T20:10:56Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.52h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.36h | limit 1.5h
- Stage57 international: **STALE** | age 101.77h | limit 30.0h
- Stage58 daily brief: **STALE** | age 9.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 14.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 85.09h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.60h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.25h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.81h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **OK** | age 1.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.97h | limit 3.0h
- Stage71 challengers: **STALE** | age 12.43h | limit 8.0h
- Stage71C team totals: **OK** | age 1.36h | limit 8.0h
- Stage71E double chance: **OK** | age 1.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.36h | limit 8.0h
- Stage71G DNB: **OK** | age 1.36h | limit 8.0h
- Stage71H readiness: **OK** | age 1.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.21h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.12h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.02h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 101.77h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 9.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 14.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 85.09h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.60h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.81h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 12.43h > 8.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.94h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.