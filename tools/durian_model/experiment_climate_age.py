"""Nested rolling-year test of climate-adjusted backcast windows, not fruit-age labels."""
from datetime import date
from itertools import product

from common import *
from analyze_harvest_backcast import exposure, month_days
from compare_harvest_stage_yield import vpd_window
from step5_evaluate_result import paired_year_bootstrap

AGE_GRID = tuple(range(110, 161, 5))
AMPLITUDES = (5, 10)
CLIMATE_FIELDS = ('reference_temperature_c', 'reference_rain_mm', 'reference_solar_mj_m2_day')
STRATEGIES = ('fixed_original', 'fixed_expanded', 'enso_age', 'local_age', 'enso_local_age', 'inner_selected')
KEYS = ['province_code', 'year_ce']


def candidates():
    configs = [dict(kind='fixed', base_age=age, amplitude=0, alpha=alpha)
               for age, alpha in product(AGE_GRID, ALPHAS)]
    configs += [dict(kind=kind, base_age=age, amplitude=amp, alpha=alpha)
                for kind, age, amp, alpha in product(
                    ('enso', 'heat', 'wet', 'local', 'enso_local'), AGES, AMPLITUDES, ALPHAS)]
    return [dict(config, config_id=i) for i, config in enumerate(configs)]


def belongs(config, strategy):
    original = config['kind'] == 'fixed' and config['base_age'] in AGES
    return {
        'fixed_original': original,
        'fixed_expanded': config['kind'] == 'fixed',
        'enso_age': original or config['kind'] == 'enso',
        'local_age': original or config['kind'] in ('heat', 'wet', 'local'),
        'enso_local_age': original or config['kind'] == 'enso_local',
        'inner_selected': True,
    }[strategy]


def completed_index_key(day):
    """Lag center month by two: its three-month season ends before this day/month."""
    ordinal = day.year * 12 + day.month - 1 - 2
    year, month = divmod(ordinal, 12)
    return year, month + 1


def roni_series(weather, records):
    observed = [r for r in records if r['index'] == 'RONI']
    mapping = {(int(r['year_ce']), int(r['center_month'])): float(r['anomaly_c']) for r in observed}
    if len(mapping) != len(observed) or not mapping or not np.isfinite(list(mapping.values())).all():
        raise ValueError('Invalid or duplicate RONI history')
    series = {}
    for code, (first, last, _) in weather.items():
        values = np.array([mapping.get(completed_index_key(date.fromordinal(n)), np.nan)
                           for n in range(first, last + 1)])
        series[code] = first, values
    return series


def reference_stats(context, cutoff):
    train = context[context.year_ce.le(cutoff)]
    reference = {}
    for code, group in train.groupby('province_code'):
        if len(group) < 4 or not np.isfinite(group[list(CLIMATE_FIELDS)]).all().all():
            raise ValueError('Need at least four complete prior climate years per province')
        reference[code] = dict(train_end=int(group.year_ce.max()), rows=len(group),
            mean=group[list(CLIMATE_FIELDS)].mean().to_dict(),
            scale=group[list(CLIMATE_FIELDS)].std(ddof=0).replace(0, 1).to_dict())
    if set(reference) != set(context.province_code):
        raise ValueError('Missing province climate reference')
    return reference


def climate_values(context, reference):
    values = context[list(CLIMATE_FIELDS)].to_numpy(float)
    means = np.array([[reference[code]['mean'][f] for f in CLIMATE_FIELDS] for code in context.province_code])
    scales = np.array([[reference[code]['scale'][f] for f in CLIMATE_FIELDS] for code in context.province_code])
    if not np.isfinite(values).all() or not np.isfinite(scales).all() or (scales <= 0).any():
        raise ValueError('Invalid climate normalization')
    return (values - means) / scales


