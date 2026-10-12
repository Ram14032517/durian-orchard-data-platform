"""Exploratory nested-year test of short weather extremes; not disaster labels."""
from itertools import product
from datetime import date

from common import *
from analyze_harvest_backcast import month_days
from step5_evaluate_result import paired_year_bootstrap

KEYS = ['province_code', 'year_ce']
DRY_HEAT = ['pre_bloom_cdd_days', 'early_fruit_cdd_days', 'early_fruit_hot35_days',
            'early_fruit_hot38_days', 'early_fruit_hot35_run_days']
WET = ['fruit_rx3day_mm', 'fruit_rx7day_mm']
SHOCKS = DRY_HEAT + WET
GROUPS = {'baseline': [], 'dry_heat': DRY_HEAT, 'heavy_rain': WET, 'all_shocks': SHOCKS}


def longest_run(mask):
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 2 or mask.shape[1] == 0:
        raise ValueError('Require nonempty cohort-by-day matrix')
    current = np.zeros(len(mask), dtype=int)
    longest = current.copy()
    for column in mask.T:
        current = np.where(column, current + 1, 0)
        longest = np.maximum(longest, current)
    return longest


def window(first, values, days, age, start, stop):
    indexes = np.array([d.toordinal() for d in days])[:, None] - age + np.arange(start, stop) - first
    if not len(days) or stop <= start or (indexes < 0).any() or (indexes >= len(values)).any():
        raise ValueError('Weather window outside source coverage')
    selected = values[indexes]
    if not np.isfinite(selected).all():
        raise ValueError('Incomplete weather; no missing-to-zero conversion')
    return selected


def shock_values(first, rain, tmax, days, age):
    if (not isinstance(age, int) or age < 30 or (np.asarray(rain)[np.isfinite(rain)] < 0).any()
            or np.any(np.isfinite(tmax) & ((tmax < -100) | (tmax > 70)))):
        raise ValueError('Invalid weather or age')
    pre = window(first, rain, days, age, -90, 0)
    early = window(first, rain, days, age, 0, 30)
    hot = window(first, tmax, days, age, 0, 30)
    fruit = window(first, rain, days, age, 0, age)
    values = [longest_run(pre < 1).mean(), longest_run(early < 1).mean(),
              (hot > 35).sum(axis=1).mean(), (hot > 38).sum(axis=1).mean(),
              longest_run(hot > 35).mean()]
    for width in (3, 7):
        rolling = np.lib.stride_tricks.sliding_window_view(fruit, width, axis=1).sum(axis=-1)
        values.append(rolling.max(axis=1).mean())
    return dict(zip(SHOCKS, map(float, values)))


def daily_arrays(raw):
    frame = pd.DataFrame(raw)
    if frame.duplicated(['province_code', 'date']).any():
        raise ValueError('Duplicate source days')
    frame['ordinal'] = frame.date.map(lambda x: date.fromisoformat(x).toordinal())
    result = {}
    for code, group in frame.groupby('province_code'):
        first, last = int(group.ordinal.min()), int(group.ordinal.max())
        arrays = []
        for field in ('PRECTOTCORR', 'T2M_MAX'):
            values = np.full(last - first + 1, np.nan)
            values[group.ordinal.to_numpy(int) - first] = pd.to_numeric(group[field].replace('', np.nan), errors='raise')
            arrays.append(values)
        result[code] = first, *arrays
    return result


def make_bank(base, seasons, weather, vpd, daily):
    stages = stage_rows(base, seasons, weather)
    bank = {}
    for age in AGES:
        features = base.merge(stages[stages.age_days.eq(age)], on=KEYS, validate='one_to_one')
        features = features.merge(vpd_rows(base, vpd, seasons, age), on=KEYS, validate='one_to_one')
        rows = []
        for record in base.itertuples():
            days = [d for m in seasons[record.province_code] for d in month_days(int(record.year_ce), m)]
            rows.append(dict(province_code=record.province_code, year_ce=record.year_ce,
                             **shock_values(*daily[record.province_code], days, int(age))))
        features = features.merge(pd.DataFrame(rows), on=KEYS, validate='one_to_one')
        if not features[KEYS].equals(base[KEYS]) or not np.isfinite(features[FEATURES + SHOCKS]).all().all():
            raise ValueError('Invalid feature alignment/coverage')
        bank[age] = features
    return bank


