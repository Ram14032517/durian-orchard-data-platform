"""Synthetic ablation boundary tests; no estimator training."""
from copy import deepcopy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
import experiment_weather_ablation as wa
import test_rebaseline as fixtures


class WeatherAblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RebaselineTests.setUpClass()
        fixture = fixtures.RebaselineTests()
        cls.prepared = fixture.prepared()
        cls.manifest = fixture.manifest
        cls.config = dict(protocol=wa.protocol(), protocol_sha256=wa.rb.digest_value(wa.protocol()))

    def fake(self, train, heldout, provinces, candidate):
        expected = set(wa.KEYS + candidate['features'])
        self.assertEqual(set(train), expected | {wa.rb.TARGET})
        self.assertEqual(set(heldout), expected)
        self.assertLess(train.year_ce.max(), heldout.year_ce.min())
        arm = candidate['group']
        if arm == wa.ARMS[0]:
            return heldout[wa.LAG].to_numpy(float)
        depth = candidate['parameter']['depth']
        error = (1 if depth == 2 else 3) if arm == wa.ARMS[1] else (3 if depth == 2 else 1)
        return np.full(5, float(train[wa.rb.TARGET].mean()) + error)

    def train(self, prepared=None, config=None, manifest=None, fitter=None):
        with redirect_stdout(io.StringIO()):
            return wa.train_predictions(prepared or self.prepared, config or self.config,
                manifest or self.manifest, fitter or self.fake)

    def test_actual_design_and_weather_projection_isolation(self):
        inputs = self.prepared['inputs']
        changed = inputs.copy()
        changed[wa.rb.FEATURES[1:]] = 999.
        for candidate in wa.candidates():
            before, after = wa.project(inputs, candidate), wa.project(changed, candidate)
            if candidate['group'] != wa.ARMS[2]:
                pd.testing.assert_frame_equal(before, after)
            else:
                self.assertFalse(before.equals(after))
            if candidate['kind'] == 'catboost':
                self.assertEqual(wa.design(before, wa.rb.PROVINCES, candidate['features']).shape, (80,
                    7 if candidate['group'] == wa.ARMS[1] else 14))

    def test_independent_selection_boundary_cache_and_target_poisoning(self):
        calls = []
        def spy(*args):
            calls.append((args[-1]['group'], args[-1]['parameter']))
            return self.fake(*args)
        with patch.object(Path, 'read_text', side_effect=AssertionError('Old artifacts cannot enter fit/selection')):
            result = self.train(fitter=spy)
        self.assertEqual(len(calls), 58)
        self.assertEqual(len(result['predictions']), 135)
        self.assertEqual(len(result['tuning']), 135)
        self.assertEqual(len(result['choices']), 27)
        choices = result['choices']
        self.assertTrue(all(json.loads(p)['depth'] == 2 for p in choices[choices.arm.eq(wa.ARMS[1])].parameter))
        self.assertTrue(all(json.loads(p)['depth'] == 3 for p in choices[choices.arm.eq(wa.ARMS[2])].parameter))
        changed = deepcopy(self.prepared)
        for fold in changed['folds']:
            if fold['stage'] == 'outer':
                fold['evaluation_reference'][wa.rb.TARGET] = 999999.
        poisoned = self.train(changed)
        pd.testing.assert_frame_equal(result['choices'], poisoned['choices'])
        np.testing.assert_array_equal(result['predictions'].predicted_kg_rai, poisoned['predictions'].predicted_kg_rai)
        self.assertFalse(result['overall'].equals(poisoned['overall']))

    def test_weather_poisoning_cannot_change_no_weather_predictions_or_choices(self):
        before = self.train()
        changed = deepcopy(self.prepared)
        changed['inputs'][wa.rb.FEATURES[1:]] = 9.
        for t in changed['lineage']:
            if t['feature'] != wa.LAG:
                t['value'] = 9.
        for f in changed['folds']:
            for key in ('train_predictors', 'forecast_predictors'):
                f[key][wa.rb.FEATURES[1:]] = 9.
        def sensitive(train, heldout, provinces, candidate):
            values = self.fake(train, heldout, provinces, candidate)
            return values + heldout[wa.rb.FEATURES[1]].to_numpy(float) if candidate['group'] == wa.ARMS[2] else values
        a, b = self.train(fitter=sensitive), self.train(changed, fitter=sensitive)
        for table, arm_column in [('choices', 'arm'), ('predictions', 'model')]:
            pd.testing.assert_frame_equal(a[table][a[table][arm_column].eq(wa.ARMS[1])],
                                          b[table][b[table][arm_column].eq(wa.ARMS[1])])
        self.assertFalse(a['predictions'][a['predictions'].model.eq(wa.ARMS[2])].equals(
                         b['predictions'][b['predictions'].model.eq(wa.ARMS[2])]))
        self.assertEqual(len(before['predictions']), 135)

    def test_derived_weather_features_and_disguised_lag_lineage_are_rejected(self):
        for feature in [wa.rb.FEATURES[-1], 'enso_lag', 'rain_x_lag', wa.rb.TARGET]:
            candidate = deepcopy(wa.candidates()[1])
            candidate['features'].append(feature)
            with self.assertRaises(ValueError):
                wa.project(self.prepared['inputs'], candidate)
        changed = deepcopy(self.prepared)
        next(t for t in changed['lineage'] if t['feature'] == wa.LAG)['source_columns'] = ['RH2M']
        with self.assertRaises(ValueError):
            self.train(changed, fitter=lambda *args: self.fail('must fail before fit'))
        manifest = deepcopy(self.manifest)
        manifest['feature_dependencies'][wa.LAG].append('power_normals')
        with self.assertRaises(ValueError):
            self.train(manifest=manifest, fitter=lambda *args: self.fail('must fail before fit'))

    def test_cutoff_and_consumed_future_dates_fail_before_fit(self):
        for field in ('observed_dates', 'normal_dates'):
            changed = deepcopy(self.prepared)
            changed['lineage'][0][field] = ['2026-01-01']
            with self.assertRaises(ValueError):
                self.train(changed, fitter=lambda *args: self.fail('must fail before fit'))
        for key in ('fit_cutoff', 'selection_cutoff'):
            changed = deepcopy(self.prepared)
            changed['folds'][0][key] = '2030-01-01T00:00:00+07:00'
            with self.assertRaises(ValueError):
                self.train(changed, fitter=lambda *args: self.fail('must fail before fit'))

    def test_availability_and_input_completeness_fail_before_fit(self):
        for section in ('availability', 'lineage', 'folds'):
            changed = deepcopy(self.prepared)
            changed[section] = changed[section][1:]
            with self.assertRaises(ValueError):
                self.train(changed, fitter=lambda *args: self.fail('must fail before fit'))
        for frame in ('inputs', 'train_predictors', 'forecast_predictors', 'training_labels', 'evaluation_reference'):
            changed = deepcopy(self.prepared)
            parent = changed if frame == 'inputs' else changed['folds'][0]
            parent[frame] = parent[frame].iloc[1:]
            with self.assertRaises(ValueError):
                self.train(changed, fitter=lambda *args: self.fail('must fail before fit'))
        changed = deepcopy(self.prepared)
        changed['folds'][0]['forecast_predictors'][wa.rb.TARGET] = 123.
        with self.assertRaises(ValueError):
            self.train(changed, fitter=lambda *args: self.fail('must fail before fit'))
        changed = deepcopy(self.prepared)
        changed['inputs'] = pd.concat([changed['inputs'], changed['inputs'].iloc[:1]])
        with self.assertRaises(ValueError):
            self.train(changed, fitter=lambda *args: self.fail('must fail before fit'))

    def test_protocol_changes_rejected_before_fit(self):
        for key, value in [('seed', 7), ('lead_days', 0), ('inner_years', 2),
                           ('anchors', {'22': '05-01'}), ('outer_years', [2025])]:
            config = deepcopy(self.config)
            config['protocol'][key] = value
            config['protocol_sha256'] = wa.rb.digest_value(config['protocol'])
            with self.assertRaises(ValueError):
                self.train(config=config, fitter=lambda *args: self.fail('must fail before fit'))

    def test_cache_key_separates_arms_parameters_cutoffs_sources_and_protocol(self):
        f, c = self.prepared['folds'][0], wa.candidates()[1]
        train = wa.project(f['train_predictors'], c).merge(f['training_labels'], on=wa.KEYS)
        forecast = wa.project(f['forecast_predictors'], c)
        base = wa.cache_key(self.config, f, c, train, forecast)
        self.assertEqual(base, wa.cache_key(self.config, deepcopy(f), deepcopy(c), train.copy(), forecast.copy()))
        modified_candidate = deepcopy(c)
        modified_candidate['parameter']['depth'] = 3
        modified_fold = deepcopy(f)
        modified_fold['fit_cutoff'] = '2026-01-01T00:00:00+07:00'
        changed = train.copy()
        changed.loc[changed.index[0], wa.LAG] += 1.
        modified_config = deepcopy(self.config)
        modified_config['protocol_sha256'] = 'a'*64
        keys = [wa.cache_key(self.config, f, wa.candidates()[3], train, forecast),
                wa.cache_key(self.config, f, modified_candidate, train, forecast),
                wa.cache_key(self.config, modified_fold, c, train, forecast),
                wa.cache_key(self.config, f, c, changed, forecast),
                wa.cache_key(modified_config, f, c, train, forecast)]
        self.assertTrue(all(k != base for k in keys))

    def test_ties_choose_depth_two(self):
        result = self.train(fitter=lambda train, heldout, provinces, candidate: np.full(5, 100.))
        self.assertTrue(all(json.loads(p)['depth'] == 2 for p in
                            result['choices'][result['choices'].arm.ne(wa.ARMS[0])].parameter))

    def test_artifacts_exclusive_projection_and_no_weather_consumed_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'weather_ablation_exploratory'
            run = wa.write_preparation(self.prepared, self.config, self.manifest, 'synthetic', root)
            content = (run / 'config.json').read_bytes()
            with self.assertRaises(ValueError):
                wa.write_preparation(self.prepared, self.config, self.manifest, 'synthetic', root)
            self.assertEqual(content, (run / 'config.json').read_bytes())
            for name in ('../escape', 'a/b', '..', 'a.b'):
                with self.assertRaises(ValueError):
                    wa.write_preparation(self.prepared, self.config, self.manifest, name, root)
            with self.assertRaises(ValueError):
                wa.write_preparation(self.prepared, self.config, self.manifest, 'new', Path(temp))
            frame = pd.read_csv(run / (wa.ARMS[1] + '_predictors.csv'))
            self.assertEqual(set(frame), set(wa.KEYS + [wa.LAG]))
            deps = json.loads((run / 'consumed_dependencies.json').read_text())
            self.assertEqual(deps[wa.ARMS[1]], {wa.LAG: ['annual_lag']})
            checks = json.loads((run / 'availability.json').read_text())
            self.assertTrue(all(c['dependency'] not in ('power_normals', 'power_observed', 'issue_rule_feature')
                                for c in checks[wa.ARMS[1]]))

    def test_metric_weather_gain_and_row_completeness(self):
        frame = pd.DataFrame([dict(model=m, province_code=p, year_ce=y, issue_date='fixed',
            actual_kg_rai=100., predicted_kg_rai={'last_year': 104., 'catboost_no_weather': 110.,
            'catboost_with_weather': 105.}[m]) for m in wa.ARMS for p in wa.rb.PROVINCES for y in wa.rb.OUTER_YEARS])
        tables = wa.summarize(frame)
        gain = tables['weather_contribution'].iloc[0]
        self.assertEqual(gain.mean_gain, 5.)
        self.assertEqual(gain.relative_mae_reduction_pct, 50.)
        self.assertEqual(gain.wins, 45)
        self.assertEqual(gain.rmse_reduction, 5.)
        self.assertEqual(len(tables['by_year']), 27)
        self.assertEqual(len(tables['by_province']), 15)
        for bad in (frame.iloc[1:], pd.concat([frame, frame.iloc[:1]])):
            with self.assertRaises(ValueError):
                wa.summarize(bad)

    def test_default_cli_does_not_prepare_or_fit(self):
        result = subprocess.run([sys.executable, str(Path(wa.__file__))], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--prepare', result.stdout)
        self.assertNotIn('completed 2017', result.stdout)

    def test_protected_hash_changes_are_rejected(self):
        config = dict(data_sha256=wa.rb.hashes(), manifest_sha256=wa.rb.digest(wa.rb.MANIFEST),
            protected_sha256={'tools/durian_model/availability_guard.py': '0'*64})
        with self.assertRaises(ValueError):
            wa.assert_unchanged(config)

    def test_preparation_never_trains(self):
        base = dict(code_sha256={}, data_sha256=wa.rb.hashes(), manifest_sha256=wa.rb.digest(wa.rb.MANIFEST))
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            with patch.object(wa.rb, 'prepare', return_value=(self.prepared, base, self.manifest)), \
                 patch.object(wa, 'compare_reference'), patch.object(wa, 'protected_hashes', return_value={}), \
                 patch.object(wa, 'write_preparation', return_value=Path(temp)), \
                 patch.object(wa, 'train_predictions', side_effect=AssertionError('Preparation must not train')):
                wa.run(training=False)
            status = json.loads((Path(temp) / 'run_status.json').read_text())
            self.assertFalse(status['training_performed'])


if __name__ == '__main__':
    unittest.main()
