const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));

export function safeMediaUrl(value){
  try{const url=new URL(String(value||''));return url.protocol==='https:'?url.href:''}catch{return ''}
}

function media(url,className,label){
  const safe=safeMediaUrl(url);
  return safe?`<img class="${className}" src="${esc(safe)}" alt="" loading="lazy" onerror="this.classList.add('match-card-v2-image-broken');this.removeAttribute('src')">`:`<span class="${className} match-card-v2-image-placeholder" aria-label="${esc(label)}"></span>`;
}

function fmtMoscow(value,withDate=true){
  if(!value)return '—';const date=new Date(value);if(Number.isNaN(date.getTime()))return String(value);
  const opts=withDate?{timeZone:'Europe/Moscow',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}:{timeZone:'Europe/Moscow',hour:'2-digit',minute:'2-digit'};
  return `${new Intl.DateTimeFormat('ru-RU',opts).format(date)} МСК`;
}

function fmtPct(value){
  if(value===null||value===undefined||value==='')return '—';const n=Number(value);if(Number.isNaN(n))return esc(value);const pct=Math.abs(n)<=1?n*100:n;return `${pct.toFixed(2).replace(/\.00$/,'')}%`;
}

function fmtNum(value,suffix=''){return value===null||value===undefined||value===''?'—':`${esc(value)}${suffix}`}
function list(value){return Array.isArray(value)?value:[]}
function section(title,body,className=''){return `<section class="match-card-v2-section ${className}"><div class="match-card-v2-section-title">${esc(title)}</div>${body}</section>`}
function empty(text){return `<div class="match-card-v2-empty">${esc(text)}</div>`}
function badge(text,tone='neutral'){return `<span class="match-card-v2-badge ${tone}">${esc(text)}</span>`}

const STATUS_RU={scheduled:'По расписанию',live:'LIVE',finished:'FT',postponed:'Перенесён',cancelled:'Отменён',suspended:'Приостановлен',interrupted:'Прерван',abandoned:'Прекращён',awarded:'Технический',walkover:'Тех. победа',unknown:'Не подтверждён'};
export function formatMatchCardStatus(status){return STATUS_RU[String(status||'').toLowerCase()]||STATUS_RU.unknown}

function redCards(count){const n=Number(count);return Number.isInteger(n)&&n>0?`<span class="match-card-v2-red">🟥${n>1?` ${n}`:''}</span>`:''}

function header(payload){
  const f=payload?.fixture||{};const status=String(f.status||'unknown').toLowerCase();const score=f.score&&f.score.home!==null&&f.score.home!==undefined&&f.score.away!==null&&f.score.away!==undefined?`${esc(f.score.home)}:${esc(f.score.away)}`:'';
  const scheduled=status==='scheduled';const center=score|| (scheduled?fmtMoscow(f.kickoff_utc):formatMatchCardStatus(status));
  const freshness=String(f.live_freshness_status||'unknown').toLowerCase();const freshnessTone=freshness==='fresh'?'good':freshness==='stale'?'warn':'neutral';
  const leagueMedia=`${media(f.country_flag_url,'match-card-v2-flag','Флаг страны')}<strong>${esc(f.league_name||'Лига не подтверждена')}</strong>${media(f.league_logo_url,'match-card-v2-league-logo','Логотип лиги')}`;
  const liveMeta=status==='live'&&f.elapsed!==null&&f.elapsed!==undefined?` · ${esc(f.elapsed)}′`:'';
  return `<section class="match-card-v2-header">
    <div class="match-card-v2-league"><div>${leagueMedia}</div><span>${esc(f.round||'Тур не подтверждён')}</span></div>
    <div class="match-card-v2-matchup">
      <div class="match-card-v2-team">${media(f.home?.logo_url,'match-card-v2-crest','Логотип хозяев')}<strong>${esc(f.home?.name||'Хозяева')}</strong>${redCards(f.home?.red_cards)}</div>
      <div class="match-card-v2-center"><div class="match-card-v2-score">${center}</div><div class="match-card-v2-status">${esc(formatMatchCardStatus(status))}${liveMeta}</div></div>
      <div class="match-card-v2-team away">${media(f.away?.logo_url,'match-card-v2-crest','Логотип гостей')}<strong>${esc(f.away?.name||'Гости')}</strong>${redCards(f.away?.red_cards)}</div>
    </div>
    <div class="match-card-v2-meta">${badge(`Freshness: ${freshness}`,freshnessTone)}${f.source_status?badge(f.source_status):''}${f.observed_at_utc?`<span>Снимок ${esc(fmtMoscow(f.observed_at_utc))}</span>`:''}${f.live_observed_at_utc?`<span>LIVE ${esc(fmtMoscow(f.live_observed_at_utc))}</span>`:''}</div>
  </section>`;
}

