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
  const snapshots = rows.filter(row => String(row.event_type || '').toUpperCase() === 'ODDS_SNAPSHOT');
  const values = snapshots.map(row => numeric(row.odds)).filter(value => value !== null);
  if (!values.length) return null;
  return {
    event_type: 'ODDS_SUMMARY',
    event_time_utc: time(snapshots[0]),
    status: snapshots[snapshots.length - 1].status || '',
    selection: snapshots[0].selection || '',
    bookmaker: snapshots[0].bookmaker || '',
    odds: `Коэффициент: первый ${formatNumber(values[0])} → min ${formatNumber(Math.min(...values))} → max ${formatNumber(Math.max(...values))} → последний ${formatNumber(values[values.length - 1])} · ${snapshots.length} снимков`
  };
}

export function projectLifecycle(rows = []) {
  const source = Array.isArray(rows) ? rows.slice().sort((a, b) => time(a).localeCompare(time(b))) : [];
  const projected = [];
  let previousMaterial = '';
  for (const row of source) {
    const event = String(row.event_type || '').toUpperCase();
    if (!meaningful.has(event)) continue;
    if (event === 'CONTEXT_SNAPSHOT' || event === 'WEATHER_SNAPSHOT' || event === 'XI_ROTATION') {
      const material = `${event}|${row.status || ''}|${row.details || ''}`;
      if (material === previousMaterial) continue;
      previousMaterial = material;
    }
    projected.push(row);
  }
  const summary = oddsSummary(source);
  if (summary) projected.push(summary);
  return projected.sort((a, b) => time(a).localeCompare(time(b)) || String(a.event_type || '').localeCompare(String(b.event_type || '')));
}

export function renderLifecycleEvent(row, esc = value => String(value ?? '')) {
  const details = row.odds || row.details || '';
  return `<div class="timeline-item"><b>${esc(row.event_type || 'EVENT')}</b><div>${esc(time(row))}${details ? ` · ${esc(details)}` : ''}</div></div>`;
}
