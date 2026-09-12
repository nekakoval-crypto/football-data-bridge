import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const source = readFileSync(new URL('../challengers.js', import.meta.url), 'utf8');
const { numeric, filterRows, renderCard, renderObservation, initChallengers } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const board = JSON.parse(readFileSync(new URL('../../ops/stage71_challenger_board.json', import.meta.url), 'utf8'));

test('real board retains all 16 leagues and both families without mutation', () => {
  const before = JSON.stringify(board);
  assert.equal(board.rows.length, 32);
  assert.equal(new Set(board.rows.map(r => r.league)).size, 16);
  for (const family of ['R1', 'R2']) assert.equal(filterRows(board.rows, {family}).length, 16);
  const selected = filterRows(board.rows, {family: 'R1', group: 'EXTENDED', status: 'MONITORING'});
  assert.ok(selected.length);
  assert.ok(selected.every(r => r.family === 'R1' && r.group === 'EXTENDED' && r.status === 'MONITORING'));
  board.rows.forEach(renderCard);
  assert.equal(JSON.stringify(board), before);
});
test('missing values differ from zero and invalid numbers never become ROI', () => {
  for (const value of [null, undefined, '', ' ', 'NaN', Infinity, false]) assert.equal(numeric(value), null);
  assert.equal(numeric('0'), 0);
  assert.match(renderCard({prospective_roi_pct: '0'}), /0\.00%/);
  assert.doesNotMatch(renderCard({}), /0\.00%/);
});
test('small samples, active baseline, half semantics and untrusted text', () => {
  const html = renderCard({status: 'ACTIVE', league: '<img src=x onerror=alert(1)>', blocking_reason: '<script>x</script>', prospective_settled: '1', prospective_roi_pct: '-100'});
  assert.match(html, /Слишком мало данных/);
  assert.match(html, /-100\.00%/);
  assert.match(html, /canonical forward/);
  assert.match(html, /не таймы матча/);
  assert.doesNotMatch(html, /<img|<script>/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(renderCard({prospective_settled: 10}), /Слишком мало данных/);
});
test('gates use server remaining counts and clamp only visual bars', () => {
  const html = renderCard({review_remaining_settled: '59', discovery_remaining_settled: '119', prospective_settled: 999, status: 'MONITORING'});
  assert.match(html, /max="60" value="1"/);
  assert.match(html, /max="120" value="1"/);
  assert.match(html, /MONITORING/);
  assert.match(renderCard({review_remaining_settled: -1}), /max="60" value="60"/);
  assert.doesNotMatch(renderCard({}), /<progress/);
});
test('controller refresh preserves filters; missing/error states clear old results', () => {
  const elements = new Map();
  const root = {querySelector(id) { if (!elements.has(id)) elements.set(id, {value:'', innerHTML:'', textContent:'', events:{}, addEventListener(k, fn) {this.events[k] = fn;}}); return elements.get(id); }};
  const ui = initChallengers(root);
  ui.update({league_challenger:board});
  assert.match(root.querySelector('#challenger-summary').textContent, /16 \/ 16.*32 \/ 32/);
  root.querySelector('#challenger-family').value = 'R2';
  ui.update({league_challenger:board});
  assert.match(root.querySelector('#challenger-summary').textContent, /показано 16/);
  ui.unavailable();
  assert.doesNotMatch(root.querySelector('#challenger-list').innerHTML, /challenger-card/);
  ui.update({});
  assert.match(root.querySelector('#challenger-list').innerHTML, /не нулевые результаты/);
  ui.update({league_challenger:{rows:[null]}});
  assert.match(root.querySelector('#challenger-summary').textContent, /0 \/ 16/);
});
test('shell and service worker include the new assets', () => {
  const shell = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
  assert.match(shell, /data-view="challengers"/);
  assert.match(shell, /id="view-challengers"/);
  for (const asset of ['/challengers.js','/challengers.css']) assert.ok(sw.includes(asset));
});

test('observation fields escape text, preserve zero and hide pending settlement', () => {
  const row = {home_team:'<img src=x>', away_team:'Away', kickoff_utc:'2026-09-12T15:00:00+03:00', selection:'П2', bet365_price:1.48, marathonbet_price:1.50, status:'SETTLED', final_home_goals:0, final_away_goals:0, result:'PUSH', user_profit_u:0};
  const html = renderObservation(row);
  assert.match(html, /2026-09-12 12:00 UTC/);
  assert.match(html, /0 : 0/);
  assert.match(html, /0\.000 u/);
  assert.match(html, /PUSH/);
  assert.match(html, /1\.48/);
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/);
  assert.doesNotMatch(renderObservation({...row, status:'PENDING'}), /0 : 0|PUSH|0\.000 u/);
  assert.doesNotMatch(renderObservation({kickoff_utc:'bad', user_profit_u:'', bet365_price:false}), /NaN|Invalid|0\.000/);
  for (const result of ['W', 'L']) assert.match(renderObservation({...row, result, user_profit_u:0.5}), /\+0\.500 u/);
});

