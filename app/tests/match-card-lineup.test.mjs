import test from 'node:test';
import assert from 'node:assert/strict';
import {renderMatchCard} from '../match-card.js';

const basePayload=()=>({
  fixture:{fixture_id:'999',league_name:'Premier League',round:'Round 5',kickoff_utc:'2026-09-20T16:00:00Z',status:'scheduled',home:{name:'Alpha'},away:{name:'Beta'}},
  coverage:{status:'PARTIAL',sections:{},limitations:[]},
  lineup_context:{
    available:true,no_lookahead:true,rotation_projection:'raw_rotation_snapshots',
    home:{status:'CONFIRMED',formation:'3-4-2-1',coach:'Coach A',expected_confidence:'LOW',expected_basis_fixtures:2,starting_xi:[{name:'Home One'},{name:'Home Two'}]},
    away:{status:'EXPECTED',formation:'4-3-3',coach:'Coach B',expected_confidence:'MEDIUM',expected_basis_fixtures:3,starting_xi:[{name:'Away One'}]},
  },
  lineup_surprise:{
    available:true,
    home:{available:true,overlap_starters:9,unexpected_starters_count:2,unexpected_starters:[{name:'New One'},{name:'New Two'}],missing_expected:[{name:'Old One'},{name:'Old Two'}],concentration:{available:true,stable_core_players:8,average_start_share_pct:78.2}},
    away:{available:true,overlap_starters:11,unexpected_starters_count:0,unexpected_starters:[],missing_expected:[],concentration:{available:true,stable_core_players:10,average_start_share_pct:91.1}},
  }
});

test('renders formation coach expected XI and factual M5 delta',()=>{
  const html=renderMatchCard(basePayload());
  assert.match(html,/Схема \/ тренер \/ состав/);
  assert.match(html,/Официальный XI/);
  assert.match(html,/Ожидаемый XI/);
  assert.match(html,/3-4-2-1/);
  assert.match(html,/Coach A/);
  assert.match(html,/Home One/);
  assert.match(html,/M5 · отклонение состава/);
  assert.match(html,/Совпадение 9\/11/);
  assert.match(html,/Неожиданных в старте: 2/);
  assert.match(html,/New One/);
  assert.match(html,/не создаёт сигнал/);
});

test('escapes player and coach text in lineup extension',()=>{
  const payload=basePayload();
  payload.lineup_context.home.coach='<img src=x onerror=1>';
  payload.lineup_context.home.starting_xi=[{name:'<script>alert(1)</script>'}];
  const html=renderMatchCard(payload);
  assert.doesNotMatch(html,/<script>alert\(1\)<\/script>/);
  assert.doesNotMatch(html,/<img src=x onerror=1>/);
  assert.match(html,/&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.match(html,/&lt;img src=x onerror=1&gt;/);
});

test('shows honest pending state before official XI',()=>{
  const payload=basePayload();
  payload.lineup_surprise={available:false};
  const html=renderMatchCard(payload);
  assert.match(html,/появится после подтверждения обоих стартовых XI/);
});
