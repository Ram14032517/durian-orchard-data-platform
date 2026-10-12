import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from experiment_dry_trigger import triggers, choose_blooms


class DryTriggerTests(unittest.TestCase):
    def fixture(self):
        first = date(2020, 1, 1)
        rain = np.full(160, 10.)
        rain[25:45] = 0
        return first, rain

    def test_first_crossing_not_end_of_episode(self):
        first, rain = self.fixture()
        events, _ = triggers(first.toordinal(), rain, first + timedelta(days=20), first + timedelta(days=80))
        self.assertEqual(events, [first + timedelta(days=38)])

    def test_reset_and_next_new_episode(self):
        first, rain = self.fixture()
        rain[50] = 26
        rain[70:90] = 0
        events, audit = triggers(first.toordinal(), rain, first + timedelta(days=20), first + timedelta(days=100), True)
        self.assertEqual(audit['rejected_rain_reset'], 1)
        self.assertEqual(events, [first + timedelta(days=83)])

    def test_left_censored_drought_is_not_new_trigger(self):
        first, rain = self.fixture()
        events, audit = triggers(first.toordinal(), rain, first + timedelta(days=40), first + timedelta(days=80))
        self.assertTrue(audit['left_censored_at_search_start'])
        self.assertEqual(events, [])

    def test_fallback_and_fifty_day_lag(self):
        harvest = date(2021, 6, 1)
        nominal = harvest - timedelta(days=120)
        blooms, found = choose_blooms([harvest], 120, [nominal - timedelta(days=45)])
        self.assertEqual(blooms, [nominal + timedelta(days=5)])
        self.assertTrue(found[0])
        blooms, found = choose_blooms([harvest], 120, [])
        self.assertEqual(blooms, [nominal])
        self.assertFalse(found[0])

    def test_missing_weather_fails_not_fallback(self):
        first, rain = self.fixture()
        rain[30] = np.nan
        with self.assertRaises(ValueError):
            triggers(first.toordinal(), rain, first + timedelta(days=20), first + timedelta(days=80))


if __name__ == '__main__':
    unittest.main()
