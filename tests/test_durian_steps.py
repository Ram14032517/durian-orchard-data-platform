"""Teaching pipeline: train-only scaling, safe schema and chronological inference."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
from common import FEATURES, PROVINCES, TARGET, design, feature_names, fit_bundle, infer, load_json, load_panel
from common import begin_step
from step5_evaluate_result import paired_year_bootstrap
from build_report import report_text, report_pages


class DurianStepsTests(unittest.TestCase):
    def test_rerun_invalidates_downstream_and_requires_predecessor(self):
        with patch('common.check_snapshot'), patch('common.load_json') as read, patch('common.save_json') as write:
            read.return_value = {'completed_steps': list(range(7))}
            begin_step(2)
            write.assert_called_once_with('workflow_state.json', {'completed_steps': [0, 1]})
            read.return_value = {'completed_steps': [0]}
            with self.assertRaises(ValueError):
                begin_step(3)

    def setUp(self):
        self.train = pd.DataFrame([
            dict(province_code=code, year_ce=year, **{TARGET: 700 + year - 2010},
                 **{f: 1.0 + year - 2010 for f in FEATURES})
            for code in PROVINCES for year in range(2010, 2015)])
        self.bundle = fit_bundle(self.train, 140, 10, {p: [5, 6, 7] for p in PROVINCES})
        self.test = self.train.iloc[:5][['province_code', 'year_ce', *FEATURES]].copy()
        self.test['province_code'] = PROVINCES
        self.test['year_ce'] = 2015

    def test_scaling_learns_training_only_and_matches_sklearn(self):
        from sklearn.linear_model import Ridge
        x = design(self.train, PROVINCES, FEATURES)
        params = self.bundle['parameters']
        np.testing.assert_allclose(params['mean'], x.mean(axis=0))
        xs = (x - params['mean']) / params['scale']
        reference = Ridge(alpha=10).fit(xs, self.train[TARGET])
        xt = (design(self.test, PROVINCES, FEATURES) - params['mean']) / params['scale']
        np.testing.assert_allclose(infer(self.bundle, self.test).predicted_kg_rai,
                                   np.maximum(0, reference.predict(xt)), atol=1e-8)

    def test_target_and_unknown_columns_are_rejected(self):
        for field in [TARGET, 'actual_kg_rai', 'production_tonnes', 'planted_rai']:
            with self.assertRaises(ValueError):
                infer(self.bundle, self.test.assign(**{field: 999}))

    def test_invalid_missing_duplicate_or_nonfuture_inputs_fail(self):
        variants = [self.test.drop(columns=FEATURES[0]), self.test.assign(year_ce=2014),
                    self.test.assign(year_ce=2015.5), self.test.assign(province_code='99'),
                    self.test.assign(previous_yield_kg_rai=np.nan),
                    self.test.assign(previous_yield_kg_rai=-1),
                    self.test.assign(bearing_rai=0), pd.concat([self.test, self.test])]
        for frame in variants:
            with self.subTest(columns=list(frame)):
                with self.assertRaises(ValueError):
                    infer(self.bundle, frame)

    def test_bearing_area_conversion_and_schema_order(self):
        out = infer(self.bundle, self.test.assign(bearing_rai=2000))
        np.testing.assert_allclose(out.predicted_tonnes_conditional, out.predicted_kg_rai * 2)
        reordered = dict(self.bundle, feature_names=list(reversed(feature_names())))
        with self.assertRaises(ValueError):
            infer(reordered, self.test)

    def test_real_panel_formula_and_size(self):
        panel = load_panel()
        self.assertEqual(len(panel), 80)
        np.testing.assert_allclose(panel[TARGET], panel.production_tonnes * 1000 / panel.bearing_rai)

    def test_saved_models_preserve_fold_boundaries(self):
        path = Path(__file__).resolve().parents[1] / 'research_data/five_province_history/training/ridge_vpd_models.json'
        if not path.exists():
            self.skipTest('Run steps 0-3 first for saved-model checks')
        for test_year, bundle in load_json('models.json').items():
            self.assertEqual(bundle['train_end'], int(test_year) - 1)
            self.assertEqual(bundle['training_rows'], 5 * (int(test_year) - 2010))
            self.assertNotIn(TARGET, bundle['features'])
            self.assertNotIn('bearing_rai', bundle['features'])


class ReportTypographyTests(unittest.TestCase):
    def test_mixed_text_preserves_thai_marks_and_escapes_markup(self):
        rendered = report_text('ขั้นที่ 5 Ridge & VPD\n<100')
        self.assertIn('ขั้นที่', rendered)
        self.assertIn('<font name="English">', rendered)
        self.assertIn('>Ridge</font>', rendered)
        self.assertIn('>&amp;</font>', rendered)
        self.assertIn('<br/><font name="English">&lt;100', rendered)
        self.assertNotIn('<100', rendered)
        self.assertIn('EnglishBold', report_text('MAE', bold=True))
        self.assertEqual(report_text(''), '')
        self.assertEqual(report_text('ทุเรียน'), '<font name="Thai">ทุเรียน</font>')
        self.assertIn('<font name="Thai">(วัน)</font>', report_text('อายุ (วัน)'))
        self.assertIn('<font name="Thai">(กก./ไร่)</font>', report_text('MAE (กก./ไร่)'))

    def test_report_order_conclusions_and_reference_provenance(self):
        pages = dict(report_pages())
        comparison = next(content for kind, content in pages['ขั้น 5: ประเมินผลย้อนหลัง'] if kind == 'table')
        values = [float(row[1]) for row in comparison[1:]]
        self.assertEqual(values, sorted(values))
        names = [row[0] for row in comparison[1:]]
        self.assertLess(names.index('previous_year'), names.index('stage_svr_combined'))
        discussion = ' '.join(str(content) for _, content in pages['อภิปรายและข้อจำกัด'])
        self.assertIn('ยังไม่มีหลักฐานชัดว่าการเพิ่ม VPD', discussion)
        self.assertNotIn('ผลสนับสนุนให้ใช้ Ridge + VPD', discussion)
        uncertainty = ' '.join(str(content) for _, content in pages['ความไม่แน่นอนของผลเปรียบเทียบ'])
        self.assertIn('ไม่มีหลักฐานลงวันที่', uncertainty)
        self.assertNotIn('กำหนดทั้งสองขนาดก่อนอ่านผล', uncertainty)
        references = pages['แหล่งอ้างอิง']
        entries = [pair for kind, pair in references if kind == 'reference']
        self.assertEqual(len(entries), 6)
        self.assertTrue(all(url.startswith('https://') for label, url in entries))
        self.assertIn('9 ตุลาคม 2569', ' '.join(str(content) for _, content in references))


class PairedYearBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            dict(year_ce=year, province_code=province, actual_kg_rai=100,
                 predicted_kg_rai=102, baseline=104)
            for year in range(2017, 2026) for province in ('22', '33')])

    def test_constant_gain_and_identical_predictions(self):
        result, yearly = paired_year_bootstrap(self.frame, 'baseline', resamples=200)
        self.assertEqual(result['n_years'], 9)
        self.assertEqual(len(yearly), 9)
        self.assertEqual(result['mae_gain_kg_rai'], 2)
        self.assertEqual(result['gain_percentile_95_kg_rai'], [2, 2])
        self.assertEqual(result['reduction_percentile_95_pct'], [50, 50])
        same, _ = paired_year_bootstrap(self.frame.assign(baseline=102), 'baseline', resamples=200)
        self.assertEqual(same['gain_percentile_95_kg_rai'], [0, 0])

    def test_pairs_ratio_of_means_and_reproducibility(self):
        frame = self.frame.copy()
        frame['baseline'] += (frame.year_ce - 2017) * 3
        frame['predicted_kg_rai'] += (frame.year_ce - 2017)
        one, yearly = paired_year_bootstrap(frame, 'baseline', resamples=200)
        two, _ = paired_year_bootstrap(frame.sample(frac=1, random_state=12), 'baseline', resamples=200)
        self.assertEqual(one, two)
        expected = 100 * (1 - yearly.model_absolute_error.mean() / yearly.baseline_absolute_error.mean())
        self.assertAlmostEqual(one['mae_reduction_pct'], expected)
        # Independently reconstruct the circular blocks and paired statistic.
        starts = np.random.default_rng(42).integers(9, size=(200, 3))
        indexes = ((starts[:, :, None] + np.arange(3)) % 9).reshape(200, 9)
        errors = yearly[['model_absolute_error', 'baseline_absolute_error']].to_numpy()
        sampled = errors[indexes].mean(axis=1)
        np.testing.assert_allclose(one['gain_percentile_95_kg_rai'],
                                   np.quantile(sampled[:, 1] - sampled[:, 0], [.025, .975]))

    def test_invalid_coverage_and_inputs_fail(self):
        for frame in (pd.concat([self.frame, self.frame.iloc[:1]]), self.frame.iloc[1:],
                      self.frame[self.frame.year_ce.ne(2020)], self.frame.assign(baseline=np.nan),
                      self.frame.assign(baseline=100), self.frame.assign(year_ce=2017.5)):
            with self.subTest(rows=len(frame)), self.assertRaises(ValueError):
                paired_year_bootstrap(frame, 'baseline', resamples=200)
        with self.assertRaises(ValueError):
            paired_year_bootstrap(self.frame, 'baseline', block_length=10)


if __name__ == '__main__':
    unittest.main()
