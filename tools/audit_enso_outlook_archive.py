"""Read-only NOAA archive audit. Never imports ML builders or fits a model."""
import argparse
import calendar
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import re
import shutil
import unicodedata

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ANCHORS = {'22': 4, '33': 5, '53': 6, '84': 7, '86': 7}
PILOT = (2017, 2020, 2023, 2025)
BASE = 'https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/'
ARCHIVE = 'https://www.cpc.ncep.noaa.gov/products/expert_assessment/ENSO_DD_archive.php'


def normalized(text):
    result = ' '.join(unicodedata.normalize('NFKC', html.unescape(text)).split())
    if '</p>' in result:
        result = BeautifulSoup(result, 'html.parser').get_text(' ', strip=True)
    result = re.sub(r'ENSO-\s+neutral', 'ENSO-neutral', result)
    return result.replace('El Nino', 'El Niño').replace('La Nina', 'La Niña')


def parse_pdf(raw, year, month):
    text = PdfReader(io.BytesIO(raw)).pages[0].extract_text()
    parts = [normalized(p) for p in re.split(r'\n\s*\n', text) if p.strip()]
    synthetic = '<div>' + html.escape(normalized(text)) + '</div>' + ''.join('<p>' + html.escape(p) + '</p>' for p in parts)
    return parse(synthetic.encode(), year, month)


def parse(content, year, month):
    soup = BeautifulSoup(content, 'html.parser')
    text = normalized(soup.get_text(' ', strip=True))
    paragraphs = [normalized(p.get_text(' ', strip=True)) for p in soup.find_all('p')]
    start = text.lower().find('issued by')
    header = text[start:start + 400] if start >= 0 else ''
    match = re.search(r'\b(\d{1,2})\s+(' + '|'.join(calendar.month_name[1:]) + r')\s+(\d{4})\b', header)
    published = None
    if match:
        published = date(int(match[3]), list(calendar.month_name).index(match[2]), int(match[1]))
    if published and (published.year != year or published.month != month):
        published = None  # Never accept a redirect/current bulletin as an old vintage.
    alert = re.search(r'ENSO Alert System Status:\s*(.*?)(?=Synopsis:|$)', text)
    synopsis = next((p for p in paragraphs if p.startswith('Synopsis:')), '')
    if not synopsis:
        found = re.search(r'Synopsis:\s*(.*?\.)(?=\s|$)', text)
        synopsis = found[0] if found else ''
    body = text
    state = None
    state_evidence = ''
    # Only observational phrasing, not Watch/Advisory or future synopsis probabilities.
    for pattern in (
        r'(?:Overall|Collectively)[^.]{0,250}?(?:consistent with|reflect(?:ed)?|indicated|reflecting)\s+(?:a\s+|weak\s+|weakening\s+|continued\s+|strong\s+|moderate\s+)*(ENSO-neutral|La Niña|El Niño)',
        r'(?:system|conditions)\s+(?:was|were|remained)\s+consistent with\s+(?:weak\s+|moderate\s+|strong\s+)?(ENSO-neutral|La Niña|El Niño)',
        r'(ENSO-neutral|La Niña|El Niño)\s+(?:conditions\s+)?(?:continued|persisted|were present|prevailed|emerged)\s+(?:during|in|across|over)',
        r'During\s+\w+\s+\d{4},\s+(ENSO-neutral|La Niña|El Niño)\s+continued',
    ):
        found = re.search(pattern, body, flags=re.I)
        if found:
            state = found[1]
            state_evidence = found[0]
            break
    if state is None:
        for found in re.finditer(r'(?:Overall|Collectively)[^.]{0,450}', body, re.I):
            clause = found[0]
            if (re.search(r'ocean|atmospher|system|observations|features|anomalies', clause, re.I)
                    and re.search(r'reflect|consistent|indicat|suggest|remains', clause, re.I)
                    and not re.search(r'forecast|models?', clause, re.I)):
                phase = re.search(r'ENSO-neutral|La Niña|El Niño', clause, re.I)
                if phase:
                    state, state_evidence = phase[0], clause
                    break
    probabilities = []
    # ponytail: text percentages only; graphics/full probability vectors need a separate audit.
    for p in paragraphs:
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z])', p):
            if not re.search(r'chance|probabilit', sentence, re.I):
                continue
            for found in re.finditer(r'(?P<approx>~|about\s+|approximately\s+)?(?P<low>\d+(?:\.\d+)?)\s*(?:to|[-–])?\s*(?P<high>\d+(?:\.\d+)?)?\s*%', sentence):
                low = float(found['low'])
                high = float(found['high']) if found['high'] else low
                if not 0 <= low <= high <= 100:
                    continue
                item = dict(percent_low=low, percent_high=high,
                            approximate=bool(found['approx']), evidence=sentence,
                            phase=None, valid_start=None, valid_end=None,
                            mapping_status='requires_phase_horizon_review')
                # Keep sparse percentages as evidence, never invent other phases or horizons.
                if item not in probabilities:
                    probabilities.append(item)
    horizon_mentions = sorted(set(re.findall(
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*[-–]\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|Northern Hemisphere\s+(?:winter|spring|summer|fall)\s+\d{4}',
        synopsis)))
    return dict(publication_date=published.isoformat() if published else None,
                publication_evidence=match[0] if published else None,
                publication_precision='date_only' if published else 'unknown',
                publication_basis='NOAA bulletin issuance header',
                alert_status=alert[1].strip() if alert else None,
                observed_state=state, observed_state_evidence=state_evidence or None,
                synopsis=synopsis, forecast_horizon_mentions=horizon_mentions,
                forecast_probability_mentions=probabilities,
                probability_vector_status='unverified_graphics_not_audited',
                historical_content_authentication='unverified',
                revised_oni_used=False)