def predict_year(frame, year, columns, alpha):
    train, test = frame.year_ce.lt(year), frame.year_ce.eq(year)
    if not train.any():
        raise ValueError('Empty training set')
    x = design(frame, PROVINCES, columns)
    model = fit_ridge(x[train], frame.loc[train, TARGET].to_numpy(float), alpha)
    return predict(model, x[test]), model


def run():
    check_snapshot()
    baseline_path = OUT / 'ridge_vpd_predictions.csv'
    original_hash = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    base = load_panel().sort_values(['year_ce', 'province_code']).reset_index(drop=True)
    harvest = pd.read_csv(DATA / 'harvest_monthly.csv', dtype={'province_code': str})
    harvest = harvest[harvest.year_ce.ge(2010)]
    if (harvest.duplicated(['province_code', 'year_ce', 'month_number']).any()
            or not harvest.month_number.between(1, 12).all()
            or not np.isfinite(harvest.tonnes).all() or (harvest.tonnes < 0).any()):
        raise ValueError('Invalid harvest keys')
    raw = read_csv(DATA / 'weather_daily.csv')
    weather, vpd, daily = weather_series(raw), vpd_series(raw), daily_arrays(raw)
    configs = [dict(group=g, age_days=a, alpha=p) for g, a, p in product(GROUPS, AGES, ALPHAS)]
    configs = [dict(c, config_id=i) for i, c in enumerate(configs)]
    cache, prediction_cache = {}, {}

    def bank_for(year):
        seasons = training_seasons(harvest, year - 1)
        signature = tuple((p, tuple(seasons[p])) for p in PROVINCES)
        if signature not in cache:
            print('Building shock bank:', seasons, flush=True)
            cache[signature] = make_bank(base, seasons, weather, vpd, daily)
        return cache[signature], seasons

    def estimate(year, config):
        key = year, config['config_id']
        if key not in prediction_cache:
            bank, _ = bank_for(year)
            columns = FEATURES + GROUPS[config['group']]
            frame = bank[config['age_days']]
            values, model = predict_year(frame, year, columns, config['alpha'])
            score = mae(frame[frame.year_ce.eq(year)][TARGET], values) if len(values) else None
            prediction_cache[key] = values, model, score
        return prediction_cache[key]

    records, tuning, context, choices = [], [], [], []
    final = None
    for year in range(2017, 2027):
        scores = [(float(np.mean([estimate(y, c)[2] for y in range(year - 3, year)])), c) for c in configs]
        tuning.extend(dict(test_year=year, inner_mae_kg_rai=s, **c) for s, c in scores)
        for policy in (*GROUPS, 'inner_selected'):
            eligible = [(s, c) for s, c in scores if policy == 'inner_selected' or c['group'] in ('baseline', policy)]
            score, config = min(eligible, key=lambda x: x[0])
            values, model, _ = estimate(year, config)
            choices.append(dict(policy=policy, test_year=year, inner_mae_kg_rai=score, **config))
            bank, seasons = bank_for(year)
            test = bank[config['age_days']].query('year_ce == @year')
            if year == 2026:
                if policy == 'inner_selected':
                    final = dict(config=config, parameters=model, season_months=seasons,
                                 predictors=FEATURES + GROUPS[config['group']], train_end=2025,
                                 mode='Conditional on complete stage weather; no live forecast generated')
                continue
            for row, value in zip(test.itertuples(), values):
                records.append(dict(policy=policy, province_code=row.province_code, province_name=row.province_name,
                                    year_ce=year, actual_kg_rai=getattr(row, TARGET), predicted_kg_rai=float(value),
                                    inner_mae_kg_rai=score, **config))
            if policy == 'inner_selected':
                detail = test[KEYS + SHOCKS].assign(age_days=config['age_days'], group=config['group'])
                detail['season_months'] = detail.province_code.map(lambda p: ','.join(map(str, seasons[p])))
                context.append(detail)
        print('Completed shock test origin:', year, flush=True)
    frame = pd.DataFrame(records)
    control = frame[frame.policy.eq('baseline')].merge(load_csv('predictions.csv'), on=KEYS,
                                                      validate='one_to_one', suffixes=('', '_old'))
    if len(control) != 45 or not np.allclose(control.predicted_kg_rai, control.predicted_kg_rai_old, atol=1e-7, rtol=1e-10):
        raise ValueError('Original control not reproduced')
    results = []
    for policy, group in frame.groupby('policy', sort=False):
        if len(group) != 45 or group.duplicated(KEYS).any():
            raise ValueError('Require 45 paired rows per policy')
        paired = group.merge(control[KEYS + ['predicted_kg_rai']], on=KEYS, validate='one_to_one', suffixes=('', '_baseline'))
        uncertainty, _ = paired_year_bootstrap(paired, 'predicted_kg_rai_baseline')
        results.append(dict(policy=policy, **metrics(group.actual_kg_rai, group.predicted_kg_rai),
                            paired_uncertainty=uncertainty,
                            recent_2020_2025=metrics(group[group.year_ce.ge(2020)].actual_kg_rai,
                                                   group[group.year_ce.ge(2020)].predicted_kg_rai),
                            by_year=[dict(year_ce=int(y), **metrics(g.actual_kg_rai, g.predicted_kg_rai))
                                     for y, g in group.groupby('year_ce')],
                            by_province=[dict(province_name=p, **metrics(g.actual_kg_rai, g.predicted_kg_rai))
                                         for p, g in group.groupby('province_name')]))
    if hashlib.sha256(baseline_path.read_bytes()).hexdigest() != original_hash:
        raise ValueError('Main predictions changed')
    result = dict(results=results, configurations=configs, fold_choices=choices, final_inner_selected_model=final,
                  candidate_count=len(configs), baseline_reproduced=True, input_sha256=hashes(),
                  target='All-cultivar production tonnes * 1000 / bearing rai',
                  independent_target_rows=80, test_years=list(range(2017, 2026)), test_rows_per_policy=45,
                  versions=dict(numpy=np.__version__, pandas=pd.__version__),
                  code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), Path(__file__).parent / 'common.py',
                                         Path(__file__).parent / 'step5_evaluate_result.py',
                                         ROOT / 'tools/compare_harvest_stage_yield.py', ROOT / 'tools/analyze_harvest_backcast.py',
                                         ROOT / 'tools/train_monthly_production.py')},
                  definitions=dict(dry='daily rain <1 mm', hot35='Tmax >35 C', hot38='Tmax >38 C',
                                   rx='Maximum 3/7-day rain sum fully inside each candidate fruit window',
                                   aggregation='Compute each harvest-day cohort statistic first, then equal-weight mean'),
                  source='https://www.climdex.org/learn/indices/',
                  limitations=['Exploratory on previously examined targets, no new independent holdout.',
                               '35/38 C thresholds are diagnostic hypotheses, not proven durian damage cutoffs.',
                               'CDD is window-truncated meteorological dry spell, not observed root-zone drought.',
                               'Heavy rain is not a measured flood or crop-damage event.',
                               'One NASA POWER reference point per province, no irrigation or water storage inputs.',
                               'Ages and stages are proxies; cultivar mix and flowering dates unmeasured.',
                               'Bootstrap conditions on fixed predictions, nine year clusters; no search/refit correction.',
                               'No main model, PDF or dashboard replaced.'])
    for name, data in [('predictions', frame), ('tuning', pd.DataFrame(tuning)), ('context', pd.concat(context))]:
        data.to_csv(OUT / f'weather_shock_{name}.csv', index=False, encoding='utf-8-sig')
    (OUT / 'weather_shock_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    labels = ['Original', 'Dry + heat', 'Heavy rain', 'All shocks', 'Inner-selected']
    bars = axes[0].barh(labels, [r['mae_kg_rai'] for r in results], color=['#64748b', '#d97706', '#2563eb', '#0891b2', '#7c3aed'])
    axes[0].bar_label(bars, fmt='%.2f', padding=3)
    axes[0].set(xlim=(0, 225), xlabel='MAE kg/rai (lower is better)', title='Exploratory weather-shock comparison')
    for policy in ('baseline', 'heavy_rain', 'inner_selected'):
        scores = next(r['by_year'] for r in results if r['policy'] == policy)
        axes[1].plot([s['year_ce'] for s in scores], [s['mae_kg_rai'] for s in scores], marker='o', label=policy)
    axes[1].set(xlabel='Test year', ylabel='MAE kg/rai', title='Five province targets per year')
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / 'weather_shock_comparison.png', dpi=160)
    plt.close(fig)
    print(pd.DataFrame(results)[['policy', 'mae_kg_rai', 'rmse_kg_rai']].to_string(index=False))
    return result


if __name__ == '__main__':
    run()
