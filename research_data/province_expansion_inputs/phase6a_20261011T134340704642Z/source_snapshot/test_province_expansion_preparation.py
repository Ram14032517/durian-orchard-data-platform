"""Phase 6A regression checks. No estimator is instantiated or fitted."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
import experiment_province_expansion as pe
import experiment_rebaseline as rb
from audit_province_expansion_inputs import check_hashes
from availability_guard import check_feature_lineage
from experiment_issue_date import IssueWeather


class ProvincePreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.annual = pd.read_csv(pe.ANNUAL, dtype={'province_code': str})

    def weather(self):
        values = {'T2M': 25., 'T2M_MAX': 30., 'T2M_MIN': 20., 'RH2M': 60.,
                  'PRECTOTCORR': 1., 'ALLSKY_SFC_SW_DWN': 15., 'WS2M': 2.}
        return dict(header=dict(start='20000101', end='20000102', time_standard='LST', fill_value=-999.),
                    parameters={k: dict(units=v) for k, v in pe.UNITS.items()},
                    properties=dict(parameter={k: dict.fromkeys(['20000101', '20000102'], v)
                                               for k, v in values.items()}))

    def test_locked_cohort_and_evaluation_keys(self):
        self.assertEqual(pe.NEW, ['21', '30', '77', '80', '85'])
        self.assertEqual(pe.COHORTS['5'], rb.PROVINCES)
        self.assertEqual(len(set(pe.COHORTS['10'])), 10)
        primary = {(p, y) for p in pe.COHORTS['5'] for y in rb.OUTER_YEARS}
        self.assertEqual(len(primary), 45)
        self.assertFalse(primary & {(p, y) for p in pe.NEW for y in rb.OUTER_YEARS})

    def test_complete_target_and_lag_sources(self):
        self.assertEqual(len(pe.check_annual(self.annual)), 170)
        for incomplete in (self.annual[~(self.annual.province_code.eq('21') & self.annual.year_ce.eq(2009))],
                           self.annual[self.annual.province_code.ne('85')],
                           pd.concat([self.annual, self.annual[self.annual.province_code.eq('30') & self.annual.year_ce.eq(2010)]])):
            with self.assertRaises(ValueError):
                pe.check_annual(incomplete)

    def test_invalid_target_never_imputed(self):
        for col, value in [('bearing_rai', 0), ('production_tonnes', np.nan), (rb.TARGET, 999999)]:
            data = self.annual.copy()
            data.loc[data.province_code.eq('21') & data.year_ce.eq(2010), col] = value
            with self.assertRaises(ValueError):
                pe.check_annual(data)

    def test_pretraining_calendar_reconciles_without_filling_months(self):
        evidence = pe.verify_calendar(pe.check_annual(self.annual))
        self.assertEqual([e['peak_month'] for e in evidence], [5, 6, 7, 8, 8])
        self.assertTrue(all(e['reconciled_years'] == 6 and e['years'] == [2004, 2009] for e in evidence))

    def test_missing_calendar_year_fails(self):
        original = pd.read_excel(pe.MONTHLY, sheet_name='durian_monthly')
        incomplete = original[~(original.province_name.eq('ระยอง') & original.year.eq(2547))]
        with patch.object(pe.pd, 'read_excel', return_value=incomplete):
            with self.assertRaises(ValueError):
                pe.verify_calendar(pe.check_annual(self.annual))

    def test_shared_cutoff_unchanged_every_inner_outer(self):
        schedule = dict(kind='fixed_calendar', anchors=pe.ANCHORS)
        for outer in rb.OUTER_YEARS:
            for y in range(outer - 3, outer + 1):
                old = min(rb.issue_date(schedule, p, y, 60) for p in rb.PROVINCES)
                expanded = min(rb.issue_date(schedule, p, y, 60) for p in pe.COHORTS['10'])
                self.assertEqual(old, expanded)
                self.assertEqual(old.month, 2 if y % 4 == 0 else 1)

    def test_valid_weather_units_and_dates(self):
        frame = pe.decode_weather(self.weather(), '21', '20000101', '20000102')
        self.assertEqual(len(frame), 2)
        self.assertTrue(np.isfinite(frame[pe.PARAMS].to_numpy()).all())

    def test_missing_weather_records_fail(self):
        for change in (lambda d: d['properties']['parameter'].pop('WS2M'),
                       lambda d: d['properties']['parameter']['T2M'].pop('20000102'),
                       lambda d: d['properties']['parameter']['T2M'].update({'20000101': -999.})):
            data = self.weather()
            change(data)
            with self.assertRaises((ValueError, KeyError)):
                pe.decode_weather(data, '21', '20000101', '20000102')

    def test_wrong_units_time_standard_physical_values_fail(self):
        for change in (lambda d: d['parameters']['ALLSKY_SFC_SW_DWN'].update(units='kWh/m^2/day'),
                       lambda d: d['header'].update(time_standard='UTC'),
                       lambda d: d['properties']['parameter']['RH2M'].update({'20000101': 101.})):
            data = self.weather()
            change(data)
            with self.assertRaises(ValueError):
                pe.decode_weather(data, '21', '20000101', '20000102')

    def test_artifacts_exclusive_no_path_escape(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pe, 'ROOT', Path(directory)):
            destination = pe.reserve('synthetic')
            pe.write_json(destination / 'test.json', dict(value=1))
            with self.assertRaises(FileExistsError):
                pe.reserve('synthetic')
            with self.assertRaises(FileExistsError):
                pe.write_json(destination / 'test.json', dict(value=2))
            with self.assertRaises(ValueError):
                pe.reserve('../escape')

    def test_exact_source_version_hash_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pe.write_json(root / 'source.json', dict(value=1))
            hashes = {'source.json': rb.digest(root / 'source.json')}
            check_hashes(root, hashes)
            with self.assertRaises(ValueError):
                check_hashes(root, {'source.json': '0'*64})
            with self.assertRaises(ValueError):
                check_hashes(root, {'missing.json': hashes['source.json']})

    def test_new_province_actual_lineage_rejects_future_and_wrong_lag(self):
        dates = pd.date_range('2000-01-01', '2010-12-31')
        raw = [dict(province_code='21', date=d.strftime('%Y-%m-%d'), T2M=25., T2M_MIN=20.,
                    T2M_MAX=30., RH2M=60., PRECTOTCORR=1., ALLSKY_SFC_SW_DWN=15.) for d in dates]
        values, issue, _, traces = IssueWeather(raw).features_with_lineage('21', 2010, [4, 5, 6], 60)
        for trace in traces:
            self.assertEqual(trace['value'], values[trace['feature']])
            check_feature_lineage(trace, 2010, issue.isoformat(), rb.midnight(issue), 7)
        for key in ('observed_dates', 'normal_dates'):
            bad = deepcopy(traces[0])
            bad[key].append('2010-12-31')
            with self.assertRaises(ValueError):
                check_feature_lineage(bad, 2010, issue.isoformat(), rb.midnight(issue), 7)
        with self.assertRaises(ValueError):
            check_feature_lineage(dict(feature=rb.FEATURES[0], value=1., source_year=2010,
                                       province_code='21', source_province='21'), 2010,
                                  issue.isoformat(), rb.midnight(issue), 7)


if __name__ == '__main__':
    unittest.main()
