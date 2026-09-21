# PBK System Health

Обновлено UTC: 2026-09-21T16:06:44Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 168 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 9.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 9.31h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 8.21h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.21h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.20h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.28h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.18h | limit 3.0h
- Stage66 attention board: **OK** | age 1.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.98h | limit 3.0h
- Stage71 challengers: **OK** | age 0.56h | limit 8.0h
- Stage71C team totals: **OK** | age 3.41h | limit 8.0h
- Stage71E double chance: **OK** | age 3.41h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.41h | limit 8.0h
- Stage71G DNB: **OK** | age 3.41h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.52h | limit 3.0h
- Stage71I settlement: **OK** | age 1.29h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.14h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 8.21h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.52h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.