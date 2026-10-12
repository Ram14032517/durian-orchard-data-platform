"""Filter official DDPM village statistics; blanks are unknown, not zero disasters."""
import csv
import calendar
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research_data/five_province_history'
PROVINCES = {'22': 'จันทบุรี', '33': 'ศรีสะเกษ', '53': 'อุตรดิตถ์',
             '84': 'สุราษฎร์ธานี', '86': 'ชุมพร'}
DATASETS = {'dpm-gd015': 'flood', 'dpm-gd013': 'windstorm'}
YEARS = tuple(range(2562, 2568))
PLAN_ID = 'e11a5fcd-2350-41c8-b951-2e64f140c131'
NEWS_ENDPOINT = 'https://dpmreporter.disaster.go.th/portal/services/disaster_news/get_news_list.php'
NEWS_TYPES = '1,2,3,5,8,16,17'
NEWS_RANGE = ('2020-01-01', '2025-12-31')
STAGES = ('before_window', 'pre_bloom_90d', 'fruit_0_29d', 'fruit_30_59d',
          'fruit_60_89d', 'fruit_90_to_harvest', 'on_or_after_harvest')
THAI_MONTHS = {'ม.ค.': 1, 'ก.พ.': 2, 'มี.ค.': 3, 'เม.ย.': 4, 'พ.ค.': 5, 'มิ.ย.': 6,
               'ก.ค.': 7, 'ส.ค.': 8, 'ก.ย.': 9, 'ต.ค.': 10, 'พ.ย.': 11, 'ธ.ค.': 12,
               **dict(zip(('มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
                           'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'), range(1, 13)))}


def drought_date(value):
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    text = str(value or '').strip()
    if text in ('', '-', 'None'):
        return ''
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}.*', text):
        return date.fromisoformat(text[:10]).isoformat()
    parts = re.split(r'[-/\s]+', text)
    if len(parts) != 3:
        raise ValueError(f'Unsupported drought date: {text}')
    day, month, year = parts
    year = int(year)
    year = (2500 + year if year < 100 else year)
    year = year - 543 if year > 2400 else year
    month = THAI_MONTHS[month] if month in THAI_MONTHS else int(month)
    return date(year, month, int(day)).isoformat()


def drought_records(table, year_be, resource):
    headers = [str(v or '').strip().lower() for v in table[0]]
    if 'province' not in headers:
        raise ValueError('Missing drought province header')
    names = {name: code for code, name in PROVINCES.items()}
    output = []
    aggregate = 'time' in headers
    for line, values in enumerate(table[1:], 2):
        row = dict(zip(headers, values))
        name = str(row.get('province') or '').strip()
        if name not in names:
            continue
        raw_start = row.get('incident date', row.get('disaster date', ''))
        start = drought_date(raw_start)
        raw_end = row.get('situation ended', '') if year_be in (2562, 2563) else ''
        end = drought_date(raw_end)
        raw_close = row.get('disaster ended', row.get('end disaster date',
                           row.get('situation ended', '') if year_be == 2567 else ''))
        closure = drought_date(raw_close)
        # ponytail: Thai source header says rai despite English "Acres"; no crop attribution.
        damage = row.get('agriculture damage', row.get('agriculture (acres)', ''))
        damage = str(damage if damage is not None else '').strip()
        if damage and (not float(damage) >= 0 or not float(damage) < float('inf')):
            raise ValueError('Invalid reported agriculture area')
        output.append(dict(province_code=names[name], province_name=name, source_year_be=year_be,
                           report_level='province_annual_aggregate' if aggregate else 'local_area_record',
                           district='' if aggregate else str(row.get('district') or '').strip(),
                           subdistrict=str(row.get('subdistrict', row.get('sub-district', '')) or '').strip(),
                           village_raw=str(row.get('moo') or '').strip(),
                           incident_date_raw=str(raw_start or '').strip(), incident_date=start,
                           situation_end_date=end, administrative_closure_date=closure,
                           interval_status='source_end_before_start' if start and end and end < start
                           else 'source_situation_dates_known' if start and end else 'duration_unconfirmed',
                           province_incidents_raw=str(row.get('time') if row.get('time') is not None else '').strip(),
                           agriculture_damage_rai_raw=damage,
                           crop_scope='all_agriculture_not_durian_specific',
                           source_resource_id=resource['id'], source_table_row=line, source_url=resource['url']))
    return output


