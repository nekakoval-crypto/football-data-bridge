# PBK System Health

Обновлено UTC: 2026-09-29T18:09:21Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.56h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.36h | limit 3.0h
- Stage55 context: **OK** | age 0.88h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.17h | limit 1.5h
- Stage57 international: **OK** | age 11.33h | limit 30.0h
- Stage58 daily brief: **STALE** | age 15.09h | limit 3.0h
- Stage59 user execution: **OK** | age 1.19h | limit 3.0h
- Stage60 forward performance: **STALE** | age 20.24h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.15h | limit 2.0h
- Stage62 Bundesliga totals watch: **STALE** | age 2.68h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 0.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.96h | limit 3.0h
- Stage71 challengers: **STALE** | age 18.61h | limit 8.0h
- Stage71C team totals: **OK** | age 5.16h | limit 8.0h
- Stage71E double chance: **OK** | age 5.16h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.16h | limit 8.0h
- Stage71G DNB: **OK** | age 5.16h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.13h | limit 1.0h
- Stage73 internal API: **OK** | age 0.04h | limit 1.0h
- Stage68 exposure map: **STALE** | age 4.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 15.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 20.24h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.15h > 2.00h
- **WARN** `STALE_STAGE` — Stage62 Bundesliga totals watch: age 2.68h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.84h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage71 challengers: age 18.61h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.44h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 4.94h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.