# PBK System Health

Обновлено UTC: 2026-10-07T12:11:45Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 5.57h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.38h | limit 3.0h
- Stage55 context: **OK** | age 0.89h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.39h | limit 1.5h
- Stage57 international: **STALE** | age 69.78h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.08h | limit 3.0h
- Stage59 user execution: **STALE** | age 9.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 53.10h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.16h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.73h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 11.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 2.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.99h | limit 3.0h
- Stage71 challengers: **OK** | age 4.49h | limit 8.0h
- Stage71C team totals: **OK** | age 5.36h | limit 8.0h
- Stage71E double chance: **OK** | age 5.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.36h | limit 8.0h
- Stage71G DNB: **OK** | age 5.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.45h | limit 3.0h
- Stage71I settlement: **OK** | age 1.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.15h | limit 1.0h
- Stage73 internal API: **OK** | age 0.19h | limit 1.0h
- Stage68 exposure map: **STALE** | age 14.02h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 69.78h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 9.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 53.10h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.16h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 11.72h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.45h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 14.02h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.