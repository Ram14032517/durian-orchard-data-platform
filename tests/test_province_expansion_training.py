"""Model boundaries with fake fitters only; never trains CatBoost."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/durian_model'))
import experiment_province_expansion_training as et
from tests.research_fixtures import expansion_prepared
from unittest.mock import patch


class ExpansionTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared=expansion_prepared(et)
        cls.config=dict(protocol=et.protocol(),protocol_hash=et.rb.digest_value(et.protocol()),
                        input_hashes={'synthetic':'1'},code_hashes={'synthetic':'1'})

    def fake(self,training,testing,provinces,c):
        self.assertEqual(set(training),set(et.KEYS+c['features']+[et.rb.TARGET]))
        self.assertEqual(set(testing),set(et.KEYS+c['features']))
        self.assertLess(training.year_ce.max(),testing.year_ce.min())
        self.assertEqual(provinces,et.pe.COHORTS[et.ARMS[c['group']][0]])
        return testing[et.wa.LAG].to_numpy(float)+c['parameter']['depth']*10

    def train(self,prepared=None,fitter=None):
        with redirect_stdout(io.StringIO()):
            return et.train(prepared or self.prepared,self.config,fitter or self.fake,gate=None)

    def test_design_encoding_and_no_weather(self):
        for arm,(size,weather) in et.ARMS.items():
            frame=self.prepared['inputs'][self.prepared['inputs'].province_code.isin(et.pe.COHORTS[size])]
            output=et.project(frame,arm)
            self.assertEqual(list(output),et.KEYS+(et.rb.FEATURES if weather else [et.wa.LAG]))
            self.assertEqual(et.wa.design(output,et.pe.COHORTS[size],et.candidate(arm,2)['features']).shape[1],
                             {'A':7,'B':14,'C':12,'D':19}[arm])
            if not weather:
                mutated=frame.copy()
                mutated[et.rb.FEATURES[1:]]=999999
                self.assertTrue(output.equals(et.project(mutated,arm)))

    def test_unknown_province_is_rejected(self):
        bad=self.prepared['inputs'].iloc[:1].copy()
        bad['province_code']='99'
        with self.assertRaises(ValueError):
            et.project(bad,'C')

    def test_reference_parity_gate_rejects_changed_predictions(self):
        source=pd.DataFrame([dict(model=model,province_code=p,year_ce=y,
            issue_date=f'{y}-01-31',actual_kg_rai=100.,predicted_kg_rai=101.)
            for model in ('catboost_no_weather','catboost_with_weather')
            for p in et.rb.PROVINCES for y in et.rb.OUTER_YEARS])
        reference=source.copy();reference['model']=reference.model.map({'catboost_no_weather':'A','catboost_with_weather':'B'})
        with patch.object(et.pd,'read_csv',return_value=source):
            et.reference_gate(reference)
            reference.loc[reference.index[0],'predicted_kg_rai']+=1
            with self.assertRaises(ValueError):
                et.reference_gate(reference)

    def test_prediction_completeness_and_inner_only_choices(self):
        tables=self.train()
        self.assertEqual(len(tables['predictions']),270)
        self.assertEqual(len(tables['choices']),36)
        self.assertEqual(tables['predictions'].groupby(['evaluation','model']).size().tolist(),[45]*6)
        for row in tables['choices'].to_dict('records'):
            values=tables['tuning']
            mean=values[values.arm.eq(row['arm']) & values.outer_year.eq(row['outer_year'])].groupby('depth').mae.mean()
            self.assertEqual(row['depth'],mean.idxmin())
        self.assertTrue(tables['fit_audit'].reused.any())

    def test_outer_2025_targets_never_enter_selection_or_fit_cache(self):
        original=self.train()
        changed=deepcopy(self.prepared)
        changed['annual'].loc[changed['annual'].year_ce.eq(2025),et.rb.TARGET]=1e9
        again=self.train(changed)
        self.assertTrue(original['choices'].equals(again['choices']))
        self.assertTrue(original['fit_audit'].equals(again['fit_audit']))
        self.assertTrue(np.array_equal(original['predictions'].predicted_kg_rai,again['predictions'].predicted_kg_rai))

    def test_new_province_inner_targets_do_not_select_depth(self):
        original=self.train()
        changed=deepcopy(self.prepared)
        changed['annual'].loc[changed['annual'].province_code.isin(et.pe.NEW),et.rb.TARGET]=1e8
        labels=changed['annual'].set_index(et.KEYS)[et.rb.TARGET]
        for fold in changed['folds']:
            keys=sorted((p,y) for p in et.pe.COHORTS[fold['cohort']] for y in range(2010,fold['fold_year']))
            fold['training_labels_sha256']=et.rb.digest_value([[p,y,float(labels.loc[p,y])] for p,y in keys])
        # Fake ignores training labels, isolating the selection-label effect alone.
        self.assertTrue(original['choices'].equals(self.train(changed)['choices']))

    def test_cache_bound_to_fold_features_hyperparameters_source_and_cutoff(self):
        fold=self.prepared['folds'][0]
        frame=self.prepared['inputs'][self.prepared['inputs'].province_code.isin(et.rb.PROVINCES)]
        train=et.project(frame[frame.year_ce.lt(fold['fold_year'])],'A')
        test=et.project(frame[frame.year_ce.eq(fold['fold_year'])],'A')
        key=et.cache_key(self.config,fold,'A',2,train,test)
        self.assertNotEqual(key,et.cache_key(self.config,fold,'B',2,train,test))
        self.assertNotEqual(key,et.cache_key(self.config,fold,'C',2,train,test))
        self.assertNotEqual(key,et.cache_key(self.config,fold,'A',3,train,test))
        for field in ('fit_cutoff','fold_year'):
            bad=deepcopy(fold);bad[field]='changed'
            self.assertNotEqual(key,et.cache_key(self.config,bad,'A',2,train,test))
        for field in ('input_hashes','code_hashes'):
            bad=deepcopy(self.config);bad[field]={'changed':'2'}
            self.assertNotEqual(key,et.cache_key(bad,fold,'A',2,train,test))

    def test_missing_fold_or_prediction_stops(self):
        bad=deepcopy(self.prepared);bad['folds']=bad['folds'][1:]
        with self.assertRaises(ValueError):
            self.train(bad)
        with self.assertRaises(ValueError):
            self.train(fitter=lambda *args:np.ones(4))
        tables=self.train()
        with self.assertRaises(ValueError):
            et.summarize(tables['predictions'].iloc[1:])

    def test_corrupt_fit_cutoff_and_selection_cohort_stop_before_fit(self):
        for field,value in [('fit_cutoff','2099-01-01T00:00:00+07:00'),('selection_keys',[['21',2014]])]:
            bad=deepcopy(self.prepared);bad['folds'][0][field]=value
            with self.assertRaises(ValueError):
                self.train(bad,fitter=lambda *args:(_ for _ in ()).throw(AssertionError('must not fit')))


if __name__=='__main__':
    unittest.main()
