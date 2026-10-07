# PBK System Health

Обновлено UTC: 2026-10-07T18:10:41Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.74h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.35h | limit 1.5h
- Stage57 international: **STALE** | age 75.76h | limit 30.0h
- Stage58 daily brief: **STALE** | age 9.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 15.21h | limit 3.0h
- Stage60 forward performance: **STALE** | age 59.08h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.55h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.10h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 17.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.24h | limit 3.0h
- Stage66 attention board: **OK** | age 0.93h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 7.97h | limit 3.0h
- Stage71 challengers: **STALE** | age 10.47h | limit 8.0h
- Stage71C team totals: **OK** | age 5.30h | limit 8.0h
- Stage71E double chance: **OK** | age 5.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.30h | limit 8.0h
- Stage71G DNB: **OK** | age 5.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.39h | limit 3.0h
- Stage71I settlement: **STALE** | age 3.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **STALE** | age 20.00h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 75.76h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 9.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 15.21h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 59.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 17.70h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 7.97h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 10.47h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.39h > 3.00h
- **WARN** `STALE_STAGE` — Stage71I settlement: age 3.27h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 20.00h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.