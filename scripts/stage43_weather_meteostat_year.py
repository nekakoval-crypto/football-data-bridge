import csv,io,gzip,math,os,re,sqlite3,sys,urllib.request
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor,as_completed
YEAR=int(sys.argv[1]); OUT=f'out_year_{YEAR}'; os.makedirs(OUT,exist_ok=True)
SEASON_CODES=['1920','2021','2122','2223','2324','2425','2526']
DIVS={'E0':('Premier League','GB','GB1','Europe/London'),'SP1':('La Liga','ES','ES1','Europe/Madrid'),'I1':('Serie A','IT','IT1','Europe/Rome'),'D1':('Bundesliga','DE','L1','Europe/Berlin'),'F1':('Ligue 1','FR','FR1','Europe/Paris')}
SL={'1920':'2019/20','2021':'2020/21','2122':'2021/22','2223':'2022/23','2324':'2023/24','2425':'2024/25','2526':'2025/26'}
UA='football-data-bridge-stage43-meteostat-year/1.0'
def get(url,timeout=90):
  req=urllib.request.Request(url,headers={'User-Agent':UA})
  with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
def decode(b):
  for e in ('utf-8-sig','cp1252','latin-1'):
    try:return b.decode(e)
    except:pass
  return b.decode('utf-8',errors='replace')
def norm(s):
  s=(s or '').lower().replace('&','and');s=re.sub(r'\b(fc|cf|calcio|football club|club de futbol|club|afc|ac|as|ssc|ss|sv|vfb|vfl|1899|1909|1910|1904|1905|1907|1908|1919|1920|1924|1927|1929|1946)\b',' ',s);s=re.sub(r'[^a-z0-9]+',' ',s);return ' '.join(s.split())
def sim(a,b):
  a=norm(a);b=norm(b)
  return 0 if not a or not b else (1 if a==b else SequenceMatcher(None,a,b).ratio())
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
def hav(a,b,c,d):
  R=6371.;p1=math.radians(a);p2=math.radians(c);dp=math.radians(c-a);dl=math.radians(d-b);x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2;return 2*R*math.asin(math.sqrt(x))
def avg(x):
  x=[v for v in x if isinstance(v,(int,float)) and math.isfinite(v)];return sum(x)/len(x) if x else None
def sm(x):
  x=[v for v in x if isinstance(v,(int,float)) and math.isfinite(v)];return sum(x) if x else None
def mx(x):
  x=[v for v in x if isinstance(v,(int,float)) and math.isfinite(v)];return max(x) if x else None
def n(x):
  try:return float(x)
  except:return None
# matches
fd=[]
for sc in SEASON_CODES:
  for div,(league,cc,tmcomp,tzname) in DIVS.items():
    url=f'https://www.football-data.co.uk/mmz4281/{sc}/{div}.csv'
    for r in csv.DictReader(io.StringIO(decode(get(url)))):
      try:d=pdate(r.get('Date'))
      except:continue
      if d.year!=YEAR:continue
      kt=ptime(r.get('Time'))
      if not kt:continue
      fd.append({'season':SL[sc],'league':league,'cc':cc,'tmcomp':tmcomp,'tzname':tzname,'date':str(d),'time':kt.strftime('%H:%M'),'home':(r.get('HomeTeam')or'').strip(),'away':(r.get('AwayTeam')or'').strip(),'hg':r.get('FTHG',''),'ag':r.get('FTAG','')})
print('YEAR',YEAR,'matches',len(fd),flush=True)
# TM games
raw=get('https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz',180);bykey=defaultdict(list)
with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
  for r in csv.DictReader(io.TextIOWrapper(gz,encoding='utf-8-sig',newline='')):
    if r.get('competition_id') not in {x[2] for x in DIVS.values()}:continue
    if not (r.get('date') or '').startswith(str(YEAR)+'-'):continue
    bykey[(r.get('competition_id'),r.get('date'))].append(r)
for m in fd:
  best=None;bs=-1
  for r in bykey.get((m['tmcomp'],m['date']),[]):
    score=sim(m['home'],r.get('home_club_name'))+sim(m['away'],r.get('away_club_name'))
    try:
      if int(float(m['hg']))==int(float(r.get('home_club_goals'))) and int(float(m['ag']))==int(float(r.get('away_club_goals'))):score+=1.2
    except:pass
    if score>bs:bs=score;best=r
  if best and bs>=1.25:m.update({'tm_game_id':best.get('game_id',''),'stadium':best.get('stadium',''),'tm_home':best.get('home_club_name',''),'tm_away':best.get('away_club_name',''),'match_score':bs})
  else:m.update({'tm_game_id':'','stadium':'','tm_home':'','tm_away':'','match_score':bs})
# stadium coords, strict fuzzy
stad=list(csv.DictReader(io.StringIO(decode(get('https://raw.githubusercontent.com/dvd23m/Football_Stadiums_Map/main/stadiums_geloc.csv')))))
coords={};miss=[]
for league,home,tmhome,stadium in sorted(set((m['league'],m['home'],m.get('tm_home',''),m.get('stadium','')) for m in fd)):
  best=None;bs=-1
  for r in stad:
    cs=max(sim(home,r.get('club')),sim(tmhome,r.get('club')));ss=sim(stadium,r.get('name_of_stadium')) if stadium else 0
    if max(cs,ss)<.55:continue
    score=max(cs,.9*ss+.1*cs)
    if score>bs:best=r;bs=score
  if best and bs>=.78:
    try:coords[(league,home)]={'lat':float(best['lat']),'lon':float(best['lon']),'score':bs,'source_club':best.get('club',''),'source_stadium':best.get('name_of_stadium','')};continue
    except:pass
  miss.append((league,home,tmhome,stadium,bs))
