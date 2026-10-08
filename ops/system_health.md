# PBK System Health

Обновлено UTC: 2026-10-08T03:08:56Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 20.52h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.15h | limit 1.5h
- Stage57 international: **STALE** | age 84.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 18.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 24.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 68.05h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.62h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.22h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.16h | limit 3.0h
- Stage66 attention board: **OK** | age 2.01h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **OK** | age 3.49h | limit 8.0h
- Stage71C team totals: **OK** | age 2.26h | limit 8.0h
- Stage71E double chance: **OK** | age 2.26h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.26h | limit 8.0h
- Stage71G DNB: **OK** | age 2.26h | limit 8.0h
- Stage71H readiness: **OK** | age 2.33h | limit 3.0h
- Stage71I settlement: **OK** | age 0.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.90h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 84.73h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 18.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 24.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 68.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.62h > 2.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.