# PBK System Health

Обновлено UTC: 2026-09-26T14:06:13Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 190 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 7.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.38h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.15h | limit 1.5h
- Stage57 international: **OK** | age 7.35h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **OK** | age 2.25h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.24h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.65h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.31h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.93h | limit 3.0h
- Stage71 challengers: **STALE** | age 30.53h | limit 8.0h
- Stage71C team totals: **OK** | age 1.36h | limit 8.0h
- Stage71E double chance: **OK** | age 1.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.36h | limit 8.0h
- Stage71G DNB: **OK** | age 1.36h | limit 8.0h
- Stage71H readiness: **OK** | age 1.49h | limit 3.0h
- Stage71I settlement: **OK** | age 1.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.14h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.92h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 30.53h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.