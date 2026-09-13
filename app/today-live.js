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

const COMPACT_STATUS_LABELS = {
  scheduled: 'По расписанию',
  live: 'LIVE',
  finished: 'FT',
  postponed: 'Перенесён',
  cancelled: 'Отменён',
  suspended: 'Приост.',
  interrupted: 'Прерван',
  abandoned: 'Прекращён',
  awarded: 'Тех.',
  walkover: 'Тех. поб.',
  unknown: 'Не подтв.',
};

export function statusLabel(status) {
  return STATUS_LABELS[status] || STATUS_LABELS.unknown;
}

export function freshnessLabel(status) {
  return FRESHNESS_LABELS[status] || FRESHNESS_LABELS.unknown;
}

export function compactStatusLabel(status) {
  return COMPACT_STATUS_LABELS[status] || COMPACT_STATUS_LABELS.unknown;
}

export function formatScore(score) {
  if (!score || score.home === null || score.home === undefined ||
      score.away === null || score.away === undefined ||
      score.home === '' || score.away === '') return '';
  return `${score.home} : ${score.away}`;
}

export function compactRightSideValue(match = {}) {
  const score = formatScore(match.score);
  if (score) return score.replaceAll(' ', '');
  if (match.status === 'scheduled' && match.kickoff_utc) {
    const date = new Date(match.kickoff_utc);
    if (!Number.isNaN(date.getTime())) {
      return `${new Intl.DateTimeFormat('ru-RU', {
        timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit',
      }).format(date)} МСК`;
    }
  }
  return compactStatusLabel(match.status);
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

export function groupMatchesByCompetition(matches = []) {
  const groups = new Map();
  for (const match of sortMatches(matches)) {
    const competition = match?.competition || 'Соревнование неизвестно';
    if (!groups.has(competition)) groups.set(competition, []);
    groups.get(competition).push(match);
  }
  return [...groups.entries()].map(([competition, groupedMatches]) => ({
    competition,
    matches: groupedMatches,
  }));
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

function matchRow(match, dateUtc) {
  const status = STATUS_LABELS[match.status] ? match.status : 'unknown';
  const observed = match.observed_at_utc ? ` · ${escapeHtml(compactMoscow(match.observed_at_utc))}` : '';
  return `<article class="today-live-row today-live-${status}" data-fixture="${escapeHtml(match.fixture_id)}">
    <div class="today-live-row-main">
      <div class="today-live-team">${escapeHtml(match.home_team || 'Хозяева неизвестны')}</div>
      <div class="today-live-team">${escapeHtml(match.away_team || 'Гости неизвестны')}</div>
      <div class="today-live-row-meta">${escapeHtml(freshnessLabel(match.freshness_status))}${observed}</div>
    </div>
    <div class="today-live-row-side">
      <strong>${escapeHtml(compactRightSideValue({...match, status}))}</strong>
      <span class="today-live-status">${escapeHtml(compactStatusLabel(status))}</span>
    </div>
  </article>`;
}

export function renderTodayLive(container, payload) {
  const model = todayViewModel(payload);
  const warning = model.coverageWarning
    ? '<div class="today-live-notice">LIVE-покрытие неполное</div>' : '';
  const generated = model.generatedAt ? ` · ${escapeHtml(compactMoscow(model.generatedAt))}` : '';
  const groups = model.matches.length
    ? groupMatchesByCompetition(model.matches).map(group => `<section class="today-live-competition-group">
        <h3>${escapeHtml(group.competition)} <span>${group.matches.length}</span></h3>
        <div>${group.matches.map(match => matchRow(match, model.dateUtc)).join('')}</div>
      </section>`).join('')
    : '<div class="empty">Сегодняшние матчи пока не собраны.</div>';
  container.innerHTML = `<div class="today-live-compact-meta">
    <span>Всего ${model.summary.total} · LIVE ${model.summary.live} · Предст. ${model.summary.upcoming} · Зав. ${model.summary.finished}</span>
    <span>UTC-день ${escapeHtml(model.dateUtc || 'неизвестен')}${generated}</span>
  </div>${warning}<div class="today-live-groups">${groups}</div>`;
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
