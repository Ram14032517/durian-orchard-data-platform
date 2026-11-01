"""Phase 5A preparation only: no fitting entry point, no production mutations."""
import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import sys
import tempfile

import pandas as pd

import experiment_weather_ablation as wa

rb = wa.rb
sys.path.insert(0, str(rb.ROOT / 'tools'))
import audit_enso_outlook_archive as archive

ARCHIVE = rb.ROOT / 'research_data/enso_outlook_archive_audit/phase4b_20261011_noaa_reviewed'
OUTPUT_ROOT = rb.OUT / 'enso_state_preparation_exploratory'
FEATURES = ['enso_el_nino', 'enso_neutral', 'enso_la_nina']
STATES = {'El Niño': 'El Niño', 'ENSO-neutral': 'Neutral', 'La Niña': 'La Niña'}
ARMS = ('catboost_with_weather', 'catboost_with_weather_enso_state')


def candidates():
    return [dict(kind='catboost', parameter=dict(depth=d, l2_leaf_reg=10, learning_rate=.03),
                 features=list(rb.FEATURES) + (FEATURES if arm == ARMS[1] else []), group=arm)
            for arm in ARMS for d in (2, 3)]


def protocol():
    base = deepcopy(wa.protocol())
    base.update(candidates=candidates(), enso_encoding=dict(states=list(STATES.values()),
        columns=FEATURES, method='fixed one-hot; no target-derived mapping'),
        enso_selection='latest bulletin strictly before min(row issue, role cutoff); max age 45 days',
        enso_content_authentication='unverified; exploratory only', forecast_probability=False,
        revised_oni=False)
    return base


def evidence_matches(actual, expected, filename, field):
    if actual == expected:
        return True
    # PDF extractors can split a word ("and" -> "an d") between versions.
    # Only evidence formatting may differ: dates, states and all source bytes
    # remain exact checks, and no non-whitespace character may be changed.
    return (filename.endswith('.pdf') and field in ('publication_evidence','observed_state_evidence')
            and re.sub(r'\s+','',actual) == re.sub(r'\s+','',expected))


def load_archive(root=ARCHIVE):
    """Check bytes and re-extract states; metadata alone is insufficient lineage."""
    root = Path(root)
    tables = {n: pd.read_csv(root / (n + '.csv'), dtype=str, keep_default_na=False)
              for n in ('documents', 'availability', 'fold_availability')}
    docs, availability, folds = (tables[n] for n in ('documents', 'availability', 'fold_availability'))
    editions = {(str(y), str(m)) for y in rb.YEARS for m in range(1, 6)}
    if len(docs) != 80 or set(zip(docs.archive_year, docs.archive_month)) != editions:
        raise ValueError('Missing/duplicate archive editions')
    keys = {(p, str(y)) for p in rb.PROVINCES for y in rb.YEARS}
    if len(availability) != 80 or set(zip(availability.province_code, availability.target_year)) != keys:
        raise ValueError('Missing/duplicate archive province-year keys')
    expected_folds = {(str(o), str(f), p, str(y), 'training_input' if y < f else 'forecast_input')
        for o in rb.OUTER_YEARS for f in range(o - 3, o + 1)
        for y in range(2010, f + 1) for p in rb.PROVINCES}
    if len(folds) != len(expected_folds) or set(zip(folds.outer_year, folds.fold_year,
            folds.province_code, folds.target_year, folds.input_role)) != expected_folds:
        raise ValueError('Incomplete archive consumption records')
    records = docs.to_dict('records')
    integrity = {}
    for r in records:
        filename = r['snapshot_path']
        if Path(filename).name != filename or filename in ('', '.', '..'):
            raise ValueError('Unsafe archive snapshot path')
        source = root / 'sources' / filename
        content = source.read_bytes()
        actual = rb.digest(source)
        proof = dict(actual_sha256=actual, expected_sha256=r['source_sha256'], comparison='exact_bytes')
        if actual != r['source_sha256']:
            raise ValueError('Archive content hash mismatch: ' + filename)
        integrity[filename] = proof
        r.update(source_actual_sha256=actual,source_hash_comparison=proof['comparison'])
        parsed = (archive.parse_pdf if filename.endswith('.pdf') else archive.parse)(
            content, int(r['archive_year']), int(r['archive_month']))
        for field in ('publication_date', 'publication_evidence', 'observed_state', 'observed_state_evidence'):
            if not evidence_matches(parsed.get(field) or '',r[field],filename,field):
                raise ValueError('Archive metadata differs from actual source extraction: ' + filename + ' / ' + field)
        if (r['archive_link_verified'] != 'True' or r['revised_oni_used'] != 'False'
                or r['publication_basis'] != 'NOAA bulletin issuance header'
                or not r['source_url'].startswith(archive.BASE)
                or r['historical_content_authentication'] != 'unverified'):
            raise ValueError('Unexpected archive product/provenance')
    inventory = {str(p.relative_to(root)).replace('\\', '/'): rb.digest(p)
                 for p in [root / 'summary.json', root / 'sources/archive_index.html',
                           *[root / (n + '.csv') for n in tables],
                           *[root / 'sources' / r['snapshot_path'] for r in records]]}
    return dict(records=records, availability=availability, fold_availability=folds,
                hashes=inventory, root=root, source_integrity=integrity)


