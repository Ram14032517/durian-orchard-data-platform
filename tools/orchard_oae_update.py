"""Read-through OAE updates for descriptive statistics ONLY; model snapshots stay sealed."""
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import time
import zipfile
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research_data/five_province_history/production_annual.csv'
CATALOG = 'https://catalog.oae.go.th/api/3/action/package_show?id=durian_product'
ITEMS = {'เนื้อที่ยืนต้น': ('planted_rai', 'ไร่'), 'เนื้อที่ให้ผล': ('bearing_rai', 'ไร่'),
         'ผลผลิต': ('production_tonnes', 'ตัน'),
         'ผลผลิตต่อเนื้อที่ให้ผล': ('yield_kg_per_rai_source', 'กิโลกรัมต่อไร่')}
LOCK = threading.Lock()


def base_rows():
    rows = []
    with BASE.open(encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            rows.append({k: (v if k in ('province_name', 'province_name_en', 'region', 'province_code')
                            else float(v) if v else None) for k, v in r.items()})
    return rows


def validate(source, baseline, current_year):
    """QC screens are review triggers, never agronomic truth or final-actual evidence."""
    required = {'year', 'crop_year', 'province_name', 'commodity', 'subcom', 'item', 'data', 'unit', 'data_date'}
    if not required <= set(source.columns):
        raise ValueError('OAE schema changed')
    names = {r['province_name']: r for r in baseline}
    old = {(r['province_code'], int(r['year_ce'])): r for r in baseline}
    result = dict(old)
    review = []
    eligible = source[source.province_name.isin(names) & source.commodity.eq('ทุเรียน')]
    if eligible.empty:
        raise ValueError('No matching provinces')
    for (name, be), g in eligible.groupby(['province_name', 'year'], dropna=False):
        flags = []
        try:
            year = int(be) - 543
            if float(be) != int(be) or not 1990 <= year <= current_year:
                raise ValueError()
        except (ValueError, TypeError, OverflowError):
            review.append({'province_name': str(name), 'year_be': str(be), 'reasons': ['invalid_or_future_year']})
            continue
        template = names[name]
        code = template['province_code']
        row = {k: template[k] for k in ('province_name', 'province_code', 'province_name_en', 'region')}
        row.update(year_ce=year, source='OAE live catalog', actual_status='final_actual_unverified',
                   source_data_date=' | '.join(sorted(set(g.data_date.dropna().astype(str)))),
                   publication_date=None)
        if len(g) != 4 or g.item.duplicated().any() or set(g.item) != set(ITEMS):
            flags.append('duplicate_or_missing_items')
        if g.crop_year.nunique() != 1 or not all(str(v).replace('.0', '') == str(int(be)) for v in g.crop_year):
            flags.append('crop_year_mismatch')
        if g.subcom.fillna('').astype(str).nunique() > 1:
            flags.append('multiple_subcommodities')
        for item, (field, unit) in ITEMS.items():
            selected = g[g.item.eq(item)]
            row[field] = None
            if len(selected) != 1:
                continue
            if selected.iloc[0].unit != unit:
                flags.append('unit_' + field)
            try:
                value = float(selected.iloc[0].data)
                if not math.isfinite(value) or value < 0:
                    raise ValueError()
                row[field] = value
            except (ValueError, TypeError):
                flags.append('missing_or_negative_' + field)
        bearing, production = row['bearing_rai'], row['production_tonnes']
        row['yield_kg_per_rai_calculated'] = production * 1000 / bearing if bearing and production is not None else None
        calculated, reported = row['yield_kg_per_rai_calculated'], row['yield_kg_per_rai_source']
        if calculated is None:
            flags.append('no_positive_bearing_area')
        if calculated is not None and reported is not None and abs(calculated - reported) > 1:
            flags.append('yield_arithmetic_difference_gt_1')
        if bearing is not None and row['planted_rai'] is not None and bearing > row['planted_rai']:
            flags.append('bearing_exceeds_standing_area')
        prior = old.get((code, year - 1))
        for field in ('production_tonnes', 'planted_rai', 'bearing_rai', 'yield_kg_per_rai_calculated'):
            if prior and prior.get(field) and row.get(field) is not None:
                if abs(row[field] / prior[field] - 1) > .5:
                    flags.append('large_yoy_review_' + field)
        existing = old.get((code, year))
        if existing:
            changed = [f for f, _ in ITEMS.values() if row.get(f) != existing.get(f)]
            if changed:
                flags.append('historical_revision_requires_review')
        if flags:
            review.append({'province_code': code, 'province_name': name, 'year_ce': year,
                           'reasons': sorted(set(flags)), 'candidate': row, 'previous': existing})
        elif not existing:
            result[(code, year)] = row
    rows = sorted(result.values(), key=lambda r: (r['province_code'], r['year_ce']))
    # Changes use consecutive years only; missing years are never bridged.
    by_key = {(r['province_code'], int(r['year_ce'])): r for r in rows}
    for row in rows:
        prev = by_key.get((row['province_code'], int(row['year_ce']) - 1))
        for field, output in [('production_tonnes', 'production_yoy_pct'), ('yield_kg_per_rai_calculated', 'yield_yoy_pct')]:
            row[output] = (100 * (row[field] / prev[field] - 1)
                           if prev and prev.get(field) and row.get(field) is not None else None)
    return rows, review, len(result) - len(old)


def get_bytes(url, limit):
    if urlsplit(url).scheme != 'https' or urlsplit(url).hostname != 'catalog.oae.go.th':
        raise ValueError('Unapproved OAE download host')
    with requests.get(url, stream=True, timeout=(5, 12), allow_redirects=False) as response:
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError('Unexpected OAE redirect')
        data = bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError('OAE response too large')
        return bytes(data)


def cache_dir():
    return (Path(tempfile.gettempdir()) / 'durian_oae_updates' if os.environ.get('VERCEL')
            else ROOT / '.build/oae_updates')


def read_update():
    """Automatic on first page request; persisted 24h cache / 1h failure backoff."""
    folder = cache_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'status.json'
    with LOCK:
        previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
        if previous and time.time() < previous.get('next_check_epoch', 0):
            return previous
        checked = datetime.now(timezone.utc).isoformat()
        try:
            meta_bytes = get_bytes(CATALOG, 2_000_000)
            package = json.loads(meta_bytes)
            resources = [r for r in package['result']['resources'] if 'province' in r.get('url', '').lower()]
            if not package.get('success') or len(resources) != 1:
                raise ValueError('Ambiguous OAE provincial resource')
            raw = get_bytes(resources[0]['url'], 20_000_000)
            # Bound XLSX expansion before pandas/openpyxl parses untrusted data.
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if sum(f.file_size for f in archive.infolist()) > 120_000_000:
                    raise ValueError('Oversized XLSX expansion')
            source = pd.read_excel(io.BytesIO(raw), sheet_name='durian', engine='openpyxl')
            baseline = base_rows()
            rows, review, _ = validate(source, (previous or {}).get('rows') or baseline, datetime.now(timezone.utc).year)
            added = len(rows) - len(baseline)
            digest = hashlib.sha256(raw).hexdigest()
            snapshot = folder / digest
            snapshot.mkdir(exist_ok=True)
            for name, body in [('source.xlsx', raw), ('catalog.json', meta_bytes)]:
                target = snapshot / name
                if not target.exists():
                    target.write_bytes(body)
            value = dict(rows=rows, review=review, added_rows=added, status='checked', checked_at=checked,
                         source_sha256=digest, source_url=resources[0]['url'],
                         resource_last_modified=resources[0].get('last_modified'),
                         final_actual='unverified', next_check_epoch=time.time() + 86400,
                         storage='ephemeral_server_cache' if os.environ.get('VERCEL') else 'local_versioned_cache')
            manifest = snapshot / 'validation.json'
            if not manifest.exists():
                manifest.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        except (requests.RequestException, ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, ImportError) as exc:
            # Error messages are controlled: no credentials or upstream response bodies.
            code = getattr(getattr(exc, 'response', None), 'status_code', None)
            value = dict(previous or {}, rows=(previous or {}).get('rows', base_rows()), status='unavailable',
                         checked_at=checked, message=('OAE HTTP ' + str(code)) if code else 'OAE unavailable or schema/QC changed',
                         storage='ephemeral_server_cache' if os.environ.get('VERCEL') else 'local_versioned_cache',
                         next_check_epoch=time.time() + 3600)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        temp.replace(path)
        return value


if __name__ == '__main__':
    value = read_update()
    print(json.dumps({k: value.get(k) for k in ('status', 'checked_at', 'added_rows', 'message')}, ensure_ascii=False))
