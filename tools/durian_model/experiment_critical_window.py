"""Test 30-50 DAA proxy exposures, without asserting tree age or fruit-drop causes."""
from itertools import product

from experiment_weather_shocks import (longest_run, window, daily_arrays, make_bank, predict_year,
                                       WET, SHOCKS, KEYS)
from common import *
from analyze_harvest_backcast import month_days
from step5_evaluate_result import paired_year_bootstrap

CRITICAL = ['critical_cdd_days', 'critical_hot38_days', 'critical_hot38_run_days',
            'critical_rain_after_dry_days']
INTERACTION = 'critical_hot38_x_cdd'
GROUPS = {'baseline': [], 'critical': CRITICAL,
          'critical_interaction': [*CRITICAL, INTERACTION], 'critical_wet': [*CRITICAL, *WET]}


def critical_values(first, rain, tmax, days, age):
    if not isinstance(age, int) or age < 51:
        raise ValueError('Age must cover the inclusive 30-50 DAA window')
    extended = window(first, rain, days, age, 23, 51)
    hot = window(first, tmax, days, age, 30, 51)
    if (extended < 0).any() or (hot < -100).any() or (hot > 70).any():
        raise ValueError('Invalid weather units/range')
    rain21 = extended[:, 7:]
    cdd = longest_run(rain21 < 1)
    heat = (hot > 38).sum(axis=1)
    # Each candidate day uses only its seven earlier days, never the day's own rainfall.
    previous = np.lib.stride_tricks.sliding_window_view(extended, 7, axis=1)[:, :21, :]
    surge = ((previous < 1).all(axis=2) & (rain21 >= 10)).sum(axis=1)
    return dict(zip([*CRITICAL, INTERACTION], map(float,
                [cdd.mean(), heat.mean(), longest_run(hot > 38).mean(), surge.mean(), (heat * cdd).mean()])))


