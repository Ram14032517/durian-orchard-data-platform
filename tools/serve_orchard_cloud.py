"""Authenticated cloud wrapper; same provincial ML, live Supabase, no training on request."""
import hmac
import hashlib
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
from orchard_current_context import province_estimate
from supabase_orchard import live_status

LOGIN_PAGE='''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} — ข้อมูลสวนทุเรียน</title><style>
:root{font-family:"Helvetica Neue",Arial,sans-serif;color:#171717;background:#F7F7F8;--accent:#002FA7}
*{box-sizing:border-box}body{margin:0}main{max-width:960px;margin:10vh auto;padding:24px;display:grid;grid-template-columns:1.2fr 1fr;gap:48px}
header{border-top:6px solid var(--accent);padding-top:24px}h1{font-size:clamp(26px,4vw,40px);line-height:1.4;margin:0 0 20px}p{font-size:17px;line-height:1.8;color:#454545}
section{background:#fff;border:1px solid #d5d5d8;padding:28px}h2{font-size:24px;margin:0 0 24px}label{display:block;font-size:17px;font-weight:600;margin:18px 0 8px}
input{font:inherit;width:100%;padding:13px;border:1px solid #777;min-height:48px}button{font:inherit;width:100%;min-height:48px;padding:12px;border:0;background:var(--accent);color:#fff;cursor:pointer;margin-top:24px}
input:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid var(--accent);outline-offset:3px}a{color:var(--accent)}.error{border-left:3px solid var(--accent);padding:10px;background:#F7F7F8}
@media(max-width:640px){main{grid-template-columns:1fr;margin:24px auto;gap:24px;padding:20px}section{padding:24px}}
</style><main><header><h1>ข้อมูลสวนทุเรียน<br>และผลผลิต 5 จังหวัด</h1><p>ดูข้อมูลสวน สภาพอากาศ ดิน และผลประมาณการระดับจังหวัดในหน้าเดียว</p><p>เว็บส่วนตัวสำหรับเจ้าของสวนและผู้ร่วมดูที่ได้รับรหัสผ่าน</p></header>
<section aria-labelledby="login-title"><h2 id="login-title">{{ title }}</h2>{% if error %}<p role="alert" class="error">{{ error }}</p>{% endif %}
<form method="post"><input type="hidden" name="csrf" value="{{ csrf }}">
{% if not logout %}<label for="username">ชื่อผู้ใช้</label><input id="username" name="username" autocomplete="username" required maxlength="128" value="{{ username }}">
<label for="password">รหัสผ่าน</label><input id="password" name="password" type="password" autocomplete="current-password" required maxlength="512">
{% else %}<p>ต้องการออกจากระบบบนเบราว์เซอร์นี้หรือไม่?</p>{% endif %}
<button type="submit">{{ title }}</button></form>
{% if logout %}<p><a href="/">กลับไปแดชบอร์ด</a></p>{% else %}<p>ใช้รหัสที่ตั้งไว้ใน Render หากลืมรหัส เจ้าของตรวจได้ที่ DASHBOARD_PASSWORD ใน Environment</p>{% endif %}
</section></main></html>'''


def create_app():
    username=os.environ.get('DASHBOARD_USER','owner')
    password=os.environ.get('DASHBOARD_PASSWORD','')
    if len(password)<16:raise RuntimeError('ตั้ง DASHBOARD_PASSWORD อย่างน้อย 16 ตัวอักษรก่อนเปิดเว็บ')
    app=Flask(__name__,static_folder=None)
    app.config['MAX_CONTENT_LENGTH']=2_100_000
    app.config.update(SECRET_KEY=hashlib.sha256(('orchard-session-v1:'+password).encode()).digest(),
        SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('RENDER')=='true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),SESSION_REFRESH_EACH_REQUEST=False)

    def csrf_valid():
        token=session.get('csrf')
        return bool(token) and hmac.compare_digest(request.form.get('csrf','').encode(),token.encode())

    def auth_page(logout=False,error=None,status=200):
        if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
        return render_template_string(LOGIN_PAGE,title='ออกจากระบบ' if logout else 'เข้าสู่ระบบ',
            logout=logout,error=error,csrf=session['csrf'],username=username),status

    @app.before_request
    def authenticate():
        if request.path=='/healthz':return None
        if os.environ.get('RENDER')=='true' and request.headers.get('X-Forwarded-Proto')!='https':
            return jsonify(error='HTTPS required'),400
        if request.path=='/login':return None
        if session.get('authenticated') is not True:
            if request.path.startswith('/api/'):return jsonify(error='กรุณาเข้าสู่ระบบ',login_url='/login'),401
            return redirect('/login')

    @app.after_request
    def security_headers(response):
        response.headers['Cache-Control']='private, no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        # OSM needs an identifying Referer; cross-origin requests expose only our public origin.
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        if os.environ.get('RENDER')=='true':response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.get('/healthz')
    def health():return jsonify(status='ok')

    @app.route('/login',methods=['GET','POST'])
    def login():
        if request.method=='POST':
            if not csrf_valid():return auth_page(error='หน้าเข้าสู่ระบบหมดอายุ กรุณาโหลดหน้าใหม่',status=403)
            if not (hmac.compare_digest(request.form.get('username','').encode(),username.encode()) and
                    hmac.compare_digest(request.form.get('password','').encode(),password.encode())):
                return auth_page(error='ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง',status=401)
            session.clear();session['authenticated']=True;session.permanent=True
            session['csrf']=secrets.token_urlsafe(32)
            return redirect('/')
        return redirect('/') if session.get('authenticated') else auth_page()

    @app.route('/logout',methods=['GET','POST'])
    def logout():
        if request.method=='POST':
            if not csrf_valid():abort(403)
            session.clear();return redirect('/login')
        return auth_page(logout=True)

    @app.get('/')
    def home():return redirect('/research_data/five_province_history/UNIFIED_MAP.html')

    @app.get('/api/project')
    def identity():return jsonify(**project_identity(),mode='cloud',orchard_source='supabase')

    @app.get('/api/orchard-status')
    def orchard():return jsonify(live_status())

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
        path=(ROOT/'research_data'/name).resolve()
        roots=[ROOT/'research_data'/p for p in ('five_province_history','priority_provinces','thailand_comparison','regional_orchards')]
        if not any(path.is_relative_to(p.resolve()) for p in roots) or not path.is_file():abort(404)
        if any(p.startswith('.') or p=='point_weather_cache' for p in path.relative_to(ROOT).parts):abort(404)
        if path.suffix.lower() not in {'.html','.js','.css','.json','.geojson','.csv','.md','.png','.svg','.jpg'}:abort(404)
        return send_file(path)

    @app.errorhandler(ValueError)
    @app.errorhandler(KeyError)
    def bad_input(error):return jsonify(error='พารามิเตอร์ไม่ถูกต้องหรือข้อมูลที่จำเป็นไม่ครบ'),400

    @app.errorhandler(RuntimeError)
    def unavailable(error):return jsonify(error=str(error)),503

    @app.errorhandler(500)
    def server_error(error):return jsonify(error='ระบบคำนวณไม่สำเร็จ ตรวจบันทึกฝั่งเซิร์ฟเวอร์'),500
    return app


if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=int(os.environ.get('PORT','8873')),debug=False)