function motivation(payload){
  const m=payload?.motivation||{};if(!m.available)return section('Мотивация / турнирный контекст',empty('Турнирная мотивация пока недоступна.'));
  const team=(label,x={})=>`<div class="match-card-v2-team-context"><span>${esc(label)}</span><strong>${esc(x.primary_context||'UNKNOWN')}</strong><div>${badge(`Давление: ${x.pressure||'UNKNOWN'}`,String(x.pressure||'').toLowerCase()==='high'?'warn':'neutral')}</div>${x.season_phase?`<small>Фаза сезона: ${esc(x.season_phase)}</small>`:''}${list(x.reason_codes).length?`<div class="match-card-v2-reasons">${list(x.reason_codes).map(code=>badge(code)).join('')}</div>`:''}</div>`;
  const s=m.standings_context||{};return section('Мотивация / турнирный контекст',`<div class="match-card-v2-two">${team('Хозяева',m.home)}${team('Гости',m.away)}</div><div class="match-card-v2-trust">${badge('Снимок до матча · без future leakage','good')}${s.snapshot_observed_at_utc?`<span>Standings: ${esc(fmtMoscow(s.snapshot_observed_at_utc))}</span>`:''}${s.requested_as_of_utc?`<span>Cutoff: ${esc(fmtMoscow(s.requested_as_of_utc))}</span>`:''}</div>`);
}

function prediction(payload){const p=payload?.prediction||{};const items=list(p.items);if(!items.length)return section('Оценка ПБК',empty('Для этого матча нет валидированной probability-записи.'));
  return section('Оценка ПБК',`<div class="match-card-v2-list">${items.map(x=>`<div class="match-card-v2-row"><div><strong>${esc(x.rule||'R')} · ${esc(x.selection||'—')}</strong><small>${esc(x.model_version||'model')} · ${esc(x.status||'frozen prematch')}</small></div><div class="match-card-v2-probs"><span>Вероятность ПБК <b>${fmtPct(x.p_pbk)}</b></span><span>Рынок без маржи <b>${fmtPct(x.p_market_no_vig)}</b></span></div></div>`).join('')}</div><div class="match-card-v2-note">Вероятность ≠ value и не создаёт новый сигнал.</div>`);
}

function odds(payload){const items=list(payload?.odds?.items);if(!items.length)return section('Коэффициенты',empty('Коэффициенты для этой карточки пока не собраны.'));
  return section('Коэффициенты',`<div class="match-card-v2-list">${items.map(x=>`<div class="match-card-v2-row"><div><strong>${esc(x.rule||'R')} · ${esc(x.selection||'—')}</strong><small>${x.captured_at_utc?`Снимок ${esc(fmtMoscow(x.captured_at_utc,false))}`:'Снимок неизвестен'}</small></div><div class="match-card-v2-odds"><b>${fmtNum(x.best_odds)}</b><span>${esc(x.best_book||'—')}</span><small>user ${fmtNum(x.user_best_odds)} ${x.user_best_book?`@ ${esc(x.user_best_book)}`:''} · Bet365 ${fmtNum(x.bet365_odds)}</small></div></div>`).join('')}</div><div class="match-card-v2-note">Наблюдение рынка, не автоматическая рекомендация.</div>`);
}

