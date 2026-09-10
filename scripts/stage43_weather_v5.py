import csv,io,json,math,os,re,time,gzip,urllib.parse,urllib.request
from collections import defaultdict
from datetime import datetime,timedelta
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor,as_completed
SEASON_CODES=['1920','2021','2122','2223','2324','2425','2526']
DIVS={'E0':('Premier League','GB','GB1'),'SP1':('La Liga','ES','ES1'),'I1':('Serie A','IT','IT1'),'D1':('Bundesliga','DE','L1'),'F1':('Ligue 1','FR','FR1')}
SL={'1920':'2019/20','2021':'2020/21','2122':'2021/22','2223':'2022/23','2324':'2023/24','2425':'2024/25','2526':'2025/26'}
UA='football-data-bridge-stage43-v5/1.0'
def req_bytes(url,timeout=120,retries=5):
  last=None
  for i in range(retries):
    try:
      q=urllib.request.Request(url,headers={'User-Agent':UA});
      with urllib.request.urlopen(q,timeout=timeout) as r:return r.read()
    except Exception as e:last=e;time.sleep(min(8,1+2*i))
  raise last
def req_json(url,timeout=120,retries=5):return json.loads(req_bytes(url,timeout,retries).decode('utf-8'))
def decode(b):
  for enc in ('utf-8-sig','cp1252','latin-1'):
    try:return b.decode(enc)
    except:pass
  return b.decode('utf-8',errors='replace')
def norm(s):
  s=(s or '').lower().replace('&','and');s=re.sub(r'\b(fc|cf|calcio|football club|club de futbol|club|afc|ac|as|ssc|ss|sv|vfb|vfl|1899|1909|1910|1904|1905|1907|1908|1919|1920|1924|1927|1929|1946)\b',' ',s);s=re.sub(r'[^a-z0-9]+',' ',s);return ' '.join(s.split())
def sim(a,b):
  a=norm(a);b=norm(b)
  if not a or not b:return 0
  if a==b:return 1
  return SequenceMatcher(None,a,b).ratio()
def pdate(s):
  for fmt in ('%d/%m/%Y','%d/%m/%y','%Y-%m-%d'):
    try:return datetime.strptime((s or '').strip(),fmt).date()
    except:pass
  raise ValueError(s)
def ptime(s):
  for fmt in ('%H:%M','%H.%M'):
    try:return datetime.strptime((s or '').strip(),fmt).time()
    except:pass
  return None
def finite(xs):return [v for v in xs if isinstance(v,(int,float)) and math.isfinite(v)]
def avg(xs):
  x=finite(xs);return sum(x)/len(x) if x else None
def sm(xs):
  x=finite(xs);return sum(x) if x else None
def mx(xs):
  x=finite(xs);return max(x) if x else None
