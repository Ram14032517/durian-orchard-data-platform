"""Shared paths and strict model I/O for the seven teaching steps."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from compare_harvest_stage_yield import (AGES, ALPHAS, TARGET, STAGE_FEATURES,
    VPD_STAGE_FEATURES, design, training_seasons, stage_rows, vpd_rows, vpd_series)
from analyze_harvest_backcast import read_csv, weather_series
from train_monthly_production import fit_ridge, predict, mae

DATA = ROOT / 'research_data/five_province_history'
OUT = DATA / 'training'
PROVINCES = ['22', '33', '53', '84', '86']
FEATURES = ['previous_yield_kg_rai', *STAGE_FEATURES, *VPD_STAGE_FEATURES]
INPUTS = ['production_annual.csv', 'harvest_monthly.csv', 'weather_daily.csv']
PREFIX = 'ridge_vpd_'


def save_json(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (PREFIX + name)).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def load_json(name):
    return json.loads((OUT / (PREFIX + name)).read_text(encoding='utf-8'))


def save_csv(name, frame):
    frame.to_csv(OUT / (PREFIX + name), index=False, encoding='utf-8-sig')


def load_csv(name):
    return pd.read_csv(OUT / (PREFIX + name), dtype={'province_code': str})


def hashes():
    """Hash actual bytes for provenance; never silently normalize saved hashes."""
    return {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest() for name in INPUTS}


def _uniform_newline_variant(raw):
    """Return the other UTF-8 LF/CRLF representation, not a content cleanup."""
    try:
        raw.decode('utf-8')  # Validate only; preserve BOM and every other byte.
    except UnicodeDecodeError:
        return None
    without_crlf = raw.replace(b'\r\n', b'')
    if b'\r' in without_crlf:
        return None
    if b'\r\n' in raw:
        if b'\n' in without_crlf:  # Mixed line endings are not a checkout conversion.
            return None
        return raw.replace(b'\r\n', b'\n'), 'CRLF', 'LF'
    if b'\n' in raw:
        return raw.replace(b'\n', b'\r\n'), 'LF', 'CRLF'
    return None


def _verify_utf8_bytes(raw, expected):
    """Comparison mechanism; callers must restrict which legacy files qualify."""
    message = 'Inputs changed. Rerun steps 0-6; do not mix snapshots.'
    if (not isinstance(expected, str) or len(expected) != 64
            or any(char not in '0123456789abcdef' for char in expected)):
        raise ValueError(message)
    actual = hashlib.sha256(raw).hexdigest()
    evidence = dict(actual_sha256=actual, expected_sha256=expected, comparison='exact_bytes')
    if actual != expected:
        variant = _uniform_newline_variant(raw)
        if variant is None or hashlib.sha256(variant[0]).hexdigest() != expected:
            raise ValueError(message)
        evidence.update(comparison='uniform_lf_crlf_only', actual_line_endings=variant[1],
                        matched_line_endings=variant[2])
    return evidence


def verify_input_file(name, expected, data_dir=None):
    """Verify one explicitly named model CSV, including a legacy newline proof."""
    if name not in INPUTS:
        raise ValueError('Unknown model snapshot input')
    return _verify_utf8_bytes(((DATA if data_dir is None else Path(data_dir)) / name).read_bytes(), expected)


def verify_production_snapshot(expected, folder=None):
    """The saved main model alone may prove its legacy LF/CRLF representation."""
    return _verify_utf8_bytes(((OUT if folder is None else Path(folder)) / 'ridge_vpd_final_model.json').read_bytes(), expected)


def verify_input_snapshot(expected):
    """Verify only the three model CSV inputs against trusted saved digests.

    Exact bytes are preferred. A uniform LF/CRLF conversion is accepted only
    when its SHA256 exactly reproduces the saved digest. No data, audit or
    model is rewritten. Return comparison evidence instead of concealing the
    difference in hashes(); all other content changes still fail closed.
    """
    message = 'Inputs changed. Rerun steps 0-6; do not mix snapshots.'
    if not isinstance(expected, dict) or set(expected) != set(INPUTS):
        raise ValueError(message)
    files = {name: verify_input_file(name, expected[name]) for name in INPUTS}
    return dict(policy='model_csv_exact_or_uniform_utf8_lf_crlf_v1', files=files)


def check_snapshot():
    return verify_input_snapshot(load_json('audit.json')['input_sha256'])


def safe_temporary_root(path):
    """Allow macOS's system /var alias, not user-created symlink escapes."""
    lexical = Path(path).absolute()
    resolved = lexical.resolve()
    temporary = Path(tempfile.gettempdir()).absolute()
    canonical = temporary.resolve()
    if lexical == resolved:
        return resolved.is_relative_to(canonical)
    return (lexical.is_relative_to(temporary)
            and resolved == canonical / lexical.relative_to(temporary))


