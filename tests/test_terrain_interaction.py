import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from experiment_terrain_interaction import (slope_pct, validate_response, add_terrain, inner_years,
                                           PROVINCES, TARGET, predict_year, infer_candidate, FEATURES, EXTREMES)


class TerrainTests(unittest.TestCase):
    def test_slope_percent_and_flat(self):
        self.assertEqual(slope_pct(np.ones((3, 3)), 15), 0)
        spacing = np.pi * 6371008.8 / (180 * 3600)
        grid = np.tile(np.array([-1, 0, 1]) * spacing * .1, (3, 1))
        self.assertAlmostEqual(slope_pct(grid, 0), 10)
        with self.assertRaises(ValueError):
            slope_pct(np.full((3, 3), np.nan), 15)

    def test_dem_missing_and_reordered_fail(self):
        response = dict(status='OK', results=[dict(dataset='srtm30m', elevation=20,
                                                   location=dict(lat=15, lng=100))])
        np.testing.assert_array_equal(validate_response(response, [(15, 100)]), [20])
        with self.assertRaises(ValueError):
            validate_response(response, [(16, 100)])
        response['results'][0]['elevation'] = None
        with self.assertRaises(ValueError):
            validate_response(response, [(15, 100)])

    def test_join_and_interactions_no_missing_zero(self):
        frame = pd.DataFrame(dict(province_code=PROVINCES, year_ce=[2020] * 5,
                                  fruit_rx7day_mm=[2.] * 5, early_fruit_hot38_days=[3.] * 5))
        table = pd.DataFrame(dict(province_code=PROVINCES, terrain_elevation_m=[100.] * 5,
                                  terrain_slope_pct=[10.] * 5))
        result = add_terrain(frame, table)
        np.testing.assert_array_equal(result.slope_x_rx7, [20] * 5)
        np.testing.assert_array_equal(result.elevation_x_hot38, [300] * 5)
        with self.assertRaises(ValueError):
            add_terrain(frame, table.iloc[:-1])

    def test_static_terrain_in_province_indicator_span(self):
        indicators = np.eye(5)
        terrain = indicators @ np.array([1., 2., 7., 4., 8.])
        self.assertEqual(np.linalg.matrix_rank(np.c_[indicators, terrain]), 5)

    def test_inner_folds_and_future_targets(self):
        self.assertEqual(inner_years(2017), [2014, 2015, 2016])
        frame = pd.DataFrame(dict(province_code=['22'] * 7, year_ce=range(2010, 2017),
                                  previous_yield_kg_rai=np.arange(7.) + 10))
        frame[TARGET] = np.arange(7.) + 11
        first = predict_year(frame, 2014, ['previous_yield_kg_rai'], 1)[0]
        frame.loc[frame.year_ce.ge(2014), TARGET] = 999999
        np.testing.assert_array_equal(first, predict_year(frame, 2014, ['previous_yield_kg_rai'], 1)[0])

    def candidate_fixture(self):
        columns = FEATURES + EXTREMES
        width = len(PROVINCES) + 1 + len(columns)
        bundle = dict(provinces=PROVINCES, config=dict(group='weather_control', age_days=140),
                      predictors=columns, train_end=2025, season_months={p: [4, 5, 6] for p in PROVINCES},
                      parameters=dict(mean=[0.] * width, scale=[1.] * width, coef=[0.] * width, intercept=500.))
        frame = pd.DataFrame([dict(province_code='22', year_ce=2026, age_days=140, season_months='4,5,6',
                                   bearing_rai=1000., **{c: 1. for c in columns})])
        return bundle, frame

    def test_prediction_contract_and_tonnes(self):
        bundle, frame = self.candidate_fixture()
        result = infer_candidate(bundle, frame)
        self.assertEqual(result.predicted_kg_rai.iloc[0], 500)
        self.assertEqual(result.predicted_tonnes_conditional.iloc[0], 500)
        for name, value in [('year_ce', 2025), ('age_days', 120), ('season_months', '5,6,7'),
                            ('early_fruit_hot38_days', 31), ('bearing_rai', 0)]:
            with self.assertRaises(ValueError):
                infer_candidate(bundle, frame.assign(**{name: value}))

    def test_predictions_reject_targets_and_unverified_model(self):
        bundle, frame = self.candidate_fixture()
        with self.assertRaises(ValueError):
            infer_candidate(bundle, frame.assign(actual_kg_rai=999))
        with self.assertRaises(ValueError):
            infer_candidate(bundle, frame.assign(previous_yield_kg_rai=np.nan))
        bundle['config']['group'] = 'supplied_main'
        with self.assertRaises(ValueError):
            infer_candidate(bundle, frame)


if __name__ == '__main__':
    unittest.main()
