export const LABELS = {
  STRONG_VALUE: 'СИЛЬНОЕ РАСХОЖДЕНИЕ', WATCH_VALUE: 'РАСХОЖДЕНИЕ',
  MARKET_DISAGREEMENT: 'РЫНОК НЕ СОГЛАСЕН',
  HIGH_PROB_LOW_VALUE: 'ВЫСОКАЯ ВЕРОЯТНОСТЬ / МАЛО VALUE'
};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '—';
export function renderRadar(payload) {
  if (payload?.status !== 'OK' || !Array.isArray(payload.items)) return '<div class="empty">Данные Radar пока недоступны. Актуальность не подтверждена.</div>';
  const seen = new Set();
  const items = payload.items.filter(row => {
    const key = `${row.api_fixture_id}|${row.selection}`;
    if (!['R1','R2','R3'].includes(row.primary_rule) || !LABELS[row.radar_level] || seen.has(key)) return false;
    seen.add(key); return true;
  });
  return `<p class="meta">Обновлено UTC: ${esc(payload.generated_at_utc || 'неизвестно')}</p>` + (items.length ? items.map(row => `
    <article class="panel radar-card">
      <div class="eyebrow">${LABELS[row.radar_level]}${row.radar_level === 'STRONG_VALUE' && row.radar_tags?.includes('LONGSHOT_STRONG') ? ' · КЭФ ≥2' : ''}</div>
      <h3>${esc(row.home_team)} — ${esc(row.away_team)}</h3>
      <p>${esc(({Away:'П2',Home:'П1',Draw:'Х'})[row.selection] || row.selection)} · ${esc((row.source_rules || [row.primary_rule]).join(' + '))} · ${esc(row.kickoff_utc)}</p>
      <dl class="radar-metrics">${[['ПБК, %',row.p_pbk_pct],['Рынок no-vig, %',row.p_market_pct],['Разница, п.п.',row.edge_pp],['Marathonbet',row.executable_odds],['EV, %',row.ev_pct]].map(([label,value]) => `<div><dt>${label}</dt><dd>${fmt(value)}</dd></div>`).join('')}</dl>
      <p class="meta">ИССЛЕДОВАНИЕ — не новый R-сигнал и не изменение ставки. Research only · не ставка.</p>
      <button type="button" data-fixture="${esc(row.api_fixture_id)}">Открыть карточку матча →</button>
    </article>`).join('') : '<div class="empty">Сейчас нет подходящих пересечений Radar.</div>');
}
export async function loadRadar(root = document, request = fetch) {
  const list = root.querySelector('#value-radar-list');
  if (!list) return;
  try {
    const response = await request('/api/v1/value-radar?limit=100', {headers:{Accept:'application/json'}, cache:'no-store'});
    if (!response.ok) throw new Error('Radar unavailable');
    list.innerHTML = renderRadar(await response.json());
  } catch {
    list.innerHTML = '<div class="empty">Не удалось обновить Radar. Актуальность не подтверждена.</div>';
  }
}
if (typeof document !== 'undefined') {
  loadRadar();
  setInterval(loadRadar, 60000);
}
