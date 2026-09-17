# PBK System Health

Обновлено UTC: 2026-09-17T21:06:02Z
Статус: 🟠 **WARN** | critical 0 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 104 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **STALE** | age 38.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.38h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.21h | limit 1.5h
- Stage57 international: **OK** | age 14.31h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **OK** | age 1.25h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.24h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.62h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.31h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **OK** | age 5.60h | limit 8.0h
- Stage71C team totals: **OK** | age 2.37h | limit 8.0h
- Stage71E double chance: **OK** | age 2.37h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.37h | limit 8.0h
- Stage71G DNB: **OK** | age 2.37h | limit 8.0h
- Stage71H readiness: **OK** | age 2.50h | limit 3.0h
- Stage71I settlement: **OK** | age 0.34h | limit 3.0h
- Stage72 data layer: **OK** | age 0.19h | limit 1.0h
- Stage73 internal API: **OK** | age 0.78h | limit 1.0h
- Stage68 exposure map: **OK** | age 0.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage53 screener: age 38.53h > 30.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.