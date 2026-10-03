# PBK System Health

Обновлено UTC: 2026-10-03T09:09:07Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 2.40h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **OK** | age 26.30h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.00h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.12h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.04h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.62h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.25h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.76h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.21h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.00h | limit 3.0h
- Stage71 challengers: **STALE** | age 9.58h | limit 8.0h
- Stage71C team totals: **OK** | age 2.18h | limit 8.0h
- Stage71E double chance: **OK** | age 2.18h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.18h | limit 8.0h
- Stage71G DNB: **OK** | age 2.18h | limit 8.0h
- Stage71H readiness: **OK** | age 2.31h | limit 3.0h
- Stage71I settlement: **OK** | age 0.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.27h | limit 1.0h
- Stage68 exposure map: **STALE** | age 8.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.00h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.12h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.76h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.00h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 9.58h > 8.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 8.92h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.