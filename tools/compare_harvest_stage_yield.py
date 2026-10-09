"""Nested rolling-year yield benchmark; observed weather, not operational forecasts."""
import hashlib
import json
import argparse
import calendar
from itertools import product
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_harvest_backcast import FIELDS, exposure, month_days, read_csv, weather_series
from train_monthly_production import fit_ridge, predict, mae

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research_data/five_province_history'
OUT = DATA / 'training'
AGES = (120, 130, 140, 150)
ALPHAS = (1.0, 10.0, 100.0)
TARGET = 'yield_kg_per_rai_calculated'
TEST_YEARS = tuple(range(2014, 2026))
INNER_YEARS = 3
SEED = 42
ANNUAL_FEATURES = ('annual_temperature_c', 'annual_rain_mm', 'annual_max_c')
STAGE_FEATURES = (
    'pre_bloom_90d_rain_mm',
    'fruit_0_29d_rain_mm',
    'fruit_30_59d_rain_mm',
    'fruit_60_89d_solar_mj_m2_day',
    'fruit_90_to_harvest_temperature_c',
)
NDVI_ANNUAL_FEATURES = ('ndvi_annual_mean', 'ndvi_annual_p10')
NDVI_STAGE_FEATURES = ('ndvi_pre_bloom_mean', 'ndvi_fruit_mean')
VPD_ANNUAL_FEATURES = ('vpd_annual_mean_kpa', 'vpd_annual_p90_kpa')
VPD_STAGE_FEATURES = ('vpd_pre_bloom_mean_kpa', 'vpd_early_fruit_p90_kpa')


def daily_vpd(tmin, tmax, rh):
    """FAO-56 Eq. 11/12/19 approximation using NASA daily mean RH, not hourly VPD."""
    tmin, tmax, rh = (np.asarray(v, dtype=float) for v in (tmin, tmax, rh))
    if not (tmin.shape == tmax.shape == rh.shape):
        raise ValueError('VPD input shapes differ')
    if any(np.isinf(v).any() for v in (tmin, tmax, rh)):
        raise ValueError('Infinite VPD input')
    if (np.any(np.isfinite(rh) & ((rh < 0) | (rh > 100)))
            or np.any(np.isfinite(tmin) & ((tmin < -100) | (tmin > 70)))
            or np.any(np.isfinite(tmax) & ((tmax < -100) | (tmax > 70)))
            or np.any(tmin > tmax)):
        raise ValueError('Invalid VPD temperature/humidity')
    es = (0.6108 * np.exp(17.27 * tmin / (tmin + 237.3))
          + 0.6108 * np.exp(17.27 * tmax / (tmax + 237.3))) / 2
    return es * (1 - rh / 100)


def vpd_series(rows):
    frame = pd.DataFrame(rows)
    if frame.duplicated(['province_code', 'date']).any():
        raise ValueError('Duplicate VPD source days')
    inputs = [pd.to_numeric(frame[c].replace('', np.nan), errors='raise').to_numpy(float)
              for c in ('T2M_MIN', 'T2M_MAX', 'RH2M')]
    frame['vpd'] = daily_vpd(*inputs)
    frame['ordinal'] = frame.date.map(lambda v: date.fromisoformat(v).toordinal())
    series = {}
    for code, group in frame.groupby('province_code'):
        first, last = int(group.ordinal.min()), int(group.ordinal.max())
        values = np.full(last - first + 1, np.nan)
        values[group.ordinal.to_numpy(int) - first] = group.vpd
        series[code] = first, values
    return series


def vpd_window(series, harvest_days, age, start, stop):
    if not harvest_days or stop <= start:
        raise ValueError('Empty VPD window')
    first, values = series
    indexes = (np.array([d.toordinal() for d in harvest_days])[:, None] - age
               + np.arange(start, stop)[None, :] - first)
    if np.any(indexes < 0) or np.any(indexes >= len(values)):
        raise ValueError('VPD window outside available weather')
    selected = values[indexes]
    if not np.isfinite(selected).all():
        raise ValueError('Missing VPD weather; no zero filling')
    return float(selected.mean()), float(np.quantile(selected, 0.9))


