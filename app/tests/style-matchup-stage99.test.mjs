import test from 'node:test';
import assert from 'node:assert/strict';

import {renderMatchCard} from '../match-card.js';
import {renderTodayLive} from '../today-live.js';


function payload(){
  return {
    fixture:{
      fixture_id:'999',
      provider_league_id:'39',
      league_name:'Premier League',
      season:'2026',
      kickoff_utc:'2026-09-20T16:00:00Z',
      status:'scheduled',
      home:{name:'Alpha'},
      away:{name:'Beta'},
    },
    coverage:{
      status:'PARTIAL',
      sections:{},
      limitations:[],
    },
    style_matchup:{
      version:'PBK_STAGE96_STYLE_MATCHUP_PASSPORT_V1',
      available:true,
      no_lookahead:true,
      style_validation:{
        status:'VALIDATION_EVIDENCE_AVAILABLE',
        ready_dimensions:[
          'ATTACK_VOLUME',
          'POSSESSION_CONTROL',
        ],
        validation_evidence_dimensions:[
          'ATTACK_VOLUME',
        ],
        validated_style_claim_allowed:false,
      },
      matchup_validation:{
        status:'DATA_BLOCKED',
        components_with_required_evidence:0,
        total_components:7,
        matchup_grade_authorized:false,
        overall_edge_authorized:false,
        validated_matchup_claim_allowed:false,
      },
      research_only:true,
      provider_polling:false,
      creates_signal:false,
      probability_mutation:false,
      eligibility_mutation:false,
      stake_changes:false,
    },
  };
}


test('Stage99 renders Style/Matchup without inventing grade or edge',()=>{
  const html=renderMatchCard(payload());

  assert.match(html,/Team Style \/ Matchup/);
  assert.match(html,/ATTACK_VOLUME/);
  assert.match(html,/VALIDATION_EVIDENCE_AVAILABLE/);
  assert.match(html,/DATA_BLOCKED/);
  assert.match(html,/0\/7/);

  assert.match(html,/Matchup Grade, общий edge и победитель не вычисляются/);
  assert.doesNotMatch(html,/Matchup Grade [0-9]/);
  assert.doesNotMatch(html,/overall edge [+-]?[0-9]/i);
});


test('Stage99 keeps DATA_WAITING explicit',()=>{
  const p=payload();

  p.style_matchup={
    available:false,
    no_lookahead:true,
    style_validation:{
      status:'DATA_WAITING',
      ready_dimensions:[],
      validation_evidence_dimensions:[],
    },
    matchup_validation:{
      status:'DATA_WAITING',
      components_with_required_evidence:0,
      total_components:0,
    },
  };

  const html=renderMatchCard(p);

  assert.match(html,/Данные накапливаются/);
  assert.match(html,/DATA_WAITING/);
});


test('LIVE and tour expose only compact backend research status',()=>{
  const container={innerHTML:''};

  const match={
    fixture_id:'100',
    status:'live',
    kickoff_utc:'2026-09-20T16:00:00Z',
    home_team:'Alpha',
    away_team:'Beta',
    style_matchup:{
      style_status:'VALIDATION_EVIDENCE_AVAILABLE',
      matchup_status:'DATA_BLOCKED',
      research_only:true,
      probability_mutation:false,
    },
  };

  renderTodayLive(container,{
    leagues:[{
      provider_league_id:'39',
      league_name:'Premier League',
      status:'available',
      matches:[match],
    }],
  },'live');

  assert.match(container.innerHTML,/STYLE · evidence/);
  assert.match(container.innerHTML,/MATCHUP · blocked/);

  assert.doesNotMatch(container.innerHTML,/вероятность/i);
  assert.doesNotMatch(container.innerHTML,/value/i);
});


test('research text is escaped',()=>{
  const p=payload();

  p.style_matchup.style_validation.status='<script>x</script>';

  const html=renderMatchCard(p);

  assert.doesNotMatch(html,/<script>x<\/script>/);
  assert.match(html,/&lt;script&gt;x&lt;\/script&gt;/);
});
