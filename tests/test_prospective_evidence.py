"""Phase 8B: synthetic local files only; no model or API calls."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/durian_model'))
import prospective_evidence as pe


class ProspectiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = pe.SyntheticLedger(self.root / 'synthetic.sqlite')
        self.request = pe.freeze_request('candidate')
        self.request.update(status='synthetic_approved', simulation=True, model_version='SYNTHETIC-NOT-A-MODEL')
        for kind in ('model', 'config', 'code'):
            path = self.root / kind
            path.write_text('synthetic ' + kind, encoding='utf-8')
            self.request['artifacts'][kind] = {'path': str(path), 'sha256': pe.file_hash(path)}
        self.source = self.make_source('one')
        self.ledger.register_source('source-1', self.source)
        self.request['required_inputs'] = {'lag': {'role': 'lag_yield', 'provider': 'OAE',
            'version': 'synthetic-v1', 'valid_start': self.source['valid_start'], 'valid_end': self.source['valid_end']}}
        self.request['feature_lineage'] = {'previous_yield': ['lag']}
        self.inputs = {'lag': 'source-1'}
        self.issue = pe.schedule()['issues']['22']

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def make_source(self, name, value_payload=None, **changes):
        data = self.root / (name + '.json')
        data.write_text(json.dumps(value_payload or {'synthetic': True, 'yield': 123}), encoding='utf-8')
        evidence = self.root / (name + '.evidence.json')
        source = {'simulation': True, 'provider': 'OAE', 'version': 'synthetic-v1',
                  'publication_time': '2027-01-02T00:00:00+07:00',
                  'retrieval_time': '2027-01-03T00:00:00+07:00',
                  'valid_start': '2026-01-01T00:00:00+07:00',
                  'valid_end': '2026-12-31T00:00:00+07:00',
                  'availability_status': 'verified_available', 'data_kind': 'observed',
                  'data_path': str(data), 'data_hash': pe.file_hash(data), 'revision_of': None}
        source.update(changes)
        binding = {k: source[k] for k in ('data_hash', 'version', 'publication_time')}
        evidence.write_text(json.dumps(binding), encoding='utf-8')
        source['evidence'] = dict(binding, path=str(evidence), sha256=pe.file_hash(evidence), source_url='synthetic://not-live')
        return source

    def check(self, request=None, inputs=None, province='22', as_of=None):
        return self.ledger.preflight(request or self.request, province, self.inputs if inputs is None else inputs, as_of or self.issue)

    def test_schedule_and_pending_freeze(self):
        self.assertEqual(pe.schedule()['issues']['22'], '2027-01-31T00:00:00+07:00')
        self.assertEqual(pe.schedule()['issues']['86'], '2027-05-02T00:00:00+07:00')
        for kind in ('candidate', 'baseline'):
            request = pe.freeze_request(kind)
            self.assertIsNone(request['selected_model'])
            self.assertFalse(request['issuance_authorized'])
            self.assertFalse(self.check(request)['passed'])

    def test_forecast_and_no_forecast_simulation(self):
        self.assertTrue(self.check()['passed'])
        self.ledger.record_attempt('f1', self.request, '22', self.inputs, self.issue, 123)
        self.ledger.record_attempt('n1', self.request, '22', {}, self.issue, 123)
        records = self.ledger.verify()
        self.assertEqual(records[-2]['kind'], 'simulated_forecast')
        self.assertEqual(records[-1]['kind'], 'no_forecast_issued')
        self.assertIsNone(records[-1]['payload']['prediction_kg_rai'])
        self.assertTrue(records[-1]['payload']['reasons'])
        self.assertFalse(records[-2]['payload']['historical_pit_certified'])

    def test_duplicate_id_and_sql_immutability(self):
        for sql in ("UPDATE records SET payload='{}'", 'DELETE FROM records'):
            with self.assertRaises(sqlite3.IntegrityError): self.ledger.db.execute(sql)
        with self.assertRaises(sqlite3.IntegrityError): self.ledger.register_source('source-1', self.source)
        self.assertEqual(len(self.ledger.verify()), 1)

    def test_integrity_checkpoint_and_reopen(self):
        head = self.ledger.verify()[-1]['hash']
        self.ledger.verify(head)
        with self.assertRaises(ValueError): self.ledger.verify('0' * 64)
        self.ledger.close()
        self.ledger = pe.SyntheticLedger(self.root / 'synthetic.sqlite')
        self.assertEqual(self.ledger.verify(head)[-1]['hash'], head)

    def test_tampered_chain_fails(self):
        self.ledger.db.execute('DROP TRIGGER immutable_update')
        self.ledger.db.execute("UPDATE records SET payload='{}'")
        self.ledger.db.commit()
        with self.assertRaises(ValueError): self.ledger.verify()

    def test_missing_evidence_and_status_fail_closed(self):
        for change in ({'publication_time': None}, {'evidence': None},
                       {'availability_status': 'unverified'}, {'availability_status': 'not_applicable'},
                       {'availability_status': 'verified_unavailable'}):
            source = deepcopy(self.source); source.update(change)
            rid = 's' + str(len(self.ledger.verify()))
            self.ledger.register_source(rid, source)
            self.assertFalse(self.check(inputs={'lag': rid})['passed'])

    def test_future_publication_and_retrieval(self):
        for field in ('publication_time', 'retrieval_time', 'valid_end'):
            source = self.make_source(field, **{field: '2027-02-02T00:00:00+07:00'})
            self.ledger.register_source(field, source)
            request = deepcopy(self.request)
            request['required_inputs']['lag']['valid_end'] = source['valid_end']
            self.assertFalse(self.check(request, {'lag': field})['passed'])

    def test_training_and_selection_use_shared_cutoff(self):
        source = self.make_source('late', publication_time='2027-03-01T00:00:00+07:00', retrieval_time='2027-03-02T00:00:00+07:00')
        self.ledger.register_source('late', source)
        request = deepcopy(self.request)
        for role in ('training_label', 'selection_label', 'training_feature'):
            request['required_inputs']['lag']['role'] = role
            self.assertFalse(self.check(request, {'lag': 'late'}, '86', pe.schedule()['issues']['86'])['passed'])
        request['required_inputs']['lag']['role'] = 'lag_yield'
        self.assertTrue(self.check(request, {'lag': 'late'}, '86', pe.schedule()['issues']['86'])['passed'])

    def test_lineage_and_input_completeness(self):
        for lineage in ({}, {'lag': []}, {'lag': ['hidden']}):
            request = deepcopy(self.request); request['feature_lineage'] = lineage
            self.assertFalse(self.check(request)['passed'])
        self.assertFalse(self.check(inputs={})['passed'])
        self.assertFalse(self.check(inputs={'lag': 'source-1', 'extra': 'source-1'})['passed'])
        request = deepcopy(self.request); request['required_inputs']['lag']['role'] = 'evaluation_target'
        self.assertFalse(self.check(request)['passed'])

    def test_artifact_and_input_bytes_protected(self):
        for target in ('model', 'config', 'code'):
            path = Path(self.request['artifacts'][target]['path']); original = path.read_bytes()
            path.write_bytes(b'changed')
            self.assertFalse(self.check()['passed']); path.write_bytes(original)
        Path(self.source['data_path']).write_bytes(b'changed')
        self.assertFalse(self.check()['passed'])

    def test_evidence_hash_and_version_binding(self):
        source = deepcopy(self.source); source['evidence']['version'] = 'other'
        self.ledger.register_source('mismatch', source)
        self.assertFalse(self.check(inputs={'lag': 'mismatch'})['passed'])
        Path(self.source['evidence']['path']).write_bytes(b'changed evidence')
        self.assertFalse(self.check()['passed'])

    def test_version_changes_create_new_records(self):
        source = self.make_source('v2', version='synthetic-v2', revision_of='source-1')
        self.ledger.register_source('source-2', source)
        self.assertEqual(self.ledger.verify()[0]['payload']['version'], 'synthetic-v1')
        self.assertFalse(self.check(inputs={'lag': 'source-2'})['passed'])
        request = deepcopy(self.request); request['required_inputs']['lag']['version'] = 'synthetic-v2'
        self.assertTrue(self.check(request, {'lag': 'source-2'})['passed'])

    def test_actual_first_release_and_revision(self):
        self.ledger.record_attempt('f', self.request, '22', self.inputs, self.issue, 123)
        for rid, version, prior, val in [('a1', 'first', None, 120), ('a2', 'revised', 'a1', 125)]:
            pub = '2028-01-02T00:00:00+07:00' if prior is None else '2028-02-02T00:00:00+07:00'
            source = self.make_source(rid, value_payload={'province': '22', 'target_year': 2027, 'yield_kg_rai': val}, version=version, publication_time=pub, retrieval_time=pub,
                valid_start='2027-01-01T00:00:00+07:00', valid_end='2027-12-31T00:00:00+07:00',
                revision_of=None if prior is None else 'actual-source-a1')
            self.ledger.register_source('actual-source-' + rid, source)
            self.ledger.record_actual(rid, 'f', 'actual-source-' + rid, val, '2028-03-01T00:00:00+07:00', prior)
        actuals = [r['payload'] for r in self.ledger.verify() if r['kind'] == 'actual']
        self.assertEqual([a['yield_kg_rai'] for a in actuals], [120,125])
        self.assertEqual([a['release_kind'] for a in actuals], ['first_release', 'revised'])
        with self.assertRaises(ValueError): self.ledger.record_actual('a3', 'f', 'actual-source-a1', 120, '2028-03-01T00:00:00+07:00')

    def test_dates_calendar_and_real_issuance_disabled(self):
        with self.assertRaises(ValueError): pe.instant('2027-01-01')
        self.assertFalse(self.check(province='21')['passed'])
        self.assertFalse(self.check(as_of='2027-02-01T00:00:00+07:00')['passed'])
        request = deepcopy(self.request); request['schedule']['lead_days'] = 59
        self.assertFalse(self.check(request)['passed'])
        with self.assertRaises(ValueError): self.ledger._append('real', 'forecast', {'simulation': False})
        for value in (-1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError): self.ledger.record_attempt('bad', self.request, '22', self.inputs, self.issue, value)

    def test_provenance_recheck_and_unknown_source(self):
        self.ledger.record_attempt('f', self.request, '22', self.inputs, self.issue, 123)
        self.assertEqual(self.ledger.verify_provenance()['records'], 2)
        self.assertFalse(self.check(inputs={'lag': 'missing'})['passed'])
        Path(self.source['data_path']).write_bytes(b'tampered')
        with self.assertRaises(ValueError): self.ledger.verify_provenance()

    def test_power_climatology_and_wrong_actual_key(self):
        source = self.make_source('power', provider='POWER', data_kind='climatology')
        self.ledger.register_source('power', source)
        request = deepcopy(self.request)
        request['required_inputs']['lag'].update(provider='POWER', role='climatology')
        self.assertTrue(self.check(request, {'lag': 'power'})['passed'])
        self.ledger.record_attempt('f', self.request, '22', self.inputs, self.issue, 123)
        source = self.make_source('wrong-actual', value_payload={'province':'86','target_year':2027,'yield_kg_rai':120},
            publication_time='2028-01-01T00:00:00+07:00', retrieval_time='2028-01-01T00:00:00+07:00',
            valid_start='2027-01-01T00:00:00+07:00', valid_end='2027-12-31T00:00:00+07:00')
        self.ledger.register_source('wrong-actual', source)
        with self.assertRaises(ValueError): self.ledger.record_actual('a', 'f', 'wrong-actual',120,'2028-02-01T00:00:00+07:00')


if __name__ == '__main__':
    unittest.main()
