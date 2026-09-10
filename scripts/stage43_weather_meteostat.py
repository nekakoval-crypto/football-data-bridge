import csv,io,gzip,math,os,re,sqlite3,urllib.request
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo
import duckdb

SEASON_CODES=['1920','2021','2122','2223','2324','2425','2526']
DIVS={'E0':('Premier League','GB','GB1','Europe/London'),'SP1':('La Liga','ES','ES1','Europe/Madrid'),'I1':('Serie A','IT','IT1','Europe/Rome'),'D1':('Bundesliga','DE','L1','Europe/Berlin'),'F1':('Ligue 1','FR','FR1','Europe/Paris')}
SL={'1920':'2019/20','2021':'2020/21','2122':'2021/22','2223':'2022/23','2324':'2023/24','2425':'2024/25','2526':'2025/26'}
UA='football-data-bridge-stage43-meteostat/1.0'

def get(url,timeout=180):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
def decode(b):
    for enc in ('utf-8-sig','cp1252','latin-1'):
        try:return b.decode(enc)
        except:pass
    return b.decode('utf-8',errors='replace')
def norm(s):
    s=(s or '').lower().replace('&','and')
    s=re.sub(r'\b(fc|cf|calcio|football club|club de futbol|club|afc|ac|as|ssc|ss|sv|vfb|vfl|1899|1909|1910|1904|1905|1907|1908|1919|1920|1924|1927|1929|1946)\b',' ',s)
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())
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
def hav(lat1,lon1,lat2,lon2):
    r=6371.0
    p1,p2=math.radians(lat1),math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))
def mean(vals):
    x=[v for v in vals if v is not None and isinstance(v,(int,float)) and math.isfinite(v)]
    return sum(x)/len(x) if x else None
def sumv(vals):
    x=[v for v in vals if v is not None and isinstance(v,(int,float)) and math.isfinite(v)]
    return sum(x) if x else None
def maxv(vals):
    x=[v for v in vals if v is not None and isinstance(v,(int,float)) and math.isfinite(v)]
    return max(x) if x else None

os.makedirs('out_meteostat',exist_ok=True)
# Football-Data matches with real kickoff time
fd=[]
for sc in SEASON_CODES:
  for div,(league,cc,tmcomp,tzname) in DIVS.items():
    url=f'https://www.football-data.co.uk/mmz4281/{sc}/{div}.csv'
    for r in csv.DictReader(io.StringIO(decode(get(url)))):
      try:d=pdate(r.get('Date'))
      except:continue
      kt=ptime(r.get('Time'))
      if not kt:continue
      fd.append({'season':SL[sc],'league':league,'cc':cc,'tmcomp':tmcomp,'tzname':tzname,'date':str(d),'time':kt.strftime('%H:%M'),'home':(r.get('HomeTeam')or'').strip(),'away':(r.get('AwayTeam')or'').strip(),'hg':r.get('FTHG',''),'ag':r.get('FTAG',''),'source_url':url})
print('fd',len(fd),flush=True)
# Transfermarkt games for stadium names
raw=get('https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz',240)
bykey=defaultdict(list)
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
# stadium coords
stad_rows=list(csv.DictReader(io.StringIO(decode(get('https://raw.githubusercontent.com/dvd23m/Football_Stadiums_Map/main/stadiums_geloc.csv')))))
venue_keys=sorted(set((m['league'],m['home'],m.get('tm_home',''),m.get('stadium','')) for m in fd))
coords={};coord_miss=[]
for league,home,tmhome,stadium in venue_keys:
  best=None;bs=-1
  for r in stad_rows:
    cs=max(sim(home,r.get('club')),sim(tmhome,r.get('club')))
    ss=sim(stadium,r.get('name_of_stadium')) if stadium else 0
    if max(cs,ss)<0.55:continue
    score=max(cs,0.90*ss+0.10*cs)
    if score>bs:bs=score;best=r
  if best is not None and bs>=0.78:
    try:coords[(league,home)]={'lat':float(best['lat']),'lon':float(best['lon']),'club':best.get('club',''),'stadium':best.get('name_of_stadium',''),'score':bs};continue
    except:pass
  coord_miss.append((league,home,tmhome,stadium,bs))
print('coords',len(coords),'miss',len(coord_miss),flush=True)
# Meteostat station database
open('stations.db','wb').write(get('https://data.meteostat.net/stations.db',240))
con=sqlite3.connect('stations.db');cur=con.cursor(); cols=[x[1] for x in cur.execute('pragma table_info(stations)').fetchall()]
print('station columns',cols,flush=True)
idc='id'; latc='latitude' if 'latitude' in cols else 'lat'; lonc='longitude' if 'longitude' in cols else 'lon'; countryc='country' if 'country' in cols else None
sel=f"select {idc},{latc},{lonc}"+(f",{countryc}" if countryc else '')+' from stations where '+latc+' is not null and '+lonc+' is not null'
st=[]
for row in cur.execute(sel):
    sid,lat,lon=row[:3];cc=row[3] if len(row)>3 else None
    try:st.append((str(sid),float(lat),float(lon),cc))
    except:pass
