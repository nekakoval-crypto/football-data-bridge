import csv, io, json, math, os, re, time, gzip, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

SEASON_CODES=["1920","2021","2122","2223","2324","2425","2526"]
DIVS={"E0":("Premier League","GB","GB1"),"SP1":("La Liga","ES","ES1"),"I1":("Serie A","IT","IT1"),"D1":("Bundesliga","DE","L1"),"F1":("Ligue 1","FR","FR1")}
SL={"1920":"2019/20","2021":"2020/21","2122":"2021/22","2223":"2022/23","2324":"2023/24","2425":"2024/25","2526":"2025/26"}
CCNAME={"GB":"United Kingdom","ES":"Spain","IT":"Italy","DE":"Germany","FR":"France"}
UA="football-data-bridge-stage43-v2/1.0"

def req_bytes(url,timeout=120,retries=4):
    last=None
    for i in range(retries):
        try:
            q=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(q,timeout=timeout) as r:return r.read()
        except Exception as e:
            last=e; time.sleep(min(5,1+i))
    raise last

def req_json(url,timeout=120,retries=4):
    return json.loads(req_bytes(url,timeout,retries).decode("utf-8"))

def decode(b):
    for enc in ("utf-8-sig","cp1252","latin-1"):
        try:return b.decode(enc)
        except:pass
    return b.decode("utf-8",errors="replace")

def norm(s):
    s=(s or "").lower().replace("&","and")
    s=re.sub(r"\b(fc|cf|calcio|football club|club de futbol|club|afc|ac|as|ssc|ss|sv|vfb|vfl|1899|1909|1910|1904|1905|1907|1908|1919|1920|1924|1927|1929|1946)\b"," ",s)
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return " ".join(s.split())

def sim(a,b):
    a=norm(a); b=norm(b)
    if not a or not b:return 0
    if a==b:return 1
    return SequenceMatcher(None,a,b).ratio()

def pdate(s):
    for fmt in ("%d/%m/%Y","%d/%m/%y","%Y-%m-%d"):
        try:return datetime.strptime((s or '').strip(),fmt).date()
        except:pass
    raise ValueError(s)

def ptime(s):
    for fmt in ("%H:%M","%H.%M"):
        try:return datetime.strptime((s or '').strip(),fmt).time()
        except:pass
    return None

def geocode(q,cc):
    params=urllib.parse.urlencode({"q":q,"format":"jsonv2","limit":1,"countrycodes":cc.lower()})
    try:
        d=req_json("https://nominatim.openstreetmap.org/search?"+params,45,2)
        if d:
            x=d[0]; return float(x['lat']),float(x['lon']),x.get('display_name','')
    except:pass
    return None

def weather(lat,lon,start,end):
    hourly="temperature_2m,relative_humidity_2m,precipitation,rain,snowfall,wind_speed_10m,wind_gusts_10m,weather_code"
    p={"latitude":f"{lat:.5f}","longitude":f"{lon:.5f}","start_date":str(start),"end_date":str(end),"hourly":hourly,"timezone":"auto","wind_speed_unit":"kmh","precipitation_unit":"mm","models":"era5_land"}
    try:return req_json("https://archive-api.open-meteo.com/v1/archive?"+urllib.parse.urlencode(p),120,4)
    except:
        p.pop('models',None); return req_json("https://archive-api.open-meteo.com/v1/archive?"+urllib.parse.urlencode(p),120,4)

def avg(xs):
    x=[v for v in xs if isinstance(v,(int,float)) and math.isfinite(v)]; return sum(x)/len(x) if x else None

def sm(xs):
    x=[v for v in xs if isinstance(v,(int,float)) and math.isfinite(v)]; return sum(x) if x else None

def mx(xs):
    x=[v for v in xs if isinstance(v,(int,float)) and math.isfinite(v)]; return max(x) if x else None

os.makedirs('out_v2',exist_ok=True)
# Football-Data matches
fd=[]
for sc in SEASON_CODES:
  for div,(league,cc,tmcomp) in DIVS.items():
    url=f"https://www.football-data.co.uk/mmz4281/{sc}/{div}.csv"
    rd=csv.DictReader(io.StringIO(decode(req_bytes(url))))
    for r in rd:
      try:d=pdate(r.get('Date'))
      except:continue
      kt=ptime(r.get('Time'))
      if not kt:continue
      fd.append({"season":SL[sc],"tm_season":int('20'+sc[:2]) if sc!='1920' else 2019,"league":league,"cc":cc,"tmcomp":tmcomp,"date":str(d),"time":kt.strftime('%H:%M'),"home":(r.get('HomeTeam')or'').strip(),"away":(r.get('AwayTeam')or'').strip(),"hg":r.get('FTHG',''),"ag":r.get('FTAG',''),"source_url":url})
