# PBK System Health

Обновлено UTC: 2026-10-05T11:09:35Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 4.44h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **OK** | age 20.75h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.97h | limit 3.0h
- Stage59 user execution: **STALE** | age 17.02h | limit 3.0h
- Stage60 forward performance: **STALE** | age 4.06h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.13h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.22h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 1.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 14.35h | limit 8.0h
- Stage71C team totals: **OK** | age 4.25h | limit 8.0h
- Stage71E double chance: **OK** | age 4.25h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.25h | limit 8.0h
- Stage71G DNB: **OK** | age 4.25h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.33h | limit 3.0h
- Stage71I settlement: **OK** | age 0.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.29h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.87h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.01h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.97h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 17.01h > 3.00h
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 4.06h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.13h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.70h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 14.35h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.33h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.87h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.