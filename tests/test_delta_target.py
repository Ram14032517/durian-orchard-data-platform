"""Phase 7B boundaries; fake estimators only, never fits CatBoost."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/durian_model'))
import experiment_delta_target as dt


class DeltaTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = dt.et.load_inputs()
        cls.config = dict(protocol=dt.protocol(),protocol_hash=dt.rb.digest_value(dt.protocol()),
                          input_hashes={'synthetic':'1'},code_hashes={'synthetic':'1'})

    def fake(self,training,testing,depth):
        self.assertLess(training.year_ce.max(),testing.year_ce.min())
        self.assertEqual(list(testing),dt.KEYS+dt.rb.FEATURES)
        self.assertEqual(list(training),dt.KEYS+dt.rb.FEATURES+[dt.rb.TARGET])
        return np.full(len(testing),float(training[dt.rb.TARGET].median())+depth)

    def session(self,prepared=None,fitter=None):
        return dt.Session(prepared or self.prepared,self.config,fitter or self.fake)

    def test_signed_delta_and_post_reconstruction_clamp(self):
        raw,result = dt.reconstruct([-20,-150,20],[100,100,100],'delta')
        np.testing.assert_array_equal(raw,[80,-50,120])
        np.testing.assert_array_equal(result,[80,0,120])
        np.testing.assert_array_equal(dt.reconstruct([-20,50],[100,100],'level')[1],[0,50])
        for raw,lag,arm in [([1],[1,2],'delta'),([np.nan],[1],'level'),([1],[1],'bad')]:
            with self.assertRaises(ValueError):dt.reconstruct(raw,lag,arm)

    def test_real_signed_fitter_never_clamps_delta(self):
        observed = {}
        class FakeModel:
            def __init__(self,**params):observed['params']=params
            def fit(self,x,y):observed['y']=y.copy()
            def predict(self,x):return np.full(len(x),-200.)
        training = self.prepared['inputs'].iloc[:2].copy()
        training[dt.rb.TARGET]=[-10,20]
        testing=self.prepared['inputs'].query('year_ce == 2014').iloc[:1]
        with patch.dict(sys.modules,{'catboost':SimpleNamespace(CatBoostRegressor=FakeModel)}):
            result=dt.signed_fit(training,testing,2)
        np.testing.assert_array_equal(result,[-200])
        np.testing.assert_array_equal(observed['y'],[-10,20])
        self.assertEqual(observed['params']['random_seed'],42)
        self.assertEqual(observed['params']['iterations'],400)

    def test_actual_training_delta_and_predictor_isolation(self):
        session=self.session()
        fold=session.folds['10',2017,2014]
        def check(training,testing,depth):
            labels=self.prepared['annual'].set_index(dt.KEYS)[dt.rb.TARGET]
            expected=[float(labels.loc[p,y]-labels.loc[p,y-1])
                      for p,y in training[dt.KEYS].itertuples(index=False,name=None)]
            np.testing.assert_allclose(training[dt.rb.TARGET],expected,rtol=0,atol=1e-12)
            self.assertTrue(training[dt.rb.TARGET].lt(0).any())
            return np.full(10,-100.)
        session.fitter=check
        testing,raw,yield_raw,values=session.predict(fold,'delta',2)
        np.testing.assert_allclose(yield_raw,testing[dt.wa.LAG]-100)
        self.assertEqual(len(values),10)

    def test_inner_complete_and_selection_from_inner_only(self):
        session=self.session();tables,gate=session.inner()
        self.assertEqual(len(tables['inner_predictions']),270)
        self.assertEqual(len(tables['choices']),18)
        self.assertEqual(len(tables['tuning']),108)
        self.assertEqual(len(tables['inner_candidate_predictions']),540)
        self.assertTrue(tables['inner_predictions'].fold_year.lt(tables['inner_predictions'].outer_year).all())
        for choice in tables['choices'].to_dict('records'):
            t=tables['tuning'].query('arm == @choice["arm"] and outer_year == @choice["outer_year"]')
            self.assertEqual(choice['depth'],t.groupby('depth').mae.mean().idxmin())
        self.assertEqual(gate['duplicate_rows_per_arm'],80)
        self.assertTrue(any(a['reused'] for a in session.audit))

    def test_outer_2025_target_cannot_enter_inner_or_cache(self):
        first=self.session();tables,gate=first.inner()
        changed=deepcopy(self.prepared)
        changed['annual'].loc[changed['annual'].year_ce.eq(2025),dt.rb.TARGET]=1e9
        second=self.session(changed);again,other=second.inner()
        self.assertTrue(tables['choices'].equals(again['choices']))
        self.assertTrue(tables['inner_predictions'].equals(again['inner_predictions']))
        self.assertEqual(first.audit,second.audit)
        self.assertEqual(gate,other)

    def test_cache_separation_and_safe_identical_reuse(self):
        s=self.session();fold=s.folds['10',2017,2014]
        train=dt.et.project(self.prepared['inputs'].query('year_ce < 2014'),'D')
        test=dt.et.project(self.prepared['inputs'].query('year_ce == 2014'),'D')
        train[dt.rb.TARGET]=1.
        key=dt.cache_key(self.config,fold,'level',2,train,test)
        self.assertNotEqual(key,dt.cache_key(self.config,fold,'delta',2,train,test))
        self.assertNotEqual(key,dt.cache_key(self.config,fold,'level',3,train,test))
        for field in ('fit_cutoff','fold_year','issue_dates'):
            bad=deepcopy(fold);bad[field]='changed'
            self.assertNotEqual(key,dt.cache_key(self.config,bad,'level',2,train,test))
        for field in ('input_hashes','code_hashes','protocol_hash'):
            bad=deepcopy(self.config);bad[field]='changed'
            self.assertNotEqual(key,dt.cache_key(bad,fold,'level',2,train,test))
        bad=train.copy();bad[dt.rb.TARGET]=2
        self.assertNotEqual(key,dt.cache_key(self.config,fold,'level',2,bad,test))
        s.predict(fold,'level',2);s.predict(fold,'level',2)
        self.assertFalse(s.audit[0]['reused']);self.assertTrue(s.audit[1]['reused'])

    def test_missing_rows_fold_and_lag_stop_before_fit(self):
        for kind in ('input','annual','fold','lag','cutoff'):
            bad=deepcopy(self.prepared)
            if kind=='input':bad['inputs']=bad['inputs'].iloc[1:]
            if kind=='annual':bad['annual']=bad['annual'].iloc[1:]
            if kind=='fold':bad['folds']=bad['folds'][1:]
            if kind=='lag':bad['inputs'].loc[0,dt.wa.LAG]+=1
            if kind=='cutoff':bad['folds'][0]['fit_cutoff']='2099-01-01T00:00:00+07:00'
            with self.assertRaises(ValueError):self.session(bad)

    def test_future_publication_revised_version_and_missing_record_fail(self):
        for kind in ('future','version','missing'):
            bad=deepcopy(self.prepared);ref='training_labels:22'
            if kind=='future':bad['manifest']['records'][ref]['publication_date']='2099-01-01'
            if kind=='version':bad['manifest']['records'][ref]['source_version']='changed'
            if kind=='missing':del bad['manifest']['records'][ref]
            with self.assertRaises(ValueError):dt.target_audit(bad)

    def test_pair_lineage_includes_both_years_and_cutoffs(self):
        lineage,deps=dt.target_audit(self.prepared)
        self.assertEqual(len(deps),2*len(lineage))
        self.assertTrue(lineage.lag_year.eq(lineage.target_year-1).all())
        self.assertTrue(lineage[lineage.role.eq('training_label')].target_year.lt(
            lineage[lineage.role.eq('training_label')].fold_year).all())
        self.assertTrue(lineage[lineage.role.eq('selection_label')].target_year.lt(
            lineage[lineage.role.eq('selection_label')].outer_year).all())
        np.testing.assert_allclose(lineage.signed_delta,lineage.yield_value-lineage.lag_value)
        self.assertTrue(deps.publication_date.isna().all())
        self.assertTrue(deps.availability_status.eq('unverified').all())

    def test_inner_gate_and_outer_block(self):
        rows=[]
        for arm in dt.ARMS:
            for outer in dt.rb.OUTER_YEARS:
                for year in range(outer-3,outer):
                    for p in dt.rb.PROVINCES:
                        rows.append(dict(arm=arm,outer_year=outer,fold_year=year,province_code=p,
                            actual_kg_rai=1000.,predicted_kg_rai=1100. if arm=='level' else 1090.))
        frame=pd.DataFrame(rows)
        self.assertTrue(dt.inner_gate(frame)['passed'])
        frame.loc[frame.arm.eq('delta'),'predicted_kg_rai']=1099.
        gate=dt.inner_gate(frame);self.assertFalse(gate['passed'])
        with self.assertRaises(ValueError):self.session().outer(pd.DataFrame(),gate)
        with self.assertRaises(ValueError):dt.inner_gate(frame.iloc[1:])
        # Overall improvement alone cannot bypass provincial deterioration.
        frame.loc[frame.arm.eq('delta'),'predicted_kg_rai']=1000.
        frame.loc[frame.arm.eq('delta') & frame.province_code.eq('22'),'predicted_kg_rai']=1111.
        self.assertFalse(dt.inner_gate(frame)['passed'])

    def test_arm_outcome_mismatch_is_rejected(self):
        tables,_=self.session().inner()
        frame=tables['inner_predictions'].copy()
        frame.loc[frame.index[0],'actual_kg_rai']+=1
        with self.assertRaises(ValueError):dt.inner_gate(frame)

    def test_bad_prediction_and_protocol_are_rejected(self):
        bad=deepcopy(self.config);bad['protocol']['cohort']='5'
        with self.assertRaises(ValueError):dt.Session(self.prepared,bad,self.fake)
        s=self.session(fitter=lambda *args:np.ones(9))
        with self.assertRaises(ValueError):s.predict(s.folds['10',2017,2014],'level',2)

    def test_artifact_overwrite_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(dt,'OUTPUT',Path(directory)):
            destination=dt.reserve('test_run')
            with self.assertRaises(FileExistsError):dt.reserve('test_run')
            with self.assertRaises(ValueError):dt.reserve('../escape')
            dt.pe.write_json(destination/'config.json',{'fixed':True})
            with self.assertRaises(FileExistsError):dt.pe.write_json(destination/'config.json',{})


if __name__=='__main__':
    unittest.main()
