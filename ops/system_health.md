# PBK System Health

Обновлено UTC: 2026-10-02T19:11:31Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 1

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 12.58h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.34h | limit 3.0h
- Stage55 context: **OK** | age 0.81h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.35h | limit 1.5h
- Stage57 international: **OK** | age 12.34h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.10h | limit 3.0h
- Stage59 user execution: **STALE** | age 23.27h | limit 3.0h
- Stage60 forward performance: **STALE** | age 33.21h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 2.20h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.31h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.82h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 2.14h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.98h | limit 3.0h
- Stage71 challengers: **OK** | age 3.40h | limit 8.0h
- Stage71C team totals: **OK** | age 6.37h | limit 8.0h
- Stage71E double chance: **OK** | age 6.37h | limit 8.0h
- Stage71F European handicap: **OK** | age 6.37h | limit 8.0h
- Stage71G DNB: **OK** | age 6.37h | limit 8.0h
- Stage71H readiness: **OK** | age 0.51h | limit 3.0h
- Stage71I settlement: **OK** | age 0.29h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.24h | limit 1.0h
- Stage68 exposure map: **STALE** | age 11.99h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.08h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 23.27h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 33.21h > 3.00h
- **WARN** `STALE_STAGE` — Stage61 EPL steam watch: age 2.20h > 2.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 11.99h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.