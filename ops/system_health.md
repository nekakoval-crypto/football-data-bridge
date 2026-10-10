# PBK System Health

Обновлено UTC: 2026-10-10T03:08:27Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 0

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 20.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **STALE** | age 132.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 12.01h | limit 3.0h
- Stage59 user execution: **STALE** | age 20.06h | limit 3.0h
- Stage60 forward performance: **STALE** | age 116.05h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.69h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.67h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.91h | limit 3.0h
- Stage71 challengers: **OK** | age 3.44h | limit 8.0h
- Stage71C team totals: **OK** | age 2.24h | limit 8.0h
- Stage71E double chance: **OK** | age 2.24h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.24h | limit 8.0h
- Stage71G DNB: **OK** | age 2.24h | limit 8.0h
- Stage71H readiness: **OK** | age 2.31h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.34h | limit 1.0h
- Stage73 internal API: **OK** | age 0.26h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.87h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 132.73h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 12.01h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 20.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 116.05h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.