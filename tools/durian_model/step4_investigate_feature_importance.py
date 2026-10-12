"""4: Standardized Ridge coefficients, not causal importance or tree importance."""
from common import *


def run():
    begin_step(4)
    bundle = load_json('final_model.json')
    table = pd.DataFrame(dict(feature=bundle['feature_names'],
                             coefficient_kg_rai_per_training_sd=bundle['parameters']['coef']))
    table['absolute_coefficient'] = table.coefficient_kg_rai_per_training_sd.abs()
    table = table.sort_values('absolute_coefficient', ascending=False)
    save_csv('coefficients.csv', table)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 6))
    ordered = table.sort_values('absolute_coefficient')
    ax.barh(ordered.feature, ordered.coefficient_kg_rai_per_training_sd,
            color=['#2563eb' if v >= 0 else '#c2410c' for v in ordered.coefficient_kg_rai_per_training_sd])
    ax.axvline(0, color='#64748b', linewidth=1)
    ax.set(xlabel='Signed coefficient: kg/rai per training SD',
           title='Final Ridge coefficients - association, not agronomic causation')
    fig.tight_layout()
    fig.savefig(OUT / 'ridge_vpd_coefficients.png', dpi=180)
    plt.close(fig)
    finish_step(4)
    print('Step 4: saved standardized coefficients; correlated inputs can share effects.')
    return table


if __name__ == '__main__':
    run()
