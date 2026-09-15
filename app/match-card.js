import {renderPitch, selectedTeam, positions} from './formations.js';
import {renderManualConfigurator,initManualLineupConfigurator} from './manual-lineup.js';
import { renderMatchCard as renderCoreMatchCard } from './match-card-core.js';
export * from './match-card-core.js';

const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
const list=value=>Array.isArray(value)?value:[];
const badge=(text,tone='neutral')=>`<span class="match-card-v2-badge ${tone}">${esc(text)}</span>`;
const empty=text=>`<div class="match-card-v2-empty">${esc(text)}</div>`;
const section=(title,body,className='')=>`<section class="match-card-v2-section ${className}"><div class="match-card-v2-section-title">${esc(title)}</div>${body}</section>`;

function playerName(item){
  if(typeof item==='string')return item;
  if(!item||typeof item!=='object')return '';
  return item.name||item.player_name||item.player?.name||item.player||'';
}

function lineupStatus(team={}){
  const status=String(team.status||'UNKNOWN').toUpperCase();
  if(status==='CONFIRMED')return badge('Официальный XI','good');
  if(status==='EXPECTED')return badge('Ожидаемый XI','warn');
  return badge('XI не подтверждён','neutral');
}

function lineupTeam(label,team={}){
  team=selectedTeam(team);
  const xi=list(team.starting_xi);
  const names=xi.map(playerName).filter(Boolean);
  const confidence=team.expected_confidence?badge(`Expected: ${team.expected_confidence}`,team.expected_confidence==='HIGH'?'good':'neutral'):'';
  const basis=Number(team.expected_basis_fixtures||0)>0?`<small>Основание expected XI: ${esc(team.expected_basis_fixtures)} прошлых официальных составов</small>`:'';
  return `<div class="match-card-v2-lineup"><div class="match-card-v2-context-meta"><span>${esc(label)}</span>${lineupStatus(team)}${confidence}</div><strong>${esc(team.formation||'Схема не подтверждена')}</strong><small>${team.coach?`Тренер: ${esc(team.coach)}`:'Тренер не подтверждён'}</small><small>Обновлено: ${esc(team.captured_at_utc||team.updated_at_utc||'неизвестно')}</small>${basis}${names.length&&!positions(team).length?`<div class="match-card-v2-reasons">${names.map(name=>badge(name)).join('')}</div>`:(!names.length?empty('Стартовый XI пока недоступен.'):'')}</div>`;
}

function lineupContext(payload={}){
  const l=payload.lineup_context||{};
  if(!l.available)return section('Схема / тренер / состав',empty('Нет данных по составу. Expected/official XI пока недоступен.'));
  const trust=`<div class="match-card-v2-trust">${l.no_lookahead?badge('Только данные до kickoff','good'):badge('Cutoff не подтверждён','warn')}${badge('provider-free')}${l.rotation_projection?`<span>${esc(l.rotation_projection)}</span>`:''}</div>`;
  return section('Схема / тренер / состав',`<div class="match-card-v2-two">${lineupTeam(l.home?.team_name||'Хозяева',l.home)}${lineupTeam(l.away?.team_name||'Гости',l.away)}</div>${renderPitch(l.home,l.away,payload.player_grade||{})}${trust}<div class="match-card-v2-note">Официальный XI имеет приоритет. Expected XI — детерминированный контекст по прошлым подтверждённым стартовым составам, а не новый прогноз ПБК.</div>`,'lineup-context');
}

function gradeTeam(label,team={}){
  const q=team.xi_quality||{};const grades=list(team.grades).filter(x=>x?.current_grade!==null&&x?.current_grade!==undefined);
  const top=[...grades].sort((a,b)=>Number(b.current_grade)-Number(a.current_grade)).slice(0,3);
  return `<div class="match-card-v2-team-context"><span>${esc(label)}</span><strong>${q.xi_quality===null||q.xi_quality===undefined?'XI Quality пока нет':`XI Quality ${esc(Number(q.xi_quality).toFixed(2))}`}</strong><small>Покрытие: ${esc(q.covered_players??0)}/${esc(team.xi?.length??11)} · pool ${esc(team.pool_size??0)}</small>${top.length?`<div class="match-card-v2-reasons">${top.map(g=>badge(`${g.player_name||g.player_id}: ${Number(g.current_grade).toFixed(1)} · ${g.grade_basis||'grade'}`,g.confidence==='HIGH'?'good':'neutral')).join('')}</div>`:''}</div>`;
}

