"""Reviewed Git payload is complete; future/private downloads remain ignored."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from tools.build_gap_map_layer import EXPOSED_PROPERTIES
from tools.build_project_update import verify_attachment

ROOT = Path(__file__).resolve().parents[1]
BASE = 'research_data/five_province_history'
MAP = f'{BASE}/gap_orchards'
PREP = f'{BASE}/gap_spatial_experiment'
RAW = 'research_data/gap_public_sources/2026-10-20'
PREP_FILES = ('manifest.json', 'availability_audit.csv',
              'matched_province_year_targets.csv', 'province_coverage.csv',
              'registry_assignments.csv', 'representative_points.csv',
              'weather_request_plan.json')
RUNS = ('gap_spatial_prep_20261021', 'gap_spatial_prep_20261021_verified')
SCRIPTS = ('collect_live_plots.py',
           'collection_east/collect_chinaport_registry.py',
           'collection_east/collect_east.py', 'collection_east/inspect_chinaport.py',
           'collection_east/query_chinaport.py',
           'collection_live_districts/extract_live_districts.py',
           'collection_national/extract_live_dashboard.py',
           'collection_national/extract_registry.py',
           'collection_north_northeast/collect.py',
           'collection_north_northeast/collect_pdf.py',
           'collection_north_northeast/prepare.py',
           'collection_north_northeast/prepare_pdf.py',
           'collection_south/extract_south.py')


class GapPublicationTests(unittest.TestCase):
    def test_all_34_reviewed_payload_files_exist_and_are_not_ignored(self):
        paths = ['docs/updates/attachments/GAP_5_PROVINCES_20261020.xlsx',
                 f'{MAP}/manifest.json']
        paths += [f'{MAP}/province_{code}.geojson' for code in ('22', '33', '53', '84', '86')]
        paths += [f'{PREP}/{run}/{name}' for run in RUNS for name in PREP_FILES]
        paths += [f'{RAW}/{name}' for name in SCRIPTS]
        self.assertEqual(len(paths), 34)
        for relative in paths:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())
                result = subprocess.run(['git', 'check-ignore', '--no-index', '-q', relative], cwd=ROOT)
                self.assertEqual(result.returncode, 1)

    def test_new_snapshots_raw_personal_files_and_environment_stay_ignored(self):
        paths = (f'{RAW}/collection_east/current_export_orchards_rows.json',
                 f'{RAW}/collection_live_plots/records_sanitized.json',
                 f'{RAW}/collection_east/future_collector.py',
                 'research_data/gap_public_sources/future_snapshot/raw.csv',
                 f'{MAP}/future.geojson', f'{PREP}/future_run/manifest.json',
                 f'{PREP}/{RUNS[1]}/private_notes.csv',
                 'docs/updates/attachments/future.xlsx', '.secrets/private.json',
                 '.build/venv/bin/python', 'tools/__pycache__/future.pyc')
        for relative in paths:
            with self.subTest(path=relative):
                result = subprocess.run(['git', 'check-ignore', '--no-index', '-q', relative], cwd=ROOT)
                self.assertEqual(result.returncode, 0)

    def test_original_workbook_and_map_hashes_and_minimized_schema(self):
        for path in ('docs/updates/attachments/GAP_5_PROVINCES_20261020.xlsx',
                     f'{MAP}/manifest.json', f'{MAP}/province_86.geojson',
                     *(f'{PREP}/{run}/{name}' for run in RUNS for name in PREP_FILES)):
            attribute = subprocess.check_output(['git', 'check-attr', 'text', '--', path], cwd=ROOT, text=True)
            self.assertEqual(attribute.strip(), f'{path}: text: unset')
        self.assertEqual(verify_attachment(),
                         'ef3d25feca214050e5e190d0f6d7f1fcc6e09e704d0bdb7b0205b8cb6c39af6c')
        manifest = json.loads((ROOT / MAP / 'manifest.json').read_text())
        count = 0
        for province in manifest['provinces']:
            data = (ROOT / MAP / province['file']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), province['sha256'])
            features = json.loads(data)['features']
            count += len(features)
            for feature in features:
                self.assertEqual(set(feature['properties']), EXPOSED_PROPERTIES)
                self.assertFalse(feature['properties']['field_verified'])
        self.assertEqual(count, 32871)

    def test_preparation_hashes_are_unchanged_and_do_not_claim_training(self):
        for run in RUNS:
            folder = ROOT / PREP / run
            manifest = json.loads((folder / 'manifest.json').read_text())
            self.assertFalse(manifest['train_eligible'])
            self.assertEqual(manifest['experiment']['fit_count'], 0)
            self.assertFalse(manifest['experiment']['metrics_created'])
            for name, digest in manifest['artifact_sha256'].items():
                self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest)

    def test_collector_source_is_valid_without_executing_or_downloading(self):
        for relative in SCRIPTS:
            path = ROOT / RAW / relative
            ast.parse(path.read_text(encoding='utf-8'), filename=relative)


if __name__ == '__main__':
    unittest.main()
