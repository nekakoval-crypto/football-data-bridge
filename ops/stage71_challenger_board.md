# PBK Stage71 — League & Market Challenger Board

Обновлено UTC: 2026-09-11T12:27:06Z
Scope: 16 лиг | API catalog: 16/16 | API calls this run: 0

> Лидер — описательный статус. Stage71 не меняет canonical R1/R2 автоматически.

## R1 | текущий лидер: **Serie A**

| Лига | Статус | TRAIN ROI | TEST ROI | Forward settled | Forward ROI |
|---|---|---:|---:|---:|---:|
| Premier League | MONITORING_REJECTED_CURRENT_RULE | 0.33 | -5.58 | 0 | — |
| La Liga | MONITORING_REJECTED_CURRENT_RULE | -5.56 | 0.11 | 0 | — |
| Serie A 🏆 | ACTIVE | 6.85 | 6.13 | 0 | — |
| Bundesliga | MONITORING_REJECTED_CURRENT_RULE | -10.87 | -5.90 | 0 | — |
| Ligue 1 | MONITORING_REJECTED_CURRENT_RULE | -3.53 | -3.81 | 0 | — |
| Austrian Bundesliga | DATA_REQUIRED | — | — | 0 | — |
| Belgian Pro League | DATA_REQUIRED | — | — | 0 | — |
| Danish Superliga | DATA_REQUIRED | — | — | 0 | — |
| A Lyga | DATA_REQUIRED | — | — | 0 | — |
| Virsliga | DATA_REQUIRED | — | — | 0 | — |
| Eredivisie | DATA_REQUIRED | — | — | 0 | — |
| Eliteserien | DATA_REQUIRED | — | — | 0 | — |
| Ekstraklasa | DATA_REQUIRED | — | — | 0 | — |
| Primeira Liga | DATA_REQUIRED | — | — | 0 | — |
| Super Lig | DATA_REQUIRED | — | — | 0 | — |
| Scottish Premiership | DATA_REQUIRED | — | — | 0 | — |

## R2 | текущий лидер: **Serie A**

| Лига | Статус | TRAIN ROI | TEST ROI | Forward settled | Forward ROI |
|---|---|---:|---:|---:|---:|
| Premier League | MONITORING_REJECTED_CURRENT_RULE | -0.43 | -8.73 | 0 | — |
| La Liga | MONITORING_REJECTED_CURRENT_RULE | -5.46 | -7.44 | 0 | — |
| Serie A 🏆 | ACTIVE | 7.23 | 9.10 | 0 | — |
| Bundesliga | MONITORING_REJECTED_CURRENT_RULE | -10.93 | -4.23 | 0 | — |
| Ligue 1 | MONITORING_REJECTED_CURRENT_RULE | -2.83 | -6.07 | 0 | — |
| Austrian Bundesliga | DATA_REQUIRED | — | — | 0 | — |
| Belgian Pro League | DATA_REQUIRED | — | — | 0 | — |
| Danish Superliga | DATA_REQUIRED | — | — | 0 | — |
| A Lyga | DATA_REQUIRED | — | — | 0 | — |
| Virsliga | DATA_REQUIRED | — | — | 0 | — |
| Eredivisie | DATA_REQUIRED | — | — | 0 | — |
| Eliteserien | DATA_REQUIRED | — | — | 0 | — |
| Ekstraklasa | DATA_REQUIRED | — | — | 0 | — |
| Primeira Liga | DATA_REQUIRED | — | — | 0 | — |
| Super Lig | DATA_REQUIRED | — | — | 0 | — |
| Scottish Premiership | DATA_REQUIRED | — | — | 0 | — |

## Правило обновления
- Здоровый ACTIVE не вытесняется автоматически.
- Новый чемпионат может стать REVIEW_ELIGIBLE только после historical + prospective gate.
- Если ACTIVE деградирует, открывается отдельный review; никакой автопаузы ставок.
- Отсутствие данных = DATA_REQUIRED, а не нулевая эффективность.