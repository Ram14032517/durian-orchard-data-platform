"""Authenticated cloud wrapper; same provincial ML, live Supabase, no training on request."""
import hmac
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, Response, abort, jsonify, redirect, request, send_file

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from serve_orchard_analysis import fetch_weather, project_identity, save_weather_export
from orchard_current_context import province_estimate
from supabase_orchard import live_status


def create_app():
    username=os.environ.get('DASHBOARD_USER','owner')
    password=os.environ.get('DASHBOARD_PASSWORD','')
    if len(password)<16:raise RuntimeError('ตั้ง DASHBOARD_PASSWORD อย่างน้อย 16 ตัวอักษรก่อนเปิดเว็บ')
    app=Flask(__name__,static_folder=None)
    app.config['MAX_CONTENT_LENGTH']=2_100_000

    @app.before_request
    def authenticate():
        if request.path=='/healthz':return None
        if os.environ.get('RENDER')=='true' and request.headers.get('X-Forwarded-Proto')!='https':
            return jsonify(error='HTTPS required'),400
        auth=request.authorization
        if not (auth and auth.type.lower()=='basic' and hmac.compare_digest((auth.username or '').encode(),username.encode())
                and hmac.compare_digest((auth.password or '').encode(),password.encode())):
            return Response('กรุณาเข้าสู่ระบบ',401,{'WWW-Authenticate':'Basic realm="Orchard", charset="UTF-8"'})

    @app.after_request
    def security_headers(response):
        response.headers['Cache-Control']='private, no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        if os.environ.get('RENDER')=='true':response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.get('/healthz')
    def health():return jsonify(status='ok')

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
