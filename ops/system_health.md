# PBK System Health

Обновлено UTC: 2026-10-04T17:52:50Z
Статус: 🔴 **CRITICAL** | critical 16 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 4.20h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 6.74h | limit 3.0h
- Stage55 context: **STALE** | age 6.35h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 7.02h | limit 1.5h
- Stage57 international: **OK** | age 3.47h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.91h | limit 3.0h
- Stage59 user execution: **STALE** | age 21.81h | limit 3.0h
- Stage60 forward performance: **STALE** | age 23.13h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.12h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 6.95h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.44h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 6.76h | limit 3.0h
- Stage66 attention board: **OK** | age 0.27h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 29.13h | limit 3.0h
- Stage71 challengers: **OK** | age 2.67h | limit 8.0h
- Stage71C team totals: **OK** | age 3.67h | limit 8.0h
- Stage71E double chance: **OK** | age 3.67h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.67h | limit 8.0h
- Stage71G DNB: **OK** | age 3.67h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.02h | limit 3.0h
- Stage71I settlement: **STALE** | age 6.94h | limit 3.0h
- Stage72 data layer: **STALE** | age 3.24h | limit 1.0h
- Stage73 internal API: **STALE** | age 3.15h | limit 1.0h
- Stage68 exposure map: **STALE** | age 6.86h | limit 3.0h
- Stage69 promotion gate: **STALE** | age 6.90h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage54 odds/closing: age 6.74h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage55 context: age 6.35h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage56 weather/XI: age 7.02h > 1.50h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.91h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 21.81h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 23.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.12h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 6.95h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.44h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage65 WATCH performance: age 6.76h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 29.13h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.02h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71I settlement: age 6.94h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 3.24h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 3.15h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 6.86h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage69 promotion gate: age 6.90h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.