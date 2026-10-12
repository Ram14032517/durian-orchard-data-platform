"""Read-only checks on prepared data, with exclusive verification outputs; no fitting."""
import argparse
from collections import Counter
from datetime import date
from importlib import metadata
import json
from pathlib import Path

import pandas as pd
import experiment_province_expansion as pe
from availability_guard import timestamp


def check_hashes(root, hashes):
    if any(not (root / key).is_file() or pe.rb.digest(root / key) != digest
           for key, digest in hashes.items()):
        raise ValueError('Source/code/artifact hash mismatch')


def audit(destination):
    load = lambda name: json.loads((destination / name).read_text(encoding='utf-8'))
    config, manifest = load('config.json'), load('manifest.json')
    check_hashes(destination, load('artifact_hashes.json'))
    check_hashes(pe.rb.ROOT, config['code_sha256'])
    check_hashes(pe.rb.ROOT, config['source_sha256'])
    check_hashes(pe.rb.ROOT, config['protected_sha256'])
    for record in manifest['records'].values():
        if 'path' in record:
            check_hashes(pe.rb.ROOT, {record['path']: record['source_version']})
    if pe.rb.digest_value(manifest) != config['protocol_hash']:
        raise ValueError('Manifest/protocol changed')
    checks, folds = load('availability_checks.json'), load('folds.json')
    for item in checks:
        if (item['role'] != 'evaluation_target' and item['observation_end']
                and date.fromisoformat(item['observation_end']) > timestamp(item['cutoff']).date()):
            raise ValueError('Consumed input/label reference exceeds cutoff')
    if len(folds) != 72:
        raise ValueError('Incomplete 36 contexts for each cohort')
    for fold in folds:
        y, outer, size = fold['fold_year'], fold['outer_year'], fold['cohort']
        if (not outer-3 <= y <= outer or fold['training_rows'] != len(pe.COHORTS[size])*(y-2010)
                or fold['forecast_rows'] != len(pe.COHORTS[size])
                or {tuple(k) for k in fold['selection_keys']} != {(p,y) for p in pe.rb.PROVINCES}):
            raise ValueError('Fold membership/selection cohort changed')
    keys = load('evaluation_keys.json')
    for role, provinces in [('primary',pe.rb.PROVINCES),('secondary',pe.NEW)]:
        expected = {(p,y) for p in provinces for y in pe.rb.OUTER_YEARS}
        if len(keys[role]) != 45 or {tuple(k) for k in keys[role]} != expected:
            raise ValueError('Evaluation keys changed')
    weather = pd.read_csv(destination/'new_weather_daily.csv',dtype={'province_code':str})
    sources = load('source_metadata.json')
    report = dict(training_performed=False, historical_pit_certified=False,
        sealed_artifacts=len(load('artifact_hashes.json')), protected_files=len(config['protected_sha256']),
        production_sha256=pe.rb.digest(pe.rb.PRODUCTION_MODEL),
        original_evaluation_keys=45, new_evaluation_keys=45, fold_contexts=len(folds),
        dependency_checks=len(checks), roles=dict(Counter(x['role'] for x in checks)),
        source_availability=dict(Counter(r['availability_status'] for r in manifest['records'].values())),
        warnings=dict(Counter(w for x in checks for w in x['warnings'])),
        weather_by_province=weather.groupby('province_code').agg(rows=('date','size'),first=('date','min'),last=('date','max')).reset_index().to_dict('records'),
        missing_weather_values=int(weather[pe.PARAMS].isna().sum().sum()),
        api_versions=sorted({s['header']['api']['version'] for s in sources}),
        source_models=sorted({model for s in sources for model in s['header']['sources']}),
        dependencies={name:metadata.version(name) for name in ('numpy','pandas','requests','openpyxl','scikit-learn','catboost')})
    pe.write_json(destination/'verification.json',report)
    print(json.dumps(report,ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot',type=Path)
    audit(parser.parse_args().snapshot)
