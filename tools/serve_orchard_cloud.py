"""Authenticated cloud wrapper; same provincial ML, live Supabase, no training on request."""
import hmac
import hashlib
import json
import os
import secrets
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, abort, jsonify, redirect, request, send_file, session, render_template_string

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from serve_orchard_analysis import fetch_weather, project_identity, save_weather_export
from orchard_current_context import province_estimate, province_forecast_readiness
from supabase_orchard import live_status, orchard_history
from orchard_harvest import HarvestStore, HarvestConflict, owner_key, public_record, baselines, training_candidates
from orchard_forecast import ForecastService, location_config
from orchard_private_assets import ASSETS, signed_asset

LOGIN_PAGE='''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} — ข้อมูลสวนทุเรียน</title><style>
:root{font-family:"Epilogue",Tahoma,Arial,sans-serif;color:#303b23;background:#8B9D83;--accent:#606C38}
*{box-sizing:border-box}body{margin:0;min-height:100dvh;background:radial-gradient(ellipse at 10% 90%,#606C38 0,transparent 55%)}main{max-width:1080px;min-height:100dvh;margin:auto;padding:48px 32px;display:grid;grid-template-columns:1.2fr 1fr;align-items:center;gap:64px}
header{color:#E8DCC7}h1{font-size:clamp(28px,4vw,44px);line-height:1.4;margin:16px 0 20px;letter-spacing:-.6px}p{font-size:16px;line-height:1.85}header p{max-width:450px}header p:last-child{font-size:14px}
.durian-art{width:220px;height:170px;display:block;filter:drop-shadow(0 16px 14px #303b2333)}
section{background:#E8DCC7;border:1px solid #D4B895;border-radius:28px;padding:36px;box-shadow:0 20px 60px #303b2326}h2{font-size:26px;margin:0 0 12px}label{display:block;font-size:15px;font-weight:600;margin:22px 0 8px}
input{font:inherit;width:100%;padding:14px;border:1px solid #B08B6E;border-radius:16px;background:#E8DCC7;color:#303b23;min-height:50px}button{font:inherit;font-weight:700;width:100%;min-height:50px;padding:14px;border:0;border-radius:16px;background:var(--accent);color:#E8DCC7;cursor:pointer;margin-top:26px;transition:background .3s ease}button:hover{background:#303b23}
input:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid #C08E3A;outline-offset:3px}a{color:var(--accent)}.error{border-left:3px solid #C66B3D;padding:10px;background:#D4B895;border-radius:16px}section>p:last-child{font-size:13px;color:#5b6048;margin-top:24px;overflow-wrap:anywhere}
@media(max-width:640px){main{grid-template-columns:1fr;gap:28px;padding:28px 20px;align-content:center}section{padding:24px}.durian-art{width:140px;height:105px}header h1{font-size:28px;margin:8px 0}header p{margin:8px 0}}
@media(prefers-reduced-motion:reduce){button{transition:none}}
</style><main><header><svg class="durian-art" viewBox="0 0 220 170" aria-hidden="true"><path d="M110 36Q109 9 130 8" fill="none" stroke="#303b23" stroke-width="9" stroke-linecap="round"/><path d="M121 24Q160 0 184 28Q147 48 121 24" fill="#606C38" stroke="#E8DCC7" stroke-width="2"/><path d="M103 35L118 31 129 40 145 37 151 52 168 55 170 72 181 85 172 100 176 119 159 127 152 145 133 145 119 155 102 148 83 153 72 139 54 133 54 114 42 101 51 85 48 67 66 59 74 42 92 45Z" fill="#606C38" stroke="#D4B895" stroke-width="3"/><path d="M109 46Q172 92 116 143Q57 101 109 46Z" fill="#C08E3A" stroke="#E8DCC7" stroke-width="5"/><path d="M109 56Q126 76 111 91Q94 74 109 56M111 92Q138 109 117 132Q92 120 111 92" fill="#D4B895"/><path d="M64 73L71 80M59 100L68 99M75 124L83 117M146 67L140 76M159 99L150 97M142 131L135 121" stroke="#8B9D83" stroke-width="5" stroke-linecap="round"/></svg><h1>ข้อมูลสวนทุเรียน<br>และผลผลิต 5 จังหวัด</h1><p>ดูข้อมูลสวน สภาพอากาศ ดิน และผลประมาณการระดับจังหวัดในหน้าเดียว</p><p>เว็บส่วนตัวสำหรับเจ้าของสวนและผู้ร่วมดูที่ได้รับรหัสผ่าน</p></header>
<section aria-labelledby="login-title"><h2 id="login-title">{{ title }}</h2>{% if error %}<p role="alert" class="error">{{ error }}</p>{% endif %}
<form method="post"><input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="next" value="{{ next_page }}">
{% if not logout %}<label for="username">ชื่อผู้ใช้</label><input id="username" name="username" autocomplete="username" required maxlength="128" value="{{ username }}">
<label for="password">รหัสผ่าน</label><input id="password" name="password" type="password" autocomplete="current-password" required maxlength="512">
<button type="button" id="toggle-password" class="password-toggle" aria-controls="password" aria-pressed="false">แสดงรหัสผ่าน</button>
{% else %}<p>ต้องการออกจากระบบบนเบราว์เซอร์นี้หรือไม่?</p>{% endif %}
<button type="submit" id="auth-submit">{{ title }}</button></form>
{% if logout %}<p><a href="/">อยู่ในระบบต่อ / กลับไปแดชบอร์ด</a></p>{% else %}<p>เข้าสู่ระบบเพื่อดูเซนเซอร์และประวัติผลผลิตส่วนตัว เมื่อเข้าสู่ระบบสำเร็จจะกลับไปหน้าที่เลือกไว้</p><p>ใช้บัญชีสวนที่ผู้ดูแลจัดให้ หากไม่ทราบรหัสผ่านให้สอบถามผู้ดูแล ไม่ใช้รหัสบัญชี Supabase</p><p><a href="/research_data/five_province_history/UNIFIED_MAP.html">กลับหน้าหลัก</a></p>{% endif %}
</section></main><style>
:root{font-family:Tahoma,"Segoe UI",Arial,sans-serif;color:#193c32;background:#f2f6f4;--accent:#187456}body{background:radial-gradient(ellipse at 10% 90%,#d8eadd 0,transparent 55%)}header{color:#174d3b}header p{color:#5d766a}section{background:#fff;border-color:#dce7df;box-shadow:0 20px 60px #174b2a10}input{background:#fafcfb;color:#193c32;border-color:#ccdcd2;border-radius:12px}button{border-radius:12px;color:#fff;margin-top:22px}button:hover{background:#105c41}button:disabled{opacity:.65;cursor:wait}.password-toggle{display:block;width:auto;min-height:0;margin:9px 0 0 auto;padding:5px 9px;background:transparent;color:#187456;font-size:13px}.password-toggle:hover{background:#eff7f1;color:#105c41}.error{background:#fff0e8;color:#8e452d;border-color:#c77c4c}section>p:last-child{color:#64776d}a{color:#187456}
</style><script>
const toggle=document.getElementById('toggle-password');if(toggle)toggle.addEventListener('click',()=>{const input=document.getElementById('password');const show=input.type==='password';input.type=show?'text':'password';toggle.setAttribute('aria-pressed',String(show));toggle.textContent=show?'ซ่อนรหัสผ่าน':'แสดงรหัสผ่าน';});
document.querySelector('form').addEventListener('submit',()=>{const button=document.getElementById('auth-submit');button.disabled=true;button.textContent='กำลังดำเนินการ…';});
</script></html>'''


