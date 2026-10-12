"""Backcast reported harvest cohorts and their weather exposure; descriptive only."""
import calendar
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1] / 'research_data/five_province_history'
AGES = (120, 130, 140, 150)
FIELDS = {'temperature_c': 'T2M', 'rain_mm': 'PRECTOTCORR',
          'humidity_pct': 'RH2M', 'solar_mj_m2_day': 'ALLSKY_SFC_SW_DWN',
          'wind_ms': 'WS2M'}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def month_days(year, month):
    first = date(year, month, 1)
    return [first + timedelta(days=i) for i in range(calendar.monthrange(year, month)[1])]


def exposure(weather, harvest_days, age, start, stop):
    """Equal possible harvest days; [start, stop) days since assumed full bloom."""
    if not (isinstance(age, int) and 90 <= age <= 180 and start < stop <= age):
        raise ValueError('Invalid fruit age or stage window')
    first, last, matrix = weather
    indexes = np.array([d.toordinal() for d in harvest_days])[:, None] - age
    indexes = indexes + np.arange(start, stop)[None, :] - first
    in_range = (indexes >= 0) & (indexes <= last - first)
    values = np.full((*indexes.shape, len(FIELDS)), np.nan)
    values[in_range] = matrix[indexes[in_range]]
    result = {}
    for i, field in enumerate(FIELDS):
        valid = np.isfinite(values[:, :, i])
        result[field + '_coverage_pct'] = float(valid.mean() * 100)
        result[field] = None
        if valid.all():
            result[field] = float(values[:, :, i].sum(axis=1).mean()
                                  if field == 'rain_mm' else values[:, :, i].mean())
    result['solar_total_mj_m2'] = (result['solar_mj_m2_day'] * (stop - start)
                                  if result['solar_mj_m2_day'] is not None else None)
    return result


def weather_series(rows):
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        key = row['province_code'], row['date']
        if key in seen:
            raise ValueError(f'Duplicate weather: {key}')
        seen.add(key)
        ordinal = date.fromisoformat(row['date']).toordinal()
        values = [np.nan if row[source] is None or row[source] == '' else float(row[source])
                  for source in FIELDS.values()]
        if any(np.isinf(values)) or any(v <= -900 for v in values):
            raise ValueError(f'Invalid weather: {key}')
        if (np.isfinite(values[2]) and not 0 <= values[2] <= 100
                or any(np.isfinite(values[i]) and values[i] < 0 for i in (1, 3, 4))):
            raise ValueError(f'Invalid weather units/range: {key}')
        grouped[key[0]].append((ordinal, values))
    series = {}
    for code, records in grouped.items():
        first, last = min(d for d, _ in records), max(d for d, _ in records)
        matrix = np.full((last - first + 1, len(FIELDS)), np.nan)
        for ordinal, values in records:
            matrix[ordinal - first] = values
        series[code] = first, last, matrix
    return series


def peak_months(cohorts):
    # Reported tonnes only: absent months remain unknown, even inside this window.
    totals = {r['month_number']: r['tonnes'] for r in cohorts}
    start = max(range(1, 11), key=lambda m: sum(totals.get(n, 0) for n in range(m, m + 3)))
    return list(range(start, start + 3))


def summarize(cohorts, annual, scope, main_months):
    selected = [r for r in cohorts if scope == 'all_reported' or r['month_number'] in main_months]
    total = sum(r['tonnes'] for r in selected)
    reported = sum(r['tonnes'] for r in cohorts)
    production = float(annual['production_tonnes']) if annual else None
    bearing = float(annual['bearing_rai']) if annual and annual['bearing_rai'] else None
    result = {k: cohorts[0][k] for k in ('province_code', 'province_name', 'year_ce', 'age_days')}
    result.update(scope=scope, main_month_start=main_months[0], main_month_end=main_months[-1],
                  reported_months=len(cohorts), selected_reported_months=len(selected),
                  selected_tonnes=total, reported_tonnes=reported,
                  selected_share_reported_pct=100 * total / reported,
                  annual_production_tonnes=production, bearing_rai=bearing,
                  annual_yield_kg_rai=production * 1000 / bearing if bearing and bearing > 0 else None,
                  monthly_to_annual_pct=100 * reported / production if production and production > 0 else None,
                  bloom_start=min(r['bloom_start'] for r in selected),
                  bloom_end=max(r['bloom_end'] for r in selected), forecast_feature_eligible=False)
    for field in cohorts[0]:
        if field.startswith(('pre_bloom_', 'fruit_')):
            values = [r[field] for r in selected]
            result[field] = (sum(r['tonnes'] * r[field] for r in selected) / total
                             if all(v is not None for v in values) else None)
    return result


