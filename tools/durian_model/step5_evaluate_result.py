"""5: Actual outer-year evaluation, baselines and reproduction of the prior benchmark."""
from common import *


def paired_year_bootstrap(frame, baseline_column, block_length=3, resamples=20000, seed=42):
    """Descriptive paired circular year-block bootstrap, conditional on saved predictions.

    Each year carries all provinces together. This is not a post-selection test,
    and assumes the short annual error series can be resampled as stationary.
    """
    columns = ['year_ce', 'province_code', 'actual_kg_rai', 'predicted_kg_rai', baseline_column]
    data = frame[columns].copy()
    if data.duplicated(['year_ce', 'province_code']).any():
        raise ValueError('Duplicate paired province-year keys')
    numeric = data[['year_ce', 'actual_kg_rai', 'predicted_kg_rai', baseline_column]].to_numpy(float)
    if not np.isfinite(numeric).all() or not np.equal(numeric[:, 0], np.floor(numeric[:, 0])).all():
        raise ValueError('Nonfinite paired inputs or noninteger years')
    groups = data.groupby('year_ce')
    province_sets = [frozenset(group.province_code) for _, group in groups]
    years = np.array(sorted(data.year_ce.unique()), dtype=int)
    if len(years) < 2 or np.any(np.diff(years) != 1) or any(s != province_sets[0] for s in province_sets):
        raise ValueError('Require consecutive years and identical province coverage each year')
    if not isinstance(block_length, int) or not 1 <= block_length <= len(years):
        raise ValueError('Invalid year block length')
    if not isinstance(resamples, int) or resamples < 2:
        raise ValueError('Require at least two resamples')
    data['model_absolute_error'] = abs(data.predicted_kg_rai - data.actual_kg_rai)
    data['baseline_absolute_error'] = abs(data[baseline_column] - data.actual_kg_rai)
    yearly = data.groupby('year_ce')[['model_absolute_error', 'baseline_absolute_error']].mean()
    errors = yearly.to_numpy(float)
    if np.any(errors[:, 1] <= 0):
        raise ValueError('Relative improvement requires positive baseline MAE in every year')
    # Consecutive equal-sized blocks, wrapping end to start, then truncate to n years.
    rng = np.random.default_rng(seed)
    starts = rng.integers(len(years), size=(resamples, (len(years) + block_length - 1) // block_length))
    indexes = ((starts[:, :, None] + np.arange(block_length)) % len(years)).reshape(resamples, -1)[:, :len(years)]
    sampled = errors[indexes].mean(axis=1)
    gain = sampled[:, 1] - sampled[:, 0]
    percent = 100 * (1 - sampled[:, 0] / sampled[:, 1])
    model_mae, baseline_mae = errors.mean(axis=0)
    return dict(method='paired circular year-block bootstrap', block_length_years=block_length,
                resamples=resamples, seed=seed, n_years=len(years), n_rows=len(data),
                mae_gain_kg_rai=float(baseline_mae - model_mae),
                mae_reduction_pct=float(100 * (1 - model_mae / baseline_mae)),
                gain_percentile_95_kg_rai=np.quantile(gain, [.025, .975]).tolist(),
                reduction_percentile_95_pct=np.quantile(percent, [.025, .975]).tolist(),
                worse_years=[int(y) for y, row in yearly.iterrows()
                             if row.model_absolute_error > row.baseline_absolute_error]), yearly.reset_index()


def run():
    begin_step(5)
    frame = load_csv('predictions.csv')
    result = dict(model='stage_ridge_vpd', selected_by='Lowest exploratory outer MAE among 26 previously compared families',
        overall=metrics(frame.actual_kg_rai, frame.predicted_kg_rai),
        previous_year=metrics(frame.actual_kg_rai, frame.previous_year_kg_rai),
        recent_2020_2025=metrics(frame[frame.year_ce.ge(2020)].actual_kg_rai,
                               frame[frame.year_ce.ge(2020)].predicted_kg_rai),
        warning='Family selection used previously explored test errors; not an independent confirmatory holdout',
        versions=dict(numpy=np.__version__, pandas=pd.__version__), input_sha256=hashes(),
        code_sha256={str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in [*sorted(Path(__file__).parent.glob('step*.py')), Path(__file__).parent / 'common.py',
                                  ROOT / 'tools/compare_harvest_stage_yield.py',
                                  ROOT / 'tools/analyze_harvest_backcast.py', ROOT / 'tools/train_monthly_production.py']})
    result['mae_reduction_vs_previous_year_pct'] = 100 * (
        1 - result['overall']['mae_kg_rai'] / result['previous_year']['mae_kg_rai'])
    benchmark = OUT / 'harvest_stage_rolling_combined_advanced_recent2010_predictions.csv'
    if benchmark.exists():
        old = pd.read_csv(benchmark, dtype={'province_code': str})
        old = old[old.model.eq('stage_ridge_vpd')]
        paired = frame.merge(old, on=['province_code', 'year_ce'], validate='one_to_one', suffixes=('', '_old'))
        if (len(paired) != 45 or not np.allclose(paired.predicted_kg_rai, paired.predicted_kg_rai_old,
                                               rtol=1e-10, atol=1e-7)
                or not np.allclose(paired.actual_kg_rai, paired.actual_kg_rai_old, rtol=1e-10, atol=1e-7)):
            raise ValueError('Independent rerun does not reproduce prior predictions')
        result['benchmark_reproduced'] = True
        result['comparison_models'] = load_existing_comparison()
        save_csv('comparison_models.csv', pd.DataFrame(result['comparison_models']))
        no_vpd = pd.read_csv(benchmark, dtype={'province_code': str})
        no_vpd = no_vpd[no_vpd.model.eq('stage_ridge')]
        frame = frame.merge(no_vpd[['province_code', 'year_ce', 'actual_kg_rai', 'predicted_kg_rai']],
                            on=['province_code', 'year_ce'], validate='one_to_one',
                            suffixes=('', '_without_vpd'))
        if len(frame) != 45 or not np.allclose(frame.actual_kg_rai, frame.actual_kg_rai_without_vpd):
            raise ValueError('VPD comparator does not match paired targets')
    else:
        result['benchmark_reproduced'] = None
    result['paired_uncertainty'] = {}
    paired_tables = []
    baselines = {'previous_year': 'previous_year_kg_rai'}
    if result['benchmark_reproduced']:
        baselines['stage_ridge'] = 'predicted_kg_rai_without_vpd'
    for name, column in baselines.items():
        estimates = []
        for length in (3, 2):  # Fixed primary and sensitivity lengths, not selected by interval.
            estimate, yearly = paired_year_bootstrap(frame, column, block_length=length)
            estimates.append(estimate)
        result['paired_uncertainty'][name] = estimates
        paired_tables.append(yearly.assign(comparator=name))
    result['uncertainty_warning'] = (
        'Descriptive percentile ranges conditional on fixed predictions; only nine year clusters, '
        'five fixed provinces, unverified stationarity and circular boundary. Block lengths 3 and 2 '
        'retain only short serial dependence. No model refitting or correction for 26-method selection '
        'optimism; not confirmatory confidence intervals or operational prediction intervals.')
    save_csv('paired_year_errors.csv', pd.concat(paired_tables, ignore_index=True))
    for field in ('province_code', 'year_ce'):
        records = [dict(**{field: str(key)}, **metrics(group.actual_kg_rai, group.predicted_kg_rai))
                   for key, group in frame.groupby(field)]
        save_csv('metrics_by_' + field + '.csv', pd.DataFrame(records))
    save_json('evaluation.json', result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for code, group in frame.groupby('province_code'):
        axes[0].scatter(group.actual_kg_rai, group.predicted_kg_rai, label=code, alpha=.8)
    lo, hi = float(frame.actual_kg_rai.min()), float(frame.actual_kg_rai.max())
    axes[0].plot([lo, hi], [lo, hi], '--', color='#64748b')
    axes[0].set(xlabel='Actual kg/rai', ylabel='Predicted kg/rai', title='45 rolling-origin test predictions')
    axes[0].legend(title='Province code', fontsize=8)
    yearly = frame.groupby('year_ce').apply(lambda g: pd.Series({
        'Ridge + VPD': mae(g.actual_kg_rai, g.predicted_kg_rai),
        'Previous year': mae(g.actual_kg_rai, g.previous_year_kg_rai)}))
    yearly.plot.bar(ax=axes[1], color=['#2563eb', '#94a3b8'])
    axes[1].set(xlabel='Outer test year', ylabel='MAE kg/rai', title='Year-by-year error; not uniformly better')
    fig.tight_layout()
    fig.savefig(OUT / 'ridge_vpd_evaluation.png', dpi=180)
    plt.close(fig)
    finish_step(5)
    print('Step 5:', json.dumps(result['overall']), 'benchmark reproduced:', result['benchmark_reproduced'])
    return result


def load_existing_comparison():
    path = OUT / 'harvest_stage_rolling_combined_advanced_recent2010_results.json'
    if not path.exists():
        return []
    original = json.loads(path.read_text(encoding='utf-8'))
    if any(not (DATA / name).exists() or hashlib.sha256((DATA / name).read_bytes()).hexdigest() != digest
           for name, digest in original['input_sha256'].items()):
        raise ValueError('Comparison results belong to a different input snapshot')
    return sorted(original['models'], key=lambda record: record['mae_kg_rai'])


if __name__ == '__main__':
    run()
