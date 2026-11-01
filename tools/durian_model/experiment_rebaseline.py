"""Isolated exploratory rebaseline; preparation stays the default, training is opt-in."""
import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

from common import ROOT, DATA, OUT, FEATURES, PROVINCES, TARGET, load_panel, check_snapshot, hashes, safe_temporary_root, verify_production_snapshot
from experiment_issue_date import IssueWeather, AGE, WEATHER_LAG, MANIFEST
from availability_guard import check, check_feature_lineage, digest, issue_date, preflight, schedule_version, source_identity

ANCHORS = {'22': '04-01', '33': '05-01', '53': '06-01', '84': '07-01', '86': '07-01'}
YEARS = tuple(range(2010, 2026))
OUTER_YEARS = tuple(range(2017, 2026))
LEAD = 60
SEED = 42
OUTPUT_ROOT = OUT / 'rebaseline_exploratory'
PRODUCTION_MODEL = OUT / 'ridge_vpd_final_model.json'
PRODUCTION_SHA256 = 'b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680'


def production_model_matches():
    try:
        verify_production_snapshot(PRODUCTION_SHA256)
        return True
    except (ValueError, OSError):
        return False


def candidates():
    return [dict(kind='previous_year', parameter=None, features=[], group='last_year')] + [
        dict(kind='ridge', parameter=a, features=list(FEATURES), group='ridge') for a in (1., 10., 100.)] + [
        dict(kind='catboost', parameter=dict(depth=d, l2_leaf_reg=10, learning_rate=.03),
             features=list(FEATURES), group='catboost') for d in (2, 3)]


def validate_panel(panel):
    required = {'province_code', 'year_ce', TARGET, 'previous_yield_kg_rai'}
    if not required.issubset(panel):
        raise ValueError('Incomplete panel columns')
    expected = {(p, y) for p in PROVINCES for y in YEARS}
    if panel.duplicated(['province_code', 'year_ce']).any() or set(zip(panel.province_code, panel.year_ce)) != expected:
        raise ValueError('Require exactly 80 province-years; never silently drop rows')
    if (not np.isfinite(panel[[TARGET, 'previous_yield_kg_rai']].to_numpy(float)).all()
            or (panel[[TARGET, 'previous_yield_kg_rai']] < 0).any().any()
            or not np.equal(panel.year_ce, np.floor(panel.year_ce)).all()):
        raise ValueError('Missing annual label/lag; no imputation')


def validate_manifest(manifest):
    if manifest['schedule']['kind'] != 'fixed_calendar' or manifest['schedule']['anchors'] != ANCHORS:
        raise ValueError('Fixed calendar is locked for Phase 1')
    expected = {f: (['annual_lag'] if f == FEATURES[0] else
                   ['power_observed', 'power_normals', 'issue_rule_feature']) for f in FEATURES}
    if manifest['feature_dependencies'] != expected:
        raise ValueError('Incomplete or changed feature dependencies')
    required = {'annual_lag', 'training_labels', 'selection_labels', 'evaluation_target',
                'power_observed', 'power_normals', 'calendar', 'issue_rule', 'issue_rule_feature'}
    if not required.issubset(manifest['records']):
        raise ValueError('Incomplete dependency records')


def midnight(day):
    return day.isoformat() + 'T00:00:00+07:00'


def versions(manifest):
    result = {k: source_identity(r, ROOT)['version'] for k, r in manifest['records'].items() if 'path' in r}
    result.update(calendar='calendar-v1', issue_rule=schedule_version(manifest['schedule']),
                  issue_rule_feature=schedule_version(manifest['schedule']))
    return result


def fold_dates(manifest, year):
    dates = {p: issue_date(manifest['schedule'], p, year, LEAD) for p in PROVINCES}
    return dates, midnight(min(dates.values()))


def build_inputs(keys, weather, manifest):
    """The builder receives keys only, never annual targets/area/production."""
    if set(keys.columns) != {'province_code', 'year_ce'} or keys.duplicated().any():
        raise ValueError('Feature construction accepts unique province-year keys only')
    values, lineage = [], []
    for row in keys.to_dict('records'):
        p, year = row['province_code'], row['year_ce']
        month = int(ANCHORS[p][:2])
        features, issue, available, traces = weather.features_with_lineage(p, year, list(range(month, month + 3)), LEAD)
        if set(features) != set(FEATURES[1:]) or {t['feature'] for t in traces} != set(FEATURES[1:]) or len(traces) != 7:
            raise ValueError('Missing engineered features/lineage')
        if issue != issue_date(manifest['schedule'], p, year, LEAD):
            raise ValueError('Feature builder issue date differs from locked calendar')
        values.append(dict(**row, **features))
        lineage.extend(dict(**row, issue_date=issue.isoformat(), weather_available_through=available.isoformat(), **t)
                       for t in traces)
    return pd.DataFrame(values), lineage


