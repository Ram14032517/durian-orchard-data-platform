"""Download QA-filtered MODIS NDVI context patches, not durian-orchard averages."""
import csv
import hashlib
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from http.client import RemoteDisconnected
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research_data/five_province_history'
API = 'https://modis.ornl.gov/rst/api/v1/MOD13Q1'
START, END = '2003-01-01', '2025-12-31'
PREFIX = '250m_16_days_'
MIN_VALID_PCT = 20


def fetch_json(url):
    key = hashlib.sha256(url.encode()).hexdigest()
    path = DATA / 'evidence' / f'modis_{key}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        payload = path.read_bytes()
    else:
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={'Accept': 'application/json'}), timeout=60) as response:
                    payload = response.read()
                json.loads(payload)
                path.write_bytes(payload)
                break
            except (HTTPError, URLError, TimeoutError, RemoteDisconnected) as error:
                if isinstance(error, HTTPError) and error.code not in (429, 500, 502, 503, 504):
                    raise
                if attempt == 2:
                    raise
                time.sleep(2 ** (attempt + 1))
    return json.loads(payload), dict(url=url, snapshot=str(path.relative_to(ROOT)),
                                   sha256=hashlib.sha256(payload).hexdigest())


def good_pixels(ndvi, reliability, quality):
    ndvi, reliability, quality = (np.asarray(v, dtype=float) for v in (ndvi, reliability, quality))
    if not (ndvi.shape == reliability.shape == quality.shape):
        raise ValueError('NDVI and QA arrays must align')
    if not all(np.isfinite(v).all() for v in (ndvi, reliability, quality)):
        raise ValueError('Invalid source pixel values')
    if any((v != np.floor(v)).any() for v in (ndvi, reliability, quality)):
        raise ValueError('Expected unscaled integer NDVI/QA')
    qa = quality.astype(np.int64)
    return ((ndvi >= -2000) & (ndvi <= 10000) & (reliability == 0)
            & (qa >= 0) & (qa <= 65534) & ((qa & 3) == 0)
            & (((qa >> 11) & 7) == 1) & (((qa >> 6) & 3) != 3)
            & ((qa & ((1 << 8) | (1 << 10) | (1 << 14) | (1 << 15))) == 0))


def parse_subset(response, point, manifest, scale):
    if float(response['latitude']) != float(point['weather_latitude']) or float(response['longitude']) != float(point['weather_longitude']):
        raise ValueError('Response location differs from requested reference point')
    size = int(response['nrows']) * int(response['ncols'])
    grouped = defaultdict(dict)
    for record in response['subset']:
        band = record['band']
        if not band.startswith(PREFIX):
            raise ValueError('Unexpected MODIS band')
        bands = grouped[record['calendar_date']]
        if band in bands or len(record['data']) != size:
            raise ValueError('Duplicate or misaligned band')
        bands[band] = record
    rows = []
    for day, bands in sorted(grouped.items()):
        raw = bands[PREFIX + 'NDVI']
        start = date.fromisoformat(day)
        expected = 'A' + start.strftime('%Y%j')
        if raw['modis_date'] != expected or not START <= day <= END:
            raise ValueError('Unexpected composite date')
        if any(r['modis_date'] != expected or r['tile'] != raw['tile'] or r['proc_date'] != raw['proc_date'] for r in bands.values()):
            raise ValueError('Band dates, tiles or processing versions do not align')
        mask = good_pixels(raw['data'], bands[PREFIX + 'pixel_reliability']['data'],
                           bands[PREFIX + 'VI_Quality']['data'])
        accepted = int(mask.sum())
        pct = 100 * accepted / size
        values = np.asarray(raw['data'])[mask] * scale
        usable = pct >= MIN_VALID_PCT
        rows.append(dict(province_code=point['province_code'], province_name=point['province_name'],
                         reference_latitude=point['weather_latitude'], reference_longitude=point['weather_longitude'],
                         composite_start_date=day,
                         composite_end_date=min(start + timedelta(days=15), date(start.year, 12, 31)).isoformat(),
                         modis_date=raw['modis_date'], tile=raw['tile'], processing_date=raw['proc_date'],
                         product='MOD13Q1', collection_version='service_not_reported',
                         nominal_pixel_m=250, actual_grid_cell_m=response['cellsize'],
                         patch_nrows=response['nrows'], patch_ncols=response['ncols'],
                         grid_xllcorner=response['xllcorner'], grid_yllcorner=response['yllcorner'],
                         total_pixels=size, good_pixels=accepted, good_pixel_pct=pct,
                         ndvi_mean=float(values.mean()) if usable else '',
                         ndvi_p10=float(np.quantile(values, 0.1)) if usable else '',
                         quality_status='usable_context_patch' if usable else 'insufficient_good_pixels',
                         area_context='reference_patch_not_bearing_orchard_mask',
                         source_url=manifest['url'], source_sha256=manifest['sha256']))
    return rows


def ndvi_series(rows):
    """Keep composite intervals; never fabricate daily satellite observations."""
    grouped = defaultdict(list)
    for row in rows:
        start = date.fromisoformat(row['composite_start_date']).toordinal()
        end = date.fromisoformat(row['composite_end_date']).toordinal() + 1
        value = float(row['ndvi_mean']) if row['ndvi_mean'] != '' else np.nan
        if not 1 <= end - start <= 16 or np.isinf(value) or (np.isfinite(value) and not -0.2 <= value <= 1):
            raise ValueError('Invalid NDVI interval or scaled value')
        grouped[row['province_code']].append((start, end, value))
    result = {}
    for code, records in grouped.items():
        matrix = np.asarray(sorted(records), dtype=float)
        if (matrix[1:, 0] < matrix[:-1, 1]).any():
            raise ValueError('Duplicate or overlapping NDVI composites')
        result[code] = matrix
    return result


