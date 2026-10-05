# PBK System Health

Обновлено UTC: 2026-10-05T08:10:46Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 1.46h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.15h | limit 1.5h
- Stage57 international: **OK** | age 17.76h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.99h | limit 3.0h
- Stage59 user execution: **STALE** | age 14.03h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.08h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.16h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.24h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.28h | limit 3.0h
- Stage66 attention board: **OK** | age 2.09h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 6.02h | limit 3.0h
- Stage71 challengers: **STALE** | age 11.37h | limit 8.0h
- Stage71C team totals: **OK** | age 1.27h | limit 8.0h
- Stage71E double chance: **OK** | age 1.27h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.27h | limit 8.0h
- Stage71G DNB: **OK** | age 1.27h | limit 8.0h
- Stage71H readiness: **OK** | age 1.35h | limit 3.0h
- Stage71I settlement: **OK** | age 1.14h | limit 3.0h
- Stage72 data layer: **OK** | age 0.13h | limit 1.0h
- Stage73 internal API: **OK** | age 0.28h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.89h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 14.03h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.16h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 6.02h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 11.37h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.