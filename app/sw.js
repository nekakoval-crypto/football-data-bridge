const CACHE='pbk-shell-v9';
const SHELL=['/','/index.html','/app.css','/filters.css','/install.css','/runtime.css','/push.css','/probability.css','/app.js','/markets.js','/filters.js','/install.js','/runtime.js','/push.js','/probability.js','/challengers.js','/challengers.css','/icon.svg','/manifest.webmanifest'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('message',e=>{if(e.data?.type==='SKIP_WAITING')self.skipWaiting()});
self.addEventListener('push',e=>{
  let d={title:'ПБК',body:'Новое событие',url:'/#notifications',severity:'medium'};
  try{if(e.data)d={...d,...e.data.json()}}catch{try{d.body=e.data?.text()||d.body}catch{}}
  const opts={body:d.body||'',icon:'/icon.svg',badge:'/icon.svg',tag:d.id||undefined,renotify:true,data:{url:d.url||'/#notifications',fixture_id:d.fixture_id||''},requireInteraction:d.severity==='high'};
  e.waitUntil(self.registration.showNotification(d.title||'ПБК',opts));
});
self.addEventListener('notificationclick',e=>{
  e.notification.close();const target=e.notification.data?.url||'/#notifications';
  e.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(list=>{for(const c of list){if('focus'in c){c.navigate(target).catch(()=>{});return c.focus()}}return clients.openWindow?clients.openWindow(target):undefined}));
});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.pathname.startsWith('/api/')){e.respondWith(fetch(e.request,{cache:'no-store'}));return}
  if(e.request.method!=='GET'||u.origin!==self.location.origin)return;
  if(e.request.mode==='navigate'){
    e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put('/index.html',copy));return r}).catch(()=>caches.match('/index.html')));return
  }
  e.respondWith(fetch(e.request).then(r=>{if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy))}return r}).catch(()=>caches.match(e.request)));
});
