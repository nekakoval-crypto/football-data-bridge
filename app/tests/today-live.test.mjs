import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {
  formatScore, formatScheduledTime, groupMatchesByLeague, liveMatches, renderTodayLive,
  redCardBadge, roundLabel, safeMediaUrl, sortMatches,
} from '../today-live.js';

const fixture = (id, status, kickoff, extra = {}) => ({
  fixture_id: String(id), status, kickoff_utc: kickoff,
  home_team: `Home ${id}`, away_team: `Away ${id}`,
  home_team_logo_url: 'https://cdn.test/home.png',
  away_team_logo_url: 'https://cdn.test/away.png',
  ...extra,
});

const payload = {
  generated_at_utc: '2026-09-13T15:00:00Z',
  coverage: {partial_leagues_possible: true},
  leagues: [
    {
      provider_league_id: '39', league_name: 'Premier League', country: 'England',
      country_flag_url: 'https://cdn.test/gb.png', league_logo_url: 'https://cdn.test/epl.png',
      round: 'Regular Season - 4', status: 'available',
      matches: [
        fixture(2, 'scheduled', '2026-09-14T16:30:00Z'),
        fixture(1, 'finished', '2026-09-14T14:00:00Z', {score: {home: '2', away: '1'}, source_status: 'FT'}),
        fixture(3, 'live', '2026-09-14T15:00:00Z', {score: null, source_status: '1H'}),
        fixture(4, 'postponed', '2026-09-14T17:00:00Z'),
      ],
    },
    {
      provider_league_id: '140', league_name: 'La Liga', country: 'Spain',
      country_flag_url: null, league_logo_url: null, round: 'Matchday 4',
      status: 'available', matches: [fixture(5, 'scheduled', '2026-09-15T16:00:00Z')],
    },
    {
      provider_league_id: '61', league_name: 'Ligue 1', country: 'France',
      round: null, status: 'unavailable', error: 'provider error', matches: [],
    },
  ],
};

test('LIVE and ТУР data preserve league order and deterministic match chronology', () => {
  assert.deepEqual(groupMatchesByLeague(payload.leagues, 'live').map(x => x.league_name),
    ['Premier League']);
  assert.deepEqual(liveMatches(payload.leagues).map(x => x.fixture_id), ['3']);
  assert.deepEqual(groupMatchesByLeague(payload.leagues, 'tour')[0].matches.map(x => x.fixture_id),
    ['1', '3', '2', '4']);
  assert.deepEqual(sortMatches([{fixture_id: '10'}, {fixture_id: '2'}]).map(x => x.fixture_id), ['2', '10']);
});

test('round formatting and null round stay explicit', () => {
  assert.equal(roundLabel('Regular Season - 4'), 'Тур 4');
  assert.equal(roundLabel('Matchday 4'), 'Matchday 4');
  assert.equal(roundLabel(null), 'Тур не подтверждён');
});

test('media URLs accept only HTTPS and scores never invent 0:0', () => {
  assert.equal(safeMediaUrl('https://cdn.test/logo.png'), 'https://cdn.test/logo.png');
  assert.equal(safeMediaUrl('http://cdn.test/logo.png'), '');
  assert.equal(safeMediaUrl(null), '');
  assert.equal(formatScore(null), '');
  assert.equal(formatScore({home: 0, away: 0}), '0:0');
});

test('red-card badges render one, multiple, and no unavailable cards', () => {
  assert.equal(redCardBadge(1), '<span class="today-live-red-card" aria-label="Удаление">🟥</span>');
  assert.equal(redCardBadge(2), '<span class="today-live-red-card" aria-label="Удаления: 2">🟥 2</span>');
  assert.equal(redCardBadge(0), '');
  assert.equal(redCardBadge(null), '');
});

