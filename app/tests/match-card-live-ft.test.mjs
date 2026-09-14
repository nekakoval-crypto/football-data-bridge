import test from 'node:test';
import assert from 'node:assert/strict';
import {renderMatchCard} from '../match-card.js';

function payload(status='live'){
  return {
    fixture:{fixture_id:'999',league_name:'Premier League',round:'Round 5',kickoff_utc:'2026-09-14T16:30:00Z',status,source_status:status==='finished'?'FT':'2H',elapsed:status==='finished'?90:67,score:{home:2,away:1},home:{name:'Alpha',logo_url:'https://img/a.png',red_cards:1},away:{name:'Beta',logo_url:'https://img/b.png',red_cards:2},observed_at_utc:'2026-09-14T18:25:00Z',live_observed_at_utc:'2026-09-14T18:25:00Z',live_freshness_status:'fresh'},
    motivation:{available:true,no_lookahead:true,standings_context:{snapshot_observed_at_utc:'2026-09-14T15:30:00Z',requested_as_of_utc:'2026-09-14T16:30:00Z'},home:{primary_context:'TITLE',pressure:'MEDIUM'},away:{primary_context:'SURVIVAL',pressure:'HIGH'}},
    prediction:{available:true,items:[{rule:'R1',selection:'Away',market_family:'MATCH_RESULT_1X2',p_pbk:0.67,p_market_no_vig:0.60,model_version:'m1',status:'FROZEN_PREMATCH'}]},
    markets:{available:true,pre_match_frozen:true,creates_signal:false,stake_changes:false,model_probability_created:false,user_line_policy:'NO_QUARTER_ASIAN_HANDICAPS',available_family_count:1,total_family_count:8,coverage_status:'PARTIAL',families:[{id:'MATCH_RESULT_1X2',label_ru:'Исход матча — П1 / Х / П2',available:true,scope:'CANONICAL_INPUT_OBSERVATION',research_only:false,observed_at_utc:'2026-09-14T15:00:00Z',source:'stage53_latest_screen',pre_match_frozen:true,items:[{selection:'П1',bet365_odds:'2.10',market_no_vig:0.45},{selection:'Х',bet365_odds:'3.40',market_no_vig:0.28},{selection:'П2',bet365_odds:'3.60',market_no_vig:0.27}],limitations:[]}]},
    odds:{available:false,items:[]},context:{available:false},value_radar:{available:false,research_only:true,creates_signal:false,stake_changes:false,items:[]},canonical:{available:false,items:[]},coverage:{status:'PARTIAL',sections:{motivation:true,context:false,prediction:true,markets:true,odds:false,value_radar:false,canonical:false},limitations:['CONTEXT_UNAVAILABLE','ODDS_UNAVAILABLE']},read_only:true,provider_polling:false,eligibility_mutation:false,model_mutation:false,
  };
}

test('LIVE card renders dynamic score elapsed red cards and frozen prematch market',()=>{
  const html=renderMatchCard(payload('live'));
  assert.match(html,/2:1/);
  assert.match(html,/LIVE/);
  assert.match(html,/67′/);
  assert.match(html,/🟥/);
  assert.match(html,/🟥 2/);
  assert.match(html,/2\.10/);
  assert.match(html,/pre-match frozen/);
  assert.match(html,/Вероятность ПБК/);
});

test('FT card renders provider-confirmed final status and final score',()=>{
  const html=renderMatchCard(payload('finished'));
  assert.match(html,/2:1/);
  assert.match(html,/FT/);
  assert.doesNotMatch(html,/67′/);
  assert.match(html,/🟥 2/);
});

test('stale LIVE freshness remains visible rather than presented as fresh',()=>{
  const p=payload('live');
  p.fixture.live_freshness_status='stale';
  const html=renderMatchCard(p);
  assert.match(html,/Freshness: stale/);
  assert.doesNotMatch(html,/Freshness: fresh/);
});

test('elapsed alone never changes a LIVE card to FT in the renderer',()=>{
  const p=payload('live');
  p.fixture.elapsed=120;
  const html=renderMatchCard(p);
  assert.match(html,/LIVE/);
  assert.match(html,/120′/);
  assert.doesNotMatch(html,/class="match-card-v2-status">FT/);
});

test('LIVE and FT render the same frozen PBK probability and prematch market observations',()=>{
  const live=renderMatchCard(payload('live'));
  const ft=renderMatchCard(payload('finished'));
  for(const token of ['67%','60%','2.10','3.40','3.60','Снимок до матча · без future leakage']){
    assert.match(live,new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
    assert.match(ft,new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
  }
});

test('Match Card LIVE/FT markup never contains a direct provider endpoint',()=>{
  assert.doesNotMatch(renderMatchCard(payload('live')),/api-football|api-sports/i);
  assert.doesNotMatch(renderMatchCard(payload('finished')),/api-football|api-sports/i);
});
