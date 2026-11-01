"""Local-only map server with cached NASA POWER daily point requests."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from pathlib import Path
from datetime import date,datetime,timezone,timedelta
import argparse,json,hashlib,threading,csv,io,os,re
import requests
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=Path(os.environ['ORCHARD_RUNTIME_DIR']) if os.environ.get('ORCHARD_RUNTIME_DIR') else ROOT/'research_data/five_province_history'
CACHE=RUNTIME/'point_weather_cache'
EXPORTS=RUNTIME/'exports'
LOCK=threading.Lock()
PARAMS='T2M,T2M_MAX,T2M_MIN,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,WS2M'

def orchard_data_source():
    source=os.environ.get('ORCHARD_DATA_SOURCE','local_snapshot')
    if source not in ('local_snapshot','supabase'):
        raise RuntimeError('ORCHARD_DATA_SOURCE ต้องเป็น local_snapshot หรือ supabase')
    return source

def supabase_configured():
    return bool(re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',os.environ.get('SUPABASE_URL','').rstrip('/'))
                and (os.environ.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY'))
                and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',os.environ.get('ORCHARD_DEVICE_ID','')))

def project_identity(source=None):
    # Identify the checkout without returning its private absolute path.
    source=orchard_data_source() if source is None else source;ready=supabase_configured()
    gap=(ROOT/'research_data/five_province_history/gap_orchards/manifest.json').is_file()
    return {'application':'orchard-analysis','protocol':1,'mode':'local','orchard_source':source,
            'workspace_id':hashlib.sha256(ROOT.resolve().as_posix().casefold().encode()).hexdigest(),
            'private_harvest_api_version':1,
            'private_storage_configured':bool(os.environ.get('SUPABASE_URL') and os.environ.get('DASHBOARD_PASSWORD')
                and (os.environ.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY'))),
            'private_storage_project_fingerprint':hashlib.sha256(os.environ['SUPABASE_URL'].rstrip('/').encode()).hexdigest()
                if os.environ.get('SUPABASE_URL') else None,
            'capabilities':{'gap_registry':{'available':gap,'message':
                'ใช้หมุด GAP ในเครื่องได้' if gap else 'ยังไม่มีชุดหมุด GAP ในเครื่องนี้ ให้ pull branch ที่รวมข้อมูลแล้ว'},
                'orchard':{'source':source,'configured':ready if source=='supabase' else
                    (ROOT/'data/processed/orchard_live/live_report.json').is_file(),
                    'history_configured':ready}}}

def local_orchard_status():
    if orchard_data_source()=='supabase':
        from supabase_orchard import live_status
        return live_status()
    from orchard_current_context import orchard_snapshot
    return orchard_snapshot()

def verified_cache(path):
    """Read a cache entry only if the recorded bytes and structure still agree."""
    try:
        raw=path.read_bytes()
        meta=json.loads(path.with_suffix('.source.json').read_text(encoding='utf-8'))
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:return None
        data=json.loads(raw)
        if not data.get('properties',{}).get('parameter'):return None
        return data,meta
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return None

def cache_is_fresh(path, end, today=None, now=None):
    """Refresh recent periods every 6h; older periods every 30d for revisions."""
    today=today or date.today()
    now=now or datetime.now(timezone.utc)
    ttl=21600 if end>=today-timedelta(days=31) else 30*86400
    try:
        cached=verified_cache(path)
        if cached is None:return False
        _,meta=cached
        age=(now-datetime.fromisoformat(meta['retrieved_utc'])).total_seconds()
        return 0<=age<ttl
    except (OSError,ValueError,KeyError,TypeError):
        return False

def daily_rows(data,start,end):
    """Preserve all requested days and parameter missingness, including zero rain."""
    p=data['properties']['parameter'];fill=data.get('header',{}).get('fill_value',-999)
    rows=[]
    for i in range((end-start).days+1):
        day=start+timedelta(days=i);key=day.strftime('%Y%m%d')
        row={'date':day.isoformat()}
        for k in PARAMS.split(','):
            v=p.get(k,{}).get(key)
            row[k]=None if v is None or v in (fill,-999) else v
        rows.append(row)
    return rows

def save_weather_export(payload):
    """Save the displayed snapshot locally, with a server-controlled filename."""
    start=date.fromisoformat(payload['start']);end=date.fromisoformat(payload['end'])
    if not date(1981,1,1)<=start<=end<=date.today() or (end-start).days>731:
        raise ValueError('ช่วงวันที่ส่งออกไม่ถูกต้อง')
    text=payload['csv']
    if not isinstance(text,str) or len(text.encode('utf-8'))>2_000_000:
        raise ValueError('ไฟล์ส่งออกต้องไม่เกิน 2 MB')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    required={'area','province_code','date','selected_latitude','selected_longitude','data_latitude','data_longitude','source_basis','time_standard'}
    if not required.issubset(reader.fieldnames or []):raise ValueError('คอลัมน์ส่งออกไม่ครบ')
    count=0
    for row in reader:
        if row['area'] not in ('A','B') or not start<=date.fromisoformat(row['date'])<=end:
            raise ValueError('แถวส่งออกอยู่นอกพื้นที่หรือวันที่เลือก')
        count+=1
    if not 1<=count<=1464:raise ValueError('จำนวนแถวส่งออกไม่ถูกต้อง')
    raw=text.encode('utf-8');digest=hashlib.sha256(raw).hexdigest()
    filename=f'weather_AB_{start}_{end}_{digest[:12]}.csv'
    EXPORTS.mkdir(parents=True,exist_ok=True);path=EXPORTS/filename
    try:
        with path.open('xb') as f:f.write(raw)
    except FileExistsError:
        if path.read_bytes()!=raw:raise ValueError('ชื่อไฟล์ซ้ำกับข้อมูลอื่น')
    return {'url':f'/research_data/five_province_history/exports/{filename}',
            'filename':filename,'rows':count,'sha256':digest,
            'folder':'research_data/five_province_history/exports'}

def fetch_weather(lat,lon,start,end):
    args=dict(parameters=PARAMS,community='AG',latitude=round(lat,5),longitude=round(lon,5),start=start.strftime('%Y%m%d'),end=end.strftime('%Y%m%d'),format='JSON',**{'time-standard':'LST'})
    key=hashlib.sha256(json.dumps(args,sort_keys=True).encode()).hexdigest()
    CACHE.mkdir(parents=True,exist_ok=True);path=CACHE/f'{key}.json'
    with LOCK:
        cached=verified_cache(path);stale=False
        if cached and cache_is_fresh(path,end):data,provenance=cached
        else:
            try:
                r=requests.get('https://power.larc.nasa.gov/api/temporal/daily/point',params=args,timeout=45);r.raise_for_status();data=r.json()
                if not data.get('properties',{}).get('parameter'):raise RuntimeError('NASA response has no daily data')
                provenance=dict(url=r.url,retrieved_utc=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(r.content).hexdigest())
                path.write_bytes(r.content)
                path.with_suffix('.source.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
            except (requests.RequestException,ValueError,RuntimeError):
                if not cached:raise
                data,provenance=cached;stale=True
    rows=daily_rows(data,start,end)
    payload=dict(rows=rows,latitude=lat,longitude=lon,time_standard='LST',source='NASA POWER daily point; grid-based, not orchard sensor',cache_key=key,stale_cache=stale)
    payload['coverage']={k:{'valid_days':sum(r[k] is not None for r in rows),'requested_days':len(rows)} for k in PARAMS.split(',')}
    payload['provenance']=provenance
    return payload


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def end_headers(self):
        path=urlparse(self.path).path
        if path.startswith('/research_data/five_province_history/') and Path(path).suffix.lower() in ('.html','.js','.css'):
            # Revalidate the local UI after a rebuild; keep large data caches unchanged.
            self.send_header('Cache-Control','no-cache, max-age=0, must-revalidate')
        super().end_headers()
    def private_route(self):
        path=urlparse(self.path).path
        if path in ('/home','/map','/weather','/yield','/seasons'):return True
        if (path=='/api/orchard-history' or (path=='/api/orchard-status' and orchard_data_source()=='supabase')) and os.environ.get('SUPABASE_URL'):
            return True
        return path in ('/login','/logout','/api/orchard-session','/api/orchard-forecast') or path=='/api/orchard-harvest' or path.startswith('/api/orchard-harvest/')

    def serve_private(self):
        """Mount the existing Flask authentication/API on the local report server."""
        from io import BytesIO
        import sys
        port=self.server.server_port
        if self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):
            return self.send_json(403,{'error':'ใช้ที่อยู่ localhost ของโครงการเท่านั้น'})
        try:
            app=private_application()
        except (RuntimeError,ImportError):
            return self.send_json(503,{'error':'ยังไม่เปิดการบันทึกส่วนตัว ตั้ง DASHBOARD_PASSWORD และ Supabase ฝั่งเซิร์ฟเวอร์ แล้วเริ่มเซิร์ฟเวอร์ใหม่; ไม่เก็บแทนในเบราว์เซอร์'})
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:return self.send_json(400,{'error':'ขนาดคำขอไม่ถูกต้อง'})
        if not 0<=size<=65536:return self.send_json(413,{'error':'คำขอประวัติสวนมีขนาดใหญ่เกินไป'})
        parsed=urlparse(self.path)
        environ={'REQUEST_METHOD':self.command,'PATH_INFO':parsed.path,'QUERY_STRING':parsed.query,
            'SCRIPT_NAME':'','SERVER_NAME':'127.0.0.1','SERVER_PORT':str(port),'SERVER_PROTOCOL':self.request_version,
            'CONTENT_LENGTH':str(size),'CONTENT_TYPE':self.headers.get('Content-Type',''),
            'REMOTE_ADDR':self.client_address[0],'wsgi.version':(1,0),'wsgi.url_scheme':'http',
            'wsgi.input':BytesIO(self.rfile.read(size)),'wsgi.errors':sys.stderr,
            'wsgi.multithread':True,'wsgi.multiprocess':False,'wsgi.run_once':False}
        for key,value in self.headers.items():
            if key.lower() not in ('content-type','content-length'):
                environ['HTTP_'+key.upper().replace('-','_')]=value
        response=[]
        def start_response(status,headers,exc_info=None):
            response[:]=[status,headers]
        result=app(environ,start_response)
        try:
            body=b''.join(result)
            self.send_response(int(response[0].split()[0]))
            for key,value in response[1]:self.send_header(key,value)
            self.end_headers();self.wfile.write(body)
        finally:
            if hasattr(result,'close'):result.close()
    def send_head(self):
        # Do not expose .git, .secrets, source files, or directory listings.
        path=Path(self.translate_path(self.path)).resolve()
        roots=[ROOT/'research_data'/p for p in ('five_province_history','priority_provinces','thailand_comparison','regional_orchards')]
        if (not any(path.is_relative_to(p.resolve()) for p in roots) or not path.is_file()
            or path.is_relative_to((ROOT/'research_data/five_province_history/gap_spatial_experiment').resolve())
            or any(p.startswith('.') for p in path.relative_to(ROOT.resolve()).parts)
            or 'point_weather_cache' in path.relative_to(ROOT.resolve()).parts
            or (path.suffix.lower() not in {'.html','.js','.css','.json','.geojson','.csv','.md','.ipynb','.png','.svg','.jpg'}
                and path != (ROOT/'research_data/five_province_history/training/training_bundle.zip').resolve())):
            self.send_error(404);return None
        return super().send_head()
    def do_GET(self):
        parsed=urlparse(self.path)
        if self.private_route():return self.serve_private()
        if parsed.path=='/api/province-forecast-readiness':
            from orchard_current_context import province_forecast_readiness
            return self.send_json(200,province_forecast_readiness())
        if parsed.path=='/api/project':
            try:return self.send_json(200,project_identity())
            except RuntimeError as e:return self.send_json(503,{'error':str(e)})
        if parsed.path=='/api/orchard-history':
            try:
                from supabase_orchard import orchard_history
                if not supabase_configured():
                    return self.send_json(503,{'error':'ยังไม่ตั้งการเชื่อม Supabase ของเครื่องนี้ (SUPABASE_URL, server key และ ORCHARD_DEVICE_ID) เว็บ cloud เดิมตั้งค่าแยกกัน','code':'orchard_not_configured'})
                q=parse_qs(parsed.query)
                return self.send_json(200,orchard_history(q.get('period',['day'])[0],end=q.get('end',[None])[0],start_date=q.get('start',[None])[0]))
            except ValueError as e:return self.send_json(400,{'error':str(e)})
            except Exception as e:return self.send_json(503,{'error':str(e)})
        if parsed.path in ('/api/orchard-status','/api/province-estimate'):
            try:
                from orchard_current_context import orchard_snapshot, province_estimate
                if parsed.path=='/api/orchard-status':return self.send_json(200,local_orchard_status())
                q=parse_qs(parsed.query)
                return self.send_json(200,province_estimate(q['province'][0],int(q['year'][0]),fetch_weather))
            except (ValueError,KeyError) as e:return self.send_json(400,{'error':str(e)})
            except RuntimeError as e:return self.send_json(503,{'error':str(e),'code':'orchard_unavailable'})
            except Exception as e:return self.send_json(502,{'error':str(e)})
        if parsed.path!='/api/weather':return super().do_GET()
        try:
            q=parse_qs(parsed.query);lat=round(float(q['lat'][0]),5);lon=round(float(q['lon'][0]),5)
            start=date.fromisoformat(q['start'][0]);end=date.fromisoformat(q['end'][0])
            if not (5<=lat<=21 and 97<=lon<=106 and date(1981,1,1)<=start<=end<=date.today() and (end-start).days<=731):
                raise ValueError('เลือกพิกัดประเทศไทยและช่วงเวลาไม่เกินสองปี ตั้งแต่ปี 1981 ถึงปัจจุบัน')
            self.send_json(200,fetch_weather(lat,lon,start,end))
        except (ValueError,KeyError) as e:self.send_json(400,{'error':str(e)})
        except Exception as e:self.send_json(502,{'error':str(e)})
    def do_POST(self):
        if self.private_route():return self.serve_private()
        if urlparse(self.path).path!='/api/weather-export':self.send_error(404);return
        origin=self.headers.get('Origin')
        port=self.server.server_port
        if origin and origin not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}'):
            self.send_json(403,{'error':'บันทึกได้จากหน้าโครงการในเครื่องเท่านั้น'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2_100_000:raise ValueError('ขนาดคำขอไม่ถูกต้อง')
            if 'application/json' not in self.headers.get('Content-Type',''):
                raise ValueError('ต้องส่งข้อมูล JSON')
            payload=json.loads(self.rfile.read(size))
            self.send_json(200,save_weather_export(payload))
        except (ValueError,KeyError,TypeError) as e:self.send_json(400,{'error':str(e)})
        except OSError:self.send_json(500,{'error':'บันทึกไฟล์ในเครื่องไม่สำเร็จ ตรวจสิทธิ์โฟลเดอร์ exports'})
    def do_PATCH(self):
        if self.private_route():return self.serve_private()
        self.send_error(404)
    def send_json(self,status,payload):
        body=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
from functools import lru_cache

@lru_cache(maxsize=1)
def private_application():
    from serve_orchard_cloud import create_app
    return create_app()

if __name__=='__main__':
    from open_orchard_report import load_local_settings
    load_local_settings()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8871)
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Port must be between 1024 and 65535')
    print(f'http://127.0.0.1:{args.port}/research_data/five_province_history/UNIFIED_MAP.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