def prepare_folds(panel, annual, weather, manifest):
    """No fit; audit every nested context with actual consumed feature provenance."""
    validate_panel(panel)
    validate_manifest(manifest)
    actual_versions = versions(manifest)
    if annual.duplicated(['province_code', 'year_ce']).any():
        raise ValueError('Duplicate annual source keys')
    annual_lookup = annual.set_index(['province_code', 'year_ce'])[TARGET]
    # Separate reference labels before feature construction; own-year targets are not passed in.
    labels = panel[['province_code', 'year_ce', TARGET]].copy()
    keys = panel[['province_code', 'year_ce']].copy()
    inputs, lineage = build_inputs(keys, weather, manifest)
    lags = []
    for row in keys.to_dict('records'):
        p, year = row['province_code'], row['year_ce']
        if (p, year - 1) not in annual_lookup.index:
            raise ValueError('Missing previous-year source row')
        value = float(annual_lookup.loc[(p, year - 1)])
        if not np.isfinite(value) or value < 0:
            raise ValueError('Invalid previous-year source value')
        lags.append(value)
        lineage.append(dict(**row, feature=FEATURES[0], value=value,
                            source_province=p, source_year=year - 1,
                            source_value_sha256=digest_value([p, year - 1, value]),
                            issue_date=issue_date(manifest['schedule'], p, year, LEAD).isoformat()))
    inputs[FEATURES[0]] = lags
    if not np.allclose(inputs[FEATURES[0]], panel['previous_yield_kg_rai'].to_numpy(float)):
        raise ValueError('Lag values differ from actual annual-source lookup')
    inputs = inputs[['province_code', 'year_ce', *FEATURES]]
    if not np.isfinite(inputs[FEATURES].to_numpy(float)).all():
        raise ValueError('Incomplete predictors')
    traces = {(p, y): [] for p, y in zip(keys.province_code, keys.year_ce)}
    for item in lineage:
        traces[item['province_code'], item['year_ce']].append(item)
    checks, folds = [], []

    def availability(ref, role, cutoff, context, observation_end=None):
        warnings = check(manifest['records'][ref], role, actual_versions[ref], cutoff,
                         'exploratory', observation_end=observation_end)
        checks.append(dict(**context, dependency=ref, role=role, use_cutoff=cutoff,
                           observation_end=observation_end, source_version=actual_versions[ref],
                           availability_status=manifest['records'][ref]['availability_status'], warnings=warnings))

    for outer in OUTER_YEARS:
        _, outer_cutoff = fold_dates(manifest, outer)
        for year in [*range(outer - 3, outer), outer]:
            stage = 'outer' if year == outer else 'inner'
            dates, fit_cutoff = fold_dates(manifest, year)
            context = dict(outer_year=outer, fold_year=year, stage=stage)
            availability('issue_rule', 'issue_rule', fit_cutoff, context)
            train = inputs[inputs.year_ce.lt(year)].copy()
            forecast = inputs[inputs.year_ce.eq(year)].copy()
            expected_train = {(p, y) for p in PROVINCES for y in range(2010, year)}
            if set(zip(train.province_code, train.year_ce)) != expected_train or len(forecast) != 5:
                raise ValueError('Incomplete fold samples')
            for role, frame in [('training_input', train), ('forecast_input', forecast)]:
                for row in frame.to_dict('records'):
                    p, row_year = row['province_code'], row['year_ce']
                    cutoff = fit_cutoff if role == 'training_input' else midnight(dates[p])
                    row_context = dict(**context, input_role=role, province_code=p, row_year=row_year)
                    availability('calendar', 'calendar', cutoff, row_context)
                    items = traces[p, row_year]
                    if len(items) != 8 or {t['feature'] for t in items} != set(FEATURES):
                        raise ValueError('Incomplete per-row lineage')
                    for item in items:
                        if item['value'] != row[item['feature']]:
                            raise ValueError('Engineered value differs from builder lineage')
                        check_feature_lineage(item, row_year, item['issue_date'], cutoff, WEATHER_LAG)
                        for ref in manifest['feature_dependencies'][item['feature']]:
                            end = None
                            if ref == 'annual_lag':
                                end = f"{item['source_year']}-12-31"
                            elif ref == 'power_observed' and item['observed_dates']:
                                end = max(item['observed_dates'])
                            elif ref == 'power_normals' and item['normal_dates']:
                                end = max(item['normal_dates'])
                            availability(ref, 'feature', cutoff, dict(**row_context, feature=item['feature']), end)
                    if role == 'training_input':
                        availability('training_labels', 'training_label', fit_cutoff, row_context,
                                     f'{row_year}-12-31')
                    else:
                        availability('evaluation_target', 'evaluation_target', cutoff, row_context)
                        if stage == 'inner':
                            availability('selection_labels', 'selection_label', outer_cutoff, row_context,
                                         f'{row_year}-12-31')
            train_labels = labels[labels.year_ce.lt(year)].copy()
            evaluation = labels[labels.year_ce.eq(year)].copy()
            folds.append(dict(**context, fit_cutoff=fit_cutoff, selection_cutoff=outer_cutoff,
                issue_dates={p: midnight(d) for p, d in dates.items()},
                training_years=list(range(2010, year)), training_rows=len(train), forecast_rows=len(forecast),
                training_labels_sha256=digest_value(train_labels.to_dict('records')),
                evaluation_reference_sha256=digest_value(evaluation.to_dict('records')),
                train_predictors=train, forecast_predictors=forecast,
                training_labels=train_labels, evaluation_reference=evaluation))
    return dict(folds=folds, inputs=inputs, lineage=lineage, availability=checks, pit_certified=False,
                source_integrity={k: source_identity(r, ROOT) for k, r in manifest['records'].items() if 'path' in r})


