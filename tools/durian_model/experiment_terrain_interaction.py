"""Exploratory terrain ablation: supplied scenarios versus sampled SRTM, never orchard means."""
import argparse
from datetime import datetime, timezone
from itertools import product
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common import *
from experiment_weather_shocks import make_bank, daily_arrays, predict_year
from step5_evaluate_result import paired_year_bootstrap

KEYS = ['province_code', 'year_ce']
ENDPOINT = 'https://api.opentopodata.org/v1/srtm30m'
RAW = DATA / 'terrain_srtm30_samples.json'
POINTS = [
    ('22', 'ท่าใหม่', 12.723, 101.983, 45., 4.5),
    ('22', 'เขาคิชฌกูฏ', 12.825, 102.135, 120., 11.),
    ('86', 'หลังสวน', 9.912, 99.034, 25., 2.5),
    ('86', 'พะโต๊ะ', 9.790, 98.785, 160., 22.),
    ('84', 'กาญจนดิษฐ์', 9.123, 99.510, 30., 3.),
    ('84', 'บ้านนาสาร', 8.815, 99.375, 65., 6.),
    ('53', 'ลับแล', 17.697, 100.015, 280., 28.),
    ('53', 'ท่าปลา', 17.892, 100.521, 230., 24.),
    ('33', 'กันทรลักษ์', 14.685, 104.665, 180., 3.5),
    ('33', 'ขุนหาญ', 14.597, 104.495, 195., 4.),
]
EXTREMES = ['fruit_rx7day_mm', 'early_fruit_hot38_days']
TERRAIN = ['terrain_elevation_m', 'terrain_slope_pct']
INTERACTIONS = ['slope_x_rx7', 'elevation_x_hot38']
PROVINCE_WEATHER = [f'province_{p}_x_{w}' for p in PROVINCES for w in EXTREMES]
GROUPS = {
    'baseline': (None, []),
    'weather_control': (None, EXTREMES),
    'supplied_main': ('supplied', TERRAIN),
    'supplied_interaction': ('supplied', EXTREMES + TERRAIN + INTERACTIONS),
    'srtm_main': ('srtm', TERRAIN),
    'srtm_interaction': ('srtm', EXTREMES + TERRAIN + INTERACTIONS),
    'province_weather_control': (None, EXTREMES + PROVINCE_WEATHER),
}


def sample_locations():
    # Nine DEM samples around each user-selected point; not an administrative polygon.
    return [(round(lat + dy / 3600, 7), round(lon + dx / 3600, 7))
            for _, _, lat, lon, _, _ in POINTS for dy in (-1, 0, 1) for dx in (-1, 0, 1)]


def validate_response(response, locations):
    rows = response.get('results', [])
    if response.get('status') != 'OK' or len(rows) != len(locations):
        raise ValueError('Incomplete/failed DEM response')
    heights = []
    for row, (lat, lon) in zip(rows, locations):
        z, loc = row.get('elevation'), row.get('location', {})
        if (row.get('dataset') != 'srtm30m' or z is None or not np.isfinite(z)
                or not -500 <= z <= 9000
                or not np.isclose(loc.get('lat', np.nan), lat, rtol=0, atol=1e-6)
                or not np.isclose(loc.get('lng', np.nan), lon, rtol=0, atol=1e-6)):
            raise ValueError('Invalid DEM height, dataset or location order')
        heights.append(float(z))
    return np.asarray(heights)


def slope_pct(grid, latitude):
    grid = np.asarray(grid, dtype=float)
    if grid.shape != (3, 3) or not np.isfinite(grid).all() or not -90 < latitude < 90:
        raise ValueError('Require finite 3x3 DEM and valid latitude')
    dy = np.pi * 6371008.8 / (180 * 3600)
    dx = dy * np.cos(np.deg2rad(latitude))
    # Horn gradient at the centre, percent rise/run, not degrees or a district mean.
    east = ((grid[0, 2] + 2 * grid[1, 2] + grid[2, 2])
            - (grid[0, 0] + 2 * grid[1, 0] + grid[2, 0])) / (8 * dx)
    north = ((grid[2, 0] + 2 * grid[2, 1] + grid[2, 2])
             - (grid[0, 0] + 2 * grid[0, 1] + grid[0, 2])) / (8 * dy)
    return float(100 * np.hypot(east, north))


