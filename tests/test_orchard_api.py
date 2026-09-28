"""Offline regression tests for the local map server."""
from datetime import date,datetime,timedelta,timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen
from urllib.error import HTTPError
from unittest.mock import Mock,patch
import hashlib,json,threading,unittest
from tools import serve_orchard_analysis as api

class WeatherTests(unittest.TestCase):
    def test_missing_days_parameters_and_zero_rain(self):
        data={'properties':{'parameter':{'T2M':{'20240401':30,'20240402':-999},'PRECTOTCORR':{'20240401':0}}}}
        rows=api.daily_rows(data,date(2024,4,1),date(2024,4,3))
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['PRECTOTCORR'],0)
        self.assertIsNone(rows[1]['T2M'])
        self.assertIsNone(rows[2]['T2M'])
        self.assertIsNone(rows[0]['RH2M'])

    def test_cache_expiry_and_integrity(self):
        now=datetime(2026,9,26,tzinfo=timezone.utc)
        with TemporaryDirectory() as d:
            p=Path(d)/'cache.json';raw=b'{}';p.write_bytes(raw)
            meta={'retrieved_utc':now.isoformat(),'sha256':hashlib.sha256(raw).hexdigest()}
            p.with_suffix('.source.json').write_text(json.dumps(meta))
            self.assertTrue(api.cache_is_fresh(p,date(2026,9,25),now.date(),now))
            self.assertFalse(api.cache_is_fresh(p,date(2026,9,25),now.date(),now+timedelta(hours=6)))
            self.assertTrue(api.cache_is_fresh(p,date(2024,4,1),now.date(),now+timedelta(days=29)))
            self.assertFalse(api.cache_is_fresh(p,date(2024,4,1),now.date(),now+timedelta(days=30)))
            p.write_bytes(b'corrupt')
            self.assertFalse(api.cache_is_fresh(p,date(2024,4,1),now.date(),now))

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),api.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def test_public_page(self):
        with urlopen(self.base+'/research_data/five_province_history/SEASONS_MAP.html') as r:
            self.assertEqual(r.status,200)
    def test_private_files_listing_traversal(self):
        for path in ['/.git/config','/.secrets/','/tools/serve_orchard_analysis.py','/research_data/','/research_data/five_province_history/../../.git/config']:
            with self.subTest(path=path),self.assertRaises(HTTPError) as cm:
                urlopen(self.base+path)
            self.assertEqual(cm.exception.code,404)
    def test_invalid_queries(self):
        for q in ['lat=nan','lat=99&lon=99&start=2024-01-01&end=2024-01-02','lat=9&lon=99&start=2024-02-01&end=2024-01-01','lat=9&lon=99&start=2020-01-01&end=2024-01-01']:
            with self.subTest(query=q),self.assertRaises(HTTPError) as cm:
                urlopen(self.base+'/api/weather?'+q)
            self.assertEqual(cm.exception.code,400)
    def test_success_coverage_and_cache(self):
        data={'properties':{'parameter':{'T2M':{'20240401':30},'PRECTOTCORR':{'20240401':0}}}}
        response=Mock();response.json.return_value=data;response.content=json.dumps(data).encode();response.url='https://power.larc.nasa.gov/api/test'
        query='/api/weather?lat=9&lon=99&start=2024-04-01&end=2024-04-03'
        with TemporaryDirectory() as d,patch.object(api,'CACHE',Path(d)),patch.object(api.requests,'get',return_value=response) as fetch:
            for _ in range(2):
                with urlopen(self.base+query) as r:result=json.load(r)
                self.assertEqual(result['coverage']['T2M']['valid_days'],1)
                self.assertEqual(result['coverage']['T2M']['requested_days'],3)
                self.assertIn('url',result['provenance'])
            self.assertEqual(fetch.call_count,1)
    def test_upstream_timeout_502(self):
        with TemporaryDirectory() as d,patch.object(api,'CACHE',Path(d)),patch.object(api.requests,'get',side_effect=api.requests.Timeout('test timeout')):
            with self.assertRaises(HTTPError) as cm:
                urlopen(self.base+'/api/weather?lat=9&lon=99&start=2024-04-01&end=2024-04-03')
            self.assertEqual(cm.exception.code,502)

if __name__=='__main__':unittest.main()
