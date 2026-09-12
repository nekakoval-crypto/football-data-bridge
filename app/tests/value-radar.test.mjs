import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source = await readFile(new URL('../value-radar.js',import.meta.url),'utf8');
const {renderRadar,loadRadar,LABELS} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const row={api_fixture_id:'123',primary_rule:'R2',source_rules:['R1','R2'],selection:'Away',radar_level:'STRONG_VALUE',radar_tags:['LONGSHOT_STRONG'],home_team:'<Home>',away_team:'Away',p_pbk_pct:52.5,p_market_pct:49.5,edge_pp:3,executable_odds:2,ev_pct:5};
test('one card per fixture/selection with Russian labels and escaped content',()=>{
  const html=renderRadar({status:'OK',items:[row,row,{...row,api_fixture_id:'9',primary_rule:'Stage61'}]});
  assert.equal((html.match(/<article/g)||[]).length,1);
  assert.match(html,/data-fixture="123"/);assert.match(html,/КЭФ ≥2/);
  assert.match(html,/&lt;Home&gt;/);assert.match(html,/не новый R-сигнал/);
  for(const [level,label] of Object.entries(LABELS)) assert.ok(renderRadar({status:'OK',items:[{...row,radar_level:level}]}).includes(label));
});
test('missing price/EV remains unknown and no-data differs from zero items',()=>{
  const html=renderRadar({status:'OK',items:[{...row,radar_level:'MARKET_DISAGREEMENT',executable_odds:null,ev_pct:null}]});
  assert.match(html,/<dd>—<\/dd>/);assert.doesNotMatch(html,/КЭФ ≥2/);
  assert.match(renderRadar({status:'NO_DATA',items:[]}),/не подтверждена/);
  assert.match(renderRadar({status:'OK',items:[]}),/нет подходящих/);
});
test('fetch uses only local API and failures clear stale cards',async()=>{
  const list={innerHTML:'stale'};const root={querySelector:()=>list};
  await loadRadar(root,async(path,options)=>{
    assert.equal(path,'/api/v1/value-radar?limit=100');assert.equal(options.cache,'no-store');
    return {ok:true,json:async()=>({status:'OK',items:[row]})};
  });
  assert.match(list.innerHTML,/СИЛЬНОЕ/);
  await loadRadar(root,async()=>{throw Error('offline')});
  assert.doesNotMatch(list.innerHTML,/СИЛЬНОЕ/);assert.match(list.innerHTML,/не подтверждена/);
});
