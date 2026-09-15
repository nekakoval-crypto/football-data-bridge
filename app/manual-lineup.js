import {renderPitch,selectedTeam} from './formations.js';

const STORAGE_KEY='pbkManualLineupScenariosV1';
const STYLE_ID='pbk-manual-lineup-style-v2';
const FORECAST_VERSION='PBK_MANUAL_WHAT_IF_FORECAST_V1';
const XI_GRADE_LOGIT_PER_POINT=0.08;
const MAX_LOGIT_SHIFT=0.25;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const FORMATIONS=['4-3-3','4-2-3-1','4-4-2','3-5-2','3-4-3','3-4-2-1','5-3-2','5-4-1'];

const pid=p=>String(p?.id??p?.player_id??'');
const name=p=>p?.lastname||p?.last_name||p?.name||p?.player_name||`#${pid(p)}`;
const clamp=(v,min,max)=>Math.max(min,Math.min(max,v));

function ensureStyle(){
  if(typeof document==='undefined'||document.getElementById(STYLE_ID))return;
  const style=document.createElement('style');style.id=STYLE_ID;style.textContent=`
  .formation-grade{display:block;color:#d8f7b7;font-size:9px;font-weight:800;text-shadow:0 1px 3px #000}
  .manual-lineup-config{display:grid;gap:12px}.manual-lineup-top,.manual-lineup-two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.manual-lineup-top label,.manual-lineup-side-head label{display:grid;gap:5px;color:var(--muted);font-size:10px}.manual-lineup-top input,.manual-lineup-side select,.manual-lineup-slot input,.manual-lineup-slot select{width:100%;box-sizing:border-box;background:#0b1117;border:1px solid #334150;border-radius:9px;color:var(--text);padding:8px;font:inherit}.manual-lineup-warning{border:1px solid #755322;background:rgba(255,173,69,.06);border-radius:10px;padding:9px;color:#ffd69c;font-size:11px}.manual-lineup-side{background:#0d131a;border:1px solid #263544;border-radius:12px;padding:10px;min-width:0}.manual-lineup-side-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}.manual-lineup-slots{display:grid;gap:5px}.manual-lineup-slot{display:grid;grid-template-columns:24px minmax(0,1fr);gap:6px;align-items:center}.manual-lineup-slot>span{color:var(--muted);font-size:10px;text-align:center}.manual-lineup-slot input{grid-column:2}.manual-lineup-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.manual-lineup-actions button{border:1px solid #3b6081;background:#16324a;color:#e5f3ff;border-radius:10px;padding:9px 12px;font-weight:750;cursor:pointer}.manual-lineup-actions button+button{background:#17221c;border-color:#38614b}.manual-lineup-actions span{color:var(--muted);font-size:10px}.manual-lineup-analysis{display:grid;gap:8px;margin-top:8px}.manual-lineup-result-side,.manual-lineup-forecast{display:grid;gap:4px;background:#0d131a;border:1px solid #263544;border-radius:10px;padding:10px}.manual-lineup-result-side span,.manual-lineup-forecast span{font-size:11px;color:var(--muted)}.manual-lineup-result-side b,.manual-lineup-forecast b{color:var(--text)}.manual-lineup-forecast-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.manual-lineup-forecast-cell{padding:8px;border:1px solid #263544;border-radius:8px;text-align:center}.manual-lineup-forecast-cell b{display:block;font-size:16px}.manual-lineup-forecast-cell small{color:var(--muted)}
  @media(max-width:760px){.manual-lineup-top,.manual-lineup-two{grid-template-columns:1fr}.manual-lineup-side-head{align-items:flex-start}.manual-lineup-slot select,.manual-lineup-slot input{min-height:40px}}
  `;document.head.appendChild(style);
}

function clonePlayer(p={}){return {id:pid(p),name:p.name||p.player_name||'',lastname:p.lastname||p.last_name||'',number:p.number??'',pos:p.pos||p.position||'',grid:p.grid||''}}
function uniquePlayers(...groups){const out=new Map();for(const group of groups)for(const p of group||[]){const id=pid(p);if(id)out.set(id,{...(out.get(id)||{}),...clonePlayer(p)})}return [...out.values()]}
function gradeMap(pg={},side){const team=pg?.[side]||{};return team.grades_by_player&&typeof team.grades_by_player==='object'?team.grades_by_player:Object.fromEntries((team.grades||[]).filter(x=>x?.player_id).map(x=>[String(x.player_id),x]))}
function fixtureTeam(payload,key){return payload?.fixture?.[key]||{}}

