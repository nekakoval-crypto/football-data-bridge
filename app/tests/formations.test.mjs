import test from 'node:test';
import assert from 'node:assert/strict';
import {positions,renderPitch,selectedTeam} from '../formations.js';
import {renderMatchCard} from '../match-card.js';
const xi=()=>Array.from({length:11},(_,i)=>({id:i+1,name:`Name Surname${i}`,number:i+1,pos:i===0?'G':'M'}));
test('standard formations place all players uniquely inside a half',()=>{
  for(const formation of ['4-4-2','4-3-3','4-2-3-1','3-5-2','3-4-3','5-3-2','3-4-2-1']){
    const players=positions({formation,starting_xi:xi()});
    assert.equal(players.length,11);
    assert.equal(new Set(players.map(p=>`${p.x}:${p.y}`)).size,11);
    assert.ok(players.every(p=>p.x>0&&p.x<100&&p.y>0&&p.y<100));
  }
});
test('valid provider grid overrides formation and away mirrors both axes',()=>{
  const players=xi(),grid=['1:1','2:1','2:2','2:3','2:4','3:1','3:2','3:3','4:1','4:2','4:3'];
  players.forEach((p,i)=>p.grid=grid[i]);
  const team={formation:'5-3-2',starting_xi:players};
  assert.equal(positions(team)[1].basis,'grid');
  assert.equal(positions(team)[1].x,20);
  const html=renderPitch(team,team);
  assert.match(html,/home" style="left:20%;top:18%/);
  assert.match(html,/away" style="left:80%;top:82%/);
  assert.equal((html.match(/formation-player /g)||[]).length,22);
  assert.match(html,/<b>2<\/b><span>Surname1<\/span>/);
});
test('explicit positions win, invalid and colliding grids fall back safely',()=>{
  const players=xi().map((p,i)=>({...p,position:{x:i*9,y:i*9},grid:'2:1'}));
  assert.equal(positions({starting_xi:players})[1].basis,'positions');
  players[0].position.x='evil';
  assert.equal(positions({formation:'4-3-3',starting_xi:players})[0].basis,'template');
  assert.deepEqual(positions({formation:'100-2',starting_xi:players}),[]);
  assert.deepEqual(positions({formation:'4-3-3',starting_xi:players.slice(0,3)}),[]);
});
test('official XI overrides expected data including formation and coach',()=>{
  const team={status:'EXPECTED',formation:'4-4-2',starting_xi:xi(),official:{formation:'3-5-2',coach:'Official',xi:xi().map(p=>({...p,number:99}))}};
  assert.equal(selectedTeam(team).status,'CONFIRMED');
  assert.equal(selectedTeam(team).formation,'3-5-2');
  assert.match(renderPitch(team,{}),/<b>99<\/b>/);
});
test('single pitch is integrated, escaped, timestamped and handles missing opponent',()=>{
  const players=xi();players[0].lastname='<img onerror=1>';
  const html=renderMatchCard({lineup_context:{available:true,home:{formation:'4-3-3',starting_xi:players,updated_at_utc:'2026-09-14T12:00:00Z'},away:{}}});
  assert.equal((html.match(/class="formation-pitch"/g)||[]).length,1);
  assert.match(html,/2026-09-14T12:00:00Z/);
  assert.match(html,/Нет данных по расстановке/);
  assert.doesNotMatch(html,/<img onerror/);
  assert.match(html,/&lt;img onerror=1&gt;/);
  assert.match(renderMatchCard({}),/Нет данных по составу/);
});
