# PBK System Health

Обновлено UTC: 2026-10-04T22:07:59Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 8.45h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.73h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.12h | limit 1.5h
- Stage57 international: **OK** | age 7.72h | limit 30.0h
- Stage58 daily brief: **STALE** | age 11.16h | limit 3.0h
- Stage59 user execution: **STALE** | age 3.99h | limit 3.0h
- Stage60 forward performance: **STALE** | age 27.39h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 8.37h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.89h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.85h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.10h | limit 3.0h
- Stage66 attention board: **OK** | age 1.02h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 33.38h | limit 3.0h
- Stage71 challengers: **OK** | age 1.32h | limit 8.0h
- Stage71C team totals: **OK** | age 0.80h | limit 8.0h
- Stage71E double chance: **OK** | age 0.80h | limit 8.0h
- Stage71F European handicap: **OK** | age 0.80h | limit 8.0h
- Stage71G DNB: **OK** | age 0.80h | limit 8.0h
- Stage71H readiness: **OK** | age 0.83h | limit 3.0h
- Stage71I settlement: **OK** | age 0.78h | limit 3.0h
- Stage72 data layer: **OK** | age 0.19h | limit 1.0h
- Stage73 internal API: **OK** | age 0.06h | limit 1.0h
- Stage68 exposure map: **STALE** | age 11.12h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 11.16h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 3.99h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 27.39h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 8.37h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.85h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage70 lifecycle: age 33.38h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 11.12h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.