# PBK System Health

Обновлено UTC: 2026-10-14T14:50:36Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 5

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 2.91h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.85h | limit 3.0h
- Stage55 context: **OK** | age 1.26h | limit 3.0h
- Stage56 weather/XI: **STALE** | age 2.35h | limit 1.5h
- Stage57 international: **STALE** | age 79.96h | limit 30.0h
- Stage58 daily brief: **STALE** | age 14.09h | limit 3.0h
- Stage59 user execution: **STALE** | age 8.10h | limit 3.0h
- Stage60 forward performance: **STALE** | age 70.85h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 4.18h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.74h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.27h | limit 3.0h
- Stage65 WATCH performance: **STALE** | age 4.39h | limit 3.0h
- Stage66 attention board: **STALE** | age 14.15h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.70h | limit 3.0h
- Stage71 challengers: **OK** | age 1.80h | limit 8.0h
- Stage71C team totals: **OK** | age 2.58h | limit 8.0h
- Stage71E double chance: **OK** | age 2.58h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.58h | limit 8.0h
- Stage71G DNB: **OK** | age 2.58h | limit 8.0h
- Stage71H readiness: **OK** | age 2.70h | limit 3.0h
- Stage71I settlement: **OK** | age 0.81h | limit 3.0h
- Stage72 data layer: **OK** | age 0.90h | limit 1.0h
- Stage73 internal API: **STALE** | age 1.64h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.66h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.63h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage56 weather/XI: age 2.35h > 1.50h
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 79.96h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 14.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 8.10h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 70.85h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 4.18h > 2.00h
- **WARN** `STALE_STAGE` — Stage65 WATCH performance: age 4.39h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 14.15h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.70h > 3.00h
- **WARN** `STALE_STAGE` — Stage73 internal API: age 1.64h > 1.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.66h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.