def vpd_rows(base, series, seasons=None, age=None):
    rows = []
    for record in base.itertuples():
        code, year = record.province_code, int(record.year_ce)
        if seasons is None:
            mean, tail = vpd_window(series[code], [date(year, 1, 1)], 0, 0,
                                    366 if calendar.isleap(year) else 365)
            features = dict(zip(VPD_ANNUAL_FEATURES, (mean, tail)))
        else:
            days = [d for month in seasons[code] for d in month_days(year, month)]
            mean, _ = vpd_window(series[code], days, age, -90, 0)
            _, tail = vpd_window(series[code], days, age, 0, 30)
            features = dict(zip(VPD_STAGE_FEATURES, (mean, tail)))
        rows.append(dict(province_code=code, year_ce=year, **features))
    return pd.DataFrame(rows)


def ndvi_annual_rows(base, series):
    from fetch_modis_ndvi import ndvi_exposure
    rows = []
    for record in base.itertuples():
        year, code = int(record.year_ce), record.province_code
        start = date(year, 1, 1)
        length = 366 if calendar.isleap(year) else 365
        values = ndvi_exposure(series[code], [start], 0, 0, length)
        selected = series[code][(series[code][:, 0] >= start.toordinal())
                                & (series[code][:, 0] < start.toordinal() + length)]
        good = selected[np.isfinite(selected[:, 2]), 2]
        rows.append(dict(province_code=code, year_ce=year, ndvi_annual_mean=values['mean'],
                         ndvi_annual_p10=float(np.quantile(good, 0.1)) if values['coverage_pct'] >= 50 else np.nan,
                         ndvi_annual_coverage_pct=values['coverage_pct']))
    return pd.DataFrame(rows)


def ndvi_stage_rows(base, seasons, age, series):
    from fetch_modis_ndvi import ndvi_exposure
    rows = []
    for record in base.itertuples():
        code, year = record.province_code, int(record.year_ce)
        days = [day for month in seasons[code] for day in month_days(year, month)]
        features = {}
        for label, start, stop in [('pre_bloom', -90, 0), ('fruit', 0, age)]:
            values = ndvi_exposure(series[code], days, age, start, stop)
            features.update({f'ndvi_{label}_mean': values['mean'],
                             f'ndvi_{label}_coverage_pct': values['coverage_pct']})
        rows.append(dict(province_code=code, year_ce=year, **features))
    return pd.DataFrame(rows)


def design(frame, provinces, features):
    province = np.column_stack([
        frame.province_code.eq(code).to_numpy(float) for code in provinces
    ])
    numeric = frame[['year_ce', *features]].to_numpy(float)
    return np.column_stack([province, numeric])


def training_seasons(harvest, last_train_year):
    """Choose each province's reported peak month using training years only."""
    training = harvest[harvest.year_ce.le(last_train_year)]
    if training.empty:
        raise ValueError('No harvest observations in training period')
    peak = training.groupby(['province_code', 'month_number']).tonnes.sum()
    seasons = {}
    for code in sorted(training.province_code.unique()):
        peak_month = int(peak.loc[code].idxmax())
        start = max(1, min(10, peak_month - 1))
        seasons[code] = list(range(start, start + 3))
    return seasons


def stage_rows(annual, seasons, weather):
    rows = []
    for record in annual[annual.year_ce.between(2004, 2025)].itertuples():
        code, year = record.province_code, int(record.year_ce)
        days = [day for month in seasons[code] for day in month_days(year, month)]
        for age in AGES:
            features = {}
            windows = {
                'pre_bloom_90d': (-90, 0),
                'fruit_0_29d': (0, 30),
                'fruit_30_59d': (30, 60),
                'fruit_60_89d': (60, 90),
                'fruit_90_to_harvest': (90, age),
            }
            for label, (start, stop) in windows.items():
                values = exposure(weather[code], days, age, start, stop)
                for field in FIELDS:
                    features[f'{label}_{field}'] = values[field]
            rows.append(dict(province_code=code, year_ce=year, age_days=age, **features))
    return pd.DataFrame(rows)


