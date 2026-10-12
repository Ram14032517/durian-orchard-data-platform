"""Download public NOAA ENSO feeds; context, not local drought or fruit-age truth."""
import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research_data/five_province_history'
SEASONS = ('DJF', 'JFM', 'FMA', 'MAM', 'AMJ', 'MJJ', 'JJA', 'JAS', 'ASO', 'SON', 'OND', 'NDJ')
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December')
URLS = {
    'ONI': 'https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt',
    'RONI': 'https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt',
    'forecast': 'https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/probabilities/',
}


def season_dates(year, month):
    """The source year belongs to the center month; DJF/NDJ cross year boundaries."""
    center = year * 12 + month - 1
    start_year, start_month = divmod(center - 1, 12)
    stop_year, stop_month = divmod(center + 2, 12)
    return (date(start_year, start_month + 1, 1).isoformat(),
            (date(stop_year, stop_month + 1, 1) - timedelta(days=1)).isoformat())


def parse_observed(text, index):
    if index not in ('ONI', 'RONI'):
        raise ValueError('Unknown index')
    lines = text.splitlines()
    expected = ['SEAS', 'YR', 'TOTAL', 'ANOM'] if index == 'ONI' else ['SEAS', 'YR', 'ANOM']
    if not lines or lines[0].split() != expected:
        raise ValueError('NOAA index header changed')
    rows, previous, previous_regime, streak = [], None, None, 0
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != len(expected) or fields[0] not in SEASONS:
            raise ValueError('Invalid ENSO row')
        season, year, value = fields[0], int(fields[1]), float(fields[-1])
        month = SEASONS.index(season) + 1
        ordinal = year * 12 + month - 1
        if not 1950 <= year <= 2200 or not math.isfinite(value) or abs(value) > 10:
            raise ValueError('Invalid index year/value; missing is not neutral')
        if previous is not None and ordinal != previous + 1:
            raise ValueError('Duplicate, unordered or missing ENSO season')
        regime = 'warm' if value >= .5 else 'cold' if value <= -.5 else 'neutral'
        streak = streak + 1 if regime == previous_regime and regime != 'neutral' else 1
        start, end = season_dates(year, month)
        rows.append(dict(index=index, year_ce=year, center_month=month, season=season,
            period_start=start, period_end=end, anomaly_c=value, threshold_regime_proxy=regime,
            persistent_index_phase_to_date=('neutral' if regime == 'neutral' else
                ('el_nino' if regime == 'warm' else 'la_nina') if streak >= 5 else 'not_yet_persistent'),
            same_regime_seasons_to_date=0 if regime == 'neutral' else streak,
            kind='observed_index_revised_snapshot', point_in_time_vintage_verified=False))
        previous, previous_regime = ordinal, regime
    if not rows:
        raise ValueError('Empty ENSO history')
    return rows


class ProbabilityTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = self.in_cell = False
        self.rows, self.row, self.cell = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag == 'table' and dict(attrs).get('id') == 'probabilities-table':
            self.active = True
        if self.active and tag == 'tr':
            self.row = []
        if self.active and tag in ('th', 'td'):
            self.in_cell, self.cell = True, []

    def handle_data(self, data):
        if self.active and self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if self.active and tag in ('th', 'td') and self.in_cell:
            self.row.append(' '.join(' '.join(self.cell).split()))
            self.in_cell = False
        if self.active and tag == 'tr' and self.row:
            self.rows.append(self.row)
        if self.active and tag == 'table':
            self.active = False


