"""3: Tune age/alpha only on earlier years; refit and save portable JSON models."""
from common import *


def run():
    begin_step(3)
    frames, seasons = load_csv('features.csv'), load_json('seasons.json')
    cache, tuning, bundles, rows = {}, [], {}, []

    def frame_for(cutoff, age):
        return frames[frames.season_fit_through.eq(cutoff) & frames.age_days.eq(age)]

    for test_year in range(2017, 2027):
        scores = []
        for age in AGES:
            for alpha in ALPHAS:
                inner = []
                for year in range(test_year - 3, test_year):
                    key = (year, age, alpha)
                    if key not in cache:
                        frame = frame_for(year - 1, age)
                        train, valid = frame[frame.year_ce.lt(year)], frame[frame.year_ce.eq(year)]
                        bundle = fit_bundle(train, age, alpha, seasons[str(year - 1)])
                        estimates = infer(bundle, valid[['province_code', 'year_ce', *FEATURES]])
                        cache[key] = mae(valid[TARGET], estimates.predicted_kg_rai)
                    inner.append(cache[key])
                score = float(np.mean(inner))
                scores.append((score, age, alpha))
                tuning.append(dict(test_year=test_year, age_days=age, alpha=alpha,
                                   inner_mae_kg_rai=score))
        score, age, alpha = min(scores, key=lambda record: record[0])
        frame = frame_for(test_year - 1, age)
        train = frame[frame.year_ce.lt(test_year)]
        bundle = fit_bundle(train, age, alpha, seasons[str(test_year - 1)])
        bundle['inner_mae_kg_rai'] = score
        bundles[str(test_year)] = bundle
        if test_year <= 2025:
            test = frame[frame.year_ce.eq(test_year)]
            estimates = infer(bundle, test[['province_code', 'year_ce', *FEATURES]])
            for actual, estimate in zip(test.itertuples(), estimates.itertuples()):
                rows.append(dict(province_code=actual.province_code, province_name=actual.province_name,
                    year_ce=test_year, actual_kg_rai=getattr(actual, TARGET),
                    predicted_kg_rai=estimate.predicted_kg_rai,
                    previous_year_kg_rai=actual.previous_yield_kg_rai,
                    age_days=age, alpha=alpha))
        print(f'Step 3: train through {test_year-1}, age={age}, alpha={alpha}', flush=True)
    predictions = pd.DataFrame(rows)
    assert len(predictions) == 45 and not predictions.duplicated(['province_code', 'year_ce']).any()
    save_csv('predictions.csv', predictions)
    save_csv('tuning.csv', pd.DataFrame(tuning))
    save_json('models.json', bundles)
    save_json('final_model.json', bundles['2026'])
    finish_step(3)
    return {'folds': 9, 'test_rows': 45, 'final_train_end': 2025,
            'final_age': bundles['2026']['age_days'], 'final_alpha': bundles['2026']['parameters']['alpha']}


if __name__ == '__main__':
    run()
