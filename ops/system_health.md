# PBK System Health

Обновлено UTC: 2026-10-10T05:08:18Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 22.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.28h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.29h | limit 1.5h
- Stage57 international: **STALE** | age 134.72h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.04h | limit 3.0h
- Stage59 user execution: **OK** | age 1.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 118.04h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.69h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.67h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 2.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.96h | limit 3.0h
- Stage71 challengers: **OK** | age 5.44h | limit 8.0h
- Stage71C team totals: **OK** | age 4.24h | limit 8.0h
- Stage71E double chance: **OK** | age 4.24h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.24h | limit 8.0h
- Stage71G DNB: **OK** | age 4.24h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.31h | limit 3.0h
- Stage71I settlement: **OK** | age 0.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.09h | limit 1.0h
- Stage73 internal API: **OK** | age 0.23h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.87h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 134.72h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 118.04h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.57h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.69h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.67h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.31h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.87h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.