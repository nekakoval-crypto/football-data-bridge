# Stage74 — PBK App Readiness

Status: **LOCAL/PWA FOUNDATION IMPLEMENTED; REMOTE DEPLOYMENT PENDING SERVER.**

Stage74 can continue without a server while the client remains local/read-only. The project owner is only required again when a permanent remote backend, domain/authentication, or external push delivery must be connected.

## Architecture

- One backend: Stage74 app API, preserving the Stage73 read-only contract over the Stage72 unified data layer.
- One responsive frontend for PC and Android.
- First delivery: installable PWA/web app.
- PC: browser/PWA first; optional desktop wrapper later if needed.
- Android: same frontend as installable PWA first; optional native wrapper/package later.
- No client reads operational CSV/JSON directly; client talks only to the PBK API.
- Canonical/WATCH/research/governance separation remains visible in UI.
- Secrets remain server-side; API-Football key is never shipped to PC/Android clients.

## Implemented

### Stage74A/B — app foundation and match cards

- Dark responsive PWA shell.
- Screens for Today, R1/R2/R3, WATCH, Matches and Health.
- Full match-detail dialog from `/v1/match`.
- Market display filters are presentation-only and never create signals.
- Russian bookmaker notation remains the user-facing standard.

### Stage74C — results / statistics

- `/v1/performance` endpoint.
- Separate prospective canonical and WATCH performance.
- Historical research is not mixed into live forward performance.
- Probability module is explicitly `NOT_VALIDATED_YET`.
- Future UI reserves two independent rankings:
  1. **Максимальная вероятность прохода**.
  2. **Лучший value**.
- No probability percentage is invented before a separately validated probability model exists.

### Stage74D — in-app notification center

- `/v1/notifications` read-only endpoint.
- Notifications are derived from already collected lifecycle/system-health data; **no extra API-Football calls**.
- Supported in-app event families:
  - new canonical R signal;
  - WATCH crossing;
  - confirmed lineup/rotation lifecycle events;
  - settlement/result;
  - fixture/status changes;
  - system-health warnings/errors.
- Notification tab shows unread count.
- Read/unread state is stored locally on the device/browser.
- Filtering by event family and "mark all read" are implemented.
- Match-related notifications open the corresponding match card.
- External push is intentionally disabled with status `PENDING_SERVER`.

CI run **34628016880** completed successfully after Stage74D: frontend syntax, deployment scripts, Stage72 rebuild, Stage73 API contract and Stage74 app API self-test all passed.

## Current screen map

1. Сегодня
2. R1 / R2 / R3
3. WATCH
4. Матчи
5. Уведомления
6. Результаты / Статистика
7. Health
8. Карточка матча (modal/detail view)

### Match card order

1. Match + kickoff + league
2. Canonical status and selection
3. WATCH/research status
4. Marathonbet executable price where available
5. Market view: 1X2, 1Х/Х2/12, Ф(0), European handicap, totals, team totals, BTTS where available
6. Context: rest, cups/Europe, injuries/XI, weather, international window
7. Trigger/open/current/close lifecycle
8. Settlement/P&L after FT

## When the owner is needed

Do **not** block local development on hosting. Bring the owner in only when one of these becomes necessary:

1. **Permanent backend server / hosting account** — to make PBK continuously reachable from PC and Android outside the development environment.
2. **Domain / TLS choice** — optional at first, but useful for a stable installable PWA URL.
3. **Authentication secret / access policy** — default remains private, owner-only access, no public registration in v1.
4. **External push notifications** — requires a permanent HTTPS origin/server and device subscription delivery path.
5. **Google Play account or native signing** — only if later distributing a packaged Android application through a store.

Until one of these gates is reached, code and UI work can continue without owner action.

## Default owner settings

- App name: ПБК
- Language: Russian
- Theme: dark
- Access: private owner-only login when remote deployment begins
- Frontend: responsive PWA first
- PC distribution: PWA/browser first
- Android distribution: installable PWA first; native package later if useful
- Backend: hosted PBK read-only API
