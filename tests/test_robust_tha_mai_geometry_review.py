"""Contract tests: no special-case waiver for the quarantined Golden Fixture."""
import copy
import unittest
from unittest.mock import patch
import shapely
from shapely.geometry import box, Polygon
from tools import diagnose_tha_mai_geometry as d
from tools import robust_tha_mai_geometry_review as r


class RobustPartitionTests(unittest.TestCase):
    def test_valid_partition_requires_all_invariants(self):
        report=r.partition(box(0,0,80,40),[box(0,0,40,40)],[box(40,0,80,40)],"synthetic")
        self.assertEqual(report["status"],"pass")
        self.assertTrue(all(x["pass"] for x in report["checks"]))
        self.assertTrue(all(not x["material"] for x in report["operation_conflicts"]))
        self.assertEqual(report["tolerance_rai"],.1)

    def test_golden_primary_pass_with_upper_bound_warning_not_id_waiver(self):
        fixture=d.read(d.ROOT/d.OUT/"minimal_inputs.json")
        g,cuts,m=d.load_fixture(fixture)
        before=[d.geometry_hash(x) for x in [g]+cuts+m]
        report=r.partition(g,cuts,m,"any_label_not_special_cased")
        self.assertEqual(report["status"],"pass")
        self.assertTrue(all(x["pass"] for x in report["checks"]))
        excess=next(x["value_rai"] for x in report["operation_conflicts"] if x["check"]=="two-stage union upper bound")
        self.assertAlmostEqual(excess,14.277753561016052,places=6)
        self.assertGreater(report["holes"][0]["two_stage_in_hole_rai"],14)
        self.assertEqual(report["diagnostic_warnings"][0]["geos_version"],shapely.geos_version_string)
        self.assertEqual(report["diagnostic_warnings"][0]["label"],"any_label_not_special_cased")
        self.assertEqual(before,[d.geometry_hash(x) for x in [g]+cuts+m])

    def test_altered_soil_cut_outside_g_rejected(self):
        report=r.partition(box(0,0,40,40),[box(0,0,50,40)],[],"altered")
        self.assertEqual(report["status"],"failed")
        self.assertTrue(any(not x["pass"] and x["check"]=="covered outside G" for x in report["checks"]))

    def test_overlapping_soil_cuts_rejected(self):
        report=r.partition(box(0,0,40,40),[box(0,0,40,40),box(0,0,20,40)],[],"overlap")
        self.assertEqual(report["status"],"failed")
        self.assertTrue(any(not x["pass"] and x["check"]=="soil cuts double counting" for x in report["checks"]))

    def test_missing_uncovered_rejected(self):
        report=r.partition(box(0,0,80,40),[box(0,0,40,40)],[],"missing")
        self.assertEqual(report["status"],"failed")

    def test_uncovered_overlapping_covered_rejected(self):
        report=r.partition(box(0,0,80,40),[box(0,0,40,40)],[box(20,0,80,40)],"overlap")
        self.assertEqual(report["status"],"failed")

    def test_uncovered_outside_g_rejected(self):
        report=r.partition(box(0,0,80,40),[box(0,0,40,40)],[box(40,0,100,40)],"outside")
        self.assertEqual(report["status"],"failed")

    def test_invalid_geometry_rejected(self):
        bow=Polygon([(0,0),(40,40),(40,0),(0,40),(0,0)])
        with self.assertRaisesRegex(ValueError,"Invalid persisted geometry"):
            r.partition(bow,[],[],"invalid")

    def test_filled_hole_rejected_even_if_geometry_valid(self):
        g=Polygon([(0,0),(80,0),(80,80),(0,80)], [[(20,20),(20,60),(60,60),(60,20)]])
        report=r.partition(g,[box(0,0,80,80)],[],"filled")
        self.assertEqual(report["status"],"failed")
        self.assertGreater(report["holes"][0]["original_pieces_in_hole_rai"],.1)

    def test_correct_hole_partition_passes(self):
        g=Polygon([(0,0),(80,0),(80,80),(0,80)], [[(20,20),(20,60),(60,60),(60,20)]])
        self.assertEqual(r.partition(g,[g],[],"valid_hole")["status"],"pass")

    def test_no_missing_sliver_is_dropped(self):
        g=box(0,0,80,40); tiny=box(79.999999,0,80,40); covered=box(0,0,79.999999,40)
        before=tiny.wkb
        report=r.partition(g,[covered],[tiny],"tiny")
        self.assertEqual(report["status"],"pass")
        self.assertGreater(report["areas_rai"]["M"],0)
        self.assertEqual(tiny.wkb,before)

    def test_duplicate_fragment_rejected(self):
        from tools import build_tha_mai_spatial_pilot as p
        dataset=p.read_json(p.ROOT/p.DEFAULT/"dataset.json")
        dataset["tables"]["district_fragments"].append(copy.deepcopy(dataset["tables"]["district_fragments"][0]))
        with self.assertRaisesRegex(ValueError,"Duplicate district_fragments"):
            r.review(dataset)

    def test_mixed_use_soil_contamination_rejected(self):
        from tools import build_tha_mai_spatial_pilot as p
        dataset=p.read_json(p.ROOT/p.DEFAULT/"dataset.json")
        mixed=next(row for row in dataset["tables"]["district_fragments"] if row["kind"]=="mixed")
        dataset["tables"]["soil_intersections"][0]["fragment_id"]=mixed["fragment_id"]
        with self.assertRaisesRegex(ValueError,"Mixed allocated as pure soil"):
            r.review(dataset)

    def test_binary_warning_never_overrides_primary_failure(self):
        fixture=d.read(d.ROOT/d.OUT/"minimal_inputs.json")
        g,cuts,m=d.load_fixture(fixture)
        report=r.partition(g,cuts+[cuts[0]],m,"any_label")
        self.assertEqual(report["status"],"failed")
        self.assertTrue(any(not x["pass"] for x in report["checks"]))

    def test_unexplained_binary_contradiction_is_inconclusive(self):
        with patch("shapely.geometry.base.BaseGeometry.union",return_value=box(40,0,80,40)):
            report=r.partition(box(0,0,40,40),[box(0,0,40,40)],[],"unknown_conflict")
        self.assertEqual(report["status"],"inconclusive")
        self.assertFalse(report["diagnostic_warnings"])

    def test_primary_operation_error_is_inconclusive(self):
        with patch("shapely.union_all",side_effect=RuntimeError("primary failure")):
            report=r.partition(box(0,0,40,40),[box(0,0,40,40)],[],"primary_error")
        self.assertEqual(report["status"],"inconclusive")


if __name__=="__main__": unittest.main()
