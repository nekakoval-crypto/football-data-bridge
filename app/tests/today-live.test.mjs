import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatMoscowTime, formatScore, freshnessLabel, sortMatches, statusLabel, todayViewModel,
} from '../today-live.js';

test('normalizes status labels and keeps unknown explicit', () => {
  assert.equal(statusLabel('live'), 'LIVE');
  assert.equal(statusLabel('suspended'), 'Приостановлен');
  assert.equal(statusLabel('unknown'), 'Статус не подтверждён');
  assert.equal(statusLabel('new-provider-state'), 'Статус не подтверждён');
});

test('formats only known scores', () => {
  assert.equal(formatScore(null), '');
  assert.equal(formatScore({home: '2', away: '1'}), '2 : 1');
});

test('maps freshness explicitly', () => {
  assert.equal(freshnessLabel('fresh'), 'Свежие данные');
  assert.equal(freshnessLabel('stale'), 'Данные устарели');
  assert.equal(freshnessLabel('unknown'), 'Свежесть неизвестна');
});

test('orders live, upcoming, exceptional, then finished deterministically', () => {
  const rows = [
    {fixture_id: '2', status: 'finished', kickoff_utc: '2026-09-13T10:00:00Z'},
    {fixture_id: '3', status: 'scheduled', kickoff_utc: '2026-09-13T09:00:00Z'},
    {fixture_id: '1', status: 'live', kickoff_utc: '2026-09-13T12:00:00Z'},
    {fixture_id: '4', status: 'unknown', kickoff_utc: '2026-09-13T08:00:00Z'},
  ];
  assert.deepEqual(sortMatches(rows).map(row => row.fixture_id), ['1', '3', '4', '2']);
});

test('formats kickoff in Moscow time and exposes UTC boundary when dates differ', () => {
  assert.match(formatMoscowTime('2026-09-12T21:30:00Z', '2026-09-13'), /13\.09 · 00:30 МСК/);
  assert.match(formatMoscowTime('2026-09-12T21:30:00Z', '2026-09-12'), /UTC-день 2026-09-12/);
});

test('coverage warning and missing optional fields are safe', () => {
  const model = todayViewModel({
    date_utc: '2026-09-13',
    coverage: {live_completeness_guaranteed: false},
    matches: [{fixture_id: '1', status: 'unknown'}],
  });
  assert.equal(model.coverageWarning, true);
  assert.equal(model.matches.length, 1);
  assert.equal(model.summary.upcoming, 0);
});
