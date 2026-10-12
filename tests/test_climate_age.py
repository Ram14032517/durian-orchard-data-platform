"""Adaptive-age scenarios: chronology, training-only normalization and controls."""
from datetime import date
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from experiment_climate_age import (AGE_GRID, CLIMATE_FIELDS, ages_for, belongs,
    candidates, completed_index_key, fit_predict_arrays, reference_stats)
from common import FEATURES, TARGET


class ClimateAgeTests(unittest.TestCase):
    def context(self):
        return pd.DataFrame(dict(province_code=['22'] * 5, year_ce=range(2010, 2015),
            reference_temperature_c=[24, 25, 26, 27, 35], reference_rain_mm=[10, 20, 30, 40, 5],
            reference_solar_mj_m2_day=[10, 11, 12, 13, 20], reference_roni_c=[0, 0, 0, 0, 1]))

    def test_completed_season_never_uses_current_or_future_month(self):
        self.assertEqual(completed_index_key(date(2025, 1, 1)), (2024, 11))
        self.assertEqual(completed_index_key(date(2025, 12, 31)), (2025, 10))

    def test_test_weather_cannot_change_training_climatology(self):
        frame = self.context()
        before = reference_stats(frame, 2013)
        frame.loc[frame.year_ce.eq(2014), list(CLIMATE_FIELDS)] = 10000
        self.assertEqual(before, reference_stats(frame, 2013))
        self.assertEqual(before['22']['rows'], 4)

    def test_age_controls_bounds_and_direction(self):
        context = self.context()
        reference = reference_stats(context, 2013)
        for kind, expected in [('heat', 110), ('enso', 110), ('wet', 110), ('enso_local', 110)]:
            config = dict(kind=kind, base_age=120, amplitude=10)
            self.assertEqual(ages_for(context, reference, config)[-1], expected)
        cold = context.copy()
        cold['reference_roni_c'] = -1
        self.assertEqual(ages_for(cold, reference, dict(kind='enso', base_age=150, amplitude=10))[-1], 160)
        np.testing.assert_array_equal(ages_for(context, reference, dict(kind='fixed', base_age=140)), [140] * 5)

    def test_fixed_grid_and_nested_zero_shift_controls(self):
        configs = candidates()
        self.assertEqual(len(configs), 153)
        self.assertEqual(sum(belongs(c, 'fixed_original') for c in configs), 12)
        self.assertEqual(sum(belongs(c, 'fixed_expanded') for c in configs), 33)
        for strategy in ('enso_age', 'local_age', 'enso_local_age'):
            self.assertTrue(all(belongs(c, strategy) for c in configs if belongs(c, 'fixed_original')))

    def test_heldout_yield_never_enters_fit_or_age_selection(self):
        context = self.context()
        base = context[['province_code', 'year_ce']].copy()
        base[TARGET] = [100, 110, 120, 130, 999]
        bank = np.ones((len(AGE_GRID), 5, len(FEATURES)))
        reference = reference_stats(context, 2013)
        config = dict(kind='enso', base_age=130, amplitude=10, alpha=1)
        first = fit_predict_arrays(base, bank, context, reference, config, 2014)
        base.loc[base.year_ce.eq(2014), TARGET] = 10000000
        second = fit_predict_arrays(base, bank, context, reference, config, 2014)
        np.testing.assert_array_equal(first[0], second[0])
        np.testing.assert_array_equal(first[1], second[1])


if __name__ == '__main__':
    unittest.main()
