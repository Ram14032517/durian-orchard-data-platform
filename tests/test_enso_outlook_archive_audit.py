import importlib.util
from datetime import date
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).resolve().parents[1] / 'tools/audit_enso_outlook_archive.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ArchiveAuditTests(unittest.TestCase):
    def test_future_and_same_day_rejected(self):
        records = [{'publication_date': '2025-01-09'}, {'publication_date': '2025-02-13'}]
        self.assertEqual(audit.select(records, date(2025, 1, 31)), records[0])
        self.assertIsNone(audit.select(records, date(2025, 1, 9)))

    def test_header_not_next_discussion(self):
        result = audit.parse(b'<div>issued by NOAA 9 January 2025</div><p>The next discussion is 13 February 2025.</p>', 2025, 1)
        self.assertEqual(result['publication_date'], '2025-01-09')
        self.assertIsNone(audit.parse(b'<div>issued by NOAA 9 January 2025</div>', 2017, 1)['publication_date'])

    def test_watch_not_observed_and_no_invented_probability(self):
        raw = '<div>issued by NOAA 9 January 2025</div><p>ENSO Alert System Status: El Niño Watch</p><p>Synopsis: El Niño is favored.</p><p>Overall, the system was consistent with ENSO-neutral.</p>'
        result = audit.parse(raw.encode(), 2025, 1)
        self.assertEqual(result['observed_state'], 'ENSO-neutral')
        self.assertEqual(result['forecast_probability_mentions'], [])
        self.assertFalse(result['revised_oni_used'])

    def test_sparse_probability_not_full_vector(self):
        result = audit.parse(b'<div>issued by NOAA 9 January 2025</div><p>Synopsis: ENSO-neutral has a ~60% chance.</p>', 2025, 1)
        self.assertTrue(result['forecast_probability_mentions'][0]['approximate'])
        self.assertIsNone(result['forecast_probability_mentions'][0]['phase'])
        self.assertEqual(result['probability_vector_status'], 'unverified_graphics_not_audited')

    def test_observed_modifiers_and_pdf_linebreak(self):
        raw = '<div>issued by NOAA 9 January 2025</div><p>Collectively, these oceanic and atmospheric patterns reflect the continuation of a weak to moderate La Niña.</p>'
        self.assertEqual(audit.parse(raw.encode(), 2025, 1)['observed_state'], 'La Niña')
        self.assertEqual(audit.normalized('ENSO-\nneutral'), 'ENSO-neutral')

    def test_calendar_locked(self):
        self.assertEqual(audit.issues(2020)['22'], date(2020, 2, 1))
        self.assertEqual(audit.issues(2025)['86'], date(2025, 5, 2))
        self.assertEqual(len(audit.ANCHORS), 5)

    def test_continued_observation_and_no_future_state(self):
        raw = '<div>issued by NOAA 7 February 2013</div><p>Synopsis: El Niño is expected during summer.</p><p>During January 2013, ENSO-neutral continued.</p>'
        self.assertEqual(audit.parse(raw.encode(), 2013, 2)['observed_state'], 'ENSO-neutral')
        self.assertIsNone(audit.parse(b'<p>Synopsis: El Nino is expected to continue during summer.</p>', 2013, 2)['observed_state'])


if __name__ == '__main__':
    unittest.main()
