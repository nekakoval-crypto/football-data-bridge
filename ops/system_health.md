# PBK System Health

Обновлено UTC: 2026-09-28T00:09:33Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.60h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.45h | limit 3.0h
- Stage55 context: **OK** | age 0.90h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 17.39h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.09h | limit 3.0h
- Stage59 user execution: **OK** | age 0.29h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.28h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 9.69h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 9.79h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 9.91h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.14h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.02h | limit 3.0h
- Stage71 challengers: **OK** | age 0.63h | limit 8.0h
- Stage71C team totals: **STALE** | age 11.42h | limit 8.0h
- Stage71E double chance: **STALE** | age 11.42h | limit 8.0h
- Stage71F European handicap: **STALE** | age 11.42h | limit 8.0h
- Stage71G DNB: **STALE** | age 11.42h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.56h | limit 3.0h
- Stage71I settlement: **OK** | age 1.37h | limit 3.0h
- Stage72 data layer: **OK** | age 0.22h | limit 1.0h
- Stage73 internal API: **OK** | age 0.17h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.01h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 9.69h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 9.79h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 9.91h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 11.42h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 11.42h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 11.42h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 11.42h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.56h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.