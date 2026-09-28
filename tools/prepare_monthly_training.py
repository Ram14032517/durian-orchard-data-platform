"""Reproducible offline CSV research export. Does not train or infer tree health."""
import calendar
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research_data/five_province_history'
OUT = BASE / 'training'
INPUTS = ['weather_monthly.csv', 'harvest_monthly.csv', 'reference_points.csv',
          'weather_daily.csv', 'production_annual.csv', 'soil_properties_by_district.csv',
          'phenology_evidence.json', 'PHENOLOGY_SOURCES_TH.md']
WEATHER = ['temperature_c', 'rain_mm', 'humidity_pct', 'solar_mj_m2_day']
FEATURES = ['province_code', 'month'] + ['lag1_' + k for k in WEATHER]

def read_csv(name):
    with (BASE / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def keyed(rows, month_key):
    result = {}
    for row in rows:
        key = (row['province_code'], int(row['year_ce']), int(row[month_key]))
        if key in result:
            raise ValueError(f'Duplicate key: {key}')
        result[key] = row
    return result

def previous_month(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)

def split_for(year):
    if year <= 2021:
        return 'train'
    if year <= 2023:
        return 'validation'
    if year <= 2025:
        return 'test'
    return 'future_holdout'

def build_rows():
    weather = keyed(read_csv('weather_monthly.csv'), 'month')
    harvest = keyed(read_csv('harvest_monthly.csv'), 'month_number')
    names = {r['province_code']: r['province_name'] for r in read_csv('reference_points.csv')}
    rows = []
    for code, year, month in sorted(set(weather) | set(harvest)):
        py, pm = previous_month(year, month)
        lag = weather.get((code, py, pm), {})
        target = harvest.get((code, year, month), {}).get('tonnes', '')
        expected = calendar.monthrange(py, pm)[1]
        full = (lag.get('days_temperature') == str(expected)
                and lag.get('days_rain') == str(expected))
        missing = [k for k in WEATHER if lag.get(k, '') == '']
        reasons = []
        if target == '': reasons.append('no_target_record')
        if not full: reasons.append('incomplete_lag_temperature_or_rain')
        if missing: reasons.append('missing_lag_feature')
        row = dict(province_code=code, province_name=names[code], year_ce=year,
                   month=month, target_month=f'{year:04d}-{month:02d}',
                   feature_month=f'{py:04d}-{pm:02d}', target_production_tonnes=target)
        row.update({'lag1_' + k: lag.get(k, '') for k in WEATHER})
        row.update(lag1_temperature_days=lag.get('days_temperature', ''),
                   lag1_rain_days=lag.get('days_rain', ''), lag1_expected_days=expected,
                   eligible_for_baseline=int(not reasons), exclusion_reason=';'.join(reasons),
                   suggested_split=split_for(year))
        rows.append(row)
    return rows

def file_info(path):
    return dict(path=path.relative_to(BASE).as_posix(), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def main():
    OUT.mkdir(exist_ok=True)
    rows = build_rows()
    panel = OUT / 'monthly_model_panel.csv'
    with panel.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    eligible = [r for r in rows if r['eligible_for_baseline']]
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(),
        purpose='Retrospective monthly province-level production baseline; not tree health or causal effects',
        rows=len(rows), eligible_rows=len(eligible),
        eligible_by_split={s: sum(r['suggested_split'] == s for r in eligible)
                          for s in ['train', 'validation', 'test', 'future_holdout']},
        feature_allowlist=FEATURES, target='target_production_tonnes',
        grain='one province and target calendar month; all durian varieties',
        source_urls=['https://power.larc.nasa.gov/docs/services/api/temporal/daily/',
                     'https://catalog.oae.go.th/dataset/durian_product_month',
                     'https://catalog.oae.go.th/dataset/durian_product'],
        limitations=['Not a point-in-time backtest: source publication latency and revisions unknown',
                     'Only temperature and rain day coverage audited; RH and solar only checked nonmissing',
                     'Unreported harvest months remain missing, not zero; seasonal selection bias remains',
                     'No local sensor, disease, fruit-drop or soil-to-yield labels included'],
        inputs=[file_info(BASE / name) for name in INPUTS], output=file_info(panel))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    with ZipFile(OUT / 'training_bundle.zip', 'w', ZIP_DEFLATED) as archive:
        for name in INPUTS:
            archive.write(BASE / name, 'sources/' + name)
        for name in ['monthly_model_panel.csv', 'manifest.json', 'README_TH.md']:
            archive.write(OUT / name, name)
    print(json.dumps({k: manifest[k] for k in ['rows', 'eligible_rows', 'eligible_by_split']}, indent=2))

if __name__ == '__main__':
    main()
