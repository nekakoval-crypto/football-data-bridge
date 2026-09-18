const STATUS_LABELS = {
  scheduled: 'По расписанию', live: 'LIVE', finished: 'FT', postponed: 'Перенесён',
  cancelled: 'Отменён', suspended: 'Приост.', interrupted: 'Прерван',
  abandoned: 'Прекращён', awarded: 'Тех.', walkover: 'Тех. поб.', unknown: 'Не подтв.',
};

const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
}[char]));

export function statusLabel(status) {
  return STATUS_LABELS[status] || STATUS_LABELS.unknown;
}

export function formatScore(score) {
  if (!score || score.home === null || score.home === undefined || score.home === '' ||
      score.away === null || score.away === undefined || score.away === '') return '';
  return `${score.home}:${score.away}`;
}

export function redCardBadge(count) {
  const value = Number(count);
  if (!Number.isInteger(value) || value <= 0) return '';
  return `<span class="today-live-red-card" aria-label="${value === 1 ? 'Удаление' : `Удаления: ${value}`}">🟥${value > 1 ? ` ${value}` : ''}</span>`;
}

export function safeMediaUrl(value) {
  try {
    const url = new URL(String(value || ''));
    return url.protocol === 'https:' ? url.href : '';
  } catch {
    return '';
  }
}

export function roundLabel(value) {
  if (!value) return 'Тур не подтверждён';
  const match = String(value).match(/^Regular Season\s*-\s*(\d+)$/i);
  return match ? `Тур ${match[1]}` : String(value);
}

export function formatScheduledTime(value) {
  if (!value) return {date: 'Дата неизвестна', time: 'Время неизвестно'};
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return {date: 'Дата неизвестна', time: 'Время неизвестно'};
  const parts = new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).formatToParts(date);
  const part = type => parts.find(item => item.type === type)?.value || '';
  return {date: `${part('day')}.${part('month')}`, time: `${part('hour')}:${part('minute')} МСК`};
}

export function sortMatches(matches = []) {
  return [...matches].sort((a, b) => {
    const kickoff = String(a?.kickoff_utc || '').localeCompare(String(b?.kickoff_utc || ''));
    if (kickoff) return kickoff;
    return String(a?.fixture_id || '').localeCompare(String(b?.fixture_id || ''), undefined, {numeric: true});
  });
}

export function liveMatches(leagues = []) {
  return leagues.filter(league => league?.status === 'available')
    .flatMap(league => (Array.isArray(league?.matches) ? league.matches : [])
    .filter(match => match?.status === 'live')
    .map(match => ({...match, provider_league_id: league.provider_league_id})));
}

export function groupMatchesByLeague(leagues = [], mode = 'tour') {
  return leagues.map(league => ({
    ...league,
    matches: sortMatches(mode === 'live'
      ? (Array.isArray(league.matches) ? league.matches.filter(match => match?.status === 'live') : [])
      : (Array.isArray(league.matches) ? league.matches : [])),
  })).filter(league => mode === 'tour'
    ? true
    : league.status === 'available' && league.matches.length);
}

function imageMarkup(url, className, label) {
  const safe = safeMediaUrl(url);
  if (!safe) return `<span class="${className} today-live-image-placeholder" aria-label="${escapeHtml(label)}"></span>`;
  return `<img class="${className}" src="${escapeHtml(safe)}" alt="" loading="lazy" onerror="this.classList.add('today-live-image-broken');this.removeAttribute('src')">`;
}

function compactResearchStatus(value) {
  const status=String(value||'DATA_WAITING').toUpperCase();
  const labels={
    DATA_WAITING:'waiting',
    READY_FOR_VALIDATION:'ready',
    VALIDATION_EVIDENCE_AVAILABLE:'evidence',
    DATA_BLOCKED:'blocked',
    VALIDATION_POLICY_PENDING:'policy pending',
    EVIDENCE_AVAILABLE_NOT_AUTHORIZED:'not authorized',
  };
  return labels[status]||status;
}

function styleMatchupCompact(match={}) {
  const sm=match.style_matchup||{};

  if(!sm||typeof sm!=='object')return '';

  const style=String(
    sm.style_status||'DATA_WAITING'
  );

  const matchup=String(
    sm.matchup_status||'DATA_WAITING'
  );

  return `<div class="today-live-style-matchup">
    <span>STYLE \u00b7 ${escapeHtml(compactResearchStatus(style))}</span>
    <span>MATCHUP \u00b7 ${escapeHtml(compactResearchStatus(matchup))}</span>
  </div>`;
}

function matchStatusLine(match) {
  if (match.status === 'live') {
    return `LIVE${match.source_status ? ` · ${escapeHtml(match.source_status)}` : ''}`;
  }
  return statusLabel(match.status);
}

