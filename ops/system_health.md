# PBK System Health

Обновлено UTC: 2026-10-06T15:11:30Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 8.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.29h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.34h | limit 1.5h
- Stage57 international: **STALE** | age 48.78h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.09h | limit 3.0h
- Stage59 user execution: **STALE** | age 21.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 32.10h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.61h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.25h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.81h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.24h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.13h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.97h | limit 3.0h
- Stage71 challengers: **OK** | age 7.47h | limit 8.0h
- Stage71C team totals: **OK** | age 2.34h | limit 8.0h
- Stage71E double chance: **OK** | age 2.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.34h | limit 8.0h
- Stage71G DNB: **OK** | age 2.34h | limit 8.0h
- Stage71H readiness: **OK** | age 2.45h | limit 3.0h
- Stage71I settlement: **OK** | age 0.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.23h | limit 1.0h
- Stage68 exposure map: **STALE** | age 32.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 48.78h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 21.21h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 32.10h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.61h > 2.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 32.91h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.