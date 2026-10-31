import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from orchard_private_assets import ASSETS,signed_asset
from serve_orchard_cloud import create_app

class PrivateAssetTests(unittest.TestCase):
    def test_exact_allowlist_private_short_link_and_no_redirect_to_other_host(self):
        env={'SUPABASE_URL':'https://test.supabase.co','SUPABASE_SECRET_KEY':'sb_secret_test','ORCHARD_GIS_PRIVATE_BUCKET':'durian-gis-private'}
        with patch.dict(os.environ,env,clear=True):
            for path in ['../secrets','five_province_history/exports/a.csv','priority_provinces/soil_layers/77.geojson']:
                with self.assertRaises(LookupError):signed_asset(path)
            r=Mock(status_code=200);r.json.return_value={'signedURL':'/object/sign/durian-gis-private/a?token=synthetic'}
            with patch('orchard_private_assets.requests.post',return_value=r) as post:
                self.assertTrue(signed_asset(sorted(ASSETS)[0]).startswith('https://test.supabase.co/storage/v1/object/sign/'))
                self.assertEqual(post.call_args.kwargs['json'],{'expiresIn':60})
                r.json.return_value={'signedURL':'https://evil.invalid/token'}
                with self.assertRaises(RuntimeError):signed_asset(sorted(ASSETS)[0])

    def test_login_gate_before_storage_signing(self):
        env={'DASHBOARD_PASSWORD':'synthetic-test-password-123','DASHBOARD_USER':'owner','VERCEL':'1','ORCHARD_GIS_PRIVATE_BUCKET':'durian-gis-private'}
        with patch.dict(os.environ,env,clear=True),patch('serve_orchard_cloud.signed_asset',return_value='https://test.supabase.co/storage/v1/object/sign/a?token=synthetic') as sign:
            app=create_app();c=app.test_client();headers={'X-Forwarded-Proto':'https'}
            url='/research_data/priority_provinces/soil_layers/22.geojson'
            self.assertEqual(c.get(url,headers=headers).status_code,302);sign.assert_not_called()
            with c.session_transaction() as s:s.update(authenticated=True,principal='owner',csrf='synthetic')
            r=c.get(url,headers=headers);self.assertEqual(r.status_code,302);self.assertIn('private, no-store',r.headers['Cache-Control']);sign.assert_called_once()

if __name__=='__main__':unittest.main()
