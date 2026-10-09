# PBK System Health

Обновлено UTC: 2026-10-09T06:12:35Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 23.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.90h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.38h | limit 1.5h
- Stage57 international: **STALE** | age 111.80h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.09h | limit 3.0h
- Stage59 user execution: **OK** | age 2.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 95.11h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.28h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 13.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **STALE** | age 8.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.01h | limit 3.0h
- Stage71 challengers: **OK** | age 6.54h | limit 8.0h
- Stage71C team totals: **OK** | age 5.27h | limit 8.0h
- Stage71E double chance: **OK** | age 5.27h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.27h | limit 8.0h
- Stage71G DNB: **OK** | age 5.27h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.35h | limit 3.0h
- Stage71I settlement: **OK** | age 1.29h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.48h | limit 1.0h
- Stage68 exposure map: **STALE** | age 13.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 111.79h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 95.11h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 13.84h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 8.12h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.35h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 13.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.