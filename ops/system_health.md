# PBK System Health

Обновлено UTC: 2026-10-09T19:08:33Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 12.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.25h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.26h | limit 1.5h
- Stage57 international: **STALE** | age 124.73h | limit 30.0h
- Stage58 daily brief: **STALE** | age 4.01h | limit 3.0h
- Stage59 user execution: **STALE** | age 12.06h | limit 3.0h
- Stage60 forward performance: **STALE** | age 108.05h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.55h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 26.77h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.20h | limit 3.0h
- Stage66 attention board: **OK** | age 0.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **OK** | age 3.38h | limit 8.0h
- Stage71C team totals: **OK** | age 0.33h | limit 8.0h
- Stage71E double chance: **OK** | age 0.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.33h | limit 8.0h
- Stage71G DNB: **OK** | age 0.33h | limit 8.0h
- Stage71H readiness: **OK** | age 0.44h | limit 3.0h
- Stage71I settlement: **OK** | age 0.19h | limit 3.0h
- Stage72 data layer: **OK** | age 0.12h | limit 1.0h
- Stage73 internal API: **OK** | age 0.49h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.95h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.02h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 124.73h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 4.01h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 12.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 108.05h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.55h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.67h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 26.77h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.