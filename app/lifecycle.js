const meaningful = new Set([
  'SIGNAL_CREATED', 'USER_EXECUTION_FROZEN', 'CONTEXT_SNAPSHOT',
  'WEATHER_SNAPSHOT', 'XI_ROTATION', 'CLOSE_LOCKED',
  'FIXTURE_EVENT', 'FIXTURE_STATUS', 'SETTLEMENT', 'WATCH_SETTLEMENT'
]);

const numeric = value => {
  if (value === null || value === undefined || String(value).trim() === '') return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
};
const time = row => String(row.event_time_utc || row.event_at_utc || row.captured_at_utc || '');
const formatNumber = value => Number.isInteger(value) ? String(value) : String(Number(value.toFixed(6)));

export function oddsSummary(rows) {
  const snapshots = rows.filter(row => String(row.event_type || '').toUpperCase() === 'ODDS_SNAPSHOT')
    .slice().sort((a, b) => time(a).localeCompare(time(b)));
  if (!snapshots.length) return null;
  const values = snapshots.map(row => numeric(row.odds)).filter(value => value !== null);
  const first = numeric(snapshots[0].odds);
  const last = numeric(snapshots[snapshots.length - 1].odds);
  const minimum = values.length ? formatNumber(Math.min(...values)) : '—';
  const maximum = values.length ? formatNumber(Math.max(...values)) : '—';
  return {
    event_type: 'ODDS_SUMMARY',
    event_time_utc: time(snapshots[0]),
    status: snapshots[snapshots.length - 1].status || '',
    selection: snapshots[0].selection || '',
    bookmaker: snapshots[0].bookmaker || '',
    odds: `Коэффициент: первый ${first === null ? '—' : formatNumber(first)} → min ${minimum} → max ${maximum} → последний ${last === null ? '—' : formatNumber(last)} · ${snapshots.length} снимков`
  };
}

export function projectLifecycle(rows = []) {
  const source = Array.isArray(rows) ? rows.slice().sort((a, b) => time(a).localeCompare(time(b))) : [];
  const projected = [];
  const snapshots = new Map();
  for (const row of source) {
    const event = String(row.event_type || '').toUpperCase();
    if (!meaningful.has(event)) continue;
    if (event === 'CONTEXT_SNAPSHOT' || event === 'WEATHER_SNAPSHOT' || event === 'XI_ROTATION') {
      snapshots.set(event, row);
      continue;
    }
    projected.push(row);
  }
  projected.push(...snapshots.values());
  const summary = oddsSummary(source);
  if (summary) projected.push(summary);
  return projected.sort((a, b) => time(a).localeCompare(time(b)) || String(a.event_type || '').localeCompare(String(b.event_type || '')));
}

export function renderLifecycleEvent(row, esc = value => String(value ?? '')) {
  const details = row.odds || row.details || '';
  return `<div class="timeline-item"><b>${esc(row.event_type || 'EVENT')}</b><div>${esc(time(row))}${details ? ` · ${esc(details)}` : ''}</div></div>`;
}
