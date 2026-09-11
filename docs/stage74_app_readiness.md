# Stage74 — PBK App Readiness

Status: PREPARED, UI implementation intentionally starts only after the backend deployment path is fixed.

## Recommended architecture

- One backend: existing Stage73 PBK API over Stage72 data layer.
- One responsive frontend for PC and Android.
- First delivery: installable PWA/web app.
- PC: browser/PWA first; optional desktop wrapper later if needed.
- Android: same frontend as installable PWA first; optional native wrapper/package later.
- No client may read operational CSV/JSON directly; client talks only to the PBK API.
- Canonical/WATCH/research/governance separation must remain visible in UI.

## What is already ready

- Stage72 unified data layer.
- Stage73 read-only PBK API.
- Canonical R1/R2/R3 views.
- WATCH/challenger/lifecycle/exposure/context/odds/attention/governance/health data paths.
- Stage66 attention-board concept and match-market cards.
- Russian bookmaker notation for user-facing markets.

## What the owner needs to prepare

### Required before public/remote app use

1. **Backend hosting account / server**
   - A place where PBK API can run continuously and be reachable from PC/Android.
   - VPS or managed app hosting are both acceptable.
   - GitHub Actions is not the production API host.

2. **Access policy**
   - Default recommendation: private app, one owner account, login required.
   - No public registration in v1.

3. **App identity**
   - Working name can remain `ПБК`.
   - Icon/logo can be temporary and replaced later.
   - Color/theme choice can be deferred; dark theme is a sensible default for odds-heavy screens.

### Only needed later

4. **Domain name** — optional initially; backend can start on a hosting URL.
5. **Google Play developer account** — only if distributing a packaged Android app through Play Store. Not needed for PWA/private testing.
6. **Code signing / desktop installer certificates** — only if/when packaging a native desktop client.
7. **Push notification provider/configuration** — deferred until alert rules are locked.

## Default Stage74 screen map

1. Сегодня
2. R1 / R2 / R3
3. WATCH
4. Матчи
5. Карточка матча
6. Контекст
7. Результаты
8. Статистика
9. Health / Governance

### Match card order

1. Match + kickoff + league
2. Canonical status and selection
3. WATCH/research status
4. Marathonbet executable price
5. Market card: 1X2, 1Х/Х2/12, Ф(0), European handicap, totals, team totals, BTTS where available
6. Context: rest, cups/Europe, injuries/XI, weather, international window
7. Trigger/open/current/close timeline
8. Settlement/P&L after FT

## Stage74 entry gate

We can start frontend coding when all are true:

- Stage73 contract remains green.
- Production/staging backend URL exists.
- API authentication policy is chosen.
- The UI reads Stage73 only, not source ledgers.
- Secrets remain server-side; API-Football key is never shipped to PC/Android clients.

## Owner defaults if no preference is supplied

- App name: ПБК
- Language: Russian
- Theme: dark
- Access: private owner-only login
- Frontend: responsive PWA first
- PC distribution: PWA/browser first
- Android distribution: installable PWA first, native package later if useful
- Backend: hosted Stage73 API

These defaults let development begin without blocking on branding, Play Store, a custom domain, or native packaging.
