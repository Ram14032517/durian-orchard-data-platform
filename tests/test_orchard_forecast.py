"""Forecast contract and ownership tests; synthetic weather, never real private coordinates."""
import copy
import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import orchard_forecast as f
from serve_orchard_cloud import create_app

NOW = datetime(2026, 10, 28, 12, 15, tzinfo=f.TZ)


def config():
    return dict(latitude=13.75, longitude=100.5, crs='EPSG:4326', owner_confirmed=True,
                confirmed_at='2026-10-27T00:00:00+07:00', owner_account='alice', sensor_device_id='TEST-ONLY',
                orchard_key='test-orchard', use='non_commercial_education')


def payload():
    start=NOW.replace(hour=0,minute=0)
    result=dict(timezone='Asia/Bangkok',utc_offset_seconds=25200)
    for group, fields, count, step in [('hourly',f.HOURLY,168,timedelta(hours=1)),('daily',f.DAILY,7,timedelta(days=1))]:
        result[group]={'time':[(start+i*step).strftime('%Y-%m-%dT%H:%M' if group=='hourly' else '%Y-%m-%d') for i in range(count)]}
        result[group+'_units']={k:v[1] for k,v in fields.items()}
        for k, (_,unit,lo,hi) in fields.items():result[group][k]=[20 if unit=='°C' else 0]*count
    return result


