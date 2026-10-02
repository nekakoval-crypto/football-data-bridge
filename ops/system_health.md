# PBK System Health

Обновлено UTC: 2026-10-02T22:06:35Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 8

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.32h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.10h | limit 1.5h
- Stage57 international: **OK** | age 15.26h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.01h | limit 3.0h
- Stage59 user execution: **STALE** | age 26.19h | limit 3.0h
- Stage60 forward performance: **STALE** | age 36.13h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.12h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 4.23h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **STALE** | age 5.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.94h | limit 3.0h
- Stage71 challengers: **OK** | age 6.32h | limit 8.0h
- Stage71C team totals: **STALE** | age 9.29h | limit 8.0h
- Stage71E double chance: **STALE** | age 9.29h | limit 8.0h
- Stage71F European handicap: **STALE** | age 9.29h | limit 8.0h
- Stage71G DNB: **STALE** | age 9.29h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.43h | limit 3.0h
- Stage71I settlement: **OK** | age 1.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **STALE** | age 14.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.01h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 26.19h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 36.13h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.12h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 4.23h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.74h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 5.06h > 3.00h
- **WARN** `STALE_STAGE` — Stage71C team totals: age 9.29h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 9.29h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 9.29h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 9.29h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.43h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 14.91h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.