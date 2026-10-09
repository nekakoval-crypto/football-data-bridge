# PBK System Health

Обновлено UTC: 2026-10-09T15:10:27Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 8.51h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.29h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.30h | limit 1.5h
- Stage57 international: **STALE** | age 120.76h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.04h | limit 3.0h
- Stage59 user execution: **STALE** | age 8.09h | limit 3.0h
- Stage60 forward performance: **STALE** | age 104.08h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.52h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.62h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 22.81h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **STALE** | age 4.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.93h | limit 3.0h
- Stage71 challengers: **OK** | age 7.40h | limit 8.0h
- Stage71C team totals: **OK** | age 2.32h | limit 8.0h
- Stage71E double chance: **OK** | age 2.32h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.32h | limit 8.0h
- Stage71G DNB: **OK** | age 2.32h | limit 8.0h
- Stage71H readiness: **OK** | age 2.42h | limit 3.0h
- Stage71I settlement: **OK** | age 0.22h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.08h | limit 1.0h
- Stage68 exposure map: **STALE** | age 22.93h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.02h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 120.76h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 8.09h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 104.08h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage63 BTTS watch: age 22.81h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 4.10h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 22.93h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.