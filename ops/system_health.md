# PBK System Health

Обновлено UTC: 2026-10-01T18:10:43Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 6

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.19h | limit 1.5h
- Stage57 international: **STALE** | age 35.35h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.09h | limit 3.0h
- Stage59 user execution: **OK** | age 2.22h | limit 3.0h
- Stage60 forward performance: **STALE** | age 8.19h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.29h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.19h | limit 3.0h
- Stage66 attention board: **OK** | age 0.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 3.00h | limit 3.0h
- Stage71 challengers: **STALE** | age 18.63h | limit 8.0h
- Stage71C team totals: **OK** | age 5.35h | limit 8.0h
- Stage71E double chance: **OK** | age 5.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.35h | limit 8.0h
- Stage71G DNB: **OK** | age 5.35h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.31h | limit 3.0h
- Stage72 data layer: **OK** | age 0.15h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 35.35h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 8.19h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.19h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.78h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 18.63h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.44h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.95h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.