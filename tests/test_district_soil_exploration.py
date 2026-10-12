"""District evidence must not multiply into fabricated soil-yield samples."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('map_builder',ROOT/'tools/build_unified_orchard_map.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class DistrictSoilExplorationTests(unittest.TestCase):
    def test_preserves_targets_and_missingness_without_soil_expansion(self):
        evidence=json.loads((ROOT/'research_data/five_province_history/production_source_review.json').read_text(encoding='utf-8'))
        soils=[dict(province_code='53',district='อ.ลับแล',soil_code=code) for code in ['SC','Ty']]
        rows=builder.district_exploration([],soils,evidence)
        self.assertEqual(len(rows),14)
        self.assertEqual(sum(r['production_tonnes'] is not None for r in rows),8)
        lablae=[r for r in rows if r['district']=='อ.ลับแล']
        self.assertEqual(len(lablae),2)
        self.assertEqual(lablae[0]['soil_codes'],'SC;Ty')
        self.assertEqual(lablae[0]['production_tonnes'],17976)
        self.assertAlmostEqual(lablae[0]['calculated_yield_kg_rai'],17976000/31592)
        self.assertTrue(all(not r['train_eligible'] and r['soil_ph_numeric'] is None for r in rows))
        self.assertTrue(all(r['yield_precision_warning'] for r in rows if r['district']=='อ.ทองแสนขัน'))
        self.assertTrue(all(r['calculated_yield_kg_rai'] is None for r in rows if r['district']=='อ.ตรอน'))

if __name__=='__main__':unittest.main()
