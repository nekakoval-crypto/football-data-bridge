# PBK System Health

Обновлено UTC: 2026-10-05T16:09:00Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.43h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.29h | limit 3.0h
- Stage55 context: **OK** | age 0.78h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **OK** | age 25.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 8.96h | limit 3.0h
- Stage59 user execution: **STALE** | age 22.00h | limit 3.0h
- Stage60 forward performance: **STALE** | age 9.05h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.55h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.63h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 9.69h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.23h | limit 3.0h
- Stage66 attention board: **OK** | age 1.04h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 19.34h | limit 8.0h
- Stage71C team totals: **OK** | age 3.28h | limit 8.0h
- Stage71E double chance: **OK** | age 3.28h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.28h | limit 8.0h
- Stage71G DNB: **OK** | age 3.28h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.38h | limit 3.0h
- Stage71I settlement: **OK** | age 1.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.06h | limit 1.0h
- Stage73 internal API: **OK** | age 0.09h | limit 1.0h
- Stage68 exposure map: **STALE** | age 9.86h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 8.96h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 22.00h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 9.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.55h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 9.69h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.95h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 19.34h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.38h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 9.86h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.