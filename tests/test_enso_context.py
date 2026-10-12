"""ENSO parsing, probability chronology and no forward-looking persistence."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from fetch_enso_context import SEASONS, annual_context, parse_forecast, parse_observed, season_dates


def forecast_html(issue='October 2026', first=9, values=(10, 20, 70)):
    rows = ['<tr><th>Season</th><th>La Ni&ntilde;a</th><th>Neutral</th><th>El Ni&ntilde;o</th></tr>']
    for i in range(9):
        season = SEASONS[(first + i) % 12]
        rows.append(f'<tr><th>{season} <span>months</span></th>'
                    + ''.join(f'<td>{v}</td>' for v in values) + '</tr>')
    return f'<h2>Issued {issue}</h2>Relative Oceanic <table id="probabilities-table">' + ''.join(rows) + '</table>'


class EnsoContextTests(unittest.TestCase):
    def test_observed_year_boundaries(self):
        self.assertEqual(season_dates(2025, 1), ('2024-12-01', '2025-02-28'))
        self.assertEqual(season_dates(2025, 12), ('2025-11-01', '2026-01-31'))

    def test_persistence_never_relabels_initial_seasons_with_future(self):
        text = 'SEAS YR ANOM\n' + '\n'.join(f'{s} 2025 0.6' for s in SEASONS[:5])
        full = parse_observed(text, 'RONI')
        prefix = parse_observed('\n'.join(text.splitlines()[:4]), 'RONI')
        self.assertEqual(full[:3], prefix)
        self.assertEqual(full[3]['persistent_index_phase_to_date'], 'not_yet_persistent')
        self.assertEqual(full[4]['persistent_index_phase_to_date'], 'el_nino')
        self.assertFalse(full[4]['point_in_time_vintage_verified'])

    def test_zero_and_cold_threshold(self):
        rows = parse_observed('SEAS YR TOTAL ANOM\nDJF 2025 26 0\nJFM 2025 25 -0.5', 'ONI')
        self.assertEqual([r['threshold_regime_proxy'] for r in rows], ['neutral', 'cold'])
        summary = annual_context(rows)[0]
        self.assertFalse(summary['complete_year'])
        self.assertEqual(summary['threshold_regimes_present'], ['cold', 'neutral'])

    def test_corrupt_or_missing_observations_rejected(self):
        for text in ['BAD HEADER', 'SEAS YR ANOM\nDJF 2025 -999',
                     'SEAS YR ANOM\nDJF 2025 nan',
                     'SEAS YR ANOM\nDJF 2025 0\nFMA 2025 0',
                     'SEAS YR ANOM\nDJF 2025 0\nDJF 2025 0']:
            with self.assertRaises(ValueError):
                parse_observed(text, 'RONI')

    def test_forecast_rollover_and_probabilities_not_actual(self):
        rows = parse_forecast(forecast_html())
        self.assertEqual((rows[2]['year_ce'], rows[2]['season']), (2026, 'NDJ'))
        self.assertEqual((rows[3]['year_ce'], rows[3]['season']), (2027, 'DJF'))
        self.assertEqual(rows[3]['period_start'], '2026-12-01')
        self.assertEqual(rows[0]['most_likely_phase'], 'el_nino')
        self.assertEqual(rows[0]['kind'], 'forecast_probability_not_observed_status')
        self.assertIsNone(rows[0]['issued_day'])

    def test_forecast_ties_and_invalid_probability_tables(self):
        self.assertEqual(parse_forecast(forecast_html(values=(50, 0, 50)))[0]['most_likely_phase'], 'tie')
        for html in [forecast_html(values=(10, 20, 80)), forecast_html(values=(-1, 1, 100)),
                     forecast_html().replace('Issued October', 'No issue October'),
                     forecast_html().replace('probabilities-table', 'wrong-table'),
                     forecast_html(first=2)]:
            with self.assertRaises(ValueError):
                parse_forecast(html)


if __name__ == '__main__':
    unittest.main()
