# PBK System Health

Обновлено UTC: 2026-10-04T10:59:15Z
Статус: 🔴 **CRITICAL** | critical 11 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 28.24h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 5.48h | limit 3.0h
- Stage55 context: **STALE** | age 5.78h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.12h | limit 1.5h
- Stage57 international: **STALE** | age 52.14h | limit 30.0h
- Stage58 daily brief: **STALE** | age 16.15h | limit 3.0h
- Stage59 user execution: **STALE** | age 14.91h | limit 3.0h
- Stage60 forward performance: **STALE** | age 16.24h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.83h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.05h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.06h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 5.51h | limit 3.0h
- Stage66 attention board: **STALE** | age 6.44h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 22.24h | limit 3.0h
- Stage71 challengers: **OK** | age 7.86h | limit 8.0h
- Stage71C team totals: **OK** | age 7.05h | limit 8.0h
- Stage71E double chance: **OK** | age 7.05h | limit 8.0h
- Stage71F European handicap: **OK** | age 7.05h | limit 8.0h
- Stage71G DNB: **OK** | age 7.05h | limit 8.0h
- Stage71H readiness: **STALE** | age 7.08h | limit 3.0h
- Stage71I settlement: **OK** | age 0.05h | limit 3.0h
- Stage72 data layer: **STALE** | age 5.03h | limit 1.0h
- Stage73 internal API: **STALE** | age 4.95h | limit 1.0h
- Stage68 exposure map: **STALE** | age 16.65h | limit 3.0h
- Stage69 promotion gate: **STALE** | age 6.42h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage54 odds/closing: age 5.48h > 3.00h
- **WARN** `STALE_STAGE` — Stage55 context: age 5.78h > 3.00h
- **WARN** `STALE_STAGE` — Stage57 international: age 52.14h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 16.15h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 14.91h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 16.24h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.83h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.06h > 3.00h
- **WARN** `STALE_STAGE` — Stage65 WATCH performance: age 5.51h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 6.44h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 22.24h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71H readiness: age 7.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 5.03h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 4.95h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 16.65h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage69 promotion gate: age 6.42h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.