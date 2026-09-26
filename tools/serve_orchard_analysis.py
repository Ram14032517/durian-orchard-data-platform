"""Local-only map server with cached NASA POWER daily point requests."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from pathlib import Path
from datetime import date,datetime,timezone
import json,hashlib,threading
import requests
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'research_data/five_province_history/point_weather_cache'
LOCK=threading.Semaphore(2)
PARAMS='T2M,T2M_MAX,T2M_MIN,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,WS2M'
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path!='/api/weather':return super().do_GET()
        try:
            q=parse_qs(parsed.query);lat=round(float(q['lat'][0]),5);lon=round(float(q['lon'][0]),5)
            start=date.fromisoformat(q['start'][0]);end=date.fromisoformat(q['end'][0])
            if not (5<=lat<=21 and 97<=lon<=106 and date(1981,1,1)<=start<=end<=date.today() and (end-start).days<=731):
                raise ValueError('เลือกพิกัดประเทศไทยและช่วงเวลาไม่เกินสองปี ตั้งแต่ปี 1981 ถึงปัจจุบัน')
            args=dict(parameters=PARAMS,community='AG',latitude=lat,longitude=lon,start=start.strftime('%Y%m%d'),end=end.strftime('%Y%m%d'),format='JSON',**{'time-standard':'LST'})
            key=hashlib.sha256(json.dumps(args,sort_keys=True).encode()).hexdigest()
            CACHE.mkdir(parents=True,exist_ok=True);path=CACHE/f'{key}.json'
            with LOCK:
                if path.exists():data=json.loads(path.read_text(encoding='utf-8'))
                else:
                    r=requests.get('https://power.larc.nasa.gov/api/temporal/daily/point',params=args,timeout=120);r.raise_for_status();data=r.json()
                    if 'parameter' not in data.get('properties',{}):raise ValueError('NASA response has no daily data')
                    path.write_bytes(r.content)
                    path.with_suffix('.source.json').write_text(json.dumps(dict(url=r.url,retrieved_utc=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(r.content).hexdigest()),indent=2),encoding='utf-8')
            p=data['properties']['parameter'];fill=data.get('header',{}).get('fill_value',-999)
            dates=sorted(set().union(*(v.keys() for v in p.values())))
            rows=[dict(date=f'{d[:4]}-{d[4:6]}-{d[6:]}',**{k:None if p.get(k,{}).get(d,fill)==fill else p[k][d] for k in PARAMS.split(',')}) for d in dates]
            payload=dict(rows=rows,latitude=lat,longitude=lon,time_standard='LST',source='NASA POWER daily point; grid-based, not orchard sensor',cache_key=key)
            self.send_json(200,payload)
        except (ValueError,KeyError) as e:self.send_json(400,{'error':str(e)})
        except Exception as e:self.send_json(502,{'error':str(e)})
    def send_json(self,status,payload):
        body=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
if __name__=='__main__':
    print('http://127.0.0.1:8871/research_data/five_province_history/UNIFIED_MAP.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8871),Handler).serve_forever()
