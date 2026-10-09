# PBK System Health

Обновлено UTC: 2026-10-09T11:09:22Z
Статус: 🔴 **CRITICAL** | critical 6 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 4.49h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.31h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.31h | limit 1.5h
- Stage57 international: **STALE** | age 116.74h | limit 30.0h
- Stage58 daily brief: **STALE** | age 9.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 4.08h | limit 3.0h
- Stage60 forward performance: **STALE** | age 100.06h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 5.14h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.65h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 18.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.26h | limit 3.0h
- Stage66 attention board: **OK** | age 0.09h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.95h | limit 3.0h
- Stage71 challengers: **OK** | age 3.38h | limit 8.0h
- Stage71C team totals: **OK** | age 4.28h | limit 8.0h
- Stage71E double chance: **OK** | age 4.28h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.28h | limit 8.0h
- Stage71G DNB: **OK** | age 4.28h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.37h | limit 3.0h
- Stage71I settlement: **OK** | age 0.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.47h | limit 1.0h
- Stage73 internal API: **OK** | age 0.36h | limit 1.0h
- Stage68 exposure map: **STALE** | age 18.91h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 116.74h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 9.04h > 3.00h
- **WARN** `STALE_STAGE` — Stage59 user execution: age 4.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 100.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 5.14h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 18.79h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.37h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 18.91h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.