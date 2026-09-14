# PBK System Health

Обновлено UTC: 2026-09-14T06:08:32Z
Статус: 🟠 **WARN** | critical 0 | warnings 6

## Ключевые проверки
- Активные canonical: 2
- Frozen Marathonbet execution: 2/2
- Context coverage: 2/2
- WATCH crossings накоплено: 11
- Team Totals: openers 1743 | snapshots 12402
- Double Chance: openers 188 | snapshots 1138
- European Handicap: openers 974 | snapshots 5415
- Ф(0): openers 168 | snapshots 912
- Stage72 Data Layer: integrity **ok** | tables 84 | schema v10
- Stage73 Internal API: tests **16/16** | API v1

## Свежесть этапов
- Stage53 screener: **OK** | age 17.33h | limit 30.0h
- Stage54 odds/closing: **OK** | age 0.40h | limit 3.0h
- Stage55 context: **OK** | age 0.87h | limit 3.0h
- Stage56 weather/XI: **OK** | age 0.21h | limit 1.5h
- Stage57 international: **OK** | age 23.38h | limit 30.0h
- Stage58 daily brief: **OK** | age 0.08h | limit 3.0h
- Stage59 user execution: **OK** | age 0.25h | limit 3.0h
- Stage60 forward performance: **OK** | age 0.24h | limit 3.0h
- Stage61 EPL steam watch: **OK** | age 0.67h | limit 2.0h
- Stage62 Bundesliga totals watch: **OK** | age 0.31h | limit 2.0h
- Stage63 BTTS watch: **OK** | age 1.86h | limit 3.0h
- Stage65 WATCH performance: **OK** | age 0.01h | limit 3.0h
- Stage66 attention board: **OK** | age 0.13h | limit 3.0h
- Stage70 lifecycle: **OK** | age 1.01h | limit 3.0h
- Stage71 challengers: **OK** | age 6.66h | limit 8.0h
- Stage71C team totals: **STALE** | age 11.45h | limit 8.0h
- Stage71E double chance: **STALE** | age 11.45h | limit 8.0h
- Stage71F European handicap: **STALE** | age 11.45h | limit 8.0h
- Stage71G DNB: **STALE** | age 11.45h | limit 8.0h
- Stage71H readiness: **STALE** | age 5.47h | limit 3.0h
- Stage71I settlement: **OK** | age 1.31h | limit 3.0h
- Stage72 data layer: **OK** | age 0.18h | limit 1.0h
- Stage73 internal API: **OK** | age 0.84h | limit 1.0h
- Stage68 exposure map: **OK** | age 1.99h | limit 3.0h
- Stage69 promotion gate: **OK** | age 0.06h | limit 3.0h

## Проблемы
- **WARN** `STALE_STAGE` — Stage71C team totals: age 11.45h > 8.00h
- **WARN** `STALE_STAGE` — Stage71E double chance: age 11.45h > 8.00h
- **WARN** `STALE_STAGE` — Stage71F European handicap: age 11.45h > 8.00h
- **WARN** `STALE_STAGE` — Stage71G DNB: age 11.45h > 8.00h
- **WARN** `STALE_STAGE` — Stage71H readiness: age 5.47h > 3.00h
- **WARN** `SCHEMA_VERSION` — Expected Stage72 schema v6, got 10

> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.

## API-Football budget guard
- Stage71J real calls: **177/190 per run**
- Shared-cache hits: **459**
- Child warnings: **0**
- Budget status: **OK**
