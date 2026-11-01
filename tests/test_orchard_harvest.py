"""Synthetic private-harvest tests; never contact or populate the real Supabase project."""
import copy
import json
import os
import sys
import threading
import unittest
import uuid
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import orchard_harvest as h
from serve_orchard_cloud import create_app
from orchard_current_context import province_forecast_readiness


def sample(**changes):
    return dict(orchard_code='TEST-ONLY-01',season_key='main',harvest_year=2025,cultivar='หมอนทอง',
        province_code='22',bearing_area_rai=10,harvested_kg=15000,harvest_start='2025-04-01',
        harvest_end='2025-05-01',source_type='farm_log',source_reference='SYNTHETIC TEST ONLY',
        status='complete',actual_harvest_confirmed=True,**changes)


class FakePostgrestStore(h.HarvestStore):
    """HTTP/database test double. Does not certify that a live SQL migration was applied."""
    def __init__(self):self.rows={};self.revisions=[];self.filters=[]
    def read(self,table,params):
        assert table==h.TABLE
        self.filters.append(params.copy());owner=params['owner_id'][3:]
        rows=[copy.deepcopy(r) for r in self.rows.values() if r['owner_id']==owner]
        if 'id' in params:rows=[r for r in rows if r['id']==params['id'][3:]]
        rows.sort(key=lambda r:(-r['harvest_year'],r['orchard_code'],r['season_key'],r['id']))
        start=int(params.get('offset',0));return rows[start:start+int(params.get('limit',1000))]
    def _write(self,method,params,payload):
        if method=='POST':
            for r in self.rows.values():
                if all(r[k]==payload[k] for k in ['owner_id','orchard_code','season_key','harvest_year']):
                    raise h.HarvestConflict('Duplicate synthetic record')
            row=dict(payload,id=str(uuid.uuid4()),version=1,created_at='2026-10-26T00:00:00Z',updated_at='2026-10-26T00:00:00Z')
            self.rows[row['id']]=row
        else:
            row=self.rows.get(params['id'][3:])
            if not row or row['owner_id']!=params['owner_id'][3:] or row['version']!=int(params['version'][3:]):return []
            self.revisions.append(copy.deepcopy(row));row.update(payload);row['version']+=1;row['updated_at']='2026-10-26T00:01:00Z'
        return [copy.deepcopy(row)]


class HarvestTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'DASHBOARD_USER':'alice','DASHBOARD_PASSWORD':'test-master-password-00001',
            'DASHBOARD_USERS_JSON':json.dumps({'bob':'test-bob-password-0000001'}),'RENDER':'false'},clear=True)
        self.env.start();self.store=FakePostgrestStore();self.reader=patch.object(h,'read_table',side_effect=self.store.read);self.reader.start()
        self.app=create_app();self.app.config['TESTING']=True;self.app.config['HARVEST_STORE']=self.store
        self.alice,self.csrf=self.login('alice','test-master-password-00001');self.bob,self.bcsrf=self.login('bob','test-bob-password-0000001')
    def tearDown(self):self.reader.stop();self.env.stop()
    def login(self,user,password):
        client=self.app.test_client();client.get('/login')
        with client.session_transaction() as s:csrf=s['csrf']
        self.assertEqual(client.post('/login',data={'username':user,'password':password,'csrf':csrf}).status_code,302)
        response=client.get('/api/orchard-session');self.assertEqual(response.status_code,200)
        return client,response.json['csrf']
    def post(self,payload=None,client=None,csrf=None):
        return (client or self.alice).post('/api/orchard-harvest',json=payload if payload is not None else sample(),headers={'X-CSRF-Token':csrf or self.csrf})

    def test_save_reload_formula_and_baseline_not_ai(self):
        r=self.post();self.assertEqual(r.status_code,201);row=r.json['record'];self.assertEqual(row['yield_kg_per_rai'],1500)
        self.assertNotIn('owner_id',row)
        result=self.alice.get('/api/orchard-harvest').json;self.assertEqual(len(result['records']),1)
        baseline=result['baselines'][0];self.assertEqual(baseline['target_year'],2026);self.assertEqual(baseline['kg_per_rai'],1500)
        self.assertFalse(baseline['is_ai_forecast']);self.assertFalse(result['auto_train'])
        self.assertIn('no-store',self.alice.get('/api/orchard-harvest').headers['Cache-Control'])

    def test_users_never_read_update_or_export_each_others_records(self):
        row=self.post().json['record'];self.assertEqual(self.bob.get('/api/orchard-harvest').json['records'],[])
        result=self.bob.patch('/api/orchard-harvest/'+row['id'],json={'harvested_kg':1,'expected_version':1},headers={'X-CSRF-Token':self.bcsrf})
        self.assertEqual(result.status_code,404)
        self.assertEqual(self.bob.get('/api/orchard-harvest/export').json['records'],[])
        self.assertNotEqual(h.owner_key('alice'),h.owner_key('bob'))
        self.assertTrue(all(x.get('owner_id','').startswith('eq.') for x in self.store.filters))
        self.assertEqual(self.bob.get('/api/orchard-status').status_code,403)
        self.assertEqual(self.bob.get('/api/orchard-history').status_code,403)

    def test_edit_keeps_revision_and_prevents_lost_updates(self):
        row=self.post().json['record'];url='/api/orchard-harvest/'+row['id'];headers={'X-CSRF-Token':self.csrf}
        result=self.alice.patch(url,json={'harvested_kg':18000,'expected_version':1},headers=headers)
        self.assertEqual(result.status_code,200);self.assertEqual(result.json['record']['version'],2)
        self.assertEqual(result.json['record']['yield_kg_per_rai'],1800)
        self.assertEqual(self.store.revisions[0]['harvested_kg'],15000)
        self.assertEqual(self.alice.patch(url,json={'harvested_kg':1,'expected_version':1},headers=headers).status_code,409)

    def test_missing_draft_keeps_null_not_zero_and_no_baseline(self):
        values=sample();values.update(status='draft',bearing_area_rai=None,harvested_kg=None,harvest_start=None,harvest_end=None,cultivar='',source_reference='',actual_harvest_confirmed=False)
        r=self.post(values);self.assertEqual(r.status_code,201);self.assertIsNone(r.json['record']['yield_kg_per_rai'])
        self.assertEqual(self.alice.get('/api/orchard-harvest').json['baselines'],[])
        values['orchard_code']='TEST-ONLY-02';values['status']='complete';self.assertEqual(self.post(values).status_code,400)

    def test_duplicates_are_not_new_training_examples(self):
        self.assertEqual(self.post().status_code,201);self.assertEqual(self.post().status_code,409)

    def test_zero_harvest_is_valid_but_zero_area_is_not(self):
        v=sample();v['harvested_kg']=0
        self.assertEqual(self.post(v).json['record']['yield_kg_per_rai'],0)
        v['orchard_code']='TEST-ZERO-AREA';v['bearing_area_rai']=0;self.assertEqual(self.post(v).status_code,400)

    def test_untrusted_fields_dates_units_and_registration_are_rejected(self):
        for changes in [dict(owner_id=h.owner_key('bob')),dict(yield_kg_per_rai=999),dict(harvest_year=2035),
                        dict(harvested_kg=-1),dict(harvested_kg=True),dict(bearing_area_rai='NaN'),
                        dict(harvest_start='2024-01-01'),dict(harvest_start='2025-06-01'),
                        dict(source_type='GAP_registration'),dict(actual_harvest_confirmed=False),dict(province_code='99')]:
            with self.subTest(changes=changes):
                v=sample();v.update(changes);self.assertEqual(self.post(v).status_code,400)

    def test_auth_csrf_cross_origin_fail_closed(self):
        anon=self.app.test_client()
        for endpoint in ['/api/orchard-session','/api/orchard-harvest','/api/orchard-harvest/export']:
            self.assertEqual(anon.get(endpoint).status_code,401)
        self.assertEqual(self.alice.post('/api/orchard-harvest',json=sample()).status_code,403)
        self.assertEqual(self.alice.post('/api/orchard-harvest',json=sample(),headers={'X-CSRF-Token':self.csrf,'Origin':'https://evil.invalid'}).status_code,403)
        self.assertEqual(self.alice.post('/api/orchard-harvest',data='x',headers={'X-CSRF-Token':self.csrf}).status_code,400)

    def test_candidate_pairs_use_same_orchard_consecutive_year_and_exact_ties(self):
        for y,kg in [(2023,10000),(2024,12000),(2025,12000)]:
            v=sample();v.update(harvest_year=y,harvested_kg=kg,harvest_start=f'{y}-04-01',harvest_end=f'{y}-05-01');self.assertEqual(self.post(v).status_code,201)
        data=self.alice.get('/api/orchard-harvest/export').json
        pairs={r['harvest_year']:r for r in data['candidate_pairs']}
        self.assertEqual(set(pairs),{2024,2025});self.assertEqual(pairs[2024]['increase_label'],1);self.assertIsNone(pairs[2025]['increase_label'])
        self.assertFalse(data['training_ready_verified']);self.assertFalse(data['auto_train'])
        self.assertEqual(pairs[2024]['previous_data_first_recorded_at'],'2026-10-26T00:00:00Z')

    def test_model_gate_does_not_promote_outer_winner_or_fetch_future_weather(self):
        data=province_forecast_readiness();self.assertFalse(data['forecast_available']);self.assertIsNone(data['predicted_kg_rai'])
        self.assertTrue(all(not r['eligible'] for r in data['reviewed_candidates']))
        self.assertFalse(data['production_model_changed'])

    def test_backend_key_stays_server_side_and_redirects_are_not_followed(self):
        response=Mock(status_code=201);response.json.return_value=[]
        with patch.dict(os.environ,{'SUPABASE_URL':'https://test.supabase.co','SUPABASE_SECRET_KEY':'sb_secret_synthetic_test'}),patch.object(h.requests,'request',return_value=response) as send:
            self.store.__class__.__mro__[1]._write(self.store,'POST',{}, {'test':'synthetic'})
            self.assertFalse(send.call_args.kwargs['allow_redirects'])
            self.assertEqual(send.call_args.kwargs['headers']['apikey'],'sb_secret_synthetic_test')
            self.assertNotIn('Authorization',send.call_args.kwargs['headers'])

    def test_missing_config_never_falls_back_to_browser_storage(self):
        with self.assertRaises(RuntimeError):h.HarvestStore()._write('POST',{}, {})

    def test_sql_private_grants_generated_yield_and_revision_trigger(self):
        sql=(ROOT/'api/supabase/migrations/004_private_orchard_harvest.sql').read_text(encoding='utf-8')
        self.assertEqual(sql.count('enable row level security'),2)
        self.assertIn('generated always as',sql);self.assertIn('before update',sql)
        self.assertIn('revoke all on public.orchard_harvest_seasons',sql)
        self.assertNotIn('to anon;',sql);self.assertNotIn('grant delete',sql.lower())

    def test_local_mount_reuses_login_and_private_api(self):
        import requests
        import serve_orchard_analysis as local
        local.private_application.cache_clear()
        local.private_application().config['HARVEST_STORE']=self.store
        server=ThreadingHTTPServer(('127.0.0.1',0),local.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        try:
            client=requests.Session()
            self.assertEqual(client.get(origin+'/api/orchard-harvest',timeout=5).status_code,401)
            with patch.dict(os.environ,{'SUPABASE_URL':'https://test.supabase.co','ORCHARD_DATA_SOURCE':'supabase'}):
                for path in ['/api/orchard-status','/api/orchard-history']:
                    self.assertEqual(client.get(origin+path,timeout=5).status_code,401)
            client.get(origin+'/login',timeout=5)
            # The fixture reads the signed session only to obtain the rendered form's token.
            import re
            html=client.get(origin+'/login',timeout=5).text;csrf=re.search(r'name="csrf" value="([^"]+)"',html).group(1)
            self.assertEqual(client.post(origin+'/login',data={'username':'alice','password':'test-master-password-00001','csrf':csrf},allow_redirects=False,timeout=5).status_code,302)
            token=client.get(origin+'/api/orchard-session',timeout=5).json()['csrf']
            with patch.dict(os.environ,{'SUPABASE_URL':'https://test.supabase.co','ORCHARD_DATA_SOURCE':'supabase'}),patch('serve_orchard_cloud.live_status',return_value={'mode':'supabase_live'}),patch('serve_orchard_cloud.orchard_history',return_value={'source':'Supabase','rows':[]}):
                self.assertEqual(client.get(origin+'/api/orchard-status',timeout=5).json()['mode'],'supabase_live')
                self.assertEqual(client.get(origin+'/api/orchard-history',timeout=5).json()['source'],'Supabase')
            self.assertEqual(client.post(origin+'/api/orchard-harvest',json=sample(),headers={'X-CSRF-Token':token},timeout=5).status_code,201)
            self.assertEqual(len(client.get(origin+'/api/orchard-harvest',timeout=5).json()['records']),1)
            self.assertEqual(client.get(origin+'/api/orchard-harvest',headers={'Host':'evil.invalid'},timeout=5).status_code,403)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5);local.private_application.cache_clear()


if __name__=='__main__':unittest.main()