def candidates(include_ndvi=False, include_vpd=False, advanced=False):
    """Small prespecified search; never expand it after inspecting outer errors."""
    result = [dict(model=name, kind=name, features=(), age_days=None, parameter=None)
              for name in ('previous_year', 'province_median')]
    for name, features in (
        ('province_trend', ()),
        ('lag_yield_ridge', ('previous_yield_kg_rai',)),
        ('whole_year_ridge', ('previous_yield_kg_rai', *ANNUAL_FEATURES)),
        ('stage_ridge', ('previous_yield_kg_rai', *STAGE_FEATURES)),
    ):
        for age in AGES if name == 'stage_ridge' else (None,):
            for alpha in ALPHAS:
                result.append(dict(model=name, kind='ridge', features=features,
                                   age_days=age, parameter=alpha))
    for kind in ('random_forest', 'gradient_boosting'):
        for scope in ('lag_yield', 'stage'):
            features = ('previous_yield_kg_rai', *STAGE_FEATURES) if scope == 'stage' else ('previous_yield_kg_rai',)
            for age in AGES if scope == 'stage' else (None,):
                for leaf in (5, 10):
                    result.append(dict(model=f'{scope}_{kind}', kind=kind, features=features,
                                       age_days=age, parameter=leaf))
    if include_ndvi or include_vpd:
        additions = []
        if include_ndvi:
            additions.append(('_ndvi', NDVI_ANNUAL_FEATURES, NDVI_STAGE_FEATURES))
        if include_vpd:
            additions.append(('_vpd', VPD_ANNUAL_FEATURES, VPD_STAGE_FEATURES))
        if include_ndvi and include_vpd:
            additions.append(('_ndvi_vpd', (*NDVI_ANNUAL_FEATURES, *VPD_ANNUAL_FEATURES),
                              (*NDVI_STAGE_FEATURES, *VPD_STAGE_FEATURES)))
        for config in list(result):
            if config['model'] in ('whole_year_ridge', 'stage_ridge', 'stage_random_forest', 'stage_gradient_boosting'):
                for suffix, annual, stage in additions:
                    added = annual if config['model'] == 'whole_year_ridge' else stage
                    result.append(dict(config, model=config['model'] + suffix,
                                       features=(*config['features'], *added)))
    if advanced:
        if not include_vpd:
            raise ValueError('Advanced experiment requires VPD')
        features = ('previous_yield_kg_rai', *STAGE_FEATURES, *VPD_STAGE_FEATURES)
        if include_ndvi:
            features += NDVI_STAGE_FEATURES
        grids = {
            'catboost': [dict(depth=d, l2_leaf_reg=l2, learning_rate=lr)
                         for d, l2, lr in product((2, 4), (3, 20), (0.03, 0.1))],
            'extra_trees': [dict(max_depth=d, min_samples_leaf=leaf, max_features=f)
                            for d, leaf, f in product((3, 5), (3, 8), (0.7, 1.0))],
            'svr': [dict(C=c, gamma=g) for c, g in product((0.1, 1, 10), ('scale', 0.03, 0.3))],
        }
        for kind, parameters in grids.items():
            for age, parameter in product(AGES, parameters):
                result.append(dict(model='stage_' + kind + ('_combined' if include_ndvi else '_vpd'),
                                   kind=kind, features=features, age_days=age, parameter=parameter))
    return result


