"""Leakage, chronology and weather-zero regression checks for the yield experiment."""
from datetime import date
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_harvest_backcast import exposure, weather_series
from compare_harvest_stage_yield import candidates, fit_predict, training_seasons


class HarvestStageYieldTests(unittest.TestCase):
    def test_zero_is_observed_not_missing(self):
        row = dict(province_code='22', date='2020-12-31', T2M=25,
                   PRECTOTCORR=0.0, RH2M=75, ALLSKY_SFC_SW_DWN=0, WS2M=0)
        series = weather_series([row])['22']
        result = exposure(series, [date(2021, 4, 30)], 120, 0, 1)
        self.assertEqual(result['rain_mm'], 0)
        self.assertEqual(result['rain_mm_coverage_pct'], 100)
        row['PRECTOTCORR'] = ''
        missing = exposure(weather_series([row])['22'], [date(2021, 4, 30)], 120, 0, 1)
        self.assertIsNone(missing['rain_mm'])
        self.assertEqual(missing['rain_mm_coverage_pct'], 0)

    def test_heldout_harvest_cannot_choose_season(self):
        harvest = pd.DataFrame([
            dict(province_code='22', year_ce=2010, month_number=5, tonnes=100),
            dict(province_code='22', year_ce=2011, month_number=9, tonnes=1000000),
        ])
        self.assertEqual(training_seasons(harvest, 2010), {'22': [4, 5, 6]})
        harvest.loc[1, 'month_number'] = 2
        self.assertEqual(training_seasons(harvest, 2010), {'22': [4, 5, 6]})
        self.assertEqual(training_seasons(harvest, 2011), {'22': [1, 2, 3]})

    def test_heldout_target_not_used_by_estimators(self):
        train = pd.DataFrame(dict(province_code=['22'] * 15, year_ce=range(2000, 2015),
                                  yield_kg_per_rai_calculated=np.arange(15) * 10 + 100,
                                  previous_yield_kg_rai=np.arange(15) * 10 + 95))
        heldout = pd.DataFrame(dict(province_code=['22'], year_ce=[2015],
                                    yield_kg_per_rai_calculated=[250], previous_yield_kg_rai=[240]))
        for kind in ('ridge', 'random_forest', 'gradient_boosting'):
            config = dict(kind=kind, parameter=5, features=('previous_yield_kg_rai',))
            first = fit_predict(train, heldout, ['22'], config)
            heldout['yield_kg_per_rai_calculated'] = 1000000
            np.testing.assert_array_equal(first, fit_predict(train, heldout, ['22'], config))

    def test_future_training_rejected(self):
        config = dict(kind='previous_year')
        frame = pd.DataFrame(dict(year_ce=[2020], previous_yield_kg_rai=[100]))
        with self.assertRaises(ValueError):
            fit_predict(frame, frame, ['22'], config)

    def test_small_fixed_grid_and_no_same_year_output_features(self):
        configs = candidates()
        self.assertEqual(len(configs), 43)
        for config in configs:
            self.assertFalse(set(config['features']) & {
                'production_tonnes', 'bearing_rai', 'yield_kg_per_rai_calculated', 'tonnes'})


if __name__ == '__main__':
    unittest.main()
