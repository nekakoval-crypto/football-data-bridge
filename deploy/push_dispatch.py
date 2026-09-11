#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path('/opt/pbk')
REPO=ROOT/'repo'
DATA=Path(os.getenv('PBK_PUSH_DATA_DIR',str(ROOT/'data')))
SUBS=DATA/'push_subscriptions.json'
SENT=DATA/'push_sent.json'
PRIVATE=DATA/'vapid_private.pem'
sys.path.insert(0,str(REPO/'scripts'))
os.environ.setdefault('PBK_DB_PATH',str(DATA/'pbk_unified.sqlite'))

from pywebpush import webpush, WebPushException
import stage74_app_api as appapi


def load_json(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError):return default

def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(obj,f,ensure_ascii=False,separators=(',',':'))
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass

def vapid_subject():
    host=os.getenv('PBK_HOST','localhost').replace('https://','').replace('http://','').split('/')[0]
    return os.getenv('PBK_VAPID_SUBJECT') or f'mailto:pbk@{host}'

def main():
    subscriptions=load_json(SUBS,[])
    if not subscriptions:
        print('PBK PUSH: no subscriptions')
        return 0
    if not PRIVATE.exists():
        print('PBK PUSH: VAPID private key missing',file=sys.stderr)
        return 1

    _,payload=appapi.notifications_payload(200)
    items=payload.get('items') or []
    current_ids=[str(x.get('id') or '') for x in items if x.get('id')]
    state=load_json(SENT,{})
    sent=list(state.get('sent_ids') or [])
    sent_set=set(sent)

    # First dispatcher run establishes a baseline so old notifications are not blasted to a new device.
    if not state.get('initialized'):
        atomic_json(SENT,{
            'initialized':True,
            'initialized_at_utc':datetime.now(timezone.utc).isoformat(),
            'sent_ids':current_ids[-1000:],
        })
        print(f'PBK PUSH: baseline initialized with {len(current_ids)} existing notifications')
        return 0

    new_items=[x for x in reversed(items) if x.get('id') and str(x['id']) not in sent_set]
    if not new_items:
        print('PBK PUSH: no new notifications')
        return 0

    active=[]
    delivered_ids=[]
    for entry in subscriptions:
        sub=entry.get('subscription') if isinstance(entry,dict) else None
        if not isinstance(sub,dict) or not sub.get('endpoint'):
            continue
        dead=False
        for item in new_items:
            data=json.dumps({
                'id':item.get('id'),
                'title':item.get('title') or 'ПБК',
                'body':item.get('body') or '',
                'category':item.get('category') or '',
                'severity':item.get('severity') or 'medium',
                'fixture_id':item.get('fixture_id') or '',
                'url':'/#notifications',
            },ensure_ascii=False,separators=(',',':'))
            try:
                webpush(
                    subscription_info=sub,
                    data=data,
                    vapid_private_key=str(PRIVATE),
                    vapid_claims={'sub':vapid_subject()},
                    ttl=300,
                )
                delivered_ids.append(str(item['id']))
            except WebPushException as e:
                code=getattr(getattr(e,'response',None),'status_code',None)
                if code in (404,410):
                    dead=True
                    print(f'PBK PUSH: removing expired subscription ({code})')
                    break
                print(f'PBK PUSH: send failed ({code or "error"}): {e}',file=sys.stderr)
        if not dead:active.append(entry)

    if len(active)!=len(subscriptions):
        atomic_json(SUBS,active)

    if delivered_ids:
        sent.extend(delivered_ids)
        # preserve order and bound state file
        uniq=list(dict.fromkeys(sent))[-1000:]
        atomic_json(SENT,{
            'initialized':True,
            'updated_at_utc':datetime.now(timezone.utc).isoformat(),
            'sent_ids':uniq,
        })
    print(f'PBK PUSH: new={len(new_items)} delivered={len(set(delivered_ids))} subscriptions={len(active)}')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
