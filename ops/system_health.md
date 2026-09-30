# PBK System Health

Обновлено UTC: 2026-09-30T20:08:04Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.52h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.15h | limit 1.5h
- Stage57 international: **OK** | age 13.31h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.05h | limit 3.0h
- Stage59 user execution: **STALE** | age 27.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 22.22h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.16h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.69h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 7.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.20h | limit 3.0h
- Stage66 attention board: **OK** | age 0.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **STALE** | age 20.60h | limit 8.0h
- Stage71C team totals: **OK** | age 7.29h | limit 8.0h
- Stage71E double chance: **OK** | age 7.29h | limit 8.0h
- Stage71F European handicap: **OK** | age 7.29h | limit 8.0h
- Stage71G DNB: **OK** | age 7.29h | limit 8.0h
- Stage71H readiness: **OK** | age 1.47h | limit 3.0h
- Stage71I settlement: **OK** | age 1.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.07h | limit 1.0h
- Stage73 internal API: **OK** | age 0.12h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.89h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 27.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 22.22h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.16h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.69h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 7.70h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 20.60h > 8.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.90h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.