def ndvi_exposure(series, harvest_days, age, start, stop):
    if stop <= start or not harvest_days:
        raise ValueError('NDVI exposure needs a nonempty window')
    starts = np.asarray([d.toordinal() - age + start for d in harvest_days])
    ends = starts + stop - start
    overlap = np.maximum(0, np.minimum(ends[:, None], series[:, 1])
                         - np.maximum(starts[:, None], series[:, 0])).sum(axis=0)
    known = np.isfinite(series[:, 2])
    weight = overlap[known].sum()
    coverage = 100 * weight / (len(harvest_days) * (stop - start))
    # ponytail: composite overlap is a timing proxy, not the measured daily greenness.
    mean = float(np.average(series[known, 2], weights=overlap[known])) if coverage >= 50 else np.nan
    return dict(mean=mean, coverage_pct=float(coverage))


def download_point(point, scale):
    params = dict(latitude=point['weather_latitude'], longitude=point['weather_longitude'])
    available, dates_manifest = fetch_json(API + '/dates?' + urlencode(params))
    dates = [d for d in available['dates'] if START <= d['calendar_date'] <= END]
    if len({d['calendar_date'] for d in dates}) != len(dates) or not dates:
        raise ValueError('Missing or duplicate available dates')
    dates.sort(key=lambda d: d['calendar_date'])
    rows, manifests = [], [dates_manifest]
    for i in range(0, len(dates), 10):
        batch = dates[i:i + 10]
        query = dict(params, startDate=batch[0]['modis_date'], endDate=batch[-1]['modis_date'],
                     kmAboveBelow=1, kmLeftRight=1)
        url = API + '/subset?' + urlencode(query)
        cached = DATA / 'evidence' / f'modis_{hashlib.sha256(url.encode()).hexdigest()}.json'
        if cached.exists():
            response, manifest = fetch_json(url)
            fragments = [manifest]
        else:
            urls = [url + '&' + urlencode({'band': PREFIX + band})
                    for band in ('NDVI', 'pixel_reliability', 'VI_Quality')]
            # Read only the three required bands; the full 12-band service is much slower.
            with ThreadPoolExecutor(max_workers=3) as bands_pool:
                parts = list(bands_pool.map(fetch_json, urls))
            response = dict(parts[0][0], subset=[s for part, _ in parts for s in part['subset']])
            geometry = ('latitude', 'longitude', 'nrows', 'ncols', 'cellsize', 'xllcorner', 'yllcorner')
            if any(any(part[k] != response[k] for k in geometry) for part, _ in parts):
                raise ValueError('Band requests have different spatial grids')
            manifest = parts[0][1]
            fragments = [m for _, m in parts]
        selected = parse_subset(response, point, manifest, scale)
        if {r['modis_date'] for r in selected} != {d['modis_date'] for d in batch}:
            raise ValueError('API returned incomplete requested composites')
        rows.extend(selected)
        manifests.extend(fragments)
        if i % 100 == 0:
            print(f"{point['province_code']}: {len(rows)}/{len(dates)} composites", flush=True)
    return rows, dict(province_code=point['province_code'], requested_dates=len(dates), sources=manifests)


def main():
    bands, band_manifest = fetch_json(API + '/bands')
    band = next(b for b in bands['bands'] if b['band'] == PREFIX + 'NDVI')
    scale = float(band['scale_factor'])
    if scale != 0.0001 or float(band['add_offset']) != 0 or band['fill_value'] != '-3000':
        raise ValueError('Source scaling changed; recheck parser')
    with (DATA / 'reference_points.csv').open(encoding='utf-8-sig', newline='') as stream:
        points = list(csv.DictReader(stream))
    if len(points) != 5 or len({p['province_code'] for p in points}) != 5:
        raise ValueError('Expected five distinct reference points')
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda p: download_point(p, scale), points))
    rows = sorted([r for data, _ in results for r in data],
                  key=lambda r: (r['province_code'], r['composite_start_date']))
    path = DATA / 'ndvi_reference_composites.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    review = dict(retrieved_at_utc=datetime.now(timezone.utc).isoformat(), api=API,
                  requested_dates=[START, END], bands=band_manifest, ndvi_band_metadata=band,
                  source_queries=[m for _, m in results], rows=len(rows),
                  usable_composites=sum(r['ndvi_mean'] != '' for r in rows),
                  csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  method=dict(patch='1 km above/below and left/right; actual returned grid recorded per row',
                              qa='reliability=0; MODLAND=0; land=1; exclude high aerosol, adjacent/mixed cloud, snow, shadow',
                              min_good_pixel_pct=MIN_VALID_PCT, scale=scale, fill=-3000),
                  documentation=['https://modis.ornl.gov/data/modis_webservice.html',
                                 'https://modis-land.gsfc.nasa.gov/pdf/MOD13_User_Guide_V61.pdf'],
                  limits=['The API does not report a collection version; do not assume C6.1 from the product name alone.',
                          'A context patch contains mixed land cover; it is not a measured durian orchard or province mean.',
                          '16-day compositing is not a daily average or a daily observation; cloudy gaps are not zero.',
                          'Accepted pixels vary across composites; a clear-sky spatial mean is not an unchanged orchard sample.',
                          'NDVI measures spectral greenness, not carbohydrate production, root health or fruit readiness.',
                          'No orchard bearing-area weights are available here; no new-tree exclusions are claimed.',
                          'Cached raw API snapshots are reused; remove only the matching cache intentionally to refresh.'])
    (DATA / 'ndvi_source_review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Saved {len(rows)} composites; {review['usable_composites']} usable", flush=True)


if __name__ == '__main__':
    main()
