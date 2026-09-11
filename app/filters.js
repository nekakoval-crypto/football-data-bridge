const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
let refreshing=false;
function fillLeagues(){const sel=$('#filter-league');if(!sel)return;const current=sel.value;const leagues=new Set();$$('#all-market-cards .match-card .eyebrow').forEach(e=>{const league=(e.textContent||'').split('·')[0].trim();if(league)leagues.add(league)});const existing=[...sel.options].slice(1).map(o=>o.value);const next=[...leagues].sort((a,b)=>a.localeCompare(b,'ru'));if(JSON.stringify(existing)===JSON.stringify(next))return;sel.innerHTML='<option value="">Все лиги</option>'+next.map(x=>`<option value="${x.replace(/"/g,'&quot;')}">${x}</option>`).join('');sel.value=next.includes(current)?current:''}
function apply(){if(refreshing)return;refreshing=true;fillLeagues();const rule=$('#filter-rule')?.value||'';const watch=$('#filter-watch')?.value||'';const league=$('#filter-league')?.value||'';const market=$('#filter-market')?.value||'';
  $$('#signals-list .card').forEach(c=>{const eyebrow=c.querySelector('.eyebrow')?.textContent||'';c.classList.toggle('filtered-out',!!rule&&!eyebrow.includes(rule))});
  $$('#watch-list .card').forEach(c=>{const eyebrow=c.querySelector('.eyebrow')?.textContent||'';c.classList.toggle('filtered-out',!!watch&&!eyebrow.includes(watch))});
  const marketRx={TEAM_TOTAL:/ИТБ|ИТМ/i,DOUBLE_CHANCE:/1Х|Х2|\b12\b/i,DNB:/Ф1\(0\)|Ф2\(0\)/i,EUROPEAN_HANDICAP:/Европ/i}[market];
  $$('#all-market-cards .match-card').forEach(c=>{const eyebrow=c.querySelector('.eyebrow')?.textContent||'';const text=c.textContent||'';const leagueOk=!league||eyebrow.startsWith(league);const marketOk=!marketRx||marketRx.test(text);c.classList.toggle('filtered-out',!(leagueOk&&marketOk))});refreshing=false}
['filter-rule','filter-watch','filter-league','filter-market'].forEach(id=>document.addEventListener('change',e=>{if(e.target?.id===id)apply()}));
document.addEventListener('click',e=>{if(e.target?.id==='filters-reset'){['filter-rule','filter-watch','filter-league','filter-market'].forEach(id=>{const x=$('#'+id);if(x)x.value=''});apply()}});
const obs=new MutationObserver(()=>queueMicrotask(apply));['signals-list','watch-list','all-market-cards'].forEach(id=>{const el=$('#'+id);if(el)obs.observe(el,{childList:true,subtree:true})});
setTimeout(apply,250);