def select_document(records, issue_date, cutoff):
    issue = date.fromisoformat(issue_date[:10])
    use = min(issue, date.fromisoformat(cutoff[:10]))
    eligible = [r for r in records if r['publication_date']
                and date.fromisoformat(r['publication_date']) < use]
    if not eligible:
        raise ValueError('No bulletin before cutoff; no future filling')
    selected = max(eligible, key=lambda r: r['publication_date'])
    if sum(r['publication_date'] == selected['publication_date'] for r in eligible) != 1:
        raise ValueError('Ambiguous archive edition')
    if (use - date.fromisoformat(selected['publication_date'])).days > 45:
        raise ValueError('Stale/missing latest archive bulletin')
    if selected['observed_state'] not in STATES or not selected['observed_state_evidence']:
        raise ValueError('Missing explicit observed ENSO state')
    return selected


def project(frame, candidate):
    if candidate not in candidates():
        raise ValueError('Unapproved feature/grid/arm')
    if candidate['group'] == ARMS[0]:
        return wa.project(frame, candidate)
    expected = wa.KEYS + list(rb.FEATURES) + FEATURES
    if set(frame) != set(expected):
        raise ValueError('Unexpected or derived feature/target')
    result = frame[expected].copy()
    if not result[FEATURES].isin([0, 1]).all().all() or not result[FEATURES].sum(axis=1).eq(1).all():
        raise ValueError('Invalid ENSO one-hot values')
    return result


def augment(prepared, manifest, bundle, enabled=False):
    """Off returns the exact legacy object; on audits every real fold consumption."""
    wa.audit(prepared, manifest)
    if not enabled:
        return prepared, []
    result = deepcopy(prepared)
    history = bundle['availability'].set_index(['province_code', 'target_year'])
    consumption = bundle['fold_availability'].set_index(
        ['outer_year', 'fold_year', 'province_code', 'target_year', 'input_role'])
    traces = []
    for fold in result['folds']:
        for name, role in [('train_predictors', 'training_input'), ('forecast_predictors', 'forecast_input')]:
            values = []
            for row in fold[name].to_dict('records'):
                p, y = row['province_code'], int(row['year_ce'])
                issue = rb.issue_date(manifest['schedule'], p, y, 60).isoformat()
                cutoff = fold['fit_cutoff'] if role == 'training_input' else fold['issue_dates'][p]
                selected = select_document(bundle['records'], issue, cutoff)
                h = history.loc[p, str(y)]
                a = consumption.loc[str(fold['outer_year']), str(fold['fold_year']), p, str(y), role]
                for audited in (h, a):
                    if (audited['issue_date'] != issue[:10] or audited['state_status'] != 'verified_available'
                            or audited['availability_status'] != 'verified_available'
                            or audited['source_sha256'] != selected['source_sha256']
                            or audited['source_url'] != selected['source_url']
                            or audited['observed_state'] != selected['observed_state']
                            or audited['publication_date'] != selected['publication_date']):
                        raise ValueError('Archive availability disagrees with actual as-of join')
                if (a['fold_fit_cutoff'] != fold['fit_cutoff'][:10]
                        or a['outer_selection_cutoff'] != fold['selection_cutoff'][:10]
                        or a['use_cutoff'][:10] != min(issue[:10], cutoff[:10])):
                    raise ValueError('Archive fold cutoff mismatch')
                state = STATES[selected['observed_state']]
                encoding = [int(state == label) for label in STATES.values()]
                values.append(encoding)
                traces.append(dict(outer_year=fold['outer_year'], fold_year=fold['fold_year'],
                    input_role=role, province_code=p, year_ce=y, issue_date=issue, role_cutoff=cutoff,
                    use_cutoff=min(issue[:10], cutoff[:10]), publication_date=selected['publication_date'],
                    source_url=selected['source_url'], source_sha256=selected['source_sha256'],
                    source_actual_sha256=selected['source_actual_sha256'],
                    source_hash_comparison=selected['source_hash_comparison'],
                    snapshot_path=selected['snapshot_path'], state=state,
                    observed_state_evidence=selected['observed_state_evidence'],
                    consumed_values=dict(zip(FEATURES, encoding)),
                    content_authentication='unverified', availability_status='verified_available',
                    pit_certified=False))
            fold[name][FEATURES] = values
            for candidate in candidates():
                project(fold[name], candidate)
    if len(traces) != 1890:
        raise ValueError('Incomplete actual ENSO lineage')
    return result, traces


