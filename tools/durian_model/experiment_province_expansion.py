"""Phase 6A data preparation only. No estimator import or training entry point."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import experiment_rebaseline as rb
from availability_guard import timestamp
from experiment_issue_date import IssueWeather

NEW = ['21', '30', '77', '80', '85']
COHORTS = {'5': list(rb.PROVINCES), '10': list(rb.PROVINCES) + NEW}
ANCHORS = {**rb.ANCHORS, '21': '04-01', '30': '05-01', '77': '06-01', '80': '07-01', '85': '07-01'}
POINTS = {'21': [12.87429, 101.44464], '30': [14.96614, 102.07023],
          '77': [11.80445, 99.72466], '80': [8.57693, 99.70082], '85': [10.04423, 98.76673]}
PARAMS = ['T2M', 'T2M_MAX', 'T2M_MIN', 'RH2M', 'PRECTOTCORR', 'ALLSKY_SFC_SW_DWN', 'WS2M']
UNITS = {'T2M': 'C', 'T2M_MAX': 'C', 'T2M_MIN': 'C', 'RH2M': '%',
         'PRECTOTCORR': 'mm/day', 'ALLSKY_SFC_SW_DWN': 'MJ/m^2/day', 'WS2M': 'm/s'}
ROOT = rb.ROOT / 'research_data/province_expansion_inputs'
ANNUAL = rb.ROOT / 'research_data/thailand_comparison/production_province_year.csv'
MONTHLY = rb.ROOT / 'research_data/external/oae_2026-09-17/durian_monthly_province.xlsx'
INVENTORY = rb.OUT / 'expansion_coverage.csv'
URL = 'https://power.larc.nasa.gov/api/temporal/daily/point'


def write_json(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)


def write_csv(path, frame):
    with Path(path).open('x', encoding='utf-8-sig', newline='') as f:
        frame.to_csv(f, index=False)


def reserve(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('Unsafe run id')
    ROOT.mkdir(parents=True, exist_ok=True)
    destination = ROOT / run_id
    if destination.resolve().parent != ROOT.resolve() or (ROOT.resolve() != ROOT.absolute() and not rb.safe_temporary_root(ROOT)):
        raise ValueError('Unsafe input snapshot root')
    destination.mkdir(exist_ok=False)
    (destination / 'raw').mkdir()
    return destination


def check_annual(frame):
    rows = frame[frame.province_code.isin(COHORTS['10']) & frame.year_ce.between(2009, 2025)].copy()
    expected = {(p, y) for p in COHORTS['10'] for y in range(2009, 2026)}
    if (len(rows) != 170 or rows.duplicated(['province_code', 'year_ce']).any()
            or set(zip(rows.province_code, rows.year_ce)) != expected
            or not np.isfinite(rows[['production_tonnes', 'bearing_rai', rb.TARGET]].to_numpy(float)).all()
            or rows.bearing_rai.le(0).any() or rows.production_tonnes.lt(0).any()):
        raise ValueError('Incomplete/invalid target or lag source; never drop rows')
    if not np.allclose(rows[rb.TARGET], rows.production_tonnes * 1000 / rows.bearing_rai, rtol=1e-14, atol=1e-12):
        raise ValueError('Calculated yield differs from production / bearing area')
    for p in NEW:
        point = rows[rows.province_code.eq(p)].iloc[0]
        if [point.weather_latitude, point.weather_longitude] != POINTS[p]:
            raise ValueError('Frozen reference point changed')
    return rows.sort_values(['province_code', 'year_ce'])


def verify_calendar(annual):
    monthly = pd.read_excel(MONTHLY, sheet_name='durian_monthly')
    monthly['year_ce'] = pd.to_numeric(monthly.year) - 543
    # Same measure filter as audit_expansion: percentages are not tonnes.
    monthly = monthly[monthly.item.eq('ปริมาณผลผลิตรายเดือน')].copy()
    numbers = dict(zip(['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
        'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'], range(1, 13)))
    evidence = []
    for p in NEW:
        group = annual[annual.province_code.eq(p)]
        m = monthly[monthly.province_name.eq(group.province_name.iloc[0]) & monthly.year_ce.between(2004, 2009)].copy()
        if set(m.year_ce) != set(range(2004, 2010)) or m.duplicated(['year_ce', 'month']).any():
            raise ValueError('Incomplete pre-training monthly calendar source')
        totals = m.groupby('year_ce').data.sum(min_count=1)
        original = pd.read_csv(ANNUAL, dtype={'province_code': str})
        source = original[original.province_code.eq(p)].set_index('year_ce').production_tonnes.loc[totals.index]
        if ((totals - source).abs() > np.maximum(1., source * .005)).any():
            raise ValueError('Calendar source does not reconcile with annual')
        m['month_number'] = m.month.map(numbers)
        if m.month_number.isna().any():
            raise ValueError('Unknown calendar month')
        peak = int(m.groupby('month_number').data.sum().sort_index().idxmax())
        if f'{max(1, min(10, peak-1)):02d}-01' != ANCHORS[p]:
            raise ValueError('Pre-training calendar differs from approved anchor')
        evidence.append(dict(province_code=p, years=[2004, 2009], peak_month=peak,
            anchor=ANCHORS[p], reconciled_years=6, monthly_missing_not_filled=True))
    return evidence


def decode_weather(data, code, start, end):
    header = data['header']
    if header['time_standard'] != 'LST' or header['start'] != start or header['end'] != end:
        raise ValueError('Weather time-standard/date mismatch')
    if {k: data['parameters'][k]['units'] for k in PARAMS} != UNITS:
        raise ValueError('Weather units differ from original AG inputs')
    source = data['properties']['parameter']
    expected = set(pd.date_range(start, end).strftime('%Y%m%d'))
    if set(source) != set(PARAMS) or any(set(source[k]) != expected for k in PARAMS):
        raise ValueError('Missing parameter/date records')
    fill = header.get('fill_value', -999.)
    rows = [dict(province_code=code, date=pd.Timestamp(d).strftime('%Y-%m-%d'),
        **{k: (np.nan if source[k][d] == fill else source[k][d]) for k in PARAMS}) for d in sorted(expected)]
    frame = pd.DataFrame(rows)
    if not np.isfinite(frame[PARAMS].to_numpy(float)).all():
        raise ValueError('Missing/nonfinite weather; no fill or criteria relaxation')
    if (frame.RH2M.lt(0).any() or frame.RH2M.gt(100).any() or frame.T2M_MIN.gt(frame.T2M_MAX).any()
            or frame.PRECTOTCORR.lt(0).any() or frame.ALLSKY_SFC_SW_DWN.lt(0).any() or frame.WS2M.lt(0).any()):
        raise ValueError('Physically invalid weather values')
    return frame


def download(job, destination):
    code, start, end = job
    lat, lon = POINTS[code]
    args = dict(parameters=','.join(PARAMS), community='AG', latitude=lat, longitude=lon,
                start=start, end=end, format='JSON', **{'time-standard': 'LST'})
    response = requests.get(URL, params=args, timeout=55)
    response.raise_for_status()
    path = destination / 'raw' / f'{code}_{start}_{end}.json'
    with path.open('xb') as f:
        f.write(response.content)
    data = response.json()
    metadata = dict(province_code=code, point=POINTS[code], point_status='province reference proxy, not orchard',
        url=response.url, request=args, retrieved_utc=datetime.now(timezone.utc).isoformat(),
        sha256=rb.digest(path), header=data.get('header'), parameters=data.get('parameters'),
        publication_date=None, availability_status='unverified', historical_vintage_verified=False)
    write_json(path.with_suffix('.source.json'), metadata)
    frame = decode_weather(data, code, start, end)
    print(f'Weather complete: {code} {start}-{end} {len(frame)} days', flush=True)
    return frame, metadata


def features(annual, weather):
    keys = pd.DataFrame([(p, y) for p in COHORTS['10'] for y in rb.YEARS], columns=['province_code', 'year_ce'])
    builder = IssueWeather(weather.to_dict('records'))
    lookup = annual.set_index(['province_code', 'year_ce'])[rb.TARGET]
    values, lineage = [], []
    schedule = dict(kind='fixed_calendar', anchors=ANCHORS)
    for p, y in keys.itertuples(index=False, name=None):
        month = int(ANCHORS[p][:2])
        result, issue, available, traces = builder.features_with_lineage(p, y, list(range(month, month+3)), 60)
        if issue != rb.issue_date(schedule, p, y, 60) or set(result) != set(rb.FEATURES[1:]):
            raise ValueError('Feature/calendar mismatch')
        lag = float(lookup.loc[p, y-1])
        values.append(dict(province_code=p, year_ce=y, **result, previous_yield_kg_rai=lag))
        lineage.extend(dict(province_code=p, year_ce=y, issue_date=issue.isoformat(),
            weather_available_through=available.isoformat(), **t) for t in traces)
        lineage.append(dict(province_code=p, year_ce=y, feature=rb.FEATURES[0], value=lag,
            issue_date=issue.isoformat(), source_province=p, source_year=y-1,
            source_value_sha256=rb.digest_value([p, y-1, lag])))
    frame = pd.DataFrame(values)[['province_code', 'year_ce', *rb.FEATURES]]
    if len(lineage) != 1280 or not np.isfinite(frame[rb.FEATURES].to_numpy(float)).all():
        raise ValueError('Incomplete 160 row feature/lineage matrix')
    return frame, lineage


def prepare_folds(inputs, annual, lineage, manifest):
    traces = {(t['province_code'], t['year_ce'], t['feature']): t for t in lineage}
    if len(traces) != 1280 or len(lineage) != 1280:
        raise ValueError('Missing/duplicate lineage')
    lookup = annual.set_index(['province_code', 'year_ce'])[rb.TARGET]
    checks, folds = [], []
    def check(ref, role, cutoff, context, observation_end=None):
        record = manifest['records'][ref]
        if record.get('publication_date') and timestamp(record['publication_date']) > timestamp(cutoff):
            raise ValueError('Known future publication cannot be consumed')
        warnings = rb.check(record, role, record['source_version'], cutoff, 'exploratory', observation_end)
        checks.append(dict(**context, dependency=ref, role=role, cutoff=cutoff,
            observation_end=observation_end, source_version=record['source_version'], warnings=warnings))
    for outer in rb.OUTER_YEARS:
        for year in range(outer-3, outer+1):
            dates = {p: rb.midnight(rb.issue_date(manifest['schedule'], p, year, 60)) for p in COHORTS['10']}
            fit = min(dates.values())
            select = min(rb.midnight(rb.issue_date(manifest['schedule'], p, outer, 60)) for p in rb.PROVINCES)
            if fit != min(dates[p] for p in rb.PROVINCES):
                raise ValueError('Shared cutoff changed by expansion')
            for size, provinces in COHORTS.items():
                train_keys = {(p, y) for p in provinces for y in range(2010, year)}
                forecast_keys = {(p, year) for p in provinces}
                train = inputs[inputs.province_code.isin(provinces) & inputs.year_ce.lt(year)].copy()
                forecast = inputs[inputs.province_code.isin(provinces) & inputs.year_ce.eq(year)].copy()
                if set(zip(train.province_code, train.year_ce)) != train_keys or set(zip(forecast.province_code,forecast.year_ce)) != forecast_keys:
                    raise ValueError('Incomplete fold membership')
                context = dict(cohort=size, outer_year=outer, fold_year=year)
                check('issue_rule', 'issue_rule', fit, context)
                for role, frame in [('training_input',train), ('forecast_input',forecast)]:
                    for row in frame.to_dict('records'):
                        p, y = row['province_code'], row['year_ce']
                        cutoff = fit if role=='training_input' else dates[p]
                        rc = dict(**context, province_code=p, row_year=y, input_role=role)
                        for feature in rb.FEATURES:
                            t = traces[p,y,feature]
                            if t['value'] != row[feature]:
                                raise ValueError('Actual values differ from lineage')
                            rb.check_feature_lineage(t,y,t['issue_date'],cutoff,7)
                            refs = [f'annual_lag:{p}'] if feature==rb.FEATURES[0] else [f'power_observed:{p}',f'power_normals:{p}','issue_rule_feature']
                            for ref in refs:
                                end = f'{y-1}-12-31' if ref.startswith('annual_lag') else (max(t['observed_dates']) if ref.startswith('power_observed') and t['observed_dates'] else max(t['normal_dates']) if ref.startswith('power_normals') and t['normal_dates'] else None)
                                check(ref,'feature',cutoff,dict(**rc,feature=feature),end)
                        if role=='training_input':
                            check(f'training_labels:{p}','training_label',fit,rc,f'{y}-12-31')
                        else:
                            check(f'evaluation_target:{p}','evaluation_target',cutoff,rc)
                            if year<outer:
                                check(f'selection_labels:{p}','selection_label',select,rc,f'{y}-12-31')
                folds.append(dict(**context, fit_cutoff=fit, selection_cutoff=select, issue_dates=dates,
                    training_rows=len(train), forecast_rows=len(forecast),
                    selection_keys=[list(k) for k in sorted({(p,year) for p in rb.PROVINCES})],
                    training_labels_sha256=rb.digest_value([[p,y,float(lookup.loc[p,y])] for p,y in sorted(train_keys)])))
    return folds, checks


def run():
    # Import hash collector only, never its training execution path.
    from experiment_enso_training import protected_hashes, unchanged
    protected = protected_hashes()
    unchanged(protected)
    destination = reserve('phase6a_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    try:
        annual = check_annual(pd.read_csv(ANNUAL,dtype={'province_code':str}))
        inventory = pd.read_csv(INVENTORY,dtype={'province_code':str}).set_index('province_code')
        if not inventory.loc[NEW,'valid_2010_2016'].eq(7).all() or not inventory.loc[NEW,'valid_test_2017_2025'].eq(9).all():
            raise ValueError('Original inventory not complete')
        calendar = verify_calendar(annual)
        write_csv(destination/'annual.csv',annual)
        write_json(destination/'calendar_evidence.json',calendar)
        jobs = [(p,f'{start}0101',f'{end}1231') for p in NEW for start,end in [(2000,2009),(2010,2019),(2020,2025)]]
        with ThreadPoolExecutor(max_workers=2) as pool:
            fetched = list(pool.map(lambda job: download(job,destination),jobs))
        new_weather = pd.concat([x[0] for x in fetched],ignore_index=True).sort_values(['province_code','date'])
        write_csv(destination/'new_weather_daily.csv',new_weather)
        old = pd.read_csv(rb.DATA/'weather_daily.csv',dtype={'province_code':str})
        combined = pd.concat([old,new_weather],ignore_index=True)
        inputs,lineage = features(annual,combined)
        saved = pd.read_csv(rb.OUTPUT_ROOT/'20261010T131023246729Z/predictors.csv',dtype={'province_code':str}).sort_values(['province_code','year_ce'])
        original = inputs[inputs.province_code.isin(rb.PROVINCES)].sort_values(['province_code','year_ce'])
        if not np.allclose(saved[rb.FEATURES],original[rb.FEATURES],atol=1e-12,rtol=1e-14):
            raise ValueError('Original five province feature parity failed')
        original_annual = pd.read_csv(rb.DATA/'production_annual.csv',dtype={'province_code':str}).set_index(['province_code','year_ce'])
        for r in annual[annual.province_code.isin(rb.PROVINCES)].to_dict('records'):
            if r[rb.TARGET] != original_annual.loc[(r['province_code'],r['year_ce']),rb.TARGET]:
                raise ValueError('Original targets changed')
        schedule = dict(kind='fixed_calendar',anchors=ANCHORS,note='2026 experimental rule; no historical certification')
        records = {}
        for p in COHORTS['10']:
            for name,role in [('annual_lag','feature'),('training_labels','training_label'),('selection_labels','selection_label'),('evaluation_target','evaluation_target'),('power_observed','feature'),('power_normals','feature')]:
                source = destination/'annual.csv' if name.startswith(('annual','training','selection','evaluation')) else destination/'new_weather_daily.csv' if p in NEW else rb.DATA/'weather_daily.csv'
                records[f'{name}:{p}']=dict(role=role,province_code=p,path=str(source.relative_to(rb.ROOT)).replace('\\','/'),source_version=rb.digest(source),publication_date=None,availability_status='unverified',evidence={})
        for name,role in [('issue_rule','issue_rule'),('issue_rule_feature','feature')]:
            records[name]=dict(role=role,source_version=rb.schedule_version(schedule),publication_date=None,
                availability_status='unverified',created_at=datetime.now(timezone.utc).isoformat(),evidence={})
        manifest = dict(schema_version=1,mode='exploratory',schedule=schedule,records=records,
            arms={a:dict(cohort=size,features=list(rb.FEATURES) if weather else [rb.FEATURES[0]]) for a,size,weather in [('A','5',False),('B','5',True),('C','10',False),('D','10',True)]},
            selection_cohort=rb.PROVINCES,enso=False,grid=dict(depths=[2,3],seed=42,iterations=400,learning_rate=.03,l2_leaf_reg=10,loss_function='RMSE',boosting_type='Ordered',thread_count=1,allow_writing_files=False))
        folds,checks = prepare_folds(inputs,annual,lineage,manifest)
        write_csv(destination/'predictors.csv',inputs)
        write_json(destination/'feature_lineage.json',lineage)
        write_json(destination/'manifest.json',manifest)
        write_json(destination/'folds.json',folds)
        write_json(destination/'availability_checks.json',checks)
        write_json(destination/'source_metadata.json',[x[1] for x in fetched])
        write_json(destination/'evaluation_keys.json',dict(primary=[[p,y] for p in rb.PROVINCES for y in rb.OUTER_YEARS],secondary=[[p,y] for p in NEW for y in rb.OUTER_YEARS]))
        write_json(destination/'config.json',dict(code_sha256={str(p.relative_to(rb.ROOT)).replace('\\','/'):rb.digest(p) for p in [Path(__file__),Path(rb.__file__),Path(rb.__file__).with_name('experiment_issue_date.py'),Path(rb.__file__).with_name('availability_guard.py')]},
            source_sha256={str(p.relative_to(rb.ROOT)).replace('\\','/'):rb.digest(p) for p in [ANNUAL,MONTHLY,INVENTORY]},
            protocol_hash=rb.digest_value(manifest),protected_sha256=protected,weather_period=['2000-01-01','2025-12-31'],
            note='new weather minimum complete period; original weather untouched; no training'))
        write_json(destination/'readiness.json',dict(ready=True,training_performed=False,pit_certified=False,
            provinces=COHORTS['10'],new_daily_rows=len(new_weather),panel_rows=len(inputs),lineage_records=len(lineage),fold_contexts=len(folds),availability_checks=len(checks),primary_keys=45,secondary_keys=45))
        unchanged(protected)
        write_json(destination/'artifact_hashes.json',{str(p.relative_to(destination)).replace('\\','/'):rb.digest(p) for p in destination.rglob('*') if p.is_file()})
        print(f'Data preparation ready: {destination}',flush=True)
    except Exception as exc:
        write_json(destination/'failure.json',dict(ready=False,training_performed=False,error_type=type(exc).__name__,error=str(exc),pit_certified=False))
        unchanged(protected)
        print(f'STOP: {destination}: {exc}',flush=True)
        raise
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        run()
    else:
        parser.print_help()
