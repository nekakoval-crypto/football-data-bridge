# PBK System Health

Обновлено UTC: 2026-10-05T05:19:51Z
Статус: 🔴 **CRITICAL** | critical 5 | warnings 4

## Ключевые проверки
- Stage72 Data Layer: integrity **ok** | tables 192 | schema v15
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 15.65h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.17h | limit 3.0h
- Stage55 context: **OK** | age 0.99h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.18h | limit 1.5h
- Stage57 international: **OK** | age 14.92h | limit 30.0h
- Stage58 daily brief: **STALE** | age 18.36h | limit 3.0h
- Stage59 user execution: **STALE** | age 11.19h | limit 3.0h
- Stage60 forward performance: **STALE** | age 34.58h | limit 3.0h
- Stage61 EPL steam watch: **STALE** | age 6.38h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 1.85h | limit 2.0h
- Stage63 BTTS watch: **STALE** | age 4.88h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.30h | limit 3.0h
- Stage66 attention board: **OK** | age 0.04h | limit 3.0h
- Stage70 lifecycle: **STALE** | age 3.17h | limit 3.0h
- Stage71 challengers: **STALE** | age 8.52h | limit 8.0h
- Stage71C team totals: **OK** | age 4.46h | limit 8.0h
- Stage71E double chance: **OK** | age 4.46h | limit 8.0h
- Stage71F European handicap: **OK** | age 4.46h | limit 8.0h
- Stage71G DNB: **OK** | age 4.46h | limit 8.0h
- Stage71H readiness: **STALE** | age 4.54h | limit 3.0h
- Stage71I settlement: **OK** | age 0.12h | limit 3.0h
- Stage72 data layer: **OK** | age 0.55h | limit 1.0h
- Stage73 internal API: **OK** | age 0.45h | limit 1.0h
- Stage68 exposure map: **STALE** | age 18.31h | limit 3.0h
- Stage69 promotion gate: **OK** | age 1.18h | limit 3.0h

## Проблемы
- **CRITICAL** `STALE_STAGE` — Stage58 daily brief: age 18.36h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage59 user execution: age 11.19h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage60 forward performance: age 34.58h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage61 EPL steam watch: age 6.38h > 2.00h
- **WARN** `STALE_STAGE` — Stage63 BTTS watch: age 4.88h > 3.00h
- **WARN** `STALE_STAGE` — Stage70 lifecycle: age 3.17h > 3.00h
- **WARN** `STALE_STAGE` — Stage71 challengers: age 8.52h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 4.54h > 3.00h
- **CRITICAL** `STALE_STAGE` — Stage68 exposure map: age 18.31h > 3.00h

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.