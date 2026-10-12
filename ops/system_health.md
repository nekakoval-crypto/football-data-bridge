# PBK System Health

Обновлено UTC: 2026-10-12T23:26:21Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 7.95h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 3.46h | limit 3.0h
- Stage55 context: **STALE** | age 3.22h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.80h | limit 1.5h
- Stage57 international: **STALE** | age 40.56h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.08h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.41h | limit 3.0h
- Stage60 forward performance: **STALE** | age 31.45h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 24.46h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.49h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.58h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.82h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.14h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 6.78h | limit 3.0h
- Stage71 challengers: **OK** | age 6.53h | limit 8.0h
- Stage71C team totals: **OK** | age 7.53h | limit 8.0h
- Stage71E double chance: **OK** | age 7.53h | limit 8.0h
- Stage71F European handicap: **OK** | age 7.53h | limit 8.0h
- Stage71G DNB: **OK** | age 7.53h | limit 8.0h
- Stage71H readiness: **STALE** | age 7.67h | limit 3.0h
- Stage71I settlement: **OK** | age 0.21h | limit 3.0h
- Stage72 data layer: **STALE** | age 4.07h | limit 1.0h
- Stage73 internal API: **STALE** | age 3.14h | limit 1.0h
- Stage68 exposure map: **STALE** | age 6.74h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage54 odds/closing: age 3.46h > 3.00h
- **WARN** `STALE_STAGE` — Stage55 context: age 3.22h > 3.00h
- **WARN** `STALE_STAGE` — Stage57 international: age 40.56h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.08h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.41h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 31.45h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 24.46h > 2.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.14h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 6.78h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71H readiness: age 7.67h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 4.07h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 3.14h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 6.74h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.