def fit_predict(train, heldout, provinces, config):
    if train.empty or heldout.empty or train.year_ce.max() >= heldout.year_ce.min():
        raise ValueError('Training must precede the held-out year')
    if config['kind'] == 'previous_year':
        return heldout.previous_yield_kg_rai.to_numpy(float)
    if config['kind'] == 'province_median':
        medians = train.groupby('province_code')[TARGET].median()
        return heldout.province_code.map(medians).to_numpy(float)
    ndvi_columns = [name for name in config['features'] if name.startswith('ndvi_')]
    indicators, test_indicators = [], []
    if ndvi_columns:
        train, heldout = train.copy(), heldout.copy()
        for column in ndvi_columns:
            if not np.isfinite(train[column].dropna()).all() or train[column].dropna().empty:
                raise ValueError('No usable training NDVI, or infinite input')
            indicators.append(train[column].isna().to_numpy(float))
            test_indicators.append(heldout[column].isna().to_numpy(float))
            fill = train[column].median()
            train[column] = train[column].fillna(fill)
            heldout[column] = heldout[column].fillna(fill)
    x, xt = design(train, provinces, config['features']), design(heldout, provinces, config['features'])
    if ndvi_columns:
        x, xt = np.column_stack([x, *indicators]), np.column_stack([xt, *test_indicators])
    y = train[TARGET].to_numpy(float)
    if not all(np.isfinite(values).all() for values in (x, xt, y)):
        raise ValueError('Missing or invalid model input; no zero imputation')
    if config['kind'] == 'ridge':
        return predict(fit_ridge(x, y, config['parameter']), xt)
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
    if config['kind'] == 'random_forest':
        model = RandomForestRegressor(n_estimators=150, max_depth=3,
                                      min_samples_leaf=config['parameter'],
                                      random_state=SEED, n_jobs=1)
    elif config['kind'] == 'gradient_boosting':
        model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.03,
                                          max_depth=2, min_samples_leaf=config['parameter'],
                                          loss='huber', random_state=SEED)
    elif config['kind'] == 'extra_trees':
        model = ExtraTreesRegressor(n_estimators=150, random_state=SEED, n_jobs=1, **config['parameter'])
    elif config['kind'] == 'catboost':
        from catboost import CatBoostRegressor
        model = CatBoostRegressor(iterations=400, loss_function='RMSE', boosting_type='Ordered',
                                  random_seed=SEED, thread_count=1, verbose=False,
                                  allow_writing_files=False, **config['parameter'])
    elif config['kind'] == 'svr':
        from sklearn.compose import TransformedTargetRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVR
        model = TransformedTargetRegressor(
            regressor=make_pipeline(StandardScaler(), SVR(epsilon=0.1, **config['parameter'])),
            transformer=StandardScaler())
    else:
        raise ValueError('Unknown estimator')
    model.fit(x, y)
    return np.maximum(0, model.predict(xt))


