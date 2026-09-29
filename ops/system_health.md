# PBK System Health

Обновлено UTC: 2026-09-29T03:06:58Z
Статус: 🟠 **WARN** | critical 0 | warnings 2

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 20.48h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.35h | limit 3.0h
- Stage55 context: **OK** | age 0.85h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.14h | limit 1.5h
- Stage57 international: **OK** | age 20.28h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.05h | limit 3.0h
- Stage59 user execution: **OK** | age 2.13h | limit 3.0h
- Stage60 forward performance: **STALE** | age 5.20h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.17h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.26h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 0.85h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.17h | limit 3.0h
- Stage66 attention board: **STALE** | age 3.10h | limit 3.0h
- Stage70 lifecycle: **OK** | age 0.97h | limit 3.0h
- Stage71 challengers: **OK** | age 3.57h | limit 8.0h
- Stage71C team totals: **OK** | age 2.33h | limit 8.0h
- Stage71E double chance: **OK** | age 2.33h | limit 8.0h
- Stage71F European handicap: **OK** | age 2.33h | limit 8.0h
- Stage71G DNB: **OK** | age 2.33h | limit 8.0h
- Stage71H readiness: **OK** | age 2.42h | limit 3.0h
- Stage71I settlement: **OK** | age 0.29h | limit 3.0h
- Stage72 data layer: **OK** | age 0.10h | limit 1.0h
- Stage73 internal API: **OK** | age 0.02h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.94h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.04h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage60 forward performance: age 5.20h > 3.00h
- **WARN** `STALE_STAGE` — Stage66 attention board: age 3.10h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.