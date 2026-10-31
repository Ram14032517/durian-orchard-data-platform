"""Short-lived private Storage links for the existing GIS asset URLs; no public buckets."""
import os
import re
from urllib.parse import urlsplit
import requests

CODES=('22','33','53','84','86')
ASSETS={'five_province_history/gap_orchards/manifest.json'}|{
    'five_province_history/gap_orchards/province_'+c+'.geojson' for c in CODES}|{
    'priority_provinces/soil_layers/'+c+'.geojson' for c in CODES}

def signed_asset(name):
    if name not in ASSETS:raise LookupError('Unapproved asset')
    base=os.environ.get('SUPABASE_URL','').rstrip('/')
    key=os.environ.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    bucket=os.environ.get('ORCHARD_GIS_PRIVATE_BUCKET','')
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',base) or not key or not re.fullmatch(r'[a-z0-9-]{1,63}',bucket):
        raise RuntimeError('ยังไม่เชื่อม Storage ส่วนตัวสำหรับ GAP/ดิน ไม่ใช้ข้อมูลสมมติแทน')
    headers={'apikey':key}
    if not key.startswith('sb_secret_'):headers['Authorization']='Bearer '+key
    try:
        r=requests.post(base+'/storage/v1/object/sign/'+bucket+'/'+name,json={'expiresIn':60},headers=headers,timeout=15,allow_redirects=False)
        if r.status_code!=200:raise ValueError()
        path=r.json().get('signedURL')
        if not isinstance(path,str) or not path.startswith('/object/sign/'+bucket+'/') or urlsplit(path).netloc or '?' not in path:raise ValueError()
        return base+'/storage/v1'+path
    except (requests.RequestException,ValueError,TypeError):
        raise RuntimeError('ยังสร้างลิงก์อ่านข้อมูลส่วนตัวไม่ได้ ตรวจ Bucket และสิทธิ์ฝั่งเซิร์ฟเวอร์') from None