export function initialScenario(payload={}){
  const lineup=payload.lineup_context||{},pg=payload.player_grade||{};
  const side=key=>{
    const raw=lineup[key]||{},base=selectedTeam(raw),currentXi=(base.starting_xi||[]).map(x=>clonePlayer(x?.player||x));
    const reference=(pg[key]?.reference_xi||[]).map(clonePlayer),baseline=currentXi.length===11?currentXi:reference;
    const pool=uniquePlayers(pg[key]?.player_pool,currentXi,reference);
    return {
      teamName:raw.team_name||fixtureTeam(payload,key).name||(key==='home'?'Хозяева':'Гости'),
      formation:base.formation||'4-3-3',
      xi:currentXi.length===11?currentXi:[],
      pool,
      baselineXi:baseline.map(clonePlayer),
      baselineFormation:base.formation||null,
      baselineStatus:currentXi.length===11?(base.status||'CURRENT'):(reference.length===11?'LAST_KNOWN_XI':'NONE'),
    };
  };
  return {fixture_id:String(payload.fixture_id||payload.fixture?.fixture_id||''),name:'Инсайд состава',note:'',home:side('home'),away:side('away')};
}

function readSaved(){try{const raw=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');return Array.isArray(raw)?raw:[]}catch{return []}}
function writeSaved(rows){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(rows.slice(-100)))}catch{}}
export function savedScenarios(fixtureId){return readSaved().filter(x=>String(x.fixture_id)===String(fixtureId))}

function quality(xi,grades){const vals=xi.map(p=>grades[pid(p)]?.current_grade).filter(v=>v!==null&&v!==undefined&&v!=='').map(Number).filter(Number.isFinite);return {value:vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null,covered:vals.length,total:xi.length}}
function lineOf(p){const pos=String(p?.pos||'').toUpperCase();if(pos.startsWith('G'))return'GK';if(pos.startsWith('D'))return'DEF';if(pos.startsWith('F')||['ST','CF','LW','RW'].includes(pos))return'ATT';return'MID'}
function lineQuality(xi,grades){const out={};for(const p of xi){const value=Number(grades[pid(p)]?.current_grade);if(!Number.isFinite(value))continue;(out[lineOf(p)]??=[]).push(value)}return Object.fromEntries(Object.entries(out).map(([k,v])=>[k,v.reduce((a,b)=>a+b,0)/v.length]))}
function probability(v){const n=Number(v);if(!Number.isFinite(n)||n<=0)return null;return n>1&&n<=100?n/100:n<=1?n:null}
function selectionKey(value){const s=String(value??'').trim().toUpperCase().replace(/\s+/g,'');if(['1','П1','HOME','HOME_WIN','H'].includes(s))return'home';if(['X','Х','DRAW','D'].includes(s))return'draw';if(['2','П2','AWAY','AWAY_WIN','A'].includes(s))return'away';return null}
function normalizeTriplet(values){if(!values||['home','draw','away'].some(k=>!Number.isFinite(values[k])||values[k]<=0))return null;const total=values.home+values.draw+values.away;if(total<=0)return null;return {home:values.home/total,draw:values.draw/total,away:values.away/total}}

export function baseline1x2(payload={}){
  const fromPrediction={};
  for(const item of payload?.prediction?.items||[]){const key=selectionKey(item?.selection),p=probability(item?.p_pbk);if(key&&p!==null)fromPrediction[key]=p}
  const pbk=normalizeTriplet(fromPrediction);if(pbk)return {available:true,source:'PBK_FROZEN',probabilities:pbk};
  const family=(payload?.markets?.families||[]).find(x=>x?.id==='MATCH_RESULT_1X2');const fromMarket={};
  for(const item of family?.items||[]){const key=selectionKey(item?.selection),p=probability(item?.market_no_vig);if(key&&p!==null)fromMarket[key]=p}
  const market=normalizeTriplet(fromMarket);if(market)return {available:true,source:'MARKET_NO_VIG',probabilities:market};
  return {available:false,source:null,probabilities:null};
}

