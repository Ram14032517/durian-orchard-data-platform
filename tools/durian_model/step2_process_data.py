"""2: Train-only season selection, stage weather and daily VPD proxy."""
from common import *


def run():
    begin_step(2)
    base = load_csv('panel.csv')
    harvest = pd.read_csv(DATA / 'harvest_monthly.csv', dtype={'province_code': str})
    if (harvest.duplicated(['province_code', 'year_ce', 'month_number']).any()
            or not harvest.month_number.between(1, 12).all()
            or not np.isfinite(harvest.tonnes).all() or (harvest.tonnes < 0).any()):
        raise ValueError('Invalid monthly harvest records')
    harvest = harvest[harvest.year_ce.ge(2010)]
    raw = read_csv(DATA / 'weather_daily.csv')
    weather, vpd = weather_series(raw), vpd_series(raw)
    cache, frames, metadata = {}, [], {}
    for cutoff in range(2013, 2026):
        seasons = training_seasons(harvest, cutoff)
        signature = tuple((code, tuple(months)) for code, months in seasons.items())
        if signature not in cache:
            stage = stage_rows(base, seasons, weather)
            cache[signature] = pd.concat([
                base.merge(stage[stage.age_days.eq(age)], on=['province_code', 'year_ce'],
                           validate='one_to_one').merge(vpd_rows(base, vpd, seasons, age),
                           on=['province_code', 'year_ce'], validate='one_to_one')
                for age in AGES], ignore_index=True)
        selected = cache[signature][['province_code', 'province_name', 'year_ce', TARGET,
                                    'age_days', *FEATURES]].copy()
        selected['season_fit_through'] = cutoff
        if not np.isfinite(selected[[TARGET, *FEATURES]].to_numpy(float)).all():
            raise ValueError('Incomplete weather windows; no zero filling')
        frames.append(selected)
        metadata[str(cutoff)] = seasons
    result = pd.concat(frames, ignore_index=True)
    save_csv('features.csv', result)
    save_json('seasons.json', metadata)
    finish_step(2)
    print('Step 2:', len(result), 'feature rows; only 80 independent annual targets.')
    return {'feature_rows': len(result), 'independent_targets': len(base), 'features': FEATURES}


if __name__ == '__main__':
    run()
