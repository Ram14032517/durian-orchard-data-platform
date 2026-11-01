"""A newline proof is explicit and cannot bypass source or PIT checks."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/durian_model'))
import common
import availability_guard as guard


class SourceIntegrityTests(unittest.TestCase):
    def test_saved_main_model_newlines_are_compatible_but_parameter_changes_are_not(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);raw=b'{"fixture_coefficient":1}\n'
            path=folder/'ridge_vpd_final_model.json';path.write_bytes(raw)
            expected=hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest()
            proof=common.verify_production_snapshot(expected,folder)
            self.assertEqual(proof['comparison'],'uniform_lf_crlf_only')
            path.write_bytes(raw.replace(b':1',b':2'))
            with self.assertRaises(ValueError):common.verify_production_snapshot(expected,folder)

    def test_known_csv_identifies_saved_version_and_preserves_actual_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'research_data/five_province_history';folder.mkdir(parents=True)
            raw=b'province,value\n84,100\n';(folder/'production_annual.csv').write_bytes(raw)
            saved=hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest()
            record=dict(path='research_data/five_province_history/production_annual.csv',source_version=saved,
                        role='feature',availability_status='unverified',publication_date=None,evidence={})
            proof=guard.source_identity(record,root)
            self.assertEqual(proof['version'],saved)
            self.assertEqual(proof['actual_sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(proof['comparison'],'uniform_lf_crlf_only')
            self.assertTrue(guard.check(record,'feature',proof['version'],'2026-01-01T00:00:00Z','exploratory'))
            with self.assertRaises(ValueError):guard.check(record,'feature',proof['version'],'2026-01-01T00:00:00Z','strict')
            (folder/'production_annual.csv').write_bytes(raw.replace(b'100',b'101'))
            with self.assertRaises(ValueError):guard.source_identity(record,root)

    def test_unrelated_text_file_never_gets_a_newline_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);raw=b'test\n';(root/'other.csv').write_bytes(raw)
            record={'path':'other.csv','source_version':hashlib.sha256(b'test\r\n').hexdigest()}
            proof=guard.source_identity(record,root)
            self.assertNotEqual(proof['version'],record['source_version'])

    def test_temp_root_allows_only_system_alias_not_an_extra_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();(root/'canonical').mkdir()
            (root/'system-alias').symlink_to(root/'canonical',target_is_directory=True)
            with patch.object(common.tempfile,'gettempdir',return_value=str(root/'system-alias')):
                self.assertTrue(common.safe_temporary_root(root/'system-alias'/'new'))
                (root/'canonical'/'extra-link').symlink_to(root/'canonical',target_is_directory=True)
                self.assertFalse(common.safe_temporary_root(root/'system-alias'/'extra-link'/'new'))


if __name__=='__main__':unittest.main()