function playerGrade(payload={}){
  const pg=payload.player_grade||{};
  if(!pg.available)return section('PBK Player Grade / XI Quality',`<div class="match-card-v2-empty">История Player Grade пока не накоплена. Поле состава и ручной сценарий работают, но числовой XI Quality будет появляться только из pre-match-safe истории.</div><div class="match-card-v2-note">Research only · no-lookahead · отсутствие grade не превращается в ноль.</div>`,'research');
  return section('PBK Player Grade / XI Quality',`<div class="match-card-v2-research-label">RESEARCH / CONTEXT</div><div class="match-card-v2-two">${gradeTeam('Хозяева',pg.home)}${gradeTeam('Гости',pg.away)}</div><div class="match-card-v2-note">Grade под игроками — Form 5 либо последняя доступная историческая оценка до kickoff. Не является live-рейтингом текущего матча и не меняет canonical probability/eligibility/stake.</div>`,'research');
}

function surpriseTeam(label,team={}){
  if(!team.available)return `<div class="match-card-v2-team-context"><span>${esc(label)}</span><strong>Ожидаем официальный XI</strong></div>`;
  const unexpected=list(team.unexpected_starters).map(playerName).filter(Boolean);
  const missing=list(team.missing_expected).map(playerName).filter(Boolean);
  const concentration=team.concentration||{};
  return `<div class="match-card-v2-team-context"><span>${esc(label)}</span><strong>Совпадение ${esc(team.overlap_starters)}/11</strong><div>${badge(`Неожиданных в старте: ${team.unexpected_starters_count??'—'}`,Number(team.unexpected_starters_count||0)>=3?'warn':'neutral')}</div>${concentration.available?`<small>Стабильное ядро: ${esc(concentration.stable_core_players)}/11 · средняя частота старта ${esc(concentration.average_start_share_pct)}%</small>`:''}${unexpected.length?`<div><small>Не ожидались:</small><div class="match-card-v2-reasons">${unexpected.map(name=>badge(name,'warn')).join('')}</div></div>`:''}${missing.length?`<div><small>Ожидались, но не в старте:</small><div class="match-card-v2-reasons">${missing.map(name=>badge(name)).join('')}</div></div>`:''}</div>`;
}

function lineupSurprise(payload={}){
  const s=payload.lineup_surprise||{};
  if(!s.available)return section('M5 · отклонение состава',empty('Сравнение expected XI с официальным составом появится после подтверждения обоих стартовых XI.'));
  return section('M5 · отклонение состава',`<div class="match-card-v2-two">${surpriseTeam('Хозяева',s.home)}${surpriseTeam('Гости',s.away)}</div><div class="match-card-v2-note">Только фактическое отклонение состава. Этот блок не создаёт сигнал, не меняет вероятность, eligibility или размер ставки.</div>`,'lineup-surprise');
}

function manualScenario(payload={}){
  return section('Ручной конфигуратор состава',`<div class="match-card-v2-research-label">MANUAL / INSIDER · WHAT-IF</div>${renderManualConfigurator(payload)}`,'research manual-lineup-section');
}

export function renderMatchCard(payload={}){
  const base=renderCoreMatchCard(payload);
  const addition=`${lineupContext(payload)}${playerGrade(payload)}${lineupSurprise(payload)}${manualScenario(payload)}`;
  const end=base.lastIndexOf('</div>');
  const html=end>=0?`${base.slice(0,end)}${addition}${base.slice(end)}`:`${base}${addition}`;
  if(typeof document!=='undefined'&&typeof queueMicrotask==='function')queueMicrotask(()=>initManualLineupConfigurator(payload,document));
  return html;
}

export function initMatchCardExtensions(payload={},container=document){
  initManualLineupConfigurator(payload,container);
}