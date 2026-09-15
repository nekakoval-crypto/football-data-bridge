import {renderPitch,selectedTeam} from './formations.js';

const STORAGE_KEY='pbkManualLineupScenariosV1';
const STYLE_ID='pbk-manual-lineup-style-v1';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const FORMATIONS=['4-3-3','4-2-3-1','4-4-2','3-5-2','3-4-3','3-4-2-1','5-3-2','5-4-1'];

const pid=p=>String(p?.id??p?.player_id??'');
const name=p=>p?.lastname||p?.last_name||p?.name||p?.player_name||`#${pid(p)}`;

function ensureStyle(){
  if(typeof document==='undefined'||document.getElementById(STYLE_ID))return;
  const style=document.createElement('style');style.id=STYLE_ID;style.textContent=`
  .formation-grade{display:block;color:#d8f7b7;font-size:9px;font-weight:800;text-shadow:0 1px 3px #000}
  .manual-lineup-config{display:grid;gap:12px}.manual-lineup-top,.manual-lineup-two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.manual-lineup-top label,.manual-lineup-side-head label{display:grid;gap:5px;color:var(--muted);font-size:10px}.manual-lineup-top input,.manual-lineup-side select,.manual-lineup-slot input,.manual-lineup-slot select{width:100%;box-sizing:border-box;background:#0b1117;border:1px solid #334150;border-radius:9px;color:var(--text);padding:8px;font:inherit}.manual-lineup-warning{border:1px solid #755322;background:rgba(255,173,69,.06);border-radius:10px;padding:9px;color:#ffd69c;font-size:11px}.manual-lineup-side{background:#0d131a;border:1px solid #263544;border-radius:12px;padding:10px;min-width:0}.manual-lineup-side-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}.manual-lineup-slots{display:grid;gap:5px}.manual-lineup-slot{display:grid;grid-template-columns:24px minmax(0,1fr);gap:6px;align-items:center}.manual-lineup-slot>span{color:var(--muted);font-size:10px;text-align:center}.manual-lineup-slot input{grid-column:2}.manual-lineup-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.manual-lineup-actions button{border:1px solid #3b6081;background:#16324a;color:#e5f3ff;border-radius:10px;padding:9px 12px;font-weight:750;cursor:pointer}.manual-lineup-actions button+button{background:#17221c;border-color:#38614b}.manual-lineup-actions span{color:var(--muted);font-size:10px}.manual-lineup-analysis{display:grid;gap:8px;margin-top:8px}.manual-lineup-result-side{display:grid;gap:4px;background:#0d131a;border:1px solid #263544;border-radius:10px;padding:10px}.manual-lineup-result-side span{font-size:11px;color:var(--muted)}.manual-lineup-result-side b{color:var(--text)}
  @media(max-width:760px){.manual-lineup-top,.manual-lineup-two{grid-template-columns:1fr}.manual-lineup-side-head{align-items:flex-start}.manual-lineup-slot select,.manual-lineup-slot input{min-height:40px}}
  `;document.head.appendChild(style);
}

function clonePlayer(p={}){return {id:pid(p),name:p.name||p.player_name||'',lastname:p.lastname||p.last_name||'',number:p.number??'',pos:p.pos||p.position||'',grid:p.grid||''}}
function uniquePlayers(...groups){const out=new Map();for(const group of groups)for(const p of group||[]){const id=pid(p);if(id)out.set(id,{...(out.get(id)||{}),...clonePlayer(p)})}return [...out.values()]}
function gradeMap(pg={},side){const team=pg?.[side]||{};return team.grades_by_player&&typeof team.grades_by_player==='object'?team.grades_by_player:Object.fromEntries((team.grades||[]).filter(x=>x?.player_id).map(x=>[String(x.player_id),x]))}

export function initialScenario(payload={}){
  const lineup=payload.lineup_context||{},pg=payload.player_grade||{};
  const side=key=>{const base=selectedTeam(lineup[key]||{}),xi=(base.starting_xi||[]).map(x=>clonePlayer(x?.player||x));const pool=uniquePlayers(pg[key]?.player_pool,xi);return {formation:base.formation||'4-3-3',xi,pool,baselineXi:xi.map(clonePlayer),baselineFormation:base.formation||null,baselineStatus:base.status||'UNKNOWN'}};
  return {fixture_id:String(payload.fixture_id||payload.fixture?.fixture_id||''),name:'Инсайд состава',note:'',home:side('home'),away:side('away')};
}

function readSaved(){try{const raw=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');return Array.isArray(raw)?raw:[]}catch{return []}}
function writeSaved(rows){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(rows.slice(-100)))}catch{}}
export function savedScenarios(fixtureId){return readSaved().filter(x=>String(x.fixture_id)===String(fixtureId))}