def multi_weather(date,entries):
  hourly='temperature_2m,relative_humidity_2m,precipitation,rain,snowfall,wind_speed_10m,wind_gusts_10m,weather_code'
  p={'latitude':','.join(f'{x[1]:.5f}' for x in entries),'longitude':','.join(f'{x[2]:.5f}' for x in entries),'start_date':date,'end_date':date,'hourly':hourly,'timezone':'auto','wind_speed_unit':'kmh','precipitation_unit':'mm','models':'era5_land'}
  try:d=req_json('https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode(p),150,5)
  except:
    p.pop('models',None);d=req_json('https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode(p),150,5)
  if isinstance(d,dict):d=[d]
  if len(d)!=len(entries):raise RuntimeError(f'count mismatch {len(d)} != {len(entries)}')
  return {entries[i][0]:d[i] for i in range(len(entries))}
os.makedirs('out_v5',exist_ok=True)
fd=[]
for sc in SEASON_CODES:
  for div,(league,cc,tmcomp) in DIVS.items():
    url=f'https://www.football-data.co.uk/mmz4281/{sc}/{div}.csv'
    for r in csv.DictReader(io.StringIO(decode(req_bytes(url)))):
      try:d=pdate(r.get('Date'))
      except:continue
      kt=ptime(r.get('Time'))
      if not kt:continue
      fd.append({'season':SL[sc],'league':league,'cc':cc,'tmcomp':tmcomp,'date':str(d),'time':kt.strftime('%H:%M'),'home':(r.get('HomeTeam')or'').strip(),'away':(r.get('AwayTeam')or'').strip(),'hg':r.get('FTHG',''),'ag':r.get('FTAG',''),'source_url':url})
print('fd',len(fd),flush=True)
raw=req_bytes('https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz',240);bykey=defaultdict(list)
with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
  text=io.TextIOWrapper(gz,encoding='utf-8-sig',newline='')
  for r in csv.DictReader(text):
    if r.get('competition_id') not in {x[2] for x in DIVS.values()}:continue
    try:sy=int(r.get('season','-1'))
    except:continue
    if 2019<=sy<=2025:bykey[(r.get('competition_id'),r.get('date'))].append(r)
unmatched=[]
for m in fd:
  best=None;bs=-1
  for r in bykey.get((m['tmcomp'],m['date']),[]):
    score=sim(m['home'],r.get('home_club_name'))+sim(m['away'],r.get('away_club_name'))
    try:
      if m['hg']!='' and m['ag']!='' and int(float(m['hg']))==int(float(r.get('home_club_goals'))) and int(float(m['ag']))==int(float(r.get('away_club_goals'))):score+=1.2
    except:pass
    if score>bs:bs=score;best=r
  if best is not None and bs>=1.25:m.update({'tm_game_id':best.get('game_id',''),'stadium':best.get('stadium',''),'tm_home':best.get('home_club_name',''),'tm_away':best.get('away_club_name',''),'match_score':bs})
  else:m.update({'tm_game_id':'','stadium':'','tm_home':'','tm_away':'','match_score':bs});unmatched.append(m)
print('tm matched',len(fd)-len(unmatched),'unmatched',len(unmatched),flush=True)
stad_rows=list(csv.DictReader(io.StringIO(decode(req_bytes('https://raw.githubusercontent.com/dvd23m/Football_Stadiums_Map/main/stadiums_geloc.csv')))))
venue_keys=sorted(set((m['league'],m['home'],m.get('tm_home',''),m.get('stadium','')) for m in fd));coords={};miss=[]
# Cache normalized strings for fast fuzzy matching
S=[(r,norm(r.get('club')),norm(r.get('name_of_stadium'))) for r in stad_rows]
for n,(league,home,tmhome,stadium) in enumerate(venue_keys,1):
  nh,nt,ns=norm(home),norm(tmhome),norm(stadium);best=None;bs=-1;why=''
  for r,nc,nstad in S:
    cs=max(1.0 if nh and nh==nc else 0,1.0 if nt and nt==nc else 0,SequenceMatcher(None,nt,nc).ratio() if nt and nc else 0,SequenceMatcher(None,nh,nc).ratio() if nh and nc else 0)
    ss=SequenceMatcher(None,ns,nstad).ratio() if ns and nstad else 0
    # club name dominates; stadium supports ambiguous names
    score=max(cs,0.85*ss+0.15*cs)
    if score>bs:bs=score;best=r;why=f'club={cs:.3f};stad={ss:.3f}'
  if best is not None and bs>=0.82:
    try:coords[(league,home)]={'lat':float(best['lat']),'lon':float(best['lon']),'source':'stadium_dataset_fuzzy','detail':best.get('club','')+' | '+best.get('name_of_stadium','')+' | '+why};continue
    except:pass
  miss.append((league,home,tmhome,stadium,bs,best.get('club','') if best else '',best.get('name_of_stadium','') if best else ''))
print('coords',len(coords),'miss',len(miss),flush=True)
with open('out_v5/stage43_team_coordinates.csv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['league','team','latitude','longitude','coordinate_source','detail']);[w.writerow([lg,t,g['lat'],g['lon'],g['source'],g['detail']]) for (lg,t),g in sorted(coords.items())]
with open('out_v5/stage43_coordinate_unmatched.csv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['league','home','tm_home','stadium','best_score','best_club','best_stadium']);w.writerows(miss)
bydate=defaultdict(set)
for m in fd:
  k=(m['league'],m['home'])
  if k in coords:bydate[m['date']].add(k)
tasks=[]
for date,keys in sorted(bydate.items()):
  ks=sorted(keys)
  for i in range(0,len(ks),25):
    b=ks[i:i+25];tasks.append((date,[(k,coords[k]['lat'],coords[k]['lon']) for k in b]))
print('dates',len(bydate),'tasks',len(tasks),flush=True)
weather_by={};errors=[]
def task(t):
  date,entries=t
  try:return date,multi_weather(date,entries),''
  except Exception as e:return date,{k:None for k,_,_ in entries},str(e)
with ThreadPoolExecutor(max_workers=10) as ex:
  fut=[ex.submit(task,t) for t in tasks]
  for n,fu in enumerate(as_completed(fut),1):
    date,d,e=fu.result();
    for k,v in d.items():weather_by[(date,k)]=v
    if e:errors.append((date,e))
    if n%50==0 or n==len(tasks):print('api',n,'/',len(tasks),'errors',len(errors),flush=True)
out=[]
for m in fd:
  k=(m['league'],m['home']);data=weather_by.get((m['date'],k));g=coords.get(k);z=dict(m);z.update({'weather_ok':0,'weather_error':''})
  if g:z.update({'latitude':g['lat'],'longitude':g['lon'],'coordinate_source':g['source'],'coordinate_detail':g['detail']})
  if not data:z['weather_error']='weather_or_coordinate_failed';out.append(z);continue
  h=data.get('hourly',{});idx={t:i for i,t in enumerate(h.get('time',[]))};kick=datetime.fromisoformat(m['date']+'T'+m['time']);floor=kick.replace(minute=0,second=0,microsecond=0);nearest=floor if kick.minute<30 else floor+timedelta(hours=1);ids=[idx.get((floor+timedelta(hours=j)).strftime('%Y-%m-%dT%H:%M')) for j in range(3)];ids=[i for i in ids if i is not None];ni=idx.get(nearest.strftime('%Y-%m-%dT%H:%M'))
  def ar(x):return h.get(x,[])
  def vals(x):return [ar(x)[i] for i in ids if i<len(ar(x))]
  z.update({'weather_ok':1,'timezone':data.get('timezone',''),'temperature_kickoff_c':ar('temperature_2m')[ni] if ni is not None and ni<len(ar('temperature_2m')) else None,'temperature_match_avg_c':avg(vals('temperature_2m')),'humidity_match_avg_pct':avg(vals('relative_humidity_2m')),'precipitation_match_sum_mm':sm(vals('precipitation')),'rain_match_sum_mm':sm(vals('rain')),'snowfall_match_sum_cm':sm(vals('snowfall')),'wind_match_avg_kmh':avg(vals('wind_speed_10m')),'wind_match_max_kmh':mx(vals('wind_speed_10m')),'gust_match_max_kmh':mx(vals('wind_gusts_10m')),'weather_code_kickoff':ar('weather_code')[ni] if ni is not None and ni<len(ar('weather_code')) else None});out.append(z)
fields=['season','league','cc','date','time','home','away','hg','ag','source_url','tm_game_id','stadium','tm_home','tm_away','match_score','weather_ok','weather_error','latitude','longitude','coordinate_source','coordinate_detail','timezone','temperature_kickoff_c','temperature_match_avg_c','humidity_match_avg_pct','precipitation_match_sum_mm','rain_match_sum_mm','snowfall_match_sum_cm','wind_match_avg_kmh','wind_match_max_kmh','gust_match_max_kmh','weather_code_kickoff']
with open('out_v5/stage43_match_weather.csv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();[w.writerow({k:r.get(k,'') for k in fields}) for r in out]
with open('out_v5/stage43_api_errors.csv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['date','error']);w.writerows(errors)
print('DONE',len(out),'weather_ok',sum(int(x.get('weather_ok',0)) for x in out),'coords',len(coords),'coord_miss',len(miss),'api_errors',len(errors),flush=True)
