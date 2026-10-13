# PBK System Health

Обновлено UTC: 2026-10-13T04:55:35Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 7

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 13.44h | limit 30.0h
- Stage54 odds/closing: **OK** | age 2.70h | limit 3.0h
- Stage55 context: **OK** | age 2.41h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 1.68h | limit 1.5h
- Stage57 international: **STALE** | age 46.05h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.88h | limit 3.0h
- Stage59 user execution: **OK** | age 2.65h | limit 3.0h
- Stage60 forward performance: **STALE** | age 36.93h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.25h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.39h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 6.06h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 1.74h | limit 3.0h
- Stage66 attention board: **STALE** | age 10.63h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 5.43h | limit 3.0h
- Stage71 challengers: **OK** | age 1.19h | limit 8.0h
- Stage71C team totals: **OK** | age 3.99h | limit 8.0h
- Stage71E double chance: **OK** | age 3.99h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.99h | limit 8.0h
- Stage71G DNB: **OK** | age 3.99h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.06h | limit 3.0h
- Stage71I settlement: **STALE** | age 5.70h | limit 3.0h
- Stage72 data layer: **STALE** | age 3.34h | limit 1.0h
- Stage73 internal API: **STALE** | age 2.34h | limit 1.0h
- Stage68 exposure map: **STALE** | age 12.23h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.37h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage56 weather/XI: age 1.68h > 1.50h
- **WARN** `STALE_STAGE` — Stage57 international: age 46.05h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.88h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 36.93h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.25h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 6.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 10.63h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 5.43h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.06h > 3.00h
- **WARN** `STALE_STAGE` — Stage71I settlement: age 5.70h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage72 data layer: age 3.34h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage73 internal API: age 2.34h > 1.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 12.23h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.