import csv, io, json, math, os, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta

SEASON_CODES = ["1920","2021","2122","2223","2324","2425","2526"]
DIVISIONS = {
    "E0": ("Premier League","GB"),
    "SP1": ("La Liga","ES"),
    "I1": ("Serie A","IT"),
    "D1": ("Bundesliga","DE"),
    "F1": ("Ligue 1","FR"),
}
SEASON_LABEL = {
    "1920":"2019/20","2021":"2020/21","2122":"2021/22","2223":"2022/23",
    "2324":"2023/24","2425":"2024/25","2526":"2025/26"
}
COUNTRY_NAME = {"GB":"United Kingdom","ES":"Spain","IT":"Italy","DE":"Germany","FR":"France"}

UA = "football-data-bridge-stage43/1.0 (historical research)"

def fetch_bytes(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def fetch_json(url, timeout=90, retries=4):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(min(8, 1.5*(i+1)))
    raise last

def decode_csv(b):
    for enc in ("utf-8-sig","cp1252","latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")

def parse_date(s):
    s=(s or "").strip()
    for fmt in ("%d/%m/%Y","%d/%m/%y","%Y-%m-%d"):
        try: return datetime.strptime(s,fmt).date()
        except: pass
    raise ValueError(s)

def parse_time(s):
    s=(s or "").strip()
    if not s: return None
    for fmt in ("%H:%M","%H.%M"):
        try: return datetime.strptime(s,fmt).time()
        except: pass
    return None

def geocode_team(team, country_code):
    country = COUNTRY_NAME[country_code]
    queries = [
        f"{team} football stadium, {country}",
        f"{team} football club, {country}",
        f"{team}, {country}",
    ]
    for q in queries:
        params = urllib.parse.urlencode({"q":q,"format":"jsonv2","limit":1,"countrycodes":country_code.lower()})
        url = "https://nominatim.openstreetmap.org/search?" + params
        try:
            data = fetch_json(url, timeout=45, retries=2)
            if data:
                x=data[0]
                return {
                    "latitude":float(x["lat"]),"longitude":float(x["lon"]),
                    "display_name":x.get("display_name",""),"query":q,
                    "osm_type":x.get("type","")
                }
        except Exception:
            pass
        time.sleep(1.05)
    return None

def openmeteo_range(lat, lon, start_date, end_date):
    hourly = "temperature_2m,relative_humidity_2m,precipitation,rain,snowfall,wind_speed_10m,wind_gusts_10m,weather_code"
    params = {
        "latitude":f"{lat:.5f}","longitude":f"{lon:.5f}",
        "start_date":str(start_date),"end_date":str(end_date),"hourly":hourly,
        "timezone":"auto","wind_speed_unit":"kmh","precipitation_unit":"mm",
        "models":"era5_land"
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    try:
        return fetch_json(url, timeout=120, retries=4)
    except Exception:
        params.pop("models",None)
        url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
        return fetch_json(url, timeout=120, retries=4)

def mean(vals):
    xs=[x for x in vals if isinstance(x,(int,float)) and math.isfinite(x)]
    return sum(xs)/len(xs) if xs else None

def vmax(vals):
    xs=[x for x in vals if isinstance(x,(int,float)) and math.isfinite(x)]
    return max(xs) if xs else None

def vsum(vals):
    xs=[x for x in vals if isinstance(x,(int,float)) and math.isfinite(x)]
    return sum(xs) if xs else None

# 1) Download Football-Data 2019/20–2025/26 and keep matches with kickoff time
matches=[]
for sc in SEASON_CODES:
    for div,(league,cc) in DIVISIONS.items():
        url=f"https://www.football-data.co.uk/mmz4281/{sc}/{div}.csv"
        text=decode_csv(fetch_bytes(url))
        rd=csv.DictReader(io.StringIO(text))
        for r in rd:
            try:
                d=parse_date(r.get("Date"))
            except:
                continue
            kt=parse_time(r.get("Time"))
            if kt is None:
                continue
            matches.append({
                "season":SEASON_LABEL[sc],"league":league,"country_code":cc,
                "match_date":str(d),"kickoff_time":kt.strftime("%H:%M"),
                "home_team":(r.get("HomeTeam") or "").strip(),"away_team":(r.get("AwayTeam") or "").strip(),
                "source_url":url
            })
print("matches",len(matches))

# 2) Geocode each league/team only once
team_keys=sorted(set((m["league"],m["country_code"],m["home_team"]) for m in matches))
coords={}
os.makedirs("out",exist_ok=True)
for i,(league,cc,team) in enumerate(team_keys,1):
    g=geocode_team(team,cc)
    coords[(league,team)]=g
    print("geo",i,"/",len(team_keys),league,team,"->",g and (g["latitude"],g["longitude"],g["display_name"][:80]))

with open("out/stage43_team_coordinates.csv","w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f); w.writerow(["league","team","country_code","latitude","longitude","geocode_query","geocode_result","osm_type"])
    for league,cc,team in team_keys:
        g=coords[(league,team)]
        w.writerow([league,team,cc,g and g["latitude"],g and g["longitude"],g and g["query"],g and g["display_name"],g and g["osm_type"]])

# 3) Query historical weather by team-season, then sample match window (kickoff to +2h)
groups=defaultdict(list)
for m in matches:
    groups[(m["league"],m["season"],m["home_team"])].append(m)

out=[]
errors=[]
for gi,(key,gmatches) in enumerate(sorted(groups.items()),1):
    league,season,team=key
    g=coords.get((league,team))
    if not g:
        for m in gmatches:
            z=dict(m); z.update({"weather_ok":0,"weather_error":"geocode_failed"}); out.append(z)
        continue
    dates=[datetime.fromisoformat(m["match_date"]).date() for m in gmatches]
    start=min(dates)-timedelta(days=1); end=max(dates)+timedelta(days=1)
    try:
        data=openmeteo_range(g["latitude"],g["longitude"],start,end)
        h=data.get("hourly",{})
        times=h.get("time",[])
        index={t:i for i,t in enumerate(times)}
        for m in gmatches:
            kick=datetime.fromisoformat(m["match_date"]+"T"+m["kickoff_time"])
            floor=kick.replace(minute=0,second=0,microsecond=0)
            nearest=floor if kick.minute<30 else floor+timedelta(hours=1)
            win=[floor+timedelta(hours=j) for j in range(3)]
            ids=[index.get(x.strftime("%Y-%m-%dT%H:%M")) for x in win]
            ids=[x for x in ids if x is not None]
            ni=index.get(nearest.strftime("%Y-%m-%dT%H:%M"))
            def arr(name): return h.get(name,[])
            vals=lambda name:[arr(name)[j] for j in ids if j < len(arr(name))]
            z=dict(m)
            z.update({
                "weather_ok":1,"weather_error":"",
                "latitude":g["latitude"],"longitude":g["longitude"],"geocode_result":g["display_name"],
                "timezone":data.get("timezone",""),
                "temperature_kickoff_c": (arr("temperature_2m")[ni] if ni is not None and ni < len(arr("temperature_2m")) else None),
                "temperature_match_avg_c":mean(vals("temperature_2m")),
                "humidity_match_avg_pct":mean(vals("relative_humidity_2m")),
                "precipitation_match_sum_mm":vsum(vals("precipitation")),
                "rain_match_sum_mm":vsum(vals("rain")),
                "snowfall_match_sum_cm":vsum(vals("snowfall")),
                "wind_match_avg_kmh":mean(vals("wind_speed_10m")),
                "wind_match_max_kmh":vmax(vals("wind_speed_10m")),
                "gust_match_max_kmh":vmax(vals("wind_gusts_10m")),
                "weather_code_kickoff": (arr("weather_code")[ni] if ni is not None and ni < len(arr("weather_code")) else None),
            })
            out.append(z)
    except Exception as e:
        errors.append((key,str(e)))
        for m in gmatches:
            z=dict(m); z.update({"weather_ok":0,"weather_error":str(e),"latitude":g["latitude"],"longitude":g["longitude"],"geocode_result":g["display_name"]}); out.append(z)
    print("weather",gi,"/",len(groups),key,"matches",len(gmatches))

fields=[
    "season","league","country_code","match_date","kickoff_time","home_team","away_team","source_url",
    "weather_ok","weather_error","latitude","longitude","geocode_result","timezone",
    "temperature_kickoff_c","temperature_match_avg_c","humidity_match_avg_pct",
    "precipitation_match_sum_mm","rain_match_sum_mm","snowfall_match_sum_cm",
    "wind_match_avg_kmh","wind_match_max_kmh","gust_match_max_kmh","weather_code_kickoff"
]
with open("out/stage43_match_weather.csv","w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader();
    for r in out: w.writerow({k:r.get(k,"") for k in fields})
with open("out/stage43_errors.csv","w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f); w.writerow(["league","season","team","error"])
    for (league,season,team),err in errors: w.writerow([league,season,team,err])
print("output",len(out),"weather_ok",sum(int(r.get("weather_ok",0)) for r in out),"errors",len(errors))
