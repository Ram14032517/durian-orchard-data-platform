"""Frozen, isolated exploratory weather ablation; default invocation never fits."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile

import numpy as np
import pandas as pd

import experiment_rebaseline as rb
from compare_harvest_stage_yield import design, fit_predict

ARMS = ('last_year', 'catboost_no_weather', 'catboost_with_weather')
KEYS = ['province_code', 'year_ce']
LAG = rb.FEATURES[0]
OUTPUT_ROOT = rb.OUT / 'weather_ablation_exploratory'
REFERENCE = rb.OUTPUT_ROOT / '20261010T131023246729Z'


def candidates():
    return [dict(kind='previous_year', parameter=None, features=[LAG], group=ARMS[0])] + [
        dict(kind='catboost', parameter=dict(depth=d, l2_leaf_reg=10, learning_rate=.03),
             features=[LAG] if arm == ARMS[1] else list(rb.FEATURES), group=arm)
        for arm in ARMS[1:] for d in (2, 3)]


def protocol():
    return dict(mode='exploratory', provinces=rb.PROVINCES, years=list(rb.YEARS),
        outer_years=list(rb.OUTER_YEARS), inner_years=3, lead_days=60, seed=42,
        anchors=rb.ANCHORS, age_days=140, weather_lag_days=7,
        normals='preceding ten years; >=8 valid cells/day; Feb29=mean(Feb28,Mar01)',
        shared_fit_cutoff='earliest provincial issue midnight +07:00',
        selection_labels_cutoff='outer shared fit cutoff', training_start=2010,
        design='five province indicators, year_ce, ordered features; no other inputs',
        candidates=candidates(), fixed_catboost=dict(iterations=400, loss_function='RMSE',
            boosting_type='Ordered', random_seed=42, thread_count=1, allow_writing_files=False),
        selection='independent within-arm inner MAE; depth2 wins exact ties; no outer targets')


def validate_config(config):
    if config['protocol'] != protocol() or config['protocol_sha256'] != rb.digest_value(protocol()):
        raise ValueError('Frozen exploratory protocol changed')


def require_rows(frame, columns, expected):
    if (set(frame) != set(columns) or frame.duplicated(KEYS).any()
            or set(zip(frame.province_code, frame.year_ce)) != expected or len(frame) != len(expected)):
        raise ValueError('Incomplete/duplicate/unexpected rows or predictor columns')
    if not np.isfinite(frame[[c for c in columns if c != 'province_code']].to_numpy(float)).all():
        raise ValueError('Non-finite model inputs/labels')


def project(frame, candidate):
    arm = candidate['group']
    allowed = [LAG] if arm in ARMS[:2] else list(rb.FEATURES)
    if candidate['features'] != allowed or arm not in ARMS:
        raise ValueError('Weather descendant or unexpected predictor in arm')
    result = frame[KEYS + allowed].copy()
    if arm != ARMS[0] and design(result, rb.PROVINCES, allowed).shape[1] != (7 if arm == ARMS[1] else 14):
        raise ValueError('Unexpected actual design matrix')
    return result


def audit(prepared, manifest):
    """Replay consumed value lineage and exact availability coverage before any fit."""
    rb.validate_manifest(manifest)
    expected = {(p, y) for p in rb.PROVINCES for y in rb.YEARS}
    require_rows(prepared['inputs'], KEYS + rb.FEATURES, expected)
    lookup = prepared['inputs'].set_index(KEYS)
    traces = {(t['province_code'], t['year_ce'], t['feature']): t for t in prepared['lineage']}
    if len(prepared['lineage']) != 640 or set(traces) != {(p, y, f) for p, y in expected for f in rb.FEATURES}:
        raise ValueError('Incomplete/duplicate feature lineage')
    actual_versions = rb.versions(manifest)
    wanted_checks = []

    def request(ref, role, cutoff, context, end=None):
        record = manifest['records'][ref]
        warnings = rb.check(record, role, actual_versions[ref], cutoff, 'exploratory', observation_end=end)
        wanted_checks.append(dict(**context, dependency=ref, role=role, use_cutoff=cutoff,
            observation_end=end, source_version=actual_versions[ref],
            availability_status=record['availability_status'], warnings=warnings))

    contexts = {(o, y) for o in rb.OUTER_YEARS for y in [*range(o - 3, o), o]}
    folds = {(f['outer_year'], f['fold_year']): f for f in prepared['folds']}
    if len(prepared['folds']) != 36 or set(folds) != contexts:
        raise ValueError('Incomplete nested contexts')
    for (outer, year), fold in folds.items():
        dates, fit_cutoff = rb.fold_dates(manifest, year)
        _, selection_cutoff = rb.fold_dates(manifest, outer)
        issues = {p: rb.midnight(d) for p, d in dates.items()}
        stage = 'outer' if year == outer else 'inner'
        if (fold['fit_cutoff'] != fit_cutoff or fold['selection_cutoff'] != selection_cutoff
                or fold['issue_dates'] != issues or fold['stage'] != stage
                or fold['training_years'] != list(range(2010, year))
                or fold['training_rows'] != 5 * (year - 2010) or fold['forecast_rows'] != 5):
            raise ValueError('Fold cutoff/calendar/stage changed')
        train_keys = {(p, y) for p in rb.PROVINCES for y in range(2010, year)}
        test_keys = {(p, year) for p in rb.PROVINCES}
        require_rows(fold['train_predictors'], KEYS + rb.FEATURES, train_keys)
        require_rows(fold['forecast_predictors'], KEYS + rb.FEATURES, test_keys)
        require_rows(fold['training_labels'], KEYS + [rb.TARGET], train_keys)
        require_rows(fold['evaluation_reference'], KEYS + [rb.TARGET], test_keys)
        context = dict(outer_year=outer, fold_year=year, stage=stage)
        request('issue_rule', 'issue_rule', fit_cutoff, context)
        for role, frame in [('training_input', fold['train_predictors']), ('forecast_input', fold['forecast_predictors'])]:
            for row in frame.to_dict('records'):
                p, y = row['province_code'], row['year_ce']
                cutoff = fit_cutoff if role == 'training_input' else issues[p]
                row_context = dict(**context, input_role=role, province_code=p, row_year=y)
                request('calendar', 'calendar', cutoff, row_context)
                for feature in rb.FEATURES:
                    t = traces[p, y, feature]
                    global_value = lookup.loc[(p, y), feature]
                    if t['value'] != row[feature] or row[feature] != global_value:
                        raise ValueError('Actual predictor differs from consumed lineage/input')
                    if t['issue_date'] != rb.issue_date(manifest['schedule'], p, y, 60).isoformat():
                        raise ValueError('Lineage issue date differs from locked rule')
                    rb.check_feature_lineage(t, y, t['issue_date'], cutoff, 7)
                    if feature == LAG and (t['source_province'] != p
                            or t['source_value_sha256'] != rb.digest_value([p, y - 1, row[feature]])
                            or t.get('source_columns', []) or t.get('normal_dates') or t.get('observed_dates')):
                        raise ValueError('Lag has unexpected/derived weather lineage')
                    for ref in manifest['feature_dependencies'][feature]:
                        end = (f"{t['source_year']}-12-31" if ref == 'annual_lag' else
                               max(t['observed_dates']) if ref == 'power_observed' and t['observed_dates'] else
                               max(t['normal_dates']) if ref == 'power_normals' and t['normal_dates'] else None)
                        request(ref, 'feature', cutoff, dict(**row_context, feature=feature), end)
                if role == 'training_input':
                    request('training_labels', 'training_label', fit_cutoff, row_context, f'{y}-12-31')
                else:
                    request('evaluation_target', 'evaluation_target', cutoff, row_context)
                    if stage == 'inner':
                        request('selection_labels', 'selection_label', selection_cutoff, row_context, f'{y}-12-31')
    if Counter(map(rb.digest_value, wanted_checks)) != Counter(map(rb.digest_value, prepared['availability'])):
        raise ValueError('Incomplete/changed availability dependency records')
    return folds


def cache_key(config, fold, candidate, train, forecast):
    return rb.digest_value(dict(protocol=config['protocol_sha256'], arm=candidate['group'],
        features=candidate['features'], parameter=candidate['parameter'], year=fold['fold_year'],
        fit_cutoff=fold['fit_cutoff'], issue_dates=fold['issue_dates'],
        consumed_inputs_and_training_labels=[train.to_dict('records'), forecast.to_dict('records')]))


def train_predictions(prepared, config, manifest, fitter=fit_predict):
    validate_config(config)
    folds = audit(prepared, manifest)
    cache, predictions, tuning, choices, fit_audit = {}, [], [], [], []
    grid = config['protocol']['candidates']

    def predict(fold, candidate):
        train = project(fold['train_predictors'], candidate).merge(
            fold['training_labels'], on=KEYS, validate='one_to_one', sort=False)
        test = project(fold['forecast_predictors'], candidate)
        key = cache_key(config, fold, candidate, train, test)
        reused = key in cache
        if not reused:
            values = np.asarray(fitter(train, test.copy(), rb.PROVINCES, deepcopy(candidate)), float)
            if values.shape != (5,) or not np.isfinite(values).all():
                raise ValueError('Incomplete/non-finite predictions')
            cache[key] = values.copy()
        fit_audit.append(dict(outer_year=fold['outer_year'], fold_year=fold['fold_year'],
            arm=candidate['group'], parameter=json.dumps(candidate['parameter'], sort_keys=True),
            cache_key=key, reused=reused, fit_cutoff=fold['fit_cutoff'],
            feature_sha256=rb.digest_value(candidate['features']), training_rows=len(train)))
        return cache[key].copy()

    def reference(fold):
        return fold['forecast_predictors'][KEYS].merge(fold['evaluation_reference'], on=KEYS,
            validate='one_to_one', sort=False)

    for outer in rb.OUTER_YEARS:
        losses = []
        for candidate in grid:
            errors = []
            for year in range(outer - 3, outer):
                fold = folds[outer, year]
                values = predict(fold, candidate)
                error = float(np.abs(values - reference(fold)[rb.TARGET].to_numpy(float)).mean())
                errors.append(error)
                tuning.append(dict(outer_year=outer, inner_year=year, arm=candidate['group'],
                    parameter=json.dumps(candidate['parameter'], sort_keys=True), inner_mae=error,
                    fit_cutoff=fold['fit_cutoff'], selection_cutoff=fold['selection_cutoff']))
            losses.append(float(np.mean(errors)))
        winners = {arm: min((i for i, c in enumerate(grid) if c['group'] == arm),
                            key=lambda i: losses[i]) for arm in ARMS}
        fold = folds[outer, outer]
        estimates = {arm: predict(fold, grid[i]) for arm, i in winners.items()}
        actual = reference(fold)  # All outer predictions/choices are frozen above.
        for arm, index in winners.items():
            choices.append(dict(outer_year=outer, arm=arm, parameter=json.dumps(grid[index]['parameter'],
                sort_keys=True), inner_mae=losses[index], fit_cutoff=fold['fit_cutoff']))
            for row, value in zip(actual.to_dict('records'), estimates[arm]):
                predictions.append(dict(model=arm, province_code=row['province_code'], year_ce=outer,
                    issue_date=fold['issue_dates'][row['province_code']], actual_kg_rai=row[rb.TARGET],
                    predicted_kg_rai=float(value)))
        print(f'Weather ablation: completed {outer}; choices locked from inner MAE', flush=True)
    tables = summarize(pd.DataFrame(predictions))
    tables.update(tuning=pd.DataFrame(tuning), choices=pd.DataFrame(choices), fit_audit=pd.DataFrame(fit_audit))
    return tables


def summarize(frame):
    expected = {(m, p, y) for m in ARMS for p in rb.PROVINCES for y in rb.OUTER_YEARS}
    if (not {'model', *KEYS, 'actual_kg_rai', 'predicted_kg_rai', 'issue_date'}.issubset(frame)
            or frame.duplicated(['model', *KEYS]).any()
            or set(zip(frame.model, frame.province_code, frame.year_ce)) != expected
            or not np.isfinite(frame[['actual_kg_rai', 'predicted_kg_rai']].to_numpy(float)).all()
            or frame.groupby(KEYS).actual_kg_rai.nunique().ne(1).any()
            or frame.groupby(KEYS).issue_date.nunique().ne(1).any()):
        raise ValueError('Require exactly 135 paired predictions/references/issues')
    result = frame.copy()
    result['error'] = result.predicted_kg_rai - result.actual_kg_rai
    result['absolute_error'] = abs(result.error)
    wide = result.pivot(index=KEYS, columns='model', values='absolute_error')
    paired = wide.reset_index()
    paired['weather_gain_kg_rai'] = paired[ARMS[1]] - paired[ARMS[2]]
    for arm in ARMS[1:]:
        paired[arm + '_gain_vs_last_year'] = paired[ARMS[0]] - paired[arm]
    paired = paired.merge(result[result.model.eq(ARMS[0])][KEYS + ['issue_date', 'actual_kg_rai']], on=KEYS)
    for arm in ARMS:
        values = result[result.model.eq(arm)][KEYS + ['predicted_kg_rai', 'error']].rename(
            columns={'predicted_kg_rai': arm + '_prediction', 'error': arm + '_error'})
        paired = paired.merge(values, on=KEYS, validate='one_to_one')
    tables = dict(predictions=result, paired_errors=paired)
    for name, groups in [('overall', ['model']), ('by_year', ['model', 'year_ce']),
                         ('by_province', ['model', 'province_code'])]:
        rows = []
        for key, g in result.groupby(groups):
            key = key if isinstance(key, tuple) else (key,)
            baseline_gain = np.array([wide.loc[(p, y), ARMS[0]] - ae
                for p, y, ae in g[['province_code', 'year_ce', 'absolute_error']].itertuples(index=False, name=None)])
            baseline_ties = np.isclose(baseline_gain, 0, atol=1e-9, rtol=0)
            rows.append(dict(zip(groups, key)) | dict(n=len(g), mae=float(g.absolute_error.mean()),
                rmse=float(np.sqrt(np.mean(g.error ** 2))), bias=float(g.error.mean()),
                median_ae=float(g.absolute_error.median()),
                baseline_wins=int(((baseline_gain > 0) & ~baseline_ties).sum()),
                baseline_ties=int(baseline_ties.sum()),
                baseline_losses=int(((baseline_gain < 0) & ~baseline_ties).sum())))
        tables[name] = pd.DataFrame(rows)
    for name, groups in [('weather_contribution', []), ('weather_by_year', ['year_ce']),
                         ('weather_by_province', ['province_code'])]:
        rows = []
        for key, g in (paired.groupby(groups) if groups else [((), paired)]):
            key = key if isinstance(key, tuple) else (key,)
            gain = g.weather_gain_kg_rai
            ties = np.isclose(gain, 0, atol=1e-9, rtol=0)
            denominator = g[ARMS[1]].mean()
            rows.append(dict(zip(groups, key)) | dict(n=len(g), mean_gain=float(gain.mean()),
                median_gain=float(gain.median()), relative_mae_reduction_pct=float(100*gain.mean()/denominator)
                if denominator else None, wins=int(((gain > 0) & ~ties).sum()), ties=int(ties.sum()),
                losses=int(((gain < 0) & ~ties).sum()),
                rmse_reduction=float(np.sqrt(np.mean(g[ARMS[1] + '_error']**2))
                                     - np.sqrt(np.mean(g[ARMS[2] + '_error']**2))),
                no_weather_bias=float(g[ARMS[1] + '_error'].mean()),
                with_weather_bias=float(g[ARMS[2] + '_error'].mean())))
        tables[name] = pd.DataFrame(rows)
    tables['worst_errors'] = result.sort_values('absolute_error', ascending=False).groupby('model').head(5)
    tables['worst_weather_losses'] = paired.sort_values('weather_gain_kg_rai').head(5)
    return tables


def compare_reference(prepared, config, tables=None):
    old_config = json.loads((REFERENCE / 'config.json').read_text(encoding='utf-8'))
    for name, sha in json.loads((REFERENCE / 'completed_artifact_hashes.json').read_text()).items():
        if rb.digest(REFERENCE / name) != sha:
            raise ValueError('Phase 2 reference inventory mismatch')
    if (config['data_sha256'] != old_config['data_sha256'] or config['dependencies'] != old_config['dependencies']
            or config['schedule_sha256'] != old_config['schedule_sha256']
            or any(rb.digest(rb.ROOT / p) != sha for p, sha in old_config['code_sha256'].items())):
        raise ValueError('Phase 2 source/protocol/dependency mismatch')
    saved = pd.read_csv(REFERENCE / 'predictors.csv', dtype={'province_code': str}).sort_values(KEYS)
    current = prepared['inputs'].sort_values(KEYS)
    if (list(saved[KEYS].itertuples(index=False, name=None)) != list(current[KEYS].itertuples(index=False, name=None))
            or not np.allclose(saved[rb.FEATURES], current[rb.FEATURES], atol=1e-12, rtol=1e-14)):
        raise ValueError('Phase 2 predictor matrix mismatch')
    old_folds = json.loads((REFERENCE / 'folds.json').read_text())
    for old, new in zip(old_folds, prepared['folds']):
        if any(old[k] != new[k] for k in ('outer_year', 'fold_year', 'fit_cutoff', 'selection_cutoff', 'issue_dates')):
            raise ValueError('Phase 2 fold cutoff mismatch')
    if tables is not None:
        previous = pd.read_csv(REFERENCE / 'predictions.csv', dtype={'province_code': str})
        for arm, model in [(ARMS[0], 'last_year'), (ARMS[2], 'catboost')]:
            match = previous[previous.model.eq(model)].merge(tables['predictions'][tables['predictions'].model.eq(arm)],
                on=KEYS, validate='one_to_one', suffixes=('_old', '_new'))
            if len(match) != 45 or not np.allclose(match.predicted_kg_rai_old, match.predicted_kg_rai_new,
                                                   atol=1e-10, rtol=1e-12):
                raise ValueError('Fresh With Weather/baseline predictions differ from Phase 2; stop')


def protected_hashes():
    roots = ['api', 'ml', 'models', 'tests', 'research_data/five_province_history/training']
    files = {p for d in roots for p in (rb.ROOT / d).rglob('*') if p.is_file() and '__pycache__' not in p.parts
             and not p.is_relative_to(OUTPUT_ROOT)}
    files.update(p for p in (rb.ROOT / 'tools').rglob('*') if p.is_file() and '__pycache__' not in p.parts
                 and p.suffix in ('.py', '.js', '.mjs', '.html', '.css', '.json'))
    files.update(rb.DATA / f for f in ['UNIFIED_MAP.html', *rb.hashes()])
    return {str(p.relative_to(rb.ROOT)).replace('\\', '/'): rb.digest(p) for p in sorted(files)}


def assert_unchanged(config):
    if (rb.hashes() != config['data_sha256'] or rb.digest(rb.MANIFEST) != config['manifest_sha256']
            or any(not (rb.ROOT / p).is_file() or rb.digest(rb.ROOT / p) != h
                   for p, h in config['protected_sha256'].items())
            or not rb.production_model_matches()):
        raise ValueError('Protected files/source/Production changed; stop')


def write_preparation(prepared, config, manifest, run_id, root=OUTPUT_ROOT):
    lexical = Path(root).absolute()
    resolved = lexical.resolve()
    if (resolved.name != 'weather_ablation_exploratory'
            or not ((resolved == lexical == OUTPUT_ROOT.absolute()) or rb.safe_temporary_root(lexical))
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', run_id)):
        raise ValueError('Unsafe output path')
    destination = (resolved / run_id).resolve()
    if destination.parent != resolved or destination.exists():
        raise ValueError('Output collision or path escape')
    resolved.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    consumed = {arm: [t for t in prepared['lineage'] if arm == ARMS[2] or t['feature'] == LAG] for arm in ARMS}
    availability = {arm: [c for c in prepared['availability'] if arm == ARMS[2]
                         or c.get('feature', LAG) == LAG] for arm in ARMS}
    arm_dependencies = {arm: {f: manifest['feature_dependencies'][f] for f in
                        (rb.FEATURES if arm == ARMS[2] else [LAG])} for arm in ARMS}
    objects = dict(config=config, manifest=manifest, consumed_dependencies=arm_dependencies,
        feature_lineage=consumed, availability=availability,
        folds=[{k: v for k, v in f.items() if not isinstance(v, pd.DataFrame)} for f in prepared['folds']])
    for name, value in objects.items():
        with (destination / (name + '.json')).open('x', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
    for arm in ARMS:
        with (destination / (arm + '_predictors.csv')).open('x', encoding='utf-8-sig', newline='') as handle:
            project(prepared['inputs'], next(c for c in candidates() if c['group'] == arm)).to_csv(handle, index=False)
    # Only allowlisted model sources are copied; never environment or account credentials.
    source_dir = destination / 'source_snapshot'
    source_dir.mkdir()
    for name, sha in config.get('code_sha256', {}).items():
        source = rb.ROOT / name
        if rb.digest(source) != sha:
            raise ValueError('Source changed before snapshot')
        with (source_dir / name.replace('/', '__')).open('xb') as handle:
            handle.write(source.read_bytes())
    return destination


def run(training=False):
    if not rb.production_model_matches():
        raise ValueError('Production changed before preparation')
    prepared, base, manifest = rb.prepare()
    config = dict(base, protocol=protocol(), protocol_sha256=rb.digest_value(protocol()),
                  candidates=candidates(), preparation_only=not training,
                  features_by_arm={c['group']: c['features'] for c in candidates()},
                  training_requested=training, protected_sha256=protected_hashes())
    config['code_sha256'][str(Path(__file__).relative_to(rb.ROOT)).replace('\\', '/')] = rb.digest(Path(__file__))
    validate_config(config)
    audit(prepared, manifest)
    compare_reference(prepared, config)
    assert_unchanged(config)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = write_preparation(prepared, config, manifest, run_id)
    print(f'Preflight passed; new run={destination}; training={training}', flush=True)
    if training:
        tables = train_predictions(prepared, config, manifest)
        compare_reference(prepared, config, tables)
        assert_unchanged(config)
        for name, frame in tables.items():
            with (destination / (name + '.csv')).open('x', encoding='utf-8-sig', newline='') as handle:
                frame.to_csv(handle, index=False)
        print(tables['overall'].to_string(index=False), flush=True)
    status = dict(mode='exploratory', training_performed=training, pit_certified=False,
        completed_utc=datetime.now(timezone.utc).isoformat(), production_sha256=rb.digest(rb.PRODUCTION_MODEL),
        protected_files_checked=len(config['protected_sha256']), phase2_consistency_passed=True)
    with (destination / 'run_status.json').open('x', encoding='utf-8') as handle:
        json.dump(status, handle, indent=2)
    with (destination / 'completed_artifact_hashes.json').open('x', encoding='utf-8') as handle:
        json.dump({str(p.relative_to(destination)).replace('\\', '/'): rb.digest(p)
                   for p in destination.rglob('*') if p.is_file() and p.name != 'completed_artifact_hashes.json'}, handle, indent=2)
    print(f'Completed: {destination}', flush=True)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--train', action='store_true')
    args = parser.parse_args()
    if args.prepare or args.train:
        run(training=args.train)
    else:
        parser.print_help()
