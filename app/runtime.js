const runtimePanel=document.querySelector('#runtime-panel');
const runtimeBadge=document.querySelector('#runtime-badge');
const fmt=(v,s='')=>v===null||v===undefined||v===''?'—':`${v}${s}`;
const escRuntime=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

function renderRuntime(x){
  if(!runtimePanel)return;
  const commit=String(x.release_commit||'UNTRACKED');
  const shortCommit=commit==='UNTRACKED'?commit:commit.slice(0,8);
  const usedMem=x.memory_total_mb&&x.memory_available_mb?Math.max(0,x.memory_total_mb-x.memory_available_mb):null;
  const memPct=x.memory_total_mb&&usedMem!==null?Math.round(usedMem/x.memory_total_mb*100):null;
  const diskPct=x.disk_total_gb?Math.round((x.disk_total_gb-x.disk_free_gb)/x.disk_total_gb*100):null;
  runtimePanel.innerHTML=`<div class="health-grid">
    <div class="health-item"><span>Production</span><b>${escRuntime(x.status||'—')}</b></div>
    <div class="health-item"><span>API version</span><b>${escRuntime(x.api_version||'—')}</b></div>
    <div class="health-item"><span>Release</span><b>${escRuntime(shortCommit)}</b></div>
    <div class="health-item"><span>API uptime</span><b>${escRuntime(fmt(Math.round((x.api_process_uptime_seconds||0)/60),' мин'))}</b></div>
    <div class="health-item"><span>RAM</span><b>${escRuntime(memPct===null?'—':`${memPct}%`)}</b></div>
    <div class="health-item"><span>Disk</span><b>${escRuntime(diskPct===null?'—':`${diskPct}%`)}</b></div>
    <div class="health-item"><span>Свободно RAM</span><b>${escRuntime(fmt(x.memory_available_mb,' MB'))}</b></div>
    <div class="health-item"><span>Свободно диска</span><b>${escRuntime(fmt(x.disk_free_gb,' GB'))}</b></div>
    <div class="health-item"><span>Load 1m</span><b>${escRuntime(fmt(x.load_average_1m))}</b></div>
    <div class="health-item"><span>SQLite</span><b>${escRuntime(fmt(x.db_size_mb,' MB'))}</b></div>
  </div><div class="market-note">Runtime read-only · эти показатели не влияют на eligibility стратегий.</div>`;
  if(runtimeBadge){runtimeBadge.textContent=x.status||'—';runtimeBadge.className=`runtime-badge ${x.status==='OK'?'ok':'bad'}`}
}

async function loadRuntime(){
  try{
    const r=await fetch('/api/v1/runtime',{headers:{Accept:'application/json'},cache:'no-store'});
    if(!r.ok)throw new Error(`${r.status} ${r.statusText}`);
    renderRuntime(await r.json());
  }catch(e){
    if(runtimePanel)runtimePanel.innerHTML=`<div class="empty">Production runtime недоступен: ${escRuntime(e.message)}</div>`;
    if(runtimeBadge){runtimeBadge.textContent='OFFLINE';runtimeBadge.className='runtime-badge bad'}
  }
}
loadRuntime();setInterval(loadRuntime,60000);
