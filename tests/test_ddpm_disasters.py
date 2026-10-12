"""DDPM source preservation, sparse coverage, and conflicting-village checks."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from prepare_ddpm_disasters import parse_resource, summarize, news_records, stage_overlap, drought_date, drought_records


def sample(year_value='', district='2201'):
    headers = ['PROVINCE_CODE', 'PROVINCE_NAME', 'AMPHUR_CODE', 'MOO_ID',
               *[f'Y{y}' for y in range(2562, 2568)]]
    values = ['22', 'จันทบุรี', district, '22010101', year_value, '', '', '', '', '']
    text = ','.join(headers) + '\n' + ','.join(values) + '\n'
    return parse_resource(text.encode('utf-8-sig'), 'dpm-gd015', 'flood', 'fixture')


class DisastersTests(unittest.TestCase):
    def test_drought_dates_keep_buddhist_and_calendar_years_distinct(self):
        for value, expected in [('8-ม.ค.-62', '2019-01-08'), ('23/03/2020', '2020-03-23'),
                                ('2 กรกฎาคม 2564', '2021-07-02'), ('12/12/2023', '2023-12-12')]:
            self.assertEqual(drought_date(value), expected)
        self.assertEqual(drought_date(' '), '')
        with self.assertRaises(ValueError):
            drought_date('not a date')

    def test_drought_admin_end_does_not_become_exposure_end_and_rai_not_acres(self):
        table = [['Province', 'Disaster Date', 'Situation Ended', 'Agriculture (Acres)'],
                 ['ชุมพร', '12/12/2023', '01/01/2024', 0]]
        row = drought_records(table, 2567, dict(id='fixture', url='fixture'))[0]
        self.assertEqual(row['incident_date'], '2023-12-12')
        self.assertEqual(row['source_year_be'], 2567)
        self.assertEqual(row['administrative_closure_date'], '2024-01-01')
        self.assertEqual(row['situation_end_date'], '')
        self.assertEqual(row['agriculture_damage_rai_raw'], '0')

    def test_drought_aggregate_not_mislabeled_as_district_event(self):
        table = [['Province', 'Time', 'District', 'Agriculture (Acres)'], ['สุราษฎร์ธานี', 2, 3, ' ']]
        row = drought_records(table, 2568, dict(id='fixture', url='fixture'))[0]
        self.assertEqual(row['report_level'], 'province_annual_aggregate')
        self.assertEqual(row['province_incidents_raw'], '2')
        self.assertEqual(row['district'], '')
        self.assertEqual(row['agriculture_damage_rai_raw'], '')
        self.assertEqual(row['incident_date'], '')
        table[1][1] = 0
        self.assertEqual(drought_records(table, 2568, dict(id='fixture', url='fixture'))[0]['province_incidents_raw'], '0')

    def test_blank_is_not_zero(self):
        rows = sample()
        result = summarize(rows)[0]
        self.assertEqual(result['reported_village_event_sum'], '')
        self.assertEqual(result['blank_village_rows'], 1)
        self.assertEqual(result['explicit_zero_village_rows'], 0)

    def test_explicit_zero_is_preserved(self):
        result = summarize(sample('0'))[0]
        self.assertEqual(result['reported_village_event_sum'], 0)
        self.assertEqual(result['nonblank_village_rows'], 1)
        self.assertEqual(result['explicit_zero_village_rows'], 1)

    def test_counts_are_not_collapsed_to_binary(self):
        result = summarize(sample('3'))[0]
        self.assertEqual(result['reported_village_event_sum'], 3)
        self.assertEqual(result['positive_village_rows'], 1)

    def test_conflicting_village_districts_are_quarantined(self):
        rows = sample('1', '2201') + sample('1', '2209')
        result = summarize(rows)[0]
        self.assertEqual(result['quarantined_rows'], 2)
        self.assertEqual(result['reported_village_event_sum'], '')
        self.assertTrue(all(r['quality_status'] == 'ambiguous_village_id' for r in rows))

    def test_invalid_count_rejected(self):
        for cell in ('-1', 'NaN', 'approximately 3', '1.5'):
            with self.subTest(cell=cell), self.assertRaises(ValueError):
                sample(cell)

    def test_source_line_and_year_preserved(self):
        row = sample('2')[0]
        self.assertEqual(row['source_csv_line'], '2')
        self.assertEqual(row['Y2562'], '2')
        self.assertEqual(row['Y2567'], '')

    def test_news_id_not_joined_province_id_and_no_private_fields_exported(self):
        item = dict(id=22, news_id=1234, news_province='จันทบุรี', province_name='จันทบุรี',
                    news_date='2024-07-27 09:00:00', news_type_name='อุทกภัย',
                    news_title='flood report', latitude=12.0, longtitude=102.0,
                    news_detail='personal details should stay in ignored raw evidence')
        response = dict(status='success', data=dict(data=dict(data=[item])))
        row = news_records(response, '22')[0]
        self.assertTrue(row['url'].endswith('/1234'))
        self.assertNotIn('latitude', row)
        self.assertNotIn('news_detail', row)
        self.assertNotIn('event_start_date', row)
        with self.assertRaises(ValueError):
            news_records(response, '33')

    def test_post_harvest_event_not_counted_as_young_fruit_shock(self):
        result = stage_overlap(date(2024, 7, 27), 2024, 5, 130)
        self.assertEqual(result['on_or_after_harvest_candidate_days_pct'], 100)
        self.assertEqual(result['fruit_0_29d_candidate_days_pct'], 0)

    def test_short_shock_preserved_and_stages_exhaust_possible_dates(self):
        result = stage_overlap(date(2024, 5, 3), 2024, 5, 130)
        self.assertAlmostEqual(sum(result.values()), 100)
        self.assertAlmostEqual(result['on_or_after_harvest_candidate_days_pct'], 3 / 31 * 100)
        self.assertAlmostEqual(result['fruit_90_to_harvest_candidate_days_pct'], 28 / 31 * 100)

    def test_previous_calendar_year_can_overlap_next_year_fruit_stage(self):
        result = stage_overlap(date(2024, 12, 15), 2025, 2, 130)
        self.assertEqual(result['before_window_candidate_days_pct'], 0)
        self.assertEqual(result['on_or_after_harvest_candidate_days_pct'], 0)
        self.assertAlmostEqual(sum(result.values()), 100)


if __name__ == '__main__':
    unittest.main()
