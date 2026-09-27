# PBK System Health

Обновлено UTC: 2026-09-27T16:06:22Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 9.34h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.22h | limit 3.0h
- Stage60 forward performance: **STALE** | age 3.17h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.63h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.74h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.85h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.19h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.97h | limit 3.0h
- Stage71 challengers: **OK** | age 0.56h | limit 8.0h
- Stage71C team totals: **OK** | age 3.36h | limit 8.0h
- Stage71E double chance: **OK** | age 3.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.36h | limit 8.0h
- Stage71G DNB: **OK** | age 3.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.47h | limit 3.0h
- Stage71I settlement: **OK** | age 1.32h | limit 3.0h
- Stage72 data layer: **OK** | age 0.16h | limit 1.0h
- Stage73 internal API: **OK** | age 0.12h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.04h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.22h > 3.00h
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 3.17h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.47h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.