def create_app():
    username=os.environ.get('DASHBOARD_USER','owner')
    password=os.environ.get('DASHBOARD_PASSWORD','')
    if len(password)<16:raise RuntimeError('ตั้ง DASHBOARD_PASSWORD อย่างน้อย 16 ตัวอักษรก่อนเปิดเว็บ')
    accounts={username:password}
    if os.environ.get('DASHBOARD_USERS_JSON'):
        try:extra=json.loads(os.environ['DASHBOARD_USERS_JSON'])
        except ValueError as exc:raise RuntimeError('DASHBOARD_USERS_JSON ไม่ถูกต้อง') from exc
        if (not isinstance(extra,dict) or len(extra)>50 or any(not isinstance(k,str) or not 1<=len(k)<=128
                or not isinstance(v,str) or len(v)<16 for k,v in extra.items())):
            raise RuntimeError('บัญชีเพิ่มเติมต้องมีชื่อและรหัสผ่านอย่างน้อย 16 ตัวอักษร')
        accounts.update(extra)
    app=Flask(__name__,static_folder=None)
    app.config['HARVEST_STORE']=HarvestStore()
    app.config['FORECAST_SERVICE']=ForecastService()
    app.config['MAX_CONTENT_LENGTH']=2_100_000
    app.config.update(SECRET_KEY=hashlib.sha256(('orchard-session-v1:'+password).encode()).digest(),
        SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=(os.environ.get('RENDER')=='true' or os.environ.get('VERCEL')=='1'),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),SESSION_REFRESH_EACH_REQUEST=False)

    def csrf_valid():
        token=session.get('csrf')
        return bool(token) and hmac.compare_digest(request.form.get('csrf','').encode(),token.encode())

    def auth_page(logout=False,error=None,status=200):
        if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
        return render_template_string(LOGIN_PAGE,title='ออกจากระบบ' if logout else 'เข้าสู่ระบบ',
            logout=logout,error=error,csrf=session['csrf'],username=username,local=not (os.environ.get('RENDER')=='true' or os.environ.get('VERCEL')=='1'),next_page=next_page()),status

    def next_page():
        base='/research_data/five_province_history/UNIFIED_MAP.html'
        candidate=request.values.get('next',base)
        path,separator,fragment=candidate.partition('#')
        return candidate if path in (base,'/home','/map','/weather','/yield','/seasons') and fragment in ('','home','map','weather','yield','seasons') else base

    @app.before_request
    def authenticate():
        if request.path=='/healthz':return None
        if (os.environ.get('RENDER')=='true' or os.environ.get('VERCEL')=='1') and request.headers.get('X-Forwarded-Proto')!='https':
            return jsonify(error='HTTPS required'),400
        if request.path=='/login':return None
        if session.get('authenticated') is not True or session.get('principal',username) not in accounts:
            if request.path.startswith('/api/'):return jsonify(error='กรุณาเข้าสู่ระบบ',login_url='/login'),401
            return redirect('/login?next='+request.path) if request.path in ('/home','/map','/weather','/yield','/seasons') else redirect('/login')

    @app.after_request
    def security_headers(response):
        response.headers['Cache-Control']='private, no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        # OSM needs an identifying Referer; cross-origin requests expose only our public origin.
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        if (os.environ.get('RENDER')=='true' or os.environ.get('VERCEL')=='1'):response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.get('/healthz')
    def health():return jsonify(status='ok')

    @app.route('/login',methods=['GET','POST'])
    def login():
        if request.method=='POST':
            if not csrf_valid():return auth_page(error='หน้าเข้าสู่ระบบหมดอายุ กรุณาโหลดหน้าใหม่',status=403)
            principal=request.form.get('username','')
            expected=accounts.get(principal)
            if not expected or not hmac.compare_digest(request.form.get('password','').encode(),expected.encode()):
                return auth_page(error='ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง',status=401)
            session.clear();session['authenticated']=True;session['principal']=principal;session.permanent=True
            session['csrf']=secrets.token_urlsafe(32)
            return redirect(next_page())
        return redirect(next_page()) if session.get('authenticated') else auth_page()

    @app.route('/logout',methods=['GET','POST'])
    def logout():
        if request.method=='POST':
            if not csrf_valid():abort(403)
            session.clear();return redirect('/login')
        return auth_page(logout=True)

    @app.get('/')
    def home():return redirect('/home')

    @app.get('/home')
    @app.get('/map')
    @app.get('/weather')
    @app.get('/yield')
    @app.get('/seasons')
    def dashboard_page():
        html=(ROOT/'research_data/five_province_history/UNIFIED_MAP.html').read_text(encoding='utf-8')
        return html if '<base ' in html else html.replace('<head>','<head><base href="/research_data/five_province_history/">',1)

    @app.get('/api/project')
    def identity():
        payload=project_identity(source='supabase')
        payload.update(mode='cloud',orchard_source='supabase')
        payload['capabilities']['gap_registry']={'available':False,
            'message':'เว็บ cloud นี้ยังไม่เปิดชั้นหมุด GAP ให้ใช้แผนที่ GAP ในเครื่องจาก branch codex/organize-project การ push Git ไม่ใช่การเปิดข้อมูลบน cloud'}
        if os.environ.get('VERCEL')=='1' and os.environ.get('ORCHARD_GIS_PRIVATE_BUCKET'):
            payload['capabilities']['gap_registry']={'available':True,
                'message':'ใช้ GIS ส่วนตัวตามสิทธิ์บัญชีผ่าน signed URL ของเซิร์ฟเวอร์นี้ ไม่ใช่ข้อมูล public'}
        payload['capabilities']['orchard'].update(source='supabase',configured=payload['capabilities']['orchard']['history_configured'])
        return jsonify(payload)

    @app.get('/api/orchard-status')
    def orchard():
        if session.get('principal',username)!=username:abort(403)
        return jsonify(live_status())

    @app.get('/api/orchard-history')
    def history():
        if session.get('principal',username)!=username:abort(403)
        return jsonify(orchard_history(request.args.get('period','day'),end=request.args.get('end'),start_date=request.args.get('start')))

    @app.get('/api/orchard-forecast')
    def orchard_forecast():
        # A GAP selection never changes ownership or the configured sensor orchard.
        if request.args:raise ValueError('ไม่รับพิกัดหรือบัญชีจาก URL')
        config=location_config()
        if session.get('principal')!=config['owner_account']:
            return jsonify(error='พยากรณ์นี้เป็นข้อมูลส่วนตัวของบัญชีสวนที่ยืนยันพิกัด บัญชีนี้ไม่มีสิทธิ์อ่าน'),403
        if config['owner_account']!=username or config['sensor_device_id']!=os.environ.get('ORCHARD_DEVICE_ID'):
            return jsonify(error='ยังยืนยันการเชื่อมพิกัดสวนกับจุดเซนเซอร์ไม่ได้ จึงยังไม่แสดงพยากรณ์'),403
        value=app.config['FORECAST_SERVICE'].get(config)
        value['orchard_key']=config['orchard_key']
        value['coordinate_basis']='owner_confirmed_sensor_orchard'
        value['coordinate_confirmed_at']=config['confirmed_at']
        value['sensor_link_confirmed']=True
        value['account']=session['principal']
        return jsonify(value)

    def harvest_owner():
        principal=session.get('principal')
        if principal not in accounts:abort(401)
        return owner_key(principal)

    def harvest_write():
        origin=request.headers.get('Origin')
        if origin and origin not in ('https://'+request.host,'http://'+request.host):abort(403)
        token=session.get('csrf','')
        if not token or not hmac.compare_digest(request.headers.get('X-CSRF-Token','').encode(),token.encode()):abort(403)
        if not request.is_json:raise ValueError('ต้องส่ง JSON')
        return request.get_json()

    @app.get('/api/orchard-session')
    def orchard_session():
        harvest_owner()
        return jsonify(csrf=session['csrf'],account=session['principal'],storage='Supabase',auto_train=False)

    @app.get('/api/orchard-harvest')
    def harvest_list():
        rows=app.config['HARVEST_STORE'].list(harvest_owner())
        return jsonify(records=[public_record(r) for r in rows],baselines=baselines(rows),auto_train=False,
            verification='ผู้ใช้รายงาน ยังไม่ตรวจหลักฐานอิสระ',storage='Supabase')

    @app.post('/api/orchard-harvest')
    def harvest_create():
        return jsonify(record=app.config['HARVEST_STORE'].create(harvest_owner(),harvest_write())),201

    @app.patch('/api/orchard-harvest/<uuid:record_id>')
    def harvest_update(record_id):
        try:record=app.config['HARVEST_STORE'].update(harvest_owner(),str(record_id),harvest_write())
        except LookupError:abort(404)
        return jsonify(record=record)

    @app.get('/api/orchard-harvest/export')
    def harvest_export():
        rows=app.config['HARVEST_STORE'].list(harvest_owner())
        return jsonify(records=[public_record(r) for r in rows],candidate_pairs=training_candidates(rows),
            auto_train=False,training_ready_verified=False,public_release='HOLD',
            warning='ข้อมูลเฉพาะบัญชีนี้; ต้องตรวจหลักฐานและเวลาเผยแพร่ก่อนฝึก แยกตามปีและสวน ไม่ใช่ข้อมูลพยากรณ์ที่รับรองแล้ว')

    @app.get('/api/province-forecast-readiness')
    def forecast_readiness():return jsonify(province_forecast_readiness())

    @app.get('/api/province-estimate')
    def province():
        today=datetime.now(ZoneInfo('Asia/Bangkok')).date()
        return jsonify(province_estimate(request.args['province'],int(request.args['year']),fetch_weather,today=today))

    @app.get('/api/weather')
    def weather():
        lat,lon=float(request.args['lat']),float(request.args['lon'])
        start,end=date.fromisoformat(request.args['start']),date.fromisoformat(request.args['end'])
        today=datetime.now(ZoneInfo('Asia/Bangkok')).date()
        if not (5<=lat<=21 and 97<=lon<=106 and date(1981,1,1)<=start<=end<=today and (end-start).days<=731):
            raise ValueError('เลือกพิกัดประเทศไทยและช่วงเวลาไม่เกินสองปี')
        return jsonify(fetch_weather(lat,lon,start,end))

    @app.post('/api/weather-export')
    def export():
        origin=request.headers.get('Origin')
        if origin and origin not in ('https://'+request.host,'http://'+request.host):abort(403)
        if not request.is_json:raise ValueError('ต้องส่ง JSON')
        return jsonify(save_weather_export(request.get_json()))

    @app.get('/research_data/<path:name>')
    def assets(name):
        if os.environ.get('VERCEL')=='1' and os.environ.get('ORCHARD_GIS_PRIVATE_BUCKET') and name in ASSETS:
            return redirect(signed_asset(name),code=302)
        path=(ROOT/'research_data'/name).resolve()
        roots=[ROOT/'research_data'/p for p in ('five_province_history','priority_provinces','thailand_comparison','regional_orchards')]
        if not any(path.is_relative_to(p.resolve()) for p in roots) or not path.is_file():abort(404)
        # Precise GAP coordinates and exploratory preparations are local-only.
        # Public publication needs a separate privacy/source-terms review.
        if any(path.is_relative_to((ROOT/'research_data/five_province_history'/folder).resolve())
               for folder in ('gap_orchards','gap_spatial_experiment')):abort(404)
        if any(p.startswith('.') or p=='point_weather_cache' for p in path.relative_to(ROOT).parts):abort(404)
        if 'exports' in path.relative_to(ROOT).parts and session.get('principal',username)!=username:abort(404)
        if path.suffix.lower() not in {'.html','.js','.css','.json','.geojson','.csv','.md','.png','.svg','.jpg'}:abort(404)
        return send_file(path)

    @app.errorhandler(ValueError)
    @app.errorhandler(KeyError)
    def bad_input(error):return jsonify(error='พารามิเตอร์ไม่ถูกต้องหรือข้อมูลที่จำเป็นไม่ครบ'),400

    @app.errorhandler(RuntimeError)
    def unavailable(error):return jsonify(error=str(error)),503

    @app.errorhandler(HarvestConflict)
    def harvest_conflict(error):return jsonify(error=str(error)),409

    @app.errorhandler(500)
    def server_error(error):return jsonify(error='ระบบคำนวณไม่สำเร็จ ตรวจบันทึกฝั่งเซิร์ฟเวอร์'),500
    return app


if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=int(os.environ.get('PORT','8873')),debug=False)
