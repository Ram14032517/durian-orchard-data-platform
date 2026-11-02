import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import orchard_oae_update as oae


class OaeTests(unittest.TestCase):
    def setUp(self):
        self.base = [dict(province_code='84', province_name='สุราษฎร์ธานี', province_name_en='Surat',
                          region='ใต้', year_ce=2024, planted_rai=120, bearing_rai=100,
                          production_tonnes=100, yield_kg_per_rai_source=1000,
                          yield_kg_per_rai_calculated=1000)]
        self.source = pd.DataFrame([dict(year=2568, crop_year=2568, province_name='สุราษฎร์ธานี',
            commodity='ทุเรียน', subcom='รวม', item=item, unit=unit, data=value, data_date='2026-01-01')
            for (item, (_, unit)), value in zip(oae.ITEMS.items(), [120, 100, 110, 1100])])

    def check(self, source=None):
        return oae.validate(self.source if source is None else source, copy.deepcopy(self.base), 2026)

    def test_consecutive_year_formula_and_no_source_mutation(self):
        original = copy.deepcopy(self.base)
        rows, review, added = self.check()
        self.assertEqual(added, 1)
        self.assertFalse(review)
        self.assertEqual(rows[-1]['yield_kg_per_rai_calculated'], 1100)
        self.assertAlmostEqual(rows[-1]['yield_yoy_pct'], 10)
        self.assertIsNone(rows[-1]['publication_date'])
        self.assertEqual(self.base, original)

    def test_missing_zero_duplicate_units_and_arithmetic(self):
        for index, value, field in [(1, None, 'data'), (1, 0, 'data'), (2, -1, 'data'),
                                    (2, 'กก.', 'unit'), (3, 9999, 'data')]:
            source = self.source.copy()
            source.loc[index, field] = value
            self.assertEqual(self.check(source)[2], 0)
            self.assertTrue(self.check(source)[1])
        self.assertEqual(self.check(pd.concat([self.source, self.source.iloc[:1]]))[2], 0)

    def test_reported_zero_is_real_zero_not_missing(self):
        self.base[0]['production_tonnes'] = 0
        self.base[0]['yield_kg_per_rai_calculated'] = 0
        self.source.loc[2:3, 'data'] = 0
        rows, _, added = self.check()
        self.assertEqual(added, 1)
        self.assertEqual(rows[-1]['yield_kg_per_rai_calculated'], 0)
        self.assertIsNone(rows[-1]['yield_yoy_pct'])

    def test_future_year_totals_and_revisions_do_not_enter(self):
        source = self.source.copy()
        source['year'] = source['crop_year'] = 2570
        self.assertEqual(self.check(source)[2], 0)
        source = self.source.copy()
        source['province_name'] = 'ภาคใต้'
        with self.assertRaises(ValueError):
            self.check(source)
        source = self.source.copy()
        source['year'] = source['crop_year'] = 2567
        rows, review, _ = self.check(source)
        self.assertEqual(rows[0]['production_tonnes'], 100)
        self.assertIn('historical_revision_requires_review', review[0]['reasons'])

    def test_gap_year_does_not_calculate_yoy(self):
        self.source['year'] = self.source['crop_year'] = 2569
        self.assertIsNone(self.check()[0][-1]['yield_yoy_pct'])

    def test_real_workbook_parses_without_modifying_originals(self):
        root = Path(__file__).resolve().parents[1]
        path = root / 'research_data/external/oae_2026-09-17/durian_province.xlsx'
        if not path.exists():
            self.skipTest('local OAE snapshot not distributed')
        source = pd.read_excel(path, sheet_name='durian', engine='openpyxl')
        rows, review, added = oae.validate(source, oae.base_rows(), 2026)
        self.assertEqual(added, 0)
        self.assertEqual(len(rows), len(oae.base_rows()))
        self.assertEqual(len({(r['province_code'], r['year_ce']) for r in rows}), len(rows))

    def test_fetch_cache_and_failure_preserve_last_data(self):
        buffer = io.BytesIO()
        self.source.to_excel(buffer, sheet_name='durian', index=False)
        metadata = json.dumps({'success': True, 'result': {'resources': [
            {'url': 'https://catalog.oae.go.th/province.xlsx'}]}}).encode()
        with tempfile.TemporaryDirectory() as directory, patch.object(oae, 'cache_dir', return_value=Path(directory)), patch.object(oae, 'base_rows', return_value=self.base), patch.object(oae, 'get_bytes', side_effect=[metadata, buffer.getvalue()]) as get:
            first = oae.read_update()
            self.assertEqual(first['status'], 'checked')
            self.assertEqual(oae.read_update()['rows'], first['rows'])
            self.assertEqual(get.call_count, 2)
            path = Path(directory) / 'status.json'
            first['next_check_epoch'] = 0
            path.write_text(json.dumps(first), encoding='utf-8')
            get.side_effect = requests.ConnectionError('secret must not be returned')
            failed = oae.read_update()
            self.assertEqual(failed['rows'], first['rows'])
            self.assertEqual(failed['status'], 'unavailable')
            self.assertNotIn('secret', failed['message'])

    def test_download_rejects_foreign_host_and_redirect(self):
        for url in ['http://catalog.oae.go.th/a', 'https://example.org/province.xlsx']:
            with self.assertRaises(ValueError):
                oae.get_bytes(url, 100)


if __name__ == '__main__':
    unittest.main()
