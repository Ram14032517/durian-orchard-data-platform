"""Small diagnostic-tool checks, not acceptance of the quarantined dataset."""
import unittest
import shapely
from shapely.geometry import box, Polygon
from tools import diagnose_tha_mai_geometry as d


def record(g, ident):
    return {"fragment_id":ident,"geometry_wkt":shapely.to_wkt(g,rounding_precision=-1),
            "geometry_sha256":d.geometry_hash(g),"area_m2":g.area}


class DiagnosisTests(unittest.TestCase):
    def test_synthetic_partition_operations(self):
        g=box(0,0,40,40); c=box(0,0,20,40); m=box(20,0,40,40)
        fixture={"G":record(g,"g"),"soil_cuts":[record(c,"c")],"uncovered_pieces":[record(m,"m")]}
        result=d.diagnose(fixture)
        self.assertEqual(result["qc_tolerance_rai_unchanged"],.1)
        unions=[x for x in result["operations"] if x["operation"] in ["C.union(M)","union_all(cuts+missing)"]]
        self.assertEqual(len(unions),2)
        self.assertTrue(all(x["area_rai"]==1 and not x["upper_bound_failed"] for x in unions))
        self.assertTrue(all(x["stored_geometry_hash_matches"] for x in result["serialization"]))

    def test_upper_bound_violation_is_flagged(self):
        r,_=d.operation("bad",lambda:box(0,0,40,40),upper=800)
        self.assertTrue(r["upper_bound_failed"])
        self.assertEqual(r["excess_rai"],.5)

    def test_holes_and_orientation_are_preserved(self):
        g=Polygon([(0,0),(40,0),(40,40),(0,40)], [[(10,10),(10,30),(30,30),(30,10)]])
        info=d.describe(g)
        self.assertEqual(info["hole_count"],1)
        self.assertEqual(info["rings"][1]["ring_enclosed_area_rai"],.25)
        self.assertEqual(d.geometry_hash(g),d.geometry_hash(shapely.from_wkt(shapely.to_wkt(g,rounding_precision=-1))))

    def test_empty_geometry_diagnostic(self):
        info=d.describe(Polygon())
        self.assertTrue(info["is_empty"]); self.assertEqual(info["area_m2"],0)
        self.assertIsNone(info["bounds"])

    def test_operation_error_is_recorded_not_hidden(self):
        def broken(): raise ValueError("operation failure")
        row,g=d.operation("fails",broken)
        self.assertIn("operation failure",row["error"]); self.assertIsNone(g)


if __name__=="__main__": unittest.main()
