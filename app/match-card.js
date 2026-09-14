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
  const xi=list(team.starting_xi);
  const names=xi.map(playerName).filter(Boolean);
  const confidence=team.expected_confidence?badge(`Expected: ${team.expected_confidence}`,team.expected_confidence==='HIGH'?'good':'neutral'):'';
  const basis=Number(team.expected_basis_fixtures||0)>0?`<small>Основание expected XI: ${esc(team.expected_basis_fixtures)} прошлых официальных составов</small>`:'';
  return `<div class="match-card-v2-lineup"><div class="match-card-v2-context-meta"><span>${esc(label)}</span>${lineupStatus(team)}${confidence}</div><strong>${esc(team.formation||'Схема не подтверждена')}</strong><small>${team.coach?`Тренер: ${esc(team.coach)}`:'Тренер не подтверждён'}</small>${basis}${names.length?`<div class="match-card-v2-reasons">${names.map(name=>badge(name)).join('')}</div>`:empty('Стартовый XI пока недоступен.')}</div>`;
}

function lineupContext(payload={}){
  const l=payload.lineup_context||{};
  if(!l.available)return section('Схема / тренер / состав',empty('Expected/official XI пока недоступен.'));
  const trust=`<div class="match-card-v2-trust">${l.no_lookahead?badge('Только данные до kickoff','good'):badge('Cutoff не подтверждён','warn')}${badge('provider-free')}${l.rotation_projection?`<span>${esc(l.rotation_projection)}</span>`:''}</div>`;
  return section('Схема / тренер / состав',`<div class="match-card-v2-two">${lineupTeam('Хозяева',l.home)}${lineupTeam('Гости',l.away)}</div>${trust}<div class="match-card-v2-note">Официальный XI имеет приоритет. Expected XI — детерминированный контекст по прошлым подтверждённым стартовым составам, а не новый прогноз ПБК.</div>`,'lineup-context');
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

export function renderMatchCard(payload={}){
  const base=renderCoreMatchCard(payload);
  const addition=`${lineupContext(payload)}${lineupSurprise(payload)}`;
  const end=base.lastIndexOf('</div>');
  return end>=0?`${base.slice(0,end)}${addition}${base.slice(end)}`:`${base}${addition}`;
}
