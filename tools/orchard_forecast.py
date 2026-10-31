"""Owner-only Open-Meteo forecast; no coordinates in responses, static files or disk cache."""
import copy
import hashlib
import json
import math
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TZ = ZoneInfo('Asia/Bangkok')
ROOT = Path(__file__).resolve().parents[1]
LOCATION_FILE = ROOT / '.secrets/orchard_forecast_location.json'
ENDPOINT = 'https://api.open-meteo.com/v1/forecast'
HOURLY = {'temperature_2m': ('temperature_c', '°C', -90, 65),
          'relative_humidity_2m': ('humidity_percent', '%', 0, 100),
          'precipitation': ('rain_mm', 'mm', 0, 2000),
          'precipitation_probability': ('rain_probability_percent', '%', 0, 100),
          'wind_speed_10m': ('wind_kmh', 'km/h', 0, 500),
          'vapour_pressure_deficit': ('vpd_kpa', 'kPa', 0, 30)}
DAILY = {'temperature_2m_max': ('temperature_max_c', '°C', -90, 65),
         'temperature_2m_min': ('temperature_min_c', '°C', -90, 65),
         'precipitation_sum': ('rain_mm', 'mm', 0, 10000),
         'precipitation_probability_max': ('rain_probability_percent', '%', 0, 100),
         'wind_speed_10m_max': ('wind_max_kmh', 'km/h', 0, 500)}
CURRENT = {k:v for k,v in HOURLY.items() if k != 'precipitation_probability'}


def current_conditions(payload, now):
    """Provider model current conditions, never sensor measurements or an hourly forecast proxy."""
    block, units = payload.get('current', {}), payload.get('current_units', {})
    result = {'time': None, 'interval_seconds': None, 'quality_flags': [],
              **{v[0]: None for v in CURRENT.values()}}
    try:
        stamp = datetime.strptime(block['time'], '%Y-%m-%dT%H:%M').replace(tzinfo=TZ)
        interval = block['interval']
        if not isinstance(interval, int) or isinstance(interval, bool) or not 1 <= interval <= 3600:
            raise ValueError()
        if stamp > now + timedelta(minutes=5) or units.get('interval') != 'seconds':
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        result['quality_flags'].append('current_time_or_interval_unavailable')
        return result
    result.update(time=stamp.isoformat(), interval_seconds=interval)
    for provider, (key, unit, lo, hi) in CURRENT.items():
        value = block.get(provider)
        if units.get(provider) == unit and not isinstance(value, bool) and isinstance(value, (int,float)) and math.isfinite(value) and lo <= value <= hi:
            result[key] = float(value)
        else:
            result['quality_flags'].append(key)
    return result


def location_config():
    """Single sensor orchard only: supplied and confirmed directly by its owner, never GAP inferred."""
    try:
        raw = os.environ.get('ORCHARD_FORECAST_LOCATION_JSON')
        if not raw and (not LOCATION_FILE.is_file() or LOCATION_FILE.is_symlink()):
            raise ValueError()
        value = json.loads(raw or LOCATION_FILE.read_text(encoding='utf-8'))
        lat, lon = value['latitude'], value['longitude']
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in (lat, lon)):
            raise ValueError()
        if not (5 <= lat <= 21 and 97 <= lon <= 106):
            raise ValueError()
        if value.get('crs') != 'EPSG:4326' or value.get('owner_confirmed') is not True or value.get('use') != 'non_commercial_education':
            raise ValueError()
        stamp = datetime.fromisoformat(value['confirmed_at'])
        if stamp.tzinfo is None or stamp > datetime.now(TZ) + timedelta(minutes=5):
            raise ValueError()
        if not value.get('owner_account') or not value.get('sensor_device_id') or not value.get('orchard_key'):
            raise ValueError()
        return value
    except (OSError, ValueError, KeyError, TypeError):
        raise RuntimeError('ยังไม่มีพิกัดสวนที่เจ้าของยืนยันและอนุญาตใช้เพื่อการศึกษา จึงไม่แทนด้วยพิกัดจังหวัด') from None


def normalize(payload, retrieved_at):
    """Strict unit/time contract; missing and invalid values stay null, never zero."""
    if not isinstance(payload, dict) or payload.get('timezone') != 'Asia/Bangkok' or payload.get('utc_offset_seconds') != 25200:
        raise RuntimeError('พยากรณ์ตอบเขตเวลาหรือรูปแบบไม่ตรงกับที่กำหนด')
    result = {'retrieved_at': retrieved_at.isoformat(), 'model_issued_at': None, 'hourly': [], 'daily': [], 'quality_flags': [],
              'current': current_conditions(payload, retrieved_at)}
    for group, fields, count in [('hourly', HOURLY, 168), ('daily', DAILY, 7)]:
        block = payload.get(group, {})
        times = block.get('time', [])
        if not isinstance(times, list) or len(times) != count or len(set(times)) != count:
            raise RuntimeError('จำนวนเวลาพยากรณ์ไม่ครบ 7 วันหรือมีเวลาซ้ำ')
        stamps = []
        for stamp in times:
            try:
                parsed = datetime.strptime(stamp, '%Y-%m-%dT%H:%M' if group == 'hourly' else '%Y-%m-%d').replace(tzinfo=TZ)
            except (ValueError, TypeError):
                raise RuntimeError('รูปแบบเวลาพยากรณ์ไม่ถูกต้อง') from None
            stamps.append(parsed)
        step = timedelta(hours=1) if group == 'hourly' else timedelta(days=1)
        if any(b-a != step for a, b in zip(stamps, stamps[1:])):
            raise RuntimeError('ช่วงเวลาพยากรณ์ไม่ต่อเนื่อง')
        if stamps[0].date() != retrieved_at.astimezone(TZ).date():
            raise RuntimeError('พยากรณ์เริ่มไม่ตรงกับวันเรียกข้อมูล จึงไม่แสดงเป็นข้อมูลล่าสุด')
        for i, stamp in enumerate(stamps):
            row = {'time': stamp.isoformat() if group == 'hourly' else stamp.date().isoformat()}
            for provider, (key, unit, lo, hi) in fields.items():
                values = block.get(provider)
                actual_unit = payload.get(group+'_units', {}).get(provider)
                if actual_unit != unit or not isinstance(values, list) or len(values) != count:
                    raise RuntimeError('หน่วยหรือโครงสร้างตัวแปรพยากรณ์ไม่ตรงกับสัญญาที่กำหนด')
                v = values[i]
                row[key] = float(v) if not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and lo <= v <= hi else None
                if row[key] is None and key not in result['quality_flags']:
                    result['quality_flags'].append(key)
            result[group].append(row)
    for row in result['daily']:
        hours = [h for h in result['hourly'] if h['time'].startswith(row['time'])]
        for key in ['humidity_percent', 'vpd_kpa']:
            values = [h[key] for h in hours if h[key] is not None]
            row[key+'_valid_hours'] = len(values)
            row[key] = sum(values)/24 if len(values) == 24 else None
    return result