def metric_records(predictions, groups):
    records = []
    for key, frame in predictions.groupby(groups, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        error = frame.predicted_kg_rai - frame.actual_kg_rai
        records.append(dict(zip(groups, key), n=len(frame),
                            mae_kg_rai=float(error.abs().mean()),
                            rmse_kg_rai=float(np.sqrt((error ** 2).mean())),
                            bias_kg_rai=float(error.mean())))
    return records


def paired_year_comparison(predictions):
    """Descriptive paired interval: resample whole years, not 60 independent rows."""
    errors = predictions.assign(error=(predictions.predicted_kg_rai - predictions.actual_kg_rai).abs())
    yearly = errors.groupby(['year_ce', 'model']).error.mean().unstack()
    rng = np.random.default_rng(SEED)
    # ponytail: year-cluster bootstrap ignores serial dependence; exploratory, not a significance test.
    samples = rng.integers(0, len(yearly), size=(5000, len(yearly)))
    result = []
    pairs = [('lag_yield_ridge', name) for name in yearly.columns]
    pairs += [('lag_yield_random_forest', 'stage_random_forest'),
              ('lag_yield_gradient_boosting', 'stage_gradient_boosting')]
    pairs += [(name.rsplit('_', 1)[0], name) for name in yearly.columns if name.endswith(('_ndvi', '_vpd'))]
    pairs = [(baseline, name) for baseline, name in pairs if baseline in yearly.columns]
    pairs += [('stage_ridge_ndvi_vpd' if name.endswith('_combined') else 'stage_ridge_vpd', name)
              for name in yearly.columns if any(kind in name for kind in ('catboost', 'extra_trees', 'svr'))]
    pairs += [(name[:-9] + '_vpd', name) for name in yearly.columns if name.endswith('_ndvi_vpd')]
    for baseline, name in pairs:
        differences = (yearly[baseline] - yearly[name]).to_numpy(float)
        low, high = np.quantile(differences[samples].mean(axis=1), [0.025, 0.975])
        result.append(dict(model=name, baseline=baseline,
                           mean_mae_reduction_kg_rai=float(differences.mean()),
                           better_years=int((differences > 0).sum()), years=len(yearly),
                           descriptive_95pct_year_bootstrap=[float(low), float(high)]))
    return result


def plot_results(predictions, results, suffix=''):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    ranked = pd.DataFrame(results).sort_values('mae_kg_rai', ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(15, 8 if suffix else 6), constrained_layout=True)
    colors = ['#167b68' if name.startswith('stage_') else '#345f91'
              if name == 'inner_selected' else '#788493' for name in ranked.model]
    axes[0].barh(ranked.model.str.replace('_', ' '), ranked.mae_kg_rai, color=colors)
    count = len(predictions[['province_code', 'year_ce']].drop_duplicates())
    axes[0].set(xlabel='MAE (kg/rai), lower is better',
                title=f'Same {count} province-years ({predictions.year_ce.min()}-{predictions.year_ce.max()})')
    for position, value in enumerate(ranked.mae_kg_rai):
        axes[0].text(value + 2, position, f'{value:.1f}', va='center', fontsize=9)
    axes[0].set_xlim(0, ranked.mae_kg_rai.max() * 1.18)
    errors = predictions.assign(error=(predictions.predicted_kg_rai - predictions.actual_kg_rai).abs())
    yearly = errors.groupby(['year_ce', 'model']).error.mean().unstack()
    for name, color in [('lag_yield_ridge', '#788493'), ('stage_ridge', '#167b68'),
                        ('stage_ridge_ndvi_vpd' if '_combined' in suffix else 'stage_ridge_vpd' if '_vpd' in suffix else 'stage_ridge_ndvi'
                         if '_ndvi' in suffix else 'inner_selected', '#345f91')]:
        axes[1].plot(yearly.index, yearly[name], marker='o', color=color,
                     label=name.replace('_', ' '))
    axes[1].set(xlabel='Held-out year', ylabel='Mean MAE across five provinces (kg/rai)',
                title='Year-to-year stability')
    axes[1].legend(frameon=False)
    for axis in axes:
        axis.spines[['top', 'right']].set_visible(False)
        axis.grid(axis='x' if axis is axes[0] else 'y', alpha=0.15)
        axis.set_axisbelow(True)
    fig.suptitle('Durian yield: nested chronological experiment\nObserved historical weather; not causal evidence or an operational forecast')
    fig.savefig(OUT / f'harvest_stage_rolling{suffix}_comparison.png', dpi=160)
    plt.close(fig)


def main(include_ndvi=False, include_vpd=False, train_start=2004, advanced=False):
    if not 2004 <= train_start <= 2018:
        raise ValueError('Training start must be 2004..2018')
    test_years = tuple(range(max(2014, train_start + 7), 2026))
    annual = pd.read_csv(DATA / 'production_annual.csv', dtype={'province_code': str})
    weather = pd.read_csv(DATA / 'production_weather_annual.csv', dtype={'province_code': str})
    harvest = pd.read_csv(DATA / 'harvest_monthly.csv', dtype={'province_code': str})
    annual_weather = weather[['province_code', 'year_ce', *ANNUAL_FEATURES]]
    provinces = sorted(annual.province_code.unique())
    if (annual.duplicated(['province_code', 'year_ce']).any() or (annual.bearing_rai <= 0).any()
            or (annual.production_tonnes < 0).any()):
        raise ValueError('Annual production keys/denominators must be valid')
    if (harvest.duplicated(['province_code', 'year_ce', 'month_number']).any()
            or not harvest.month_number.between(1, 12).all()
            or not np.isfinite(harvest.tonnes).all() or (harvest.tonnes < 0).any()):
        raise ValueError('Invalid monthly harvest records')
    calculated = annual.production_tonnes * 1000 / annual.bearing_rai
    if not np.isfinite(calculated).all() or not np.allclose(calculated, annual[TARGET]):
        raise ValueError('Target must equal actual production / bearing area')
    lag = annual[['province_code', 'year_ce', TARGET]].rename(columns={TARGET: 'previous_yield_kg_rai'})
    lag['year_ce'] += 1
    base = annual[annual.year_ce.between(2004, 2025)].merge(
        lag, on=['province_code', 'year_ce'], validate='one_to_one').merge(
        annual_weather, on=['province_code', 'year_ce'], validate='one_to_one')
    if len(base) != 110 or base.previous_yield_kg_rai.isna().any():
        raise ValueError('Expected complete five-province panel, 2004-2025')
    vegetation = None
    satellite_source = None
    if include_ndvi:
        from fetch_modis_ndvi import ndvi_series
        satellite_source = json.loads((DATA / 'ndvi_source_review.json').read_text(encoding='utf-8'))
        if hashlib.sha256((DATA / 'ndvi_reference_composites.csv').read_bytes()).hexdigest() != satellite_source['csv_sha256']:
            raise ValueError('NDVI CSV no longer matches its source manifest; rebuild or re-audit')
        vegetation = ndvi_series(read_csv(DATA / 'ndvi_reference_composites.csv'))
        if set(vegetation) != set(provinces):
            raise ValueError('NDVI and target provinces differ')
        ndvi_annual = ndvi_annual_rows(base, vegetation)
        base = base.merge(ndvi_annual, on=['province_code', 'year_ce'], validate='one_to_one')
        ndvi_annual.to_csv(OUT / 'ndvi_annual_context.csv', index=False, encoding='utf-8-sig')
    weather_rows = read_csv(DATA / 'weather_daily.csv')
    daily_weather = weather_series(weather_rows)
    vpd = vpd_series(weather_rows) if include_vpd else None
    if include_vpd:
        vpd_annual = vpd_rows(base, vpd)
        base = base.merge(vpd_annual, on=['province_code', 'year_ce'], validate='one_to_one')
        vpd_annual.to_csv(OUT / 'vpd_annual_context.csv', index=False, encoding='utf-8-sig')
    base = base[base.year_ce.ge(train_start)].copy()
    harvest = harvest[harvest.year_ce.ge(train_start)].copy()
    zero_rain = next(row for row in weather_rows
                     if row['PRECTOTCORR'] and float(row['PRECTOTCORR']) == 0)
    first_day, _, matrix = daily_weather[zero_rain['province_code']]
    assert np.isfinite(matrix[pd.Timestamp(zero_rain['date']).date().toordinal() - first_day, 1])
    stage_cache = {}

    def frame_for(config, cutoff):
        if config['age_days'] is None:
            return base
        seasons = training_seasons(harvest, cutoff)
        signature = tuple((code, tuple(months)) for code, months in seasons.items())
        if signature not in stage_cache:
            stages = stage_rows(annual, seasons, daily_weather)
            stage_cache[signature] = {
                age: base.merge(stages[stages.age_days.eq(age)],
                                on=['province_code', 'year_ce'], validate='one_to_one')
                for age in AGES
            }
            if include_ndvi:
                for age in AGES:
                    stage_cache[signature][age] = stage_cache[signature][age].merge(
                        ndvi_stage_rows(base, seasons, age, vegetation),
                        on=['province_code', 'year_ce'], validate='one_to_one')
            if include_vpd:
                for age in AGES:
                    stage_cache[signature][age] = stage_cache[signature][age].merge(
                        vpd_rows(base, vpd, seasons, age),
                        on=['province_code', 'year_ce'], validate='one_to_one')
        return stage_cache[signature][config['age_days']]

    configs = candidates(include_ndvi, include_vpd, advanced)
    inner_cache, folds, rows = {}, [], []
    for test_year in test_years:
        validation_years = tuple(range(test_year - INNER_YEARS, test_year))
        scores = []
        for number, config in enumerate(configs):
            values = []
            for valid_year in validation_years:
                key = number, valid_year
                if key not in inner_cache:
                    frame = frame_for(config, valid_year - 1)
                    train, valid = frame[frame.year_ce.lt(valid_year)], frame[frame.year_ce.eq(valid_year)]
                    inner_cache[key] = mae(valid[TARGET], fit_predict(train, valid, provinces, config))
                values.append(inner_cache[key])
            scores.append(float(np.mean(values)))
        selected = {}
        for number, config in enumerate(configs):
            name = config['model']
            if name not in selected or scores[number] < scores[selected[name]]:
                selected[name] = number
        overall = min(range(len(configs)), key=lambda number: scores[number])
        selected['inner_selected'] = overall
        for name, number in selected.items():
            config = configs[number]
            frame = frame_for(config, test_year - 1)
            train, test = frame[frame.year_ce.lt(test_year)], frame[frame.year_ce.eq(test_year)]
            estimates = fit_predict(train, test, provinces, config)
            for record, estimate in zip(test.itertuples(), estimates):
                rows.append(dict(model=name, source_model=config['model'],
                                 province_code=record.province_code, province_name=record.province_name,
                                 year_ce=test_year, actual_kg_rai=getattr(record, TARGET),
                                 predicted_kg_rai=float(estimate), age_days=config['age_days'],
                                 parameter=config['parameter']))
            folds.append(dict(test_year=test_year, model=name, selected=dict(config),
                              train_year_min=train_start, train_year_max=test_year - 1,
                              validation_years=list(validation_years), inner_mae_kg_rai=scores[number],
                              train_rows=len(train), test_rows=len(test),
                              season_months=training_seasons(harvest, test_year - 1)
                              if config['age_days'] is not None else None,
                              ndvi_missing_train={c: int(train[c].isna().sum()) for c in config['features'] if c.startswith('ndvi_')},
                              ndvi_missing_test={c: int(test[c].isna().sum()) for c in config['features'] if c.startswith('ndvi_')}))
        print(f'Completed outer year {test_year}; selected on earlier years: {configs[overall]["model"]}', flush=True)
    predictions = pd.DataFrame(rows)
    assert len(predictions) == len(test_years) * len(provinces) * (len(selected))
    assert not predictions.duplicated(['model', 'province_code', 'year_ce']).any()
    results = metric_records(predictions, ['model'])
    import sklearn
    versions = dict(numpy=np.__version__, pandas=pd.__version__, scikit_learn=sklearn.__version__)
    if advanced:
        import catboost
        versions['catboost'] = catboost.__version__
    output = dict(
        purpose='Exploratory nested rolling-year retrospective comparison; not operational forecasts or causal attribution.',
        target='OAE annual production tonnes * 1000 / bearing rai; province-year.',
        protocol=dict(panel_years=[train_start, 2025], outer_test_years=list(test_years),
                      inner_validation='Three immediately preceding years; each fit uses earlier years only',
                      refit='After inner selection, refit on every year before the outer test year',
                      seasons='Peak month and fixed three-month season relearned from earlier harvest data inside every fit',
                      weather_availability='Observed weather through stage end or December, not forecast vintages',
                      stage_features=list(STAGE_FEATURES), annual_features=list(ANNUAL_FEATURES),
                      ndvi_features=dict(annual=list(NDVI_ANNUAL_FEATURES), stage=list(NDVI_STAGE_FEATURES)) if include_ndvi else None,
                      ndvi_missing='Require 50% composite-time coverage; otherwise training-fold median plus missing indicator; no interpolation or zero filling' if include_ndvi else None,
                      candidate_configs=[dict(config) for config in configs], seed=SEED),
        data_rows=len(base), evaluated_province_years=len(test_years) * len(provinces),
        models=results,
        per_province=metric_records(predictions, ['model', 'province_code']),
        per_year=metric_records(predictions, ['model', 'year_ce']),
        paired_comparisons=paired_year_comparison(predictions), folds=folds,
        versions=versions,
        code_sha256={name: hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest()
                     for name in ('compare_harvest_stage_yield.py', 'analyze_harvest_backcast.py',
                                  'train_monthly_production.py')},
        input_sha256={name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                      for name in ('production_annual.csv', 'harvest_monthly.csv',
                                   'weather_daily.csv', 'production_weather_annual.csv')},
        research_sources=[
            dict(url='https://arxiv.org/abs/2104.13246', adaptation='Nested year-separated tuning, province encoding and simple benchmarks; changed from leave-year-out to forward-only rolling origins.'),
            dict(url='https://doi.org/10.3389/fpls.2023.1128388', adaptation='Chronological extrapolation test and constrained nonlinear comparators; no simulated wheat/sunflower targets or coefficients imported.'),
            dict(url='https://doi.org/10.1038/s41598-022-06249-w', adaptation='Stage-aware weather aggregation; bearing-area spatial weighting is a later data task, not implemented here.'),
        ],
        interpretation_limits=[
            'The entire historical dataset has been explored; rolling results are not a new independent confirmatory holdout.',
            'The climate predictors are observed retrospective weather, not the forecasts available at an issue date; annual inputs include weather after harvest.',
            'All candidates use the same province-year target; repeated ages, windows and models do not multiply the number of independent target observations.',
            'Prior-year yield comes from revised annual records; historical publication delays and revisions are not reconstructed.',
            'Stage and annual candidates differ in weather feature content as well as timing; their difference does not isolate the causal effect of stage alignment.',
            'The selected season is an approximate calendar window, not an observed flowering/fruit stage for each year.',
            'Harvest data include cultivars; fruit-age scenarios are assumptions, not observed flowering dates.',
            'Weather is one NASA POWER reference point per province, not a productive-area-weighted spatial mean.',
            'Only five provinces: static soil shares are confounded with province identity; no fabricated numeric pH/NPK or soil-specific yields are added.',
            'No tree photosynthesis, root-zone water balance or orchard readiness is measured by these weather features.',
            'The descriptive year-cluster bootstrap ignores serial dependence and model search; it is not a significance test.',
            'Do not interpret prediction error or feature importance as proof of agronomic causation.',
        ],
    )
    if include_ndvi:
        output['satellite_source'] = satellite_source
        output['code_sha256']['fetch_modis_ndvi.py'] = hashlib.sha256((ROOT / 'tools/fetch_modis_ndvi.py').read_bytes()).hexdigest()
        for name in ('ndvi_reference_composites.csv', 'ndvi_source_review.json'):
            output['input_sha256'][name] = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
        output['interpretation_limits'] += [
            'NDVI is a mixed-land-cover reference patch (1 km each side), not bearing-durian-area weighted.',
            'Composite-period overlap is a timing proxy: MOD13Q1 values are not daily greenness or daily photosynthesis.',
            'Annual NDVI includes observations after harvest; stage NDVI can include a partially overlapping 16-day composite.',
            'Observed reprocessed satellite data and processing delays are not the data available on an operational issue date.',
            'Greenness does not confirm drought damage, nutrient availability, tree readiness or fruit loss.',
            'Adding NDVI does not increase the number of independent annual targets; comparison remains exploratory.',
        ]
    if include_vpd:
        output['vpd_method'] = dict(
            source='https://www.fao.org/4/X0490E/x0490e07.htm',
            formula='es=(e(Tmin)+e(Tmax))/2; e(T)=0.6108*exp(17.27*T/(T+237.3)); VPD=es*(1-RH2M/100)',
            units='kPa', annual=list(VPD_ANNUAL_FEATURES), stage=list(VPD_STAGE_FEATURES),
            limitation='FAO Eq.19-style approximation: NASA daily mean RH is not (RHmax+RHmin)/2; no dewpoint or hourly daytime VPD.')
        output['interpretation_limits'] += [
            'VPD is a derived daily proxy from existing weather, not new independent observations or leaf VPD.',
            'Early-fruit p90 is a distribution proxy under assumed harvest windows, not observed damage or a durian stress threshold.',
            'Recent-year sensitivity excludes years by calendar cutoff, never by low target yield; different test periods must be matched before comparison.',
        ]
    if advanced:
        output['advanced_method'] = dict(
            candidate_configs_added=100, catboost_iterations=400, catboost_boosting='Ordered',
            svr_scaling='X and y scalers fitted exclusively on each training fold',
            selection='Fixed grid; no early stopping on outer test; select mean MAE across three earlier years',
            sources=['https://catboost.ai/docs/en/concepts/parameter-tuning',
                     'https://catboost.ai/docs/en/references/training-parameters/common'])
        output['interpretation_limits'].append('The expanded search is an additional exploratory experiment after prior results; no independent confirmatory test is claimed.')
    OUT.mkdir(exist_ok=True)
    suffix = '_combined' if include_ndvi and include_vpd else '_ndvi' if include_ndvi else '_vpd' if include_vpd else ''
    if advanced:
        suffix += '_advanced'
    if train_start != 2004:
        suffix += f'_recent{train_start}'
    predictions.to_csv(OUT / f'harvest_stage_rolling{suffix}_predictions.csv', index=False, encoding='utf-8-sig')
    (OUT / f'harvest_stage_rolling{suffix}_results.json').write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    plot_results(predictions, results, suffix)
    print(pd.DataFrame(results).sort_values('mae_kg_rai').to_string(index=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndvi', action='store_true', help='Paired comparison with downloaded MODIS NDVI; combine with --vpd for joint experiment')
    parser.add_argument('--vpd', action='store_true', help='Paired comparison with derived daily VPD proxy')
    parser.add_argument('--advanced', action='store_true', help='Tune CatBoost, Extra Trees and scaled SVR; requires --vpd')
    parser.add_argument('--train-start-year', type=int, default=2004, help='Calendar cutoff, not filtering low yields; default 2004')
    args = parser.parse_args()
    main(args.ndvi, args.vpd, args.train_start_year, args.advanced)