def digest_value(value):
    import hashlib
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def configuration(manifest_path, manifest):
    code_files = [Path(__file__), Path(__file__).with_name('experiment_issue_date.py'),
                  Path(__file__).with_name('availability_guard.py'), Path(__file__).with_name('common.py'),
                  ROOT / 'tools/compare_harvest_stage_yield.py', ROOT / 'tools/train_monthly_production.py',
                  ROOT / 'tools/analyze_harvest_backcast.py', Path(__file__).with_name('step5_evaluate_result.py')]
    git = lambda *args: subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    return dict(schema_version=1, mode='exploratory', preparation_only=True, training_performed=False,
        score_label='Exploratory retrospective; not PIT-certified', pit_certified=False,
        created_utc=datetime.now(timezone.utc).isoformat(), seed=SEED, lead_days=LEAD,
        years=list(YEARS), outer_years=list(OUTER_YEARS), inner_years=3, provinces=PROVINCES,
        features=FEATURES, target=TARGET, age_days=AGE, weather_lag_days=WEATHER_LAG,
        schedule=manifest['schedule'], schedule_sha256=schedule_version(manifest['schedule']),
        manifest_sha256=digest(manifest_path), data_sha256=hashes(),
        production_integrity=verify_production_snapshot(PRODUCTION_SHA256),
        code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in code_files},
        git_head=git('rev-parse', 'HEAD'), git_status=git('status', '--porcelain'),
        python=sys.version, dependencies={p: metadata.version(p) for p in ('numpy', 'pandas', 'scikit-learn', 'catboost')},
        candidates=candidates(), catboost_fixed=dict(iterations=400, loss_function='RMSE',
            boosting_type='Ordered', random_seed=SEED, thread_count=1, allow_writing_files=False),
        selection='Within-family inner MAE only; deterministic candidate-order tie break; no outer target access',
        output_tables=['overall', 'by_year', 'by_province', 'paired_errors', 'wins', 'worst_errors'],
        limitations=['OAE/POWER revised values and publication vintages remain unverified',
            'Calendar created in 2026; not a historically predeclared rule',
            'Future weather is climatology, not historical forecast or future observations',
            'Seven-day POWER latency is assumed', 'All-cultivar annual yield; not Monthong-only',
            '2017-2025 previously inspected; not an independent confirmation set'])


