import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from supabase_orchard import orchard_history
from serve_orchard_cloud import create_app


class HistoryTests(unittest.TestCase):
    def row(self,event,time,value=40,valid=True):
        return dict(event_id=event,recorded_at=time,soil_moisture_percent=value,soil_temperature_c=27,
            outdoor_temperature_c=31,outdoor_humidity_percent=70,soil_valid=valid,weather_valid=True,
            soil_age_sec=0,weather_age_sec=0)

    def run_history(self,rows,period='day'):
        with patch.dict(os.environ,{'ORCHARD_DEVICE_ID':'farm_gateway_s3'}):
            return orchard_history(period,now='2026-10-09T12:00:00Z',reader=lambda table,params:rows)

    def test_gaps_invalid_values_and_timezone(self):
        result=self.run_history([self.row('a','2026-10-09T10:10:00Z'),self.row('b','2026-10-09T11:00:00Z',90,False)])
        self.assertEqual(len(result['rows']),25)
        self.assertEqual(result['rows'][-3]['soil_moisture_percent'],40)
        self.assertIsNone(result['rows'][-2]['soil_moisture_percent'])
        self.assertTrue(result['rows'][-1]['time'].endswith('+07:00'))

    def test_daily_mean_weights_hours_not_packets(self):
        rows=[self.row(str(i),'2026-10-09T08:00:00Z',20) for i in range(10)]
        rows.append(self.row('last','2026-10-09T09:00:00Z',80))
        result=self.run_history(rows,'week')
        self.assertEqual(result['rows'][-1]['soil_moisture_percent'],50)
        self.assertEqual(result['raw_count'],11)

    def test_period_validation_empty_and_future(self):
        with self.assertRaises(ValueError):self.run_history([],'year')
        self.assertEqual(self.run_history([])['rows'],[])
        result=self.run_history([self.row('future','2026-10-10T00:00:00Z')])
        self.assertEqual(result['raw_count'],0)

    def test_api_requires_authentication_and_validates_period(self):
        with patch.dict(os.environ,{'DASHBOARD_PASSWORD':'test-password-12345678','RENDER':'false'}):
            client=create_app().test_client()
            self.assertEqual(client.get('/api/orchard-history').status_code,401)
            with client.session_transaction() as state:state['authenticated']=True
            self.assertEqual(client.get('/api/orchard-history?period=year').status_code,400)

    def test_historical_end_is_thai_calendar_day(self):
        with patch.dict(os.environ,{'ORCHARD_DEVICE_ID':'farm_gateway_s3'}):
            queries=[]
            def reader(table,params):queries.append(params);return []
            result=orchard_history(now='2026-10-09T12:00:00Z',end='2026-10-01',reader=reader)
            self.assertTrue(result['end'].startswith('2026-10-01T23:59:59'))
            self.assertIn('(recorded_at.lte.2026-10-01T23:59:59',queries[0]['and'])
            with self.assertRaises(ValueError):orchard_history(now='2026-10-09T12:00:00Z',end='2026-10-10')


if __name__=='__main__':unittest.main()
