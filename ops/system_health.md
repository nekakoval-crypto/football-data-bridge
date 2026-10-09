# PBK System Health

Обновлено UTC: 2026-10-09T03:08:39Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 20.48h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.33h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.34h | limit 1.5h
- Stage57 international: **STALE** | age 108.73h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.03h | limit 3.0h
- Stage59 user execution: **OK** | age 1.16h | limit 3.0h
- Stage60 forward performance: **STALE** | age 92.05h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.36h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.70h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 10.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.87h | limit 3.0h
- Stage71 challengers: **OK** | age 3.47h | limit 8.0h
- Stage71C team totals: **OK** | age 2.20h | limit 8.0h
- Stage71E double chance: **OK** | age 2.20h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.20h | limit 8.0h
- Stage71G DNB: **OK** | age 2.20h | limit 8.0h
- Stage71H readiness: **OK** | age 2.28h | limit 3.0h
- Stage71I settlement: **OK** | age 0.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.16h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.90h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 108.73h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 92.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.36h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 10.78h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.90h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.