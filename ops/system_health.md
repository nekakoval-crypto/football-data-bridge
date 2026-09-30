# PBK System Health

Обновлено UTC: 2026-09-30T15:11:38Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 8.58h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **OK** | age 8.37h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 22.23h | limit 3.0h
- Stage60 forward performance: **STALE** | age 17.28h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.29h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 2.76h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.29h | limit 3.0h
- Stage66 attention board: **OK** | age 1.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.98h | limit 3.0h
- Stage71 challengers: **STALE** | age 15.66h | limit 8.0h
- Stage71C team totals: **OK** | age 2.35h | limit 8.0h
- Stage71E double chance: **OK** | age 2.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.35h | limit 8.0h
- Stage71G DNB: **OK** | age 2.35h | limit 8.0h
- Stage71H readiness: **OK** | age 2.43h | limit 3.0h
- Stage71I settlement: **OK** | age 0.27h | limit 3.0h
- Stage72 data layer: **OK** | age 0.11h | limit 1.0h
- Stage73 internal API: **OK** | age 0.27h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 22.23h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 17.28h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 15.66h > 8.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.