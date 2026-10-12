"""Offline, synthetic-only preparation. No network, estimator or production imports."""
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import sqlite3

ANCHORS = {'22': '04-01', '33': '05-01', '53': '06-01', '84': '07-01', '86': '07-01'}
FIT_ROLES = {'training_label', 'selection_label', 'training_feature'}
INPUT_ROLES = FIT_ROLES | {'lag_yield', 'weather', 'climatology'}
STATUSES = {'verified_available', 'verified_unavailable', 'unverified', 'not_applicable'}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def instant(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('timestamp requires explicit timezone; date-only evidence is insufficient')
    return result


def schedule():
    issues = {p: (datetime.fromisoformat('2027-' + a + 'T00:00:00+07:00')
                  - timedelta(days=60)).isoformat() for p, a in ANCHORS.items()}
    return {'target_year': 2027, 'lead_days': 60, 'anchors': ANCHORS.copy(),
            'issues': issues, 'shared_fit_cutoff': min(issues.values())}


def freeze_request(kind):
    if kind not in {'candidate', 'baseline'}:
        raise ValueError('unknown freeze kind')
    return {'kind': kind, 'status': 'pending_approval', 'selected_model': None,
            'model_version': None, 'artifacts': {}, 'schedule': schedule(),
            'required_inputs': {}, 'feature_lineage': {}, 'truth_policy':
            'score first-release and revised actual separately; never overwrite',
            'training_authorized': False, 'issuance_authorized': False,
            'historical_pit_certified': False}


class SyntheticLedger:
    """Only simulations are supported until a separate real-issuance implementation approval."""

    def __init__(self, path):
        self.path = Path(path)
        self.db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('''CREATE TABLE IF NOT EXISTS records (
            seq INTEGER PRIMARY KEY, record_id TEXT UNIQUE NOT NULL,
            kind TEXT NOT NULL, payload TEXT NOT NULL,
            previous_hash TEXT NOT NULL, record_hash TEXT UNIQUE NOT NULL)''')
        self.db.executescript('''
            CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON records
            BEGIN SELECT RAISE(ABORT, 'immutable records'); END;
            CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON records
            BEGIN SELECT RAISE(ABORT, 'immutable records'); END;
        ''')
        self.verify()

    def close(self):
        self.db.close()

    def verify(self, expected_head=None):
        previous = '0' * 64
        records = []
        for seq, rid, kind, payload, prev, sha in self.db.execute('SELECT * FROM records ORDER BY seq'):
            value = json.loads(payload)
            if seq != len(records) + 1 or prev != previous or value.get('simulation') is not True:
                raise ValueError('ledger sequence/chain/simulation corrupted')
            if digest({'id': rid, 'kind': kind, 'payload': value, 'previous_hash': prev}) != sha:
                raise ValueError('ledger hash mismatch')
            records.append({'id': rid, 'kind': kind, 'payload': value, 'hash': sha})
            previous = sha
        if expected_head is not None and previous != expected_head:
            raise ValueError('external checkpoint mismatch (possible truncation/replacement)')
        return records

    def _append(self, rid, kind, payload):
        if not rid or payload.get('simulation') is not True:
            raise ValueError('synthetic simulation required; real issuance disabled')
        canonical(payload)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            records = self.verify()
            prev = records[-1]['hash'] if records else '0' * 64
            sha = digest({'id': rid, 'kind': kind, 'payload': payload, 'previous_hash': prev})
            self.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?)',
                            (len(records) + 1, rid, kind, canonical(payload), prev, sha))
            self.db.commit()
            return sha
        except Exception:
            self.db.rollback()
            raise

    def _get(self, rid, kind):
        records = self.verify()
        match = [r for r in records if r['id'] == rid and r['kind'] == kind]
        if len(match) != 1:
            raise ValueError('missing or wrong-kind record: ' + rid)
        return match[0]

    def verify_provenance(self):
        records = self.verify()
        for record in records:
            payload = record['payload']
            if record['kind'] == 'source':
                if file_hash(payload['data_path']) != payload['data_hash']:
                    raise ValueError('registered source bytes changed')
                evidence = payload['evidence']
                if evidence and file_hash(evidence['path']) != evidence['sha256']:
                    raise ValueError('registered evidence bytes changed')
            elif record['kind'] == 'simulated_forecast':
                audit = self.preflight(payload['freeze_request'], payload['province'],
                                       payload['input_records'], payload['as_of'])
                if not audit['passed']:
                    raise ValueError('forecast provenance no longer verifies: ' + str(audit['reasons']))
        return {'records': len(records), 'head': records[-1]['hash'] if records else '0' * 64}

    def register_source(self, rid, source):
        source = json.loads(canonical(source))
        required = {'provider', 'version', 'publication_time', 'retrieval_time', 'valid_start',
                    'valid_end', 'availability_status', 'data_path', 'data_hash',
                    'evidence', 'data_kind', 'simulation', 'revision_of'}
        if not required <= source.keys():
            raise ValueError('incomplete source registry schema')
        if source['provider'] not in {'OAE', 'POWER'} or not source['version']:
            raise ValueError('provider/version missing or unsupported')
        if source['availability_status'] not in STATUSES:
            raise ValueError('unknown availability status')
        if source['data_kind'] not in {'observed', 'reanalysis', 'climatology'}:
            raise ValueError('unsupported data kind')
        instant(source['retrieval_time'])
        if instant(source['valid_start']) > instant(source['valid_end']):
            raise ValueError('invalid valid period')
        if source['publication_time'] is not None:
            instant(source['publication_time'])
        if file_hash(source['data_path']) != source['data_hash']:
            raise ValueError('source bytes mismatch')
        if source['revision_of']:
            original = self._get(source['revision_of'], 'source')['payload']
            if original['provider'] != source['provider'] or original['version'] == source['version']:
                raise ValueError('revision requires same provider and new version')
        return self._append(rid, 'source', source)

    def _source_check(self, rid, cutoff):
        source = self._get(rid, 'source')['payload']
        if source['availability_status'] != 'verified_available':
            raise ValueError('source availability is not verified')
        if not source['publication_time'] or not source['evidence']:
            raise ValueError('missing publication evidence')
        evidence = source['evidence']
        # Evidence must identify these exact bytes/version/time, not just a URL or file mtime.
        expected = {'data_hash': source['data_hash'], 'version': source['version'],
                    'publication_time': source['publication_time']}
        if any(evidence.get(k) != v for k, v in expected.items()) or not evidence.get('source_url'):
            raise ValueError('publication evidence does not bind source vintage')
        if file_hash(evidence['path']) != evidence['sha256'] or file_hash(source['data_path']) != source['data_hash']:
            raise ValueError('source/evidence bytes changed')
        boundary = instant(cutoff)
        published = instant(source['publication_time'])
        retrieved = instant(source['retrieval_time'])
        if published > boundary or retrieved > boundary or published > retrieved:
            raise ValueError('source unavailable/uncaptured at cutoff')
        if instant(source['valid_end']) > boundary:
            raise ValueError('future observations or climatology dependency')
        return source

    def preflight(self, request, province, inputs, as_of):
        errors = []
        try:
            fixed = schedule()
            if province not in ANCHORS or request['schedule'] != fixed:
                raise ValueError('fixed-calendar/province mismatch')
            if request['status'] != 'synthetic_approved' or request.get('simulation') is not True:
                raise ValueError('freeze pending; only synthetic approvals accepted')
            if not request.get('model_version') or not request.get('artifacts'):
                raise ValueError('missing model/config/code hashes')
            if set(request['artifacts']) != {'model', 'config', 'code'}:
                raise ValueError('incomplete artifact provenance')
            for item in request['artifacts'].values():
                if file_hash(item['path']) != item['sha256']:
                    raise ValueError('model/config/code bytes changed')
            issue = fixed['issues'][province]
            if instant(as_of) != instant(issue):
                raise ValueError('not the planned issue time')
            required = request['required_inputs']
            if not required or set(required) != set(inputs):
                raise ValueError('missing/extra inputs')
            lineage = request['feature_lineage']
            if not lineage or any(not ids for ids in lineage.values()):
                raise ValueError('missing feature lineage')
            if {k for ids in lineage.values() for k in ids} != set(required):
                raise ValueError('feature lineage dependency mismatch')
            for name, spec in required.items():
                if spec['role'] not in INPUT_ROLES:
                    raise ValueError('evaluation targets forbidden as inputs')
                cutoff = fixed['shared_fit_cutoff'] if spec['role'] in FIT_ROLES else issue
                source = self._source_check(inputs[name], cutoff)
                if source['provider'] != spec['provider'] or source['version'] != spec['version']:
                    raise ValueError('source role/version mismatch')
                if (source['valid_start'], source['valid_end']) != (spec['valid_start'], spec['valid_end']):
                    raise ValueError('input coverage mismatch')
        except (ValueError, KeyError, OSError, TypeError) as exc:
            errors.append(str(exc))
        return {'passed': not errors, 'reasons': errors, 'request_hash': digest(request),
                'input_records': inputs.copy(), 'as_of': as_of, 'simulation': True,
                'historical_pit_certified': False}

    def record_attempt(self, rid, request, province, inputs, as_of, prediction=None):
        audit = self.preflight(request, province, inputs, as_of)
        if prediction is not None and (not isinstance(prediction, (float, int))
                                       or isinstance(prediction, bool) or not math.isfinite(prediction) or prediction < 0):
            raise ValueError('invalid prediction')
        if audit['passed'] and prediction is None:
            audit['passed'] = False
            audit['reasons'] = ['no synthetic prediction supplied']
        payload = dict(audit, forecast_id=rid, province=province, target_year=2027,
                       issued_at=as_of, planned_issue_date=schedule()['issues'].get(province),
                       model_version=request.get('model_version'), freeze_request=request,
                       prediction_kg_rai=prediction if audit['passed'] else None)
        kind = 'simulated_forecast' if audit['passed'] else 'no_forecast_issued'
        return self._append(rid, kind, payload)

    def record_actual(self, rid, forecast_id, source_id, value, recorded_at, revision_of=None):
        forecast = self._get(forecast_id, 'simulated_forecast')['payload']
        source = self._source_check(source_id, recorded_at)
        if source['provider'] != 'OAE' or not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError('invalid actual')
        actual = json.loads(Path(source['data_path']).read_text(encoding='utf-8'))
        if (actual.get('province'), actual.get('target_year'), actual.get('yield_kg_rai')) != (forecast['province'], forecast['target_year'], value):
            raise ValueError('actual value/key does not match hashed source extract')
        if instant(source['valid_start']).year != forecast['target_year'] or instant(source['valid_end']).year != forecast['target_year']:
            raise ValueError('actual target period mismatch')
        if revision_of:
            original = self._get(revision_of, 'actual')['payload']
            if original['forecast_id'] != forecast_id or original['source_id'] == source_id:
                raise ValueError('invalid actual revision')
            prior = self._get(original['source_id'], 'source')['payload']
            if instant(source['publication_time']) <= instant(prior['publication_time']):
                raise ValueError('revision must be published later')
            if source['revision_of'] != original['source_id']:
                raise ValueError('source revision lineage mismatch')
        elif source['revision_of'] is not None:
            raise ValueError('revised source cannot be labeled first-release')
        elif any(r['kind'] == 'actual' and r['payload']['forecast_id'] == forecast_id for r in self.verify()):
            raise ValueError('first-release already recorded; append a revision')
        return self._append(rid, 'actual', {'simulation': True, 'forecast_id': forecast_id,
                            'source_id': source_id, 'yield_kg_rai': value, 'recorded_at': recorded_at,
                            'release_kind': 'revised' if revision_of else 'first_release',
                            'revision_of': revision_of, 'historical_pit_certified': False})
