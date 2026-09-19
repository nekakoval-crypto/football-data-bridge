# PBK System Health

Обновлено UTC: 2026-09-19T20:05:49Z
Статус: 🟠 **WARN** | critical 0 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 161 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.57h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.42h | limit 3.0h
- Stage55 context: **OK** | age 0.88h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.22h | limit 1.5h
- Stage57 international: **OK** | age 13.37h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **OK** | age 1.23h | limit 3.0h
- Stage60 forward performance: **OK** | age 2.22h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.21h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.78h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.21h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.98h | limit 3.0h
- Stage71 challengers: **OK** | age 4.58h | limit 8.0h
- Stage71C team totals: **OK** | age 1.42h | limit 8.0h
- Stage71E double chance: **OK** | age 1.42h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.42h | limit 8.0h
- Stage71G DNB: **OK** | age 1.42h | limit 8.0h
- Stage71H readiness: **OK** | age 1.54h | limit 3.0h
- Stage71I settlement: **OK** | age 1.30h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.16h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.84h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.