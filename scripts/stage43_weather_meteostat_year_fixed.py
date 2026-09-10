import csv, runpy

_OrigDictReader = csv.DictReader

class MeteostatAwareDictReader(_OrigDictReader):
    def __next__(self):
        row = super().__next__()
        keys = {str(k).lower(): k for k in (self.fieldnames or [])}
        if all(k in keys for k in ('year','month','day','hour')) and not row.get('time'):
            try:
                y=int(float(row[keys['year']]))
                m=int(float(row[keys['month']]))
                d=int(float(row[keys['day']]))
                h=int(float(row[keys['hour']]))
                row['time']=f'{y:04d}-{m:02d}-{d:02d}T{h:02d}:00:00'
            except Exception:
                pass
        return row

csv.DictReader = MeteostatAwareDictReader
runpy.run_path('scripts/stage43_weather_meteostat_year.py', run_name='__main__')
