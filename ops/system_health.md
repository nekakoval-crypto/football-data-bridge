# PBK System Health

Обновлено UTC: 2026-09-30T14:11:13Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 7.57h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.41h | limit 1.5h
- Stage57 international: **OK** | age 7.36h | limit 30.0h
- Stage58 daily brief: **STALE** | age 12.12h | limit 3.0h
- Stage59 user execution: **STALE** | age 21.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 16.27h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.20h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.28h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.75h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 0.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.97h | limit 3.0h
- Stage71 challengers: **STALE** | age 14.65h | limit 8.0h
- Stage71C team totals: **OK** | age 1.34h | limit 8.0h
- Stage71E double chance: **OK** | age 1.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.34h | limit 8.0h
- Stage71G DNB: **OK** | age 1.34h | limit 8.0h
- Stage71H readiness: **OK** | age 1.43h | limit 3.0h
- Stage71I settlement: **OK** | age 1.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.06h | limit 1.0h
- Stage73 internal API: **OK** | age 0.17h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 12.12h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 21.22h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 16.27h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 14.65h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.