function buildForecast(result,payload={}){
  const base=baseline1x2(payload);if(!base.available)return {version:FORECAST_VERSION,available:false,experimental:true,reason:'NO_BASELINE_1X2'};
  const h=result.sides.home,a=result.sides.away;
  const manualCoverage=Math.min(h.manual_quality.covered/11,a.manual_quality.covered/11);
  const baselineCoverage=Math.min((h.baseline_quality.covered||0)/11,(a.baseline_quality.covered||0)/11);
  const coverage=clamp(Math.min(manualCoverage,baselineCoverage),0,1);
  const hDelta=Number(h.quality_delta),aDelta=Number(a.quality_delta);
  const canAdjust=Number.isFinite(hDelta)&&Number.isFinite(aDelta)&&h.baseline_quality.value!==null&&a.baseline_quality.value!==null&&coverage>0;
  const rawImpact=canAdjust?hDelta-aDelta:0;
  const shift=canAdjust?clamp(rawImpact*XI_GRADE_LOGIT_PER_POINT*coverage,-MAX_LOGIT_SHIFT,MAX_LOGIT_SHIFT):0;
  const p=base.probabilities;
  const weights={home:p.home*Math.exp(shift),draw:p.draw,away:p.away*Math.exp(-shift)};
  const scenario=normalizeTriplet(weights)||p;
  const delta={home:scenario.home-p.home,draw:scenario.draw-p.draw,away:scenario.away-p.away};
  const confidence=canAdjust?(coverage>=0.75?'MEDIUM':'LOW'):'LOW';
  return {
    version:FORECAST_VERSION,available:true,experimental:true,source:base.source,
    baseline:p,scenario,delta,adjustment_applied:canAdjust,confidence,
    coverage_pct:Math.round(coverage*1000)/10,xi_grade_impact:canAdjust?rawImpact:null,logit_shift:canAdjust?shift:0,
    limitations:canAdjust?['UNVALIDATED_XI_GRADE_TO_PROBABILITY_HEURISTIC']:['NO_PREMATCH_SAFE_BASELINE_XI_GRADE_DELTA','BASELINE_FORECAST_ONLY'],
    canonical_mutation:false,eligibility_mutation:false,stake_changes:false,
  };
}

export function analyzeScenario(draft,payload={}){
  const pg=payload.player_grade||{};const result={fixture_id:draft.fixture_id,what_if_only:true,research_only:true,probability_mutation:false,eligibility_mutation:false,stake_changes:false,sides:{}};
  for(const side of ['home','away']){
    const grades=gradeMap(pg,side),s=draft[side],base=quality(s.baselineXi,grades),manual=quality(s.xi,grades),bLines=lineQuality(s.baselineXi,grades),mLines=lineQuality(s.xi,grades);
    const before=new Set(s.baselineXi.map(pid)),after=new Set(s.xi.map(pid));
    result.sides[side]={formation:s.formation,baseline_formation:s.baselineFormation,baseline_status:s.baselineStatus,formation_changed:Boolean(s.baselineFormation&&s.formation!==s.baselineFormation),added:s.xi.filter(p=>!before.has(pid(p))),removed:s.baselineXi.filter(p=>!after.has(pid(p))),overlap:[...after].filter(x=>before.has(x)).length,baseline_quality:base,manual_quality:manual,quality_delta:base.value!==null&&manual.value!==null?manual.value-base.value:null,line_delta:Object.fromEntries([...new Set([...Object.keys(bLines),...Object.keys(mLines)])].map(k=>[k,bLines[k]!==undefined&&mLines[k]!==undefined?mLines[k]-bLines[k]:null]))};
  }
  result.forecast=buildForecast(result,payload);
  return result;
}

