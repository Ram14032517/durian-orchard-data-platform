import copy
import unittest
from unittest.mock import patch
from tools import audit_chanthaburi_historical_district_yield as a
from tools import extract_chanthaburi_district_yield as extraction
from tests.research_support import needs_files


class HistoricalDistrictAuditTests(unittest.TestCase):
    def setUp(self):
        original = a.read
        crosswalk = [{'district_code':str(2201+i),'table_district_name':row[0]}
                     for i,row in enumerate(extraction.TRANSCRIPTION)]
        mock = patch.object(a,'read',side_effect=lambda path:
            crosswalk if path == a.OLD/'district_crosswalk.json' else original(path))
        mock.start();self.addCleanup(mock.stop)

    def row(self):
        return dict(province_code='22',district_code='2201',district_name='เมืองจันทบุรี',
            year_be=2566,year_ce=2023,year_basis='unverified_test_fixture',commodity='ทุเรียน',
            standing_area_rai=150.,bearing_area_rai=100.,production_tonnes=200.,reported_yield_kg_rai=2000.,
            units=extraction.UNITS.copy(),missingness={f:'present' for f in extraction.FIELDS},
            source_version='a'*64,source_sha256='a'*64,source_anchor={'fixture':'synthetic_unit_only'},
            finality='unverified',acceptance_scope='source_transcription_only')

    def test_crosswalk_rejects_wrong_name(self):
        r=self.row(); r['district_name']='ท่าใหม่'
        with self.assertRaisesRegex(ValueError,'Crosswalk'): a.validate([r])

    def test_units_reject_tonne_as_kg(self):
        r=self.row(); r['units']['production_tonnes']='kg'
        with self.assertRaisesRegex(ValueError,'Unit'): a.validate([r])

    def test_year_definition_unverified_is_not_final_certification(self):
        r=self.row(); self.assertTrue(a.validate([r]))
        r['acceptance_scope']='final_actual'
        with self.assertRaisesRegex(ValueError,'Unverified year'): a.validate([r])

    def test_year_conversion(self):
        r=self.row(); r['year_ce']+=1
        with self.assertRaisesRegex(ValueError,'Year definition'): a.validate([r])

    def test_finality_requires_evidence(self):
        r=self.row(); r['finality']='final'
        with self.assertRaisesRegex(ValueError,'Final without'): a.validate([r])

    def test_missingness_is_not_zero_or_imputed_target(self):
        r=self.row(); r['reported_yield_kg_rai']=None
        with self.assertRaisesRegex(ValueError,'Missingness'): a.validate([r])
        r['missingness']['reported_yield_kg_rai']='missing_in_source'
        self.assertTrue(a.validate([r])); self.assertFalse(a.target_complete(r))
        self.assertIsNone(a.yield_check(r)['derived_yield_kg_rai'])

    def test_version_duplicates_fail_but_different_versions_survive(self):
        r=self.row()
        with self.assertRaisesRegex(ValueError,'Duplicate'): a.validate([r,copy.deepcopy(r)])
        s=copy.deepcopy(r); s['source_version']=s['source_sha256']='b'*64
        self.assertTrue(a.validate([r,s]))

    def test_arithmetic_rounding_and_corruption(self):
        r=self.row(); self.assertEqual(a.yield_check(r)['status'],'rounding_consistent')
        r['reported_yield_kg_rai']+=100
        with self.assertRaisesRegex(ValueError,'Arithmetic'): a.validate([r])

    def test_source_lineage_and_anchor_required(self):
        r=self.row(); r['source_anchor']={}
        with self.assertRaisesRegex(ValueError,'lineage'): a.validate([r])
        r=self.row(); r['source_sha256']='c'*64
        with self.assertRaisesRegex(ValueError,'lineage'): a.validate([r])

    @needs_files(a.OUT/'candidate_standing_area.csv',a.OUT/'candidate_standing_source.json')
    def test_candidate_coverage_never_counts_as_yield(self):
        rows=a.candidate_rows()
        self.assertEqual(len(rows),110)
        self.assertEqual({r['year_be'] for r in rows},set(range(2557,2568)))
        for y in range(2557,2568):
            self.assertEqual({r['district_code'] for r in rows if r['year_be']==y},set(map(str,range(2201,2211))))
        self.assertFalse(any(a.target_complete(r) for r in rows))
        self.assertTrue(all(r['publication_date'] is None and r['revision_date'] is None for r in rows))

    def test_negative_and_nonfinite_values(self):
        for value in (-1,float('nan')):
            r=self.row(); r['standing_area_rai']=value
            with self.assertRaisesRegex(ValueError,'Negative'): a.validate([r])


if __name__=='__main__': unittest.main()