def ages_for(context, reference, config):
    if config['kind'] == 'fixed':
        return np.full(len(context), config['base_age'], dtype=int)
    z = climate_values(context, reference)
    heat = np.clip(z[:, 0], -1, 1)
    wet = np.clip((z[:, 1] - z[:, 2]) / 2, -1, 1)
    enso = np.clip(context.reference_roni_c.to_numpy(float), -1, 1)
    # Hypotheses: warmer shortens, wetter/cloudier lengthens; zero-shift controls remain candidates.
    drivers = dict(enso=-enso, heat=-heat, wet=wet,
                   local=(wet - heat) / 2, enso_local=(wet - heat - enso) / 3)
    shift = config['amplitude'] * drivers[config['kind']]
    if not np.isfinite(shift).all():
        raise ValueError('Missing climate driver; do not classify it as normal')
    adjusted = config['base_age'] + 5 * np.rint(shift / 5)
    return np.clip(adjusted, min(AGE_GRID), max(AGE_GRID)).astype(int)


def build_bank(base, seasons, weather, vpd, roni):
    context, features = [], {age: [] for age in AGE_GRID}
    for record in base.itertuples():
        code, year = record.province_code, int(record.year_ce)
        days = [d for month in seasons[code] for d in month_days(year, month)]
        climate = exposure(weather[code], days, 120, 0, 120)
        roni_mean, _ = vpd_window(roni[code], days, 120, 0, 120)
        context.append(dict(province_code=code, province_name=record.province_name, year_ce=year,
            reference_temperature_c=climate['temperature_c'], reference_rain_mm=climate['rain_mm'],
            reference_solar_mj_m2_day=climate['solar_mj_m2_day'], reference_roni_c=roni_mean,
            season_months=','.join(map(str, seasons[code])),
            reference_period_start=date.fromordinal(days[0].toordinal() - 120).isoformat(),
            reference_period_end=date.fromordinal(days[-1].toordinal() - 1).isoformat()))
        for age in AGE_GRID:
            values = {'previous_yield_kg_rai': record.previous_yield_kg_rai}
            for label, field, start, stop in (
                ('pre_bloom_90d', 'rain_mm', -90, 0),
                ('fruit_0_29d', 'rain_mm', 0, 30),
                ('fruit_30_59d', 'rain_mm', 30, 60),
                ('fruit_60_89d', 'solar_mj_m2_day', 60, 90),
                ('fruit_90_to_harvest', 'temperature_c', 90, age)):
                values[f'{label}_{field}'] = exposure(weather[code], days, age, start, stop)[field]
            values[VPD_STAGE_FEATURES[0]], _ = vpd_window(vpd[code], days, age, -90, 0)
            _, values[VPD_STAGE_FEATURES[1]] = vpd_window(vpd[code], days, age, 0, 30)
            features[age].append([values[f] for f in FEATURES])
    context = pd.DataFrame(context)
    arrays = np.array([features[age] for age in AGE_GRID], dtype=float)
    if not np.isfinite(arrays).all() or not np.isfinite(context[[*CLIMATE_FIELDS, 'reference_roni_c']]).all().all():
        raise ValueError('Incomplete stage weather or ENSO window; no imputation')
    return context, arrays


