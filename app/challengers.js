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
  </article>`;
}
export function initChallengers(root = document) {
  let board = null;
  const list = root.querySelector('#challenger-list');
  const summary = root.querySelector('#challenger-summary');
  const selects = Object.fromEntries(['family', 'status', 'group'].map(key => [key, root.querySelector(`#challenger-${key}`)]));
  function render() {
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
      board = null;
      summary.textContent = 'Актуальность Stage71 не подтверждена.';
      list.innerHTML = '<div class="empty">Не удалось обновить данные. Повторная загрузка — при восстановлении связи или следующем обновлении.</div>';
    }
  };
}