def cache_key(config, fold, candidate, train, forecast):
    if candidate not in candidates() or config['protocol'] != protocol():
        raise ValueError('Protocol/candidate changed')
    return rb.digest_value(dict(protocol=rb.digest_value(protocol()), archive=config['archive_hashes'],
        arm=candidate['group'], features=candidate['features'], parameter=candidate['parameter'],
        fold_year=fold['fold_year'], fit_cutoff=fold['fit_cutoff'], issue_dates=fold['issue_dates'],
        actual_consumed=[train.to_dict('records'), forecast.to_dict('records')]))


def write_preparation(prepared, config, traces, manifest, run_id, root=OUTPUT_ROOT):
    root = Path(root).absolute()
    if (not ((root.resolve() == root == OUTPUT_ROOT.absolute()) or rb.safe_temporary_root(root))
            or root.name != OUTPUT_ROOT.name
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', run_id)):
        raise ValueError('Unsafe experimental output directory')
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / run_id
    destination.mkdir(exist_ok=False)
    objects = dict(config=config, enso_lineage=traces, base_lineage=prepared['lineage'],
        base_availability=prepared['availability'], manifest=manifest,
        folds=[{k: v for k, v in f.items() if not isinstance(v, pd.DataFrame)} for f in prepared['folds']],
        status=dict(training_performed=False, pit_certified=False))
    for name, value in objects.items():
        with (destination / (name + '.json')).open('x', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
    for f in prepared['folds']:
        for name in ('train_predictors', 'forecast_predictors'):
            with (destination / f"{f['outer_year']}_{f['fold_year']}_{name}.csv").open('x', encoding='utf-8-sig', newline='') as handle:
                f[name].to_csv(handle, index=False)
    with (destination / 'artifact_hashes.json').open('x', encoding='utf-8') as handle:
        json.dump({p.name: rb.digest(p) for p in destination.iterdir()
                   if p.is_file() and p.name != 'artifact_hashes.json'}, handle, indent=2)
    return destination


def prepare():
    prepared, base, manifest = rb.prepare()
    off, off_traces = augment(prepared, manifest, None, enabled=False)
    assert off is prepared and not off_traces
    wa.compare_reference(off, base)
    bundle = load_archive()
    expanded, traces = augment(prepared, manifest, bundle, enabled=True)
    config = dict(base, protocol=protocol(), protocol_sha256=rb.digest_value(protocol()),
        archive_root=str(bundle['root'].relative_to(rb.ROOT)), archive_hashes=bundle['hashes'],
        preparation_only=True, training_requested=False,
        code_sha256={**base['code_sha256'],
            'tools/durian_model/experiment_weather_ablation.py': rb.digest(Path(wa.__file__)),
            'tools/durian_model/experiment_enso_state.py': rb.digest(Path(__file__)),
            'tools/audit_enso_outlook_archive.py': rb.digest(Path(archive.__file__))})
    return expanded, config, traces, manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        data, config, lineage, manifest = prepare()
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        print(write_preparation(data, config, lineage, manifest, run_id))
    else:
        parser.print_help()
