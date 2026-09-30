# PBK System Health

Обновлено UTC: 2026-09-30T10:08:03Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 3.52h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.82h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.32h | limit 1.5h
- Stage57 international: **OK** | age 3.31h | limit 30.0h
- Stage58 daily brief: **STALE** | age 8.06h | limit 3.0h
- Stage59 user execution: **STALE** | age 17.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 12.22h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.58h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.22h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.75h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.22h | limit 3.0h
- Stage66 attention board: **OK** | age 0.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.94h | limit 3.0h
- Stage71 challengers: **STALE** | age 10.60h | limit 8.0h
- Stage71C team totals: **OK** | age 3.34h | limit 8.0h
- Stage71E double chance: **OK** | age 3.34h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.34h | limit 8.0h
- Stage71G DNB: **OK** | age 3.34h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.43h | limit 3.0h
- Stage71I settlement: **OK** | age 1.25h | limit 3.0h
- Stage72 data layer: **OK** | age 0.17h | limit 1.0h
- Stage73 internal API: **OK** | age 0.10h | limit 1.0h
- Stage68 exposure map: **OK** | age 2.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 8.06h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 17.17h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 12.22h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.75h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 10.60h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.43h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.