def fetch_drought():
    metadata, manifest = package('dpm-gd028')
    resources, rows = [], []
    for year in range(2562, 2569):
        candidates = [r for r in metadata['resources'] if r['name'].startswith(str(year))]
        resource = next((r for r in candidates if r['format'].lower() == 'csv'), None)
        resource = resource or next(r for r in candidates if r['url'].endswith('.xlsx'))
        payload, digest, snapshot = fetch(resource['url'], f'drought_{resource["id"]}')
        if resource['format'].lower() == 'csv':
            tables = [('CSV', list(csv.reader(io.StringIO(payload.decode('utf-8-sig')))))]
        else:
            from openpyxl import load_workbook
            book = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
            tables = [(sheet.title, list(sheet.values)) for sheet in book if sheet.title != 'Column_Name']
            book.close()
        selected = []
        for sheet, table in tables:
            records = drought_records(table, year, resource)
            selected.extend([dict(r, source_sheet=sheet) for r in records])
        rows.extend(selected)
        resources.append(dict(source_year_be=year, id=resource['id'], url=resource['url'],
                              sha256=digest, snapshot=snapshot, selected_rows=len(selected),
                              evidence_status='actual_statistics_not_risk_map_absence_not_zero'))
    if not rows:
        raise ValueError('No drought records selected; investigate before overwriting')
    write_csv(DATA / 'drought_area_records.csv', rows)
    return dict(dataset_id='dpm-gd028', title=metadata['title'],
                url='https://catalog.disaster.go.th/dataset/dpm-gd028', metadata=manifest,
                resources=resources, selected_rows=len(rows),
                limits=['Source reporting year may include incidents starting in the preceding calendar year.',
                        '2019-2024 local records and 2025 province aggregates have different units; do not sum them.',
                        'Administrative closure dates are not an observed end of meteorological or orchard drought.',
                        'Agricultural damage is all-crop rai, not durian rai or tonnes; blank is not zero.',
                        'Absent province records do not prove absence of drought; no synthetic zero province-years are created.'])


def fetch(url, label):
    payload = urlopen(url, timeout=60).read()
    digest = hashlib.sha256(payload).hexdigest()
    path = DATA / 'evidence' / f'ddpm_{label}_{digest[:12]}'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)
    return payload, digest, str(path.relative_to(ROOT))


def package(key):
    url = f'https://catalog.disaster.go.th/api/3/action/package_show?id={key}'
    payload, digest, path = fetch(url, f'{key}.json')
    response = json.loads(payload)
    if not response.get('success'):
        raise ValueError(f'DDPM package lookup failed: {key}')
    return response['result'], dict(url=url, sha256=digest, snapshot=path)


def parse_resource(payload, dataset, hazard, resource_id):
    reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
    rows = []
    for line, original in enumerate(reader, 2):
        row = {key.strip(): value.strip() for key, value in original.items()}
        if row['PROVINCE_CODE'] not in PROVINCES:
            continue
        if row['PROVINCE_NAME'] != PROVINCES[row['PROVINCE_CODE']]:
            raise ValueError(f'Province code/name mismatch: {resource_id}:{line}')
        for year in YEARS:
            cell = row[f'Y{year}']
            if cell and (not cell.isdigit() or int(cell) < 0):
                raise ValueError(f'Invalid annual count: {resource_id}:{line}:Y{year}')
        row['MOO_ID_NORMALIZED'] = row['MOO_ID'].replace(',', '')
        if not row['MOO_ID_NORMALIZED'].isdigit():
            raise ValueError(f'Invalid village identifier: {resource_id}:{line}')
        row.update(dataset_id=dataset, hazard_type=hazard,
                   source_resource_id=resource_id, source_csv_line=str(line))
        rows.append(row)
    return rows


