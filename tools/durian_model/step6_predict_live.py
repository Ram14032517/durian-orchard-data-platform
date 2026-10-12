"""6: Safe conditional prediction; default is a rolling-origin 2025 retrospective demo."""
import argparse
from common import *


def run(input_path=None, output_path=None):
    check_snapshot()
    if input_path:
        bundle = load_json('final_model.json')
        if load_json('workflow_state.json')['completed_steps'] != list(range(7)):
            raise ValueError('Run all steps 0-6 before predicting new inputs')
        if bundle['input_sha256'] != hashes():
            raise ValueError('Saved model belongs to another input snapshot')
        inputs = pd.read_csv(input_path, dtype={'province_code': str})
        estimates = infer(bundle, inputs)
        if not output_path:
            raise ValueError('Supply --output for custom inputs')
        output = Path(output_path).resolve()
        if output == Path(input_path).resolve() or output in [(DATA / n).resolve() for n in INPUTS]:
            raise ValueError('Do not overwrite prediction inputs or source files')
        if output.exists():
            raise FileExistsError('Output exists; choose a new filename')
        estimates.to_csv(output, index=False, encoding='utf-8-sig')
    else:
        begin_step(6)
        bundle = load_json('models.json')['2025']
        frames = load_csv('features.csv')
        demo = frames[frames.year_ce.eq(2025) & frames.season_fit_through.eq(2024)
                      & frames.age_days.eq(bundle['age_days'])]
        inputs = demo[['province_code', 'year_ce', *FEATURES]]
        estimates = infer(bundle, inputs)
        save_csv('demo_2025_inputs.csv', inputs)
        save_csv('demo_2025_predictions.csv', estimates)
        save_csv('future_input_template.csv', pd.DataFrame(columns=['province_code', 'year_ce', *FEATURES, 'bearing_rai']))
        save_json('prediction_contract.json', dict(
            demo='2025 rolling-origin test data; model trained through 2024; observed weather, not a live forecast',
            future_model_train_end=2025, age_days=load_json('final_model.json')['age_days'],
            seasons=load_json('final_model.json')['season_months'], predictors=FEATURES,
            warning='Populate every window using the saved age and season; use issue-date forecasts/scenarios for unavailable days. Never label scenarios as observations.',
            area='Optional bearing_rai converts kg/rai to conditional tonnes; excludes newly planted nonbearing area'))
        finish_step(6)
    print('Step 6: conditional predictions, not validated live forecasts.\n', estimates.to_string(index=False))
    return estimates


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    run(args.input, args.output)