def begin_step(number):
    check_snapshot()
    completed = load_json('workflow_state.json')['completed_steps']
    if number - 1 not in completed:
        raise ValueError(f'Run step {number - 1} first; old downstream files are not valid.')
    # A rerun invalidates this step and downstream results, even if it later fails.
    save_json('workflow_state.json', {'completed_steps': [n for n in completed if n < number]})


def finish_step(number):
    completed = load_json('workflow_state.json')['completed_steps']
    save_json('workflow_state.json', {'completed_steps': sorted(set([*completed, number]))})


def load_panel():
    annual = pd.read_csv(DATA / INPUTS[0], dtype={'province_code': str})
    keys = ['province_code', 'year_ce']
    if annual.duplicated(keys).any() or set(annual.province_code) != set(PROVINCES):
        raise ValueError('Invalid province-year keys')
    numeric = annual[['year_ce', 'production_tonnes', 'bearing_rai', TARGET]].to_numpy(float)
    if (not np.isfinite(numeric).all() or (annual.bearing_rai <= 0).any()
            or (annual.production_tonnes < 0).any()
            or not np.allclose(annual.production_tonnes * 1000 / annual.bearing_rai, annual[TARGET])):
        raise ValueError('Target must be real production tonnes * 1000 / bearing rai')
    lag = annual[keys + [TARGET]].rename(columns={TARGET: 'previous_yield_kg_rai'})
    lag['year_ce'] += 1
    panel = annual[annual.year_ce.between(2010, 2025)].merge(lag, on=keys, validate='one_to_one')
    if len(panel) != 80 or panel.groupby('year_ce').size().ne(5).any():
        raise ValueError('Expected 80 complete province-years, 2010-2025')
    return panel


def feature_names():
    return [f'province_{p}' for p in PROVINCES] + ['year_ce', *FEATURES]


def fit_bundle(train, age, alpha, seasons):
    x = design(train, PROVINCES, FEATURES)
    y = train[TARGET].to_numpy(float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Missing input; no zero imputation')
    model = fit_ridge(x, y, float(alpha))
    return dict(schema_version=1, model='stage_ridge_vpd', parameters=model,
        feature_names=feature_names(), features=FEATURES, provinces=PROVINCES,
        age_days=int(age), season_months=seasons, train_start=2010,
        train_end=int(train.year_ce.max()), training_rows=len(train),
        input_sha256=hashes(), mode='conditional on complete observed/scenario stage weather')


def infer(bundle, frame):
    """No target/production columns accepted; input stages must match bundle metadata."""
    required = {'province_code', 'year_ce', *FEATURES}
    if not required.issubset(frame.columns) or frame.empty:
        raise ValueError('Missing required predictors or empty input')
    if set(frame.columns) - required - {'bearing_rai'}:
        raise ValueError('Unexpected columns; do not include targets, production or metadata')
    if (bundle['features'] != FEATURES or bundle['feature_names'] != feature_names()
            or bundle['provinces'] != PROVINCES):
        raise ValueError('Model schema/order mismatch')
    if not frame.province_code.isin(PROVINCES).all():
        raise ValueError('Unknown province; this model supports five provinces only')
    if frame.duplicated(['province_code', 'year_ce']).any():
        raise ValueError('Duplicate prediction keys')
    x = design(frame, PROVINCES, FEATURES)
    if not np.isfinite(x).all() or (frame.year_ce <= bundle['train_end']).any():
        raise ValueError('Invalid predictors or prediction year not after training')
    if not np.equal(frame.year_ce, np.floor(frame.year_ce)).all():
        raise ValueError('Year must be an integer')
    nonnegative = [f for f in FEATURES if f != 'fruit_90_to_harvest_temperature_c']
    if (frame[nonnegative] < 0).any().any():
        raise ValueError('Rain, solar, VPD and prior yield must be nonnegative')
    if not frame.fruit_90_to_harvest_temperature_c.between(-100, 70).all():
        raise ValueError('Invalid temperature')
    params = bundle['parameters']
    arrays = [np.asarray(params[k], dtype=float) for k in ('mean', 'scale', 'coef')]
    if any(a.shape != (len(feature_names()),) or not np.isfinite(a).all() for a in arrays):
        raise ValueError('Invalid model parameters')
    if (arrays[1] <= 0).any() or not np.isfinite(params['intercept']):
        raise ValueError('Invalid model scale/intercept')
    result = frame[['province_code', 'year_ce']].copy()
    result['predicted_kg_rai'] = predict(params, x)
    if 'bearing_rai' in frame:
        if not np.isfinite(frame.bearing_rai).all() or (frame.bearing_rai <= 0).any():
            raise ValueError('Bearing area must be finite and positive')
        result['predicted_tonnes_conditional'] = result.predicted_kg_rai * frame.bearing_rai / 1000
    return result


def metrics(actual, estimated):
    error = np.asarray(estimated) - np.asarray(actual)
    return dict(n=len(error), mae_kg_rai=float(np.abs(error).mean()),
                rmse_kg_rai=float(np.sqrt(np.mean(error ** 2))), bias_kg_rai=float(error.mean()))
