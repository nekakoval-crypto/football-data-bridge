# PBK System Health

Обновлено UTC: 2026-10-02T05:07:07Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 22.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 46.29h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 9.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 19.13h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.68h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 5.56h | limit 8.0h
- Stage71C team totals: **OK** | age 4.32h | limit 8.0h
- Stage71E double chance: **OK** | age 4.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.32h | limit 8.0h
- Stage71G DNB: **OK** | age 4.32h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.39h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.07h | limit 1.0h
- Stage73 internal API: **OK** | age 0.12h | limit 1.0h
- Stage68 exposure map: **STALE** | age 7.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 46.29h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 9.20h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 19.13h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.70h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.39h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 7.95h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.