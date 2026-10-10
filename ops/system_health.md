# PBK System Health

Обновлено UTC: 2026-10-10T04:08:19Z
Статус: 🔴 **CRITICAL** | critical 2 | warnings 3

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 21.47h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.30h | limit 3.0h
- Stage55 context: **OK** | age 0.84h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.31h | limit 1.5h
- Stage57 international: **STALE** | age 133.72h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.04h | limit 3.0h
- Stage59 user execution: **OK** | age 0.17h | limit 3.0h
- Stage60 forward performance: **STALE** | age 117.04h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 1.57h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.69h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 3.67h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.13h | limit 3.0h
- Stage66 attention board: **OK** | age 1.08h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.96h | limit 3.0h
- Stage71 challengers: **OK** | age 4.44h | limit 8.0h
- Stage71C team totals: **OK** | age 3.24h | limit 8.0h
- Stage71E double chance: **OK** | age 3.24h | limit 8.0h
- Stage71F European handicap: **OK** | age 3.24h | limit 8.0h
- Stage71G DNB: **OK** | age 3.24h | limit 8.0h
- Stage71H readiness: **STALE** | age 3.31h | limit 3.0h
- Stage71I settlement: **OK** | age 1.24h | limit 3.0h
- Stage72 data layer: **OK** | age 0.36h | limit 1.0h
- Stage73 internal API: **OK** | age 0.26h | limit 1.0h
- Stage68 exposure map: **STALE** | age 3.87h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.03h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage57 international: age 133.72h > 30.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 117.04h > 3.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 3.67h > 3.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 3.31h > 3.00h
- **WARN** `STALE_STAGE` — Stage68 exposure map: age 3.87h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.