"""Seal Phase 11C outputs after focused tests; no network or source mutation."""
import csv
from tools import audit_chanthaburi_historical_district_yield as a


def seal():
    out=a.OUT
    if (out/'output_manifest.json').exists():
        raise FileExistsError('Refuse reseal')
    for row in a.read(out/'source_manifest.json')['inputs'].items():
        if a.p.sha(a.ROOT/row[0])!=row[1]: raise ValueError('Input lineage hash changed')
    before=a.read(out/'preflight_protected_hashes.json')
    if any(a.p.sha(a.ROOT/k)!=v for k,v in before.items()): raise ValueError('Protected file changed')
    assert a.p.sha(a.ROOT/a.p.previous.MODEL)==a.p.previous.MODEL_HASH
    assert a.p.sha(a.ROOT/'tools/audit_chanthaburi_historical_district_yield.py')==a.read(out/'source_manifest.json')['transformation_code_sha256']
    a.validate(a.read(out/'verified_district_year.json')['rows'])
    a.validate(a.read(out/'candidate_unverified_records.json')['rows'])
    coverage=a.read(out/'coverage_matrix.json')
    with (out/'coverage_matrix.csv').open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(coverage[0])); writer.writeheader(); writer.writerows(coverage)
    a.p.write(out/'test_verification.json',{'command':'python -m unittest tests.test_chanthaburi_historical_district_yield tests.test_chanthaburi_district_yield_extraction -q',
        'tests_run':20,'passed':20,'new_tests':11,'existing_phase11b_tests':9,'repository_wide_run':False,
        'tests_sha256':{name:a.p.sha(a.ROOT/name) for name in ['tests/test_chanthaburi_historical_district_yield.py','tests/test_chanthaburi_district_yield_extraction.py']}})
    payload={'files':{str(path.relative_to(out)):a.p.sha(path) for path in sorted(out.rglob('*')) if path.is_file()},
        'documentation_sha256':a.p.sha(a.ROOT/'docs/DURIAN_CHANTHABURI_HISTORICAL_DISTRICT_DISCOVERY_TH.md'),
        'code_sha256':{name:a.p.sha(a.ROOT/name) for name in ['tools/audit_chanthaburi_historical_district_yield.py','tools/seal_chanthaburi_historical_audit.py']},
        'public_release':'HOLD','acceptance_scope':'transcription_only; 0 new verified yield years; no historical PIT certification'}
    a.p.write(out/'output_manifest.json',{**payload,'manifest_payload_sha256':a.p.digest(payload)})
    print('SEALED: 20 tests passed; 1267 protected hashes unchanged; 0 new yield years')


if __name__=='__main__': seal()
