"""Nested year experiment with an issue-date weather cutoff, not forecast vintages.

Unobserved stage weather uses prior-year calendar-day climatology. Targets and
prior yields are the revised local snapshot; historical publication availability
has not been reconstructed. This experiment never replaces the production model.
"""
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import importlib.util
import argparse

from common import *
from analyze_harvest_backcast import month_days
from compare_harvest_stage_yield import daily_vpd, fit_predict
from step5_evaluate_result import paired_year_bootstrap
from availability_guard import preflight

MANIFEST = Path(__file__).with_name('availability_manifest.json')
_OUTPUT_DIR = OUT / 'issue_date_guarded' / 'exploratory'

AGE = 140  # Fixed from the existing model, not selected on this experiment's errors.
HORIZONS = (60, 0)  # Days before the first day of the train-derived main season.
WEATHER_LAG = 7  # Assumed release lag; not a verified NASA publication vintage.
WINDOWS = [(-90, 0, 'rain', 'sum'), (0, 30, 'rain', 'sum'),
           (30, 60, 'rain', 'sum'), (60, 90, 'solar', 'mean'),
           (90, AGE, 'temperature', 'mean'), (-90, 0, 'vpd', 'mean'),
           (0, 30, 'vpd', 'p90')]
PREDICTORS = FEATURES[1:]


def output_json(name, value):
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (_OUTPUT_DIR / ('issue_date_' + name)).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def output_csv(name, frame):
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(_OUTPUT_DIR / ('issue_date_' + name), index=False, encoding='utf-8-sig')


def stage_feature(values, observed, normals, reducer):
    """Future entries cannot affect the result, even if stored source values exist."""
    values, observed, normals = np.asarray(values), np.asarray(observed, bool), np.asarray(normals)
    if values.shape != observed.shape or values.shape != normals.shape or values.ndim != 2:
        raise ValueError('Require matching cohort-by-day arrays')
    mixed = np.where(observed, values, normals)
    if not np.isfinite(mixed).all():
        raise ValueError('Missing observed weather or climatology; no zero filling')
    if reducer == 'sum':
        value = mixed.sum(axis=1).mean()
    elif reducer == 'mean':
        value = mixed.mean()
    elif reducer == 'p90':
        value = np.quantile(mixed, .9)
    else:
        raise ValueError('Unknown reducer')
    return float(value), float(observed.mean())


