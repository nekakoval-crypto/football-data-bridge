# PBK System Health

Обновлено UTC: 2026-10-12T00:09:24Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 1.76h | limit 3.0h
- Stage55 context: **OK** | age 1.39h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.11h | limit 1.5h
- Stage57 international: **OK** | age 17.28h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.57h | limit 3.0h
- Stage59 user execution: **OK** | age 1.65h | limit 3.0h
- Stage60 forward performance: **STALE** | age 8.16h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.18h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 3.18h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.59h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 3.05h | limit 3.0h
- Stage66 attention board: **STALE** | age 17.57h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.36h | limit 3.0h
- Stage71 challengers: **OK** | age 4.43h | limit 8.0h
- Stage71C team totals: **OK** | age 1.85h | limit 8.0h
- Stage71E double chance: **OK** | age 1.85h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.85h | limit 8.0h
- Stage71G DNB: **OK** | age 1.85h | limit 8.0h
- Stage71H readiness: **OK** | age 2.00h | limit 3.0h
- Stage71I settlement: **OK** | age 0.17h | limit 3.0h
- Stage72 data layer: **OK** | age 0.26h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.30h | limit 1.0h
- Stage68 exposure map: **STALE** | age 13.45h | limit 3.0h
- Stage69 promotion gate: **STALE** | age 3.42h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 8.16h > 3.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 3.18h > 2.00h
- **WARN** `STALE_STAGE` — Stage65 WATCH performance: age 3.05h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 17.57h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.36h > 3.00h
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.30h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 13.45h > 3.00h
- **WARN** `STALE_STAGE` — Stage69 promotion gate: age 3.42h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.