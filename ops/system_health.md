# PBK System Health

Обновлено UTC: 2026-10-09T13:12:44Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 6.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.28h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.29h | limit 1.5h
- Stage57 international: **STALE** | age 118.80h | limit 30.0h
- Stage58 daily brief: **STALE** | age 11.10h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.13h | limit 3.0h
- Stage60 forward performance: **STALE** | age 102.12h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 7.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.71h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 20.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.10h | limit 3.0h
- Stage66 attention board: **OK** | age 2.14h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.99h | limit 3.0h
- Stage71 challengers: **OK** | age 5.43h | limit 8.0h
- Stage71C team totals: **OK** | age 0.35h | limit 8.0h
- Stage71E double chance: **OK** | age 0.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.35h | limit 8.0h
- Stage71G DNB: **OK** | age 0.35h | limit 8.0h
- Stage71H readiness: **OK** | age 0.46h | limit 3.0h
- Stage71I settlement: **OK** | age 0.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.61h | limit 1.0h
- Stage73 internal API: **OK** | age 0.52h | limit 1.0h
- Stage68 exposure map: **STALE** | age 20.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.07h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 118.80h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 11.10h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 102.12h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 7.19h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.71h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 20.84h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 20.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.