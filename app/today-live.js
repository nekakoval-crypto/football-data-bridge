const STATUS_LABELS = {
  scheduled: 'По расписанию',
  live: 'LIVE',
  finished: 'Завершён',
  postponed: 'Перенесён',
  cancelled: 'Отменён',
  suspended: 'Приостановлен',
  interrupted: 'Прерван',
  abandoned: 'Прекращён',
  awarded: 'Тех. результат',
  walkover: 'Тех. победа',
  unknown: 'Статус не подтверждён',
};

const STATUS_GROUP = {
  live: 0,
  scheduled: 1,
  interrupted: 2,
  suspended: 2,
  postponed: 3,
  cancelled: 3,
  abandoned: 3,
  awarded: 3,
  walkover: 3,
  unknown: 3,
  finished: 4,
};

const FRESHNESS_LABELS = {
  fresh: 'Свежие данные',
  stale: 'Данные устарели',
  unknown: 'Свежесть неизвестна',
};

export function statusLabel(status) {
  return STATUS_LABELS[status] || STATUS_LABELS.unknown;
}

export function freshnessLabel(status) {
  return FRESHNESS_LABELS[status] || FRESHNESS_LABELS.unknown;
}

export function formatScore(score) {
  if (!score || score.home === null || score.home === undefined ||
      score.away === null || score.away === undefined ||
      score.home === '' || score.away === '') return '';
  return `${score.home} : ${score.away}`;
}

export function formatMoscowTime(value, dateUtc = '') {
  if (!value) return 'Время неизвестно';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Время неизвестно';
  const formatted = new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date).replace(',', ' ·');
  const moscowDate = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Moscow',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
  return moscowDate === dateUtc ? `${formatted} МСК` : `${formatted} МСК · UTC-день ${dateUtc || 'неизвестен'}`;
}

export function sortMatches(matches = []) {
  return [...matches].sort((a, b) => {
    const group = (STATUS_GROUP[a?.status] ?? STATUS_GROUP.unknown) -
      (STATUS_GROUP[b?.status] ?? STATUS_GROUP.unknown);
    if (group) return group;
    const kickoff = String(a?.kickoff_utc || '').localeCompare(String(b?.kickoff_utc || ''));
    if (kickoff) return kickoff;
    return String(a?.fixture_id || '').localeCompare(String(b?.fixture_id || ''), undefined, { numeric: true });
  });
}

export function todayViewModel(payload = {}) {
  const matches = sortMatches(Array.isArray(payload.matches) ? payload.matches : []);
  return {
    dateUtc: payload.date_utc || null,
    generatedAt: payload.generated_at_utc || null,
    coverageWarning: payload.coverage?.live_completeness_guaranteed === false,
    matches,
    summary: {
      total: matches.length,
      live: matches.filter(x => x.status === 'live').length,
      upcoming: matches.filter(x => x.status === 'scheduled').length,
      finished: matches.filter(x => x.status === 'finished').length,
    },
  };
}

const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
}[char]));

function compactMoscow(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).format(date).replace(',', ' ·') + ' МСК';
}

function matchCard(match, dateUtc) {
  const status = STATUS_LABELS[match.status] ? match.status : 'unknown';
  const score = formatScore(match.score);
  const observed = match.observed_at_utc ? `<div>Наблюдение: ${escapeHtml(compactMoscow(match.observed_at_utc))}</div>` : '';
  return `<article class="today-live-card today-live-${status}" data-fixture="${escapeHtml(match.fixture_id)}">
    <div class="today-live-card-main">
      <div class="today-live-competition">${escapeHtml(match.competition || 'Соревнование неизвестно')}</div>
      <div class="today-live-teams">${escapeHtml(match.home_team || 'Хозяева неизвестны')} — ${escapeHtml(match.away_team || 'Гости неизвестны')}</div>
      <div class="today-live-meta">${escapeHtml(formatMoscowTime(match.kickoff_utc, dateUtc))}${score ? ` · ${escapeHtml(score)}` : ''}</div>
    </div>
    <div class="today-live-card-side">
      <span class="today-live-status">${escapeHtml(statusLabel(status))}</span>
      <span class="today-live-freshness freshness-${escapeHtml(match.freshness_status || 'unknown')}">${escapeHtml(freshnessLabel(match.freshness_status))}</span>
      ${observed}
    </div>
  </article>`;
}

export function renderTodayLive(container, payload) {
  const model = todayViewModel(payload);
  const warning = model.coverageWarning
    ? '<div class="today-live-notice">LIVE-покрытие неполное: ПБК показывает только уже собранные статусы.</div>' : '';
  const generated = model.generatedAt ? ` · собрано ${escapeHtml(compactMoscow(model.generatedAt))}` : '';
  const cards = model.matches.length
    ? model.matches.map(match => matchCard(match, model.dateUtc)).join('')
    : '<div class="empty">Сегодняшние матчи пока не собраны.</div>';
  container.innerHTML = `<div class="today-live-summary">
    ${[['Всего', model.summary.total], ['LIVE', model.summary.live], ['Предстоящие', model.summary.upcoming], ['Завершены', model.summary.finished]]
      .map(([label, value]) => `<div class="metric"><b>${value}</b><span>${label}</span></div>`).join('')}
  </div>${warning}<div class="today-live-generated">UTC-день ${escapeHtml(model.dateUtc || 'неизвестен')}${generated}</div>
  <div class="today-live-list">${cards}</div>`;
}

function renderError(container) {
  container.innerHTML = '<div class="empty today-live-error">Не удалось загрузить Матчи сегодня / LIVE. Остальные разделы ПБК доступны.</div>';
}

export function initTodayLive(documentRef = document) {
  const container = documentRef.querySelector('#today-live-content');
  if (!container) return () => {};
  let loading = false;
  const load = async () => {
    if (loading) return;
    loading = true;
    try {
      const response = await fetch('/api/v1/today', {
        headers: {Accept: 'application/json'},
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      renderTodayLive(container, await response.json());
    } catch (error) {
      renderError(container);
      console.error('Today/LIVE unavailable', error);
    } finally {
      loading = false;
    }
  };
  const refresh = () => { if (!documentRef.hidden) load(); };
  const timer = setInterval(refresh, 5 * 60 * 1000);
  documentRef.addEventListener('visibilitychange', refresh);
  load();
  return () => {
    clearInterval(timer);
    documentRef.removeEventListener('visibilitychange', refresh);
  };
}

if (typeof document !== 'undefined') initTodayLive();