def fetch(key, destination, listed_urls):
    year, month = key
    url = BASE + f'enso_disc_{calendar.month_abbr[month].lower()}{year}/ensodisc.shtml'
    record = dict(archive_year=year, archive_month=month, source_url=url,
                  product_family='NOAA ENSO Diagnostic Discussion', signal_type='observed_and_forecast_bulletin')
    landing = BASE + f'enso_disc_{calendar.month_abbr[month].lower()}{year}/'
    record.update(archive_index_url=ARCHIVE, archive_link_verified=landing in listed_urls)
    if landing not in listed_urls:
        return dict(record, missing_reason='not_listed_in_official_archive')
    try:
        response = requests.get(url, timeout=35)
        record.update(http_status=response.status_code, final_url=response.url,
                      retrieved_utc=datetime.now(timezone.utc).isoformat(),
                      http_last_modified=response.headers.get('Last-Modified'))
        raw = response.content
        record['source_sha256'] = hashlib.sha256(raw).hexdigest()
        filename = f'{year}_{month:02d}.html'
        (destination / filename).write_bytes(raw)
        record['snapshot_path'] = filename
        if response.status_code != 200:
            record['missing_reason'] = f'http_{response.status_code}'
        else:
            record.update(parse(raw, year, month))
            record['missing_reason'] = None if record['publication_date'] else 'missing_or_wrong_issuance_header'
        if record.get('missing_reason'):
            # Follow the official landing page's English PDF link; do not assume HTTP 200 is a bulletin.
            landing_response = requests.get(landing, timeout=35)
            links = BeautifulSoup(landing_response.content, 'html.parser').find_all('a')
            pdf_link = next((a.get('href') for a in links if a.get_text(' ', strip=True) == 'English Version'
                             and str(a.get('href')).lower().endswith('.pdf')), None)
            if pdf_link:
                from urllib.parse import urljoin
                pdf_url = urljoin(landing, pdf_link)
                pdf = requests.get(pdf_url, timeout=35)
                if pdf.status_code == 200 and pdf.content.startswith(b'%PDF-'):
                    filename = f'{year}_{month:02d}.pdf'
                    (destination / filename).write_bytes(pdf.content)
                    original = {k: record.get(k) for k in ('source_url', 'source_sha256', 'snapshot_path', 'http_status', 'missing_reason')}
                    record.update(parse_pdf(pdf.content, year, month))
                    record.update(html_attempt=original, source_url=pdf_url,
                                  source_sha256=hashlib.sha256(pdf.content).hexdigest(), snapshot_path=filename,
                                  retrieved_utc=datetime.now(timezone.utc).isoformat(), http_status=pdf.status_code,
                                  http_last_modified=pdf.headers.get('Last-Modified'), source_format='pdf_text_first_page',
                                  missing_reason=None if record['publication_date'] else 'pdf_issuance_unparsed')
    except requests.RequestException as error:
        record.update(missing_reason='fetch_failed_' + type(error).__name__)
    return record