def terrain_tables():
    locations = sample_locations()
    if RAW.exists():
        envelope = json.loads(RAW.read_text(encoding='utf-8'))
        if envelope['locations'] != [list(p) for p in locations]:
            raise ValueError('DEM cache belongs to different sample points')
    else:
        query = urlencode(dict(locations='|'.join(f'{a},{b}' for a, b in locations),
                               interpolation='bilinear'))
        url = ENDPOINT + '?' + query
        with urlopen(Request(url, headers={'User-Agent': 'DurianResearch/1.0'}), timeout=45) as stream:
            response = json.load(stream)
        validate_response(response, locations)
        envelope = dict(url=url, downloaded_utc=datetime.now(timezone.utc).isoformat(),
                        locations=locations, response=response,
                        scope='3x3 one-arcsecond sample patches around user-selected coordinates; not orchard/district masks')
        RAW.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    heights = validate_response(envelope['response'], locations).reshape(10, 3, 3)
    rows = []
    for point, grid in zip(POINTS, heights):
        code, district, lat, lon, elevation, slope = point
        rows.append(dict(province_code=code, district_label=district, latitude=lat, longitude=lon,
                         supplied_elevation_m=elevation, supplied_slope_pct=slope,
                         srtm_elevation_m=float(grid.mean()), srtm_slope_pct=slope_pct(grid, lat),
                         srtm_centre_elevation_m=float(grid[1, 1]),
                         scope='Selected-point terrain proxy; not district or bearing-orchard mean',
                         supplied_status='Unverified values from user attachment, scenario only',
                         srtm_status='SRTM30m sampled patch; coordinate representativeness unverified'))
    points = pd.DataFrame(rows)
    # ponytail: equal two-point weights, not planted/bearing-area weights; replace only with verified masks.
    tables = {source: points.groupby('province_code')[[source + '_elevation_m', source + '_slope_pct']]
              .mean().rename(columns={source + '_elevation_m': TERRAIN[0], source + '_slope_pct': TERRAIN[1]})
              .reset_index() for source in ('supplied', 'srtm')}
    return points, tables, envelope


def add_terrain(frame, table):
    if (table.duplicated('province_code').any() or set(table.province_code) != set(PROVINCES)
            or not np.isfinite(table[TERRAIN]).all().all() or (table.terrain_slope_pct < 0).any()):
        raise ValueError('Invalid province terrain proxy')
    merged = frame.merge(table, on='province_code', validate='many_to_one')
    if not merged[KEYS].equals(frame[KEYS]):
        raise ValueError('Terrain join changed row alignment')
    merged[INTERACTIONS[0]] = merged.terrain_slope_pct * merged.fruit_rx7day_mm
    merged[INTERACTIONS[1]] = merged.terrain_elevation_m * merged.early_fruit_hot38_days
    return merged


def inner_years(test_year):
    return list(range(test_year - 3, test_year))