print('fd',len(fd))

# Transfermarkt games
raw=req_bytes('https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz',180)
tm=[]; bykey=defaultdict(list)
with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
    text=io.TextIOWrapper(gz,encoding='utf-8-sig',newline='')
    for r in csv.DictReader(text):
        if r.get('competition_id') not in {x[2] for x in DIVS.values()}:continue
        try:sy=int(r.get('season','-1'))
        except:continue
        if sy<2019 or sy>2025:continue
        key=(r.get('competition_id'),r.get('date'))
        bykey[key].append(r)

# match and stadium
unmatched=[]
for m in fd:
    cand=bykey.get((m['tmcomp'],m['date']),[])
    best=None; bs=-1
    for r in cand:
        score=sim(m['home'],r.get('home_club_name'))+sim(m['away'],r.get('away_club_name'))
        try:
            if m['hg']!='' and m['ag']!='' and int(float(m['hg']))==int(float(r.get('home_club_goals'))) and int(float(m['ag']))==int(float(r.get('away_club_goals'))):score+=1.2
        except:pass
        if score>bs:bs=score; best=r
    if best is not None and bs>=1.25:
        m['tm_game_id']=best.get('game_id',''); m['stadium']=best.get('stadium',''); m['tm_home']=best.get('home_club_name',''); m['tm_away']=best.get('away_club_name',''); m['match_score']=bs
    else:
        m['tm_game_id']='';m['stadium']='';m['tm_home']='';m['tm_away']='';m['match_score']=bs;unmatched.append(m)
print('tm matched',len(fd)-len(unmatched),'unmatched',len(unmatched))

# Stadium geolocation dataset
stad_text=decode(req_bytes('https://raw.githubusercontent.com/dvd23m/Football_Stadiums_Map/main/stadiums_geloc.csv'))
stad_rows=list(csv.DictReader(io.StringIO(stad_text)))
by_stad=defaultdict(list)
for r in stad_rows:by_stad[norm(r.get('name_of_stadium'))].append(r)

venue_keys=sorted(set((m['league'],m['cc'],m['home'],m.get('tm_home',''),m.get('stadium','')) for m in fd))
coords={}
for i,(league,cc,home,tmhome,stadium) in enumerate(venue_keys,1):
    choices=by_stad.get(norm(stadium),[]) if stadium else []
    pick=None; source=''
    if choices:
        pick=max(choices,key=lambda r:max(sim(home,r.get('club')),sim(tmhome,r.get('club'))))
        if max(sim(home,pick.get('club')),sim(tmhome,pick.get('club')))>=0.35:
            try:
                coords[(league,home)]={"lat":float(pick['lat']),"lon":float(pick['lon']),"source":"stadium_dataset","detail":pick.get('club','')+' | '+pick.get('name_of_stadium','')}
                continue
            except:pass
    # fuzzy stadium fallback among dataset if strong
    if stadium:
        ns=norm(stadium); top=[]
        for r in stad_rows:
            s=SequenceMatcher(None,ns,norm(r.get('name_of_stadium'))).ratio() if ns else 0
            if s>=0.88: top.append((s,r))
        if top:
            top.sort(key=lambda x:(x[0],max(sim(home,x[1].get('club')),sim(tmhome,x[1].get('club')))),reverse=True)
            s,pick=top[0]
            if max(sim(home,pick.get('club')),sim(tmhome,pick.get('club')))>=0.35:
                try:
                    coords[(league,home)]={"lat":float(pick['lat']),"lon":float(pick['lon']),"source":"stadium_dataset_fuzzy","detail":pick.get('club','')+' | '+pick.get('name_of_stadium','')}
                    continue
                except:pass
    # network geocoder only for unresolved
    qs=[]
    if stadium:qs.append(f"{stadium}, {CCNAME[cc]}")
    if tmhome:qs.append(f"{tmhome} football stadium, {CCNAME[cc]}")
    qs.append(f"{home} football stadium, {CCNAME[cc]}")
    for q in qs:
        g=geocode(q,cc)
        if g:
            coords[(league,home)]={"lat":g[0],"lon":g[1],"source":"nominatim_fallback","detail":g[2]};break
        time.sleep(1.05)
    print('coord',i,'/',len(venue_keys),home,coords.get((league,home)))

