import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../markets.js',import.meta.url),'utf8');
const {marketCard,leagueOptions}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
test('all 16 fixture leagues survive with no market rows and duplicates',()=>{
  const catalog=readFileSync(new URL('../../ops/stage71_league_catalog.csv',import.meta.url),'utf8').trim().split(/\r?\n/).slice(1).map(r=>r.split(',')[1]);
  const cards=catalog.map(league=>({dataset:{league}}));
  assert.equal(leagueOptions([...cards,cards[0]]).length,16);
  assert.match(marketCard({league:catalog[15],markets:[]}),/Нет данных/);
});
test('snapshot timestamp, identity and missing markets are escaped and explicitly research only',()=>{
  const html=marketCard({fixture_id:'1',league:'<img>',home_team:'<script>',markets:[{market:'DNB',text:'Ф(0) — нет данных'},{market:'MATCH_WINNER',text:'1X2 @ Bet365',captured_at_utc:'2026-09-12T10:00:00Z'}]});
  assert.doesNotMatch(html,/<img>|<script>/);
  assert.match(html,/data-league="&lt;img&gt;"/);
  assert.match(html,/data-market="DNB"/);
  assert.match(html,/Снимок: 2026-09-12/);
  assert.match(html,/не сигнал и не рекомендация/);
  assert.match(html,/актуальность не гарантирована/);
});
