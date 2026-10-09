"""Dated province estimates and private orchard snapshot for the existing local dashboard."""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from durian_model.common import (DATA, FEATURES, check_snapshot, infer, load_json,
                                weather_series, vpd_series)
from analyze_harvest_backcast import month_days, exposure
from compare_harvest_stage_yield import vpd_window

ROOT = Path(__file__).resolve().parents[1]


def orchard_snapshot(now=None):
    now = now or datetime.now(timezone.utc)
    path = ROOT / 'data/processed/orchard_live/live_report.json'
    if not path.exists():
        return dict(status='missing', message='ยังไม่มี snapshot สวน กรุณา export และรัน orchard_live_model.py')
    report = json.loads(path.read_text(encoding='utf-8'))
    age = (now - datetime.fromisoformat(report['snapshot_last_sensor_th'])).total_seconds() / 60
    # Only curated summaries; no device IDs, coordinates, keys or raw private tables.
    return dict(status='fresh_snapshot' if 0 <= age <= 60 else 'stale_snapshot',
                sensor_time=report['snapshot_last_sensor_th'], age_minutes=age,
                soil_percent=report['latest_soil_sensor_percent'], vpd_kpa=report['latest_outdoor_vpd_kpa'],
                prediction=report['live'], mode='local_snapshot_not_direct_sheet_connection')


def province_estimate(code, year, fetch_weather, today=None):
    today = today or date.today()
    check_snapshot()
    model = load_json('final_model.json')
    if code not in model['provinces'] or year not in (today.year, today.year + 1) or year <= model['train_end']:
        raise ValueError('เลือกหนึ่งใน 5 จังหวัด และปีปัจจุบันหรือปีถัดไปหลังปีฝึก')
    days = [d for m in model['season_months'][code] for d in month_days(year, m)]
    start = min(days) - timedelta(days=model['age_days'] + 90)
    end = max(days) - timedelta(days=1)
    result = dict(province_code=code, year_ce=year, as_of=today.isoformat(),
                  season_months=model['season_months'][code], age_days=model['age_days'],
                  weather_start=start.isoformat(), weather_end=end.isoformat(),
                  resolution='province yield; one reference weather grid; all cultivars',
                  predicted_kg_rai=None, predicted_tonnes=None)
    annual = pd.read_csv(DATA / 'production_annual.csv', dtype={'province_code': str})
    prior = annual[annual.province_code.eq(code) & annual.year_ce.eq(year - 1)]
    if prior.empty:
        return dict(**result, status='pending_prior_yield', message='ยังไม่มีผลผลิตปีก่อนที่ตรวจสอบแล้ว ไม่ใช้ค่าทำนายแทนยอดจริง')
    if end >= today:
        return dict(**result, status='pending_future_weather', message='หน้าต่างยังไม่จบ ต้องเชื่อมพยากรณ์/สถานการณ์สำหรับวันที่เหลือก่อนคำนวณ ไม่เติมศูนย์หรืออ้างอากาศอนาคตเป็นข้อมูลจริง')
    points = pd.read_csv(DATA / 'reference_points.csv', dtype={'province_code': str})
    point = points[points.province_code.eq(code)].iloc[0]
    payload = fetch_weather(float(point.weather_latitude), float(point.weather_longitude), start, end)
    rows = [dict(**row, province_code=code) for row in payload['rows']]
    series = weather_series(rows)[code]
    values = dict(province_code=code, year_ce=year,
                  previous_yield_kg_rai=float(prior.iloc[0].yield_kg_per_rai_calculated))
    windows = [('pre_bloom_90d', -90, 0, 'rain_mm'), ('fruit_0_29d', 0, 30, 'rain_mm'),
               ('fruit_30_59d', 30, 60, 'rain_mm'), ('fruit_60_89d', 60, 90, 'solar_mj_m2_day'),
               ('fruit_90_to_harvest', 90, model['age_days'], 'temperature_c')]
    for name, first, last, field in windows:
        values[name + '_' + field] = exposure(series, days, model['age_days'], first, last)[field]
    try:
        vpds = vpd_series(rows)[code]
        values['vpd_pre_bloom_mean_kpa'] = vpd_window(vpds, days, model['age_days'], -90, 0)[0]
        values['vpd_early_fruit_p90_kpa'] = vpd_window(vpds, days, model['age_days'], 0, 30)[1]
    except ValueError:
        values['vpd_pre_bloom_mean_kpa'] = values['vpd_early_fruit_p90_kpa'] = None
    result.update(weather_provenance=payload['provenance'], stale_cache=payload['stale_cache'])
    if any(values.get(f) is None for f in FEATURES):
        return dict(**result, status='missing_weather', message='อากาศในหน้าต่างไม่ครบ ยังไม่แสดงตัวเลขผลผลิต')
    predicted = float(infer(model, pd.DataFrame([values])).predicted_kg_rai.iloc[0])
    # A previous year's bearing area is not the current bearing area.
    return dict(**{**result, 'predicted_kg_rai': predicted}, status='retrospective_weather_estimate',
                message='ประมาณการจากอากาศที่เกิดแล้วหลังจบหน้าต่างฤดู ไม่ใช่พยากรณ์ก่อนเก็บเกี่ยว; ยังไม่มีพื้นที่ให้ผลปีนี้เพื่อแปลงเป็นตัน')