def summarize(rows):
    # Repeated village IDs can contradict their district: quarantine, never guess.
    keys = Counter((r['hazard_type'], r['PROVINCE_CODE'], r['MOO_ID_NORMALIZED']) for r in rows)
    for row in rows:
        key = row['hazard_type'], row['PROVINCE_CODE'], row['MOO_ID_NORMALIZED']
        row['quality_status'] = 'ambiguous_village_id' if keys[key] > 1 else 'retained'
    result = []
    for hazard in DATASETS.values():
        for code, name in PROVINCES.items():
            subset = [r for r in rows if r['hazard_type'] == hazard and r['PROVINCE_CODE'] == code]
            retained = [r for r in subset if r['quality_status'] == 'retained']
            for year in YEARS:
                known = [int(r[f'Y{year}']) for r in retained if r[f'Y{year}'] != '']
                result.append(dict(
                    province_code=code, province_name=name, hazard_type=hazard,
                    year_ce=year-543, year_be=year, source_rows=len(subset),
                    quarantined_rows=len(subset)-len(retained), nonblank_village_rows=len(known),
                    blank_village_rows=len(retained)-len(known),
                    positive_village_rows=sum(n > 0 for n in known),
                    explicit_zero_village_rows=sum(n == 0 for n in known),
                    reported_village_event_sum=sum(known) if known else '',
                    coverage_status='annual_completeness_unverified',
                ))
    return result


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def news_records(response, code):
    if response.get('status') != 'success':
        raise ValueError(f'DDPM news request failed for province {code}')
    result = []
    for item in response['data']['data']['data']:
        if item['news_province'] != PROVINCES[code] or item['province_name'] != PROVINCES[code]:
            raise ValueError('DDPM news filter returned a different province')
        stamp = datetime.fromisoformat(item['news_date'])
        if not NEWS_RANGE[0] <= stamp.date().isoformat() <= NEWS_RANGE[1]:
            raise ValueError('DDPM news filter returned a date outside requested range')
        result.append(dict(
            news_id=item['news_id'], province_code=code, province_name=PROVINCES[code],
            source_hazard_type=item['news_type_name'], title=item['news_title'],
            ddpm_news_datetime=item['news_date'],
            url=f'https://dpmreporter.disaster.go.th/portal/disaster-news/{item["news_id"]}',
            review_status='event_date_and_crop_exposure_pending',
            reviewed_event_date='', reviewed_districts='', crop_damage_status='',
        ))
    return result


def fetch_news():
    records, queries = [], []
    for code in PROVINCES:
        province_rows, pages, number = [], 1, 1
        while number <= pages:
            params = dict(type=NEWS_TYPES, type_date=1, date_start=NEWS_RANGE[0],
                          date_end=NEWS_RANGE[1], province=code, page_size=50, page_number=number)
            url = NEWS_ENDPOINT + '?' + urlencode(params)
            payload, digest, path = fetch(url, f'news_{code}_{number}.json')
            response = json.loads(payload)
            parsed = news_records(response, code)
            pages = int(response['data']['page_count'])
            if pages > 100:
                raise ValueError('Unexpected DDPM news pagination size')
            province_rows.extend(parsed)
            queries.append(dict(province_code=code, url=url, sha256=digest, snapshot=path,
                                found_rows=int(response['data']['found_row']),
                                page_number=number, page_count=pages))
            number += 1
        if len(province_rows) != queries[-1]['found_rows']:
            raise ValueError(f'Incomplete news pagination: {code}')
        if len({r['news_id'] for r in province_rows}) != len(province_rows):
            raise ValueError(f'Duplicate news IDs across pages: {code}')
        records.extend(province_rows)
    return records, queries


