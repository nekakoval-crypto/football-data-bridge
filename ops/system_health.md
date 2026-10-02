# PBK System Health

Обновлено UTC: 2026-10-02T18:09:55Z
Статус: 🔴 **CRITICAL** | critical 3 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 11.55h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.38h | limit 3.0h
- Stage55 context: **OK** | age 0.86h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.09h | limit 1.5h
- Stage57 international: **OK** | age 11.31h | limit 30.0h
- Stage58 daily brief: **OK** | age 1.08h | limit 3.0h
- Stage59 user execution: **STALE** | age 22.25h | limit 3.0h
- Stage60 forward performance: **STALE** | age 32.18h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.18h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.29h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 5.79h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.15h | limit 3.0h
- Stage66 attention board: **OK** | age 1.11h | limit 3.0h
- Stage70 lifecycle: **OK** | age 2.00h | limit 3.0h
- Stage71 challengers: **OK** | age 2.38h | limit 8.0h
- Stage71C team totals: **OK** | age 5.35h | limit 8.0h
- Stage71E double chance: **OK** | age 5.35h | limit 8.0h
- Stage71F European handicap: **OK** | age 5.35h | limit 8.0h
- Stage71G DNB: **OK** | age 5.35h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.44h | limit 3.0h
- Stage71I settlement: **OK** | age 1.28h | limit 3.0h
- Stage72 data layer: **OK** | age 0.14h | limit 1.0h
- Stage73 internal API: **OK** | age 0.03h | limit 1.0h
- Stage68 exposure map: **STALE** | age 10.97h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.05h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 22.24h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 32.18h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 5.79h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.44h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 10.97h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.