def issues(year):
    return {p: date(year, m, 1) - timedelta(days=60) for p, m in ANCHORS.items()}


def select(records, cutoff):
    # Date-only publication is conservatively unavailable until the next local day.
    valid = [r for r in records if r.get('publication_date') and date.fromisoformat(r['publication_date']) < cutoff]
    return max(valid, key=lambda r: r['publication_date']) if valid else None


def row(records, province, year, **context):
    issue = issues(year)[province]
    use_cutoff = context.pop('use_cutoff', issue)
    cutoff = min(issue, use_cutoff)
    relevant = [r for r in records if r['archive_year'] == year]
    chosen = select(relevant, cutoff)
    value = dict(province_code=province, target_year=year, issue_date=issue.isoformat(),
                 shared_fit_cutoff=min(issues(year).values()).isoformat(), use_cutoff=cutoff.isoformat(), **context)
    if chosen is None:
        status = 'unverified' if any(r.get('missing_reason') for r in relevant) else 'unavailable'
        return dict(value, availability_status=status, missing_reason='no_verified_pre_cutoff_bulletin')
    # Require a dated bulletin from the immediately preceding calendar month or current month.
    age = (cutoff - date.fromisoformat(chosen['publication_date'])).days
    status = 'verified_available' if age <= 45 else 'unavailable'
    if age > 45 and any(r.get('missing_reason') for r in relevant):
        status = 'unverified'
    return dict(value, availability_status=status,
                publication_date=chosen['publication_date'], publication_evidence=chosen['publication_evidence'],
                source_url=chosen['source_url'], source_sha256=chosen['source_sha256'],
                snapshot_path=chosen['snapshot_path'], observed_state=chosen['observed_state'],
                state_status='verified_available' if chosen['observed_state'] and status == 'verified_available' else 'unverified',
                forecast_probability_mentions=chosen['forecast_probability_mentions'],
                forecast_horizon_mentions=chosen['forecast_horizon_mentions'],
                probability_vector_status=chosen['probability_vector_status'],
                content_authentication='unverified',
                missing_reason='stale_bulletin_over_45_days' if age > 45 else None)


def summary(rows):
    counts = {s: sum(r['availability_status'] == s for r in rows)
              for s in ('verified_available', 'unverified', 'unavailable')}
    return dict(rows=len(rows), counts=counts,
                percentages={k: round(v * 100 / len(rows), 2) for k, v in counts.items()},
                observed_state_verified=sum(r.get('state_status') == 'verified_available' for r in rows),
                full_probability_vectors_verified=0)


def write_csv(path, rows):
    fields = sorted({k for r in rows for k in r})
    with path.open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                             for k, v in r.items()})