def stage_overlap(event_day, year, month, age):
    """Percent of possible harvest dates, NOT percent of affected trees/area."""
    if age not in (120, 130, 140, 150):
        raise ValueError('Unsupported fruit-age scenario')
    days = [date(year, month, 1) + timedelta(days=n)
            for n in range(calendar.monthrange(year, month)[1])]
    counts = Counter()
    for harvest_day in days:
        since_bloom = (event_day - harvest_day).days + age
        if since_bloom < -90:
            stage = STAGES[0]
        elif since_bloom < 0:
            stage = STAGES[1]
        elif since_bloom < 30:
            stage = STAGES[2]
        elif since_bloom < 60:
            stage = STAGES[3]
        elif since_bloom < 90:
            stage = STAGES[4]
        elif since_bloom < age:
            stage = STAGES[5]
        else:
            stage = STAGES[6]
        counts[stage] += 1
    return {f'{s}_candidate_days_pct': counts[s] * 100 / len(days) for s in STAGES}


def reviewed_overlaps(news):
    path = DATA / 'disaster_events_reviewed.json'
    reviewed = json.loads(path.read_text(encoding='utf-8'))
    by_id = {r['news_id']: r for r in news}
    if len({r['news_id'] for r in reviewed['events']}) != len(reviewed['events']):
        raise ValueError('Duplicate reviewed news ID')
    with (DATA / 'harvest_monthly.csv').open(encoding='utf-8-sig', newline='') as stream:
        harvest = list(csv.DictReader(stream))
    overlaps = []
    for event in reviewed['events']:
        row = by_id[event['news_id']]
        if row['province_code'] != event['province_code'] or row['url'] != event['url']:
            raise ValueError('Reviewed report does not match source index')
        day = date.fromisoformat(event['observed_event_date'])
        if event['event_end_date'] and date.fromisoformat(event['event_end_date']) < day:
            raise ValueError('Reviewed event ends before observed date')
        row.update(review_status='event_date_and_area_reviewed_crop_loss_not_inferred',
                   reviewed_event_date=day.isoformat(),
                   reviewed_districts='; '.join(event['districts']),
                   crop_damage_status=event['crop_damage_status'])
        for cohort in harvest:
            year, month = int(cohort['year_ce']), int(cohort['month_number'])
            if cohort['province_code'] != event['province_code'] or year not in (day.year, day.year + 1):
                continue
            if float(cohort['tonnes']) <= 0:
                continue
            for age in (120, 130, 140, 150):
                values = stage_overlap(day, year, month, age)
                if year > day.year and values['before_window_candidate_days_pct'] == 100:
                    continue
                overlaps.append(dict(news_id=event['news_id'], province_code=event['province_code'],
                                     observed_event_date=day.isoformat(), hazard_type=event['hazard_type'],
                                     reported_districts='; '.join(event['districts']),
                                     area_context='local_report_not_province_wide_exposure',
                                     cohort_year=year, cohort_month=month, age_days=age,
                                     observed_cohort_tonnes=cohort['tonnes'],
                                     **values, interpretation='possible_dates_not_orchard_damage',
                                     source_url=event['url']))
    return overlaps, dict(path=str(path.relative_to(ROOT)),
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          reviewed_reports=len(reviewed['events']), overlap_rows=len(overlaps),
                          harvest_source_sha256=hashlib.sha256((DATA / 'harvest_monthly.csv').read_bytes()).hexdigest())


