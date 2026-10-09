# PBK System Health

Обновлено UTC: 2026-10-09T21:09:00Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.48h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **STALE** | age 126.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.02h | limit 3.0h
- Stage59 user execution: **STALE** | age 14.07h | limit 3.0h
- Stage60 forward performance: **STALE** | age 110.05h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.55h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 28.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.14h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.95h | limit 3.0h
- Stage71 challengers: **OK** | age 5.39h | limit 8.0h
- Stage71C team totals: **OK** | age 2.34h | limit 8.0h
- Stage71E double chance: **OK** | age 2.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.34h | limit 8.0h
- Stage71G DNB: **OK** | age 2.34h | limit 8.0h
- Stage71H readiness: **OK** | age 2.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 126.73h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.02h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 14.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 110.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.55h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.67h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 28.78h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.96h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.