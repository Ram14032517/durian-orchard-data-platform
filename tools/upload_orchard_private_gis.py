"""Owner-authorized private GIS upload. No raw registry, credentials or coordinates in output."""
import hashlib
import os
from pathlib import Path
import requests
from orchard_private_assets import ASSETS

ROOT=Path(__file__).resolve().parents[1]
BUCKET='durian-gis-private'

def upload():
    from open_orchard_report import load_local_settings
    load_local_settings()
    base=os.environ['SUPABASE_URL'].rstrip('/')+'/storage/v1'
    key=os.environ.get('SUPABASE_SECRET_KEY') or os.environ['SUPABASE_SERVICE_ROLE_KEY']
    headers={'apikey':key}
    if not key.startswith('sb_secret_'):headers['Authorization']='Bearer '+key
    session=requests.Session();session.headers.update(headers)
    def call(method,path,**kwargs):return session.request(method,base+path,timeout=(10,90),allow_redirects=False,**kwargs)
    r=call('GET','/bucket/'+BUCKET)
    if r.status_code==404 or (r.status_code==400 and str(r.json().get('statusCode'))=='404'):
        r=call('POST','/bucket',json={'id':BUCKET,'name':BUCKET,'public':False,'allowed_mime_types':['application/geo+json','application/json'],'file_size_limit':20_000_000})
        if r.status_code not in (200,201):raise RuntimeError('Cannot create private bucket; no details logged')
        r=call('GET','/bucket/'+BUCKET)
    if r.status_code!=200 or r.json().get('public') is not False:raise RuntimeError('Bucket must be verified PRIVATE before any upload')
    for name in sorted(ASSETS):
        data=(ROOT/'research_data'/name).read_bytes();digest=hashlib.sha256(data).hexdigest()
        url='/object/'+BUCKET+'/'+name
        prior=call('GET','/object/authenticated/'+BUCKET+'/'+name)
        if prior.status_code==200:
            if hashlib.sha256(prior.content).hexdigest()!=digest:raise RuntimeError('Existing object differs; refusing overwrite: '+name)
            print('Verified existing',name,flush=True);continue
        if prior.status_code not in (400,404):raise RuntimeError('Cannot verify existing object')
        r=call('POST',url,data=data,headers={'Content-Type':'application/geo+json' if name.endswith('.geojson') else 'application/json','x-upsert':'false'})
        if r.status_code not in (200,201):raise RuntimeError('Upload did not succeed: '+name)
        check=call('GET','/object/authenticated/'+BUCKET+'/'+name)
        if check.status_code!=200 or hashlib.sha256(check.content).hexdigest()!=digest:raise RuntimeError('Uploaded hash mismatch: '+name)
        print('Uploaded and hash verified',name,len(data),'bytes',flush=True)
    print('Verified PRIVATE bucket; all',len(ASSETS),'assets verified; public release remains HOLD')

if __name__=='__main__':upload()
