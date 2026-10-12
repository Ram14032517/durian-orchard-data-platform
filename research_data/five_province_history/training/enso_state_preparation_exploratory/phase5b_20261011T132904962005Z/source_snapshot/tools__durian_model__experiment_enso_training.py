"""Phase 5B frozen exploratory training. Requires explicit --train."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import argparse

import numpy as np
import pandas as pd
import experiment_enso_state as es

rb, wa = es.rb, es.wa
REFERENCE = wa.OUTPUT_ROOT / '20261011T122324056845Z'


def protected_hashes():
    result = wa.protected_hashes()
    for root in (wa.OUTPUT_ROOT, rb.OUTPUT_ROOT, es.OUTPUT_ROOT, es.ARCHIVE, rb.ROOT / 'docs'):
        result.update({str(p.relative_to(rb.ROOT)).replace('\\', '/'): rb.digest(p)
                       for p in root.rglob('*') if p.is_file()})
    return result


def unchanged(hashes):
    if any(not (rb.ROOT / p).is_file() or rb.digest(rb.ROOT / p) != sha for p, sha in hashes.items()):
        raise ValueError('Protected files changed; stop')
    if rb.digest(rb.PRODUCTION_MODEL) != rb.PRODUCTION_SHA256:
        raise ValueError('Production model changed; stop')


def audit(prepared, config, traces, manifest):
    if config['protocol'] != es.protocol() or config['protocol_sha256'] != rb.digest_value(es.protocol()):
        raise ValueError('Frozen protocol changed')
    if rb.hashes() != config['data_sha256'] or rb.digest(rb.MANIFEST) != config['manifest_sha256']:
        raise ValueError('Inputs/manifest changed')
    if any(rb.digest(rb.ROOT / p) != sha for p, sha in config['code_sha256'].items()):
        raise ValueError('Code changed')
    if any(rb.digest(es.ARCHIVE / p) != sha for p, sha in config['archive_hashes'].items()):
        raise ValueError('ENSO source changed')
    base = deepcopy(prepared)
    for fold in base['folds']:
        for name in ('train_predictors', 'forecast_predictors'):
            fold[name] = fold[name][wa.KEYS + rb.FEATURES].copy()
    wa.audit(base, manifest)
    table = {(t['outer_year'], t['fold_year'], t['input_role'], t['province_code'], t['year_ce']): t
             for t in traces}
    if len(table) != 1890 or len(traces) != 1890:
        raise ValueError('Incomplete ENSO lineage')
    consumed = set()
    for f in prepared['folds']:
        for name, role in [('train_predictors', 'training_input'), ('forecast_predictors', 'forecast_input')]:
            for c in es.candidates():
                es.project(f[name], c)
            for row in f[name].to_dict('records'):
                key = (f['outer_year'], f['fold_year'], role, row['province_code'], row['year_ce'])
                t = table[key]
                cutoff = f['fit_cutoff'] if role == 'training_input' else f['issue_dates'][row['province_code']]
                if (t['role_cutoff'] != cutoff or t['use_cutoff'] != min(t['issue_date'][:10], cutoff[:10])
                        or t['publication_date'] >= t['use_cutoff']
                        or t['consumed_values'] != {c: row[c] for c in es.FEATURES}):
                    raise ValueError('ENSO feature/cutoff differs from actual lineage')
                consumed.add(key)
    if consumed != set(table):
        raise ValueError('Unexpected lineage records')


def train_predictions(prepared, config, traces, manifest, fitter=wa.fit_predict):
    audit(prepared, config, traces, manifest)
    folds = {(f['outer_year'], f['fold_year']): f for f in prepared['folds']}
    cache, predictions, tuning, choices, fit_records = {}, [], [], [], []
    states = {(t['outer_year'], t['province_code']): t['state'] for t in traces
              if t['input_role'] == 'forecast_input' and t['outer_year'] == t['fold_year']}
    grid = es.candidates()

    def predict(fold, candidate):
        train = es.project(fold['train_predictors'], candidate).merge(
            fold['training_labels'], on=wa.KEYS, validate='one_to_one', sort=False)
        forecast = es.project(fold['forecast_predictors'], candidate)
        key = es.cache_key(config, fold, candidate, train, forecast)
        reused = key in cache
        if not reused:
            values = np.asarray(fitter(train, forecast.copy(), rb.PROVINCES, deepcopy(candidate)), float)
            if values.shape != (5,) or not np.isfinite(values).all():
                raise ValueError('Incomplete predictions')
            cache[key] = values.copy()
        fit_records.append(dict(outer_year=fold['outer_year'], fold_year=fold['fold_year'],
            arm=candidate['group'], parameter=json.dumps(candidate['parameter'], sort_keys=True),
            cache_key=key, reused=reused, fit_cutoff=fold['fit_cutoff'], training_rows=len(train),
            encoding='fixed three-state vocabulary; no learned encoder parameters'))
        return cache[key].copy()

    def reference(fold):
        return fold['forecast_predictors'][wa.KEYS].merge(fold['evaluation_reference'],
            on=wa.KEYS, validate='one_to_one', sort=False)

    for outer in rb.OUTER_YEARS:
        losses = []
        for candidate in grid:
            errors = []
            for year in range(outer - 3, outer):
                f = folds[outer, year]
                values = predict(f, candidate)
                error = float(np.abs(values - reference(f)[rb.TARGET].to_numpy(float)).mean())
                errors.append(error)
                tuning.append(dict(outer_year=outer, inner_year=year, arm=candidate['group'],
                    depth=candidate['parameter']['depth'], inner_mae=error,
                    fit_cutoff=f['fit_cutoff'], selection_cutoff=f['selection_cutoff']))
            losses.append(float(np.mean(errors)))
        winners = {arm: min((i for i, c in enumerate(grid) if c['group'] == arm), key=lambda i: losses[i])
                   for arm in es.ARMS}
        f = folds[outer, outer]
        estimates = {arm: predict(f, grid[i]) for arm, i in winners.items()}
        actual = reference(f)  # Outer labels only after both estimates and choices are frozen.
        for arm, index in winners.items():
            choices.append(dict(outer_year=outer, arm=arm, depth=grid[index]['parameter']['depth'],
                inner_mae=losses[index], fit_cutoff=f['fit_cutoff']))
            for row, value in zip(actual.to_dict('records'), estimates[arm]):
                predictions.append(dict(model=arm, province_code=row['province_code'], year_ce=outer,
                    issue_date=f['issue_dates'][row['province_code']], actual_kg_rai=row[rb.TARGET],
                    predicted_kg_rai=float(value), enso_state=states[outer, row['province_code']]))
        print(f'ENSO: completed {outer}; inner-only choices frozen', flush=True)
    return dict(predictions=pd.DataFrame(predictions), tuning=pd.DataFrame(tuning),
                choices=pd.DataFrame(choices), fit_audit=pd.DataFrame(fit_records))


def summarize(frame):
    expected = {(m, p, y) for m in es.ARMS for p in rb.PROVINCES for y in rb.OUTER_YEARS}
    if (len(frame) != 90 or frame.duplicated(['model', *wa.KEYS]).any()
            or set(zip(frame.model, frame.province_code, frame.year_ce)) != expected
            or frame.groupby(wa.KEYS).actual_kg_rai.nunique().ne(1).any()
            or frame.groupby(wa.KEYS).enso_state.nunique().ne(1).any()):
        raise ValueError('Require 90 paired predictions')
    frame = frame.copy()
    frame['error'] = frame.predicted_kg_rai - frame.actual_kg_rai
    frame['absolute_error'] = abs(frame.error)
    tables = dict(predictions=frame)
    for name, groups in [('overall', ['model']), ('by_year', ['model', 'year_ce']),
                         ('by_province', ['model', 'province_code']), ('by_state', ['model', 'enso_state'])]:
        rows = []
        for key, g in frame.groupby(groups):
            key = key if isinstance(key, tuple) else (key,)
            rows.append(dict(zip(groups, key)) | dict(n=len(g), mae=float(g.absolute_error.mean()),
                rmse=float(np.sqrt(np.mean(g.error**2))), bias=float(g.error.mean())))
        tables[name] = pd.DataFrame(rows)
    a = frame[frame.model.eq(es.ARMS[0])]
    b = frame[frame.model.eq(es.ARMS[1])]
    paired = a.merge(b, on=wa.KEYS, validate='one_to_one', suffixes=('_weather', '_enso'))
    paired['enso_gain_kg_rai'] = paired.absolute_error_weather - paired.absolute_error_enso
    tables['paired_errors'] = paired
    rows = []
    for dimension in (None, 'year_ce', 'province_code', 'enso_state_weather'):
        for key, g in ([(None, paired)] if dimension is None else paired.groupby(dimension)):
            gain = g.enso_gain_kg_rai
            ties = np.isclose(gain, 0, atol=1e-9, rtol=0)
            rows.append(dict(dimension=dimension or 'overall', key=key, n=len(g),
                mean_gain=float(gain.mean()), median_gain=float(gain.median()),
                wins=int(((gain > 0) & ~ties).sum()), ties=int(ties.sum()),
                losses=int(((gain < 0) & ~ties).sum())))
    tables['contribution'] = pd.DataFrame(rows)
    tables['worst_errors'] = frame.sort_values('absolute_error', ascending=False).groupby('model').head(5)
    tables['worst_enso_losses'] = paired.sort_values('enso_gain_kg_rai').head(5)
    return tables


def compare_weather(frame):
    inventory = json.loads((REFERENCE / 'completed_artifact_hashes.json').read_text())
    if any(rb.digest(REFERENCE / p) != sha for p, sha in inventory.items()):
        raise ValueError('Phase 3 reference changed')
    saved = pd.read_csv(REFERENCE / 'predictions.csv', dtype={'province_code': str})
    match = saved[saved.model.eq(es.ARMS[0])].merge(frame[frame.model.eq(es.ARMS[0])],
        on=wa.KEYS, validate='one_to_one', suffixes=('_old', '_new'))
    if (len(match) != 45 or not np.allclose(match.predicted_kg_rai_old, match.predicted_kg_rai_new,
            atol=1e-10, rtol=1e-12) or not np.array_equal(match.actual_kg_rai_old, match.actual_kg_rai_new)
            or not np.array_equal(match.issue_date_old, match.issue_date_new)):
        raise ValueError('Weather regression; stop without changing model')


def run():
    before = protected_hashes()
    unchanged(before)
    prepared, config, traces, manifest = es.prepare()
    config.update(preparation_only=False, training_requested=True, protected_sha256=before)
    config['code_sha256']['tools/durian_model/experiment_enso_training.py'] = rb.digest(Path(__file__))
    audit(prepared, config, traces, manifest)
    unchanged(before)
    run_id = 'phase5b_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if (es.OUTPUT_ROOT / run_id).exists():
        raise ValueError('Output already exists')
    destination = es.write_preparation(prepared, config, traces, manifest, run_id)
    snapshot = destination / 'source_snapshot'
    snapshot.mkdir()
    for name, sha in config['code_sha256'].items():
        source = rb.ROOT / name
        if source.suffix != '.py' or rb.digest(source) != sha:
            raise ValueError('Unsafe/changed source snapshot')
        with (snapshot / name.replace('/', '__')).open('xb') as handle:
            handle.write(source.read_bytes())
    print(f'Preflight passed; new run={destination}', flush=True)
    tables = train_predictions(prepared, config, traces, manifest)
    compare_weather(tables['predictions'])
    tables.update(summarize(tables['predictions']))
    unchanged(before)
    for name, table in tables.items():
        with (destination / (name + '.csv')).open('x', encoding='utf-8-sig', newline='') as handle:
            table.to_csv(handle, index=False)
    with (destination / 'training_status.json').open('x', encoding='utf-8') as handle:
        json.dump(dict(training_performed=True, pit_certified=False, weather_regression_passed=True,
            protected_files_checked=len(before), production_sha256=rb.digest(rb.PRODUCTION_MODEL)), handle, indent=2)
    with (destination / 'completed_artifact_hashes.json').open('x', encoding='utf-8') as handle:
        json.dump({str(p.relative_to(destination)).replace('\\', '/'): rb.digest(p)
            for p in destination.rglob('*') if p.is_file() and p.name != 'completed_artifact_hashes.json'}, handle, indent=2)
    print(tables['overall'].to_string(index=False), flush=True)
    print(f'Completed {destination}', flush=True)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', action='store_true')
    args = parser.parse_args()
    if args.train:
        run()
    else:
        parser.print_help()
