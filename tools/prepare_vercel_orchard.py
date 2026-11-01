"""Prepare a bounded, private Vercel deployment; never upload the project root."""
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.build/vercel_orchard'
TOOLS=['serve_orchard_cloud.py','serve_orchard_analysis.py','orchard_current_context.py',
       'supabase_orchard.py','orchard_harvest.py','orchard_forecast.py','clean_stale_weather.py',
       'train_monthly_production.py','compare_harvest_stage_yield.py','analyze_harvest_backcast.py','durian_model/common.py','orchard_private_assets.py']

def prepare(private_gis=False):
    out=ROOT/'.build/vercel_orchard_private' if private_gis else OUT
    files={}
    def copy(source,target=None):
        files[target or source]=(ROOT/source).read_bytes()
    for name in TOOLS:copy('tools/'+name)
    copy('ml/orchard_live_model.py');copy('models/orchard_soil_6h.json')
    for name in ['production_annual.csv','harvest_monthly.csv','weather_daily.csv','reference_points.csv']:
        copy('research_data/five_province_history/'+name)
    for name in ['ridge_vpd_final_model.json','ridge_vpd_audit.json']:
        copy('research_data/five_province_history/training/'+name)
    base='research_data/five_province_history/'
    for name in ['orchard_app.js','orchard_app.css']:copy(base+name)
    html=(ROOT/base/'UNIFIED_MAP.html').read_text(encoding='utf-8')
    match=re.search(r'const DATA=(.*?);window\.__ORCHARD_DATA__',html,re.S)
    if not match:raise RuntimeError('Build the reviewed React HTML first')
    data=json.loads(match[1])
    # Derived GIS and registry coordinates remain local (Public HOLD).
    if not private_gis:
        data.update(boundaries={'type':'FeatureCollection','features':[]},districts=[],soil_properties=[],district_exploration=[])
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html=html[:match.start(1)]+payload+html[match.end(1):]
    files[base+'UNIFIED_MAP.html']=html.encode()
    for name in ['app.py','vercel.json','requirements.txt','pyproject.toml','.vercelignore']:
        copy('deployment/vercel/'+name,name)
    # Unexpected files fail closed; do not silently retain or recursively remove old contents.
    expected=set(files)|{'deployment_manifest.json'}
    if out.exists():
        extra=[p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()
               and p.relative_to(out).as_posix() not in expected and '.vercel' not in p.relative_to(out).parts]
        if extra:raise RuntimeError('Unexpected files in deployment folder; review before upload: '+str(extra))
    for name,body in files.items():
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
    manifest={'public_release':'HOLD','excluded':['all .secrets','GAP registry / precise orchard coordinates','all soil GeoJSON / derived GIS','private exports / IoT snapshots'],
              'files':{name:hashlib.sha256(body).hexdigest() for name,body in files.items()},'bytes':sum(map(len,files.values()))}
    if private_gis:
        manifest['requires_private_gis_upload_approval']=True
        manifest['excluded']=['all .secrets','raw personal registry','sensor snapshots / exports','GeoJSON bodies (private Storage only)']
    (out/'deployment_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--private-gis',action='store_true');args=parser.parse_args()
    result=prepare(args.private_gis);print('Prepared',len(result['files']),'files;',result['bytes'],'bytes;', 'private GIS variant' if args.private_gis else str(OUT))