with open('out_v2/stage43_team_coordinates.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['league','team','latitude','longitude','coordinate_source','detail'])
    for (league,home),g in sorted(coords.items()):w.writerow([league,home,g['lat'],g['lon'],g['source'],g['detail']])

# group team-season and fetch weather concurrently
groups=defaultdict(list)
for m in fd:groups[(m['league'],m['season'],m['home'])].append(m)

def do_group(item):
    key,gm=item; league,season,home=key; g=coords.get((league,home))
    if not g:return key,None,'coord_failed'
    ds=[datetime.fromisoformat(x['date']).date() for x in gm]
    try:return key,weather(g['lat'],g['lon'],min(ds)-timedelta(days=1),max(ds)+timedelta(days=1)),''
    except Exception as e:return key,None,str(e)

weather_by={};errors=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    fut={ex.submit(do_group,it):it[0] for it in groups.items()}
    for n,fu in enumerate(as_completed(fut),1):
        key,data,err=fu.result(); weather_by[key]=data
        if err:errors.append((key,err))
        if n%25==0:print('weather groups',n,'/',len(groups),'errors',len(errors))

out=[]
for m in fd:
    key=(m['league'],m['season'],m['home']); data=weather_by.get(key); g=coords.get((m['league'],m['home']))
    z=dict(m);z.update({'weather_ok':0,'weather_error':''})
    if g:z.update({'latitude':g['lat'],'longitude':g['lon'],'coordinate_source':g['source'],'coordinate_detail':g['detail']})
    if not data:
        z['weather_error']='weather_or_coordinate_failed';out.append(z);continue
    h=data.get('hourly',{}); idx={t:i for i,t in enumerate(h.get('time',[]))}
    kick=datetime.fromisoformat(m['date']+'T'+m['time']);floor=kick.replace(minute=0,second=0,microsecond=0);nearest=floor if kick.minute<30 else floor+timedelta(hours=1)
    ids=[idx.get((floor+timedelta(hours=j)).strftime('%Y-%m-%dT%H:%M')) for j in range(3)];ids=[i for i in ids if i is not None];ni=idx.get(nearest.strftime('%Y-%m-%dT%H:%M'))
    def ar(k):return h.get(k,[])
    def vals(k):return [ar(k)[i] for i in ids if i<len(ar(k))]
    z.update({'weather_ok':1,'timezone':data.get('timezone',''),
      'temperature_kickoff_c':ar('temperature_2m')[ni] if ni is not None and ni<len(ar('temperature_2m')) else None,
      'temperature_match_avg_c':avg(vals('temperature_2m')),'humidity_match_avg_pct':avg(vals('relative_humidity_2m')),
      'precipitation_match_sum_mm':sm(vals('precipitation')),'rain_match_sum_mm':sm(vals('rain')),'snowfall_match_sum_cm':sm(vals('snowfall')),
      'wind_match_avg_kmh':avg(vals('wind_speed_10m')),'wind_match_max_kmh':mx(vals('wind_speed_10m')),'gust_match_max_kmh':mx(vals('wind_gusts_10m')),
      'weather_code_kickoff':ar('weather_code')[ni] if ni is not None and ni<len(ar('weather_code')) else None})
    out.append(z)

fields=['season','league','cc','date','time','home','away','hg','ag','source_url','tm_game_id','stadium','tm_home','tm_away','match_score','weather_ok','weather_error','latitude','longitude','coordinate_source','coordinate_detail','timezone','temperature_kickoff_c','temperature_match_avg_c','humidity_match_avg_pct','precipitation_match_sum_mm','rain_match_sum_mm','snowfall_match_sum_cm','wind_match_avg_kmh','wind_match_max_kmh','gust_match_max_kmh','weather_code_kickoff']
with open('out_v2/stage43_match_weather.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();
    for r in out:w.writerow({k:r.get(k,'') for k in fields})
with open('out_v2/stage43_errors.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['league','season','team','error']);
    for (lg,se,te),e in errors:w.writerow([lg,se,te,e])
with open('out_v2/stage43_match_join_unmatched.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['season','league','date','time','home','away','hg','ag','match_score']);w.writeheader();
    for r in unmatched:w.writerow({k:r.get(k,'') for k in w.fieldnames})
print('DONE rows',len(out),'weather ok',sum(int(x.get('weather_ok',0)) for x in out),'coords',len(coords),'groups errors',len(errors))
