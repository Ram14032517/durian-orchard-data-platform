"""Guard moved entry points and private-file ignore rules without reading secrets."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectOrganizationTests(unittest.TestCase):
    def test_firmware_sketch_names_and_local_headers_are_preserved(self):
        for name in ['sender_1', 'receiver_gateway', 'soil_only', 'soil_rs485_diag', 'wifi_range_test']:
            self.assertTrue((ROOT / 'iot' / name / (name + '.ino')).is_file())
            self.assertFalse((ROOT / name).exists())
        for name in ['farm_secret.example.h', 'tuya_local_secret.example.h', 'TuyaLocal34.h', 'TuyaLocal34.cpp']:
            self.assertTrue((ROOT / 'iot/receiver_gateway' / name).is_file())

    def test_ingestion_sources_keep_supabase_layout(self):
        for name in ['api/google-apps-script/Code.gs', 'api/supabase/functions/farm-ingest/index.ts',
                     'api/supabase/migrations/001_iot_schema.sql']:
            self.assertTrue((ROOT / name).is_file())

    def test_private_files_ignored_at_new_paths(self):
        names = ['iot/receiver_gateway/farm_secret.h', 'iot/receiver_gateway/tuya_cloud_secret.h',
                 'iot/receiver_gateway/tuya_local_secret.h', 'iot/wifi_range_test/wifi_secret.h',
                 'iot/receiver_gateway/receiver_gateway.private-backup.ino']
        result = subprocess.run(['git', 'check-ignore', '--no-index', *names], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        self.assertEqual(set(result.stdout.splitlines()), set(names))
        example = subprocess.run(['git', 'check-ignore', '--no-index',
                                  'iot/receiver_gateway/farm_secret.example.h'], cwd=ROOT,
                                 capture_output=True)
        self.assertEqual(example.returncode, 1)

    def test_secret_helpers_use_moved_paths(self):
        for name in ['tools/audit_staged_secrets.py', 'tools/move_gateway_ingest_secrets.ps1',
                     'tools/sanitize_firmware_secrets.ps1']:
            source = (ROOT / name).read_text(encoding='utf-8')
            self.assertRegex(source, r'iot[/\\]receiver_gateway[/\\]')


if __name__ == '__main__':
    unittest.main()
