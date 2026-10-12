"""Daily VPD proxy units, missing weather and unchanged paired candidates."""
from datetime import date
from pathlib import Path
import sys
import unittest
import importlib.util
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from compare_harvest_stage_yield import daily_vpd, vpd_series, vpd_window, candidates, fit_predict


class VpdTests(unittest.TestCase):
    def check_target_independence(self, kind, parameter):
        train = pd.DataFrame(dict(province_code=['22'] * 15, year_ce=range(2000, 2015),
                                  yield_kg_per_rai_calculated=np.arange(15) * 10 + 100,
                                  previous_yield_kg_rai=np.arange(15) * 10 + 95))
        test = pd.DataFrame(dict(province_code=['22'], year_ce=[2015],
                                 yield_kg_per_rai_calculated=[250], previous_yield_kg_rai=[240]))
        config = dict(kind=kind, parameter=parameter, features=('previous_yield_kg_rai',))
        first = fit_predict(train, test, ['22'], config)
        test['yield_kg_per_rai_calculated'] = 10000000
        np.testing.assert_array_equal(first, fit_predict(train, test, ['22'], config))

    def test_scaled_svr_and_extra_trees_never_use_heldout_target(self):
        self.check_target_independence('svr', dict(C=1, gamma='scale'))
        self.check_target_independence('extra_trees', dict(max_depth=3, min_samples_leaf=3, max_features=1.0))

    @unittest.skipUnless(importlib.util.find_spec('catboost'), 'Optional advanced CatBoost dependency absent')
    def test_catboost_never_uses_heldout_target(self):
        self.check_target_independence('catboost', dict(depth=2, l2_leaf_reg=3, learning_rate=0.03))

    def test_units_saturation_and_missing(self):
        self.assertAlmostEqual(float(daily_vpd(20, 30, 50)), 1.645, places=2)
        self.assertEqual(float(daily_vpd(20, 30, 100)), 0)
        self.assertTrue(np.isnan(daily_vpd(np.nan, 30, 50)))
        for args in [(30, 20, 50), (20, 30, 101), (-999, 30, 50), (20, np.inf, 50)]:
            with self.assertRaises(ValueError):
                daily_vpd(*args)

    def test_windows_do_not_use_future_or_fill_missing(self):
        first = date(2020, 1, 1).toordinal()
        series = first, np.array([0, 1, 2, 1000, np.nan])
        mean, tail = vpd_window(series, [date(2020, 1, 4)], 0, -3, 0)
        self.assertEqual(mean, 1)
        self.assertAlmostEqual(tail, 1.8)
        with self.assertRaises(ValueError):
            vpd_window(series, [date(2020, 1, 5)], 0, 0, 1)
        with self.assertRaises(ValueError):
            vpd_window(series, [date(2019, 12, 31)], 0, 0, 1)

    def test_duplicate_source_days_and_paired_grid(self):
        row = dict(province_code='22', date='2020-01-01', T2M_MIN=20, T2M_MAX=30, RH2M=50)
        with self.assertRaises(ValueError):
            vpd_series([row, row])
        self.assertGreater(vpd_series([row])['22'][1][0], 0)
        original, added = candidates(), candidates(include_vpd=True)
        self.assertEqual(len(added), 74)
        self.assertEqual(added[:43], original)
        for config in added[43:]:
            matches = [c for c in original if c['model'] == config['model'][:-4]
                       and c['age_days'] == config['age_days'] and c['parameter'] == config['parameter']]
            self.assertEqual(len(matches), 1)
            self.assertEqual(config['features'][:-2], matches[0]['features'])
        self.assertEqual(len(candidates(True, True)), 136)
        self.assertEqual(len(candidates(True, True, True)), 236)
        with self.assertRaises(ValueError):
            candidates(advanced=True)


if __name__ == '__main__':
    unittest.main()
