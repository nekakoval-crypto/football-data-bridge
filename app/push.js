const pushBtn=document.querySelector('#push-toggle');
const pushState=document.querySelector('#push-state');

function b64urlToBytes(s){
  const pad='='.repeat((4-s.length%4)%4);const b64=(s+pad).replace(/-/g,'+').replace(/_/g,'/');
  const raw=atob(b64);return Uint8Array.from([...raw].map(c=>c.charCodeAt(0)));
}
function setState(text,cls=''){if(pushState){pushState.textContent=text;pushState.className=`push-state ${cls}`}}
async function pushApi(path,opts={}){const r=await fetch(`/api${path}`,{cache:'no-store',headers:{Accept:'application/json','Content-Type':'application/json',...(opts.headers||{})},...opts});if(!r.ok)throw new Error(`${r.status} ${r.statusText}`);return r.json()}

async function currentSubscription(){if(!('serviceWorker'in navigator))return null;const reg=await navigator.serviceWorker.ready;return reg.pushManager.getSubscription()}

async function refreshPushUI(){
  if(!pushBtn)return;
  if(!('Notification'in window)||!('serviceWorker'in navigator)||!('PushManager'in window)){pushBtn.disabled=true;setState('Web Push не поддерживается этим браузером','bad');return}
  try{
    const status=await pushApi('/v1/push/status');
    if(!status.enabled){pushBtn.disabled=true;setState('Push ещё настраивается сервером','warn');return}
    const sub=await currentSubscription();
    if(sub){pushBtn.disabled=false;pushBtn.textContent='Отключить push';pushBtn.dataset.mode='off';setState(`Push включён · устройств: ${status.subscription_count||1}`,'ok')}
    else{pushBtn.disabled=false;pushBtn.textContent='Включить push';pushBtn.dataset.mode='on';setState(Notification.permission==='denied'?'Уведомления запрещены в браузере':'Push готов к включению',Notification.permission==='denied'?'bad':'')}
  }catch(e){pushBtn.disabled=true;setState(`Push недоступен: ${e.message}`,'bad')}
}

async function enablePush(){
  const status=await pushApi('/v1/push/status');if(!status.enabled||!status.public_key)throw new Error('VAPID key unavailable');
  const permission=await Notification.requestPermission();if(permission!=='granted')throw new Error('Разрешение на уведомления не выдано');
  const reg=await navigator.serviceWorker.ready;
  let sub=await reg.pushManager.getSubscription();
  if(!sub)sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64urlToBytes(status.public_key)});
  await pushApi('/v1/push/subscribe',{method:'POST',body:JSON.stringify({subscription:sub.toJSON()})});
}
async function disablePush(){
  const sub=await currentSubscription();if(!sub)return;
  await pushApi('/v1/push/unsubscribe',{method:'POST',body:JSON.stringify({endpoint:sub.endpoint})});
  await sub.unsubscribe();
}

pushBtn?.addEventListener('click',async()=>{
  pushBtn.disabled=true;setState('Обновляю push…');
  try{if(pushBtn.dataset.mode==='off')await disablePush();else await enablePush();await refreshPushUI()}
  catch(e){setState(e.message,'bad');pushBtn.disabled=false}
});
window.addEventListener('focus',refreshPushUI);
refreshPushUI();