con.close();print('stations',len(st),flush=True)
# candidate nearest 4 stations; prefer same country when metadata available
nearest={}
for k,g in coords.items():
    league,home=k; cc=next((m['cc'] for m in fd if m['league']==league and m['home']==home),None)
    pool=[x for x in st if not countryc or x[3]==cc] or st
    arr=sorted(((hav(g['lat'],g['lon'],x[1],x[2]),x[0]) for x in pool))[:4]
    nearest[k]=arr
print('nearest mapped',len(nearest),flush=True)
# query bulk hourly parquet by year through DuckDB httpfs
all_ids=sorted({sid for arr in nearest.values() for _,sid in arr})
db=duckdb.connect();db.execute('INSTALL httpfs');db.execute('LOAD httpfs')
weather={} # (station, utc_hour) -> values
for year in range(2019,2027):
    ids_sql=','.join("'"+x.replace("'","''")+"'" for x in all_ids)
    url=f'https://data.meteostat.net/hourly/{year}.parquet'
    q=f"select station,time,temp,rhum,prcp,snwd,wspd,wpgt,coco from read_parquet('{url}') where cast(station as varchar) in ({ids_sql})"
    try:
        rows=db.execute(q).fetchall()
    except Exception as e:
        print('year query failed',year,e,flush=True);continue
    for sid,t,temp,rhum,prcp,snwd,wspd,wpgt,coco in rows:
        if isinstance(t,str):
            try:t=datetime.fromisoformat(t)
            except:continue
        if t.tzinfo is not None:t=t.astimezone(timezone.utc).replace(tzinfo=None)
        weather[(str(sid),t.replace(minute=0,second=0,microsecond=0))]=(temp,rhum,prcp,snwd,wspd,wpgt,coco)
    print('year',year,'rows',len(rows),'weather map',len(weather),flush=True)
# extract match-window weather; choose nearest station with records
out=[]
for m in fd:
    k=(m['league'],m['home']);g=coords.get(k); z=dict(m); z.update({'weather_ok':0,'weather_error':''})
    if not g or k not in nearest:
        z['weather_error']='coordinate_unmatched';out.append(z);continue
    local=datetime.fromisoformat(m['date']+'T'+m['time']).replace(tzinfo=ZoneInfo(m['tzname']))
    utc=local.astimezone(timezone.utc).replace(tzinfo=None); floor=utc.replace(minute=0,second=0,microsecond=0)
    chosen=None;dist=None;vals=[]
    for d,sid in nearest[k]:
        tmp=[]
        for j in range(3):tmp.append(weather.get((sid,floor+timedelta(hours=j))))
        if sum(v is not None for v in tmp)>=2:
            chosen=sid;dist=d;vals=tmp;break
    if not chosen:
        z['weather_error']='no_station_hourly_data';out.append(z);continue
    temps=[v[0] for v in vals if v]; rhs=[v[1] for v in vals if v]; pr=[v[2] for v in vals if v]; sn=[v[3] for v in vals if v]; ws=[v[4] for v in vals if v]; wg=[v[5] for v in vals if v]; co=[v[6] for v in vals if v]
    z.update({'weather_ok':1,'latitude':g['lat'],'longitude':g['lon'],'stadium_coord_match_score':g['score'],'meteostat_station':chosen,'station_distance_km':dist,'temperature_match_avg_c':mean(temps),'humidity_match_avg_pct':mean(rhs),'precipitation_match_sum_mm':sumv(pr),'snow_depth_match_avg_mm':mean(sn),'wind_match_avg_kmh':mean(ws),'gust_match_max_kmh':maxv(wg),'weather_code_mode':max(set(co),key=co.count) if co else None})
    out.append(z)
fields=['season','league','cc','date','time','home','away','hg','ag','tm_game_id','stadium','tm_home','tm_away','match_score','weather_ok','weather_error','latitude','longitude','stadium_coord_match_score','meteostat_station','station_distance_km','temperature_match_avg_c','humidity_match_avg_pct','precipitation_match_sum_mm','snow_depth_match_avg_mm','wind_match_avg_kmh','gust_match_max_kmh','weather_code_mode']
with open('out_meteostat/stage43_match_weather_meteostat.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();[w.writerow({x:r.get(x,'') for x in fields}) for r in out]
with open('out_meteostat/stage43_coordinates.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['league','team','lat','lon','source_club','source_stadium','match_score']);
    for (lg,t),g in sorted(coords.items()):w.writerow([lg,t,g['lat'],g['lon'],g['club'],g['stadium'],g['score']])
with open('out_meteostat/stage43_coordinate_unmatched.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['league','home','tm_home','stadium','best_score']);w.writerows(coord_miss)
with open('out_meteostat/stage43_nearest_stations.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['league','team','rank','station','distance_km']);
    for (lg,t),arr in sorted(nearest.items()):
        for i,(d,sid) in enumerate(arr,1):w.writerow([lg,t,i,sid,d])
print('DONE',len(out),'weather_ok',sum(int(r.get('weather_ok',0)) for r in out),'coords',len(coords),'coord_miss',len(coord_miss),flush=True)
