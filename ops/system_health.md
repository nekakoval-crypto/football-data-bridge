# PBK System Health

Обновлено UTC: 2026-10-06T23:07:04Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.48h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.10h | limit 1.5h
- Stage57 international: **STALE** | age 56.70h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 4.11h | limit 3.0h
- Stage60 forward performance: **STALE** | age 40.02h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 10.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **STALE** | age 11.05h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.92h | limit 3.0h
- Stage71 challengers: **OK** | age 7.43h | limit 8.0h
- Stage71C team totals: **OK** | age 4.31h | limit 8.0h
- Stage71E double chance: **OK** | age 4.31h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.31h | limit 8.0h
- Stage71G DNB: **OK** | age 4.31h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.41h | limit 3.0h
- Stage71I settlement: **OK** | age 0.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.15h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 56.70h > 30.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 4.11h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 40.02h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 10.74h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 11.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.92h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.41h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.