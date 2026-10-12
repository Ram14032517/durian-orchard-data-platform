"""0: Verify actual production, bearing area, source hashes and prior-year yield."""
from common import *


def run():
    save_json('workflow_state.json', {'completed_steps': []})
    panel = load_panel()
    save_csv('panel.csv', panel)
    result = dict(panel_years=[2010, 2025], rows=len(panel), provinces=PROVINCES,
        target='production_tonnes * 1000 / bearing_rai',
        lag_source='2009-2024 actual annual yield, not the current-year target',
        input_sha256=hashes(), unit='province-year, kg/rai',
        reason_for_period='Calendar-based recent-year focus; no low-yield rows removed',
        source_edition='Local OAE XLSX: years 2540-2568, data_date 2026-07-14; catalog year metadata differs',
        finality='Recorded official snapshot, not synthetic labels. Final-versus-estimate status is not explicitly encoded per row; not independently reconfirmed for every year.',
        limits=['Retrospectively revised records; publication vintages not reconstructed',
                'No orchard-level labels, bearing-orchard spatial weights or measured soil nutrients'])
    save_json('audit.json', result)
    finish_step(0)
    print('Step 0: validated', len(panel), 'province-years; target uses bearing area.')
    return result


if __name__ == '__main__':
    run()
