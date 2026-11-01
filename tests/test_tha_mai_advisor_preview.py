"""Display-only aggregation/accepted-input checks; never write GIS artifacts."""
import copy
import unittest
from tools import build_tha_mai_advisor_preview as a
from tools import build_tha_mai_spatial_pilot as p
from tools import run_tha_mai_acceptance_policy as f
from tests.research_support import needs_files


class AdvisorPreviewTests(unittest.TestCase):
    def test_display_grouping_preserves_area_and_special_units(self):
        rows=[{"soil_unit":str(i),"area_rai":i+1} for i in range(8)]
        rows += [{"soil_unit":code,"area_rai":1e-9} for code in a.SPECIAL]
        before=copy.deepcopy(rows)
        top,groups=a.display_groups(rows)
        self.assertEqual(len(top),6)
        self.assertTrue(a.SPECIAL.issubset(groups))
        self.assertEqual(groups["OTHER"],3)
        self.assertAlmostEqual(sum(groups.values()),sum(r["area_rai"] for r in rows))
        self.assertEqual(rows,before)

    @needs_files(p.ROOT/f.RELEASE/'output_manifest.json', p.ROOT/a.OUT/'soil_composition_summary.json')
    def test_accepted_input_and_display_values_are_identical(self):
        release=p.ROOT/f.RELEASE
        p.previous.verify_seal(p.ROOT,f.RELEASE)
        source=p.read_json(release/"dataset.json")["tables"]["soil_composition"]
        shown=p.read_json(p.ROOT/a.OUT/"soil_composition_summary.json")["rows"]
        self.assertEqual(len(source),43)
        self.assertEqual(len(shown),43)
        for original,row in zip(source,shown):
            self.assertTrue(all(row[key]==value for key,value in original.items()))

    @needs_files(p.ROOT/a.OUT/'display_qc.json')
    def test_display_census_and_public_hold(self):
        qc=p.read_json(p.ROOT/a.OUT/"display_qc.json")
        self.assertEqual(qc["map_record_counts"]["pure_panel1"],1504)
        self.assertEqual(qc["map_record_counts"]["pure_panel3"],1504)
        self.assertEqual(qc["map_record_counts"]["mixed_panel3"],1407)
        self.assertFalse(qc["raw_overlay_rerun"])
        self.assertEqual(qc["public_release"],"HOLD")
        self.assertEqual(len(qc["geometry_warnings"]),1)


if __name__=="__main__": unittest.main()