def fit_predict_arrays(base, bank, context, reference, config, year):
    ages = ages_for(context, reference, config)
    chosen = bank[(ages - min(AGE_GRID)) // 5, np.arange(len(base)), :]
    x = np.column_stack([*(base.province_code.eq(p).to_numpy(float) for p in PROVINCES),
                         base.year_ce.to_numpy(float), chosen])
    train, test = base.year_ce.lt(year).to_numpy(), base.year_ce.eq(year).to_numpy()
    if not train.any() or base.loc[train, 'year_ce'].max() >= year:
        raise ValueError('Training must precede prediction year')
    model = fit_ridge(x[train], base.loc[train, TARGET].to_numpy(float), config['alpha'])
    predictions = predict(model, x[test])
    return predictions, ages[test], model


def run():
    check_snapshot()
    old_hash = hashlib.sha256((OUT / 'ridge_vpd_predictions.csv').read_bytes()).hexdigest()
    base = load_panel().sort_values(['year_ce', 'province_code']).reset_index(drop=True)
    harvest = pd.read_csv(DATA / 'harvest_monthly.csv', dtype={'province_code': str})
    if (harvest.duplicated(['province_code', 'year_ce', 'month_number']).any()
            or not harvest.month_number.between(1, 12).all()
            or not np.isfinite(harvest.tonnes).all() or (harvest.tonnes < 0).any()):
        raise ValueError('Invalid monthly harvest')
    harvest = harvest[harvest.year_ce.ge(2010)]
    enso_path = DATA / 'enso_context.json'
    enso = json.loads(enso_path.read_text(encoding='utf-8'))
    for source in enso['sources'].values():
        if hashlib.sha256((ROOT / source['snapshot']).read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('ENSO raw snapshot does not match provenance')
    raw = read_csv(DATA / 'weather_daily.csv')
    weather, vpd = weather_series(raw), vpd_series(raw)
    roni = roni_series(weather, enso['observed'])
    configs = candidates()
    bank_cache, cutoff_cache, prediction_cache = {}, {}, {}

    def for_cutoff(cutoff):
        if cutoff not in cutoff_cache:
            seasons = training_seasons(harvest, cutoff)
            signature = tuple((p, tuple(seasons[p])) for p in PROVINCES)
            if signature not in bank_cache:
                print('Building stage/weather bank:', seasons, flush=True)
                bank_cache[signature] = build_bank(base, seasons, weather, vpd, roni)
            context, bank = bank_cache[signature]
            cutoff_cache[cutoff] = (context, bank, reference_stats(context, cutoff), seasons)
        return cutoff_cache[cutoff]

    def predict_year(year, config):
        key = year, config['config_id']
        if key not in prediction_cache:
            context, bank, reference, _ = for_cutoff(year - 1)
            estimates, ages, model = fit_predict_arrays(base, bank, context, reference, config, year)
            test = base[base.year_ce.eq(year)]
            error = mae(test[TARGET], estimates) if len(test) else None
            prediction_cache[key] = estimates, ages, model, error
        return prediction_cache[key]

    predictions, tuning, contexts, choices = [], [], [], []
    final = None
    for year in range(2017, 2027):
        scores = []
        for config in configs:
            score = float(np.mean([predict_year(y, config)[3] for y in range(year - 3, year)]))
            scores.append((score, config))
            tuning.append(dict(test_year=year, inner_mae_kg_rai=score, **config))
        context, _, reference, seasons = for_cutoff(year - 1)
        for strategy in STRATEGIES:
            score, config = min((s for s in scores if belongs(s[1], strategy)), key=lambda s: s[0])
            estimates, ages, model, _ = predict_year(year, config)
            choices.append(dict(strategy=strategy, test_year=year, inner_mae_kg_rai=score, **config))
            if year == 2026:
                if strategy == 'inner_selected':
                    final = dict(config=config, inner_mae_kg_rai=score, parameters=model,
                        train_start=2010, train_end=2025, feature_names=feature_names(),
                        climate_reference=reference, season_months=seasons,
                        mode='Requires complete future observed/scenario stage weather; not a live prediction')
                continue
            test = base[base.year_ce.eq(year)]
            for record, estimate, age in zip(test.itertuples(), estimates, ages):
                predictions.append(dict(strategy=strategy, province_code=record.province_code,
                    province_name=record.province_name, year_ce=year,
                    actual_kg_rai=getattr(record, TARGET), predicted_kg_rai=float(estimate),
                    previous_year_kg_rai=record.previous_yield_kg_rai,
                    adjusted_age_days=int(age), age_shift_days=int(age - config['base_age']),
                    inner_mae_kg_rai=score, **config))
            if strategy == 'inner_selected':
                detail = context[context.year_ce.eq(year)].copy()
                z = climate_values(detail, reference)
                for i, f in enumerate(('temperature_z', 'rain_z', 'solar_z')):
                    detail[f] = z[:, i]
                detail['local_temperature_label'] = np.where(z[:, 0] >= 1, 'hotter', np.where(z[:, 0] <= -1, 'cooler', 'near_reference'))
                detail['local_rain_label'] = np.where(z[:, 1] >= 1, 'wetter', np.where(z[:, 1] <= -1, 'drier', 'near_reference'))
                detail['enso_window_proxy'] = np.where(detail.reference_roni_c >= .5, 'warm',
                    np.where(detail.reference_roni_c <= -.5, 'cold', 'neutral'))
                detail['climate_reference_train_end'] = year - 1
                detail['adjusted_age_days'] = ages
                detail['recipe'] = config['kind']
                detail['base_age_days'] = config['base_age']
                contexts.append(detail)
        print('Completed outer year:', year, flush=True)
    frame = pd.DataFrame(predictions)
    old = load_csv('predictions.csv')
    original = frame[frame.strategy.eq('fixed_original')].merge(old, on=KEYS, validate='one_to_one', suffixes=('', '_old'))
    if (len(original) != 45 or not np.allclose(original.predicted_kg_rai, original.predicted_kg_rai_old, atol=1e-7, rtol=1e-10)
            or not np.allclose(original.actual_kg_rai, original.actual_kg_rai_old)):
        raise ValueError('Original control must reproduce all 45 saved predictions')
    results = []
    for strategy in STRATEGIES:
        selected = frame[frame.strategy.eq(strategy)]
        if len(selected) != 45 or selected.duplicated(KEYS).any():
            raise ValueError('Expected 45 paired province-years per strategy')
        paired = selected.merge(original[KEYS + ['predicted_kg_rai']], on=KEYS,
                                validate='one_to_one', suffixes=('', '_original'))
        uncertainty, _ = paired_year_bootstrap(paired, 'predicted_kg_rai_original')
        results.append(dict(strategy=strategy, **metrics(selected.actual_kg_rai, selected.predicted_kg_rai),
            recent_2020_2025=metrics(selected[selected.year_ce.ge(2020)].actual_kg_rai,
                                     selected[selected.year_ce.ge(2020)].predicted_kg_rai),
            paired_uncertainty_vs_original=uncertainty,
            by_year=[dict(year_ce=int(y), **metrics(g.actual_kg_rai, g.predicted_kg_rai))
                     for y, g in selected.groupby('year_ce')],
            by_province=[dict(province_code=p, **metrics(g.actual_kg_rai, g.predicted_kg_rai))
                         for p, g in selected.groupby('province_code')]))
    if hashlib.sha256((OUT / 'ridge_vpd_predictions.csv').read_bytes()).hexdigest() != old_hash:
        raise ValueError('Original predictions changed during the experiment')
    result = dict(model='Ridge + VPD with climate-adjusted backcast scenarios', results=results,
        baseline_reproduced=True, original_artifacts_unchanged=True, final_inner_selected_model=final,
        candidate_count=len(configs), configurations=configs, fold_choices=choices,
        grid=dict(ages=list(AGE_GRID), base_adaptive_ages=list(AGES), shift_amplitudes=list(AMPLITUDES),
                  alphas=list(ALPHAS), max_shift_days=10, rounding_days=5),
        target='All-cultivar production tonnes * 1000 / bearing rai', independent_targets=80,
        test_years=list(range(2017, 2026)), test_rows_per_strategy=45,
        enso_source_sha256=hashlib.sha256(enso_path.read_bytes()).hexdigest(), input_sha256=hashes(),
        code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in [Path(__file__), Path(__file__).parent / 'common.py',
                               ROOT / 'tools/fetch_enso_context.py', ROOT / 'tools/analyze_harvest_backcast.py',
                               ROOT / 'tools/compare_harvest_stage_yield.py', ROOT / 'tools/train_monthly_production.py',
                               Path(__file__).parent / 'step5_evaluate_result.py']},
        methods=[
            'Three peak-season months learned from earlier production only; dominant-cultivar proxy, not proven Monthong-only harvest.',
            'Climate driver: fixed 120-day pre-harvest exposure, equally averaged over possible harvest days.',
            'Local temperature/rain/solar standardized separately by province using only prior training years.',
            'Wet/cloudy driver = clipped (rain_z - solar_z)/2. Heat and RONI drivers clipped to [-1,1].',
            'ENSO driver uses RONI of the last calendar-completed three-month season for each exposure day.',
            'Age hypotheses: heat or positive RONI shortens; wet/cloudy lengthens. Zero shift is an eligible control.',
            'ENSO-local driver = (wet - heat - RONI)/3. Local driver = (wet - heat)/2.',
            'Base 120/130/140/150 days, amplitude 5/10; round shifts to nearest 5 days, clip ages 110-160.',
            'All coefficients, age recipes, seasons, normalizers and alpha chosen on earlier years; three-year inner validation.',
            'Independent fixed-expanded control tests whether merely widening the age grid helps.',
            'Future ENSO probabilities downloaded separately and NEVER used to reconstruct past test inputs.'],
        limitations=[
            'Exploratory comparison on previously examined 2017-2025 targets; no new confirmatory holdout or preregistration claim.',
            '153 configurations and six policies increase selection opportunity; inner tuning reduces but does not remove small-sample instability.',
            'Only 80 province-year targets. Daily and candidate exposure rows do not increase target sample size.',
            'NOAA indices are revised snapshots; calendar-completed seasons do not prove historical publication-time availability.',
            'Peak season, duration and climate shifts are feature scenarios, not observed flowering dates or measured fruit ages.',
            'No measured historical cultivar mix; Monthong proxy does not turn the target into Monthong-only yield.',
            'NASA POWER reference point is not bearing-area weighted provincial weather.',
            'Observed pre-harvest weather conditions, not operational seasonal weather forecasts.',
            'Bootstrap ranges condition on fixed predictions; nine year clusters, no refitting or model-selection correction.',
            'No main model/report/dashboard automatically replaced; no live yield prediction generated.'])
    OUT.mkdir(exist_ok=True)
    for name, data in [('predictions.csv', frame), ('tuning.csv', pd.DataFrame(tuning)),
                       ('context.csv', pd.concat(contexts, ignore_index=True))]:
        data.to_csv(OUT / ('climate_age_' + name), index=False, encoding='utf-8-sig')
    (OUT / 'climate_age_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                                           allow_nan=False), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7))
    labels = [r['strategy'] for r in results]
    bars = axes[0].barh(labels, [r['mae_kg_rai'] for r in results], color=['#64748b', '#94a3b8', '#7c3aed', '#0891b2', '#2563eb', '#d97706'])
    axes[0].bar_label(bars, fmt='%.2f', padding=3, fontsize=8)
    axes[0].set_xlim(0, 220)
    axes[0].set(xlabel='MAE kg/rai (lower is better)', title='Exploratory rolling-year comparison')
    for strategy in ('fixed_original', 'enso_local_age', 'inner_selected'):
        selected = frame[frame.strategy.eq(strategy)]
        annual = selected.groupby('year_ce').apply(lambda g: mae(g.actual_kg_rai, g.predicted_kg_rai))
        axes[1].plot(annual.index, annual, marker='o', label=strategy)
    axes[1].set(xlabel='Test year', ylabel='MAE kg/rai', title='Year-level errors, five provinces each')
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / 'climate_age_comparison.png', dpi=160)
    plt.close(fig)
    print(pd.DataFrame(results)[['strategy', 'mae_kg_rai', 'rmse_kg_rai']].to_string(index=False))
    return result


if __name__ == '__main__':
    run()
