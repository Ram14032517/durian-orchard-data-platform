import sys
from pathlib import Path
import unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from audit_expansion import eligible_as_of, valid_target, paired


class ExpansionAuditTests(unittest.TestCase):
    def test_release_guard(self):
        self.assertFalse(eligible_as_of(None, '2017-02-01'))
        self.assertFalse(eligible_as_of('2026-07-14', '2017-02-01'))
        self.assertTrue(eligible_as_of('2017-01-31', '2017-02-01'))

    def test_invalid_bearing_area_not_imputed(self):
        frame = pd.DataFrame(dict(production_tonnes=[0, 1, 2, float('nan')], bearing_rai=[1, 0, -1, 3]))
        self.assertEqual(valid_target(frame).tolist(), [True, False, False, False])

    def test_pair_gain_and_duplicates(self):
        frame = pd.DataFrame(dict(province_code=['22'], year_ce=[2017], actual_kg_rai=[10],
                                  predicted_kg_rai=[8], previous_year_kg_rai=[5]))
        self.assertEqual(paired(frame).gain_kg_rai.iloc[0], 3)
        with self.assertRaises(ValueError):
            paired(pd.concat([frame, frame]))


if __name__ == '__main__':
    unittest.main()
