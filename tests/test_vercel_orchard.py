"""Exercise the actual isolated deploy package, with synthetic credentials only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from prepare_vercel_orchard import OUT,prepare

class VercelTests(unittest.TestCase):
    def test_package_allowlist_and_no_derived_geometry(self):
        result=prepare()
        self.assertLess(result['bytes'],20_000_000)
        self.assertFalse(any('.secrets' in p or 'gap_orchards' in p or p.endswith('.geojson') for p in result['files']))
        html=(OUT/'research_data/five_province_history/UNIFIED_MAP.html').read_text(encoding='utf-8')
        import re
        data=json.loads(re.search(r'const DATA=(.*?);window\.__ORCHARD_DATA__',html,re.S)[1])
        self.assertEqual(data['boundaries']['features'],[]);self.assertEqual(data['soil_properties'],[])
        self.assertEqual(data['districts'],[]);self.assertIn('Public HOLD',html)

    def test_deployment_auth_secure_cookies_and_tmp_cache(self):
        prepare()
        script="""
import app,serve_orchard_analysis as backend
from pathlib import Path
c=app.app.test_client();h={'X-Forwarded-Proto':'https'}
assert c.get('/healthz',headers=h).status_code==200
assert c.get('/api/orchard-status',headers=h).status_code==401
assert c.get('/research_data/five_province_history/orchard_app.js',headers=h).status_code==302
r=c.get('/login',headers=h)
assert 'Secure;' in r.headers['Set-Cookie']
with c.session_transaction() as s: token=s['csrf']
assert c.post('/login',data={'csrf':token,'username':'owner','password':'synthetic-vercel-password-123'},headers=h).status_code==302
assert c.get('/research_data/five_province_history/UNIFIED_MAP.html',headers=h).status_code==200
assert c.get('/research_data/five_province_history/orchard_app.js',headers=h).status_code==200
assert c.get('/research_data/five_province_history/gap_orchards/manifest.json',headers=h).status_code==404
assert c.get('/research_data/priority_provinces/soil_layers/22.geojson',headers=h).status_code==404
assert c.get('/.secrets/supabase_local.json',headers=h).status_code==404
assert c.get('/api/orchard-forecast',headers=h).status_code==503
assert c.get('/login',headers={'X-Forwarded-Proto':'http'}).status_code==400
assert backend.CACHE.is_relative_to(Path(app.tempfile.gettempdir()))
print('Isolated Vercel app smoke checks passed')
"""
        env={k:v for k,v in os.environ.items() if not k.startswith(('SUPABASE','DASHBOARD','ORCHARD'))}
        env.update(VERCEL='1',DASHBOARD_USER='owner',DASHBOARD_PASSWORD='synthetic-vercel-password-123',PYTHONDONTWRITEBYTECODE='1')
        r=subprocess.run([sys.executable,'-B','-c',script],cwd=OUT,env=env,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_unconfigured_deployment_never_serves_private_assets(self):
        prepare()
        env={k:v for k,v in os.environ.items() if not k.startswith(('SUPABASE','DASHBOARD','ORCHARD'))}
        env['PYTHONDONTWRITEBYTECODE']='1'
        script="import app; c=app.app.test_client(); assert c.get('/').status_code==503; assert c.get('/research_data/five_province_history/UNIFIED_MAP.html').status_code==503"
        r=subprocess.run([sys.executable,'-B','-c',script],cwd=OUT,env=env,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

if __name__=='__main__':unittest.main()
