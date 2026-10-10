# PBK System Health

Обновлено UTC: 2026-10-10T17:06:55Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 10.50h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **OK** | age 10.25h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 6.18h | limit 3.0h
- Stage60 forward performance: **STALE** | age 130.02h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.58h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.23h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.76h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.10h | limit 3.0h
- Stage66 attention board: **STALE** | age 7.07h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.93h | limit 3.0h
- Stage71 challengers: **OK** | age 1.37h | limit 8.0h
- Stage71C team totals: **OK** | age 4.29h | limit 8.0h
- Stage71E double chance: **OK** | age 4.29h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.29h | limit 8.0h
- Stage71G DNB: **OK** | age 4.29h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.39h | limit 3.0h
- Stage71I settlement: **OK** | age 0.23h | limit 3.0h
- Stage72 data layer: **OK** | age 0.20h | limit 1.0h
- Stage73 internal API: **OK** | age 0.07h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.89h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 6.18h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 130.02h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.58h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.76h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 7.07h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.93h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.39h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.90h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.