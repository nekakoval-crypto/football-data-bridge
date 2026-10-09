# PBK System Health

Обновлено UTC: 2026-10-09T04:09:03Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 21.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.29h | limit 3.0h
- Stage55 context: **OK** | age 0.83h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **STALE** | age 109.74h | limit 30.0h
- Stage58 daily brief: **OK** | age 2.03h | limit 3.0h
- Stage59 user execution: **OK** | age 0.15h | limit 3.0h
- Stage60 forward performance: **STALE** | age 93.06h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.55h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.67h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 11.78h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.12h | limit 3.0h
- Stage66 attention board: **STALE** | age 6.06h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **OK** | age 4.48h | limit 8.0h
- Stage71C team totals: **OK** | age 3.21h | limit 8.0h
- Stage71E double chance: **OK** | age 3.21h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.21h | limit 8.0h
- Stage71G DNB: **OK** | age 3.21h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.29h | limit 3.0h
- Stage71I settlement: **OK** | age 1.26h | limit 3.0h
- Stage72 data layer: **OK** | age 0.06h | limit 1.0h
- Stage73 internal API: **OK** | age 0.25h | limit 1.0h
- Stage68 exposure map: **STALE** | age 11.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 109.74h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 93.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 11.78h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage66 attention board: age 6.06h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.29h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 11.91h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.