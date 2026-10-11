# PBK System Health

Обновлено UTC: 2026-10-11T16:29:58Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.88h | limit 30.0h
- Stage54 odds/closing: **STALE** | age 3.08h | limit 3.0h
- Stage55 context: **OK** | age 2.58h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 5.03h | limit 1.5h
- Stage57 international: **OK** | age 9.62h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.85h | limit 3.0h
- Stage59 user execution: **STALE** | age 29.56h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.51h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.39h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 10.81h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.94h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 3.80h | limit 3.0h
- Stage66 attention board: **STALE** | age 9.91h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 5.91h | limit 3.0h
- Stage71 challengers: **OK** | age 2.20h | limit 8.0h
- Stage71C team totals: **OK** | age 3.20h | limit 8.0h
- Stage71E double chance: **OK** | age 3.20h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.20h | limit 8.0h
- Stage71G DNB: **OK** | age 3.20h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.38h | limit 3.0h
- Stage71I settlement: **OK** | age 0.06h | limit 3.0h
- Stage72 data layer: **STALE** | age 3.00h | limit 1.0h
- Stage73 internal API: **STALE** | age 2.51h | limit 1.0h
- Stage68 exposure map: **STALE** | age 5.79h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.42h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage54 odds/closing: age 3.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage56 weather/XI: age 5.03h > 1.50h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 29.56h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.39h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 10.81h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.94h > 3.00h
- **WARN** `STALE_STAGE` — Stage65 WATCH performance: age 3.80h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 9.91h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 5.91h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.38h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 3.00h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 2.51h > 1.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 5.79h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.