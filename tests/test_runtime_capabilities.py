"""Runtime capabilities must describe policy, not expose credentials or fake live data."""
import json
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from tools import serve_orchard_analysis as api


class RuntimeCapabilitiesTests(unittest.TestCase):
    def test_local_default_is_explicit_snapshot_not_fake_live(self):
        with patch.dict(os.environ,{},clear=True):
            data=api.project_identity()
        self.assertEqual(data['mode'],'local')
        self.assertEqual(data['orchard_source'],'local_snapshot')
        self.assertFalse(data['capabilities']['orchard']['history_configured'])

    def test_local_snapshot_does_not_call_supabase_even_when_credentials_exist(self):
        with patch.dict(os.environ,{'ORCHARD_DATA_SOURCE':'local_snapshot'}), \
             patch('orchard_current_context.orchard_snapshot',return_value={'mode':'fixture_snapshot'}) as snapshot, \
             patch('supabase_orchard.live_status') as live:
            self.assertEqual(api.local_orchard_status(),{'mode':'fixture_snapshot'})
        snapshot.assert_called_once();live.assert_not_called()

    def test_opt_in_supabase_never_falls_back_to_snapshot(self):
        with patch.dict(os.environ,{'ORCHARD_DATA_SOURCE':'supabase'}), \
             patch('supabase_orchard.live_status',side_effect=RuntimeError('not configured')) as live, \
             patch('orchard_current_context.orchard_snapshot') as snapshot:
            with self.assertRaisesRegex(RuntimeError,'not configured'):api.local_orchard_status()
        live.assert_called_once();snapshot.assert_not_called()

    def test_invalid_mode_fails_closed(self):
        with patch.dict(os.environ,{'ORCHARD_DATA_SOURCE':'anything-else'}):
            with self.assertRaises(RuntimeError):api.local_orchard_status()

    def test_identity_reports_presence_without_credentials_or_device_identifier(self):
        fixture={'SUPABASE_URL':'https://fixture-only.supabase.co','SUPABASE_SECRET_KEY':'sb_secret_not_a_real_key',
                 'ORCHARD_DEVICE_ID':'fixture-device-only','ORCHARD_DATA_SOURCE':'supabase'}
        with patch.dict(os.environ,fixture,clear=True):data=api.project_identity()
        self.assertTrue(data['capabilities']['orchard']['configured'])
        text=json.dumps(data)
        for secret in fixture.values():
            if secret!='supabase':self.assertNotIn(secret,text)

    def test_missing_gap_snapshot_is_not_advertised_as_available(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(api,'ROOT',Path(directory)), \
             patch.dict(os.environ,{},clear=True):
            self.assertFalse(api.project_identity()['capabilities']['gap_registry']['available'])

    def test_local_live_routes_keep_private_auth_without_hijacking_snapshot(self):
        handler=object.__new__(api.Handler)
        with patch.dict(os.environ,{'SUPABASE_URL':'https://fixture-only.supabase.co','ORCHARD_DATA_SOURCE':'local_snapshot'}):
            handler.path='/api/orchard-status';self.assertFalse(handler.private_route())
            handler.path='/api/orchard-history';self.assertTrue(handler.private_route())
            os.environ['ORCHARD_DATA_SOURCE']='supabase'
            handler.path='/api/orchard-status';self.assertTrue(handler.private_route())
            os.environ['ORCHARD_DATA_SOURCE']='invalid'
            self.assertFalse(handler.private_route())  # Dispatcher returns the controlled 503.

    def test_clean_page_alias_is_local_static_only_without_private_configuration(self):
        handler=object.__new__(api.Handler)
        with patch.dict(os.environ,{},clear=True):
            for path in api.APP_PATHS:
                handler.path=path;self.assertFalse(handler.private_route())
            for path in ['/api/orchard-harvest','/api/orchard-forecast','/api/orchard-session']:
                handler.path=path;self.assertTrue(handler.private_route())
            os.environ['DASHBOARD_PASSWORD']='fixture-not-used-for-authentication'
            for path in api.APP_PATHS:
                handler.path=path;self.assertTrue(handler.private_route())


if __name__=='__main__':unittest.main()
