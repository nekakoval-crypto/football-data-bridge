# PBK System Health

Обновлено UTC: 2026-10-01T21:07:05Z
Статус: 🔴 **CRITICAL** | critical 7 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 14.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.76h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 38.29h | limit 30.0h
- Stage58 daily brief: **STALE** | age 6.03h | limit 3.0h
- Stage59 user execution: **OK** | age 1.20h | limit 3.0h
- Stage60 forward performance: **STALE** | age 11.13h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.12h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.23h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 8.72h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.23h | limit 3.0h
- Stage66 attention board: **OK** | age 2.07h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **STALE** | age 21.57h | limit 8.0h
- Stage71C team totals: **STALE** | age 8.29h | limit 8.0h
- Stage71E double chance: **STALE** | age 8.29h | limit 8.0h
- Stage71F European handicap: **STALE** | age 8.29h | limit 8.0h
- Stage71G DNB: **STALE** | age 8.29h | limit 8.0h
- Stage71H readiness: **OK** | age 2.42h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.09h | limit 1.0h
- Stage68 exposure map: **STALE** | age 7.88h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage57 international: age 38.29h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 6.03h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 11.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.13h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.23h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 8.72h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 21.57h > 8.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 8.29h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 8.29h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 8.29h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 8.29h > 8.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 7.89h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.