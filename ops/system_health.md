# PBK System Health

Обновлено UTC: 2026-10-09T07:12:37Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 0.54h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.26h | limit 3.0h
- Stage55 context: **OK** | age 0.80h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.27h | limit 1.5h
- Stage57 international: **STALE** | age 112.80h | limit 30.0h
- Stage58 daily brief: **STALE** | age 5.09h | limit 3.0h
- Stage59 user execution: **OK** | age 0.13h | limit 3.0h
- Stage60 forward performance: **STALE** | age 96.11h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.19h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.63h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 14.84h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.10h | limit 3.0h
- Stage66 attention board: **STALE** | age 9.12h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **OK** | age 7.54h | limit 8.0h
- Stage71C team totals: **OK** | age 0.33h | limit 8.0h
- Stage71E double chance: **OK** | age 0.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.33h | limit 8.0h
- Stage71G DNB: **OK** | age 0.33h | limit 8.0h
- Stage71H readiness: **OK** | age 0.43h | limit 3.0h
- Stage71I settlement: **OK** | age 0.19h | limit 3.0h
- Stage72 data layer: **OK** | age 0.08h | limit 1.0h
- Stage73 internal API: **OK** | age 0.29h | limit 1.0h
- Stage68 exposure map: **STALE** | age 14.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.06h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 112.80h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 5.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 96.11h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 14.84h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 9.12h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 14.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.