def run():
    check_snapshot()
    original_hash = hashlib.sha256((OUT / 'ridge_vpd_predictions.csv').read_bytes()).hexdigest()
    points, tables, envelope = terrain_tables()
    points.to_csv(DATA / 'terrain_selected_points.csv', index=False, encoding='utf-8-sig')
    base = load_panel().sort_values(['year_ce', 'province_code']).reset_index(drop=True)
    harvest = pd.read_csv(DATA / 'harvest_monthly.csv', dtype={'province_code': str})
    harvest = harvest[harvest.year_ce.ge(2010)]
    if (harvest.duplicated(KEYS + ['month_number']).any() or not harvest.month_number.between(1, 12).all()
            or not np.isfinite(harvest.tonnes).all() or (harvest.tonnes < 0).any()):
        raise ValueError('Invalid harvest source')
    raw = read_csv(DATA / 'weather_daily.csv')
    weather, vpd, daily = weather_series(raw), vpd_series(raw), daily_arrays(raw)
    configs = [dict(group=g, age_days=a, alpha=p, config_id=i)
               for i, (g, a, p) in enumerate(product(GROUPS, AGES, ALPHAS))]
    cache, predictions = {}, {}

    def bank_for(year):
        seasons = training_seasons(harvest, year - 1)
        signature = tuple((p, tuple(seasons[p])) for p in PROVINCES)
        if signature not in cache:
            print('Building terrain bank:', seasons, flush=True)
            bank = make_bank(base, seasons, weather, vpd, daily)
            arms = {}
            for age, frame in bank.items():
                for p, field in product(PROVINCES, EXTREMES):
                    frame[f'province_{p}_x_{field}'] = frame.province_code.eq(p).astype(float) * frame[field]
                arms[age] = {None: frame, **{s: add_terrain(frame, t) for s, t in tables.items()}}
            cache[signature] = arms
        return cache[signature], seasons

    def estimate(year, config):
        key = year, config['config_id']
        if key not in predictions:
            bank, _ = bank_for(year)
            source, extra = GROUPS[config['group']]
            frame = bank[config['age_days']][source]
            values, model = predict_year(frame, year, FEATURES + extra, config['alpha'])
            actual = frame.loc[frame.year_ce.eq(year), TARGET]
            predictions[key] = values, model, mae(actual, values) if len(actual) else None
        return predictions[key]

    records, tuning, choices, final, evidence_final = [], [], [], None, None
    for year in range(2017, 2027):
        scores = [(float(np.mean([estimate(v, c)[2] for v in inner_years(year)])), c) for c in configs]
        tuning.extend(dict(test_year=year, inner_mae_kg_rai=s, **c) for s, c in scores)
        for policy in (*GROUPS, 'inner_selected', 'evidence_selected'):
            eligible = [(s, c) for s, c in scores if policy == 'inner_selected' or c['group'] == policy
                        or (policy == 'evidence_selected' and not c['group'].startswith('supplied'))]
            score, config = min(eligible, key=lambda item: item[0])
            values, model, _ = estimate(year, config)
            choices.append(dict(policy=policy, test_year=year, inner_mae_kg_rai=score, **config))
            bank, seasons = bank_for(year)
            source, extra = GROUPS[config['group']]
            frame = bank[config['age_days']][source]
            if year == 2026:
                bundle = dict(config=config, parameters=model, season_months=seasons,
                              predictors=FEATURES + extra, train_end=2025, provinces=PROVINCES,
                              terrain_table=tables[source].to_dict('records') if source else None,
                              mode='Exploratory conditional estimate; not an operational forecast or main-model promotion')
                if policy == 'inner_selected':
                    final = bundle
                elif policy == 'evidence_selected':
                    evidence_final = bundle
                continue
            test = frame[frame.year_ce.eq(year)]
            for row, value in zip(test.itertuples(), values):
                records.append(dict(policy=policy, province_code=row.province_code, province_name=row.province_name,
                                    year_ce=year, actual_kg_rai=getattr(row, TARGET), predicted_kg_rai=float(value), **config))
        print('Completed terrain test origin:', year, flush=True)
    frame = pd.DataFrame(records)
    control = frame[frame.policy.eq('baseline')].merge(load_csv('predictions.csv'), on=KEYS,
                                                      validate='one_to_one', suffixes=('', '_old'))
    if len(control) != 45 or not np.allclose(control.predicted_kg_rai, control.predicted_kg_rai_old, rtol=1e-10, atol=1e-7):
        raise ValueError('Original baseline not reproduced')
    results = []
    for policy, group in frame.groupby('policy', sort=False):
        if len(group) != 45 or group.duplicated(KEYS).any():
            raise ValueError('Require 45 paired predictions per policy')
        comparison = {}
        for comparator in ('baseline', 'weather_control'):
            paired = group.merge(frame[frame.policy.eq(comparator)][KEYS + ['predicted_kg_rai']],
                                 on=KEYS, validate='one_to_one', suffixes=('', '_control'))
            comparison[comparator] = paired_year_bootstrap(paired, 'predicted_kg_rai_control')[0]
        results.append(dict(policy=policy, **metrics(group.actual_kg_rai, group.predicted_kg_rai),
                            paired_uncertainty=comparison,
                            by_year=[dict(year_ce=int(y), **metrics(g.actual_kg_rai, g.predicted_kg_rai))
                                     for y, g in group.groupby('year_ce')],
                            by_province=[dict(province_name=p, **metrics(g.actual_kg_rai, g.predicted_kg_rai))
                                         for p, g in group.groupby('province_name')]))
    if hashlib.sha256((OUT / 'ridge_vpd_predictions.csv').read_bytes()).hexdigest() != original_hash:
        raise ValueError('Main baseline changed')
    result = dict(results=results, configurations=configs, candidate_count=len(configs), fold_choices=choices,
                  final_inner_selected_model=final, final_evidence_selected_model=evidence_final,
                  baseline_reproduced=True, input_sha256=hashes(),
                  terrain_sha256=hashlib.sha256(RAW.read_bytes()).hexdigest(),
                  supplied_values=POINTS, terrain_aggregation='Unweighted mean of two selected point proxies per province',
                  source_url=ENDPOINT, downloaded_utc=envelope['downloaded_utc'],
                  source_docs='https://www.opentopodata.org/datasets/srtm/',
                  code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), Path(__file__).parent / 'common.py',
                                         Path(__file__).parent / 'experiment_weather_shocks.py',
                                         Path(__file__).parent / 'step5_evaluate_result.py',
                                         ROOT / 'tools/compare_harvest_stage_yield.py',
                                         ROOT / 'tools/analyze_harvest_backcast.py', ROOT / 'tools/train_monthly_production.py')},
                  validation='Outer 2017-2025; inner three prior years, training strictly before each validation year; train-only scaling/seasons',
                  target='All-cultivar production tonnes * 1000 / bearing rai',
                  limitations=['Supplied elevation/slope values have no verifiable DEM provenance; scenario only.',
                               'SRTM 3x3 sampled patches at supplied coordinates are not district/orchard spatial averages.',
                               'Equal two-point province weights are not bearing-area weights; point selection not independently validated.',
                               'DEM is static terrain, not measured soil moisture, groundwater or irrigation.',
                               'Static province terrain is redundant with province indicators; gains may reflect Ridge regularization.',
                               'Interactions are statistical hypotheses, with no imposed signs or causal interpretation.',
                               'Only five provinces; all targets previously examined, no independent confirmatory holdout.',
                               'Bootstrap is descriptive conditional on fixed predictions, no search/refit correction.',
                               'No main model, PDF or dashboard changed.'])
    frame.to_csv(OUT / 'terrain_predictions.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(tuning).to_csv(OUT / 'terrain_tuning.csv', index=False, encoding='utf-8-sig')
    (OUT / 'terrain_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    (OUT / 'terrain_candidate_model.json').write_text(json.dumps(evidence_final, ensure_ascii=False, indent=2,
                                                                allow_nan=False), encoding='utf-8')
    pd.DataFrame(columns=['province_code', 'year_ce', 'age_days', 'season_months', *FEATURES, *EXTREMES,
                          'bearing_rai']).to_csv(OUT / 'terrain_future_input_template.csv', index=False, encoding='utf-8-sig')
    summary = pd.DataFrame(results)[['policy', 'mae_kg_rai', 'rmse_kg_rai']]
    summary.to_csv(OUT / 'terrain_summary.csv', index=False, encoding='utf-8-sig')
    print(summary.to_string(index=False))
    return result


