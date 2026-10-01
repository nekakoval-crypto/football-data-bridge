# PBK System Health

Обновлено UTC: 2026-10-01T12:11:01Z
Статус: 🔴 **CRITICAL** | critical 1 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 5.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.37h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.40h | limit 1.5h
- Stage57 international: **OK** | age 29.36h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 43.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.20h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.20h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.72h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.29h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.13h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.01h | limit 3.0h
- Stage71 challengers: **STALE** | age 12.64h | limit 8.0h
- Stage71C team totals: **OK** | age 5.36h | limit 8.0h
- Stage71E double chance: **OK** | age 5.36h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.36h | limit 8.0h
- Stage71G DNB: **OK** | age 5.36h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.45h | limit 3.0h
- Stage71I settlement: **OK** | age 1.30h | limit 3.0h
- Stage72 data layer: **OK** | age 0.11h | limit 1.0h
- Stage73 internal API: **OK** | age 0.02h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 43.22h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.84h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.13h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 12.64h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.45h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.