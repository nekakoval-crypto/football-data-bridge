# PBK System Health

Обновлено UTC: 2026-10-09T23:08:15Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.35h | limit 1.5h
- Stage57 international: **STALE** | age 128.72h | limit 30.0h
- Stage58 daily brief: **STALE** | age 8.00h | limit 3.0h
- Stage59 user execution: **STALE** | age 16.06h | limit 3.0h
- Stage60 forward performance: **STALE** | age 112.04h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 6.54h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 6.66h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 30.77h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.21h | limit 3.0h
- Stage66 attention board: **OK** | age 2.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 7.38h | limit 8.0h
- Stage71C team totals: **OK** | age 4.33h | limit 8.0h
- Stage71E double chance: **OK** | age 4.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.33h | limit 8.0h
- Stage71G DNB: **OK** | age 4.33h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.43h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.10h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 128.72h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 8.00h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 16.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 112.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 6.54h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 6.66h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 30.77h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.43h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.95h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.