def prepare_backcast(base=BASE):
    inputs = ['harvest_monthly.csv', 'production_annual.csv', 'weather_daily.csv', 'reference_points.csv']
    names = {r['province_code']: r['province_name'] for r in read_csv(base / inputs[3])}
    annual_rows = read_csv(base / inputs[1])
    annual = {(r['province_code'], int(r['year_ce'])): r for r in annual_rows}
    if len(annual) != len(annual_rows):
        raise ValueError('Duplicate annual production')
    weather = weather_series(read_csv(base / inputs[2]))
    harvest = defaultdict(list)
    seen = set()
    for row in read_csv(base / inputs[0]):
        code, year, month = row['province_code'], int(row['year_ce']), int(row['month_number'])
        tonnes = float(row['tonnes'])
        if (code, year, month) in seen or not np.isfinite(tonnes) or tonnes < 0 or not 1 <= month <= 12:
            raise ValueError(f'Invalid/duplicate harvest: {code} {year} {month}')
        seen.add((code, year, month))
        if tonnes > 0:
            harvest[code, year].append(dict(province_code=code, year_ce=year, month_number=month, tonnes=tonnes))
    monthly, yearly = [], []
    for (code, year), cohorts in sorted(harvest.items()):
        main = peak_months(cohorts)
        total = sum(r['tonnes'] for r in cohorts)
        for age in AGES:
            scenario = []
            for cohort in sorted(cohorts, key=lambda r: r['month_number']):
                days = month_days(year, cohort['month_number'])
                row = dict(cohort, province_name=names[code], age_days=age,
                           harvest_share_pct=100 * cohort['tonnes'] / total,
                           in_main_peak3=cohort['month_number'] in main,
                           bloom_start=(days[0] - timedelta(days=age)).isoformat(),
                           bloom_end=(days[-1] - timedelta(days=age)).isoformat())
                windows = {'pre_bloom_90d': (-90, 0), 'fruit_full': (0, age),
                           'fruit_0_29d': (0, 30), 'fruit_30_59d': (30, 60),
                           'fruit_60_89d': (60, 90), 'fruit_90_to_harvest': (90, age)}
                for label, (start, stop) in windows.items():
                    row.update({label + '_' + k: v for k, v in exposure(weather[code], days, age, start, stop).items()})
                scenario.append(row)
            monthly.extend(scenario)
            for scope in ('all_reported', 'main_peak3'):
                yearly.append(summarize(scenario, annual.get((code, year)), scope, main))
    info = dict(age_scenarios_days=list(AGES), monthly_rows=len(monthly), annual_scenario_rows=len(yearly),
                province_years=len(harvest), year_min=min(y for _, y in harvest), year_max=max(y for _, y in harvest),
                stages={'pre_bloom_90d': '90 วันก่อนดอกบานสมมติ', 'fruit_full': 'ดอกบานสมมติถึงก่อนเก็บเกี่ยว',
                        'fruit_0_29d': 'อายุ 0–29 วัน', 'fruit_30_59d': 'อายุ 30–59 วัน',
                        'fruit_60_89d': 'อายุ 60–89 วัน', 'fruit_90_to_harvest': 'อายุ 90 วันถึงก่อนเก็บเกี่ยว'},
                weather_scope='NASA POWER province reference point; LST; not bearing-area spatial mean',
                cultivar_scope='OAE monthly/annual production includes all cultivars; Monthong age scenarios only',
                forecast_feature_eligible=False,
                methods=['Full bloom = harvest day minus assumed age; every day in each reported month is equally possible',
                         'Stage windows are analytical bins, not observed physiological stages',
                         'Peak3 = three consecutive calendar months with greatest reported tonnes, separately for each province-year',
                         'Weather means and expected rain/radiation totals are averaged over possible harvest dates, then weighted by monthly tonnes',
                         'Monthly/annual reconciliation is reported; missing harvest months are not observed zero',
                         'Missing weather makes that feature null; per-field exposure coverage remains available',
                         'Realized harvest timing/shares are outcome information: descriptive retrospective analysis, not prospective forecast features',
                         'Annual yield denominator is bearing area; new non-bearing planted area is excluded',
                         'Temporal harvest weights do not replace spatial bearing-area weights; soil/crop maps do not identify tree age'],
                research_urls=['https://kukr.lib.ku.ac.th/KPS/Detail/info/276150',
                               'https://doi.org/10.3390/horticulturae11040432',
                               'https://www.opsmoac.go.th/chiangrai-dwl-files-472791791910'],
                inputs={name: hashlib.sha256((base / name).read_bytes()).hexdigest() for name in inputs})
    output = base / 'training'
    output.mkdir(exist_ok=True)
    for name, rows in [('harvest_backcast_monthly.csv', monthly), ('harvest_backcast_annual.csv', yearly)]:
        with (output / name).open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    (output / 'harvest_backcast_info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    compact = ['province_code', 'year_ce', 'month_number', 'tonnes', 'age_days', 'harvest_share_pct',
               'in_main_peak3', 'bloom_start', 'bloom_end', 'fruit_full_rain_mm', 'fruit_full_temperature_c']
    return dict(info=info, annual=yearly, monthly=[{k: r[k] for k in compact} for r in monthly])


if __name__ == '__main__':
    result = prepare_backcast()
    print(json.dumps({k: result['info'][k] for k in ('province_years', 'year_min', 'year_max', 'monthly_rows', 'annual_scenario_rows')}, indent=2))
