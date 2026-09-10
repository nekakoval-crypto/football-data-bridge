import csv, runpy

_OrigDictReader = csv.DictReader

class Stage43FixedDictReader(_OrigDictReader):
    def __next__(self):
        row = super().__next__()
        keys = {str(k).lower(): k for k in (self.fieldnames or [])}
        # Meteostat raw hourly files: construct timestamp from year/month/day/hour
        if all(k in keys for k in ('year','month','day','hour')) and not row.get('time'):
            try:
                y=int(float(row[keys['year']]))
                m=int(float(row[keys['month']]))
                d=int(float(row[keys['day']]))
                h=int(float(row[keys['hour']]))
                row['time']=f'{y:04d}-{m:02d}-{d:02d}T{h:02d}:00:00'
            except Exception:
                pass
        # Football_Stadiums_Map CSV has headers lon,lat but values are actually latitude,longitude.
        # Swap the values only for rows identifiable as stadium-dataset rows.
        if 'club' in keys and 'name_of_stadium' in keys and 'lon' in keys and 'lat' in keys:
            klat, klon = keys['lat'], keys['lon']
            row[klat], row[klon] = row.get(klon), row.get(klat)
        return row

csv.DictReader = Stage43FixedDictReader
runpy.run_path('scripts/stage43_weather_meteostat_year.py', run_name='__main__')
