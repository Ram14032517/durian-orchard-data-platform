import sys
import unittest
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from orchard_current_context import province_estimate, orchard_snapshot


def weather(lat, lon, start, end):
    rows=[]
    for i in range((end-start).days+1):
        rows.append(dict(date=(start+timedelta(days=i)).isoformat(), T2M=28., T2M_MIN=23.,
                         T2M_MAX=33., RH2M=75., PRECTOTCORR=2., ALLSKY_SFC_SW_DWN=18., WS2M=2.))
    return dict(rows=rows, provenance={'test':'synthetic fixture, not live weather'}, stale_cache=False)


class CurrentContextTests(unittest.TestCase):
    def test_future_window_cannot_be_labeled_observed(self):
        fetch=Mock(side_effect=AssertionError('No future observed requests'))
        r=province_estimate('84',2026,fetch,today=date(2026,3,1))
        self.assertEqual(r['status'],'pending_future_weather')
        self.assertIsNone(r['predicted_kg_rai'])
        fetch.assert_not_called()

    def test_prior_prediction_does_not_replace_actual_previous_year(self):
        r=province_estimate('84',2027,Mock(),today=date(2026,10,9))
        self.assertEqual(r['status'],'pending_prior_yield')

    def test_complete_weather_preserves_province_model_and_no_old_area(self):
        r=province_estimate('84',2026,weather,today=date(2026,10,9))
        self.assertEqual(r['status'],'retrospective_weather_estimate')
        self.assertGreater(r['predicted_kg_rai'],0)
        self.assertIsNone(r['predicted_tonnes'])
        self.assertEqual(r['season_months'],[6,7,8])

    def test_missing_weather_is_not_zero_filled(self):
        def missing(*args):
            data=weather(*args)
            for row in data['rows']:row['RH2M']=None
            return data
        r=province_estimate('84',2026,missing,today=date(2026,10,9))
        self.assertEqual(r['status'],'missing_weather')
        self.assertIsNone(r['predicted_kg_rai'])

    def test_unknown_province_fails(self):
        with self.assertRaises(ValueError):province_estimate('99',2026,Mock(),today=date(2026,10,9))

    def test_snapshot_has_no_private_raw_tables_or_device_ids(self):
        r=orchard_snapshot()
        self.assertNotIn('device_id',r)
        self.assertNotIn('readings',r)
        self.assertIn(r['status'],['missing','fresh_snapshot','stale_snapshot'])


if __name__=='__main__':unittest.main()
