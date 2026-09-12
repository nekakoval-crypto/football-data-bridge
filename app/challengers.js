const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
export function numeric(value) {
  if (value === null || value === undefined || typeof value === 'boolean' || String(value).trim() === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}
const number = value => numeric(value) === null ? '—' : String(numeric(value));
const percent = value => numeric(value) === null ? '—' : `${numeric(value).toFixed(2)}%`;
export const filterRows = (rows, filters) => rows.filter(row => ['family', 'status', 'group'].every(key => !filters[key] || row[key] === filters[key]));
function gate(row, key, target, label) {
  const remaining = numeric(row[`${key}_remaining_settled`]);
  const progress = remaining === null ? '' : `<progress max="${target}" value="${Math.max(0, Math.min(target, target - remaining))}" aria-label="${label}: до ${target}"></progress>`;
  return `<div class="challenger-gate"><span>${label} · до ${target}: <b>${number(remaining)}</b> settled</span>${progress}</div>`;
}
const value = v => v === null || v === undefined || String(v).trim() === '' ? '—' : esc(v);
export function renderObservation(row) {
  const settled = row.status === 'SETTLED';
  const date = row.kickoff_utc ? new Date(row.kickoff_utc) : null;
  const kickoff = date && Number.isFinite(date.getTime()) ? `${date.toISOString().slice(0, 16).replace('T', ' ')} UTC` : '—';
  const score = settled && numeric(row.final_home_goals) !== null && numeric(row.final_away_goals) !== null ? `${number(row.final_home_goals)} : ${number(row.final_away_goals)}` : '—';
  const profit = settled ? numeric(row.user_profit_u) : null;
  return `<li class="challenger-observation"><b>${value(row.home_team)} — ${value(row.away_team)}</b>
    <div class="meta">Начало: ${kickoff}</div>
    <dl class="observation-fields">${[
      ['Выбор', value(row.selection)], ['Статус', value(row.status)],
      ['Bet365 · frozen', number(row.bet365_price)], ['Marathonbet · executable', number(row.marathonbet_price)],
      ['Счёт · FT', score], ['Результат', settled && ['W', 'L', 'PUSH'].includes(row.result) ? row.result : '—'],
      ['P/L · user_profit_u', profit === null ? '—' : `${profit > 0 ? '+' : ''}${profit.toFixed(3)} u`]
    ].map(([label, v]) => `<div><dt>${label}</dt><dd>${v}</dd></div>`).join('')}</dl></li>`;
}
export function renderCard(row) {
  const settled = numeric(row.prospective_settled);
  const active = ['ACTIVE', 'DEGRADATION_REVIEW', 'SUSPENSION_REVIEW'].includes(row.status);
  return `<article class="panel challenger-card">
    <div class="eyebrow">${esc(row.family)} · ${esc(row.country)} · ${esc(row.group)}</div>
    <h3>${esc(row.league)}</h3>
    <div class="meta">${active ? 'Действующий canonical forward · справочная строка' : 'Research-only · не canonical сигнал'}</div>
    <div class="challenger-status">Статус: <b>${esc(row.status || '—')}</b></div>
    <div class="challenger-flow">${[['Captured', 'prospective_captured', 'Зафиксировано'], ['Executable', 'prospective_executable', 'Доступна цена'], ['Settled', 'prospective_settled', 'Рассчитано']].map(([label, key, title]) => `<div><span>${label}</span><b>${number(row[key])}</b><small>${title}</small></div>`).join('<span aria-hidden="true">→</span>')}</div>
    <dl class="challenger-metrics">${[['Marathonbet coverage', 'marathonbet_coverage_pct'], ['ROI', 'prospective_roi_pct'], ['1H ROI', 'prospective_first_half_roi_pct'], ['2H ROI', 'prospective_second_half_roi_pct']].map(([label, key]) => `<div><dt>${label}</dt><dd>${percent(row[key])}</dd></div>`).join('')}</dl>
    <p class="meta">${settled === null ? 'Размер выборки неизвестен.' : settled < 10 ? 'Слишком мало данных: settled < 10. ROI не позволяет сделать вывод об эффективности.' : 'Наблюдаемый ROI сам по себе не подтверждает эффективность.'} 1H/2H — первая и вторая хронологические половины выборки, не таймы матча.</p>
    ${gate(row, 'review', 60, active ? 'Наблюдение active forward' : 'Review')}
    ${gate(row, 'discovery', 120, 'Discovery')}
    <div class="meta">Путь: ${esc(row.progress_path || '—')}</div>
    <div class="meta">Причина / ограничения: ${esc(row.blocking_reason || 'Не указаны источником')}</div>
    <details class="challenger-observations" data-family="${esc(row.family)}" data-league="${esc(row.league)}">
      <summary>Наблюдения</summary>
      <div class="observation-content" aria-live="polite"></div>
    </details>
  </article>`;
}
export function initChallengers(root = document, request = async path => {
  const response = await fetch(`/api${path}`, {headers: {Accept: 'application/json'}, cache: 'no-store'});
  if (!response.ok) throw new Error('Observations unavailable');
  return response.json();
}) {
  let board = null;
  let generation = 0;
  let observations = new WeakMap();
  const list = root.querySelector('#challenger-list');
  const summary = root.querySelector('#challenger-summary');
  const selects = Object.fromEntries(['family', 'status', 'group'].map(key => [key, root.querySelector(`#challenger-${key}`)]));
  function paint(details, state) {
    details.querySelector('.observation-content').innerHTML = state.error
      ? '<p class="meta">Не удалось загрузить наблюдения.</p><button type="button" data-observation-action="retry">Повторить</button>'
      : `<p class="meta">${state.source === 'canonical' ? 'Canonical forward · справочные наблюдения' : 'Research-only · не canonical сигнал'}. Последние по kickoff, сначала новые.</p>
         <ol class="observation-list">${(state.all ? state.items : state.items.slice(0, 5)).map(renderObservation).join('')}</ol>
         ${state.items.length ? '' : '<p class="meta">Наблюдений пока нет.</p>'}
         ${state.count > 5 ? `<button type="button" data-observation-action="${state.all ? 'collapse' : 'all'}">${state.all ? 'Свернуть до 5' : `Показать все (${state.count})`}</button>` : ''}`;
  }
  async function loadObservations(details, all = false) {
    const version = generation;
    const state = observations.get(details) || {};
    if (state.loading) return;
    state.loading = true;
    observations.set(details, state);
    details.querySelector('.observation-content').innerHTML = '<p class="meta">Загрузка наблюдений…</p>';
    try {
      const items = [];
      let page;
      do {
        const params = new URLSearchParams({family: details.dataset.family, league: details.dataset.league, limit: all ? '500' : '5', offset: String(items.length)});
        page = await request(`/v1/challengers/observations?${params}`);
        if (version !== generation) return;
        if (!page.available || !Array.isArray(page.items) || !Number.isInteger(page.count) || page.count < 0 || (!page.items.length && items.length < page.count)) throw new Error('Invalid observations');
        items.push(...page.items);
      } while (all && items.length < page.count);
      Object.assign(state, {items, count: page.count, source: page.source, all, error: false});
    } catch {
      if (version !== generation) return;
      state.error = true;
    } finally {
      state.loading = false;
    }
    if (version === generation) paint(details, state);
  }
  list.addEventListener('toggle', event => {
    const details = event.target;
    if (details.matches?.('.challenger-observations') && details.open && !observations.has(details)) loadObservations(details);
  }, true);
  list.addEventListener('click', event => {
    const button = event.target.closest?.('[data-observation-action]');
    if (!button) return;
    const details = button.closest('.challenger-observations');
    const state = observations.get(details);
    if (button.dataset.observationAction === 'collapse' && state) { state.all = false; paint(details, state); }
    else loadObservations(details, button.dataset.observationAction === 'all');
  });
  function render() {
    generation++;
    observations = new WeakMap();
    const rows = Array.isArray(board?.rows) ? board.rows.filter(row => row && ['R1', 'R2'].includes(row.family)) : [];
    const filtered = filterRows(rows, Object.fromEntries(Object.entries(selects).map(([key, el]) => [key, el.value])));
    summary.textContent = `${new Set(rows.map(row => row.league)).size} / 16 лиг · ${rows.length} / 32 строк R1/R2 · показано ${filtered.length}. Обновлено UTC: ${board?.progress_generated_at_utc || board?.generated_at_utc || 'неизвестно'}`;
    list.innerHTML = filtered.length ? filtered.map(renderCard).join('') : `<div class="empty">${rows.length ? 'Нет строк по выбранным фильтрам.' : 'Challenger board пока не содержит данных. Это не нулевые результаты.'}</div>`;
  }
  Object.values(selects).forEach(el => el.addEventListener('change', render));
  root.querySelector('#challenger-reset').addEventListener('click', () => { Object.values(selects).forEach(el => { el.value = ''; }); render(); });
  return {
    update(governance) {
      board = governance?.league_challenger;
      for (const [key, el] of Object.entries(selects)) {
        const previous = el.value;
        const values = [...new Set((Array.isArray(board?.rows) ? board.rows : []).filter(row => row && ['R1', 'R2'].includes(row.family)).map(row => row[key]).filter(Boolean))].sort();
        el.innerHTML = '<option value="">Все</option>' + values.map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
        el.value = values.includes(previous) ? previous : '';
      }
      render();
    },
    unavailable() {
      generation++;
      observations = new WeakMap();
      board = null;
      summary.textContent = 'Актуальность Stage71 не подтверждена.';
      list.innerHTML = '<div class="empty">Не удалось обновить данные. Повторная загрузка — при восстановлении связи или следующем обновлении.</div>';
    }
  };
}
