# PBK System Health

Обновлено UTC: 2026-10-09T01:13:35Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 18.56h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.23h | limit 3.0h
- Stage55 context: **OK** | age 0.72h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.08h | limit 1.5h
- Stage57 international: **STALE** | age 106.81h | limit 30.0h
- Stage58 daily brief: **STALE** | age 14.12h | limit 3.0h
- Stage59 user execution: **STALE** | age 4.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 90.13h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.44h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.56h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.86h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.08h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.14h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 1.55h | limit 8.0h
- Stage71C team totals: **OK** | age 0.28h | limit 8.0h
- Stage71E double chance: **OK** | age 0.28h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.28h | limit 8.0h
- Stage71G DNB: **OK** | age 0.28h | limit 8.0h
- Stage71H readiness: **OK** | age 0.36h | limit 3.0h
- Stage71I settlement: **OK** | age 0.18h | limit 3.0h
- Stage72 data layer: **OK** | age 0.82h | limit 1.0h
- Stage73 internal API: **OK** | age 0.61h | limit 1.0h
- Stage68 exposure map: **STALE** | age 8.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.08h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 106.81h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 14.12h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 4.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 90.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.86h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.14h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 8.98h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.