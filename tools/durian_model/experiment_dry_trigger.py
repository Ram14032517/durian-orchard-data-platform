"""Dry-trigger feature-window experiment with explicit baseline fallback, not bloom truth."""
from datetime import date, timedelta
from itertools import product

from common import *
from analyze_harvest_backcast import exposure, month_days
from compare_harvest_stage_yield import vpd_window
from experiment_weather_shocks import predict_year, KEYS
from step5_evaluate_result import paired_year_bootstrap

RECIPES = ('baseline', 'dry_trigger', 'dry_trigger_reset')


def triggers(first, rain, start, end, reset=False):
    """First downward crossing per dry episode; left-censored episodes are not new triggers."""
    lo, hi = start.toordinal() - first, end.toordinal() - first
    if lo < 15 or hi + 30 >= len(rain) or hi < lo:
        raise ValueError('Trigger search outside weather coverage')
    source = rain[lo - 15:hi + 31]
    if not np.isfinite(source).all() or (source < 0).any():
        raise ValueError('Missing/invalid trigger rain; do not call it no trigger')
    cumulative = np.r_[0., np.cumsum(rain[lo - 15:hi + 1])]
    averages = (cumulative[15:] - cumulative[:-15]) / 15
    dry = averages < 1
    crossing = np.flatnonzero(dry[1:] & ~dry[:-1]) + lo
    accepted, rejected = [], 0
    for offset in crossing:
        if reset and (rain[offset:offset + 31] > 25).any():
            rejected += 1
        else:
            accepted.append(date.fromordinal(first + int(offset)))
    return accepted, dict(rejected_rain_reset=rejected, left_censored_at_search_start=bool(dry[0]))


def choose_blooms(days, age, events):
    blooms, detected = [], []
    for harvest_day in days:
        nominal = harvest_day - timedelta(days=age)
        options = [t + timedelta(days=50) for t in events if abs((t + timedelta(days=50) - nominal).days) <= 30]
        # Nearest training-season cohort anchor, not nearest realized test harvest or yield.
        selected = min(options, key=lambda b: (abs((b - nominal).days), b)) if options else nominal
        blooms.append(selected)
        detected.append(bool(options))
    return blooms, np.array(detected, dtype=bool)


def stage_values(weather, vpd, blooms, age):
    virtual_harvest = [b + timedelta(days=age) for b in blooms]
    values = {}
    for label, field, start, stop in (
        ('pre_bloom_90d', 'rain_mm', -90, 0), ('fruit_0_29d', 'rain_mm', 0, 30),
        ('fruit_30_59d', 'rain_mm', 30, 60), ('fruit_60_89d', 'solar_mj_m2_day', 60, 90),
        ('fruit_90_to_harvest', 'temperature_c', 90, age)):
        values[f'{label}_{field}'] = exposure(weather, virtual_harvest, age, start, stop)[field]
    values[VPD_STAGE_FEATURES[0]], _ = vpd_window(vpd, virtual_harvest, age, -90, 0)
    _, values[VPD_STAGE_FEATURES[1]] = vpd_window(vpd, virtual_harvest, age, 0, 30)
    if not np.isfinite(list(values.values())).all():
        raise ValueError('Incomplete shifted stage weather')
    return values


def make_bank(base, seasons, weather, vpd):
    bank = {}
    for recipe, age in product(RECIPES, AGES):
        rows = []
        for r in base.itertuples():
            code, year = r.province_code, int(r.year_ce)
            days = [d for m in seasons[code] for d in month_days(year, m)]
            start = date(year, 1, 15) if code in ('84', '86') else date(year - 1, 12, 1)
            end = days[-1] - timedelta(days=int(age) + 20)
            events, audit = [], dict(rejected_rain_reset=0, left_censored_at_search_start=False)
            if recipe != 'baseline' and end >= start:
                first, _, matrix = weather[code]
                events, audit = triggers(first, matrix[:, 1], start, end, recipe == 'dry_trigger_reset')
            blooms, found = choose_blooms(days, int(age), events)
            shifts = np.array([(b - (h - timedelta(days=int(age)))).days for b, h in zip(blooms, days)])
            status = ('baseline' if recipe == 'baseline' else
                      'dry_trigger_not_found' if not found.any() else
                      'estimated_all_cohorts' if found.all() else 'estimated_with_partial_baseline_fallback')
            rows.append(dict(province_code=code, year_ce=year,
                             **stage_values(weather[code], vpd[code], blooms, int(age)),
                             trigger_status=status, trigger_cohorts=int(found.sum()), cohort_count=len(days),
                             fallback_cohorts=0 if recipe == 'baseline' else int((~found).sum()), candidate_trigger_count=len(events),
                             no_trigger_reason=('not_applicable' if recipe == 'baseline' or found.any() else
                                                'no_accepted_episode' if not events else 'outside_cohort_matching_window'),
                             mean_bloom_shift_days=float(shifts.mean()), search_start=start.isoformat(),
                             search_end=end.isoformat(), bloom_proxy_start=min(blooms).isoformat(),
                             bloom_proxy_end=max(blooms).isoformat(), **audit))
        bank[recipe, age] = base.merge(pd.DataFrame(rows), on=KEYS, validate='one_to_one')
        if not bank[recipe, age][KEYS].equals(base[KEYS]):
            raise ValueError('Feature alignment changed')
    return bank


