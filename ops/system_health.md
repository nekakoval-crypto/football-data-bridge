# PBK System Health

Обновлено UTC: 2026-10-10T18:07:53Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.52h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.17h | limit 1.5h
- Stage57 international: **OK** | age 11.27h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.19h | limit 3.0h
- Stage60 forward performance: **STALE** | age 131.04h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.26h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.17h | limit 3.0h
- Stage66 attention board: **STALE** | age 8.08h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 4.95h | limit 3.0h
- Stage71 challengers: **OK** | age 2.38h | limit 8.0h
- Stage71C team totals: **OK** | age 5.30h | limit 8.0h
- Stage71E double chance: **OK** | age 5.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.30h | limit 8.0h
- Stage71G DNB: **OK** | age 5.30h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.41h | limit 3.0h
- Stage71I settlement: **OK** | age 1.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.13h | limit 1.0h
- Stage73 internal API: **OK** | age 0.03h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.19h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 131.04h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.78h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 8.08h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 4.95h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.41h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.