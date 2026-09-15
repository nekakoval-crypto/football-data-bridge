import test from 'node:test';
import assert from 'node:assert/strict';
import {initialScenario,analyzeScenario,renderManualConfigurator} from '../manual-lineup.js';
import {renderPitch} from '../formations.js';
import {renderMatchCard} from '../match-card.js';

const xi=(prefix)=>Array.from({length:11},(_,i)=>({id:`${prefix}${i+1}`,name:`${prefix} Surname${i+1}`,number:i+1,pos:i===0?'G':i<5?'D':i<9?'M':'F'}));
const payload=()=>{
  const home=xi('H'),away=xi('A');
  const homeGrades=Object.fromEntries(home.map((p,i)=>[p.id,{player_id:p.id,player_name:p.name,current_grade:7+i/20,grade_basis:'FORM_5',confidence:'MEDIUM'}]));
  const awayGrades=Object.fromEntries(away.map((p,i)=>[p.id,{player_id:p.id,player_name:p.name,current_grade:6.8+i/20,grade_basis:'FORM_5',confidence:'MEDIUM'}]));
  return {fixture_id:'999',lineup_context:{available:true,home:{team_id:'10',team_name:'Home',status:'EXPECTED',formation:'4-3-3',starting_xi:home},away:{team_id:'20',team_name:'Away',status:'CONFIRMED',formation:'4-2-3-1',starting_xi:away}},player_grade:{available:true,home:{player_pool:[...home,{id:'H12',name:'Home Reserve',number:20,pos:'M'}],grades_by_player:{...homeGrades,H12:{player_id:'H12',current_grade:5.5,confidence:'LOW'}}},away:{player_pool:away,grades_by_player:awayGrades}}};
};

test('manual scenario starts from current expected/official lineups',()=>{
  const draft=initialScenario(payload());
  assert.equal(draft.fixture_id,'999');
  assert.equal(draft.home.xi.length,11);
  assert.equal(draft.away.xi.length,11);
  assert.equal(draft.home.formation,'4-3-3');
  assert.ok(draft.home.pool.some(p=>p.id==='H12'));
});

test('manual replacement reports XI quality drop without canonical mutations',()=>{
  const p=payload(),draft=initialScenario(p);
  draft.home.xi[draft.home.xi.length-1]=draft.home.pool.find(x=>x.id==='H12');
  draft.home.formation='4-2-3-1';
  const result=analyzeScenario(draft,p);
  assert.equal(result.what_if_only,true);
  assert.equal(result.probability_mutation,false);
  assert.equal(result.eligibility_mutation,false);
  assert.equal(result.stake_changes,false);
  assert.equal(result.sides.home.overlap,10);
  assert.equal(result.sides.home.added[0].id,'H12');
  assert.ok(result.sides.home.quality_delta<0);
  assert.equal(result.sides.home.formation_changed,true);
});

test('configurator is clearly labelled WHAT-IF and exposes both teams',()=>{
  const html=renderManualConfigurator(payload());
  assert.match(html,/Ручной сценарий/);
  assert.match(html,/data-manual-side="home"/);
  assert.match(html,/data-manual-side="away"/);
  assert.match(html,/Запустить анализ/);
  assert.match(html,/Сохранить сценарий/);
  assert.match(html,/игрок вручную/);
});

test('mirrored pitch shows PBK grade below surname when grade exists',()=>{
  const p=payload();
  const html=renderPitch(p.lineup_context.home,p.lineup_context.away,p.player_grade);
  assert.match(html,/formation-grade/);
  assert.match(html,/PBK 7\.0/);
  assert.equal((html.match(/formation-player /g)||[]).length,22);
});

test('Match Card contains Player Grade and manual configurator as research blocks',()=>{
  const html=renderMatchCard(payload());
  assert.match(html,/PBK Player Grade \/ XI Quality/);
  assert.match(html,/Ручной конфигуратор состава/);
  assert.match(html,/MANUAL \/ INSIDER · WHAT-IF/);
  assert.match(html,/Research|RESEARCH/);
});