def run():
    check_snapshot()
    old_hash = hashlib.sha256((OUT / 'ridge_vpd_predictions.csv').read_bytes()).hexdigest()
    base = load_panel().sort_values(['year_ce', 'province_code']).reset_index(drop=True)
    harvest = pd.read_csv(DATA / 'harvest_monthly.csv', dtype={'province_code': str})
    harvest = harvest[harvest.year_ce.ge(2010)]
    if (harvest.duplicated(['province_code', 'year_ce', 'month_number']).any()
            or not np.isfinite(harvest.tonnes).all() or (harvest.tonnes < 0).any()
            or not harvest.month_number.between(1, 12).all()):
        raise ValueError('Invalid harvest source')
    raw = read_csv(DATA / 'weather_daily.csv')
    weather, vpd = weather_series(raw), vpd_series(raw)
    configs = [dict(recipe=g, age_days=int(a), alpha=p, config_id=i)
               for i, (g, a, p) in enumerate(product(RECIPES, AGES, ALPHAS))]
    cache, predictions = {}, {}

    def bank_for(year):
        seasons = training_seasons(harvest, year - 1)
        key = tuple((p, tuple(seasons[p])) for p in PROVINCES)
        if key not in cache:
            print('Building dry-trigger bank:', seasons, flush=True)
            cache[key] = make_bank(base, seasons, weather, vpd)
        return cache[key], seasons

    def estimate(year, config):
        key = year, config['config_id']
        if key not in predictions:
            frame = bank_for(year)[0][config['recipe'], config['age_days']]
            values, model = predict_year(frame, year, FEATURES, config['alpha'])
            score = mae(frame[frame.year_ce.eq(year)][TARGET], values) if len(values) else None
            predictions[key] = values, model, score
        return predictions[key]

    records, tuning, choices, contexts = [], [], [], []
    final = None
    for year in range(2017, 2027):
        scores = [(float(np.mean([estimate(y, c)[2] for y in range(year - 3, year)])), c) for c in configs]
        tuning.extend(dict(test_year=year, inner_mae_kg_rai=s, **c) for s, c in scores)
        for policy in (*RECIPES, 'inner_selected'):
            # Separate forced-trigger policies from adaptive selection to expose failed recipes.
            score, config = min((v for v in scores if policy == 'inner_selected' or v[1]['recipe'] == policy), key=lambda v: v[0])
            values, model, _ = estimate(year, config)
            choices.append(dict(policy=policy, test_year=year, inner_mae_kg_rai=score, **config))
            bank, seasons = bank_for(year)
            test = bank[config['recipe'], config['age_days']].query('year_ce == @year')
            if year == 2026:
                if policy == 'inner_selected':
                    final = dict(config=config, parameters=model, predictors=FEATURES,
                                 season_months=seasons, train_end=2025, live_prediction_generated=False)
                continue
            for row, value in zip(test.itertuples(), values):
                records.append(dict(policy=policy, province_code=row.province_code, province_name=row.province_name,
                                    year_ce=year, actual_kg_rai=getattr(row, TARGET), predicted_kg_rai=float(value),
                                    trigger_status=row.trigger_status, fallback_cohorts=row.fallback_cohorts,
                                    cohort_count=row.cohort_count, mean_bloom_shift_days=row.mean_bloom_shift_days, **config))
            detail = test.drop(columns=[TARGET, 'production_tonnes']).copy().assign(policy=policy, age_days=config['age_days'])
            detail['season_months'] = detail.province_code.map(lambda p: ','.join(map(str, seasons[p])))
            contexts.append(detail)
        print('Completed dry-trigger origin:', year, flush=True)
    frame = pd.DataFrame(records)
    control = frame[frame.policy.eq('baseline')].merge(load_csv('predictions.csv'), on=KEYS, validate='one_to_one', suffixes=('', '_old'))
    if len(control) != 45 or not np.allclose(control.predicted_kg_rai, control.predicted_kg_rai_old, atol=1e-7, rtol=1e-10):
        raise ValueError('Original predictions not reproduced')
    results = []
    for policy, group in frame.groupby('policy', sort=False):
        if len(group) != 45 or group.duplicated(KEYS).any():
            raise ValueError('Require 45 paired targets')
        paired = group.merge(control[KEYS + ['predicted_kg_rai']], on=KEYS, validate='one_to_one', suffixes=('', '_baseline'))
        uncertainty, _ = paired_year_bootstrap(paired, 'predicted_kg_rai_baseline')
        results.append(dict(policy=policy, **metrics(group.actual_kg_rai, group.predicted_kg_rai),
                            paired_uncertainty=uncertainty, trigger_status_counts=group.trigger_status.value_counts().to_dict(),
                            fallback_cohort_pct=float(100 * group.fallback_cohorts.sum() / group.cohort_count.sum()),
                            by_year=[dict(year_ce=int(y), **metrics(g.actual_kg_rai, g.predicted_kg_rai)) for y, g in group.groupby('year_ce')],
                            by_province=[dict(province_name=p, **metrics(g.actual_kg_rai, g.predicted_kg_rai)) for p, g in group.groupby('province_name')]))
    if hashlib.sha256((OUT / 'ridge_vpd_predictions.csv').read_bytes()).hexdigest() != old_hash:
        raise ValueError('Main predictions changed')
    result = dict(results=results, configurations=configs, candidate_count=len(configs), fold_choices=choices,
                  final_inner_selected_model=final, baseline_reproduced=True, input_sha256=hashes(),
                  code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), Path(__file__).parent / 'common.py',
                                         Path(__file__).parent / 'experiment_weather_shocks.py', Path(__file__).parent / 'step5_evaluate_result.py',
                                         ROOT / 'tools/analyze_harvest_backcast.py', ROOT / 'tools/compare_harvest_stage_yield.py',
                                         ROOT / 'tools/train_monthly_production.py')},
                  settings=dict(rain_rolling_days=15, dry_mean_lt_mm_day=1, trigger_to_bloom_days=50,
                                max_shift_from_baseline_days=30, reset_rain_gt_mm=25, reset_check_days_inclusive=31,
                                north_east_search_start='December 1 of prior calendar year', south_search_start='January 15',
                                left_censored_episode='Exclude; require a new downward crossing inside search window'),
                  reference='https://doi.org/10.1007/s00484-024-02819-x',
                  limitations=['Dry triggers and shifted blooms are estimates, not surveyed dates.',
                               'Regional start dates, reset threshold, shift cap and cohort matching are experimental hypotheses.',
                               'Reset does not prove bud abortion; meteorological rain does not include irrigation or management.',
                               'All original features, including VPD and solar, are recomputed together; no new predictor added.',
                               'One NASA reference point per province; no observed cultivar mix or flowering cohorts.',
                               'Observed weather hindcast; not a real-time forecasting evaluation.',
                               'Same previously explored 45 targets; bootstrap conditional, nine year clusters, no selection correction.',
                               'No surveyed-bloom arm available; no fabricated observations or replacement of main model.'])
    for name, data in [('predictions', frame), ('tuning', pd.DataFrame(tuning)), ('context', pd.concat(contexts))]:
        data.to_csv(OUT / f'dry_trigger_{name}.csv', index=False, encoding='utf-8-sig')
    (OUT / 'dry_trigger_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(pd.DataFrame(results)[['policy', 'mae_kg_rai', 'rmse_kg_rai', 'fallback_cohort_pct']].to_string(index=False))
    return result


if __name__ == '__main__':
    run()
