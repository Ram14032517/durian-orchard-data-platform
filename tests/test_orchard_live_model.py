import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from orchard_live_model import (HOURS, WEATHER, prepare_readings, prepare_forecasts,
                               forecast_at, make_panel, train_before, estimate, vpd)


def readings():
    times = pd.date_range('2026-10-01', periods=20, freq='15min', tz='UTC')
    frame = pd.DataFrame({field: np.ones(20) for field in WEATHER})
    frame['recorded_at'] = times.astype(str)
    frame['event_id'] = np.arange(20)
    frame['device_id'] = 'test'
    frame['soil_moisture_percent'] = 30.
    frame['soil_temperature_c'] = 27.
    frame['outdoor_temperature_c'] = 30.
    frame['outdoor_humidity_percent'] = 70.
    frame['air_temperature_c'] = 40.
    frame['humidity_percent'] = 10.
    return frame


def forecast(origin, available, rain=1.):
    return pd.DataFrame(dict(
        forecast_time=pd.date_range(origin + pd.Timedelta(hours=1), periods=HOURS, freq='1h').astype(str),
        issued_at=available.isoformat(), received_at=available.isoformat(), source='tmd',
        temperature_c=30., humidity_percent=70., rain_mm=rain))


class OrchardLiveTests(unittest.TestCase):
    def test_online_stale_rule_never_revises_past(self):
        raw = readings()
        prefix, _ = prepare_readings(raw.iloc[:4])
        full, _ = prepare_readings(raw)
        pd.testing.assert_series_equal(prefix.vpd_kpa, full.vpd_kpa.iloc[:4])
        self.assertFalse(full.weather_stale_online.iloc[3])
        self.assertTrue(full.weather_stale_online.iloc[4])
        self.assertEqual(full.soil_moisture_percent.iloc[4], 30.)

    def test_only_outdoor_weather_and_valid_ranges(self):
        prepared, _ = prepare_readings(readings())
        self.assertAlmostEqual(prepared.vpd_kpa.iloc[0], float(vpd(30., 70.)))
        self.assertTrue(np.isnan(vpd(30., 101.)))
        self.assertTrue(np.isnan(vpd(np.nan, 70.)))

    def test_forecast_vintage_is_available_at_origin(self):
        origin = pd.Timestamp('2026-10-01T12:00:00Z')
        before = forecast(origin, origin - pd.Timedelta(hours=1), rain=2.)
        after = forecast(origin, origin + pd.Timedelta(minutes=1), rain=99.)
        selected = forecast_at(prepare_forecasts(pd.concat([before, after])), origin)
        self.assertEqual(selected['forecast_rain_max_mm'], 2.)
        self.assertLessEqual(pd.Timestamp(selected['forecast_available_utc']), origin)

    def test_incomplete_batches_are_not_combined(self):
        origin = pd.Timestamp('2026-10-01T12:00:00Z')
        first = forecast(origin, origin - pd.Timedelta(hours=1)).iloc[:3]
        second = forecast(origin, origin - pd.Timedelta(hours=2)).iloc[3:]
        self.assertIsNone(forecast_at(prepare_forecasts(pd.concat([first, second])), origin))

    def test_missing_rain_and_timezone_do_not_become_zero(self):
        origin = pd.Timestamp('2026-10-01T12:00:00Z')
        raw = forecast(origin, origin - pd.Timedelta(hours=1))
        raw.loc[0, 'rain_mm'] = np.nan
        self.assertIsNone(forecast_at(prepare_forecasts(raw), origin))
        raw['forecast_time'] = '2026-10-01 13:00:00'
        with self.assertRaises(ValueError):
            prepare_forecasts(raw)

    def test_training_purges_future_labels(self):
        index = pd.date_range('2026-10-01', periods=12, freq='1h', tz='UTC')
        frame = pd.DataFrame({'target_time': index + pd.Timedelta(hours=HOURS)}, index=index)
        cutoff = index[10]
        result = train_before(frame, cutoff)
        self.assertEqual(len(result), 4)
        self.assertTrue(result.target_time.lt(cutoff).all())

    def test_missing_sensor_path_invalidates_target(self):
        index = pd.date_range('2026-10-01', periods=12, freq='1h', tz='UTC')
        hourly = pd.DataFrame({'soil': 30.}, index=index)
        hourly.loc[index[3], 'soil'] = np.nan
        forecasts = prepare_forecasts(forecast(index[0], index[0]))
        panel = make_panel(hourly, forecasts)
        self.assertTrue(np.isnan(panel.target_soil.iloc[0]))

    def test_negative_change_is_not_clipped_to_zero(self):
        model = dict(mean=[0.], scale=[1.], coef=[0.], intercept=-5.)
        frame = pd.DataFrame({'soil': [30.]})
        self.assertEqual(estimate(model, frame, ['soil'])[0], 25.)

    def test_duplicates_and_multiple_devices_fail(self):
        raw = readings()
        with self.assertRaises(ValueError):
            prepare_readings(pd.concat([raw, raw.iloc[:1]]))
        raw.loc[0, 'device_id'] = 'other'
        with self.assertRaises(ValueError):
            prepare_readings(raw)


if __name__ == '__main__':
    unittest.main()
