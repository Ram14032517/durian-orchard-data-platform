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

    def test_all_soil_weather_fields_respect_quality_and_rain_windows(self):
        a=self.row('a','2026-10-09T10:10:00Z')
        a.update(soil_ec=123,soil_ph=6.4,soil_n=8,soil_p=9,soil_k=10,rain_1h_mm=3,rain_24h_mm=8,wind_gust=15,light_lux=42)
        b=self.row('b','2026-10-09T10:50:00Z')
        b.update(soil_ec=200,soil_ph=6.6,soil_n=10,soil_p=11,soil_k=12,rain_1h_mm=4,rain_24h_mm=9,wind_gust=12,light_lux=44)
        c=self.row('c','2026-10-09T11:10:00Z',valid=False)
        c.update(soil_ec=999,soil_ph=14,rain_1h_mm=2,rain_24h_mm=10,wind_gust=20,weather_valid=False)
        result=self.run_history([a,b,c]);hour=result['rows'][-3];invalid=result['rows'][-2]
        self.assertAlmostEqual(hour['soil_ec'],161.5);self.assertAlmostEqual(hour['soil_ph'],6.5)
        self.assertEqual(hour['rain_1h_mm'],4);self.assertEqual(hour['rain_24h_mm'],9)
        self.assertEqual(hour['wind_gust'],15);self.assertEqual(hour['valid_counts']['soil_n'],2)
        self.assertGreater(hour['vpd_kpa'],0);self.assertEqual(hour['valid_counts']['vpd_kpa'],2)
        self.assertIsNone(invalid['soil_ec']);self.assertIsNone(invalid['rain_1h_mm'])
        self.assertIsNone(invalid['vpd_kpa'])
        self.assertEqual(invalid['valid_counts']['soil_ec'],0)
        self.assertIn('ไม่ใช่ผลรวม',result['message'])

    def test_daily_window_rain_uses_last_and_gust_uses_max(self):
        a=self.row('a','2026-10-09T08:00:00Z');a.update(rain_1h_mm=3,rain_24h_mm=7,wind_gust=20)
        b=self.row('b','2026-10-09T09:00:00Z');b.update(rain_1h_mm=5,rain_24h_mm=9,wind_gust=10)
        day=self.run_history([a,b],'week')['rows'][-1]
        self.assertEqual(day['rain_1h_mm'],5);self.assertEqual(day['rain_24h_mm'],9)
        self.assertEqual(day['wind_gust'],20)

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

    def test_custom_dates_are_bounded_and_respect_thai_dates(self):
        rows=[self.row('a','2026-10-01T10:00:00Z'),self.row('b','2026-10-05T10:00:00Z')]
        with patch.dict(os.environ,{'ORCHARD_DEVICE_ID':'fixture'}):
            reader=lambda table,params:rows
            result=orchard_history('custom',now='2026-10-09T12:00:00Z',reader=reader,start_date='2026-10-01',end='2026-10-01')
            self.assertEqual(result['raw_count'],1)
            self.assertEqual(result['aggregation'],'ค่าเฉลี่ยรายชั่วโมง')
            self.assertTrue(result['start'].startswith('2026-10-01T00:00:00'))
            for start,end in [('2026-10-02','2026-10-01'),('2026-01-01','2026-10-01'),('2026-10-01','2026-10-10')]:
                with self.assertRaises(ValueError):orchard_history('custom',now='2026-10-09T12:00:00Z',reader=reader,start_date=start,end=end)


if __name__=='__main__':unittest.main()
