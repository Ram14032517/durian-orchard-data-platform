import copy
import unittest
from tools import extract_chanthaburi_district_yield as e
from tools import build_tha_mai_spatial_pilot as p
from tests.research_support import require_files


class DistrictYieldExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_files(*(p.ROOT/e.OUT/name for name in ('district_year.json','reconciliation.json','field_lineage.json')))
        cls.rows=p.read_json(p.ROOT/e.OUT/"district_year.json")["rows"]

    def test_complete_extraction_and_known_visual_cells(self):
        self.assertTrue(e.validate(self.rows))
        self.assertEqual(len(self.rows),20)
        tha={r["year_be"]:r for r in self.rows if r["district_code"]=="2203"}
        self.assertEqual(tha[2566]["production_tonnes"],171229)
        self.assertEqual(tha[2567]["production_tonnes"],130314)
        self.assertTrue(all(r["source_anchor"]["pdf_page_1based"]==5 and r["source_anchor"]["table_number"]==2 for r in self.rows))

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            e.validate(self.rows+[self.rows[0]])

    def test_missing_coverage_rejected(self):
        with self.assertRaisesRegex(ValueError,"coverage"):
            e.validate(self.rows[:-1])

    def test_unit_and_negative_rejected(self):
        for mutate,error in [(lambda r:r["units"].update(production_tonnes="kg"),"Unit"),
                              (lambda r:r.update(production_tonnes=-1),"Negative")]:
            rows=copy.deepcopy(self.rows); mutate(rows[0])
            with self.assertRaisesRegex(ValueError,error): e.validate(rows)

    def test_missing_is_preserved_not_zero(self):
        rows=copy.deepcopy(self.rows); rows[0]["production_tonnes"]=None
        rows[0]["missingness"]["production_tonnes"]="missing_in_source"
        self.assertTrue(e.validate(rows))
        self.assertIsNone(rows[0]["production_tonnes"])
        self.assertIsNone(e.yield_check(rows[0])["derived_yield_kg_rai"])

    def test_yield_rounding_and_zero_bearing(self):
        self.assertTrue(all(e.yield_check(r)["status"]=="rounding_consistent" for r in self.rows))
        bad=copy.deepcopy(self.rows[0]); bad["reported_yield_kg_rai"]+=100
        self.assertEqual(e.yield_check(bad)["status"],"inconsistent")
        bad["bearing_area_rai"]=0
        self.assertEqual(e.yield_check(bad)["status"],"unavailable")

    def test_crosswalk_exact_and_ambiguity(self):
        admin=[{"AMPHOE_T":"อ.ท่าใหม่","AMPHOE_IDN":"2203"}]
        self.assertEqual(e.match_name("ท่าใหม่",admin),("2203","verified_normalized_exact"))
        self.assertEqual(e.match_name("ท่าใหม่",admin+[{"AMPHOE_T":"อ.ท่าใหม่","AMPHOE_IDN":"9999"}])[1],"ambiguous")
        self.assertEqual(e.match_name("unknown",admin)[1],"unmatched")

    def test_reconciliation_no_scaling_or_yield_sum(self):
        result=p.read_json(p.ROOT/e.OUT/"reconciliation.json")
        for row in result:
            if row["field"]=="standing_area_rai":
                self.assertEqual(row["difference_absolute"],7374 if row["year_be"]==2566 else 7804)
            else: self.assertEqual(row["difference_absolute"],0)
            if row["field"]=="reported_yield_kg_rai": self.assertIsNone(row["district_sum"])
            else: self.assertEqual(row["district_sum_minus_pdf_province"],0)

    def test_lineage_and_unverified_vintage_are_explicit(self):
        lineage=p.read_json(p.ROOT/e.OUT/"field_lineage.json")
        self.assertEqual(sum(x["field"] in e.FIELDS for x in lineage),80)
        self.assertTrue(all(r["publication_date"] is None and r["finality"]=="unverified"
                            and not r["training_eligible"] for r in self.rows))


if __name__=="__main__": unittest.main()
