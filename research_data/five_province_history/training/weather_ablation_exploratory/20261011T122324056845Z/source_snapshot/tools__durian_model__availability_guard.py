"""Availability checks for experiments only; metadata checks are not evidence verification."""
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path

STATUSES = {'verified_available', 'verified_unavailable', 'unverified', 'not_applicable'}
ROLES = {'feature', 'training_label', 'selection_label', 'evaluation_target', 'issue_rule', 'calendar'}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Require an explicit timezone, not an inferred publication time')
    return parsed


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schedule_version(schedule):
    return hashlib.sha256(json.dumps(schedule, sort_keys=True).encode()).hexdigest()


def issue_date(schedule, province, year, lead):
    if schedule['kind'] != 'fixed_calendar' or lead not in (0, 60):
        raise ValueError('Only explicit fixed-calendar schedules and leads 0/60 supported')
    month, day = map(int, schedule['anchors'][province].split('-'))
    return date(year, month, day) - timedelta(days=lead)


def check(record, used_role, actual_version, cutoff, mode, observation_end=None):
    """A reference label can be late; promoting it into an input cannot bypass checks."""
    if mode not in ('exploratory', 'strict') or used_role not in ROLES:
        raise ValueError('Invalid mode or role')
    if record['role'] != used_role or record['availability_status'] not in STATUSES:
        raise ValueError('Role/status mismatch')
    if not actual_version or record['source_version'] != actual_version:
        raise ValueError('Source version mismatch: possible revised-data substitution')
    cutoff = timestamp(cutoff)
    if observation_end is not None and date.fromisoformat(observation_end) > cutoff.date():
        raise ValueError('Future observations cannot be treated as observed inputs')
    warnings = []
    state = record['availability_status']
    if state == 'not_applicable':
        if used_role != 'calendar' or record.get('basis') != 'known_by_definition':
            raise ValueError('not_applicable only allowed for deterministic calendar keys')
        return warnings
    if used_role == 'evaluation_target':
        # The caller must keep this record outside fit/predict/selection inputs.
        return ['Later evaluation reference; finality must be checked separately']
    if state != 'verified_available':
        warnings.append('availability_status=' + state)
    publication = record.get('publication_date')
    if not publication:
        warnings.append('Missing publication date for the exact source version')
    else:
        if timestamp(publication) > cutoff:
            warnings.append('Publication after use cutoff')
    evidence = record.get('evidence', {})
    if (not evidence.get('reference') or evidence.get('source_version') != actual_version
            or evidence.get('publication_date') != publication):
        warnings.append('Missing or mismatched version-specific publication evidence')
    if used_role == 'issue_rule' and timestamp(record['created_at']) > cutoff:
        warnings.append('Issue rule created after historical issue date')
    if mode == 'strict' and warnings:
        raise ValueError('; '.join(warnings))
    return warnings


def preflight(manifest, root, features, provinces, mode):
    if manifest['schema_version'] != 1:
        raise ValueError('Unsupported manifest schema')
    schedule = manifest['schedule']
    if set(schedule['anchors']) != set(provinces):
        raise ValueError('Schedule must explicitly cover every experimental province')
    if any(not anchor.endswith('-01') or not 1 <= int(anchor[:2]) <= 10
           for anchor in schedule['anchors'].values()):
        raise ValueError('Stage pipeline requires month-start anchors with three months in the same year')
    records = manifest['records']
    lineage = manifest['feature_dependencies']
    if set(lineage) != set(features) or any(not refs for refs in lineage.values()):
        raise ValueError('Every feature requires explicit dependencies')
    versions = {'issue_rule': schedule_version(schedule), 'issue_rule_feature': schedule_version(schedule),
                'calendar': 'calendar-v1'}
    for key, record in records.items():
        if 'path' in record:
            versions[key] = digest(Path(root) / record['path'])
    rows = []
    for year in range(2014, 2026):
        for lead in (60, 0):
            dates = {p: issue_date(schedule, p, year, lead) for p in provinces}
            # One shared model per year must be fit/selected before the earliest issue.
            fit_cutoff = min(dates.values()).isoformat() + 'T00:00:00+07:00'
            for p in provinces:
                issue = dates[p].isoformat() + 'T00:00:00+07:00'
                requests = [('issue_rule', 'issue_rule', fit_cutoff, 'issue_date'),
                            ('calendar', 'calendar', issue, 'calendar'),
                            ('training_labels', 'training_label', fit_cutoff, 'training_labels'),
                            ('selection_labels', 'selection_label', fit_cutoff, 'selection_labels'),
                            ('evaluation_target', 'evaluation_target', issue, 'evaluation_target')]
                requests += [(ref, 'feature', issue, feature)
                             for feature in features for ref in lineage[feature]]
                requests += [(ref, 'feature', fit_cutoff, 'training_input:' + feature)
                             for feature in features for ref in lineage[feature]]
                for ref, role, cutoff, feature in requests:
                    if ref not in records or ref not in versions:
                        raise ValueError('Missing lineage record/version: ' + ref)
                    warnings = check(records[ref], role, versions[ref], cutoff, mode)
                    rows.append(dict(province=p, target_year=year, lead_days=lead,
                        feature=feature, dependency=ref, issue_date=issue, use_cutoff=cutoff,
                        availability_status=records[ref]['availability_status'], warnings=warnings))
    return dict(mode=mode, pit_certified=False, schedule_version=versions['issue_rule'],
                fit_policy='shared model before earliest provincial issue', checks=rows,
                limitation='Manifest evidence is reviewer-supplied, not independently authenticated by this guard')


def check_feature_lineage(item, row_year, issue, use_cutoff, weather_lag):
    """Validate consumed input dates, not nominal stage dates or source-file end dates."""
    cutoff = timestamp(use_cutoff).date()
    if not math.isfinite(item['value']):
        raise ValueError('Non-finite engineered feature')
    if item['feature'] == 'previous_yield_kg_rai':
        if item['source_year'] != row_year - 1 or item['source_province'] != item['province_code']:
            raise ValueError('Lag yield must use the same province and exactly the preceding year')
        if date(item['source_year'], 12, 31) > cutoff:
            raise ValueError('Lag yield reference period exceeds use cutoff')
        return
    available = date.fromisoformat(issue) - timedelta(days=weather_lag)
    observed = [date.fromisoformat(d) for d in item['observed_dates']]
    normals = [date.fromisoformat(d) for d in item['normal_dates']]
    if any(d > min(available, cutoff) for d in observed):
        raise ValueError('Consumed weather exceeds issue/fit cutoff')
    if any(not row_year - 10 <= d.year < row_year or d > min(available, cutoff) for d in normals):
        raise ValueError('Consumed climatology exceeds historical window/cutoff')
    if bool(item['observed_cells']) != bool(observed) or bool(item['climatology_cells']) != bool(normals):
        raise ValueError('Missing consumed weather lineage')
    total = item['cohort_days'] * item['window_days']
    if item['observed_cells'] + item['climatology_cells'] != total or total <= 0:
        raise ValueError('Incomplete cohort/window lineage')
    if not math.isclose(item['observed_fraction'], item['observed_cells'] / total):
        raise ValueError('Observed coverage does not match consumed cells')
    if not math.isclose(item['climatology_fraction'], item['climatology_cells'] / total):
        raise ValueError('Climatology coverage does not match consumed cells')
    for key in ('observed_values_sha256', 'normal_values_sha256'):
        if len(item[key]) != 64:
            raise ValueError('Missing consumed-value digest')
