# PBK System Health

Обновлено UTC: 2026-10-03T04:11:15Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 21.57h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.23h | limit 3.0h
- Stage55 context: **OK** | age 0.79h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.24h | limit 1.5h
- Stage57 international: **OK** | age 21.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.03h | limit 3.0h
- Stage59 user execution: **STALE** | age 32.27h | limit 3.0h
- Stage60 forward performance: **STALE** | age 42.20h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.08h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.17h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.30h | limit 3.0h
- Stage66 attention board: **OK** | age 0.97h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.02h | limit 3.0h
- Stage71 challengers: **OK** | age 4.62h | limit 8.0h
- Stage71C team totals: **OK** | age 3.40h | limit 8.0h
- Stage71E double chance: **OK** | age 3.39h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.39h | limit 8.0h
- Stage71G DNB: **OK** | age 3.39h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.48h | limit 3.0h
- Stage71I settlement: **STALE** | age 3.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.27h | limit 1.0h
- Stage73 internal API: **OK** | age 0.20h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.94h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 32.27h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 42.20h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.80h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.48h > 3.00h
- **WARN** `STALE_STAGE` — Stage71I settlement: age 3.28h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.95h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.