def run(output, source_run=None):
    output.mkdir(parents=True, exist_ok=False)
    sources = output / 'sources'
    sources.mkdir()
    cached = {}
    if source_run:
        index_bytes = (source_run / 'sources/archive_index.html').read_bytes()
        source_summary = json.loads((source_run / 'summary.json').read_text(encoding='utf-8'))
        if hashlib.sha256(index_bytes).hexdigest() != source_summary['archive_index_sha256']:
            raise ValueError('Cached archive index changed')
        with (source_run / 'documents.csv').open(encoding='utf-8-sig', newline='') as handle:
            for record in csv.DictReader(handle):
                cached[int(record['archive_year']), int(record['archive_month'])] = record
    else:
        index = requests.get(ARCHIVE, timeout=35)
        index.raise_for_status()
        index_bytes = index.content
    (sources / 'archive_index.html').write_bytes(index_bytes)
    from urllib.parse import urljoin
    listed_urls = {urljoin(ARCHIVE, a.get('href', '')) for a in BeautifulSoup(index_bytes, 'html.parser').find_all('a')}
    def obtain(key):
        if key not in cached:
            return fetch(key, sources, listed_urls)
        record = dict(cached[key])
        filename = record['snapshot_path']
        if Path(filename).name != filename:
            raise ValueError('Invalid cached snapshot path')
        raw = (source_run / 'sources' / filename).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['source_sha256']:
            raise ValueError('Cached source changed')
        shutil.copyfile(source_run / 'sources' / filename, sources / filename)
        record.update(parse_pdf(raw, *key) if filename.endswith('.pdf') else parse(raw, *key))
        record.update(archive_year=key[0], archive_month=key[1], http_status=int(record['http_status']),
                      missing_reason=None if record['publication_date'] else 'cached_issuance_unparsed')
        return record
    def download(years):
        with ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(obtain, [(y, m) for y in years for m in range(1, 6)]))
    records = download(PILOT)
    pilot = [row(records, p, y, cohort='pilot') for y in PILOT for p in ANCHORS]
    pilot_passed = all(r['availability_status'] == 'verified_available' for r in pilot)
    if pilot_passed:
        records += download([y for y in range(2010, 2026) if y not in PILOT])
    years = range(2010, 2026) if pilot_passed else PILOT
    inputs = [row(records, p, y, cohort='outer' if y >= 2017 else 'training_history') for y in years for p in ANCHORS]
    folds = []
    if pilot_passed:
        for outer in range(2017, 2026):
            for fold in [*range(outer - 3, outer), outer]:
                fit_cutoff = min(issues(fold).values())
                for y in range(2010, fold + 1):
                    for p in ANCHORS:
                        training = y < fold
                        folds.append(row(records, p, y, outer_year=outer, fold_year=fold,
                                         input_role='training_input' if training else 'forecast_input',
                                         fold_fit_cutoff=fit_cutoff.isoformat(),
                                         outer_selection_cutoff=min(issues(outer).values()).isoformat(),
                                         use_cutoff=fit_cutoff if training else issues(y)[p]))
    write_csv(output / 'documents.csv', records)
    write_csv(output / 'pilot.csv', pilot)
    write_csv(output / 'availability.csv', inputs)
    if folds:
        write_csv(output / 'fold_availability.csv', folds)
    result = dict(pilot_passed=pilot_passed, pilot=summary(pilot), all_inputs=summary(inputs),
                  outer=summary([r for r in inputs if r['target_year'] >= 2017]),
                  folds=summary(folds) if folds else None,
                  source_documents=len(records), fetched_ok=sum(r.get('http_status') == 200 for r in records),
                  dated_documents=sum(bool(r.get('publication_date')) for r in records),
                  archive_index_sha256=hashlib.sha256(index_bytes).hexdigest(), archive_index_url=ARCHIVE,
                  reused_source_run=str(source_run) if source_run else None,
                  state_missing_documents=[r['source_url'] for r in records if not r.get('observed_state')],
                  protocol=dict(anchors=ANCHORS, lead_days=60, years=list(years), outer_years=list(range(2017, 2026)),
                                inner_years=3, latest_as_of='publication_date strictly before issue local day',
                                content_authentication='not independently certified', probability_parser='sparse text mentions only'),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  models_fitted=0, ml_pipeline_modified=False)
    (output / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-run', type=Path, help='Reparse hash-verified audit snapshots, without refetching')
    args = parser.parse_args()
    safe_root = (ROOT / 'research_data/enso_outlook_archive_audit').resolve()
    if not args.output.resolve().is_relative_to(safe_root) or args.output.resolve() == safe_root:
        raise ValueError('Use a new run directory under research_data/enso_outlook_archive_audit')
    if args.source_run and not args.source_run.resolve().is_relative_to(safe_root):
        raise ValueError('Source run must belong to the isolated audit root')
    run(args.output, args.source_run)