class ForecastTests(unittest.TestCase):
    def test_current_model_weather_units_time_interval_and_missing(self):
        data=payload();data['current']={'time':'2026-10-28T12:00','interval':900}
        data['current_units']={'interval':'seconds'}
        for k, (_,unit,_,_) in f.CURRENT.items():
            data['current'][k]=28 if unit=='°C' else 0
            data['current_units'][k]=unit
        r=f.ForecastService.present(f.normalize(data,NOW),NOW,'fresh')
        self.assertEqual(r['current']['status'],'fresh');self.assertEqual(r['current']['interval_seconds'],900)
        self.assertEqual(r['current']['rain_mm'],0);self.assertEqual(r['current']['temperature_c'],28)
        self.assertEqual(r['current']['age_minutes'],15)
        r=f.ForecastService.present(f.normalize(data,NOW),NOW+timedelta(hours=2),'cached')
        self.assertEqual(r['current']['status'],'stale')
        data['current_units']['vapour_pressure_deficit']='Pa'
        self.assertIsNone(f.normalize(data,NOW)['current']['vpd_kpa'])
        data['current']['time']='2026-10-28T13:00'
        self.assertIsNone(f.normalize(data,NOW)['current']['time'])
        self.assertIsNone(f.normalize(payload(),NOW)['current']['temperature_c'])

    def test_contract_missing_zero_units_and_daily_aggregation(self):
        data=payload();data['hourly']['vapour_pressure_deficit'][2]=None
        data['hourly']['relative_humidity_2m'][3]=101
        r=f.normalize(data,NOW)
        self.assertEqual(len(r['hourly']),168);self.assertEqual(len(r['daily']),7)
        self.assertEqual(r['hourly'][0]['rain_mm'],0)
        self.assertIsNone(r['daily'][0]['vpd_kpa']);self.assertIsNone(r['daily'][0]['humidity_percent'])
        self.assertEqual(r['daily'][0]['vpd_kpa_valid_hours'],23)
        self.assertIsNone(r['model_issued_at'])
        data['hourly_units']['vapour_pressure_deficit']='Pa'
        with self.assertRaises(RuntimeError):f.normalize(data,NOW)

    def test_reject_duplicate_gaps_and_old_response(self):
        for mutation in ['duplicate','gap','old']:
            data=payload()
            if mutation=='duplicate':data['hourly']['time'][1]=data['hourly']['time'][0]
            if mutation=='gap':data['hourly']['time'][1]='2026-10-28T01:30'
            if mutation=='old':data['daily']['time']=['2026-10-'+str(n) for n in range(20,27)]
            with self.assertRaises(RuntimeError):f.normalize(data,NOW)

    def test_private_location_requires_confirmation_and_noncommercial_use(self):
        for change in [dict(owner_confirmed=False),dict(latitude=True),dict(latitude=99),dict(crs='EPSG:3857'),dict(use='commercial')]:
            c={**config(),**change}
            with patch.dict(os.environ,{'ORCHARD_FORECAST_LOCATION_JSON':json.dumps(c)}):
                with self.assertRaises(RuntimeError):f.location_config()

    def test_cache_error_stale_cooldown_and_no_coordinate_leak(self):
        service=f.ForecastService();response=Mock(status_code=200,headers={'Content-Type':'application/json'},content=b'{}')
        response.json.return_value=payload()
        with patch.object(f.requests,'get',return_value=response) as get:
            first=service.get(config(),NOW);second=service.get(config(),NOW+timedelta(minutes=1))
            self.assertEqual(get.call_count,1);self.assertEqual(second['status'],'cached')
            args=get.call_args.kwargs
            self.assertEqual(args['params']['timezone'],'Asia/Bangkok');self.assertFalse(args['allow_redirects'])
            self.assertIn('vapour_pressure_deficit',args['params']['current'])
            self.assertNotIn('latitude',json.dumps(first));self.assertNotIn('longitude',json.dumps(first))
            get.side_effect=f.requests.Timeout('PRIVATE COORDINATE URL MUST NEVER APPEAR')
            stale=service.get(config(),NOW+timedelta(minutes=31));self.assertEqual(stale['status'],'stale')
            service.get(config(),NOW+timedelta(minutes=32));self.assertEqual(get.call_count,2)
            with self.assertRaisesRegex(RuntimeError,'Open-Meteo'):service.get(config(),NOW+timedelta(hours=4))
            self.assertEqual(len(first['summaries']),3);self.assertEqual(first['summaries'][0]['rain_mm'],0)
            self.assertTrue(first['summaries'][0]['complete'])

    def test_partial_summary_never_adds_missing_as_zero(self):
        data=payload();data['hourly']['precipitation'][16]=None
        r=f.ForecastService.present(f.normalize(data,NOW),NOW,'fresh')
        self.assertFalse(r['summaries'][0]['complete']);self.assertIsNone(r['summaries'][0]['rain_mm'])

    def test_auth_owner_sensor_link_url_and_static_restrictions(self):
        with patch.dict(os.environ,{'DASHBOARD_USER':'alice','DASHBOARD_PASSWORD':'test-pass-0000000000000',
              'DASHBOARD_USERS_JSON':json.dumps({'bob':'test-bob-00000000000000'}),'ORCHARD_DEVICE_ID':'TEST-ONLY','RENDER':'false'},clear=True):
            app=create_app();app.config['TESTING']=True;service=Mock();service.get.return_value={'status':'fresh'}
            app.config['FORECAST_SERVICE']=service;c=app.test_client()
            self.assertEqual(c.get('/api/orchard-forecast').status_code,401)
            with c.session_transaction() as s:s.update(authenticated=True,principal='bob',csrf='test')
            with patch('serve_orchard_cloud.location_config',return_value=config()):
                self.assertEqual(c.get('/api/orchard-forecast').status_code,403)
                with c.session_transaction() as s:s['principal']='alice'
                r=c.get('/api/orchard-forecast');self.assertEqual(r.status_code,200)
                self.assertTrue(r.json['sensor_link_confirmed']);self.assertEqual(r.headers['Cache-Control'],'private, no-store')
                self.assertEqual(c.get('/api/orchard-forecast?latitude=1').status_code,400)
                wrong={**config(),'sensor_device_id':'other'}
                with patch('serve_orchard_cloud.location_config',return_value=wrong):self.assertEqual(c.get('/api/orchard-forecast').status_code,403)
            self.assertNotEqual(c.get('/.secrets/orchard_forecast_location.json').status_code,200)
            self.assertEqual(service.get.call_count,1)


if __name__=='__main__':unittest.main()
