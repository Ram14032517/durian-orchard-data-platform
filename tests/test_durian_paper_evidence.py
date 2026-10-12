import unittest
from tools.export_durian_paper_evidence import require_verified


class PaperEvidenceTests(unittest.TestCase):
    def test_article_claim_not_certified_data(self):
        self.assertTrue(require_verified({'status':'data_source_lead_only'}))

    def test_missing_year_fails_official_certification(self):
        with self.assertRaises(ValueError):
            require_verified({'status':'verified_official_district_year_data','district_code':'2203','year_ce':None})

    def test_complete_evidence_record(self):
        self.assertTrue(require_verified(dict(status='verified_official_district_year_data',district_code='2203',
            year_ce=2023,unit='kg/rai',official_origin_evidence='sealed DOAE Table2',source_sha256='a'*64,anchor='p5 table2 row3')))

    def test_missing_unit_or_lineage_fails(self):
        for field in ('unit','source_sha256','anchor','official_origin_evidence'):
            r=dict(status='verified_official_district_year_data',district_code='2203',year_ce=2023,
                unit='kg/rai',source_sha256='a'*64,anchor='p5',official_origin_evidence='DOAE')
            r[field]=None
            with self.assertRaises(ValueError): require_verified(r)


if __name__=='__main__': unittest.main()
