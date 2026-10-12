"""Six-hour soil-sensor forecast using causally available readings and saved TMD uploads.

Not a yield, root-zone stress, irrigation-dose or disease model. Raw tables stay intact.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from clean_stale_weather import SIGNATURE, WEATHER
from train_monthly_production import fit_ridge

HOURS = 6
BASE = ['soil', 'soil_delta_3h', 'soil_temperature_c', 'hour_sin', 'hour_cos']
EXTRA = ['vpd_kpa', 'forecast_vpd_mean_kpa', 'forecast_rain_max_mm', 'forecast_temp_max_c']


def vpd(temperature, humidity):
    t, rh = np.asarray(temperature, float), np.asarray(humidity, float)
    return np.where(np.isfinite(t) & np.isfinite(rh) & (t >= -10) & (t <= 60)
                    & (rh >= 0) & (rh <= 100), .6108 * np.exp(17.27 * t / (t + 237.3)) * (1 - rh / 100), np.nan)


def prepare_readings(raw):
    df = raw.copy()
    df['time'] = pd.to_datetime(df.recorded_at, utc=True, errors='raise', format='mixed')
    if (df.empty or df.time.isna().any() or df.device_id.isna().any()
            or df.event_id.isna().any() or df.device_id.nunique() != 1 or df.event_id.duplicated().any()
            or df.duplicated(['device_id', 'time']).any()):
        raise ValueError('Require one device and unique events/timestamps')
    df = df.sort_values('time').reset_index(drop=True)
    for field in set(SIGNATURE + WEATHER + ['soil_moisture_percent', 'soil_temperature_c']):
        df[field] = pd.to_numeric(df[field], errors='coerce')
    complete = df[SIGNATURE].notna().all(axis=1)
    same = df[SIGNATURE].eq(df[SIGNATURE].shift()).all(axis=1) & complete & complete.shift(fill_value=False)
    gap = df.time.diff().dt.total_seconds().div(60)
    run = (~same | gap.gt(30)).cumsum()
    start = df.groupby(run).time.transform('min')
    # Online rule only flags this row after 60 elapsed minutes; never revises preceding rows.
    df['weather_stale_online'] = complete & (df.time - start).dt.total_seconds().ge(3600)
    df.loc[df.weather_stale_online, WEATHER] = np.nan
    df.loc[~df.soil_moisture_percent.between(0, 100), 'soil_moisture_percent'] = np.nan
    df.loc[~df.soil_temperature_c.between(-10, 60), 'soil_temperature_c'] = np.nan
    df['vpd_kpa'] = vpd(df.outdoor_temperature_c, df.outdoor_humidity_percent)
    indexed = df.set_index('time')
    hourly = indexed[['soil_moisture_percent', 'soil_temperature_c', 'vpd_kpa']].resample('1h', closed='right', label='right').mean()
    counts = indexed[['soil_moisture_percent', 'soil_temperature_c', 'vpd_kpa']].resample('1h', closed='right', label='right').count()
    hourly = hourly.where(counts.ge(3)).rename(columns={'soil_moisture_percent': 'soil'})
    hourly['soil_delta_3h'] = hourly.soil - hourly.soil.shift(3)
    history = pd.concat([hourly.soil.shift(i) for i in range(4)], axis=1)
    hourly.loc[~history.notna().all(axis=1), 'soil_delta_3h'] = np.nan
    hour = hourly.index.tz_convert('Asia/Bangkok').hour
    hourly['hour_sin'], hourly['hour_cos'] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
    return df, hourly


def prepare_forecasts(raw):
    frame = raw.copy()
    if not frame.forecast_time.astype(str).str.contains(r'(?:Z|[+-]\d\d:\d\d)$', regex=True).all():
        raise ValueError('Forecast times require explicit UTC offsets; no guessing timezone')
    frame['valid'] = pd.to_datetime(frame.forecast_time, utc=True, errors='raise', format='mixed')
    issued = pd.to_datetime(frame.issued_at, utc=True, errors='raise', format='mixed')
    received = pd.to_datetime(frame.received_at, utc=True, errors='raise', format='mixed')
    if frame['valid'].isna().any() or issued.isna().any() or received.isna().any():
        raise ValueError('Forecast availability and valid times cannot be missing')
    frame['available'] = pd.concat([issued, received], axis=1).max(axis=1)
    frame['issued'] = issued
    if frame[['source', 'issued', 'valid']].duplicated().any():
        raise ValueError('Duplicate forecast-vintage keys')
    for field in ['temperature_c', 'humidity_percent', 'rain_mm']:
        frame[field] = pd.to_numeric(frame[field], errors='raise')
    frame['forecast_vpd_kpa'] = vpd(frame.temperature_c, frame.humidity_percent)
    frame.loc[frame.rain_mm.lt(0), 'rain_mm'] = np.nan
    return frame


def forecast_at(frame, origin):
    future = pd.date_range(origin + pd.Timedelta(hours=1), periods=HOURS, freq='1h')
    eligible = frame[frame.available.le(origin) & frame.valid.isin(future)
                     & frame.available.ge(origin - pd.Timedelta(hours=24))]
    # Prefer latest complete upload, rather than mixing six different forecast runs/providers.
    groups = sorted(eligible.groupby(['issued', 'source']), key=lambda x: x[0][0], reverse=True)
    for (issue, source), rows in groups:
        if len(rows) != HOURS or not rows.valid.sort_values().tolist() == future.tolist():
            continue
        if not np.isfinite(rows[['forecast_vpd_kpa', 'rain_mm', 'temperature_c']]).all().all():
            continue
        return dict(forecast_vpd_mean_kpa=float(rows.forecast_vpd_kpa.mean()),
                    forecast_rain_max_mm=float(rows.rain_mm.max()),
                    forecast_temp_max_c=float(rows.temperature_c.max()),
                    forecast_upload_utc=issue.isoformat(), forecast_available_utc=rows.available.max().isoformat(),
                    forecast_source=str(source), forecast_upload_age_h=(origin - rows.available.max()).total_seconds() / 3600)
    return None


def make_panel(hourly, forecasts):
    frame = hourly.copy()
    frame['target_soil'] = frame.soil.shift(-HOURS)
    frame['target_time'] = frame.index + pd.Timedelta(hours=HOURS)
    # Reject horizons with missing soil readings; gaps are not dry spells.
    path = pd.concat([frame.soil.shift(-i) for i in range(HOURS + 1)], axis=1)
    frame.loc[~path.notna().all(axis=1), 'target_soil'] = np.nan
    rows = []
    for origin in frame.index:
        forecast = forecast_at(forecasts, origin)
        rows.append(forecast or {})
    values = pd.DataFrame(rows, index=frame.index).reindex(columns=EXTRA[1:] + [
        'forecast_upload_utc', 'forecast_available_utc', 'forecast_source', 'forecast_upload_age_h'])
    return pd.concat([frame, values], axis=1)


def train_before(frame, cutoff):
    # A six-hour label is only known after target_time, not after its input timestamp.
    return frame[(frame.index < cutoff) & frame.target_time.lt(cutoff)]


def estimate(model, frame, columns):
    x = frame[columns].to_numpy(float)
    delta = ((x - np.asarray(model['mean'])) / np.asarray(model['scale'])) @ np.asarray(model['coef']) + model['intercept']
    return np.clip(frame.soil.to_numpy(float) + delta, 0, 100)


def metrics(actual, predicted):
    error = np.asarray(predicted) - np.asarray(actual)
    return dict(n=len(error), mae_pp=float(np.abs(error).mean()), rmse_pp=float(np.sqrt(np.mean(error ** 2))),
                bias_pp=float(error.mean()))


def write_summary(report, output_dir):
    live = report['live']
    predicted = live['predicted_hour_mean_soil_percent']
    value = f'{predicted:.2f}%' if predicted is not None else 'ไม่พร้อมคำนวณ (ข้อมูลขาดหรือเซนเซอร์เก่า)'
    lines = ['# ผลทดลองข้อมูลสวนจริง', '',
             f"ข้อมูลเซนเซอร์ล่าสุด: {report['snapshot_last_sensor_th']} · {report['reading_rows']:,} แถว",
             f"ค่าจุดเซนเซอร์ล่าสุด: {report['latest_soil_sensor_percent']:.1f}% (ยังไม่สอบเทียบ)", '',
             '## ผลคำนวณล่วงหน้า 6 ชั่วโมง', '',
             f"ค่าเฉลี่ยรายชั่วโมงที่สิ้นสุด {live['target_th']}: **{value}**",
             f"รุ่นที่เลือกจาก validation: `{report['selected_by_validation']['group']}`",
             'ถ้าเป็น persistence หมายถึงคงค่าเฉลี่ยชั่วโมงปัจจุบัน ไม่ใช่หลักฐานว่าความชื้นจะไม่เปลี่ยน', '',
             '## เปรียบเทียบช่วงทดสอบที่กันไว้', '',
             '| รุ่น | MAE (จุดเปอร์เซ็นต์) | RMSE | Bias |', '| --- | ---: | ---: | ---: |']
    lines += [f"| {r['group']} | {r['mae_pp']:.3f} | {r['rmse_pp']:.3f} | {r['bias_pp']:.3f} |"
              for r in report['test_results']]
    split = report['validation']
    lines += ['', f"Train / validation / test: {split['train_rows']} / {split['validation_rows']} / {split['test_rows']} จุดเริ่มพยากรณ์",
              f"ช่วง test: {split['test_start_utc']} ถึง {split['test_origin_max_utc']} (UTC)",
              'เลือก family และ alpha จาก validation เท่านั้น; คะแนน test เป็นการตรวจภายหลัง ไม่ใช้เลือกผู้ชนะ',
              'จุดทดสอบอยู่ในช่วงสั้นและหน้าต่าง 6 ชั่วโมงซ้อนกัน ไม่ใช่ตัวอย่างอิสระหรือผลยืนยันทั้งฤดู', '',
              '## คุณภาพและขอบเขต', '',
              f"จับคู่ข้อมูลอากาศและพยากรณ์ได้ {report['matched_training_origins']} จุดเริ่มพยากรณ์",
              f"ตัดค่าอากาศที่เข้าเกณฑ์ค้างแบบออนไลน์ {report['online_weather_stale_rows']:,} แถว; เก็บค่าดินไว้",
              'ใช้เฉพาะอากาศภายนอก และพยากรณ์ที่ถูกบันทึกก่อนเวลาคำนวณ ไม่ใช้ค่าอากาศจริงในอนาคต',
              'พยากรณ์ฝนใช้ค่าสูงสุดของช่วงที่รายงาน ไม่บวกค่าฝนสะสมซ้ำและไม่แปลงเป็นปริมาณให้น้ำ',
              'เวลา upload ไม่ใช่เวลาออกแบบจำลองของผู้ให้บริการ; ประวัติพยากรณ์ที่เหลือในชีตอาจมี retention bias',
              'เฟิร์มแวร์เดิมอาจแทนค่าที่ API ไม่ส่งมาด้วยศูนย์ จึงยังแยกศูนย์จริงกับข้อมูลขาดต้นทางไม่ได้ครบ',
              'ยังไม่ใช่โมเดลผลผลิต สุขภาพต้น หรือคำสั่งให้น้ำ; ไม่มีการเขียนชีต สั่งปั๊ม หรือแก้โมเดลจังหวัด', '',
              'ไฟล์ประกอบ: [รายงานเต็ม](live_report.json) · [ผลทดสอบทีละจุด](soil_6h_test_predictions.csv) · [โมเดล](soil_6h_model.json)', '']
    (output_dir / 'LIVE_REPORT_TH.md').write_text('\n'.join(lines), encoding='utf-8')


def run(input_dir, output_dir):
    asof = pd.Timestamp(datetime.now(timezone.utc))
    raw = pd.read_csv(input_dir / 'readings_15min.csv')
    readings, hourly = prepare_readings(raw)
    if readings.time.max() > asof + pd.Timedelta(minutes=5):
        raise ValueError('Sensor timestamp is ahead of execution clock')
    forecast_raw = pd.read_csv(input_dir / 'forecast_hourly.csv')
    forecasts = prepare_forecasts(forecast_raw)
    panel = make_panel(hourly, forecasts)
    paired = panel.dropna(subset=BASE + EXTRA + ['target_soil'])
    if len(paired) < 100:
        raise ValueError('Fewer than 100 complete matched origins; do not claim validation')
    validation_start = paired.index[int(.60 * len(paired))]
    test_start = paired.index[int(.80 * len(paired))]
    train = train_before(paired, validation_start)
    validation = paired[(paired.index >= validation_start) & paired.target_time.lt(test_start)]
    test = paired[paired.index >= test_start]
    if min(len(train), len(validation), len(test)) < 20:
        raise ValueError('Insufficient purged chronological split')
    configs = [dict(group='persistence', columns=[], alpha=None)] + [
        dict(group=g, columns=c, alpha=a) for g, c in [('soil_history', BASE), ('soil_weather_forecast', BASE + EXTRA)]
        for a in (1., 10., 100.)]
    models, tuning = [], []
    for config in configs:
        model = fit_ridge(train[config['columns']].to_numpy(float), (train.target_soil - train.soil).to_numpy(float), config['alpha']) if config['columns'] else None
        prediction = estimate(model, validation, config['columns']) if model else validation.soil.to_numpy(float)
        models.append(model)
        tuning.append(dict(**config, **metrics(validation.target_soil, prediction)))
    winner = min(range(len(configs)), key=lambda i: tuning[i]['mae_pp'])
    results, predictions = [], []
    for group in ('persistence', 'soil_history', 'soil_weather_forecast'):
        eligible = [i for i, c in enumerate(configs) if c['group'] == group]
        index = min(eligible, key=lambda i: tuning[i]['mae_pp'])
        config, model = configs[index], models[index]
        values = estimate(model, test, config['columns']) if model else test.soil.to_numpy(float)
        results.append(dict(group=group, alpha=config['alpha'], **metrics(test.target_soil, values)))
        predictions.append(pd.DataFrame(dict(origin_utc=test.index, target_utc=test.target_time, group=group,
                                             actual_soil_percent=test.target_soil, predicted_soil_percent=values)))
    config = configs[winner]
    known = train_before(paired, asof)
    model = fit_ridge(known[config['columns']].to_numpy(float), (known.target_soil - known.soil).to_numpy(float), config['alpha']) if config['columns'] else None
    origin = hourly.index[hourly.index <= readings.time.max()].max()
    live = panel.loc[[origin]]
    sensor_age = (asof - readings.time.max()).total_seconds() / 60
    complete = live[config['columns'] or ['soil']].notna().all().all()
    status = 'available' if complete and sensor_age <= 60 else 'unavailable_missing_features_or_stale_sensor'
    projection = float(estimate(model, live, config['columns'])[0] if model else live.soil.iloc[0]) if status == 'available' else None
    latest = readings.iloc[-1]
    future = forecast_at(forecasts, origin)
    report = dict(generated_utc=asof.isoformat(), source_mode='Authenticated Google Sheets export; immutable local snapshot',
                  snapshot_last_sensor_th=readings.time.max().tz_convert('Asia/Bangkok').isoformat(),
                  sensor_age_minutes=float(sensor_age), latest_soil_sensor_percent=float(latest.soil_moisture_percent),
                  latest_outdoor_vpd_kpa=float(latest.vpd_kpa) if np.isfinite(latest.vpd_kpa) else None,
                  device_count=1, reading_rows=len(readings), online_weather_stale_rows=int(readings.weather_stale_online.sum()),
                  matched_training_origins=len(paired), horizon_hours=HOURS,
                  target='Mean sensor moisture in the hour ending at origin+6h; percentage points, not root-zone average',
                  validation=dict(train_rows=len(train), validation_rows=len(validation), test_rows=len(test),
                                  validation_start_utc=validation_start.isoformat(), test_start_utc=test_start.isoformat(),
                                  test_origin_max_utc=test.index.max().isoformat(),
                                  train_target_max_utc=train.target_time.max().isoformat(),
                                  validation_target_max_utc=validation.target_time.max().isoformat(),
                                  note='60/20/20 chronological origins, purged overlapping labels; alpha/family chosen by validation only'),
                  test_results=results, validation_tuning=tuning, selected_by_validation=config,
                  live=dict(status=status, origin_th=origin.tz_convert('Asia/Bangkok').isoformat(),
                            target_th=(origin + pd.Timedelta(hours=HOURS)).tz_convert('Asia/Bangkok').isoformat(),
                            current_hour_mean_soil_percent=float(live.soil.iloc[0]) if np.isfinite(live.soil.iloc[0]) else None,
                            predicted_hour_mean_soil_percent=projection, forecast_context=future),
                  input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [input_dir / 'readings_15min.csv', input_dir / 'forecast_hourly.csv']},
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  limits=['Soil moisture is an uncalibrated sensor reading at one point/depth; not plant health or yield.',
                          'No irrigation/flowering/fruit-drop/harvest labels: no invented yield prediction.',
                          'Forecast available time is max(upload,received), not provider issue time; retained uploads only.',
                          'Firmware uses zero defaults for absent provider fields; upstream missing cannot be fully distinguished from real zeros.',
                          'Future rain feature is max reported period, not sum or a calibrated irrigation water balance.',
                          'Historical forecast retention/overwrites can cause selection bias; save new exports immutably.',
                          'Single recent chronological test, overlapping six-hour targets; no formal uncertainty/causality claims.',
                          'No outdoor lux-to-PAR conversion, fixed root depth, soil water capacity or ETc prescription.',
                          'No live Sheets writes, pump control, firmware deployment, provincial model change or public raw-data export.'])
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(predictions).to_csv(output_dir / 'soil_6h_test_predictions.csv', index=False, encoding='utf-8-sig')
    panel.to_csv(output_dir / 'soil_6h_panel.csv', index_label='origin_utc', encoding='utf-8-sig')
    (output_dir / 'live_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    (output_dir / 'soil_6h_model.json').write_text(json.dumps(dict(config=config, parameters=model,
                                                              trained_through=known.target_time.max().isoformat()),
                                                          ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    write_summary(report, output_dir)
    print(json.dumps({k: report[k] for k in ('snapshot_last_sensor_th', 'latest_soil_sensor_percent',
                                           'matched_training_origins', 'test_results', 'selected_by_validation', 'live')},
                     ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/processed/orchard_live')
    args = parser.parse_args()
    run(args.input_dir, args.output_dir)
