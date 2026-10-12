"""Satellite scaling, cloudy gaps, composite timing, and paired model controls."""
from datetime import date
from pathlib import Path
from http.client import RemoteDisconnected
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from fetch_modis_ndvi import fetch_json, good_pixels, ndvi_series, ndvi_exposure, parse_subset, PREFIX
from compare_harvest_stage_yield import candidates, fit_predict, ndvi_annual_rows


def composite(day='2020-01-01', end='2020-01-16', value='0.8'):
    return dict(province_code='22', composite_start_date=day, composite_end_date=end, ndvi_mean=value)


class NdviTests(unittest.TestCase):
    def test_remote_disconnect_retries_and_success_is_cached(self):
        with TemporaryDirectory() as folder, patch('fetch_modis_ndvi.DATA', Path(folder)), \
                patch('fetch_modis_ndvi.ROOT', Path(folder)), \
                patch('fetch_modis_ndvi.time.sleep'), \
                patch('fetch_modis_ndvi.urlopen', side_effect=[RemoteDisconnected(), BytesIO(b'{"ok": true}')]) as request:
            self.assertEqual(fetch_json('https://example.test/subset')[0], {'ok': True})
            self.assertEqual(fetch_json('https://example.test/subset')[0], {'ok': True})
            self.assertEqual(request.call_count, 2)

    def test_zero_greenness_is_observed_and_clouds_fill_water_are_excluded(self):
        ndvi = [0, -3000, 9000, 9000, 9000, 9000, 9000, 9000]
        rel = [0, 0, 3, 0, 0, 0, 0, 0]
        qa = [2048, 2048, 2048, 0, 2048 | 256, 2048 | 1024, 2048 | 32768, 2048 | 192]
        np.testing.assert_array_equal(good_pixels(ndvi, rel, qa), [True, False, False, False, False, False, False, False])

    def test_integer_and_shape_validation(self):
        for ndvi, rel, qa in [([1000.5], [0], [2048]), ([np.nan], [0], [2048]), ([0, 0], [0], [2048])]:
            with self.assertRaises(ValueError):
                good_pixels(ndvi, rel, qa)

    def test_parser_applies_scale_once_and_does_not_turn_clouds_into_zero(self):
        point = dict(province_code='22', province_name='จันทบุรี', weather_latitude=12.815, weather_longitude=102.17964)
        response = dict(latitude=12.815, longitude=102.17964, nrows=1, ncols=2,
                        cellsize=231.65, xllcorner=0, yllcorner=0, subset=[])
        for band, values in [('NDVI', [8000, -3000]), ('pixel_reliability', [0, 3]), ('VI_Quality', [2048, 2048])]:
            response['subset'].append(dict(band=PREFIX + band, data=values, calendar_date='2020-01-01',
                                           modis_date='A2020001', tile='h27v07', proc_date='2020049123456'))
        row = parse_subset(response, point, dict(url='fixture', sha256='fixture'), 0.0001)[0]
        self.assertEqual(row['ndvi_mean'], 0.8)
        self.assertEqual(row['good_pixel_pct'], 50)
        response['subset'][1]['data'] = [3, 3]
        self.assertEqual(parse_subset(response, point, dict(url='fixture', sha256='fixture'), 0.0001)[0]['ndvi_mean'], '')
        response['subset'][1]['proc_date'] = 'different_processing_version'
        with self.assertRaises(ValueError):
            parse_subset(response, point, dict(url='fixture', sha256='fixture'), 0.0001)

    def test_duplicate_intervals_rejected(self):
        with self.assertRaises(ValueError):
            ndvi_series([composite(), composite()])

    def test_exposure_uses_only_overlapping_period_and_preserves_missing(self):
        series = ndvi_series([composite(), composite('2020-01-17', '2020-02-01', '0.2')])['22']
        result = ndvi_exposure(series, [date(2020, 1, 25)], 0, -8, 0)
        self.assertEqual(result['mean'], 0.2)
        self.assertEqual(result['coverage_pct'], 100)
        # February does not gain invented daily observations from the last composite.
        missing = ndvi_exposure(series, [date(2020, 2, 20)], 0, 0, 16)
        self.assertTrue(np.isnan(missing['mean']))
        self.assertEqual(missing['coverage_pct'], 0)

    def test_previous_year_window_is_supported(self):
        series = ndvi_series([composite('2019-12-19', '2019-12-31', '0.7'), composite()])['22']
        result = ndvi_exposure(series, [date(2020, 1, 9)], 0, -16, 0)
        self.assertAlmostEqual(result['mean'], (8 * 0.7 + 8 * 0.8) / 16)

    def test_annual_features_do_not_borrow_future_year(self):
        series = ndvi_series([composite(), composite('2021-01-01', '2021-01-16', '1')])
        frame = ndvi_annual_rows(pd.DataFrame([dict(province_code='22', year_ce=2020)]), series)
        self.assertTrue(np.isnan(frame.iloc[0].ndvi_annual_mean))
        self.assertAlmostEqual(frame.iloc[0].ndvi_annual_coverage_pct, 16 / 366 * 100)

    def test_added_candidates_are_exact_weather_pairs(self):
        original = candidates()
        extended = candidates(True)
        self.assertEqual(len(original), 43)
        self.assertEqual(len(extended), 74)
        self.assertEqual(extended[:43], original)
        for added in extended[43:]:
            paired = [c for c in original if c['model'] == added['model'][:-5]
                      and c['parameter'] == added['parameter'] and c['age_days'] == added['age_days']]
            self.assertEqual(len(paired), 1)
            self.assertEqual(added['features'][:-2], paired[0]['features'])

    def test_missing_ndvi_uses_training_median_not_test_or_target(self):
        train = pd.DataFrame(dict(province_code=['22'] * 8, year_ce=range(2000, 2008),
                                  yield_kg_per_rai_calculated=np.arange(8) * 10 + 100,
                                  previous_yield_kg_rai=np.arange(8) * 10 + 95,
                                  ndvi_test=[0.1, 0.2, np.nan, 0.4, 0.5, 0.6, 0.7, 0.8]))
        heldout = pd.DataFrame(dict(province_code=['22'], year_ce=[2008],
                                    yield_kg_per_rai_calculated=[180], previous_yield_kg_rai=[175], ndvi_test=[np.nan]))
        config = dict(kind='ridge', parameter=10, features=('previous_yield_kg_rai', 'ndvi_test'))
        first = fit_predict(train, heldout, ['22'], config)
        heldout.yield_kg_per_rai_calculated = 100000
        np.testing.assert_array_equal(first, fit_predict(train, heldout, ['22'], config))
        self.assertTrue(heldout.ndvi_test.isna().all())
        self.assertEqual(train.ndvi_test.isna().sum(), 1)
        train['ndvi_test'] = np.nan
        with self.assertRaises(ValueError):
            fit_predict(train, heldout, ['22'], config)


if __name__ == '__main__':
    unittest.main()
