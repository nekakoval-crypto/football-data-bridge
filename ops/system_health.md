# PBK System Health

Обновлено UTC: 2026-09-20T19:04:57Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 163 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 12.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.79h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.18h | limit 1.5h
- Stage57 international: **OK** | age 12.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.23h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.20h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.69h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.19h | limit 3.0h
- Stage66 attention board: **OK** | age 0.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.93h | limit 3.0h
- Stage71 challengers: **OK** | age 3.55h | limit 8.0h
- Stage71C team totals: **OK** | age 0.41h | limit 8.0h
- Stage71E double chance: **OK** | age 0.41h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.41h | limit 8.0h
- Stage71G DNB: **OK** | age 0.41h | limit 8.0h
- Stage71H readiness: **OK** | age 0.52h | limit 3.0h
- Stage71I settlement: **OK** | age 0.29h | limit 3.0h
- Stage72 data layer: **OK** | age 0.15h | limit 1.0h
- Stage73 internal API: **OK** | age 0.12h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.23h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.19h > 2.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.