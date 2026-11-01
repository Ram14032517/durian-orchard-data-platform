"""Fabricated unit-test rows only: never an observation, metric or research export."""
import hashlib
from pathlib import Path
import pandas as pd


def expansion_annual(pe):
    rows = []
    for index, province in enumerate(pe.COHORTS['10']):
        for year in range(2009, 2026):
            value = 1000. + index * 5 + (year - 2009) % 2 * 50
            lat, lon = pe.POINTS.get(province, [9., 99.])
            rows.append(dict(province_code=province, province_name='synthetic-' + province,
                year_ce=year, bearing_rai=1000., production_tonnes=value,
                **{pe.rb.TARGET: value}, weather_latitude=lat, weather_longitude=lon))
    return pd.DataFrame(rows)


def expansion_prepared(et):
    pe, rb = et.pe, et.rb
    annual = expansion_annual(pe)
    lookup = annual.set_index(et.KEYS)[rb.TARGET]
    inputs = pd.DataFrame([dict(province_code=p, year_ce=y,
        previous_yield_kg_rai=float(lookup.loc[p, y - 1]),
        **{f: 1. + (y - 2010) / 10 for f in rb.FEATURES[1:]})
        for p in pe.COHORTS['10'] for y in rb.YEARS])
    folds = []
    for size in pe.COHORTS:
        for outer in rb.OUTER_YEARS:
            for year in range(outer - 3, outer + 1):
                dates = {p: rb.midnight(rb.issue_date(dict(kind='fixed_calendar', anchors=pe.ANCHORS), p, year, 60))
                         for p in pe.COHORTS['10']}
                keys = sorted((p, y) for p in pe.COHORTS[size] for y in range(2010, year))
                folds.append(dict(cohort=size, outer_year=outer, fold_year=year,
                    issue_dates=dates, fit_cutoff=min(dates.values()),
                    selection_cutoff=min(rb.midnight(rb.issue_date(dict(kind='fixed_calendar', anchors=pe.ANCHORS), p, outer, 60)) for p in rb.PROVINCES),
                    training_rows=len(keys), forecast_rows=len(pe.COHORTS[size]),
                    selection_keys=[[p, year] for p in rb.PROVINCES],
                    training_labels_sha256=rb.digest_value([[p, y, float(lookup.loc[p, y])] for p, y in keys])))
    source = Path(__file__).resolve()
    version = hashlib.sha256(source.read_bytes()).hexdigest()
    records = {kind + ':' + p: dict(role=role, path=str(source.relative_to(rb.ROOT)),
        source_version=version, publication_date=None, availability_status='unverified', evidence={})
        for kind, role in [('training_labels', 'training_label'), ('selection_labels', 'selection_label')]
        for p in pe.COHORTS['10']}
    return dict(inputs=inputs, annual=annual, folds=folds,
                manifest=dict(records=records, fixture_kind='synthetic_unit_only'))
