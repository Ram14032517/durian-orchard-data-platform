"""Synthetic evidence tests guard logic, not historical provider availability."""
from datetime import date
from pathlib import Path
import json
import sys
import unittest
import pandas as pd
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from availability_guard import check, issue_date, preflight, schedule_version
import experiment_issue_date as experiment


class AvailabilityGuardTests(unittest.TestCase):
    def record(self, role='feature'):
        return dict(role=role, availability_status='verified_available', source_version='old-sha',
            publication_date='2016-12-01T00:00:00+07:00',
            evidence=dict(reference='synthetic://test-only', source_version='old-sha',
                          publication_date='2016-12-01T00:00:00+07:00'))

    def guard(self, record, role='feature', mode='strict', version='old-sha', **kwargs):
        return check(record, role, version, '2017-01-31T00:00:00+07:00', mode, **kwargs)

    def test_verified_exact_version_available(self):
        self.assertEqual(self.guard(self.record()), [])

    def test_missing_publication_not_a_pass(self):
        r = self.record()
        r['publication_date'] = None
        with self.assertRaises(ValueError):
            self.guard(r)
        self.assertTrue(self.guard(r, mode='exploratory'))

    def test_future_publication_leakage(self):
        r = self.record()
        r['publication_date'] = '2017-02-01T00:00:00+07:00'
        r['evidence']['publication_date'] = r['publication_date']
        with self.assertRaisesRegex(ValueError, 'Publication after'):
            self.guard(r)

    def test_revised_bytes_cannot_use_old_version_evidence(self):
        with self.assertRaisesRegex(ValueError, 'Source version mismatch'):
            self.guard(self.record(), version='new-revised-sha')
        r = self.record()
        r['evidence']['source_version'] = 'different-version'
        with self.assertRaisesRegex(ValueError, 'version-specific'):
            self.guard(r)

    def test_training_and_selection_labels_use_fit_cutoff(self):
        for role in ('training_label', 'selection_label'):
            r = self.record(role)
            r['publication_date'] = '2017-02-01T00:00:00+07:00'
            with self.assertRaises(ValueError):
                self.guard(r, role)

    def test_later_reference_allowed_only_for_evaluation(self):
        r = self.record('evaluation_target')
        r['availability_status'] = 'unverified'
        r['publication_date'] = '2026-07-14T00:00:00+07:00'
        self.assertTrue(self.guard(r, 'evaluation_target'))
        with self.assertRaisesRegex(ValueError, 'Role/status'):
            self.guard(r, 'feature')

    def test_predictor_whitelist_excludes_target_area_and_production(self):
        frame = pd.DataFrame([{k: 1 for k in ['province_code', 'year_ce', *experiment.FEATURES,
            experiment.TARGET, 'bearing_rai', 'production_tonnes']}])
        safe = experiment.prediction_inputs(frame)
        self.assertEqual(set(safe), {'province_code', 'year_ce', *experiment.FEATURES})

    def test_all_four_states_and_not_applicable_boundary(self):
        for state in ('verified_unavailable', 'unverified'):
            r = self.record()
            r['availability_status'] = state
            with self.assertRaises(ValueError):
                self.guard(r)
            self.assertTrue(self.guard(r, mode='exploratory'))
        r = self.record('calendar')
        r.update(availability_status='not_applicable', publication_date=None, basis='known_by_definition')
        self.assertEqual(self.guard(r, 'calendar'), [])
        r['role'] = 'feature'
        with self.assertRaises(ValueError):
            self.guard(r)

    def test_future_observation_rejected_even_exploratory(self):
        with self.assertRaisesRegex(ValueError, 'Future observations'):
            self.guard(self.record(), mode='exploratory', observation_end='2017-02-01')

    def test_issue_rule_created_later_is_not_historically_predeclared(self):
        r = self.record('issue_rule')
        r['created_at'] = '2026-10-10T00:00:00+07:00'
        with self.assertRaisesRegex(ValueError, 'Issue rule created after'):
            self.guard(r, 'issue_rule')

    def test_fixed_issue_dates_ignore_revised_monthly_data(self):
        s = dict(kind='fixed_calendar', anchors={'22': '04-01'})
        self.assertEqual(issue_date(s, '22', 2023, 60), date(2023, 1, 31))
        with self.assertRaises(ValueError):
            issue_date(dict(kind='revised_monthly_peak', anchors=s['anchors']), '22', 2023, 60)

    def test_missing_timezone_not_guessed(self):
        r = self.record()
        r['publication_date'] = '2016-12-01'
        with self.assertRaisesRegex(ValueError, 'timezone'):
            self.guard(r)

    def test_missing_feature_lineage_cannot_silently_pass(self):
        m = json.loads(experiment.MANIFEST.read_text(encoding='utf-8'))
        del m['feature_dependencies'][experiment.FEATURES[0]]
        with self.assertRaisesRegex(ValueError, 'Every feature'):
            preflight(m, experiment.ROOT, experiment.FEATURES, experiment.PROVINCES, 'exploratory')

    def test_schedule_mutation_requires_new_version(self):
        m = json.loads(experiment.MANIFEST.read_text(encoding='utf-8'))
        m['schedule']['anchors']['22'] = '05-01'
        with self.assertRaisesRegex(ValueError, 'Source version mismatch'):
            preflight(m, experiment.ROOT, experiment.FEATURES, experiment.PROVINCES, 'exploratory')

    def test_strict_stops_before_fit_or_any_output(self):
        with patch.object(experiment, 'fit_predict', side_effect=AssertionError('must not fit')) as fit:
            with patch.object(experiment, 'output_json') as output:
                with self.assertRaises(ValueError):
                    experiment.run(mode='strict', preflight_only=False)
                fit.assert_not_called()
                output.assert_not_called()

    def test_preflight_default_never_trains(self):
        with patch.object(experiment, 'fit_predict', side_effect=AssertionError('must not fit')) as fit:
            with patch.object(experiment, 'output_json'):
                result = experiment.run()
                self.assertEqual(result['mode'], 'exploratory')
                self.assertFalse(result['pit_certified'])
                manifest = json.loads(experiment.MANIFEST.read_text(encoding='utf-8'))
                self.assertEqual(len(result['checks']), 120 * (5 + 2 * sum(
                    len(refs) for refs in manifest['feature_dependencies'].values())))
                fit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
