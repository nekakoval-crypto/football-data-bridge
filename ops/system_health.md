# PBK System Health

Обновлено UTC: 2026-10-06T21:07:11Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.48h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.27h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.31h | limit 1.5h
- Stage57 international: **STALE** | age 54.70h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **OK** | age 2.12h | limit 3.0h
- Stage60 forward performance: **STALE** | age 38.02h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.51h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.21h | limit 3.0h
- Stage66 attention board: **STALE** | age 9.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.93h | limit 3.0h
- Stage71 challengers: **OK** | age 5.43h | limit 8.0h
- Stage71C team totals: **OK** | age 2.31h | limit 8.0h
- Stage71E double chance: **OK** | age 2.31h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.31h | limit 8.0h
- Stage71G DNB: **OK** | age 2.31h | limit 8.0h
- Stage71H readiness: **OK** | age 2.41h | limit 3.0h
- Stage71I settlement: **OK** | age 0.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.13h | limit 1.0h
- Stage73 internal API: **OK** | age 0.45h | limit 1.0h
- Stage68 exposure map: **STALE** | age 38.83h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 54.70h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 38.02h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.51h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.74h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 9.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 38.83h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.