function quality(xi,grades){const vals=xi.map(p=>grades[pid(p)]?.current_grade).filter(v=>v!==null&&v!==undefined&&v!=='').map(Number).filter(Number.isFinite);return {value:vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null,covered:vals.length,total:xi.length}}
function lineOf(p){const pos=String(p?.pos||'').toUpperCase();if(pos.startsWith('G'))return'GK';if(pos.startsWith('D'))return'DEF';if(pos.startsWith('F')||['ST','CF','LW','RW'].includes(pos))return'ATT';return'MID'}
function lineQuality(xi,grades){const out={};for(const p of xi){const value=Number(grades[pid(p)]?.current_grade);if(!Number.isFinite(value))continue;(out[lineOf(p)]??=[]).push(value)}return Object.fromEntries(Object.entries(out).map(([k,v])=>[k,v.reduce((a,b)=>a+b,0)/v.length]))}

export function analyzeScenario(draft,payload={}){
  const pg=payload.player_grade||{};const result={fixture_id:draft.fixture_id,what_if_only:true,research_only:true,probability_mutation:false,eligibility_mutation:false,stake_changes:false,sides:{}};
  for(const side of ['home','away']){
    const grades=gradeMap(pg,side),s=draft[side],base=quality(s.baselineXi,grades),manual=quality(s.xi,grades),bLines=lineQuality(s.baselineXi,grades),mLines=lineQuality(s.xi,grades);
    const before=new Set(s.baselineXi.map(pid)),after=new Set(s.xi.map(pid));
    result.sides[side]={formation:s.formation,baseline_formation:s.baselineFormation,formation_changed:Boolean(s.baselineFormation&&s.formation!==s.baselineFormation),added:s.xi.filter(p=>!before.has(pid(p))),removed:s.baselineXi.filter(p=>!after.has(pid(p))),overlap:[...after].filter(x=>before.has(x)).length,baseline_quality:base,manual_quality:manual,quality_delta:base.value!==null&&manual.value!==null?manual.value-base.value:null,line_delta:Object.fromEntries([...new Set([...Object.keys(bLines),...Object.keys(mLines)])].map(k=>[k,bLines[k]!==undefined&&mLines[k]!==undefined?mLines[k]-bLines[k]:null]))};
  }
  return result;
}

function playerOption(p,current){return `<option value="${esc(pid(p))}" ${pid(p)===current?'selected':''}>${esc(p.number?`${p.number} · `:'')}${esc(name(p))}${p.pos?` · ${esc(p.pos)}`:''}</option>`}
function slotEditor(side,index,player,pool){return `<div class="manual-lineup-slot"><span>${index+1}</span><select data-manual-side="${side}" data-manual-slot="${index}"><option value="">— выбрать —</option>${pool.map(p=>playerOption(p,pid(player))).join('')}<option value="__custom__">+ игрок вручную</option></select><input type="text" data-manual-custom="${side}:${index}" value="" placeholder="Фамилия / неизвестный игрок" hidden></div>`}
function formationSelect(side,value){return `<select data-manual-formation="${side}">${[...new Set([value,...FORMATIONS].filter(Boolean))].map(x=>`<option value="${esc(x)}" ${x===value?'selected':''}>${esc(x)}</option>`).join('')}</select>`}
function sideEditor(side,label,s){return `<div class="manual-lineup-side"><div class="manual-lineup-side-head"><strong>${esc(label)}</strong><label>Схема ${formationSelect(side,s.formation)}</label></div><div class="manual-lineup-slots">${Array.from({length:11},(_,i)=>slotEditor(side,i,s.xi[i]||{},s.pool)).join('')}</div></div>`}
function fmt(v){return v===null||v===undefined||!Number.isFinite(Number(v))?'—':Number(v).toFixed(2)}
function resultHtml(result){const one=(label,s)=>`<div class="manual-lineup-result-side"><strong>${label}</strong><span>XI Quality: ${fmt(s.baseline_quality.value)} → ${fmt(s.manual_quality.value)} <b>Δ ${fmt(s.quality_delta)}</b></span><span>Покрытие grade: ${s.manual_quality.covered}/${s.manual_quality.total}</span><span>Совпадение: ${s.overlap}/11 · схема ${esc(s.baseline_formation||'—')} → ${esc(s.formation||'—')}</span><span>Линии: ${Object.entries(s.line_delta).map(([k,v])=>`${k} ${fmt(v)}`).join(' · ')||'—'}</span><span>Вышли: ${s.added.map(name).join(', ')||'—'}</span><span>Убраны: ${s.removed.map(name).join(', ')||'—'}</span></div>`;return `<div class="manual-lineup-analysis"><div class="match-card-v2-research-label">MANUAL SCENARIO / WHAT-IF</div>${one('Хозяева',result.sides.home)}${one('Гости',result.sides.away)}<div class="match-card-v2-note">Это sandbox-анализ состава. Он не меняет probability, R1/R2/R3, Value eligibility, ставку или Forward-журнал.</div></div>`}

