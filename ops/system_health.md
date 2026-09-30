# PBK System Health

Обновлено UTC: 2026-09-30T09:07:37Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 2.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.29h | limit 3.0h
- Stage55 context: **OK** | age 0.78h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **OK** | age 2.30h | limit 30.0h
- Stage58 daily brief: **STALE** | age 7.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 16.16h | limit 3.0h
- Stage60 forward performance: **STALE** | age 11.21h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.60h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.64h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.93h | limit 3.0h
- Stage71 challengers: **STALE** | age 9.59h | limit 8.0h
- Stage71C team totals: **OK** | age 2.33h | limit 8.0h
- Stage71E double chance: **OK** | age 2.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.33h | limit 8.0h
- Stage71G DNB: **OK** | age 2.33h | limit 8.0h
- Stage71H readiness: **OK** | age 2.42h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.07h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 7.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 16.16h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 11.21h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.60h > 2.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 9.59h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.