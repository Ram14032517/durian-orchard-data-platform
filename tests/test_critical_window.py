import sys
import unittest
from datetime import date
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from experiment_critical_window import critical_values


class CriticalWindowTests(unittest.TestCase):
    def fixture(self):
        first = date(2020, 1, 1).toordinal()
        return first, np.ones(180), np.full(180, 38.), [date.fromordinal(first + 120)], 120

    def test_inclusive_boundaries_and_strict_hot_threshold(self):
        first, rain, heat, days, age = self.fixture()
        heat[[29, 30, 50, 51]] = 39
        value = critical_values(first, rain, heat, days, age)
        self.assertEqual(value['critical_hot38_days'], 2)
        self.assertEqual(value['critical_hot38_run_days'], 1)

    def test_surge_uses_prior_seven_days_not_current_or_future(self):
        first, rain, heat, days, age = self.fixture()
        rain[23:30] = 0
        rain[30] = 10
        value = critical_values(first, rain, heat, days, age)
        self.assertEqual(value['critical_rain_after_dry_days'], 1)
        rain[26] = 1
        self.assertEqual(critical_values(first, rain, heat, days, age)['critical_rain_after_dry_days'], 0)

    def test_interaction_and_truncated_dry_run(self):
        first, rain, heat, days, age = self.fixture()
        rain[30:35] = 0
        heat[30:33] = 39
        value = critical_values(first, rain, heat, days, age)
        self.assertEqual(value['critical_cdd_days'], 5)
        self.assertEqual(value['critical_hot38_x_cdd'], 15)

    def test_missing_data_rejected(self):
        first, rain, heat, days, age = self.fixture()
        rain[25] = np.nan
        with self.assertRaises(ValueError):
            critical_values(first, rain, heat, days, age)


if __name__ == '__main__':
    unittest.main()
