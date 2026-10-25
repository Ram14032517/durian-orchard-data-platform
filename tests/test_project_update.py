"""Readable update preserves Excel bytes and does not expose it via IoT routes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import zipfile

from tools.build_project_update import ROOT, UPDATE, OUTPUT, ATTACHMENTS, render_update, verify_attachment
from tools.serve_orchard_analysis import Handler


class ProjectUpdateTests(unittest.TestCase):
    def test_readable_copy_matches_source_and_has_no_live_scripts(self):
        rendered = render_update(UPDATE.read_text(encoding='utf-8'))
        self.assertEqual(OUTPUT.read_text(encoding='utf-8'), rendered)
        self.assertIn('attachments/GAP_5_PROVINCES_20261020.xlsx', rendered)
        self.assertIn('id="section-1"', rendered)
        self.assertNotIn('<script', rendered.lower())

    def test_attachment_manifest_records_public_git_not_dashboard_or_training(self):
        meta = json.loads(ATTACHMENTS.read_text(encoding='utf-8'))
        self.assertEqual(meta['training']['gap_fit_count'], 0)
        self.assertFalse(meta['training']['gap_metrics_created'])
        self.assertFalse(meta['training']['gap_train_eligible'])
        self.assertEqual(len(meta['workbook']['sheets']), 10)
        self.assertEqual(meta['privacy'], 'public_git_snapshot_not_served_by_local_or_cloud_dashboard')
        self.assertEqual(meta['distribution']['authorized_date_thailand'], '2026-10-25')
        self.assertFalse(meta['distribution']['raw_personal_evidence_included'])
        self.assertFalse(meta['distribution']['dashboard_access_rules_changed'])
        self.assertIn('!docs/updates/attachments/GAP_5_PROVINCES_20261020.xlsx', (ROOT/'.gitignore').read_text())

    def test_attachment_is_blocked_by_static_server(self):
        handler = object.__new__(Handler)
        handler.path = '/docs/updates/attachments/GAP_5_PROVINCES_20261020.xlsx'
        handler.translate_path = Mock(return_value=str(ROOT/handler.path.lstrip('/')))
        handler.send_error = Mock()
        self.assertIsNone(handler.send_head())
        handler.send_error.assert_called_once_with(404)

    def test_attachment_verification_rejects_changed_file(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            attachment = base/'original.xlsx'
            with zipfile.ZipFile(attachment, 'w') as archive:
                archive.writestr('xl/workbook.xml', '<workbook/>')
            digest = hashlib.sha256(attachment.read_bytes()).hexdigest()
            manifest = base/'manifest.json'
            manifest.write_text(json.dumps({'workbook': {'path': 'original.xlsx', 'sha256': digest}}))
            self.assertEqual(verify_attachment(base, manifest), digest)
            attachment.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                verify_attachment(base, manifest)


if __name__ == '__main__':
    unittest.main()