def infer_candidate(bundle, frame):
    required = {'province_code', 'year_ce', 'age_days', 'season_months', *FEATURES, *EXTREMES}
    if (frame.empty or not required.issubset(frame.columns) or set(frame.columns) - required - {'bearing_rai'}
            or frame.duplicated(KEYS).any() or not frame.province_code.isin(PROVINCES).all()
            or bundle['provinces'] != PROVINCES or bundle['config']['group'].startswith('supplied')):
        raise ValueError('Invalid input/schema; no targets or unverified supplied terrain accepted')
    numeric = frame[['year_ce', 'age_days', *FEATURES, *EXTREMES]].to_numpy(float)
    if (not np.isfinite(numeric).all() or not np.equal(frame.year_ce, np.floor(frame.year_ce)).all()
            or not frame.year_ce.gt(bundle['train_end']).all()
            or not frame.age_days.eq(bundle['config']['age_days']).all()):
        raise ValueError('Invalid numeric input, year or stage age')
    nonnegative = [f for f in FEATURES + EXTREMES if f != 'fruit_90_to_harvest_temperature_c']
    if ((frame[nonnegative] < 0).any().any() or not frame.early_fruit_hot38_days.le(30).all()
            or not frame.fruit_90_to_harvest_temperature_c.between(-100, 70).all()):
        raise ValueError('Weather predictors outside physical ranges')
    expected = frame.province_code.map(lambda p: ','.join(map(str, bundle['season_months'][p])))
    if not frame.season_months.eq(expected).all():
        raise ValueError('Weather stages must match trained season_months')
    frame = frame.copy()
    source, extra = GROUPS[bundle['config']['group']]
    if bundle['predictors'] != FEATURES + extra:
        raise ValueError('Model predictor contract mismatch')
    if source:
        frame = add_terrain(frame, pd.DataFrame(bundle['terrain_table']))
    for p, field in product(PROVINCES, EXTREMES):
        frame[f'province_{p}_x_{field}'] = frame.province_code.eq(p).astype(float) * frame[field]
    x = design(frame, PROVINCES, bundle['predictors'])
    params = bundle['parameters']
    arrays = [np.asarray(params[k], float) for k in ('mean', 'scale', 'coef')]
    if (any(a.shape != (x.shape[1],) or not np.isfinite(a).all() for a in arrays)
            or (arrays[1] <= 0).any() or not np.isfinite(params['intercept'])):
        raise ValueError('Invalid model parameters')
    output = frame[KEYS].copy()
    output['predicted_kg_rai'] = predict(params, x)
    output['status'] = 'Exploratory conditional estimate, not validated live forecast'
    if 'bearing_rai' in frame:
        if not np.isfinite(frame.bearing_rai).all() or (frame.bearing_rai <= 0).any():
            raise ValueError('Require positive finite bearing area')
        output['predicted_tonnes_conditional'] = output.predicted_kg_rai * frame.bearing_rai / 1000
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch-only', action='store_true', help='Validate/cache terrain without training')
    parser.add_argument('--predict-input', type=Path, help='Complete stage-weather CSV matching candidate contract')
    parser.add_argument('--output', type=Path, help='New prediction CSV path (existing files will not be overwritten)')
    args = parser.parse_args()
    if args.predict_input:
        if args.fetch_only or args.output is None or args.output.exists():
            parser.error('Prediction requires --output pointing to a new file and cannot combine --fetch-only')
        bundle = json.loads((OUT / 'terrain_candidate_model.json').read_text(encoding='utf-8'))
        frame = pd.read_csv(args.predict_input, dtype={'province_code': str, 'season_months': str})
        infer_candidate(bundle, frame).to_csv(args.output, index=False, encoding='utf-8-sig')
    elif args.fetch_only:
        points, _, _ = terrain_tables()
        points.to_csv(DATA / 'terrain_selected_points.csv', index=False, encoding='utf-8-sig')
        print(points[['district_label', 'supplied_elevation_m', 'srtm_elevation_m', 'supplied_slope_pct', 'srtm_slope_pct']].to_string(index=False))
    else:
        run()