def parse_forecast(html):
    issued = re.search(r'Issued\s+([A-Za-z]+)\s+(\d{4})', html)
    if not issued or issued[1] not in MONTHS or 'Relative Oceanic' not in html:
        raise ValueError('Missing issuance month or RONI definition')
    issued_year, issued_month = int(issued[2]), MONTHS.index(issued[1]) + 1
    issue_ordinal = issued_year * 12 + issued_month - 1
    table = ProbabilityTable()
    table.feed(html)
    if (len(table.rows) != 10 or table.rows[0] != ['Season', 'La Niña', 'Neutral', 'El Niño']):
        raise ValueError('NOAA probability table changed; expect header plus nine seasons')
    rows, previous = [], None
    for cells in table.rows[1:]:
        if len(cells) != 4 or not cells[0].split() or cells[0].split()[0] not in SEASONS:
            raise ValueError('Invalid probability row')
        season = cells[0].split()[0]
        month = SEASONS.index(season) + 1
        if previous is None:
            candidates = [y * 12 + month - 1 for y in (issued_year - 1, issued_year, issued_year + 1)]
            candidates = [n for n in candidates if issue_ordinal - 1 <= n <= issue_ordinal + 1]
            if len(candidates) != 1:
                raise ValueError('Cannot assign forecast year from issuance and season')
            ordinal = candidates[0]
        else:
            ordinal = previous + 1
            if ordinal % 12 != month - 1:
                raise ValueError('Forecast seasons must be consecutive')
        year = ordinal // 12
        probabilities = list(map(float, cells[1:]))
        if (any(not math.isfinite(p) or not 0 <= p <= 100 for p in probabilities)
                or abs(sum(probabilities) - 100) > 1):
            raise ValueError('Invalid forecast probabilities')
        start, end = season_dates(year, month)
        winners = [phase for phase, p in zip(('la_nina', 'neutral', 'el_nino'), probabilities)
                   if p == max(probabilities)]
        rows.append(dict(index='RONI', issued_year=issued_year, issued_month=issued_month,
            issued_day=None, issuance_precision='month_only', year_ce=year, center_month=month,
            season=season, period_start=start, period_end=end,
            la_nina_pct=probabilities[0], neutral_pct=probabilities[1], el_nino_pct=probabilities[2],
            most_likely_phase=winners[0] if len(winners) == 1 else 'tie',
            kind='forecast_probability_not_observed_status'))
        previous = ordinal
    return rows


def annual_context(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['index'], row['year_ce']].append(row)
    return [dict(index=index, year_ce=year, observed_seasons=len(group),
        complete_year=len(group) == 12,
        threshold_regimes_present=sorted(set(r['threshold_regime_proxy'] for r in group)),
        warm_seasons=sum(r['threshold_regime_proxy'] == 'warm' for r in group),
        cold_seasons=sum(r['threshold_regime_proxy'] == 'cold' for r in group),
        neutral_seasons=sum(r['threshold_regime_proxy'] == 'neutral' for r in group))
        for (index, year), group in sorted(groups.items())]


def run(start_year=2009):
    if not 1950 <= start_year <= date.today().year:
        raise ValueError('Invalid start year')
    fetched_at = datetime.now(timezone.utc).isoformat()
    payloads, sources = {}, {}
    for name, url in URLS.items():
        # ponytail: public TXT/HTML feeds, not a versioned JSON API; schema changes fail closed.
        with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0 DurianResearch/1.0'}), timeout=30) as response:
            payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                raise ValueError('Unexpectedly large NOAA feed')
            payloads[name] = payload.decode('utf-8-sig')
            digest = hashlib.sha256(payload).hexdigest()
            path = DATA / 'evidence' / 'enso' / (digest + ('.html' if name == 'forecast' else '.txt'))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            sources[name] = dict(url=url, sha256=digest, retrieved_utc=fetched_at,
                snapshot=str(path.relative_to(ROOT)).replace('\\', '/'),
                http_last_modified=response.headers.get('Last-Modified'))
    observed = [row for index in ('ONI', 'RONI') for row in parse_observed(payloads[index], index)
                if row['year_ce'] >= start_year]
    if set(r['index'] for r in observed) != {'ONI', 'RONI'}:
        raise ValueError('Requested years contain no data')
    forecast = parse_forecast(payloads['forecast'])
    result = dict(schema_version=1, retrieved_utc=fetched_at, sources=sources,
        documentation_urls=[
            'https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/',
            'https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/'],
        official_monitoring_index='RONI', observed=observed, annual_context=annual_context(observed),
        forecast=forecast, train_imported=False,
        limitations=[
            'Index thresholds are computed proxies, not an official coupled ocean-atmosphere diagnosis.',
            'Persistence counts only preceding/current seasons; no backward confirmation using later seasons.',
            'Revised current snapshots are not historical as-of observations. Publication vintages are not reconstructed.',
            'RONI/ONI source edition is a live endpoint; retain hashes and documentation, never silently splice versions.',
            'Recent RONI observations can be revised; neutral ENSO is not normal local weather.',
            'Forecasts cover nine overlapping three-month seasons, not a guaranteed label for a whole year.',
            'Forecast issuance is month-only here; the exact publication day has not been verified.',
            'ENSO alone cannot determine Thai provincial rain, drought or fruit age. Use local stage weather.',
            'No automatic days-shorter/longer formula has been calibrated or imported into yield training.'])
    target = DATA / 'enso_context.json'
    # One normalized JSON prevents mixing an updated history with an old forecast file.
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(target)
    print(json.dumps(dict(observed_rows=len(observed), forecast_rows=len(forecast),
        forecast_issue=f'{forecast[0]["issued_year"]}-{forecast[0]["issued_month"]:02d}',
        output=str(target)), ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-year', type=int, default=2009)
    run(parser.parse_args().start_year)
