import { leagueOptions } from './markets.js';
import './install.js';
const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
let refreshing=false;
function fillLeagues(){const sel=$('#filter-league');if(!sel)return;const current=sel.value;const next=leagueOptions($$('#all-market-cards .match-card'));const existing=[...sel.options].slice(1).map(o=>o.value);if(JSON.stringify(existing)===JSON.stringify(next))return;sel.replaceChildren(new Option('Все лиги',''),...next.map(x=>new Option(x,x)));sel.value=next.includes(current)?current:''}
function apply(){if(refreshing)return;refreshing=true;fillLeagues();const rule=$('#filter-rule')?.value||'';const watch=$('#filter-watch')?.value||'';const league=$('#filter-league')?.value||'';const market=$('#filter-market')?.value||'';
  $$('#signals-list .card').forEach(c=>{const eyebrow=c.querySelector('.eyebrow')?.textContent||'';c.classList.toggle('filtered-out',!!rule&&!eyebrow.includes(rule))});
  $$('#watch-list .card').forEach(c=>{const eyebrow=c.querySelector('.eyebrow')?.textContent||'';c.classList.toggle('filtered-out',!!watch&&!eyebrow.includes(watch))});
  $$('#all-market-cards .match-card').forEach(c=>{const leagueOk=!league||c.dataset.league===league;c.classList.toggle('filtered-out',!leagueOk);c.querySelectorAll('[data-market]').forEach(row=>row.classList.toggle('filtered-out',!!market&&row.dataset.market!==market))});refreshing=false}
['filter-rule','filter-watch','filter-league','filter-market'].forEach(id=>document.addEventListener('change',e=>{if(e.target?.id===id)apply()}));
document.addEventListener('click',e=>{if(e.target?.id==='filters-reset'){['filter-rule','filter-watch','filter-league','filter-market'].forEach(id=>{const x=$('#'+id);if(x)x.value=''});apply()}});
const obs=new MutationObserver(()=>queueMicrotask(apply));['signals-list','watch-list','all-market-cards'].forEach(id=>{const el=$('#'+id);if(el)obs.observe(el,{childList:true,subtree:true})});
setTimeout(apply,250);
