"""Read-only source/model audit. Never trains or replaces production artifacts."""
from common import *
from experiment_issue_date import score

SOURCE = ROOT / 'research_data/external/oae_2026-09-17'


def eligible_as_of(published_at, issue_date):
    """Unknown publication dates fail closed; observation year is not release date."""
    published = pd.to_datetime(published_at, errors='coerce', utc=True)
    issue = pd.to_datetime(issue_date, errors='coerce', utc=True)
    return bool(pd.notna(published) and pd.notna(issue) and published <= issue)


def valid_target(frame):
    return (np.isfinite(frame[['production_tonnes', 'bearing_rai']]).all(axis=1)
            & frame.bearing_rai.gt(0) & frame.production_tonnes.ge(0))


def paired(frame):
    frame = frame.copy()
    if frame.duplicated(['province_code', 'year_ce']).any():
        raise ValueError('Duplicate paired keys')
    if not np.isfinite(frame[['actual_kg_rai', 'predicted_kg_rai', 'previous_year_kg_rai']]).all().all():
        raise ValueError('Nonfinite paired errors')
    frame['model_ae'] = abs(frame.predicted_kg_rai - frame.actual_kg_rai)
    frame['baseline_ae'] = abs(frame.previous_year_kg_rai - frame.actual_kg_rai)
    frame['gain_kg_rai'] = frame.baseline_ae - frame.model_ae
    frame['win'] = frame.gain_kg_rai > 0
    return frame


