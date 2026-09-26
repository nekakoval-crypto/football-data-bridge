# PBK System Health

Обновлено UTC: 2026-09-26T23:05:59Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 190 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 16.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.20h | limit 1.5h
- Stage57 international: **OK** | age 16.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **OK** | age 0.22h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.21h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.68h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.80h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.18h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **STALE** | age 39.53h | limit 8.0h
- Stage71C team totals: **OK** | age 4.38h | limit 8.0h
- Stage71E double chance: **OK** | age 4.38h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.38h | limit 8.0h
- Stage71G DNB: **OK** | age 4.38h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.50h | limit 3.0h
- Stage71I settlement: **OK** | age 0.31h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.12h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.96h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.57h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.68h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.80h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 39.53h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.50h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.