function fixtureMini(title,x={}){if(!x||(!x.opponent&&!x.fixture_id&&!x.date_utc))return `<div class="match-card-v2-mini"><span>${esc(title)}</span><b>Нет подтверждённых данных</b></div>`;return `<div class="match-card-v2-mini"><span>${esc(title)}</span><b>${esc(x.opponent||'Соперник не указан')}</b><small>${x.date_utc?esc(fmtMoscow(x.date_utc)):''}${x.competition?` · ${esc(x.competition)}`:''}${x.hours_to_next!==null&&x.hours_to_next!==undefined?` · через ${esc(x.hours_to_next)} ч`:''}${String(x.is_uefa_or_cup||'').toUpperCase()==='YES'?' · UEFA/кубок':''}</small></div>`}
function context(payload){const c=payload?.context||{};if(!c.available)return section('Контекст матча',empty('Нет подтверждённых данных по контексту матча.'));
  const v=c.venue||{},rest=c.rest_hours||{},prev=c.previous_fixture||{},next=c.next_fixture||{};return section('Контекст матча',`<div class="match-card-v2-facts"><div><span>Судья</span><b>${esc(c.referee||'—')}</b></div><div><span>Стадион</span><b>${esc(v.name||'—')}</b><small>${esc(v.city||'')}</small></div><div><span>Отдых хозяев</span><b>${fmtNum(rest.home,' ч')}</b></div><div><span>Отдых гостей</span><b>${fmtNum(rest.away,' ч')}</b></div></div><div class="match-card-v2-two">${fixtureMini('Предыдущий матч · хозяева',prev.home)}${fixtureMini('Предыдущий матч · гости',prev.away)}${fixtureMini('Следующий матч · хозяева',next.home)}${fixtureMini('Следующий матч · гости',next.away)}</div>`)}

