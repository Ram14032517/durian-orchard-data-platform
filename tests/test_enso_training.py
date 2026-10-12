"""Training orchestration tests use a prediction stub, never train estimators."""
from copy import deepcopy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
import experiment_enso_training as et


class EnsoTrainingTests(unittest.TestCase):
    def inputs(self):
        folds, traces = [], []
        for outer in et.rb.OUTER_YEARS:
            for year in range(outer - 3, outer + 1):
                def frame(y):
                    return pd.DataFrame([dict(province_code=p, year_ce=y,
                        **{f: 100. for f in et.rb.FEATURES},
                        **dict(zip(et.es.FEATURES, [0, 1, 0]))) for p in et.rb.PROVINCES])
                folds.append(dict(outer_year=outer, fold_year=year, fit_cutoff=f'{year}-01-31',
                    selection_cutoff=f'{outer}-01-31', issue_dates={p:f'{year}-01-31' for p in et.rb.PROVINCES},
                    train_predictors=frame(year-1), forecast_predictors=frame(year),
                    training_labels=frame(year-1)[et.wa.KEYS].assign(**{et.rb.TARGET:100.}),
                    evaluation_reference=frame(year)[et.wa.KEYS].assign(**{et.rb.TARGET:100.})))
                for p in et.rb.PROVINCES:
                    traces.append(dict(outer_year=outer, fold_year=year, province_code=p,
                        input_role='forecast_input', state='Neutral'))
        return dict(folds=folds), dict(protocol=et.es.protocol(), archive_hashes={'source':'hash'}), traces

    def predict(self, prepared=None):
        base, config, traces = self.inputs()
        calls = []
        def fake(train, forecast, provinces, candidate):
            self.assertLess(train.year_ce.max(), forecast.year_ce.min())
            self.assertEqual(set(train), set(et.wa.KEYS + candidate['features'] + [et.rb.TARGET]))
            self.assertEqual(set(forecast), set(et.wa.KEYS + candidate['features']))
            calls.append(candidate['group'])
            depth = candidate['parameter']['depth']
            error = depth if candidate['group']==et.es.ARMS[0] else 4-depth
            return np.full(5, float(train[et.rb.TARGET].mean()) + error)
        with patch.object(et, 'audit'), redirect_stdout(io.StringIO()):
            tables = et.train_predictions(prepared or base, config, traces, {}, fitter=fake)
        return tables, calls

    def test_inner_only_selection_and_cache(self):
        tables, calls = self.predict()
        self.assertEqual(len(tables['predictions']),90)
        # 2014–2024: four inner candidates/year; 2025: only two selected outer winners.
        self.assertEqual(len(calls),46)
        choices = tables['choices']
        self.assertTrue(choices[choices.arm.eq(et.es.ARMS[0])].depth.eq(2).all())
        self.assertTrue(choices[choices.arm.eq(et.es.ARMS[1])].depth.eq(3).all())
        for arm in et.es.ARMS:
            keys = set(tables['fit_audit'].loc[tables['fit_audit'].arm.eq(arm), 'cache_key'])
            self.assertEqual(len(keys),23)
        audit = tables['fit_audit']
        self.assertEqual(len(audit),126)  # 9 × (3 inner years × 4 candidates + 2 outer winners).
        self.assertEqual(int((~audit.reused).sum()),46)
        self.assertEqual(int(audit.reused.sum()),80)
        for key, records in audit.groupby('cache_key', sort=False):
            self.assertFalse(bool(records.iloc[0].reused))
            self.assertTrue(records.iloc[1:].reused.all())
            for column in ('fold_year', 'arm', 'parameter', 'fit_cutoff', 'training_rows'):
                self.assertEqual(records[column].nunique(),1)
        signatures = ['fold_year', 'arm', 'parameter', 'fit_cutoff']
        self.assertTrue(audit.groupby(signatures).cache_key.nunique().eq(1).all())
        fits = audit[~audit.reused]
        for year in range(2014,2025):
            group = fits[fits.fold_year.eq(year)]
            self.assertEqual(len(group),4)
            for arm in et.es.ARMS:
                depths = {json.loads(v)['depth'] for v in group[group.arm.eq(arm)].parameter}
                self.assertEqual(depths,{2,3})
        final = audit[audit.fold_year.eq(2025)]
        self.assertEqual(len(final),2)
        self.assertFalse(final.reused.any())
        for arm in et.es.ARMS:
            inner = tables['tuning'][(tables['tuning'].outer_year.eq(2025)) & tables['tuning'].arm.eq(arm)]
            self.assertEqual(set(inner.inner_year),{2022,2023,2024})
            self.assertEqual(len(inner),6)
            selected = int(inner.groupby('depth').inner_mae.mean().idxmin())
            self.assertEqual(int(choices[(choices.outer_year.eq(2025)) & choices.arm.eq(arm)].iloc[0].depth),selected)
            self.assertEqual(json.loads(final[final.arm.eq(arm)].iloc[0].parameter)['depth'],selected)
            predictions = tables['predictions'][tables['predictions'].model.eq(arm)]
            self.assertEqual(set(zip(predictions.province_code,predictions.year_ce)),
                             {(p,y) for p in et.rb.PROVINCES for y in et.rb.OUTER_YEARS})

    def test_outer_target_poison_cannot_change_choices_predictions(self):
        base, _, _ = self.inputs()
        for f in base['folds']:
            if f['outer_year']==f['fold_year']:
                f['evaluation_reference'][et.rb.TARGET]=999999.
        a, _ = self.predict()
        b, _ = self.predict(base)
        pd.testing.assert_frame_equal(a['choices'],b['choices'])
        np.testing.assert_array_equal(a['predictions'].predicted_kg_rai,b['predictions'].predicted_kg_rai)

    def test_paired_summary_and_missing_keys(self):
        tables, _ = self.predict()
        result = et.summarize(tables['predictions'])
        overall = result['contribution'].iloc[0]
        self.assertEqual((overall.n,overall.wins,overall.ties,overall.losses),(45,45,0,0))
        self.assertEqual(overall.mean_gain,1.)
        self.assertEqual(len(result['paired_errors']),45)
        with self.assertRaises(ValueError):
            et.summarize(tables['predictions'].iloc[1:])


if __name__=='__main__':
    unittest.main()