export function renderManualConfigurator(payload={}){
  ensureStyle();
  const draft=initialScenario(payload),saved=savedScenarios(draft.fixture_id);
  if(!(payload.lineup_context||{}).available)return `<div class="match-card-v2-empty">Конфигуратор появится, когда для матча доступен хотя бы expected/official XI.</div>`;
  return `<div class="manual-lineup-config" data-manual-fixture="${esc(draft.fixture_id)}"><div class="manual-lineup-top"><label>Название сценария <input data-manual-name value="${esc(draft.name)}"></label><label>Источник / заметка <input data-manual-note placeholder="например: инсайд по составу"></label></div><div class="manual-lineup-warning">Ручной сценарий не перезаписывает данные провайдера и всегда помечается как WHAT-IF.</div><div class="manual-lineup-two">${sideEditor('home','Хозяева',draft.home)}${sideEditor('away','Гости',draft.away)}</div><div data-manual-preview>${renderPitch({...selectedTeam(payload.lineup_context.home),formation:draft.home.formation,starting_xi:draft.home.xi},{...selectedTeam(payload.lineup_context.away),formation:draft.away.formation,starting_xi:draft.away.xi},payload.player_grade||{})}</div><div class="manual-lineup-actions"><button type="button" data-manual-run>Запустить анализ</button><button type="button" data-manual-save>Сохранить сценарий</button>${saved.length?`<span>Сохранено для матча: ${saved.length}</span>`:''}</div><div data-manual-result></div></div>`;
}

function pullDraft(root,payload){const draft=initialScenario(payload);draft.name=root.querySelector('[data-manual-name]')?.value||'Инсайд состава';draft.note=root.querySelector('[data-manual-note]')?.value||'';for(const side of ['home','away']){draft[side].formation=root.querySelector(`[data-manual-formation="${side}"]`)?.value||draft[side].formation;draft[side].xi=[];for(let i=0;i<11;i++){const select=root.querySelector(`[data-manual-side="${side}"][data-manual-slot="${i}"]`);if(!select)continue;let p;if(select.value==='__custom__'){const input=root.querySelector(`[data-manual-custom="${side}:${i}"]`);const custom=(input?.value||'').trim();if(custom)p={id:`manual:${side}:${i}:${custom}`,name:custom,number:'?',pos:''}}else p=draft[side].pool.find(x=>pid(x)===select.value);if(p)draft[side].xi.push(clonePlayer(p))}}return draft}
function validDraft(draft){const problems=[];for(const side of ['home','away']){if(draft[side].xi.length!==11)problems.push(`${side}: нужно 11 игроков`);if(new Set(draft[side].xi.map(pid)).size!==11)problems.push(`${side}: игроки не должны повторяться`)}return problems}

export function initManualLineupConfigurator(payload={},container=document){
  const roots=[...(container.querySelectorAll?.('[data-manual-fixture]')||[])];if(!roots.length)return;
  const root=roots[roots.length-1];if(root.dataset.manualReady==='1')return;root.dataset.manualReady='1';
  root.addEventListener('change',event=>{const select=event.target.closest?.('[data-manual-side]');if(select){const side=select.dataset.manualSide,index=select.dataset.manualSlot,input=root.querySelector(`[data-manual-custom="${side}:${index}"]`);if(input)input.hidden=select.value!=='__custom__'}const draft=pullDraft(root,payload);const preview=root.querySelector('[data-manual-preview]');if(preview&&draft.home.xi.length===11&&draft.away.xi.length===11)preview.innerHTML=renderPitch({...selectedTeam(payload.lineup_context.home),formation:draft.home.formation,starting_xi:draft.home.xi},{...selectedTeam(payload.lineup_context.away),formation:draft.away.formation,starting_xi:draft.away.xi},payload.player_grade||{})});
  root.querySelector('[data-manual-run]')?.addEventListener('click',()=>{const draft=pullDraft(root,payload),problems=validDraft(draft),target=root.querySelector('[data-manual-result]');target.innerHTML=problems.length?`<div class="match-card-v2-error">${problems.map(esc).join(' · ')}</div>`:resultHtml(analyzeScenario(draft,payload))});
  root.querySelector('[data-manual-save]')?.addEventListener('click',()=>{const draft=pullDraft(root,payload),problems=validDraft(draft),target=root.querySelector('[data-manual-result]');if(problems.length){target.innerHTML=`<div class="match-card-v2-error">${problems.map(esc).join(' · ')}</div>`;return}const result=analyzeScenario(draft,payload);const saved={...draft,analysis:result,created_at_utc:new Date().toISOString(),source_label:'MANUAL/INSIDER',what_if_only:true};const rows=readSaved();rows.push(saved);writeSaved(rows);target.innerHTML=`${resultHtml(result)}<div class="match-card-v2-note">Сценарий сохранён локально в этом браузере. Provider/Forward данные не изменены.</div>`});
}