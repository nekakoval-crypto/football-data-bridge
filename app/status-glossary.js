export const STATUS_GLOSSARY = Object.freeze({
  CANONICAL: 'БРАТЬ ПО СИСТЕМЕ',
  WATCH: 'НАБЛЮДЕНИЕ',
  VALUE_RADAR: 'РАСХОЖДЕНИЕ С РЫНКОМ',
  RESEARCH: 'ИССЛЕДОВАНИЕ',
  MARKET_VIEW: 'РЫНОК',
  ACTION_REQUIRED: 'НУЖНО ДЕЙСТВИЕ',
  SYSTEM_WARNING: 'СИСТЕМНОЕ ПРЕДУПРЕЖДЕНИЕ',
  INFO: 'ИНФОРМАЦИЯ'
});

const canonicalRules = new Set(['R1', 'R2', 'R3']);
const warningStates = new Set(['CRITICAL', 'ERROR', 'FAIL', 'BLOCKED', 'STALE']);
const actionStates = new Set(['ACTION_REQUIRED', 'MANUAL_REVIEW', 'REVIEW_REQUIRED']);

export function statusClass(value = {}) {
  const row = typeof value === 'string' ? {status: value} : value || {};
  const raw = String(row.status || row.state || '').trim().toUpperCase();
  if (row.action_required === true || actionStates.has(raw)) return 'ACTION_REQUIRED';
  if (row.canonical === true || row.entity_type === 'CANONICAL' || canonicalRules.has(String(row.rule || '').toUpperCase())) return 'CANONICAL';
  if (row.blocking === true && (row.system_warning === true || warningStates.has(raw))) return 'SYSTEM_WARNING';
  if (row.value_radar === true || row.category === 'VALUE_RADAR' || row.radar_kind) return 'VALUE_RADAR';
  if (row.watch === true || row.entity_type === 'WATCH' || row.category === 'WATCH') return 'WATCH';
  if (row.research === true || row.category === 'RESEARCH') return 'RESEARCH';
  if (row.market_view === true || row.category === 'MARKET_VIEW') return 'MARKET_VIEW';
  if (row.system_warning === true || warningStates.has(raw)) return 'SYSTEM_WARNING';
  return 'INFO';
}

export function statusLabel(value = {}) {
  return STATUS_GLOSSARY[statusClass(value)];
}