function playerOption(p,current){return `<option value="${esc(pid(p))}" ${pid(p)===current?'selected':''}>${esc(p.number?`${p.number} · `:'')}${esc(name(p))}${p.pos?` · ${esc(p.pos)}`:''}</option>`}
function slotEditor(side,index,player,pool){const noPool=!pool.length&&!pid(player);const selectValue=pid(player)|| (noPool?'__custom__':'');return `<div class="manual-lineup-slot"><span>${index+1}</span><select data-manual-side="${side}" data-manual-slot="${index}"><option value="" ${selectValue===''?'selected':''}>— выбрать —</option>${pool.map(p=>playerOption(p,pid(player))).join('')}<option value="__custom__" ${selectValue==='__custom__'?'selected':''}>+ игрок вручную</option></select><input type="text" data-manual-custom="${side}:${index}" value="" placeholder="Фамилия / неизвестный игрок" ${selectValue==='__custom__'?'':'hidden'}></div>`}
function formationSelect(side,value){return `<select data-manual-formation="${side}">${[...new Set([value,...FORMATIONS].filter(Boolean))].map(x=>`<option value="${esc(x)}" ${x===value?'selected':''}>${esc(x)}</option>`).join('')}</select>`}
function sideEditor(side,label,s){return `<div class="manual-lineup-side"><div class="manual-lineup-side-head"><strong>${esc(s.teamName||label)}</strong><label>Схема ${formationSelect(side,s.formation)}</label></div><div class="manual-lineup-slots">${Array.from({length:11},(_,i)=>slotEditor(side,i,s.xi[i]||{},s.pool)).join('')}</div></div>`}
function fmt(v){return v===null||v===undefined||!Number.isFinite(Number(v))?'—':Number(v).toFixed(2)}
function pct(v){return v===null||v===undefined||!Number.isFinite(Number(v))?'—':`${(Number(v)*100).toFixed(1)}%`}
function pp(v){return v===null||v===undefined||!Number.isFinite(Number(v))?'—':`${Number(v)>=0?'+':''}${(Number(v)*100).toFixed(1)} п.п.`}
function forecastHtml(f){if(!f?.available)return `<div class="manual-lineup-forecast"><strong>WHAT-IF прогноз · EXPERIMENTAL</strong><span>Нет полной базовой вероятности 1X2. Состав можно сохранить и сравнивать, но числовой прогноз сейчас честно не строится.</span></div>`;const cell=(label,key)=>`<div class="manual-lineup-forecast-cell"><small>${label}</small><b>${pct(f.scenario[key])}</b><small>${pp(f.delta[key])}</small></div>`;return `<div class="manual-lineup-forecast"><strong>WHAT-IF прогноз · EXPERIMENTAL</strong><span>Базовая основа: ${esc(f.source)} · confidence ${esc(f.confidence)} · покрытие grade/reference ${esc(f.coverage_pct)}%</span><div class="manual-lineup-forecast-grid">${cell('П1','home')}${cell('Х','draw')}${cell('П2','away')}</div><span>Baseline: П1 ${pct(f.baseline.home)} · Х ${pct(f.baseline.draw)} · П2 ${pct(f.baseline.away)}</span>${f.adjustment_applied?`<span>Эвристическая поправка по Δ XI Grade применена: ${fmt(f.xi_grade_impact)}. Она ещё не откалибрована forward-выборкой.</span>`:`<span>Сценарная поправка состава пока не применена: нет достаточного pre-match-safe baseline XI Grade. Показан baseline-прогноз.</span>`}<span>Sandbox only: canonical probability, R1/R2/R3, eligibility, stake и Forward не меняются.</span></div>`}
function resultHtml(result){const one=(label,s)=>`<div class="manual-lineup-result-side"><strong>${label}</strong><span>XI Quality: ${fmt(s.baseline_quality.value)} → ${fmt(s.manual_quality.value)} <b>Δ ${fmt(s.quality_delta)}</b></span><span>Покрытие grade: ${s.manual_quality.covered}/${s.manual_quality.total}</span><span>Baseline: ${esc(s.baseline_status||'NONE')} · совпадение ${s.overlap}/11 · схема ${esc(s.baseline_formation||'—')} → ${esc(s.formation||'—')}</span><span>Линии: ${Object.entries(s.line_delta).map(([k,v])=>`${k} ${fmt(v)}`).join(' · ')||'—'}</span><span>Вышли: ${s.added.map(name).join(', ')||'—'}</span><span>Убраны: ${s.removed.map(name).join(', ')||'—'}</span></div>`;return `<div class="manual-lineup-analysis"><div class="match-card-v2-research-label">MANUAL SCENARIO / WHAT-IF</div>${one('Хозяева',result.sides.home)}${one('Гости',result.sides.away)}${forecastHtml(result.forecast)}<div class="match-card-v2-note">Это sandbox-анализ состава. Он не меняет canonical probability, R1/R2/R3, Value eligibility, ставку или Forward-журнал.</div></div>`}