test('LIVE and ТУР render confirmed red cards next to the affected teams', () => {
  const container = {innerHTML: ''};
  const leagues = [{...payload.leagues[0], matches: [
    fixture(9, 'live', '2026-09-14T15:00:00Z',
      {red_cards_home: 1, red_cards_away: 2, score: {home: 0, away: 1}}),
  ]}];
  renderTodayLive(container, {leagues}, 'live');
  assert.match(container.innerHTML, /Home 9<span class="today-live-red-card"[^>]*>🟥<\/span>/);
  assert.match(container.innerHTML, /Away 9<span class="today-live-red-card"[^>]*>🟥 2<\/span>/);
  renderTodayLive(container, {leagues}, 'tour');
  assert.match(container.innerHTML, /🟥 2/);
});

test('scheduled kickoff contains Moscow date and time', () => {
  assert.deepEqual(formatScheduledTime('2026-09-14T16:30:00Z'), {date: '14.09', time: '19:30 МСК'});
});

test('LIVE mode renders only confirmed live matches and explicit empty state', () => {
  const container = {innerHTML: ''};
  renderTodayLive(container, payload, 'live');
  assert.match(container.innerHTML, /LIVE · 1H/);
  assert.match(container.innerHTML, /data-fixture="3"/);
  assert.doesNotMatch(container.innerHTML, /data-fixture="1"/);
  assert.doesNotMatch(container.innerHTML, /data-fixture="2"/);
  renderTodayLive(container, {...payload, leagues: payload.leagues.map(x => ({...x, matches: []}))}, 'live');
  assert.match(container.innerHTML, /Сейчас подтверждённых LIVE-матчей нет/);
});

test('ТУР renders complete rounds, logos, order, unavailable league, and warning', () => {
  const container = {innerHTML: ''};
  renderTodayLive(container, payload, 'tour');
  assert.match(container.innerHTML, /data-fixture="1"/);
  assert.match(container.innerHTML, /data-fixture="3"/);
  assert.match(container.innerHTML, /data-fixture="4"/);
  assert.match(container.innerHTML, /Данные тура недоступны/);
  assert.match(container.innerHTML, /Часть данных туров недоступна/);
  assert.match(container.innerHTML, /https:\/\/cdn.test\/gb.png/);
  assert.match(container.innerHTML, /https:\/\/cdn.test\/epl.png/);
  assert.match(container.innerHTML, /https:\/\/cdn.test\/home.png/);
  assert.match(container.innerHTML, /https:\/\/cdn.test\/away.png/);
  assert.match(container.innerHTML, /Тур 4/);
  assert.match(container.innerHTML, /Matchday 4/);
  assert.match(container.innerHTML, /Тур не подтверждён/);
  assert.match(container.innerHTML, /2:1/);
  assert.doesNotMatch(container.innerHTML, /0:0/);
  assert.match(container.innerHTML, /14\.09/);
  assert.match(container.innerHTML, /19:30 МСК/);
  assert.match(container.innerHTML, /data-fixture="1"[\s\S]*data-fixture="3"[\s\S]*data-fixture="2"/);
});

test('invalid and missing media use reserved placeholders and text is escaped', () => {
  const container = {innerHTML: ''};
  renderTodayLive(container, {
    leagues: [{league_name: '<League>', status: 'available', matches: [{
      ...fixture('<x>', 'unknown', null, {home_team_logo_url: 'javascript:bad', away_team_logo_url: null}),
      home_team: '<Home>',
    }]}],
  }, 'tour');
  assert.match(container.innerHTML, /&lt;League&gt;/);
  assert.match(container.innerHTML, /&lt;Home&gt;/);
  assert.match(container.innerHTML, /today-live-image-placeholder/);
  assert.doesNotMatch(container.innerHTML, /javascript:bad/);
  assert.doesNotMatch(container.innerHTML, /src="null"/);
});

test('only the local current-round endpoint and v14 shell cache are used', async () => {
  const source = await readFile(new URL('../today-live.js', import.meta.url), 'utf8');
  const sw = await readFile(new URL('../sw.js', import.meta.url), 'utf8');
  assert.ok(source.includes("fetch('/api/v1/rounds/current'"));
  assert.ok(!source.includes("fetch('/api/v1/today'"));
  assert.ok(sw.includes('pbk-shell-v15'));
});
