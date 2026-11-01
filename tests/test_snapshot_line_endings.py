"""Only uniform UTF-8 LF/CRLF differences may match an audited input snapshot."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/durian_model'))
import common
import step6_predict_live as step6


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class SnapshotLineEndingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = '\ufeffprovince,value\nสุราษฎร์ธานี,100\nชุมพร,200\n'.encode('utf-8')
        self.expected = {name: sha(self.source) for name in common.INPUTS}
        for name in common.INPUTS:
            (self.folder / name).write_bytes(self.source)
        self.data_patch = patch.object(common, 'DATA', self.folder)
        self.data_patch.start()
        self.addCleanup(self.data_patch.stop)

    def check_audit(self, expected=None):
        with patch.object(common, 'load_json', return_value={'input_sha256': self.expected if expected is None else expected}):
            return common.check_snapshot()

    def test_exact_bytes_keep_raw_sha256_and_report_provenance(self):
        result = self.check_audit()
        self.assertEqual(common.hashes(), self.expected)
        for name, evidence in result['files'].items():
            self.assertEqual(evidence['comparison'], 'exact_bytes')
            self.assertEqual(evidence['actual_sha256'], self.expected[name])
            self.assertEqual(evidence['expected_sha256'], self.expected[name])

    def test_lf_checkout_matches_crlf_audit_without_rewriting_any_bytes(self):
        expected = {name: sha(self.source.replace(b'\n', b'\r\n')) for name in common.INPUTS}
        result = self.check_audit(expected)
        self.assertEqual(common.hashes(), self.expected)  # hashes() remains byte-exact.
        for name, evidence in result['files'].items():
            self.assertEqual(evidence['comparison'], 'uniform_lf_crlf_only')
            self.assertEqual(evidence['actual_line_endings'], 'LF')
            self.assertEqual(evidence['matched_line_endings'], 'CRLF')
            self.assertEqual(evidence['expected_sha256'], expected[name])
            self.assertEqual((self.folder / name).read_bytes(), self.source)

    def test_crlf_checkout_matches_lf_audit(self):
        for name in common.INPUTS:
            (self.folder / name).write_bytes(self.source.replace(b'\n', b'\r\n'))
        result = self.check_audit()
        self.assertTrue(all(item['actual_line_endings'] == 'CRLF' and item['matched_line_endings'] == 'LF'
                            for item in result['files'].values()))

    def test_each_file_may_have_its_own_audited_newline_style(self):
        first = common.INPUTS[0]
        (self.folder / first).write_bytes(self.source.replace(b'\n', b'\r\n'))
        result = self.check_audit()
        self.assertEqual(result['files'][first]['comparison'], 'uniform_lf_crlf_only')
        self.assertEqual(result['files'][common.INPUTS[1]]['comparison'], 'exact_bytes')

    def test_real_content_changes_are_rejected_even_with_newline_conversion(self):
        expected = {name: sha(self.source.replace(b'\n', b'\r\n')) for name in common.INPUTS}
        mutations = (self.source.replace(b'100', b'101'),
                     self.source.replace(b'value', b'other'),
                     self.source.replace(b'100', b'100 '),
                     self.source.removeprefix(b'\xef\xbb\xbf'),
                     self.source.rstrip(b'\n'), self.source + b'\n',
                     b'\xef\xbb\xbfprovince,value\n' + 'ชุมพร,200\nสุราษฎร์ธานี,100\n'.encode('utf-8'))
        target = self.folder / common.INPUTS[0]
        for raw in mutations:
            with self.subTest(raw_hash=sha(raw)):
                target.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, 'Inputs changed'):
                    self.check_audit(expected)

    def test_mixed_or_lone_cr_newlines_are_not_accepted_as_equivalent(self):
        for raw in (self.source.replace(b'\n', b'\r\n', 1),
                    self.source.replace(b'\n', b'\r'),
                    self.source.replace(b'100', b'10\r0')):
            with self.subTest(raw_hash=sha(raw)):
                (self.folder / common.INPUTS[0]).write_bytes(raw)
                with self.assertRaises(ValueError):
                    self.check_audit()

    def test_non_utf8_text_does_not_get_a_newline_exception(self):
        raw = b'province,value\n\xff,100\n'
        (self.folder / common.INPUTS[0]).write_bytes(raw)
        expected = dict(self.expected, **{common.INPUTS[0]: sha(raw.replace(b'\n', b'\r\n'))})
        with self.assertRaises(ValueError):
            self.check_audit(expected)

    def test_manifest_cannot_omit_or_add_files_or_have_invalid_digests(self):
        for expected in ({}, {**self.expected, 'unknown.csv': sha(self.source)},
                         {**self.expected, common.INPUTS[0]: 'not-a-sha256'},
                         {**self.expected, common.INPUTS[0]: None}, None):
            with self.subTest(expected_type=type(expected).__name__):
                with self.assertRaises(ValueError):
                    common.verify_input_snapshot(expected)

    def test_missing_source_still_fails_closed(self):
        (self.folder / common.INPUTS[0]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.check_audit()

    def test_custom_prediction_accepts_same_model_snapshot_in_other_newline_style(self):
        model = {'input_sha256': {name: sha(self.source.replace(b'\n', b'\r\n')) for name in common.INPUTS}}
        output = self.folder / 'fixture_predictions.csv'
        read = lambda name: model if name == 'final_model.json' else {'completed_steps': list(range(7))}
        predictions = pd.DataFrame([{'province_code': '84', 'year_ce': 2026, 'predicted_kg_rai': 100.}])
        with patch.object(common, 'load_json', return_value={'input_sha256': self.expected}), \
             patch.object(step6, 'load_json', side_effect=read), \
             patch.object(step6.pd, 'read_csv', return_value=pd.DataFrame()), \
             patch.object(step6, 'infer', return_value=predictions), redirect_stdout(io.StringIO()):
            result = step6.run(self.folder / 'synthetic-input.csv', output)
        self.assertTrue(output.is_file())
        pd.testing.assert_frame_equal(result, predictions)

    def test_custom_prediction_rejects_different_model_snapshot_before_inference(self):
        model = {'input_sha256': {name: '0' * 64 for name in common.INPUTS}}
        read = lambda name: model if name == 'final_model.json' else {'completed_steps': list(range(7))}
        with patch.object(common, 'load_json', return_value={'input_sha256': self.expected}), \
             patch.object(step6, 'load_json', side_effect=read), patch.object(step6, 'infer') as infer:
            with self.assertRaisesRegex(ValueError, 'Saved model belongs to another input snapshot'):
                step6.run(self.folder / 'synthetic-input.csv', self.folder / 'never-written.csv')
        infer.assert_not_called()
        self.assertFalse((self.folder / 'never-written.csv').exists())


class CheckedInSnapshotTests(unittest.TestCase):
    def test_original_checked_in_snapshot_is_usable_without_retraining(self):
        report = common.check_snapshot()
        self.assertEqual(set(report['files']), set(common.INPUTS))
        common.verify_input_snapshot(common.load_json('final_model.json')['input_sha256'])

    def test_git_preserves_input_bytes_on_future_checkouts(self):
        import subprocess
        for name in common.INPUTS:
            relative = f'research_data/five_province_history/{name}'
            result = subprocess.check_output(['git', 'check-attr', 'text', '--', relative], cwd=ROOT, text=True)
            self.assertEqual(result.strip(), f'{relative}: text: unset')


if __name__ == '__main__':
    unittest.main()
