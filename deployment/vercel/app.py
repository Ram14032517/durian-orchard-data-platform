"""Vercel Flask entrypoint; all assets remain behind existing authentication."""
import os
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
os.environ.setdefault('ORCHARD_RUNTIME_DIR',str(Path(tempfile.gettempdir())/'durian-orchard'))

from flask import Flask, jsonify
app=Flask(__name__,static_folder=None)
if len(os.environ.get('DASHBOARD_PASSWORD',''))<16:
    @app.route('/',defaults={'path':''})
    @app.route('/<path:path>')
    def not_configured(path):
        response=jsonify(error='ตั้ง Environment Variables ฝั่ง Vercel ก่อนใช้งาน; ยังไม่เปิดข้อมูลสวน')
        response.headers['Cache-Control']='private, no-store'
        return response,503
else:
    from serve_orchard_cloud import create_app
    app=create_app()
