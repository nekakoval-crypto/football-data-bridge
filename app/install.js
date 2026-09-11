let deferredInstallPrompt=null;
const installBtn=document.querySelector('#install-app');
const updateBtn=document.querySelector('#app-update');
const installHint=document.querySelector('#install-hint');

function isStandalone(){return window.matchMedia('(display-mode: standalone)').matches||window.navigator.standalone===true}
function setInstallState(){
  if(!installBtn)return;
  if(isStandalone()){installBtn.hidden=true;if(installHint)installHint.textContent='ПБК установлена как приложение';return}
  installBtn.hidden=false;
  installBtn.disabled=!deferredInstallPrompt;
  installBtn.textContent=deferredInstallPrompt?'Установить ПБК':'Как установить';
}

window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferredInstallPrompt=e;setInstallState()});
window.addEventListener('appinstalled',()=>{deferredInstallPrompt=null;setInstallState()});

installBtn?.addEventListener('click',async()=>{
  if(deferredInstallPrompt){
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt=null;setInstallState();return;
  }
  const android=/Android/i.test(navigator.userAgent);
  const ios=/iPhone|iPad|iPod/i.test(navigator.userAgent);
  let msg='На ПК: открой меню браузера и выбери «Установить ПБК» / «Установить приложение». На Android: меню браузера → «Установить приложение» или «Добавить на главный экран».';
  if(android)msg='Android: открой меню браузера (⋮) → «Установить приложение» или «Добавить на главный экран».';
  if(ios)msg='iPhone/iPad: кнопка «Поделиться» → «На экран Домой». Полная PWA-поддержка зависит от версии iOS.';
  alert(msg);
});

async function registerSW(){
  if(!('serviceWorker' in navigator))return;
  try{
    const reg=await navigator.serviceWorker.register('/sw.js',{scope:'/'});
    if(reg.waiting)showUpdate(reg);
    reg.addEventListener('updatefound',()=>{
      const nw=reg.installing;if(!nw)return;
      nw.addEventListener('statechange',()=>{if(nw.state==='installed'&&navigator.serviceWorker.controller)showUpdate(reg)});
    });
    navigator.serviceWorker.addEventListener('controllerchange',()=>window.location.reload());
  }catch(err){console.warn('PBK service worker registration failed',err)}
}
function showUpdate(reg){
  if(!updateBtn)return;updateBtn.hidden=false;
  updateBtn.onclick=()=>{if(reg.waiting)reg.waiting.postMessage({type:'SKIP_WAITING'});else window.location.reload()};
}

setInstallState();registerSW();