class IssueWeather:
    def __init__(self, raw):
        frame = pd.DataFrame(raw)
        if frame.duplicated(['province_code', 'date']).any():
            raise ValueError('Duplicate daily weather')
        frame['date'] = pd.to_datetime(frame.date)
        frame['year'] = frame.date.dt.year
        frame['calendar_day'] = frame.date.dt.strftime('%m-%d')
        for field in ['T2M', 'T2M_MIN', 'T2M_MAX', 'RH2M', 'PRECTOTCORR', 'ALLSKY_SFC_SW_DWN']:
            frame[field] = pd.to_numeric(frame[field].replace('', np.nan), errors='raise')
        frame['vpd'] = daily_vpd(frame.T2M_MIN, frame.T2M_MAX, frame.RH2M)
        frame = frame.rename(columns={'T2M': 'temperature', 'PRECTOTCORR': 'rain',
                                      'ALLSKY_SFC_SW_DWN': 'solar'})
        self.frame = frame
        self.columns = ['rain', 'solar', 'temperature', 'vpd']
        self.series = {}
        for code, group in frame.groupby('province_code'):
            first, last = group.date.min(), group.date.max()
            daily = group.set_index('date').reindex(pd.date_range(first, last))
            self.series[code] = first.date().toordinal(), daily[self.columns].to_numpy(float)

    @lru_cache(maxsize=None)
    def normal(self, code, year):
        # Every historical row's normal excludes its own year and all later years.
        history = self.frame[self.frame.province_code.eq(code) & self.frame.year.between(year - 10, year - 1)]
        counts = history.groupby('calendar_day')[self.columns].count()
        normals = history.groupby('calendar_day')[self.columns].mean()
        if normals.empty or (counts.loc[counts.index != '02-29'] < 8).any().any():
            raise ValueError('Insufficient prior-year normal coverage')
        # Explicit February 29 rule; no future source is consulted.
        normals.loc['02-29'] = (normals.loc['02-28'] + normals.loc['03-01']) / 2
        return normals

    def features(self, code, year, months, lead):
        # Keep the original four-item return and coverage schema for existing callers.
        return self._features(code, year, months, lead, False)

    def features_with_lineage(self, code, year, months, lead):
        """Same builder, with provenance captured from the arrays actually consumed."""
        return self._features(code, year, months, lead, True)

    def _features(self, code, year, months, lead, trace):
        days = [d for month in months for d in month_days(year, month)]
        issue = min(days) - timedelta(days=lead)
        available = issue - timedelta(days=WEATHER_LAG)
        first, matrix = self.series[code]
        normal = self.normal(code, year)
        features, coverage = {}, []
        for name, (start, stop, field, reducer) in zip(PREDICTORS, WINDOWS):
            ordinals = np.array([d.toordinal() for d in days])[:, None] - AGE + np.arange(start, stop)
            indexes = ordinals - first
            observed = ordinals <= available.toordinal()
            source = np.full(indexes.shape, np.nan)
            in_range = (indexes >= 0) & (indexes < len(matrix)) & observed
            source[in_range] = matrix[indexes[in_range], self.columns.index(field)]
            calendar_days = [date.fromordinal(int(n)).strftime('%m-%d') for n in ordinals.ravel()]
            scenario = normal.loc[calendar_days, field].to_numpy().reshape(indexes.shape)
            features[name], fraction = stage_feature(source, observed, scenario, reducer)
            item = dict(feature=name, observed_fraction=fraction, climatology_fraction=1 - fraction)
            if trace:
                used = sorted(set(int(n) for n in ordinals[observed]))
                observed_inputs = [(date.fromordinal(n).isoformat(),
                                    float(matrix[n - first, self.columns.index(field)])) for n in used]
                keys = sorted(set(np.asarray(calendar_days).reshape(indexes.shape)[~observed].tolist()))
                raw_keys = set(keys)
                if '02-29' in raw_keys:
                    raw_keys.remove('02-29')
                    raw_keys.update(('02-28', '03-01'))
                history = self.frame[self.frame.province_code.eq(code)
                    & self.frame.year.between(year - 10, year - 1)
                    & self.frame.calendar_day.isin(raw_keys) & self.frame[field].notna()].sort_values('date')
                normal_inputs = [(d.date().isoformat(), float(v)) for d, v in zip(history.date, history[field])]
                components = ['T2M_MIN', 'T2M_MAX', 'RH2M'] if field == 'vpd' else [field]
                observed_raw = self.frame[self.frame.province_code.eq(code)
                    & self.frame.date.isin(pd.to_datetime([d for d, _ in observed_inputs]))].sort_values('date')
                raw_digest = lambda frame: hashlib.sha256(json.dumps([
                    [r['date'].date().isoformat(), *[float(r[c]) for c in components]]
                    for r in frame.to_dict('records')]).encode()).hexdigest()
                item.update(source_field=field, reducer=reducer, value=features[name],
                    source_columns=({'rain': ['PRECTOTCORR'], 'solar': ['ALLSKY_SFC_SW_DWN'],
                                     'temperature': ['T2M'], 'vpd': components}[field]),
                    observed_raw_components_sha256=raw_digest(observed_raw),
                    normal_raw_components_sha256=raw_digest(history),
                    observed_dates=[d for d, _ in observed_inputs],
                    observed_values_sha256=hashlib.sha256(json.dumps(observed_inputs).encode()).hexdigest(),
                    normal_dates=[d for d, _ in normal_inputs], normal_calendar_days=keys,
                    normal_values_sha256=hashlib.sha256(json.dumps(normal_inputs).encode()).hexdigest(),
                    cohort_days=len(days), window_days=stop - start,
                    observed_cells=int(observed.sum()), climatology_cells=int((~observed).sum()),
                    normal_cell_values={k: float(normal.loc[k, field]) for k in keys},
                    normal_years=[year - 10, year - 1], feb29_rule='mean of Feb28 and Mar01')
            coverage.append(item)
        return features, issue, available, coverage


def configurations():
    configs = [dict(kind='previous_year', parameter=None, features=[], group='lag'),
               dict(kind='province_median', parameter=None, features=[], group='median')]
    for group, columns in [('lag_ridge', [FEATURES[0]]), ('stage_ridge', FEATURES)]:
        configs += [dict(kind='ridge', parameter=alpha, features=columns, group=group)
                    for alpha in (1., 10., 100.)]
    configs += [dict(kind='random_forest', parameter=leaf, features=FEATURES, group='stage_rf')
                for leaf in (3, 5)]
    if importlib.util.find_spec('catboost'):
        configs += [dict(kind='catboost', parameter=dict(depth=depth, l2_leaf_reg=10,
                       learning_rate=.03), features=FEATURES, group='stage_catboost') for depth in (2, 3)]
    return configs


