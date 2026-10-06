# PBK System Health

Обновлено UTC: 2026-10-06T00:10:42Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.45h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.43h | limit 3.0h
- Stage55 context: **OK** | age 0.91h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.24h | limit 1.5h
- Stage57 international: **STALE** | age 33.76h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.11h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 17.08h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.61h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.33h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 17.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **STALE** | age 6.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.02h | limit 3.0h
- Stage71 challengers: **OK** | age 0.56h | limit 8.0h
- Stage71C team totals: **OK** | age 5.34h | limit 8.0h
- Stage71E double chance: **OK** | age 5.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.34h | limit 8.0h
- Stage71G DNB: **OK** | age 5.34h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.33h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.06h | limit 1.0h
- Stage68 exposure map: **STALE** | age 17.89h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 33.76h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 17.08h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.61h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 17.72h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 6.09h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.44h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 17.89h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.