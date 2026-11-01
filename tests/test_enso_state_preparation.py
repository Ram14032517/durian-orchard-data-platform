"""Preparation boundaries; synthetic predictors only, never estimator fitting."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
import experiment_enso_state as es
from tests import test_rebaseline as fixtures


class EnsoPreparationTests(unittest.TestCase):
    def test_pdf_extractor_spacing_never_changes_source_state_or_words(self):
        self.assertTrue(es.evidence_matches('atmospheric an d oceanic','atmospheric and oceanic','fixture.pdf','observed_state_evidence'))
        self.assertFalse(es.evidence_matches('El Niño','La Niña','fixture.pdf','observed_state'))
        self.assertFalse(es.evidence_matches('2014-02-06','2014-02-07','fixture.pdf','publication_date'))
        self.assertFalse(es.evidence_matches('and','or','fixture.pdf','observed_state_evidence'))
        self.assertFalse(es.evidence_matches('an d','and','fixture.html','observed_state_evidence'))

    @classmethod
    def setUpClass(cls):
        fixtures.RebaselineTests.setUpClass()
        fixture = fixtures.RebaselineTests()
        cls.prepared = fixture.prepared()
        cls.production_sha256 = es.rb.digest(es.rb.PRODUCTION_MODEL)
        cls.manifest = fixture.manifest
        cls.bundle = es.load_archive()
        cls.expanded, cls.traces = es.augment(cls.prepared, cls.manifest, cls.bundle, True)

    def test_asof_rejects_future_and_same_day(self):
        records = self.bundle['records']
        a = es.select_document(records, '2023-03-02', '2023-03-02')
        self.assertEqual(a['publication_date'], '2023-02-09')
        a = es.select_document(records, '2023-03-02', '2023-02-09')
        self.assertEqual(a['publication_date'], '2023-01-12')
        with self.assertRaises(ValueError):
            es.select_document(records, '2010-01-01', '2010-01-01')

    def test_all_actual_fold_values_have_evidence_before_cutoffs(self):
        self.assertEqual(len(self.traces), 1890)
        for t in self.traces:
            self.assertLess(t['publication_date'], t['use_cutoff'])
            self.assertEqual(sum(t['consumed_values'].values()), 1)
            self.assertTrue(t['source_sha256'] and t['observed_state_evidence'])
            self.assertFalse(t['pit_certified'])
        for old, new in zip(self.prepared['folds'], self.expanded['folds']):
            for name in ('training_labels', 'evaluation_reference'):
                pd.testing.assert_frame_equal(old[name], new[name])

    def test_disabled_feature_exact_legacy_object_design_and_stub_predictions(self):
        off, traces = es.augment(self.prepared, self.manifest, None, False)
        self.assertIs(off, self.prepared)
        self.assertEqual(traces, [])
        candidate = es.candidates()[0]
        for old, new in zip(self.prepared['folds'], self.expanded['folds']):
            for name in ('train_predictors', 'forecast_predictors'):
                a, b = es.wa.project(old[name], candidate), es.project(new[name], candidate)
                pd.testing.assert_frame_equal(a, b, check_exact=True)
                np.testing.assert_array_equal(es.wa.design(a, es.rb.PROVINCES, es.rb.FEATURES),
                                              es.wa.design(b, es.rb.PROVINCES, es.rb.FEATURES))
                # Prediction boundary spy, not a trained estimator.
                np.testing.assert_array_equal(a[es.wa.LAG].to_numpy(), b[es.wa.LAG].to_numpy())

    def test_target_poisoning_does_not_enter_enso_features(self):
        changed = deepcopy(self.prepared)
        for f in changed['folds']:
            f['evaluation_reference'][es.rb.TARGET] = 999999.
        expanded, traces = es.augment(changed, self.manifest, self.bundle, True)
        self.assertEqual(traces, self.traces)
        for a, b in zip(expanded['folds'], self.expanded['folds']):
            pd.testing.assert_frame_equal(a['forecast_predictors'], b['forecast_predictors'])
        for extra in ('enso_probability', 'revised_oni', es.rb.TARGET):
            frame = expanded['folds'][0]['forecast_predictors'].copy()
            frame[extra] = 1.
            with self.assertRaises(ValueError):
                es.project(frame, es.candidates()[2])

    def test_cache_arm_grid_archive_separation_and_reproducibility(self):
        fold = self.expanded['folds'][0]
        config = dict(protocol=es.protocol(), archive_hashes=self.bundle['hashes'])
        def key(candidate, cfg=config):
            return es.cache_key(cfg, fold, candidate, es.project(fold['train_predictors'], candidate),
                                es.project(fold['forecast_predictors'], candidate))
        keys = [key(c) for c in es.candidates()]
        self.assertEqual(len(set(keys)), 4)
        self.assertEqual(keys, [key(c) for c in es.candidates()])
        changed = deepcopy(config)
        changed['archive_hashes']['documents.csv'] = 'changed'
        self.assertNotEqual(keys[0], key(es.candidates()[0], changed))

    def test_missing_archive_and_dependency_records_fail_fast(self):
        for name in ('availability', 'fold_availability'):
            bundle = dict(self.bundle)
            bundle[name] = bundle[name].iloc[1:]
            with self.assertRaises((ValueError, KeyError)):
                es.augment(self.prepared, self.manifest, bundle, True)
        bundle = deepcopy(self.bundle)
        bundle['records'] = [r for r in bundle['records'] if r['archive_year'] != '2010']
        with self.assertRaises(ValueError):
            es.augment(self.prepared, self.manifest, bundle, True)

    def test_metadata_and_bytes_tampering_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'archive'
            shutil.copytree(es.ARCHIVE, root)
            path = root / 'documents.csv'
            docs = pd.read_csv(path, dtype=str, keep_default_na=False)
            docs.loc[0, 'observed_state'] = 'El Niño'
            docs.to_csv(path, index=False)
            with self.assertRaises(ValueError):
                es.load_archive(root)
            shutil.copyfile(es.ARCHIVE / 'documents.csv', path)
            (root / 'sources/2017_01.html').write_bytes(b'altered')
            with self.assertRaises(ValueError):
                es.load_archive(root)

    def test_no_missing_state_future_fill(self):
        records = deepcopy(self.bundle['records'])
        chosen = es.select_document(records, '2023-03-02', '2023-03-02')
        chosen['observed_state'] = ''
        with self.assertRaises(ValueError):
            es.select_document(records, '2023-03-02', '2023-03-02')

    def test_output_collision_path_and_production_protection(self):
        config = dict(protocol=es.protocol(), archive_hashes=self.bundle['hashes'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / es.OUTPUT_ROOT.name
            destination = es.write_preparation(self.expanded, config, self.traces, self.manifest, 'test', root)
            before = es.rb.digest(destination / 'config.json')
            inventory = json.loads((destination / 'artifact_hashes.json').read_text())
            self.assertNotIn('artifact_hashes.json', inventory)
            self.assertTrue(all(es.rb.digest(destination / name) == sha for name, sha in inventory.items()))
            with self.assertRaises(FileExistsError):
                es.write_preparation(self.expanded, config, self.traces, self.manifest, 'test', root)
            self.assertEqual(before, es.rb.digest(destination / 'config.json'))
            with self.assertRaises(ValueError):
                es.write_preparation(self.expanded, config, self.traces, self.manifest, '../escape', root)
        self.assertEqual(es.rb.digest(es.rb.PRODUCTION_MODEL), self.production_sha256)

    def test_protocol_and_candidates_are_frozen_to_two_arms(self):
        protocol = es.protocol()
        legacy = es.wa.protocol()
        for name in ('anchors', 'outer_years', 'inner_years', 'lead_days', 'provinces',
                     'fixed_catboost', 'seed', 'shared_fit_cutoff', 'selection'):
            self.assertEqual(protocol[name], legacy[name])
        self.assertEqual([c['parameter']['depth'] for c in es.candidates()], [2, 3, 2, 3])
        self.assertNotIn('forecast_probability', es.candidates()[2]['features'])
        self.assertFalse(protocol['forecast_probability'])


if __name__ == '__main__':
    unittest.main()
