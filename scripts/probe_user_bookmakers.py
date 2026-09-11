#!/usr/bin/env python3
import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE='https://v3.football.api-sports.io'
OPS=Path(os.getenv('OPS_DIR','ops'))
NAMES=['Fonbet','Betera','Parimatch','Marathonbet']

def api(path, params):
    key=os.environ['API_FOOTBALL_KEY'].strip()
    q=urllib.parse.urlencode(params)
    req=urllib.request.Request(BASE+path+'?'+q,headers={'x-apisports-key':key,'User-Agent':'pbk-bookmaker-probe/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

def main():
    OPS.mkdir(parents=True,exist_ok=True)
    out=[]
    for name in NAMES:
        try:
            d=api('/odds/bookmakers',{'search':name})
            resp=d.get('response') or []
            out.append({'query':name,'matches':[{'id':x.get('id'),'name':x.get('name')} for x in resp],'errors':d.get('errors') or []})
        except Exception as e:
            out.append({'query':name,'matches':[],'error':str(e)})
    payload={'run_at_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),'status':'OK','results':out}
    (OPS/'bookmaker_probe.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
