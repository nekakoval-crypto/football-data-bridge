# PBK System Health

Обновлено UTC: 2026-10-02T07:08:56Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 0.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.26h | limit 3.0h
- Stage55 context: **OK** | age 0.76h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.24h | limit 1.5h
- Stage57 international: **OK** | age 0.30h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.07h | limit 3.0h
- Stage59 user execution: **STALE** | age 11.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 21.16h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.50h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.63h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.73h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.09h | limit 3.0h
- Stage66 attention board: **OK** | age 0.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 7.59h | limit 8.0h
- Stage71C team totals: **OK** | age 0.33h | limit 8.0h
- Stage71E double chance: **OK** | age 0.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.33h | limit 8.0h
- Stage71G DNB: **OK** | age 0.33h | limit 8.0h
- Stage71H readiness: **OK** | age 0.43h | limit 3.0h
- Stage71I settlement: **OK** | age 0.21h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.09h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.98h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.02h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.07h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 11.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 21.16h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.73h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.