print('coords',len(coords),'miss',len(miss),flush=True)
# stations
open('stations.db','wb').write(get('https://data.meteostat.net/stations.db',180));db=sqlite3.connect('stations.db');c=db.cursor();cols=[x[1] for x in c.execute('pragma table_info(stations)').fetchall()];latc='latitude' if 'latitude' in cols else 'lat';lonc='longitude' if 'longitude' in cols else 'lon';countryc='country' if 'country' in cols else None
q=f'select id,{latc},{lonc}'+(f',{countryc}' if countryc else '')+f' from stations where {latc} is not null and {lonc} is not null';stations=[]
for r in c.execute(q):
  try:stations.append((str(r[0]),float(r[1]),float(r[2]),r[3] if len(r)>3 else None))
  except:pass
db.close();nearest={}
for k,g in coords.items():
  cc=next((m['cc'] for m in fd if (m['league'],m['home'])==k),None);pool=[x for x in stations if not countryc or x[3]==cc] or stations;nearest[k]=sorted((hav(g['lat'],g['lon'],x[1],x[2]),x[0]) for x in pool)[:4]
ids=sorted({sid for a in nearest.values() for _,sid in a});print('candidate stations',len(ids),flush=True)
# station-year gz in parallel
station_data={};errors=[]
def fetch_station(sid):
  u=f'https://data.meteostat.net/hourly/{YEAR}/{sid}.csv.gz'
  try:
    b=get(u,60); rr=list(csv.DictReader(io.StringIO(decode(gzip.decompress(b))))); d={}
    for r in rr:
      ts=r.get('time') or r.get('date')
      if not ts:continue
      try:t=datetime.fromisoformat(ts.replace(' ','T')).replace(tzinfo=None)
      except:continue
      d[t.replace(minute=0,second=0,microsecond=0)]=r
    return sid,d,''
  except Exception as e:return sid,{},str(e)
with ThreadPoolExecutor(max_workers=32) as ex:
  fut=[ex.submit(fetch_station,s) for s in ids]
  for i,fu in enumerate(as_completed(fut),1):
    sid,d,e=fu.result();station_data[sid]=d
    if e:errors.append((sid,e))
    if i%50==0 or i==len(ids):print('stations fetched',i,'/',len(ids),'errors',len(errors),flush=True)
# extract
out=[]
for m in fd:
  k=(m['league'],m['home']);g=coords.get(k);z=dict(m);z.update({'weather_ok':0,'weather_error':''})
  if not g or k not in nearest:z['weather_error']='coordinate_unmatched';out.append(z);continue
  local=datetime.fromisoformat(m['date']+'T'+m['time']).replace(tzinfo=ZoneInfo(m['tzname']));utc=local.astimezone(timezone.utc).replace(tzinfo=None);floor=utc.replace(minute=0,second=0,microsecond=0)
  chosen=None;vals=[];dist=None
  for d,sid in nearest[k]:
    dat=station_data.get(sid,{});tmp=[dat.get(floor+timedelta(hours=j)) for j in range(3)]
    if sum(x is not None for x in tmp)>=2:chosen=sid;vals=tmp;dist=d;break
  if not chosen:z['weather_error']='no_hourly_station_data';out.append(z);continue
  temp=[n(r.get('temp')) for r in vals if r];hum=[n(r.get('rhum')) for r in vals if r];pr=[n(r.get('prcp')) for r in vals if r];snow=[n(r.get('snwd') or r.get('snow')) for r in vals if r];wind=[n(r.get('wspd')) for r in vals if r];gust=[n(r.get('wpgt')) for r in vals if r];code=[n(r.get('coco')) for r in vals if r]
  z.update({'weather_ok':1,'latitude':g['lat'],'longitude':g['lon'],'coordinate_source':'stadium_dataset_fuzzy','coordinate_detail':g['source_club']+' | '+g['source_stadium'],'station_id':chosen,'station_distance_km':dist,'timezone':'UTC_station_data','temperature_match_avg_c':avg(temp),'humidity_match_avg_pct':avg(hum),'precipitation_match_sum_mm':sm(pr),'rain_match_sum_mm':sm(pr),'snowfall_match_sum_cm':(avg(snow)/10 if avg(snow) is not None else 0),'wind_match_avg_kmh':avg(wind),'gust_match_max_kmh':mx(gust),'weather_code_kickoff':code[0] if code else None});out.append(z)
fields=['season','league','date','time','home','away','hg','ag','tm_game_id','stadium','tm_home','tm_away','match_score','weather_ok','weather_error','latitude','longitude','coordinate_source','coordinate_detail','station_id','station_distance_km','timezone','temperature_match_avg_c','humidity_match_avg_pct','precipitation_match_sum_mm','rain_match_sum_mm','snowfall_match_sum_cm','wind_match_avg_kmh','gust_match_max_kmh','weather_code_kickoff']
with open(f'{OUT}/stage43_weather_{YEAR}.csv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();[w.writerow({x:r.get(x,'') for x in fields}) for r in out]
with open(f'{OUT}/qc_{YEAR}.csv','w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['metric','value']);w.writerows([['year',YEAR],['matches',len(out)],['weather_ok',sum(int(r.get('weather_ok',0)) for r in out)],['coord_count',len(coords)],['coord_miss',len(miss)],['candidate_stations',len(ids)],['station_download_errors',len(errors)]])
print('DONE',YEAR,'matches',len(out),'ok',sum(int(r.get('weather_ok',0)) for r in out),'errors',len(errors),flush=True)
