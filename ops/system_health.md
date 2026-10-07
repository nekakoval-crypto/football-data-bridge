# PBK System Health

Обновлено UTC: 2026-10-07T17:18:12Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 10.68h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.43h | limit 3.0h
- Stage55 context: **OK** | age 0.95h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.45h | limit 1.5h
- Stage57 international: **STALE** | age 74.89h | limit 30.0h
- Stage58 daily brief: **STALE** | age 8.19h | limit 3.0h
- Stage59 user execution: **STALE** | age 14.33h | limit 3.0h
- Stage60 forward performance: **STALE** | age 58.21h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.67h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.22h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 16.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **OK** | age 0.06h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 7.10h | limit 3.0h
- Stage71 challengers: **STALE** | age 9.59h | limit 8.0h
- Stage71C team totals: **OK** | age 4.43h | limit 8.0h
- Stage71E double chance: **OK** | age 4.43h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.43h | limit 8.0h
- Stage71G DNB: **OK** | age 4.43h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.51h | limit 3.0h
- Stage71I settlement: **OK** | age 2.39h | limit 3.0h
- Stage72 data layer: **OK** | age 0.60h | limit 1.0h
- Stage73 internal API: **OK** | age 0.48h | limit 1.0h
- Stage68 exposure map: **STALE** | age 19.13h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.12h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 74.89h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 8.19h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 14.33h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 58.21h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 16.82h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 7.10h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 9.59h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.52h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 19.13h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.