export function renderManualConfigurator(payload={}){
  ensureStyle();
  const draft=initialScenario(payload),saved=savedScenarios(draft.fixture_id),hasKnownPool=draft.home.pool.length||draft.away.pool.length;
  const stateNote=(payload.lineup_context||{}).available?'Expected/official XI подставлен как текущая основа. Его можно полностью заменить.':(hasKnownPool?'Expected/official XI пока нет. Конфигуратор уже активен: выбирай игроков из ранее известного roster или вводи вручную.':'Expected/official XI и roster пока не собраны. Конфигуратор всё равно активен: собери 11+11 вручную.');
  const homeBase=(payload.lineup_context||{}).home||{},awayBase=(payload.lineup_context||{}).away||{};
  return `<div class="manual-lineup-config" data-manual-fixture="${esc(draft.fixture_id)}"><div class="manual-lineup-top"><label>Название сценария <input data-manual-name value="${esc(draft.name)}"></label><label>Источник / заметка <input data-manual-note placeholder="например: инсайд по составу"></label></div><div class="manual-lineup-warning">${esc(stateNote)} Ручной сценарий не перезаписывает данные провайдера и всегда помечается WHAT-IF.</div><div class="manual-lineup-two">${sideEditor('home','Хозяева',draft.home)}${sideEditor('away','Гости',draft.away)}</div><div data-manual-preview>${renderPitch({...selectedTeam(homeBase),formation:draft.home.formation,starting_xi:draft.home.xi},{...selectedTeam(awayBase),formation:draft.away.formation,starting_xi:draft.away.xi},payload.player_grade||{})}</div><div class="manual-lineup-actions"><button type="button" data-manual-run>Запустить анализ и прогноз</button><button type="button" data-manual-save>Сохранить сценарий</button>${saved.length?`<span>Сохранено для матча: ${saved.length}</span>`:''}</div><div data-manual-result></div></div>`;
}

function pullDraft(root,payload){const draft=initialScenario(payload);draft.name=root.querySelector('[data-manual-name]')?.value||'Инсайд состава';draft.note=root.querySelector('[data-manual-note]')?.value||'';for(const side of ['home','away']){draft[side].formation=root.querySelector(`[data-manual-formation="${side}"]`)?.value||draft[side].formation;draft[side].xi=[];for(let i=0;i<11;i++){const select=root.querySelector(`[data-manual-side="${side}"][data-manual-slot="${i}"]`);if(!select)continue;let p;if(select.value==='__custom__'){const input=root.querySelector(`[data-manual-custom="${side}:${i}"]`);const custom=(input?.value||'').trim();if(custom)p={id:`manual:${side}:${i}:${custom}`,name:custom,number:'?',pos:''}}else p=draft[side].pool.find(x=>pid(x)===select.value);if(p)draft[side].xi.push(clonePlayer(p))}}return draft}
function validDraft(draft){const problems=[];for(const side of ['home','away']){if(draft[side].xi.length!==11)problems.push(`${side}: нужно 11 игроков`);if(new Set(draft[side].xi.map(pid)).size!==11)problems.push(`${side}: игроки не должны повторяться`)}return problems}

export function initManualLineupConfigurator(payload={},container=document){
  const roots=[...(container.querySelectorAll?.('[data-manual-fixture]')||[])];if(!roots.length)return;
  const root=roots[roots.length-1];if(root.dataset.manualReady==='1')return;root.dataset.manualReady='1';
  root.addEventListener('change',event=>{const select=event.target.closest?.('[data-manual-side]');if(select){const side=select.dataset.manualSide,index=select.dataset.manualSlot,input=root.querySelector(`[data-manual-custom="${side}:${index}"]`);if(input)input.hidden=select.value!=='__custom__'}const draft=pullDraft(root,payload);const preview=root.querySelector('[data-manual-preview]');if(preview&&draft.home.xi.length===11&&draft.away.xi.length===11)preview.innerHTML=renderPitch({...selectedTeam((payload.lineup_context||{}).home||{}),formation:draft.home.formation,starting_xi:draft.home.xi},{...selectedTeam((payload.lineup_context||{}).away||{}),formation:draft.away.formation,starting_xi:draft.away.xi},payload.player_grade||{})});
  root.querySelector('[data-manual-run]')?.addEventListener('click',()=>{const draft=pullDraft(root,payload),problems=validDraft(draft),target=root.querySelector('[data-manual-result]');target.innerHTML=problems.length?`<div class="match-card-v2-error">${problems.map(esc).join(' · ')}</div>`:resultHtml(analyzeScenario(draft,payload))});
  root.querySelector('[data-manual-save]')?.addEventListener('click',()=>{const draft=pullDraft(root,payload),problems=validDraft(draft),target=root.querySelector('[data-manual-result]');if(problems.length){target.innerHTML=`<div class="match-card-v2-error">${problems.map(esc).join(' · ')}</div>`;return}const result=analyzeScenario(draft,payload);const saved={...draft,analysis:result,created_at_utc:new Date().toISOString(),source_label:'MANUAL/INSIDER',what_if_only:true};const rows=readSaved();rows.push(saved);writeSaved(rows);target.innerHTML=`${resultHtml(result)}<div class="match-card-v2-note">Сценарий сохранён локально в этом браузере. Provider/Forward данные не изменены.</div>`});
}
