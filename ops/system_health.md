# PBK System Health

Обновлено UTC: 2026-09-29T08:09:15Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 1.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.37h | limit 1.5h
- Stage57 international: **OK** | age 1.33h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.09h | limit 3.0h
- Stage59 user execution: **OK** | age 0.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 10.24h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.53h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.70h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.19h | limit 3.0h
- Stage66 attention board: **OK** | age 2.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **STALE** | age 8.61h | limit 8.0h
- Stage71C team totals: **OK** | age 1.35h | limit 8.0h
- Stage71E double chance: **OK** | age 1.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.35h | limit 8.0h
- Stage71G DNB: **OK** | age 1.35h | limit 8.0h
- Stage71H readiness: **OK** | age 1.46h | limit 3.0h
- Stage71I settlement: **OK** | age 1.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.16h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 10.24h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 8.61h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.