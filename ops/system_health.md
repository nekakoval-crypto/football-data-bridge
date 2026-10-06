# PBK System Health

Обновлено UTC: 2026-10-06T13:10:49Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 6.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.29h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.28h | limit 1.5h
- Stage57 international: **STALE** | age 46.77h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.08h | limit 3.0h
- Stage59 user execution: **STALE** | age 19.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 30.09h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.60h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.63h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 1.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **OK** | age 5.46h | limit 8.0h
- Stage71C team totals: **OK** | age 0.33h | limit 8.0h
- Stage71E double chance: **OK** | age 0.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.33h | limit 8.0h
- Stage71G DNB: **OK** | age 0.33h | limit 8.0h
- Stage71H readiness: **OK** | age 0.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.51h | limit 1.0h
- Stage68 exposure map: **STALE** | age 30.89h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.05h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 46.77h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 19.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 30.08h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.60h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 30.89h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.