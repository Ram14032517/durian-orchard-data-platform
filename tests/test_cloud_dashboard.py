import base64
import os
import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, Mock

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from serve_orchard_cloud import create_app
from supabase_orchard import live_status, read_table
from clean_stale_weather import WEATHER


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'DASHBOARD_USER':'owner','DASHBOARD_PASSWORD':'test-password-123456789','RENDER':'false','ORCHARD_DEVICE_ID':'test-device'},clear=True)
        self.env.start()
        self.app=create_app();self.client=self.app.test_client()
        self.client.get('/login')
        with self.client.session_transaction() as state:self.csrf=state['csrf']
        self.client.post('/login',data={'csrf':self.csrf,'username':'owner','password':'test-password-123456789'})
        self.auth={}

    def tearDown(self):self.env.stop()

    def test_fail_closed_without_password(self):
        with patch.dict(os.environ,{'DASHBOARD_PASSWORD':''}):
            with self.assertRaises(RuntimeError):create_app()

    def test_every_page_and_api_requires_login_except_health(self):
        anonymous=self.app.test_client()
        self.assertEqual(anonymous.get('/healthz').status_code,200)
        for path in ['/','/api/project','/api/orchard-status','/api/province-estimate','/research_data/five_province_history/UNIFIED_MAP.html']:
            response=anonymous.get(path)
            self.assertEqual(response.status_code,401 if path.startswith('/api/') else 302)
            self.assertNotIn('WWW-Authenticate',response.headers)
        self.assertEqual(self.client.get('/api/project',headers=self.auth).status_code,200)

    def test_form_login_csrf_wrong_password_and_logout(self):
        anonymous=self.app.test_client()
        self.assertEqual(anonymous.get('/login').status_code,200)
        self.assertEqual(anonymous.post('/login',data={'username':'owner','password':'test-password-123456789'}).status_code,403)
        with anonymous.session_transaction() as state:token=state['csrf']
        credentials={'csrf':token,'username':'owner','password':'wrong'}
        self.assertEqual(anonymous.post('/login',data=credentials).status_code,401)
        credentials['password']='test-password-123456789'
        response=anonymous.post('/login',data=credentials)
        self.assertEqual(response.status_code,302)
        self.assertIn('HttpOnly',response.headers['Set-Cookie'])
        self.assertIn('SameSite=Lax',response.headers['Set-Cookie'])
        self.assertEqual(anonymous.get('/api/project').status_code,200)
        self.assertEqual(anonymous.post('/logout').status_code,403)
        with anonymous.session_transaction() as state:token=state['csrf']
        self.assertEqual(anonymous.post('/logout',data={'csrf':token}).status_code,302)
        self.assertEqual(anonymous.get('/api/project').status_code,401)

    def test_private_paths_and_directory_listing_blocked(self):
        for path in ['/models/orchard_soil_6h.json','/.secrets/tuya_local.json','/tools/serve_orchard_cloud.py',
                     '/docs/updates/attachments/GAP_5_PROVINCES_20261020.xlsx',
                     '/research_data/gap_public_sources/2026-10-20/README.md',
                     '/research_data/five_province_history/gap_orchards/manifest.json',
                     '/research_data/five_province_history/gap_orchards/province_84.geojson',
                     '/research_data/five_province_history/gap_spatial_experiment/gap_spatial_prep_20261021_verified/manifest.json',
                     '/research_data/five_province_history/point_weather_cache/a.json','/research_data/five_province_history/']:
            self.assertEqual(self.client.get(path,headers=self.auth).status_code,404)

    def test_render_requires_tls_before_accepting_login(self):
        with patch.dict(os.environ,{'RENDER':'true'}):
            self.assertEqual(self.client.get('/api/project',headers=self.auth).status_code,400)
            response=self.client.get('/api/project',headers={**self.auth,'X-Forwarded-Proto':'https'})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['Cache-Control'],'private, no-store')
            self.assertEqual(response.headers['Referrer-Policy'],'strict-origin-when-cross-origin')

    def test_cross_site_export_and_bad_weather_rejected(self):
        response=self.client.post('/api/weather-export',headers={**self.auth,'Origin':'https://evil.invalid'},json={})
        self.assertEqual(response.status_code,403)
        self.assertEqual(self.client.get('/api/weather?lat=nan&lon=99&start=2026-01-01&end=2026-01-02',headers=self.auth).status_code,400)

    def test_supabase_missing_config_does_not_fallback_to_fake_live_snapshot(self):
        self.assertEqual(self.client.get('/api/orchard-status',headers=self.auth).status_code,503)

    def test_secret_key_stays_in_server_headers(self):
        response=Mock(status_code=200);response.json.return_value=[]
        with patch.dict(os.environ,{'SUPABASE_URL':'https://test.supabase.co','SUPABASE_SECRET_KEY':'sb_secret_fixture'}),patch('supabase_orchard.requests.get',return_value=response) as get:
            self.assertEqual(read_table('sensor_readings',{'limit':'1'}),[])
            self.assertNotIn('Authorization',get.call_args.kwargs['headers'])
            self.assertEqual(get.call_args.kwargs['headers']['apikey'],'sb_secret_fixture')
            self.assertFalse(get.call_args.kwargs['allow_redirects'])

    def test_live_reading_scope_quality_and_model(self):
        now=pd.Timestamp('2026-10-09T14:00:00Z')
        rows=[]
        for i,t in enumerate(pd.date_range(now-pd.Timedelta(hours=8),now,freq='15min')):
            row={field:float(i+1) for field in WEATHER}
            row.update(event_id=str(i),recorded_at=t.isoformat(),device_id='test-device',soil_moisture_percent=30.,
                       soil_temperature_c=27.,outdoor_temperature_c=29.,outdoor_humidity_percent=75.,
                       soil_valid=True,weather_valid=True,soil_age_sec=0,weather_age_sec=0)
            rows.append(row)
        reader=Mock(return_value=rows)
        result=live_status(now.to_pydatetime(),reader)
        self.assertEqual(result['mode'],'supabase_live')
        self.assertEqual(result['soil_percent'],30.)
        self.assertEqual(result['prediction']['predicted_hour_mean_soil_percent'],30.)
        self.assertEqual(reader.call_args.args[1]['device_id'],'eq.test-device')
        self.assertNotIn('device_id',result)
        rows[-1]['weather_valid']=False
        result=live_status(now.to_pydatetime(),reader)
        self.assertIsNone(result['vpd_kpa'])

    def test_only_free_render_plan_and_no_cloud_training(self):
        import yaml
        config=yaml.safe_load((ROOT/'render.yaml').read_text(encoding='utf-8'))
        self.assertEqual(config['services'][0]['plan'],'free')
        self.assertNotIn('service_role',str(config))
        docker=(ROOT/'Dockerfile').read_text()
        self.assertNotIn('COPY . ',docker)
        self.assertIn('USER orchard',docker)

    def test_portable_context_contains_model_inputs_but_no_private_exports(self):
        from prepare_cloud_deploy import selected_files
        names=selected_files()
        for name in ['production_annual.csv','harvest_monthly.csv','weather_daily.csv','UNIFIED_MAP.html']:
            self.assertIn('research_data/five_province_history/'+name,names)
        for code in ['22','33','53','84','86']:
            self.assertIn('research_data/priority_provinces/soil_layers/'+code+'.geojson',names)
        self.assertFalse(any(name.startswith(('data/','iot/','.secrets/','.git/')) for name in names))
        from durian_model.common import check_snapshot
        check_snapshot()
        with self.client.get('/research_data/five_province_history/UNIFIED_MAP.html',headers=self.auth) as response:
            self.assertEqual(response.status_code,200)


if __name__=='__main__':unittest.main()
