"""Synthetic preparation tests only: no estimator is trained."""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
import experiment_rebaseline as rb
from experiment_issue_date import IssueWeather, WINDOWS, PREDICTORS
from availability_guard import check_feature_lineage


class RebaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(rb.MANIFEST.read_text(encoding='utf-8'))
        cls.panel = pd.DataFrame([dict(province_code=p, year_ce=y,
            previous_yield_kg_rai=100., **{rb.TARGET: 100.}) for p in rb.PROVINCES for y in rb.YEARS])
        cls.annual = pd.DataFrame([dict(province_code=p, year_ce=y, **{rb.TARGET: 100.})
                                  for p in rb.PROVINCES for y in range(2009, 2026)])
        days = pd.date_range('2000-01-01', '2011-12-31')
        cls.raw = [dict(province_code='22', date=d.strftime('%Y-%m-%d'), T2M=25.,
                       T2M_MIN=20., T2M_MAX=30., RH2M=60., PRECTOTCORR=float(d.day),
                       ALLSKY_SFC_SW_DWN=15.) for d in days]

    def test_complete_panel_and_fail_fast_missing_year_province_lag(self):
        panel = self.__class__.panel.copy()
        rb.validate_panel(panel)
        for incomplete in (panel.iloc[1:], panel[panel.year_ce.ne(2010)],
                           panel[panel.province_code.ne('22')], panel.drop(columns=['previous_yield_kg_rai']),
                           pd.concat([panel, panel.iloc[:1]])):
            with self.assertRaises(ValueError):
                rb.validate_panel(incomplete)
        panel.loc[0, 'previous_yield_kg_rai'] = np.nan
        with self.assertRaises(ValueError):
            rb.validate_panel(panel)

    def test_locked_calendar_and_dependencies_cannot_be_reduced(self):
        rb.validate_manifest(self.manifest)
        for mutate in (lambda m: m['schedule']['anchors'].update({'22': '05-01'}),
                       lambda m: m['records'].pop('selection_labels'),
                       lambda m: m['feature_dependencies'].pop(rb.FEATURES[1]),
                       lambda m: m['feature_dependencies'][rb.FEATURES[1]].pop(0)):
            manifest = deepcopy(self.manifest)
            mutate(manifest)
            with self.assertRaises(ValueError):
                rb.validate_manifest(manifest)

    def test_same_legacy_interface_and_values(self):
        weather = IssueWeather(self.raw)
        old = weather.features('22', 2010, [4, 5, 6], 60)
        traced = weather.features_with_lineage('22', 2010, [4, 5, 6], 60)
        self.assertEqual(old[:3], traced[:3])
        self.assertEqual(old[3], [{k: t[k] for k in ('feature', 'observed_fraction', 'climatology_fraction')}
                                  for t in traced[3]])

    def test_lineage_hashes_actual_consumed_observations_and_normal_inputs(self):
        weather = IssueWeather(self.raw)
        values, issue, _, traces = weather.features_with_lineage('22', 2010, [4, 5, 6], 60)
        rain = {r['date']: r['PRECTOTCORR'] for r in self.raw}
        for t in traces:
            check_feature_lineage(t, 2010, issue.isoformat(), rb.midnight(issue), 7)
            self.assertEqual(values[t['feature']], t['value'])
            if t['source_field'] == 'rain':
                observed = [(d, rain[d]) for d in t['observed_dates']]
                self.assertEqual(t['observed_values_sha256'], hashlib.sha256(json.dumps(observed).encode()).hexdigest())
                normals = [(d, rain[d]) for d in t['normal_dates']]
                self.assertEqual(t['normal_values_sha256'], hashlib.sha256(json.dumps(normals).encode()).hexdigest())
                self.assertTrue(all(date.fromisoformat(d).year < 2010 for d, _ in normals))

    def test_traced_rain_value_recomputes_from_consumed_values(self):
        from analyze_harvest_backcast import month_days
        weather = IssueWeather(self.raw)
        features, _, available, traces = weather.features_with_lineage('22', 2010, [4, 5, 6], 60)
        trace = traces[0]
        raw = {date.fromisoformat(r['date']): r['PRECTOTCORR'] for r in self.raw}
        sums = []
        for harvest in [d for m in (4, 5, 6) for d in month_days(2010, m)]:
            values = []
            for delta in range(-90, 0):
                d = date.fromordinal(harvest.toordinal() - 140 + delta)
                values.append(raw[d] if d <= available else trace['normal_cell_values'][d.strftime('%m-%d')])
            sums.append(sum(values))
        self.assertAlmostEqual(features[trace['feature']], float(np.mean(sums)))

    def test_missing_normal_coverage_fails_without_filling(self):
        raw = [r for r in self.raw if not r['date'].endswith('-05-01')]
        with self.assertRaises((ValueError, KeyError)):
            IssueWeather(raw).features_with_lineage('22', 2010, [4, 5, 6], 60)

    def test_future_weather_changes_neither_features_nor_lineage(self):
        weather = IssueWeather(self.raw)
        before = weather.features_with_lineage('22', 2010, [4, 5, 6], 60)
        raw = deepcopy(self.raw)
        for row in raw:
            if date.fromisoformat(row['date']) > before[2]:
                row.update(PRECTOTCORR=999., T2M=35., T2M_MIN=30., T2M_MAX=40.,
                           RH2M=20., ALLSKY_SFC_SW_DWN=25.)
        self.assertEqual(before, IssueWeather(raw).features_with_lineage('22', 2010, [4, 5, 6], 60))

    def test_future_observations_and_climatology_fail_even_exploratory(self):
        _, issue, _, traces = IssueWeather(self.raw).features_with_lineage('22', 2010, [4, 5, 6], 60)
        for key in ('observed_dates', 'normal_dates'):
            item = deepcopy(traces[0])
            item[key] = ['2011-01-01']
            with self.assertRaises(ValueError):
                check_feature_lineage(item, 2010, issue.isoformat(), rb.midnight(issue), 7)
        with self.assertRaises(ValueError):
            check_feature_lineage(traces[0], 2010, issue.isoformat(), '2000-01-01T00:00:00+07:00', 7)

    def test_missing_lineage_and_invalid_lag_fail(self):
        _, issue, _, traces = IssueWeather(self.raw).features_with_lineage('22', 2010, [4, 5, 6], 60)
        t = deepcopy(traces[0])
        t['normal_dates'] = []
        with self.assertRaises(ValueError):
            check_feature_lineage(t, 2010, issue.isoformat(), rb.midnight(issue), 7)
        lag = dict(feature=rb.FEATURES[0], value=100., source_year=2010, source_province='22', province_code='22')
        with self.assertRaises(ValueError):
            check_feature_lineage(lag, 2010, issue.isoformat(), rb.midnight(issue), 7)

    def test_builder_rejects_targets_and_missing_features(self):
        weather = IssueWeather(self.raw)
        with self.assertRaises(ValueError):
            rb.build_inputs(pd.DataFrame([dict(province_code='22', year_ce=2010, **{rb.TARGET: 100.})]), weather, self.manifest)
        with patch.object(weather, 'features_with_lineage', return_value=({}, date(2010, 1, 31), date(2010, 1, 24), [])):
            with self.assertRaises(ValueError):
                rb.build_inputs(pd.DataFrame([dict(province_code='22', year_ce=2010)]), weather, self.manifest)

    def synthetic_builder(self, keys, weather, manifest):
        rows, traces = [], []
        for row in keys.to_dict('records'):
            year, p = row['year_ce'], row['province_code']
            issue = rb.issue_date(manifest['schedule'], p, year, 60)
            rows.append(dict(**row, **{f: 1. for f in rb.FEATURES[1:]}))
            for f in rb.FEATURES[1:]:
                traces.append(dict(**row, feature=f, value=1., issue_date=issue.isoformat(),
                    observed_dates=[f'{year - 1}-12-01'], normal_dates=[f'{year - 1}-01-01'],
                    observed_values_sha256='a' * 64, normal_values_sha256='b' * 64,
                    cohort_days=1, window_days=2, observed_cells=1, climatology_cells=1,
                    observed_fraction=.5, climatology_fraction=.5))
        return pd.DataFrame(rows), traces

    def prepared(self, panel=None, annual=None):
        with patch.object(rb, 'build_inputs', side_effect=self.synthetic_builder):
            return rb.prepare_folds(self.__class__.panel.copy() if panel is None else panel,
                self.annual.copy() if annual is None else annual, None, self.manifest)

    def test_all_outer_inner_folds_and_label_cutoffs_are_audited(self):
        result = self.prepared()
        self.assertEqual(len(result['folds']), 36)
        self.assertEqual(len(result['inputs']), 80)
        self.assertFalse(result['pit_certified'])
        for fold in result['folds']:
            self.assertLess(fold['training_labels'].year_ce.max(), fold['fold_year'])
            self.assertEqual(len(fold['forecast_predictors']), 5)
            self.assertEqual(set(fold['forecast_predictors']), {'province_code', 'year_ce', *rb.FEATURES})
            self.assertEqual(fold['fit_cutoff'], min(fold['issue_dates'].values()))
        checks = pd.DataFrame(result['availability'])
        self.assertEqual(set(checks.role), {'issue_rule', 'calendar', 'feature', 'training_label', 'evaluation_target', 'selection_label'})
        for f in result['folds']:
            part = checks[(checks.outer_year == f['outer_year']) & (checks.fold_year == f['fold_year'])]
            self.assertTrue(part[part.role.eq('training_label')].use_cutoff.eq(f['fit_cutoff']).all())
            if f['stage'] == 'inner':
                selection = part[part.role.eq('selection_label')]
                self.assertEqual(len(selection), 5)
                self.assertTrue(selection.use_cutoff.eq(f['selection_cutoff']).all())

    def test_missing_lag_source_and_changed_lag_fail(self):
        with self.assertRaises(ValueError):
            self.prepared(annual=self.annual.iloc[1:])
        panel = self.__class__.panel.copy()
        panel.loc[0, 'previous_yield_kg_rai'] = 999.
        with self.assertRaises(ValueError):
            self.prepared(panel=panel)

    def test_fold_rejects_consumed_future_lineage(self):
        def bad_builder(*args):
            frame, traces = self.synthetic_builder(*args)
            traces[0]['observed_dates'] = ['2026-01-01']
            return frame, traces
        with patch.object(rb, 'build_inputs', side_effect=bad_builder):
            with self.assertRaisesRegex(ValueError, 'cutoff'):
                rb.prepare_folds(self.__class__.panel.copy(), self.annual.copy(), None, self.manifest)

    def test_missing_vintage_is_a_warning_not_pit_certification(self):
        prepared = self.prepared()
        self.assertFalse(prepared['pit_certified'])
        external = [c for c in prepared['availability'] if c['dependency'] in
                    ('training_labels', 'selection_labels', 'annual_lag', 'power_observed', 'power_normals')]
        self.assertTrue(external)
        self.assertTrue(all(c['availability_status'] == 'unverified' and c['warnings'] for c in external))

    def test_outer_targets_do_not_enter_features_or_training_labels_of_that_fold(self):
        before = self.prepared()
        for outer in (2017, 2025):
            panel, annual = self.__class__.panel.copy(), self.annual.copy()
            panel.loc[panel.year_ce.eq(outer), rb.TARGET] = 999999.
            annual.loc[annual.year_ce.eq(outer), rb.TARGET] = 999999.
            # A later fold legitimately sees this as its lag; the current fold must not.
            panel.loc[panel.year_ce.eq(outer + 1), 'previous_yield_kg_rai'] = 999999.
            after = self.prepared(panel, annual)
            for a, b in zip(before['folds'], after['folds']):
                if a['outer_year'] == outer:
                    for key in ('train_predictors', 'forecast_predictors', 'training_labels'):
                        pd.testing.assert_frame_equal(a[key], b[key])
            selection_before = [c for c in before['availability'] if c['role'] == 'selection_label' and c['outer_year'] == outer]
            self.assertEqual(selection_before, [c for c in after['availability'] if c['role'] == 'selection_label' and c['outer_year'] == outer])

    def test_artifacts_are_exclusive_isolated_and_never_contain_targets_in_predictors(self):
        prepared = self.prepared()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'rebaseline_exploratory'
            legacy = Path(temp) / 'issue_date_results.json'
            legacy.write_text('unchanged')
            run = rb.write_preparation(prepared, {'training_performed': False}, self.manifest, 'synthetic-only', root)
            self.assertEqual(legacy.read_text(), 'unchanged')
            self.assertNotIn(rb.TARGET, pd.read_csv(run / 'predictors.csv').columns)
            original = (run / 'config.json').read_bytes()
            with self.assertRaises(ValueError):
                rb.write_preparation(prepared, {}, self.manifest, 'synthetic-only', root)
            self.assertEqual((run / 'config.json').read_bytes(), original)
            for bad in ('../production', 'a/b', '..', 'a.b'):
                with self.assertRaises(ValueError):
                    rb.write_preparation(prepared, {}, self.manifest, bad, root)
            with self.assertRaises(ValueError):
                rb.write_preparation(prepared, {}, self.manifest, 'run', Path(temp))

    def test_configuration_hashes_dependencies_and_candidates(self):
        config = rb.configuration(rb.MANIFEST, self.manifest)
        self.assertEqual(config['seed'], 42)
        self.assertEqual(config['lead_days'], 60)
        self.assertTrue(config['preparation_only'])
        self.assertFalse(config['training_performed'])
        self.assertEqual(config['data_sha256'], rb.hashes())
        self.assertEqual(config['manifest_sha256'], rb.digest(rb.MANIFEST))
        self.assertEqual(set(config['dependencies']), {'numpy', 'pandas', 'scikit-learn', 'catboost'})
        self.assertEqual({c['kind'] for c in rb.candidates()}, {'previous_year', 'ridge', 'catboost'})
        self.assertEqual(len(rb.candidates()), 6)

    def test_synthetic_report_has_full_keys_and_paired_wins(self):
        predictions = pd.DataFrame([dict(model=m, province_code=p, year_ce=y, actual_kg_rai=100.,
            predicted_kg_rai={'last_year': 90., 'ridge': 95., 'catboost': 85.}[m])
            for m in ('last_year', 'ridge', 'catboost') for p in rb.PROVINCES for y in rb.OUTER_YEARS])
        result = rb.summarize_predictions(predictions)
        self.assertEqual(len(result['paired_errors']), 135)
        self.assertEqual(len(result['by_year']), 27)
        self.assertEqual(len(result['by_province']), 15)
        self.assertEqual(result['wins'].set_index('model').loc['ridge', 'wins'], 45)
        self.assertEqual(result['wins'].set_index('model').loc['catboost', 'losses'], 45)
        self.assertEqual(result['wins'].set_index('model').loc['ridge', 'year_wins'], 9)
        self.assertEqual(result['wins'].set_index('model').loc['ridge', 'province_wins'], 5)
        for bad in (predictions.iloc[1:], pd.concat([predictions, predictions.iloc[:1]])):
            with self.assertRaises(ValueError):
                rb.summarize_predictions(bad)
        predictions.loc[0, 'actual_kg_rai'] = 99.
        with self.assertRaises(ValueError):
            rb.summarize_predictions(predictions)

    def test_training_selects_within_family_and_never_passes_outer_targets_to_fitter(self):
        prepared = self.prepared()
        config = rb.configuration(rb.MANIFEST, self.manifest)
        calls = []
        def fitter(train, heldout, provinces, candidate):
            self.assertEqual(set(heldout), {'province_code', 'year_ce', *rb.FEATURES})
            self.assertLess(train.year_ce.max(), heldout.year_ce.min())
            self.assertEqual(set(train), {'province_code', 'year_ce', *rb.FEATURES, rb.TARGET})
            calls.append((int(heldout.year_ce.min()), candidate['kind']))
            error = (0. if candidate['kind'] == 'previous_year' else
                     {1.: 5., 10.: 1., 100.: 3.}[candidate['parameter']] if candidate['kind'] == 'ridge' else
                     {2: 4., 3: 2.}[candidate['parameter']['depth']])
            return np.full(5, 100. + error)
        result = rb.train_predictions(prepared, config, fitter=fitter)
        self.assertEqual(len(result['predictions']), 135)
        self.assertEqual(len(result['tuning']), 162)
        self.assertEqual(len(result['choices']), 27)
        self.assertEqual(len(calls), 69)
        choices = result['choices']
        self.assertTrue(choices[choices.model.eq('ridge')].candidate.eq(2).all())
        self.assertTrue(choices[choices.model.eq('catboost')].candidate.eq(5).all())
        changed = deepcopy(prepared)
        for fold in changed['folds']:
            if fold['outer_year'] == fold['fold_year']:
                fold['evaluation_reference'][rb.TARGET] = 999999.
        again = rb.train_predictions(changed, config, fitter=fitter)
        pd.testing.assert_frame_equal(result['choices'], again['choices'])
        np.testing.assert_array_equal(result['predictions'].predicted_kg_rai, again['predictions'].predicted_kg_rai)

    def test_training_refuses_missing_context_or_protocol_change_before_fitting(self):
        prepared = self.prepared()
        config = rb.configuration(rb.MANIFEST, self.manifest)
        def forbidden(*args):
            raise AssertionError('must fail before fitting')
        incomplete = dict(prepared, folds=prepared['folds'][:-1])
        with self.assertRaises(ValueError):
            rb.train_predictions(incomplete, config, forbidden)
        for key, value in (('mode', 'strict'), ('lead_days', 0), ('seed', 1), ('features', [])):
            wrong = dict(config, **{key: value})
            with self.assertRaises(ValueError):
                rb.train_predictions(prepared, wrong, forbidden)

    def test_training_refuses_dropped_labels_or_target_in_forecast_before_fitting(self):
        config = rb.configuration(rb.MANIFEST, self.manifest)
        for problem in ('dropped_label', 'target_in_predictors'):
            prepared = self.prepared()
            first = prepared['folds'][0]
            if problem == 'dropped_label':
                first['training_labels'] = first['training_labels'].iloc[1:]
            else:
                first['forecast_predictors'][rb.TARGET] = 999.
            with self.assertRaises(ValueError):
                rb.train_predictions(prepared, config, lambda *args: (_ for _ in ()).throw(AssertionError('must not fit')))


if __name__ == '__main__':
    unittest.main()
