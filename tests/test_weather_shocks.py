import sys
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from experiment_weather_shocks import longest_run, shock_values, window, predict_year, TARGET


class WeatherShockTests(unittest.TestCase):
    def test_runs_reset_and_cohorts_stay_separate(self):
        np.testing.assert_array_equal(longest_run([[1, 1, 0, 1], [0, 1, 1, 1]]), [2, 3])

    def test_thresholds_rain_sums_and_stage_boundaries(self):
        first = date(2020, 1, 1).toordinal()
        rain = np.full(160, 1.)
        tmax = np.full(160, 35.)
        # Harvest at offset 140, assumed flower at offset 20.
        rain[0:5] = 0
        rain[20:24] = 0
        rain[100:107] = 10
        tmax[20:23] = [36, 38, 39]
        value = shock_values(first - 90, np.r_[np.ones(90), rain], np.r_[np.full(90, 35.), tmax],
                             [date.fromordinal(first + 140)], 120)
        self.assertEqual(value['pre_bloom_cdd_days'], 5)
        self.assertEqual(value['early_fruit_cdd_days'], 4)
        self.assertEqual(value['early_fruit_hot35_days'], 3)
        self.assertEqual(value['early_fruit_hot38_days'], 1)
        self.assertEqual(value['early_fruit_hot35_run_days'], 3)
        self.assertEqual(value['fruit_rx3day_mm'], 30)
        self.assertEqual(value['fruit_rx7day_mm'], 70)

    def test_missing_and_outside_coverage_fail_closed(self):
        with self.assertRaises(ValueError):
            window(1, np.array([1., np.nan]), [date.fromordinal(2)], 0, 0, 1)
        with self.assertRaises(ValueError):
            window(1, np.ones(5), [date.fromordinal(1)], 2, 0, 1)

    def test_heldout_target_does_not_change_prediction(self):
        frame = pd.DataFrame(dict(province_code=['22'] * 5, year_ce=range(2010, 2015),
                                  previous_yield_kg_rai=[10, 20, 30, 40, 50]))
        frame[TARGET] = [11, 22, 33, 44, 55]
        first = predict_year(frame, 2014, ['previous_yield_kg_rai'], 1)[0]
        frame.loc[frame.year_ce.eq(2014), TARGET] = 999999
        np.testing.assert_array_equal(first, predict_year(frame, 2014, ['previous_yield_kg_rai'], 1)[0])


if __name__ == '__main__':
    unittest.main()