def run():
    check_snapshot()
    plan = json.loads((OUT / 'issue_date_plan.json').read_text(encoding='utf-8'))
    if plan['input_sha256'] != hashes():
        raise ValueError('Issue-date predictions are from another input snapshot')
    annual = pd.read_csv(ROOT / 'research_data/thailand_comparison/production_province_year.csv',
                         dtype={'province_code': str})
    raw = pd.read_excel(SOURCE / 'durian_province.xlsx', sheet_name='durian')
    monthly = pd.read_excel(SOURCE / 'durian_monthly_province.xlsx', sheet_name='durian_monthly')
    if annual.duplicated(['province_code', 'year_ce']).any():
        raise ValueError('Duplicate annual keys')
    if raw.duplicated(['province_name', 'year', 'item']).any():
        raise ValueError('Duplicate source measure keys')
    measures = {'เนื้อที่ยืนต้น': 'planted_rai', 'เนื้อที่ให้ผล': 'bearing_rai',
                'ผลผลิต': 'production_tonnes', 'ผลผลิตต่อเนื้อที่ให้ผล': 'yield_kg_per_rai_source'}
    source_wide = raw.pivot(index=['province_name', 'year'], columns='item', values='data').rename(columns=measures).reset_index()
    source_wide['year_ce'] = pd.to_numeric(source_wide.year) - 543
    matched = annual.merge(source_wide, on=['province_name', 'year_ce'], validate='one_to_one', suffixes=('', '_raw'))
    if len(matched) != len(annual) or any(not np.allclose(matched[c], matched[c+'_raw'], equal_nan=True)
                                           for c in measures.values()):
        raise ValueError('Prepared annual table differs from preserved OAE workbook')
    monthly['year_ce'] = pd.to_numeric(monthly.year) - 543
    monthly = monthly[monthly.item.eq('ปริมาณผลผลิตรายเดือน')].copy()
    if monthly.duplicated(['province_name', 'year_ce', 'month']).any():
        raise ValueError('Duplicate monthly keys')
    records = []
    for code, group in annual.groupby('province_code'):
        name = group.province_name.iloc[0]
        valid = group[valid_target(group)]
        years = set(valid.year_ce.astype(int))
        m = monthly[monthly.province_name.eq(name)]
        annual_for_month = group.set_index('year_ce').production_tonnes
        sums = m.groupby('year_ce').data.sum(min_count=1)
        reconciled = sums.index[(sums - annual_for_month.reindex(sums.index)).abs()
                                <= np.maximum(1., annual_for_month.reindex(sums.index) * .005)]
        records.append(dict(province_code=code, province_name=name,
            region=group.region.iloc[0], first_year=int(group.year_ce.min()),
            last_year=int(group.year_ce.max()), annual_rows=len(group), valid_targets=len(valid),
            invalid_targets=len(group)-len(valid),
            missing_1997_2025=','.join(map(str, sorted(set(range(1997, 2026))-years))),
            valid_2010_2016=sum(y in years for y in range(2010, 2017)),
            valid_test_2017_2025=sum(y in years for y in range(2017, 2026)),
            monthly_years_2004_2016=m[m.year_ce.between(2004, 2016)].year_ce.nunique(),
            reconciled_monthly_years_2004_2016=sum(2004 <= y <= 2016 for y in reconciled),
            pre2017_peak_month=m[m.year_ce.lt(2017)].groupby('month').data.sum().idxmax()
                if not m[m.year_ce.lt(2017)].empty else None,
            source_release_verified=False,
            weather_cached=code in PROVINCES,
            original=code in PROVINCES))
    coverage = pd.DataFrame(records)
    coverage.to_csv(OUT / 'expansion_coverage.csv', index=False, encoding='utf-8-sig')
    saved = pd.read_csv(OUT / 'issue_date_predictions.csv', dtype={'province_code': str})
    cat = paired(saved[saved.lead_days.eq(60) & saved.policy.eq('stage_catboost')])
    if len(cat) != 45 or set(cat.year_ce) != set(range(2017, 2026)):
        raise ValueError('Expected original 45 evaluation keys')
    cat.to_csv(OUT / 'expansion_paired_errors.csv', index=False, encoding='utf-8-sig')
    summaries = {}
    for key in ('province_code', 'year_ce'):
        summary = cat.groupby(key).agg(n=('win', 'size'), model_mae=('model_ae', 'mean'),
            baseline_mae=('baseline_ae', 'mean'), bias=('predicted_kg_rai', lambda _: 0),
            mean_gain=('gain_kg_rai', 'mean'), median_gain=('gain_kg_rai', 'median'),
            wins=('win', 'sum'))
        summary['bias'] = cat.assign(error=cat.predicted_kg_rai-cat.actual_kg_rai).groupby(key).error.mean()
        summary.to_csv(OUT / f'expansion_errors_by_{key}.csv', encoding='utf-8-sig')
        summaries[key] = summary.reset_index().to_dict('records')
    tuning = pd.read_csv(OUT / 'issue_date_tuning.csv')
    choices = pd.read_csv(OUT / 'issue_date_choices.csv')
    auto = choices[choices.lead_days.eq(60) & choices.policy.eq('inner_selected')].sort_values('year_ce')
    margins = []
    for year, group in tuning[tuning.lead_days.eq(60)].groupby('test_year'):
        best = group.sort_values('inner_mae_kg_rai').head(2)
        margins.append(dict(year_ce=int(year), gap=float(best.inner_mae_kg_rai.iloc[1]-best.inner_mae_kg_rai.iloc[0])))
    context = pd.read_csv(OUT / 'issue_date_weather_context.csv')
    if (pd.to_datetime(context.weather_available_through) > pd.to_datetime(context.issue_date)).any():
        raise ValueError('Weather cutoff exceeds issue date')
    if (context.normal_end_year >= context.year_ce).any():
        raise ValueError('Normal includes target or future year')
    if not np.allclose(context.observed_fraction + context.climatology_fraction, 1):
        raise ValueError('Weather coverage fractions do not reconcile')
    result = dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(), input_sha256=hashes(),
        annual_source_sha256=hashlib.sha256((SOURCE/'durian_province.xlsx').read_bytes()).hexdigest(),
        monthly_source_sha256=hashlib.sha256((SOURCE/'durian_monthly_province.xlsx').read_bytes()).hexdigest(),
        annual_data_dates=[str(x) for x in raw.data_date.unique()],
        monthly_data_dates=[str(x) for x in monthly.data_date.unique()],
        catboost=score(cat.actual_kg_rai, cat.predicted_kg_rai),
        paired_mean_gain=float(cat.gain_kg_rai.mean()), paired_median_gain=float(cat.gain_kg_rai.median()),
        wins=int(cat.win.sum()), ties=int(cat.gain_kg_rai.eq(0).sum()),
        grouped=summaries, selection_margins=margins,
        candidate_switches=int(auto.candidate.ne(auto.candidate.shift()).sum()-1),
        weather_context_rows_checked=len(context),
        normal_cutoff_check=True, weather_cutoff_check=True,
        strict_forecast_eligible=False,
        reason='Historical annual/monthly publication vintages and weather release availability unverified',
        production_changed=False)
    (OUT/'expansion_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('grouped','input_sha256')}, ensure_ascii=False, indent=2))
    print(coverage[coverage.province_name.isin(['ระยอง','ตราด','นครศรีธรรมราช','ระนอง','ประจวบคีรีขันธ์','นครราชสีมา','พิษณุโลก'])].to_string(index=False))


if __name__ == '__main__':
    run()
