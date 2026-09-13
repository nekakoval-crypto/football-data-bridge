import test from 'node:test';
import assert from 'node:assert/strict';
import {
  compactRightSideValue, compactStatusLabel, formatMoscowTime, formatScore, freshnessLabel,
  groupMatchesByCompetition, renderTodayLive, sortMatches, statusLabel, todayViewModel,
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

test('uses compact status labels and right-side score/status values', () => {
  assert.equal(compactStatusLabel('finished'), 'FT');
  assert.equal(compactStatusLabel('unknown'), 'Не подтв.');
  assert.equal(compactRightSideValue({status: 'live', score: {home: '2', away: '0'}}), '2:0');
  assert.equal(compactRightSideValue({status: 'unknown'}), 'Не подтв.');
  assert.match(compactRightSideValue({
    status: 'scheduled', kickoff_utc: '2026-09-13T15:30:00Z',
  }), /18:30 МСК/);
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

test('groups competitions after deterministic status and kickoff ordering', () => {
  const groups = groupMatchesByCompetition([
    {fixture_id: '2', competition: 'Лига B', status: 'scheduled', kickoff_utc: '2026-09-13T12:00:00Z'},
    {fixture_id: '1', competition: 'Лига A', status: 'live', kickoff_utc: '2026-09-13T11:00:00Z'},
    {fixture_id: '3', competition: 'Лига B', status: 'live', kickoff_utc: '2026-09-13T10:00:00Z'},
  ]);
  assert.deepEqual(groups.map(group => group.competition), ['Лига B', 'Лига A']);
  assert.deepEqual(groups[0].matches.map(match => match.fixture_id), ['3', '2']);
});

test('coverage warning and missing optional fields are safe', () => {
  const payload = {
    date_utc: '2026-09-13',
    coverage: {live_completeness_guaranteed: false},
    matches: [{fixture_id: '1', status: 'unknown'}],
  };
  const model = todayViewModel(payload);
  assert.equal(model.coverageWarning, true);
  assert.equal(model.matches.length, 1);
  assert.equal(model.summary.upcoming, 0);
  const container = {innerHTML: ''};
  renderTodayLive(container, payload);
  assert.match(container.innerHTML, /LIVE-покрытие неполное/);
  assert.match(container.innerHTML, /Не подтв\./);
});
