"""Private, owner-scoped seasonal harvest records in the existing Supabase backend."""
import hashlib
import os
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import requests
from supabase_orchard import read_table

TABLE = 'orchard_harvest_seasons'
FIELDS = ('id,owner_id,orchard_code,season_key,harvest_year,cultivar,province_code,'
          'bearing_area_rai,harvested_kg,harvest_start,harvest_end,source_type,source_reference,'
          'status,actual_harvest_confirmed,yield_kg_per_rai,version,created_at,updated_at')
INPUTS = set('orchard_code season_key harvest_year cultivar province_code bearing_area_rai harvested_kg '
             'harvest_start harvest_end source_type source_reference status actual_harvest_confirmed'.split())
PROVINCES = {str(code) for first,last in [(10,19),(20,27),(30,39),(40,49),(50,58),(60,67),(70,77),(80,86),(90,96)]
             for code in range(first,last+1)}


class HarvestConflict(Exception):
    pass


def owner_key(username):
    return hashlib.sha256(('orchard-owner-v1:' + username).encode()).hexdigest()


def validate(payload, today=None):
    today = today or datetime.now(ZoneInfo('Asia/Bangkok')).date()
    if not isinstance(payload, dict) or set(payload) - INPUTS:
        raise ValueError('ข้อมูลมีช่องที่ไม่อนุญาต ห้ามกำหนดเจ้าของหรือค่าผลผลิตต่อไร่เอง')
    result = {}
    for field, limit in [('orchard_code', 64), ('season_key', 64), ('cultivar', 120), ('source_reference', 1000)]:
        value = payload.get(field, '')
        if not isinstance(value, str) or len(value.strip()) > limit or any(ord(c) < 32 for c in value):
            raise ValueError('ข้อความไม่ถูกต้องหรือยาวเกินกำหนด')
        result[field] = value.strip()
    if not result['orchard_code'] or not result['season_key']:
        raise ValueError('ระบุรหัสสวนของคุณและชื่อฤดูให้คงที่ ไม่ใช้รหัส GAP ยืนยันสิทธิ์')
    year = payload.get('harvest_year')
    if isinstance(year, bool) or not isinstance(year, int) or not 1981 <= year <= today.year:
        raise ValueError('ปีเก็บเกี่ยวต้องเป็น ค.ศ. ที่เกิดขึ้นแล้ว')
    result['harvest_year'] = year
    province = payload.get('province_code') or None
    if province is not None and (not isinstance(province, str) or province not in PROVINCES):
        raise ValueError('ต้องใช้รหัสจังหวัดจริงสองหลัก หรือเว้นว่าง')
    result['province_code'] = province
    for field in ['bearing_area_rai', 'harvested_kg']:
        raw = payload.get(field)
        if raw is None or raw == '':
            result[field] = None
            continue
        if isinstance(raw, bool):
            raise ValueError('พื้นที่และน้ำหนักต้องเป็นตัวเลข')
        try:
            value = Decimal(str(raw))
        except InvalidOperation as exc:
            raise ValueError('พื้นที่และน้ำหนักต้องเป็นตัวเลข') from exc
        if not value.is_finite() or value < 0 or (field == 'bearing_area_rai' and value == 0) or value > Decimal('1000000000000'):
            raise ValueError('พื้นที่ให้ผลต้องมากกว่า 0 และน้ำหนักต้องไม่ติดลบ; ไม่ทราบให้เว้นว่าง')
        if max(0, -value.as_tuple().exponent) > 6:
            raise ValueError('ระบุตัวเลขทศนิยมไม่เกิน 6 ตำแหน่ง')
        result[field] = float(value)
    for field in ['harvest_start', 'harvest_end']:
        raw = payload.get(field)
        if not raw:
            result[field] = None
            continue
        try:
            stamp = date.fromisoformat(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError('วันที่เก็บเกี่ยวต้องเป็น YYYY-MM-DD') from exc
        if stamp.year != year or stamp > today:
            raise ValueError('วันที่ต้องอยู่ในปีเก็บเกี่ยวที่ระบุและไม่ใช่อนาคต')
        result[field] = stamp.isoformat()
    if result['harvest_start'] and result['harvest_end'] and result['harvest_start'] > result['harvest_end']:
        raise ValueError('วันเริ่มเก็บเกี่ยวต้องไม่อยู่หลังวันสิ้นสุด')
    result['status'] = payload.get('status', 'draft')
    result['source_type'] = payload.get('source_type', 'farm_log')
    if result['status'] not in ('draft', 'complete') or result['source_type'] not in ('farm_log', 'weighbridge', 'sales_receipts', 'self_report'):
        raise ValueError('สถานะหรือแหล่งข้อมูลไม่ถูกต้อง')
    confirmed = payload.get('actual_harvest_confirmed', False)
    if not isinstance(confirmed, bool):
        raise ValueError('ต้องยืนยันประเภทน้ำหนักด้วยช่องยืนยัน')
    result['actual_harvest_confirmed'] = confirmed
    if result['status'] == 'complete' and (not confirmed or any(result[k] is None or result[k] == '' for k in
            ['cultivar', 'bearing_area_rai', 'harvested_kg', 'harvest_start', 'harvest_end', 'source_reference'])):
        raise ValueError('ปิดฤดูได้เมื่อมีพันธุ์ พื้นที่ให้ผล น้ำหนักจริง วันที่ แหล่งอ้างอิง และยืนยันว่าเก็บเกี่ยวครบฤดูแล้ว')
    return result


def public_record(row):
    result = {k: v for k, v in row.items() if k != 'owner_id'}
    complete = row.get('status') == 'complete'
    result['yield_kg_per_rai'] = (float(Decimal(str(row['harvested_kg'])) / Decimal(str(row['bearing_area_rai'])))
                                  if complete else None)
    result['verification_status'] = 'user_reported_not_independently_verified'
    return result


class HarvestStore:
    def _write(self, method, params, payload):
        url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        key = os.environ.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', url) or not key:
            raise RuntimeError('ยังไม่ตั้ง Supabase ฝั่งเซิร์ฟเวอร์ จึงไม่บันทึกแทนด้วย localStorage')
        headers = {'apikey': key, 'Accept': 'application/json', 'Prefer': 'return=representation'}
        if not key.startswith('sb_secret_'):
            headers['Authorization'] = 'Bearer ' + key
        try:
            response = requests.request(method, url + '/rest/v1/' + TABLE, params=params, json=payload,
                                        headers=headers, timeout=15, allow_redirects=False)
        except requests.RequestException as exc:
            raise RuntimeError('ยังยืนยันการบันทึกไม่ได้ โหลดประวัติใหม่ก่อนลองอีกครั้ง') from exc
        if response.status_code == 409:
            raise HarvestConflict('มีสวน–ปี–ฤดูนี้แล้ว ให้แก้ไขรายการเดิม')
        if response.status_code not in (200, 201):
            raise RuntimeError('ฐานข้อมูลประวัติสวนยังไม่พร้อม ตรวจ migration 004 และสิทธิ์ service role')
        rows = response.json()
        if not isinstance(rows, list):
            raise RuntimeError('รูปแบบคำตอบฐานข้อมูลไม่ถูกต้อง')
        return rows

    def list(self, owner):
        result = []
        for offset in range(0, 10000, 1000):
            rows = read_table(TABLE, dict(select=FIELDS, owner_id='eq.' + owner,
                order='harvest_year.desc,orchard_code.asc,season_key.asc,id.asc', limit='1000', offset=str(offset)))
            if any(row.get('owner_id') != owner for row in rows):
                raise RuntimeError('ข้อมูลเจ้าของไม่ตรง จึงไม่ส่งข้อมูลประวัติ')
            result.extend(rows)
            if len(rows) < 1000:
                return result
        raise RuntimeError('ประวัติมากเกินขอบเขตการอ่านครั้งเดียว จึงไม่ส่งข้อมูลที่ถูกตัดทอน')

    def create(self, owner, payload):
        rows = self._write('POST', {'select': FIELDS}, dict(validate(payload), owner_id=owner))
        if len(rows) != 1 or rows[0].get('owner_id') != owner:
            raise RuntimeError('ยังยืนยันเจ้าของข้อมูลที่บันทึกไม่ได้')
        return public_record(rows[0])

    def update(self, owner, record_id, payload):
        record_id = str(uuid.UUID(record_id))
        if not isinstance(payload, dict):
            raise ValueError('ต้องส่ง JSON object')
        expected = payload.get('expected_version')
        if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
            raise ValueError('ต้องระบุรุ่นรายการที่กำลังแก้ไข')
        patch = {k: v for k, v in payload.items() if k != 'expected_version'}
        if set(patch) - INPUTS:
            raise ValueError('มีช่องข้อมูลที่ไม่อนุญาตให้แก้')
        filters = dict(select=FIELDS, owner_id='eq.' + owner, id='eq.' + record_id, limit='1')
        rows = read_table(TABLE, filters)
        if not rows:
            raise LookupError('ไม่พบรายการของบัญชีนี้')
        old = rows[0]
        if old.get('owner_id') != owner:
            raise RuntimeError('เจ้าของไม่ตรง')
        if old['version'] != expected:
            raise HarvestConflict('รายการมีการแก้ไขแล้ว โหลดประวัติใหม่ก่อนบันทึก')
        values = validate({**{k: old.get(k) for k in INPUTS}, **patch})
        filters.pop('limit'); filters['version'] = 'eq.' + str(expected)
        rows = self._write('PATCH', filters, values)
        if not rows:
            raise HarvestConflict('รายการเปลี่ยนระหว่างบันทึก กรุณาโหลดใหม่')
        if len(rows) != 1 or rows[0].get('owner_id') != owner:
            raise RuntimeError('คำตอบไม่ตรงกับเจ้าของรายการ')
        return public_record(rows[0])


def baselines(rows):
    latest = {}
    for row in rows:
        if row.get('status') != 'complete':
            continue
        key = (row['orchard_code'], row['season_key'])
        if key not in latest or row['harvest_year'] > latest[key]['harvest_year']:
            latest[key] = row
    return [dict(orchard_code=r['orchard_code'], season_key=r['season_key'],
        source_harvest_year=r['harvest_year'], target_year=r['harvest_year'] + 1,
        kg_per_rai=public_record(r)['yield_kg_per_rai'], source_record_id=r['id'], source_version=r['version'],
        method='previous_season_persistence_baseline', is_ai_forecast=False,
        warning='ค่าฐานจากผลที่ผู้ใช้บันทึก ไม่ใช่คำรับรองผลผลิตปีถัดไป และไม่ใช่ AI Forecast')
        for r in latest.values()]


def training_candidates(rows):
    complete = {(r['orchard_code'], r['season_key'], r['harvest_year']): r for r in rows if r.get('status') == 'complete'}
    pairs = []
    for (orchard, season, year), current in complete.items():
        previous = complete.get((orchard, season, year - 1))
        if not previous:
            continue
        # Compare ratios by cross multiplication; exact ties do not become a class.
        difference = Decimal(str(current['harvested_kg'])) * Decimal(str(previous['bearing_area_rai'])) - Decimal(str(previous['harvested_kg'])) * Decimal(str(current['bearing_area_rai']))
        pairs.append(dict(orchard_code=orchard, season_key=season, harvest_year=year,
            previous_record_id=previous['id'], current_record_id=current['id'],
            previous_version=previous['version'], current_version=current['version'],
            previous_yield_kg_per_rai=public_record(previous)['yield_kg_per_rai'],
            current_yield_kg_per_rai=public_record(current)['yield_kg_per_rai'],
            increase_label=None if difference == 0 else int(difference > 0),
            cultivar_changed=previous['cultivar'] != current['cultivar'],
            previous_data_first_recorded_at=previous['created_at'], previous_data_updated_at=previous['updated_at'],
            target_data_first_recorded_at=current['created_at'], target_data_updated_at=current['updated_at'],
            training_ready_verified=False, warning='ข้อมูลผู้ใช้ ยังไม่ตรวจหลักฐาน/วันทราบข้อมูล; ต้องแบ่งตามปีและสวน ไม่ Auto-train'))
    return pairs