function playerName(item){if(typeof item==='string')return item;if(!item||typeof item!=='object')return '';return item.name||item.player_name||item.player?.name||item.player||''}
function injuryLabel(item){if(typeof item==='string')return item;if(!item||typeof item!=='object')return '';const name=item.player_name||item.name||item.player?.name||item.player||'Игрок';const reason=item.reason||item.type||item.injury||item.detail||'';return `${name}${reason?` · ${reason}`:''}`}
function squad(payload){const c=payload?.context||{},l=c.lineups||{},inj=c.injuries||{};const injuryItems=list(inj.items).map(injuryLabel).filter(Boolean);const lineup=(label,formation,coach,xi)=>`<div class="match-card-v2-lineup"><span>${esc(label)}</span><strong>${esc(formation||'Схема не подтверждена')}</strong><small>${coach?`Тренер: ${esc(coach)}`:'Тренер не подтверждён'}</small>${list(xi).length?`<ol>${list(xi).map(item=>playerName(item)).filter(Boolean).map(name=>`<li>${esc(name)}</li>`).join('')}</ol>`:empty('Стартовый XI не подтверждён.')}</div>`;
  const body=`<div class="match-card-v2-injuries"><b>Потери</b><span>Всего ${fmtNum(inj.total)} · хозяева ${fmtNum(inj.home)} · гости ${fmtNum(inj.away)}</span>${injuryItems.length?`<ul>${injuryItems.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}</div>${l.available?`<div class="match-card-v2-two">${lineup('Хозяева',l.home_formation,l.home_coach,l.home_start_xi)}${lineup('Гости',l.away_formation,l.away_coach,l.away_start_xi)}</div>`:empty('Подтверждённые составы ещё не получены.')}`;
  return section('Составы / потери',body);
}

function radar(payload){const r=payload?.value_radar||{},items=list(r.items);if(!items.length)return section('Value Radar',empty('Независимых radar-событий по матчу нет.'),'research');
  return section('Value Radar',`<div class="match-card-v2-research-label">Research only · не новый сигнал</div><div class="match-card-v2-list">${items.map(x=>`<div class="match-card-v2-row"><div><strong>${esc(x.primary_rule||'R')} · ${esc(x.selection||'—')}</strong><small>${esc(x.radar_kind||'RADAR')} · ${esc(x.probability_status||'')}</small></div><div class="match-card-v2-radar"><span>ПБК ${fmtPct(x.p_pbk_pct??x.p_pbk)}</span><span>рынок ${fmtPct(x.p_market_pct??x.p_market_no_vig)}</span><span>edge ${fmtNum(x.edge_pp,' п.п.')}</span><span>EV ${fmtPct(x.ev_pct??x.ev)}</span><b>${fmtNum(x.executable_odds)} ${x.executable_bookmaker?`@ ${esc(x.executable_bookmaker)}`:''}</b></div></div>`).join('')}</div><div class="match-card-v2-note">creates_signal=false · stake_changes=false</div>`,'research');
}

function canonical(payload){const items=list(payload?.canonical?.items);if(!items.length)return section('Canonical / Forward',empty('Canonical-сигнала по матчу нет.'),'canonical');
  return section('Canonical / Forward',`<div class="match-card-v2-list">${items.map(x=>`<div class="match-card-v2-row"><div><strong>${esc(x.rule||'R')} · ${esc(x.selection||'—')}</strong><small>${esc(x.status||'')} ${x.result?`· ${esc(x.result)}`:''}</small></div><div class="match-card-v2-canonical"><b>${fmtNum(x.stake_u,'u')}</b><span>${x.paper_user_execution_odds?`paper ${fmtNum(x.paper_user_execution_odds)} ${x.paper_user_execution_bookmaker?`@ ${esc(x.paper_user_execution_bookmaker)}`:''}`:'paper —'}</span>${x.notes?`<small>${esc(x.notes)}</small>`:''}</div></div>`).join('')}</div>`,'canonical');
}

export function matchCardCoverage(payload={}){const c=payload.coverage||{},limitations=list(c.limitations);return {status:c.status||'PARTIAL',limitations,sections:c.sections||{}}}
function coverage(payload){const c=matchCardCoverage(payload),available=String(c.status).toUpperCase()==='AVAILABLE';const labels={MOTIVATION_UNAVAILABLE:'Мотивация',CONTEXT_UNAVAILABLE:'Контекст',PREDICTION_UNAVAILABLE:'Probability',ODDS_UNAVAILABLE:'Коэффициенты',VALUE_RADAR_UNAVAILABLE:'Value Radar',CANONICAL_UNAVAILABLE:'Canonical'};return section('Coverage / качество данных',`<div class="match-card-v2-coverage ${available?'good':'partial'}"><strong>${available?'Карточка собрана полностью':'Часть разделов недоступна'}</strong>${c.limitations.length?`<div>${c.limitations.map(x=>badge(labels[x]||x,'warn')).join('')}</div>`:''}</div><div class="match-card-v2-safety">Read-only · без прямого provider polling · модель и eligibility не изменяются</div>`)}

export function matchCardHeading(payload={}){const f=payload.fixture||{};return {title:`${f.home?.name||'—'} — ${f.away?.name||'—'}`,eyebrow:`${f.league_name||'Матч'}${f.round?` · ${f.round}`:''}`}}
export function renderMatchCardLoading(){return '<div class="match-card-v2-loading">Собираю Match Card v2…</div>'}
export function renderMatchCardError(message){return `<div class="match-card-v2-error">Не удалось открыть карточку: ${esc(message||'ошибка')}</div>`}
export function renderMatchCard(payload={}){return `<div class="match-card-v2">${header(payload)}${motivation(payload)}${prediction(payload)}${odds(payload)}${context(payload)}${squad(payload)}${radar(payload)}${canonical(payload)}${coverage(payload)}</div>`}
