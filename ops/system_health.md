# PBK System Health

Обновлено UTC: 2026-10-07T15:21:44Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 8.74h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.53h | limit 3.0h
- Stage55 context: **OK** | age 1.02h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.53h | limit 1.5h
- Stage57 international: **STALE** | age 72.95h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.25h | limit 3.0h
- Stage59 user execution: **STALE** | age 12.39h | limit 3.0h
- Stage60 forward performance: **STALE** | age 56.27h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.65h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.77h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 14.88h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.42h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.27h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 5.15h | limit 3.0h
- Stage71 challengers: **OK** | age 7.65h | limit 8.0h
- Stage71C team totals: **OK** | age 2.49h | limit 8.0h
- Stage71E double chance: **OK** | age 2.49h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.49h | limit 8.0h
- Stage71G DNB: **OK** | age 2.49h | limit 8.0h
- Stage71H readiness: **OK** | age 2.57h | limit 3.0h
- Stage71I settlement: **OK** | age 0.45h | limit 3.0h
- Stage72 data layer: **OK** | age 0.69h | limit 1.0h
- Stage73 internal API: **OK** | age 0.58h | limit 1.0h
- Stage68 exposure map: **STALE** | age 17.19h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.23h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 72.95h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.25h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 12.39h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 56.27h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.65h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.77h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 14.88h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.27h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 5.15h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 17.19h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.