function matchRow(match) {
  const status = STATUS_LABELS[match.status] ? match.status : 'unknown';
  const scheduled = status === 'scheduled' ? formatScheduledTime(match.kickoff_utc) : null;
  const score = formatScore(match.score);
  const right = score || (scheduled ? `<span>${escapeHtml(scheduled.date)}</span><span>${escapeHtml(scheduled.time)}</span>` : '');
  return `<article class="today-live-row today-live-${status}" data-fixture="${escapeHtml(match.fixture_id)}">
    <div class="today-live-row-main">
      <div class="today-live-team">${imageMarkup(match.home_team_logo_url, 'today-live-team-logo', 'Логотип хозяев')}<span>${escapeHtml(match.home_team || 'Хозяева неизвестны')}${redCardBadge(match.red_cards_home)}</span></div>
      <div class="today-live-team">${imageMarkup(match.away_team_logo_url, 'today-live-team-logo', 'Логотип гостей')}<span>${escapeHtml(match.away_team || 'Гости неизвестны')}${redCardBadge(match.red_cards_away)}</span></div>
      ${styleMatchupCompact(match)}
    </div>
    <div class="today-live-row-side"><strong>${right || escapeHtml(matchStatusLine({...match, status}))}</strong><span class="today-live-status">${escapeHtml(matchStatusLine({...match, status}))}</span></div>
  </article>`;
}

function leagueHeader(league) {
  return `<header class="today-live-league-head">
    <div class="today-live-league-identity">
      ${imageMarkup(league.country_flag_url, 'today-live-flag', 'Флаг страны')}
      <strong>${escapeHtml(league.league_name || 'Лига не подтверждена')}</strong>
      ${imageMarkup(league.league_logo_url, 'today-live-league-logo', 'Логотип лиги')}
    </div>
    <span class="today-live-round">${escapeHtml(roundLabel(league.round))}</span>
  </header>`;
}

export function renderTodayLive(container, payload = {}, selectedMode = 'live') {
  const leagues = Array.isArray(payload.leagues) ? payload.leagues : [];
  const groups = groupMatchesByLeague(leagues, selectedMode);
  const liveCount = liveMatches(leagues).length;
  const warning = payload.coverage?.partial_leagues_possible
    ? '<div class="today-live-notice">Часть данных туров недоступна</div>' : '';
  const generated = payload.generated_at_utc
    ? `Снимок: ${escapeHtml(formatScheduledTime(payload.generated_at_utc).date)} ${escapeHtml(formatScheduledTime(payload.generated_at_utc).time)}`
    : 'Снимок неизвестен';
  let body = '';
  if (selectedMode === 'live' && !liveCount) {
    body = '<div class="empty">Сейчас подтверждённых LIVE-матчей нет.</div>';
  } else if (!groups.length) {
    body = '<div class="empty">Данные тура пока недоступны.</div>';
  } else {
    body = groups.map(league => `<section class="today-live-league-group">
      ${leagueHeader(league)}
      ${league.status !== 'available' ? '<div class="today-live-unavailable">Данные тура недоступны</div>' :
        `<div class="today-live-group-matches">${league.matches.map(matchRow).join('')}</div>`}
    </section>`).join('');
  }
  container.innerHTML = `<div class="today-live-compact-meta"><span>${selectedMode === 'live' ? `LIVE ${liveCount}` : `Лиг ${leagues.length}`}</span><span>${generated}</span></div>${warning}<div class="today-live-groups">${body}</div>`;
}

function renderError(container) {
  container.innerHTML = '<div class="empty today-live-error">Не удалось загрузить данные LIVE / тура.</div>';
}

export function initTodayLive(documentRef = document) {
  const container = documentRef.querySelector('#today-live-content');
  if (!container) return () => {};
  const buttons = [...documentRef.querySelectorAll('[data-today-live-mode]')];
  let selectedMode = 'live';
  let payload = null;
  let loading = false;
  const render = () => {
    buttons.forEach(button => {
      const active = button.dataset.todayLiveMode === selectedMode;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
    });
    if (payload) renderTodayLive(container, payload, selectedMode);
  };
  buttons.forEach(button => button.addEventListener('click', () => {
    selectedMode = button.dataset.todayLiveMode === 'tour' ? 'tour' : 'live';
    render();
  }));
  const load = async () => {
    if (loading) return;
    loading = true;
    try {
      const response = await fetch('/api/v1/rounds/current', {
        headers: {Accept: 'application/json'}, cache: 'no-store',
      });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      payload = await response.json();
      render();
    } catch (error) {
      renderError(container);
      console.error('LIVE / tour unavailable', error);
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
    buttons.forEach(button => button.replaceWith(button.cloneNode(true)));
  };
}

if (typeof document !== 'undefined') initTodayLive();