def run():
    check_snapshot()
    base = load_panel().sort_values(['year_ce', 'province_code']).reset_index(drop=True)
    original = load_csv('predictions.csv')
    original_hash = hashlib.sha256((OUT / 'ridge_vpd_predictions.csv').read_bytes()).hexdigest()
    harvest = pd.read_csv(DATA / 'harvest_monthly.csv', dtype={'province_code': str})
    harvest = harvest[harvest.year_ce.ge(2010)]
    if (harvest.duplicated(['province_code', 'year_ce', 'month_number']).any()
            or not harvest.month_number.between(1, 12).all()
            or not np.isfinite(harvest.tonnes).all() or (harvest.tonnes < 0).any()):
        raise ValueError('Invalid harvest source')
    raw = read_csv(DATA / 'weather_daily.csv')
    weather, vpd, daily = weather_series(raw), vpd_series(raw), daily_arrays(raw)
    configs = [dict(group=g, age_days=a, alpha=p, config_id=i)
               for i, (g, a, p) in enumerate(product(GROUPS, AGES, ALPHAS))]
    cache, estimates = {}, {}

    def bank_for(year):
        seasons = training_seasons(harvest, year - 1)
        signature = tuple((p, tuple(seasons[p])) for p in PROVINCES)
        if signature not in cache:
            print('Building critical bank:', seasons, flush=True)
            bank = make_bank(base, seasons, weather, vpd, daily)
            for age, frame in bank.items():
                rows = []
                for r in base.itertuples():
                    days = [d for m in seasons[r.province_code] for d in month_days(int(r.year_ce), m)]
                    rows.append(dict(province_code=r.province_code, year_ce=r.year_ce,
                                     **critical_values(*daily[r.province_code], days, int(age))))
                bank[age] = frame.merge(pd.DataFrame(rows), on=KEYS, validate='one_to_one')
                if not bank[age][KEYS].equals(base[KEYS]):
                    raise ValueError('Feature alignment changed')
            cache[signature] = bank
        return cache[signature], seasons

    def estimate(year, config):
        key = year, config['config_id']
        if key not in estimates:
            frame = bank_for(year)[0][config['age_days']]
            values, model = predict_year(frame, year, FEATURES + GROUPS[config['group']], config['alpha'])
            score = mae(frame[frame.year_ce.eq(year)][TARGET], values) if len(values) else None
            estimates[key] = values, model, score
        return estimates[key]

    records, tuning, choices, contexts = [], [], [], []
    final = None
    for year in range(2017, 2027):
        scores = [(float(np.mean([estimate(y, c)[2] for y in range(year - 3, year)])), c) for c in configs]
        tuning.extend(dict(test_year=year, inner_mae_kg_rai=s, **c) for s, c in scores)
        for policy in (*GROUPS, 'inner_selected'):
            score, config = min((v for v in scores if policy == 'inner_selected'
                                or v[1]['group'] in ('baseline', policy)), key=lambda x: x[0])
            values, model, _ = estimate(year, config)
            choices.append(dict(policy=policy, test_year=year, inner_mae_kg_rai=score, **config))
            bank, seasons = bank_for(year)
            test = bank[config['age_days']].query('year_ce == @year')
            if year == 2026:
                if policy == 'inner_selected':
                    final = dict(config=config, parameters=model, predictors=FEATURES + GROUPS[config['group']],
                                 season_months=seasons, train_end=2025, live_prediction_generated=False)
                continue
            for row, value in zip(test.itertuples(), values):
                records.append(dict(policy=policy, province_code=row.province_code, province_name=row.province_name,
                                    year_ce=year, actual_kg_rai=getattr(row, TARGET), predicted_kg_rai=float(value), **config))
            if policy == 'inner_selected':
                detail = test[KEYS + SHOCKS + CRITICAL + [INTERACTION]].assign(age_days=config['age_days'], group=config['group'])
                detail['season_months'] = detail.province_code.map(lambda p: ','.join(map(str, seasons[p])))
                contexts.append(detail)
        print('Completed critical origin:', year, flush=True)
    frame = pd.DataFrame(records)
    control = frame[frame.policy.eq('baseline')].merge(original, on=KEYS, validate='one_to_one', suffixes=('', '_old'))
    if len(control) != 45 or not np.allclose(control.predicted_kg_rai, control.predicted_kg_rai_old, atol=1e-7, rtol=1e-10):
        raise ValueError('Baseline control not reproduced')
    results = []
    for policy, group in frame.groupby('policy', sort=False):
        if len(group) != 45 or group.duplicated(KEYS).any():
            raise ValueError('Require identical 45 paired targets')
        paired = group.merge(control[KEYS + ['predicted_kg_rai']], on=KEYS, validate='one_to_one', suffixes=('', '_baseline'))
        uncertainty, _ = paired_year_bootstrap(paired, 'predicted_kg_rai_baseline')
        results.append(dict(policy=policy, **metrics(group.actual_kg_rai, group.predicted_kg_rai),
                            paired_uncertainty=uncertainty,
                            by_year=[dict(year_ce=int(y), **metrics(g.actual_kg_rai, g.predicted_kg_rai))
                                     for y, g in group.groupby('year_ce')],
                            by_province=[dict(province_name=p, **metrics(g.actual_kg_rai, g.predicted_kg_rai))
                                         for p, g in group.groupby('province_name')]))
    if hashlib.sha256((OUT / 'ridge_vpd_predictions.csv').read_bytes()).hexdigest() != original_hash:
        raise ValueError('Main output changed')
    result = dict(results=results, candidate_count=len(configs), configurations=configs, fold_choices=choices,
                  final_inner_selected_model=final, baseline_reproduced=True, input_sha256=hashes(),
                  code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), Path(__file__).parent / 'experiment_weather_shocks.py',
                                         Path(__file__).parent / 'common.py', Path(__file__).parent / 'step5_evaluate_result.py',
                                         ROOT / 'tools/compare_harvest_stage_yield.py', ROOT / 'tools/analyze_harvest_backcast.py',
                                         ROOT / 'tools/train_monthly_production.py')},
                  definitions=dict(window='Inclusive 30-50 DAA (21 days), reconstructed from harvest-season proxy',
                                   rain_surge='Rain >=10 mm after all seven preceding days <1 mm, within critical window',
                                   interaction='Mean of cohort hot38-day count * cohort CDD; no forced negative coefficient',
                                   cohort_aggregation='Equal possible harvest-day weights; no test production weights'),
                  limitations=['No tree-age input exists; age_days is a backcast feature-window parameter.',
                               '30-50 DAA and 38 C/10 mm cutoffs are hypotheses, not calibrated fruit-drop thresholds.',
                               'Rain surge is not measured leaf flush; CDD is not root-zone water shortage.',
                               'No measured flowering dates, cultivar mixture, irrigation or crop-damage labels.',
                               'Previously explored 45 test targets; no independent holdout or causal attribution.',
                               'Nine year clusters in descriptive fixed-prediction bootstrap; no selection correction.',
                               'No main model, previous experiment outputs, report or dashboard replaced.'])
    for name, data in [('predictions', frame), ('tuning', pd.DataFrame(tuning)), ('context', pd.concat(contexts))]:
        data.to_csv(OUT / f'critical_window_{name}.csv', index=False, encoding='utf-8-sig')
    (OUT / 'critical_window_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(pd.DataFrame(results)[['policy', 'mae_kg_rai', 'rmse_kg_rai']].to_string(index=False))
    return result


if __name__ == '__main__':
    run()