function observationHarness(request) {
  const elements = new Map();
  const root = {querySelector(id) { if (!elements.has(id)) elements.set(id, {value:'', innerHTML:'', textContent:'', events:{}, addEventListener(k, fn) {this.events[k] = fn;}}); return elements.get(id); }};
  const ui = initChallengers(root, request);
  const content = {innerHTML:''};
  const details = {dataset:{family:'R1', league:'League & One'}, open:true, matches:()=>true, querySelector:()=>content};
  const list = root.querySelector('#challenger-list');
  const open = () => list.events.toggle({target:details});
  const click = action => list.events.click({target:{closest:()=>({dataset:{observationAction:action}, closest:()=>details})}});
  return {ui, content, open, click};
}
const flush = () => new Promise(resolve => setImmediate(resolve));
const observationsPage = (count, offset, limit) => ({available:true, source:'research-only', count, items:Array.from({length:Math.min(limit, count-offset)}, (_, i)=>({home_team:`Team-${offset+i}`, status:'PENDING'}))});

test('lazy first five, show all across pages, collapse, and reopen without a request', async () => {
  const requests = [];
  const h = observationHarness(async path => {
    requests.push(path);
    const q = new URL(path, 'https://local').searchParams;
    assert.equal(q.get('league'), 'League & One');
    return observationsPage(502, Number(q.get('offset')), Number(q.get('limit')));
  });
  assert.equal(requests.length, 0);
  h.open(); await flush();
  assert.equal((h.content.innerHTML.match(/class="challenger-observation"/g)||[]).length, 5);
  assert.match(h.content.innerHTML, /Показать все \(502\)/);
  h.open(); assert.equal(requests.length, 1);
  h.click('all'); await flush();
  assert.equal(requests.length, 3);
  assert.match(requests[2], /offset=500/);
  assert.equal((h.content.innerHTML.match(/class="challenger-observation"/g)||[]).length, 502);
  h.click('collapse');
  assert.equal((h.content.innerHTML.match(/class="challenger-observation"/g)||[]).length, 5);
  assert.equal(requests.length, 3);
});

test('empty and unavailable observations differ; retry works', async () => {
  let fail = true;
  const h = observationHarness(async () => fail ? {available:false, items:[], count:0} : observationsPage(0,0,5));
  h.open(); await flush();
  assert.match(h.content.innerHTML, /Не удалось/);
  fail = false; h.click('retry'); await flush();
  assert.match(h.content.innerHTML, /Наблюдений пока нет/);
  assert.doesNotMatch(h.content.innerHTML, /Показать все/);
});

test('late response cannot restore observations after offline or refresh', async () => {
  let resolve;
  const h = observationHarness(() => new Promise(r => {resolve = r;}));
  h.open(); h.ui.unavailable(); resolve(observationsPage(1,0,5)); await flush();
  assert.doesNotMatch(h.content.innerHTML, /Team-0/);
});
