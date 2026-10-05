# PBK System Health

Обновлено UTC: 2026-10-05T01:09:58Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.48h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.24h | limit 3.0h
- Stage55 context: **OK** | age 0.70h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.21h | limit 1.5h
- Stage57 international: **OK** | age 10.75h | limit 30.0h
- Stage58 daily brief: **STALE** | age 14.20h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.02h | limit 3.0h
- Stage60 forward performance: **STALE** | age 30.42h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.22h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.56h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.71h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.20h | limit 3.0h
- Stage66 attention board: **OK** | age 0.05h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.93h | limit 3.0h
- Stage71 challengers: **OK** | age 4.36h | limit 8.0h
- Stage71C team totals: **OK** | age 0.30h | limit 8.0h
- Stage71E double chance: **OK** | age 0.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.30h | limit 8.0h
- Stage71G DNB: **OK** | age 0.30h | limit 8.0h
- Stage71H readiness: **OK** | age 0.37h | limit 3.0h
- Stage71I settlement: **OK** | age 0.17h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.41h | limit 1.0h
- Stage68 exposure map: **STALE** | age 14.15h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 14.19h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.02h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 30.42h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.22h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 14.15h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.