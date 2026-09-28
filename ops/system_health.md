# PBK System Health

Обновлено UTC: 2026-09-28T15:09:32Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 8.52h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **OK** | age 8.32h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.07h | limit 3.0h
- Stage59 user execution: **OK** | age 2.18h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.18h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.23h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.27h | limit 3.0h
- Stage66 attention board: **OK** | age 1.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **STALE** | age 15.63h | limit 8.0h
- Stage71C team totals: **OK** | age 2.35h | limit 8.0h
- Stage71E double chance: **OK** | age 2.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.35h | limit 8.0h
- Stage71G DNB: **OK** | age 2.35h | limit 8.0h
- Stage71H readiness: **OK** | age 2.45h | limit 3.0h
- Stage71I settlement: **OK** | age 0.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.19h | limit 1.0h
- Stage73 internal API: **OK** | age 0.13h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 15.63h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.