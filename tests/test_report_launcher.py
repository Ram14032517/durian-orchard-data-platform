import hashlib,json,unittest,os,tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from tools import open_orchard_report as launcher

class LauncherTests(unittest.TestCase):
    def test_local_settings_private_whitelist_and_existing_environment(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(launcher,'ROOT',Path(folder)),patch.dict(os.environ,{'DASHBOARD_USER':'existing'},clear=True):
            secret=Path(folder)/'.secrets/supabase_local.json';secret.parent.mkdir()
            secret.write_text(json.dumps({'DASHBOARD_USER':'owner','DASHBOARD_PASSWORD':'synthetic-password'}))
            self.assertTrue(launcher.load_local_settings())
            self.assertEqual(os.environ['DASHBOARD_USER'],'existing')
            self.assertEqual(os.environ['DASHBOARD_PASSWORD'],'synthetic-password')
            secret.write_text(json.dumps({'UNEXPECTED_SETTING':'synthetic'}))
            with self.assertRaises(RuntimeError):launcher.load_local_settings()
            os.environ['RENDER']='true'
            self.assertFalse(launcher.load_local_settings())

    @patch.object(launcher,'urlopen')
    def test_configured_launcher_does_not_reuse_unconfigured_or_different_project(self,open_url):
        response=open_url.return_value.__enter__.return_value;response.status=200
        identity={'application':'orchard-analysis','protocol':1,'workspace_id':hashlib.sha256(launcher.ROOT.resolve().as_posix().casefold().encode()).hexdigest()}
        with patch.dict(os.environ,{'SUPABASE_URL':'https://test.supabase.co','DASHBOARD_PASSWORD':'synthetic-password'},clear=True):
            response.read.side_effect=[json.dumps(identity).encode()]
            self.assertFalse(launcher.server_ready())
            identity.update(private_harvest_api_version=1,private_storage_configured=True,private_storage_project='https://other.supabase.co')
            response.read.side_effect=[json.dumps(identity).encode()]
            self.assertFalse(launcher.server_ready())
            identity['private_storage_project']='https://test.supabase.co'
            response.read.side_effect=[json.dumps(identity).encode(),launcher.MARKER]
            self.assertTrue(launcher.server_ready())

    @patch.object(launcher,'urlopen')
    def test_only_expected_page_is_ready(self,open_url):
        response = open_url.return_value.__enter__.return_value
        response.status = 200
        identity={'application':'orchard-analysis','protocol':1,'workspace_id':hashlib.sha256(launcher.ROOT.resolve().as_posix().casefold().encode()).hexdigest()}
        response.read.side_effect=[json.dumps(identity).encode(),launcher.MARKER]
        self.assertTrue(launcher.server_ready())
        response.read.side_effect=[json.dumps(identity).encode(),b'<html>another application</html>']
        self.assertFalse(launcher.server_ready())
        response.read.side_effect=[json.dumps({**identity,'workspace_id':'another checkout'}).encode()]
        self.assertFalse(launcher.server_ready())
        response.read.side_effect=[b'Forbidden']
        self.assertFalse(launcher.server_ready())

    @patch.object(launcher.subprocess,'Popen')
    @patch.object(launcher,'server_ready',return_value=True)
    def test_reuses_server(self,ready,spawn):
        self.assertEqual(launcher.ensure_server(),'existing')
        spawn.assert_not_called()

    @patch.object(launcher.subprocess,'Popen')
    @patch.object(launcher.socket,'socket')
    @patch.object(launcher,'server_ready',return_value=False)
    def test_occupied_port_is_not_replaced(self,ready,socket,spawn):
        socket.return_value.__enter__.return_value.connect_ex.return_value = 0
        with self.assertRaises(RuntimeError): launcher.ensure_server()
        spawn.assert_not_called()

    @patch.object(launcher,'server_ready',return_value=False)
    @patch.object(launcher,'port_occupied',side_effect=lambda port:port==8871)
    def test_different_checkout_gets_free_port(self,occupied,ready):
        self.assertEqual(launcher.choose_port(),8872)

    @patch.object(launcher,'server_ready',side_effect=lambda port:port==8873)
    @patch.object(launcher,'port_occupied',side_effect=lambda port:port in (8871,8873))
    def test_reuses_matching_checkout_before_free_port(self,occupied,ready):
        self.assertEqual(launcher.choose_port(),8873)

if __name__ == '__main__': unittest.main()
