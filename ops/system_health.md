# PBK System Health

Обновлено UTC: 2026-10-08T14:11:35Z
Статус: 🔴 **CRITICAL** | critical 4 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 7.53h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.33h | limit 1.5h
- Stage57 international: **STALE** | age 95.78h | limit 30.0h
- Stage58 daily brief: **STALE** | age 3.08h | limit 3.0h
- Stage59 user execution: **STALE** | age 8.22h | limit 3.0h
- Stage60 forward performance: **STALE** | age 79.10h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 3.58h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.24h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 13.74h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.95h | limit 3.0h
- Stage71 challengers: **OK** | age 6.44h | limit 8.0h
- Stage71C team totals: **OK** | age 1.31h | limit 8.0h
- Stage71E double chance: **OK** | age 1.31h | limit 8.0h
- Stage71F European handicap: **OK** | age 1.31h | limit 8.0h
- Stage71G DNB: **OK** | age 1.31h | limit 8.0h
- Stage71H readiness: **OK** | age 1.40h | limit 3.0h
- Stage71I settlement: **OK** | age 1.17h | limit 3.0h
- Stage72 data layer: **OK** | age 0.07h | limit 1.0h
- Stage73 internal API: **OK** | age 0.11h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.98h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 95.78h > 30.00h
- **WARN** `STALE_STAGE` — Stage58 daily brief: age 3.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 8.22h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 79.10h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 3.58h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 13.74h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.09h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.