class ForecastService:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def get(self, location, now=None):
        now = now or datetime.now(TZ)
        key = hashlib.sha256(json.dumps(location, sort_keys=True).encode()).hexdigest()
        with self.lock:
            prior = self.cache.get(key)
            age = (now-datetime.fromisoformat(prior['retrieved_at'])).total_seconds() if prior else None
            same_day = prior and prior['daily'][0]['time'] == now.astimezone(TZ).date().isoformat()
            if prior and same_day and 0 <= age < 900:
                return self.present(prior, now, 'cached')
            # Failures also cool down for five minutes; repeated UI retry never hammers the provider.
            failure = self.cache.get(key+':retry')
            if failure and (now-failure).total_seconds() < 300:
                if prior and 0 <= age <= 10800:
                    return self.present(prior, now, 'stale', 'บริการยังไม่พร้อม ใช้สำเนาเก่าเพื่อดูประกอบ งดคำแนะนำจากพยากรณ์เก่า')
                raise RuntimeError('บริการพยากรณ์ยังไม่พร้อม โปรดลองใหม่ใน 5 นาที')
            params = dict(latitude=location['latitude'], longitude=location['longitude'],
                hourly=','.join(HOURLY), daily=','.join(DAILY), current=','.join(CURRENT), forecast_days=7,
                timezone='Asia/Bangkok', temperature_unit='celsius', wind_speed_unit='kmh', precipitation_unit='mm')
            try:
                response = requests.get(ENDPOINT, params=params, timeout=(5, 20), allow_redirects=False)
                if response.status_code != 200 or 'application/json' not in response.headers.get('Content-Type', '') or len(response.content) > 1_000_000:
                    raise RuntimeError('บริการพยากรณ์ตอบไม่สำเร็จ')
                value = normalize(response.json(), now)
            except (requests.RequestException, ValueError, RuntimeError):
                self.cache[key+':retry'] = now
                if prior and 0 <= age <= 10800:
                    return self.present(prior, now, 'stale', 'เรียกบริการไม่สำเร็จ กำลังแสดงสำเนาเก่า งดคำแนะนำจากพยากรณ์เก่า')
                raise RuntimeError('เรียก Open-Meteo ไม่สำเร็จ ไม่มีข้อมูลทดแทน โปรดลองใหม่ใน 5 นาที') from None
            # One configured orchard. Limit memory without saving any location-bearing data on disk.
            self.cache = {key: value}
            return self.present(value, now, 'fresh')

    @staticmethod
    def present(value, now, status, warning=None):
        result = copy.deepcopy(value)
        result.update(status=status, warning=warning, source='Open-Meteo Forecast API', timezone='Asia/Bangkok',
            attribution_url='https://open-meteo.com/', license_url='https://creativecommons.org/licenses/by/4.0/',
            model='best_match', spatial_precision='global_model_grid_not_orchard_measurement',
            spatial_note='แบบจำลองกริดโลกหลายชุด ความละเอียดต่างกันตามตัวแปรและแบบจำลอง ไม่ใช่เครื่องวัดในสวน; โอกาสฝนมาจาก ensemble grid ประมาณ 27 กม.',
            age_minutes=round((now-datetime.fromisoformat(value['retrieved_at'])).total_seconds()/60, 1))
        current = result['current']
        age_current = (now-datetime.fromisoformat(current['time'])).total_seconds()/60 if current.get('time') else None
        current['age_minutes'] = round(age_current,1) if age_current is not None else None
        current['status'] = ('missing' if age_current is None or age_current < -5 else
                             'stale' if status == 'stale' or age_current > 60 else 'fresh')
        first = now.replace(minute=0, second=0, microsecond=0)+timedelta(hours=1)
        result['hourly'] = [r for r in result['hourly'] if datetime.fromisoformat(r['time']) >= first]
        result['summaries'] = []
        for n in [24, 48, 72]:
            rows = [r for r in result['hourly'] if datetime.fromisoformat(r['time']) < first+timedelta(hours=n)]
            values = [r['rain_mm'] for r in rows if r['rain_mm'] is not None]
            result['summaries'].append(dict(hours=n, valid_rain_hours=len(values), expected_hours=n,
                start=(first-timedelta(hours=1)).isoformat(), end=(first+timedelta(hours=n-1)).isoformat(),
                rain_mm=sum(values) if len(values) == n else None,
                wet_hours=sum(v > 0 for v in values), complete=len(values) == n))
        return result