def write_preparation(prepared, config, manifest, run_id, root=OUTPUT_ROOT):
    lexical_root = Path(root).absolute()
    root = lexical_root.resolve()
    if root.name != 'rebaseline_exploratory' or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', run_id):
        raise ValueError('Unsafe experimental output root/run id')
    if not ((root == lexical_root == OUTPUT_ROOT.absolute()) or safe_temporary_root(lexical_root)):
        raise ValueError('Only the designated experimental root or temporary test root is allowed')
    # Resolve symlinks too; refuse a path that lands inside an existing production subtree.
    destination = (root / run_id).resolve()
    if destination.parent != root or destination.exists():
        raise ValueError('Run directory exists or escapes the experimental root')
    root.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    artifacts = dict(config=config, manifest=manifest, feature_lineage=prepared['lineage'],
                     availability=prepared['availability'],
                     source_integrity=prepared.get('source_integrity',{}),
                     folds=[{k: v for k, v in f.items() if not isinstance(v, pd.DataFrame)} for f in prepared['folds']])
    for name, value in artifacts.items():
        with (destination / (name + '.json')).open('x', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
    with (destination / 'predictors.csv').open('x', encoding='utf-8-sig', newline='') as handle:
        prepared['inputs'].to_csv(handle, index=False)
    inventory = {p.name: digest(p) for p in destination.iterdir() if p.is_file()}
    with (destination / 'artifact_hashes.json').open('x', encoding='utf-8') as handle:
        json.dump(inventory, handle, indent=2)
    return destination


def summarize_predictions(frame):
    """For future authorized runs only; tests use synthetic predictions, never fit."""
    required = {'model', 'province_code', 'year_ce', 'actual_kg_rai', 'predicted_kg_rai'}
    expected = {(m, p, y) for m in ('last_year', 'ridge', 'catboost') for p in PROVINCES for y in OUTER_YEARS}
    if not required.issubset(frame) or frame.duplicated(['model', 'province_code', 'year_ce']).any():
        raise ValueError('Incomplete/duplicate prediction columns/keys')
    if set(zip(frame.model, frame.province_code, frame.year_ce)) != expected:
        raise ValueError('Require all 135 predictions on the same 45 keys')
    if not np.isfinite(frame[['actual_kg_rai', 'predicted_kg_rai']].to_numpy(float)).all():
        raise ValueError('Non-finite predictions')
    if frame.groupby(['province_code', 'year_ce']).actual_kg_rai.nunique().ne(1).any():
        raise ValueError('Models must use the same evaluation references')
    result = frame.copy()
    result['error'] = result.predicted_kg_rai - result.actual_kg_rai
    result['absolute_error'] = abs(result.error)
    baseline = result[result.model.eq('last_year')][['province_code', 'year_ce', 'absolute_error']].rename(
        columns={'absolute_error': 'baseline_absolute_error'})
    result = result.merge(baseline, on=['province_code', 'year_ce'], validate='many_to_one')
    result['gain_kg_rai'] = result.baseline_absolute_error - result.absolute_error
    result['outcome'] = np.where(np.isclose(result.gain_kg_rai, 0, atol=1e-9, rtol=0), 'tie',
                                np.where(result.gain_kg_rai > 0, 'win', 'loss'))
    tables = {}
    for name, grouping in [('overall', ['model']), ('by_year', ['model', 'year_ce']),
                           ('by_province', ['model', 'province_code'])]:
        rows = []
        for key, group in result.groupby(grouping):
            key = key if isinstance(key, tuple) else (key,)
            rows.append(dict(zip(grouping, key)) | dict(n=len(group), mae_kg_rai=float(group.absolute_error.mean()),
                rmse_kg_rai=float(np.sqrt((group.error ** 2).mean())), bias_kg_rai=float(group.error.mean()),
                median_absolute_error=float(group.absolute_error.median()),
                wins=int(group.outcome.eq('win').sum()), ties=int(group.outcome.eq('tie').sum()),
                losses=int(group.outcome.eq('loss').sum())))
        tables[name] = pd.DataFrame(rows)
    tables['paired_errors'] = result
    tables['wins'] = tables['overall'][['model', 'wins', 'ties', 'losses']].copy()
    for dimension in ('year', 'province'):
        table = tables['by_' + dimension]
        key = 'year_ce' if dimension == 'year' else 'province_code'
        reference = table[table.model.eq('last_year')].set_index(key).mae_kg_rai
        for model in ('last_year', 'ridge', 'catboost'):
            group = table[table.model.eq(model)]
            gain = group[key].map(reference) - group.mae_kg_rai
            tied = np.isclose(gain, 0, atol=1e-9, rtol=0)
            index = tables['wins'].model.eq(model)
            tables['wins'].loc[index, dimension + '_wins'] = int(((gain > 0) & ~tied).sum())
            tables['wins'].loc[index, dimension + '_ties'] = int(tied.sum())
            tables['wins'].loc[index, dimension + '_losses'] = int(((gain < 0) & ~tied).sum())
    tables['worst_errors'] = result.sort_values('absolute_error', ascending=False).groupby('model').head(5)
    return tables


def prepare(manifest_path=MANIFEST):
    check_snapshot()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    validate_manifest(manifest)
    preflight(manifest, ROOT, FEATURES, PROVINCES, 'exploratory')
    config = configuration(manifest_path, manifest)
    panel = load_panel()
    annual = pd.read_csv(DATA / 'production_annual.csv', dtype={'province_code': str})
    weather = IssueWeather(pd.read_csv(DATA / 'weather_daily.csv', dtype={'province_code': str}).to_dict('records'))
    prepared = prepare_folds(panel, annual, weather, manifest)
    if hashes() != config['data_sha256'] or digest(manifest_path) != config['manifest_sha256']:
        raise ValueError('Dataset/manifest changed during preparation')
    if any(digest(ROOT / path) != value for path, value in config['code_sha256'].items()):
        raise ValueError('Code changed during preparation')
    return prepared, config, manifest


def train_predictions(prepared, config, fitter=None):
    """Choose parameters within each family using inner references, never outer labels."""
    if (config['mode'] != 'exploratory' or config['candidates'] != candidates()
            or config['lead_days'] != LEAD or config['seed'] != SEED
            or config['features'] != FEATURES or config['outer_years'] != list(OUTER_YEARS)):
        raise ValueError('Training must use the frozen exploratory protocol')
    if fitter is None:
        from compare_harvest_stage_yield import fit_predict
        fitter = fit_predict
    folds = {(f['outer_year'], f['fold_year']): f for f in prepared['folds']}
    expected = {(o, y) for o in OUTER_YEARS for y in [*range(o - 3, o), o]}
    if len(prepared['folds']) != 36 or set(folds) != expected:
        raise ValueError('All 36 nested contexts are required before fit')
    predictions, tuning, choices, fit_audit, cache = [], [], [], [], {}

    def predict(fold, index):
        year = fold['fold_year']
        x, forecast, labels = (fold[k] for k in ('train_predictors', 'forecast_predictors', 'training_labels'))
        required = {'province_code', 'year_ce', *FEATURES}
        if set(x) != required or set(forecast) != required or set(labels) != {'province_code', 'year_ce', TARGET}:
            raise ValueError('Invalid predictor/label boundary')
        train = x.merge(labels, on=['province_code', 'year_ce'], validate='one_to_one', sort=False)
        expected_train = {(p, y) for p in PROVINCES for y in range(2010, year)}
        if (set(zip(train.province_code, train.year_ce)) != expected_train or len(train) != len(x)
                or set(zip(forecast.province_code, forecast.year_ce)) != {(p, year) for p in PROVINCES}
                or len(forecast) != 5):
            raise ValueError('Incomplete train/forecast rows; no silent inner join losses')
        signature = digest_value([train.to_dict('records'), forecast.to_dict('records')])
        key = year, index
        reused = key in cache
        if reused and cache[key][0] != signature:
            raise ValueError('Cached inner context differs from current inputs/labels')
        if not reused:
            values = np.asarray(fitter(train, forecast.copy(), PROVINCES, config['candidates'][index]), dtype=float)
            if values.shape != (5,) or not np.isfinite(values).all():
                raise ValueError('Invalid/incomplete estimator output')
            cache[key] = signature, values.copy()
        fit_audit.append(dict(outer_year=fold['outer_year'], fold_year=year, stage=fold['stage'],
            candidate=index, fit_cutoff=fold['fit_cutoff'], training_rows=len(train), forecast_rows=5,
            input_and_training_label_sha256=signature, reused_identical_fit=reused))
        return cache[key][1].copy()

    def reference(fold):
        labels = fold['evaluation_reference']
        if set(labels) != {'province_code', 'year_ce', TARGET}:
            raise ValueError('Invalid evaluation/selection reference schema')
        result = fold['forecast_predictors'][['province_code', 'year_ce']].merge(
            labels, on=['province_code', 'year_ce'], validate='one_to_one', sort=False)
        if len(result) != 5 or not np.isfinite(result[TARGET].to_numpy(float)).all():
            raise ValueError('Incomplete evaluation/selection references')
        return result

    for outer in OUTER_YEARS:
        losses = []
        for index, candidate in enumerate(config['candidates']):
            errors = []
            for year in range(outer - 3, outer):
                fold = folds[outer, year]
                values = predict(fold, index)
                # This reference is used only after prediction, and was audited at outer selection cutoff.
                error = float(np.abs(values - reference(fold)[TARGET].to_numpy(float)).mean())
                errors.append(error)
                tuning.append(dict(outer_year=outer, inner_year=year, candidate=index,
                    model=candidate['group'], parameter=json.dumps(candidate['parameter'], sort_keys=True),
                    inner_mae_kg_rai=error, fit_cutoff=fold['fit_cutoff'], selection_cutoff=fold['selection_cutoff']))
            losses.append(float(np.mean(errors)))
        outer_fold = folds[outer, outer]
        winners = {model: min((i for i, c in enumerate(config['candidates']) if c['group'] == model),
                              key=lambda i: losses[i]) for model in ('last_year', 'ridge', 'catboost')}
        # Freeze all choices and outer predictions before inspecting outer targets.
        estimates = {model: predict(outer_fold, index) for model, index in winners.items()}
        actual = reference(outer_fold)
        for model, index in winners.items():
            choices.append(dict(outer_year=outer, model=model, candidate=index,
                parameter=json.dumps(config['candidates'][index]['parameter'], sort_keys=True),
                inner_mae_kg_rai=losses[index], fit_cutoff=outer_fold['fit_cutoff']))
            for row, value in zip(actual.to_dict('records'), estimates[model]):
                predictions.append(dict(model=model, province_code=row['province_code'], year_ce=outer,
                    actual_kg_rai=row[TARGET], predicted_kg_rai=float(value), candidate=index))
        print(f'Rebaseline: completed outer year {outer}; choices locked from inner MAE', flush=True)
    frame = pd.DataFrame(predictions)
    tables = summarize_predictions(frame)
    tables.update(predictions=frame, tuning=pd.DataFrame(tuning), choices=pd.DataFrame(choices),
                  fit_audit=pd.DataFrame(fit_audit))
    return tables


def train_run(manifest_path=MANIFEST):
    if not production_model_matches():
        raise ValueError('Production hash differs before training')
    prepared, config, manifest = prepare(manifest_path)
    config = dict(config, preparation_only=False, training_requested=True,
                  preflight_tests=dict(python_passed=211, javascript_passed=30,
                      original_python_tests_passed=208, added_training_tests=3),
                  production_before_sha256=digest(PRODUCTION_MODEL))
    # Completion is recorded separately; this immutable config records the pre-fit state.
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if (OUTPUT_ROOT / run_id).exists():
        raise ValueError('New run directory already exists')
    destination = write_preparation(prepared, config, manifest, run_id)
    print(f'Preflight passed; run={destination}; training starts now', flush=True)
    tables = train_predictions(prepared, config)
    if (hashes() != config['data_sha256'] or digest(manifest_path) != config['manifest_sha256']
            or any(digest(ROOT / p) != sha for p, sha in config['code_sha256'].items())
            or not production_model_matches()
            or digest(PRODUCTION_MODEL) != config['production_before_sha256']):
        raise ValueError('Input/code/manifest/production changed during training; results not finalized')
    for name, frame in tables.items():
        with (destination / (name + '.csv')).open('x', encoding='utf-8-sig', newline='') as handle:
            frame.to_csv(handle, index=False)
    status = dict(completed_utc=datetime.now(timezone.utc).isoformat(), mode='exploratory',
                  training_performed=True, pit_certified=False, production_sha256=digest(PRODUCTION_MODEL),
                  predictions=len(tables['predictions']), overall=tables['overall'].to_dict('records'))
    with (destination / 'run_status.json').open('x', encoding='utf-8') as handle:
        json.dump(status, handle, ensure_ascii=False, indent=2, allow_nan=False)
    with (destination / 'completed_artifact_hashes.json').open('x', encoding='utf-8') as handle:
        json.dump({p.name: digest(p) for p in destination.iterdir() if p.is_file()
                   and p.name != 'completed_artifact_hashes.json'}, handle, indent=2)
    print(tables['overall'].to_string(index=False), flush=True)
    print(f'Completed exploratory run: {destination}', flush=True)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Isolated exploratory rebaseline; explicit --train required to fit.')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--prepare', action='store_true', help='Build and audit inputs/folds; never fit a model')
    action.add_argument('--train', action='store_true', help='Run the frozen exploratory nested rebaseline')
    args = parser.parse_args()
    if args.train:
        train_run()
    elif not args.prepare:
        parser.print_help()
    else:
        prepared, config, manifest = prepare()
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        destination = write_preparation(prepared, config, manifest, run_id)
        print(f'Prepared {len(prepared["folds"])} folds; no training performed. {destination}')
