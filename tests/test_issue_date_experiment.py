"""Forecast-cutoff checks: future weather/labels never affect earlier predictions."""
from datetime import date
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from experiment_issue_date import IssueWeather, stage_feature, prior_interval, score


class IssueDateTests(unittest.TestCase):
    def test_future_weather_is_replaced_even_if_finite(self):
        source = np.array([[2., 9999.]])
        observed = np.array([[True, False]])
        normal = np.array([[4., 6.]])
        self.assertEqual(stage_feature(source, observed, normal, 'sum'), (8., .5))
        source[0, 1] = np.nan
        self.assertEqual(stage_feature(source, observed, normal, 'sum'), (8., .5))
        source[0, 0] = np.nan
        with self.assertRaises(ValueError):
            stage_feature(source, observed, normal, 'sum')

    def test_climatology_and_stage_ignore_all_post_issue_weather(self):
        days = pd.date_range('2000-01-01', '2011-12-31')
        raw = [dict(province_code='22', date=d.strftime('%Y-%m-%d'), T2M=25.,
                    T2M_MIN=20., T2M_MAX=30., RH2M=60., PRECTOTCORR=2.,
                    ALLSKY_SFC_SW_DWN=15.) for d in days]
        first, issue, available, coverage = IssueWeather(raw).features('22', 2010, [4, 5, 6], 60)
        self.assertEqual((issue - available).days, 7)
        for row in raw:
            if date.fromisoformat(row['date']) > available:
                row['PRECTOTCORR'] = 500.
                row['ALLSKY_SFC_SW_DWN'] = 40.
        second, *_ = IssueWeather(raw).features('22', 2010, [4, 5, 6], 60)
        self.assertEqual(first, second)
        self.assertTrue(any(item['climatology_fraction'] > 0 for item in coverage))

    def test_interval_never_uses_current_or_later_errors(self):
        frame = pd.DataFrame(dict(year_ce=range(2017, 2024), predicted_kg_rai=100.,
                                  actual_kg_rai=[90.] * 5 + [99999., 99999.]))
        self.assertEqual(prior_interval(frame, 2022), 10.)
        self.assertIsNone(prior_interval(frame, 2021))

    def test_metrics_units_and_zero_denominators(self):
        self.assertEqual(score([100., 200.], [110., 180.])['wape_pct'], 10.)
        self.assertIsNone(score([0., 0.], [0., 0.])['wape_pct'])


if __name__ == '__main__':
    unittest.main()
