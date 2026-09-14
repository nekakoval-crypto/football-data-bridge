const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

export function selectedTeam(team={}){
  if(!team||typeof team!=='object')team={};
  const official=team.official;
  if(Array.isArray(official?.xi)&&official.xi.length===11)return {...team,...official,starting_xi:official.xi,status:'CONFIRMED'};
  return team;
}

// Coordinates are team-relative: goalkeeper at y=0, attacking end at y=100.
export function positions(team={}){
  if(!team||typeof team!=='object')return [];
  const xi=Array.isArray(team.starting_xi)?team.starting_xi.map(p=>p?.player||p):[];
  if(xi.length!==11||xi.some(p=>!p||typeof p!=='object'))return [];
  const explicit=xi.map(p=>p.position);
  if(explicit.every(p=>p&&Number.isFinite(p.x)&&Number.isFinite(p.y)&&p.x>=0&&p.x<=100&&p.y>=0&&p.y<=100)&&new Set(explicit.map(p=>`${p.x}:${p.y}`)).size===11)
    return xi.map((p,i)=>({...p,x:8+explicit[i].x*.84,y:8+explicit[i].y*.84,basis:'positions'}));
  const grid=xi.map(p=>/^[1-6]:[1-5]$/.test(p.grid||'')?p.grid.split(':').map(Number):null);
  if(grid.every(Boolean)&&new Set(grid.map(p=>p.join(':'))).size===11){
    const rows=[...new Set(grid.map(p=>p[0]))].sort((a,b)=>a-b);
    if(rows.length>=3&&grid.filter(p=>p[0]===rows[0]).length===1)return xi.map((p,i)=>{
      const members=grid.filter(g=>g[0]===grid[i][0]).map(g=>g[1]).sort((a,b)=>a-b);
      return {...p,x:100*(members.indexOf(grid[i][1])+1)/(members.length+1),y:8+84*rows.indexOf(grid[i][0])/(rows.length-1),basis:'grid'};
    });
  }
  const formation=String(team.formation||'');
  if(!/^[1-5](?:-[1-5]){1,4}$/.test(formation))return [];
  const lines=formation.split('-').map(Number);
  if(lines.reduce((a,b)=>a+b,0)!==10)return [];
  const ordered=[...xi].sort((a,b)=>({G:0,D:1,M:2,F:3}[a.pos]??4)-({G:0,D:1,M:2,F:3}[b.pos]??4));
  let i=0;
  return [1,...lines].flatMap((n,row)=>Array.from({length:n},(_,col)=>({...ordered[i++],x:100*(col+1)/(n+1),y:8+84*row/lines.length,basis:'template'})));
}

export function renderPitch(home={},away={}){
  const half=(raw,side)=>{
    const team=selectedTeam(raw),players=positions(team);
    if(!players.length)return `<div class="formation-no-data ${side}">Нет данных по расстановке${team.starting_xi?.length?' · XI доступен списком':''}</div>`;
    return players.map(p=>{
      const name=p.lastname||p.last_name||String(p.name||p.player_name||'—').trim().split(/\s+/).slice(-1)[0];
      const x=side==='home'?p.x:100-p.x,y=side==='home'?p.y/2:100-p.y/2;
      return `<div class="formation-player ${side}" style="left:${x}%;top:${y}%" title="${esc(p.name||name)}"><b>${esc(p.number??'—')}</b><span>${esc(name)}</span></div>`;
    }).join('');
  };
  const template=[home,away].some(t=>positions(selectedTeam(t)).some(p=>p.basis==='template'));
  return `<div class="formation-pitch" role="group" aria-label="Составы: хозяева сверху, гости снизу"><div class="formation-circle" aria-hidden="true"></div><div class="formation-box top" aria-hidden="true"></div><div class="formation-box bottom" aria-hidden="true"></div>${half(home,'home')}${half(away,'away')}</div><div class="match-card-v2-note">Хозяева сверху · гости снизу.${template?' Шаблонные позиции — условная расстановка.':''}</div>`;
}
