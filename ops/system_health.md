# PBK System Health

Обновлено UTC: 2026-10-06T01:09:41Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 18.44h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.25h | limit 3.0h
- Stage55 context: **OK** | age 0.69h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.24h | limit 1.5h
- Stage57 international: **STALE** | age 34.75h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.09h | limit 3.0h
- Stage59 user execution: **STALE** | age 7.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 18.07h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.60h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.32h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 18.70h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.20h | limit 3.0h
- Stage66 attention board: **OK** | age 0.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.91h | limit 3.0h
- Stage71 challengers: **OK** | age 1.55h | limit 8.0h
- Stage71C team totals: **OK** | age 0.30h | limit 8.0h
- Stage71E double chance: **OK** | age 0.30h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.30h | limit 8.0h
- Stage71G DNB: **OK** | age 0.30h | limit 8.0h
- Stage71H readiness: **OK** | age 0.36h | limit 3.0h
- Stage71I settlement: **OK** | age 2.31h | limit 3.0h
- Stage72 data layer: **OK** | age 0.06h | limit 1.0h
- Stage73 internal API: **OK** | age 0.59h | limit 1.0h
- Stage68 exposure map: **STALE** | age 18.88h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 34.75h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 7.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 18.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.60h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 18.70h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 18.88h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.