def main():
    rows, sources = [], []
    for key, hazard in DATASETS.items():
        metadata, manifest = package(key)
        resources = []
        for resource in metadata['resources']:
            if resource['format'].lower() != 'csv':
                continue
            payload, digest, path = fetch(resource['url'], f'{key}_{resource["id"]}.csv')
            selected = parse_resource(payload, key, hazard, resource['id'])
            rows.extend(selected)
            resources.append(dict(id=resource['id'], url=resource['url'], sha256=digest,
                                  snapshot=path, selected_rows=len(selected),
                                  description=resource.get('description'),
                                  last_modified=resource.get('last_modified')))
        sources.append(dict(dataset_id=key, title=metadata['title'], hazard_type=hazard,
                            url=f'https://catalog.disaster.go.th/dataset/{key}',
                            metadata=manifest, resources=resources))
    summary = summarize(rows)
    news, news_queries = fetch_news()
    overlaps, event_review = reviewed_overlaps(news)
    drought = fetch_drought()
    plans, plan_manifest = package(PLAN_ID)
    province_plans = [dict(province_code=code, province_name=name, title=r['name'],
                           url=r['url'], evidence_status='document_link_only_not_dated_event')
                      for code, name in PROVINCES.items() for r in plans['resources']
                      if name in r['name']]
    assert len(summary) == 60
    assert {r['PROVINCE_CODE'] for r in rows} == set(PROVINCES)
    write_csv(DATA / 'disaster_village_annual.csv', rows)
    write_csv(DATA / 'disaster_province_annual.csv', summary)
    write_csv(DATA / 'disaster_news_index.csv', news)
    write_csv(DATA / 'disaster_harvest_overlap.csv', overlaps)
    review = dict(
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(), provinces=PROVINCES,
        sources=sources, province_plan_catalog=plan_manifest, province_plans=province_plans,
        news_sources=dict(endpoint=NEWS_ENDPOINT, discovery_url='https://dpmreporter.disaster.go.th/portal/assets/js/modules/disaster_news.js',
                          requested_date_range=list(NEWS_RANGE), requested_type_ids=NEWS_TYPES,
                          queries=news_queries, index_rows=len(news)),
        event_review=event_review,
        drought_statistics=drought,
        additional_pending_sources=[dict(
            province_code='33', url='https://data.go.th/dataset/dis_2568_56',
            title='สถิติการเกิดอุทกภัยรายตำบลและหมู่บ้าน',
            agency='สำนักงานป้องกันและบรรเทาสาธารณภัยจังหวัดศรีสะเกษ',
            status='catalog_metadata_reviewed_resource_not_downloaded',
            note='Metadata describes fiscal-year counts 2562-2567; do not merge with calendar-year statistics without checking the resource.')],
        selected_source_rows=len(rows), summary_rows=len(summary),
        ambiguous_records=[r for r in rows if r['quality_status'] != 'retained'],
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        interpretation_limits=[
            'Counts are village-events, not unique province-wide disasters, flooded rai, or durian loss.',
            'Blank source cells remain blank. Neither missing cells nor absent villages establish zero disasters.',
            'Annual completeness is unverified, especially the sparse 2024 column; do not use as closed-year targets.',
            'Annual columns have no event dates; these cannot identify shocks in a fruit-development window.',
            'Duplicate village IDs are retained for audit but excluded from every summary until corrected by source.',
            'Province plans include historical statistics and prospective risk; a plan is not an observed disaster.',
            'Statistics are not bearing-orchard-area weighted and are not automatically merged into ML training.',
            'News items are sparse reports, sometimes warnings or aid updates; news_datetime is not automatically an event onset.',
            'An empty province-year news search means no retrieved report, not proof that no disaster happened.',
            'The public website search endpoint is discovered from its own JavaScript, not a guaranteed stable API contract.',
            'Only report metadata are exported; raw responses with public personal details/coordinates remain in ignored evidence/.',
            'Harvest overlap uses actual reported monthly cohorts and uniform possible dates with ages 120/130/140/150 days; retrospective only.',
            'Candidate-date percentages are not probabilities of damage, damaged orchard area, observed phenology, or causal effect.',
            'Next-year cohorts can overlap late-year events; post-harvest events cannot explain losses of already harvested cohorts.',
        ],
    )
    (DATA / 'disaster_source_review.json').write_text(
        json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
    for code, name in PROVINCES.items():
        counts = Counter(r['hazard_type'] for r in rows if r['PROVINCE_CODE'] == code)
        print(name, dict(counts))
    print(f'{len(rows)} source rows; {len(summary)} province-year-hazard rows; '
          f'{len(review["ambiguous_records"])} quarantined rows')


if __name__ == '__main__':
    main()
