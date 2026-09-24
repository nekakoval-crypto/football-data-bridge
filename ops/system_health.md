# PBK System Health

Обновлено UTC: 2026-09-24T20:07:03Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 189 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.39h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 13.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 11.20h | limit 3.0h
- Stage60 forward performance: **OK** | age 1.19h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.21h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.31h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.83h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.11h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.96h | limit 3.0h
- Stage71 challengers: **OK** | age 4.53h | limit 8.0h
- Stage71C team totals: **OK** | age 1.40h | limit 8.0h
- Stage71E double chance: **OK** | age 1.40h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.40h | limit 8.0h
- Stage71G DNB: **OK** | age 1.40h | limit 8.0h
- Stage71H readiness: **OK** | age 1.51h | limit 3.0h
- Stage71I settlement: **OK** | age 1.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.15h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 11.20h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.83h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.96h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.