def score(actual, predicted):
    result = metrics(actual, predicted)
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    denominator = float(np.abs(actual).sum())
    spread = float(((actual - actual.mean()) ** 2).sum())
    result['wape_pct'] = float(100 * np.abs(predicted - actual).sum() / denominator) if denominator else None
    result['r2'] = float(1 - ((predicted - actual) ** 2).sum() / spread) if spread else None
    return result


def prior_interval(previous, year, level=.8):
    """Descriptive max-residual year bands, using only preceding prediction errors."""
    old = previous[(previous.year_ce < year) & (previous.year_ce >= year - 5)].copy()
    if old.empty:
        return None
    old['error'] = abs(old.predicted_kg_rai - old.actual_kg_rai)
    maxima = old.groupby('year_ce').error.max().to_numpy()
    rank = int(np.ceil((len(maxima) + 1) * level))
    if len(maxima) < 5 or rank > len(maxima):
        return None
    return float(np.sort(maxima)[rank - 1])


def prediction_inputs(frame):
    return frame[['province_code', 'year_ce', *FEATURES]].copy()


def run(mode='exploratory', manifest_path=MANIFEST, preflight_only=True):
    global _OUTPUT_DIR
    check_snapshot()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    availability = preflight(manifest, ROOT, FEATURES, PROVINCES, mode)
    _OUTPUT_DIR = OUT / 'issue_date_guarded' / mode
    output_json('availability.json', availability)
    if preflight_only:
        print(f'{mode}: {len(availability["checks"])} dependency checks; no training performed')
        return availability
    base = load_panel()
    seasons = {code: list(range(int(anchor[:2]), int(anchor[:2]) + 3))
               for code, anchor in manifest['schedule']['anchors'].items()}
    if any(months[-1] > 12 for months in seasons.values()):
        raise ValueError('Fixed experimental season exceeds calendar year')
    config = dict(created_utc=datetime.now(timezone.utc).isoformat(), target=TARGET,
        independent_rows=len(base), years=[2010, 2025], provinces=PROVINCES,
        outer_years=list(range(2017, 2026)), inner_years=3, age_days=AGE,
        leads_days_before_main_season=list(HORIZONS), weather_release_lag_days=WEATHER_LAG,
        mode=mode, score_label='Exploratory retrospective score; not PIT-certified',
        schedule=manifest['schedule'], availability_manifest_sha256=hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
        future_weather='calendar-day means from 10 preceding years; VPD mean of daily VPD',
        selection='all families and parameters selected by earlier-year inner MAE only',
        missing_package='XGBoost not installed; not downloaded for this experiment',
        input_sha256=hashes(), limitations=[
            'Revised annual target and lag snapshots; historical release vintages unverified',
            'Climatology scenario is not an archived numerical weather forecast',
            'Seven-day weather release lag is an assumption, not validated source latency',
            'One reference weather grid per province, no bearing-orchard weights',
            'All cultivars; main-season proxy does not isolate Monthong targets',
            'Annual targets include off-season production outside the main-season proxy',
            '2017-2025 previously inspected; exploratory, not a new independent holdout'])
    config['candidates'] = configurations()
    output_json('plan.json', config)
    weather = IssueWeather(read_csv(DATA / 'weather_daily.csv'))
    contexts, cache = [], {}

    @lru_cache(maxsize=None)
    def frame_for(cutoff, lead):
        signature = tuple((code, tuple(months)) for code, months in seasons.items())
        key = signature, lead
        if key not in cache:
            rows = []
            for row in base.to_dict('records'):
                values, issue, available, coverage = weather.features(row['province_code'], row['year_ce'],
                                                                      seasons[row['province_code']], lead)
                rows.append(dict(**row, **values))
                contexts.extend(dict(province_code=row['province_code'], year_ce=row['year_ce'],
                    season_signature=str(signature), lead_days=lead, issue_date=issue.isoformat(),
                    weather_available_through=available.isoformat(), normal_end_year=row['year_ce'] - 1,
                    **item) for item in coverage)
            cache[key] = pd.DataFrame(rows)
        return cache[key]

    predictions, tuning, choices = [], [], []
    for lead in HORIZONS:
        estimates = {}
        def predict_year(year, index):
            key = year, index
            if key not in estimates:
                frame = frame_for(year - 1, lead)
                train, test = frame[frame.year_ce.lt(year)], frame[frame.year_ce.eq(year)]
                # Evaluation targets must never be passed into the predictor frame.
                estimates[key] = fit_predict(train, prediction_inputs(test), PROVINCES, config['candidates'][index])
            return estimates[key]
        for year in range(2017, 2026):
            inner = []
            for i, candidate in enumerate(config['candidates']):
                loss = [mae(base.loc[base.year_ce.eq(v), TARGET], predict_year(v, i))
                        for v in range(year - 3, year)]
                inner.append(float(np.mean(loss)))
                tuning.append(dict(lead_days=lead, test_year=year, candidate=i,
                                   group=candidate['group'], inner_mae_kg_rai=inner[-1]))
            groups = sorted({c['group'] for c in config['candidates']})
            winners = {group: min((i for i, c in enumerate(config['candidates']) if c['group'] == group),
                                 key=lambda i: inner[i]) for group in groups}
            winners['inner_selected'] = int(np.argmin(inner))
            test = frame_for(year - 1, lead).query('year_ce == @year')
            for policy, i in winners.items():
                choices.append(dict(lead_days=lead, year_ce=year, policy=policy,
                                    candidate=i, group=config['candidates'][i]['group'], inner_mae=inner[i]))
                for actual, value in zip(test.to_dict('records'), predict_year(year, i)):
                    predictions.append(dict(lead_days=lead, policy=policy, year_ce=year,
                        province_code=actual['province_code'], actual_kg_rai=actual[TARGET],
                        predicted_kg_rai=float(value), previous_year_kg_rai=actual['previous_yield_kg_rai']))
            print(f'Issue-date experiment: lead={lead}, test={year}, selected={winners["inner_selected"]}', flush=True)
    frame = pd.DataFrame(predictions)
    summaries = [dict(lead_days=lead, policy=policy, **score(group.actual_kg_rai, group.predicted_kg_rai))
                 for (lead, policy), group in frame.groupby(['lead_days', 'policy'])]
    summary = pd.DataFrame(summaries)
    result = dict(plan=config, overall=summaries, by_province=[], by_year=[], paired_uncertainty={},
                  intervals='80% nominal descriptive bands: max absolute error across five provinces per prior year; five prior years; no coverage guarantee under dependence/shift')
    for dimension in ('province_code', 'year_ce'):
        result['by_province' if dimension == 'province_code' else 'by_year'] = [
            dict(lead_days=lead, policy=policy, **{dimension:str(value)},
                 **score(group.actual_kg_rai, group.predicted_kg_rai))
            for (lead, policy, value), group in frame.groupby(['lead_days', 'policy', dimension])]
    bands = []
    for lead in HORIZONS:
        selected = frame[frame.lead_days.eq(lead) & frame.policy.eq('inner_selected')]
        result['paired_uncertainty'][str(lead)] = paired_year_bootstrap(selected, 'previous_year_kg_rai')[0]
        for row in selected.to_dict('records'):
            radius = prior_interval(selected, row['year_ce'])
            if radius is not None:
                lower, upper = max(0., row['predicted_kg_rai'] - radius), row['predicted_kg_rai'] + radius
                bands.append(dict(**row, lower_kg_rai=lower, upper_kg_rai=upper,
                                  covered=lower <= row['actual_kg_rai'] <= upper))
    result['interval_rows'] = len(bands)
    result['interval_coverage_pct'] = 100 * np.mean([r['covered'] for r in bands]) if bands else None
    output_csv('predictions.csv', frame)
    output_csv('tuning.csv', pd.DataFrame(tuning))
    output_csv('choices.csv', pd.DataFrame(choices))
    output_csv('weather_context.csv', pd.DataFrame(contexts))
    output_csv('summary.csv', summary)
    output_csv('intervals.csv', pd.DataFrame(bands))
    output_json('results.json', result)
    print(summary.to_string(index=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Experimental availability preflight; training requires --train')
    parser.add_argument('--mode', choices=('exploratory', 'strict'), default='exploratory')
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--train', action='store_true', help='Explicit opt-in; otherwise only validate availability')
    args = parser.parse_args()
    run(args.mode, args.manifest, preflight_only=not args.train)
